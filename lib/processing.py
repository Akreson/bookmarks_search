import aiohttp
import asyncio
import multiprocessing
import os
import sys
import re
import time
import math
from typing import Set, List, Tuple, Optional

from .aggregate import AggregateResult
from .data_parser import SearchData, UrlGroup
from .custom_types import (
    Context,
    Queue,
    MatchingResult,
    WorkerJobData,
    WorkerTaskResult,
)

proc_context: Context = multiprocessing.get_context('spawn')

def find_matching(text: str, find_strings: List[str]) -> MatchingResult:
    result = []

    for i, string in enumerate(find_strings):
        match_pos = [m.start() for m in re.finditer(string, text)]

        #NOTE: count_match not used for now
        count_match = len(match_pos)
        if count_match != 0:
            result.append((i, count_match))
    
    return result

class WorkerCommand:
    End = 0
    Task = 1
    JobInfo = 2

#NOTE: Worker command
#(JobInfo, (start link index, time to wait req. completed, max async task, string for search, urls list to process))
#(Task, (link index, search result for each string))
#(End, 0)

class Worker:
    def __init__(self, result_q: Queue, task_q: Queue) -> None:
        self.result_q = result_q
        self.task_q = task_q
        self.search_string = []
        self.urls = []
        self.add_index = 0
        self.max_async_task = 0
        self.last_pushed_url_count = 0

        self.global_done = 0

        self.process = proc_context.Process(target=self.start_processing)

    def start(self) -> None:
        self.process.start()

    def init_tasks_data(self, task_payload: WorkerJobData) -> None:
        self.add_index = task_payload[0]
        self.time_to_wait = task_payload[1]
        self.max_async_task = task_payload[2]
        self.search_string = list(task_payload[3])
        self.urls = list(task_payload[4])

        self.max_async_task = min(len(self.urls), self.max_async_task)
        
    def dispatch_task(self, link_index: int, html: str) -> None:
        result_msg = find_matching(html, self.search_string)

        if len(result_msg) > 0:
            prime_link_index = link_index + self.add_index
            self.result_q.put_nowait((WorkerCommand.Task, (prime_link_index, list(result_msg))))

    #TODO: Handling and store error
    async def process_link(self, session: aiohttp.ClientSession, link_index: int) -> None:
        link_url = self.urls[link_index]

        try:
            async with session.get(link_url) as response:
                if response.status >= 200 and response.status <= 299:
                    html = await response.text()
                    self.dispatch_task(link_index, html)
                    self.global_done += 1
        except:
            pass
    
    def push_init_pending_links(
        self, session: aiohttp.ClientSession, pending_task: Set[asyncio.Task]
    ) -> None:
        for i in range(self.max_async_task):
            task = asyncio.create_task(self.process_link(session, i))
            pending_task.add(task)
        
        self.last_pushed_url_count = self.max_async_task

    async def run(self) -> None:
        pending_task: Set[asyncio.Task] = set()
        urls_count = len(self.urls)

        if self.max_async_task > 100:
            conn = aiohttp.TCPConnector(limit=self.max_async_task)
        else:
            conn = aiohttp.TCPConnector()
        
        if self.time_to_wait != 0:
            conn_timeout = aiohttp.ClientTimeout(total=None, sock_connect=self.time_to_wait, sock_read=self.time_to_wait)
        else:
            conn_timeout = aiohttp.ClientTimeout()

        async with aiohttp.ClientSession(connector=conn, timeout=conn_timeout) as session:
            self.push_init_pending_links(session, pending_task)
            
            while pending_task:
                done, _ = await asyncio.wait(pending_task,  timeout=2, return_when=asyncio.FIRST_COMPLETED)
                print('IN SET {}\n'.format(len(pending_task)))

                for future in done:
                    pending_task.discard(future)

                    if self.last_pushed_url_count < urls_count:
                        task = asyncio.create_task(self.process_link(session, self.last_pushed_url_count))
                        pending_task.add(task)
                        self.last_pushed_url_count += 1
    
    def start_processing(self) -> None:
        while True:
            try:
                task = self.task_q.get()
            except self.task_q.Empty:
                time.sleep(0.005)
                continue

            task_type, task_payload = task

            if task_type == WorkerCommand.JobInfo:
                self.init_tasks_data(task_payload)
                break
        
        asyncio.run(self.run())
        self.result_q.put((WorkerCommand.End, 0))


class DataProcess:
    def __init__(
        self, search_data: SearchData,
        payload_string: Optional[List[str]] = None,
        max_workers: int = 4,
        max_async_task: int = 200,
        max_wait_time: int = 0
    ) -> None:
        self.worker_count = max(1, min(os.cpu_count() - 1, max_workers))
        self.worker_proc = []
        self.search_data = search_data
        self.search_string = payload_string
        self.max_wait_time = max_wait_time

        self.max_async_task = min(max_async_task, len(self.search_data.urls))
        self.last_pushed_url_count = self.max_async_task
    
    def create_worker(self) -> Worker:
        result_q = proc_context.Queue()
        task_q = proc_context.Queue()
        worker = Worker(result_q, task_q)
        worker.start()

        return worker

    def init_workers(self) -> None:
        for _ in range(self.worker_count):
            self.worker_proc.append(self.create_worker())

        urls_len = len(self.search_data.urls)
        task_per_worker = int(math.floor(urls_len / self.worker_count))
        remain_task = urls_len % self.worker_count

        start_index = 0
        end_index = task_per_worker + remain_task
        for worker in self.worker_proc:
            urls_list = self.search_data.urls[start_index:end_index]
            worker_task_data = \
                (WorkerCommand.JobInfo, (start_index, self.max_wait_time, self.max_async_task, self.search_string, urls_list)) 

            worker.task_q.put(worker_task_data)

            start_index += task_per_worker
            end_index += task_per_worker


    def link_processing(self, aggregate: AggregateResult) -> None:
        self.init_workers()

        while True:
            if len(self.worker_proc) > 0:
                for worker in self.worker_proc:
                    try:
                        task_comm, task_payload = worker.result_q.get()
                    except worker.result_q.Empty:
                        continue
                    
                    if task_comm == WorkerCommand.Task:
                        aggregate.put(task_payload)
                    elif task_comm == WorkerCommand.End:
                        self.worker_proc.remove(worker)
            else:
                break
        
        aggregate.sort_group_index()
    
    def title_processing(self, aggregate: AggregateResult) -> None:
        search_string = self.search_string
        
        for i, title in enumerate(self.search_data.urls_title):
            match_result = find_matching(title, search_string)
            aggregate.put((i, match_result))
        
        aggregate.sort_group_index()
    
    def url_processing(self, aggregate: AggregateResult) -> None:
        search_string = self.search_string

        for i, url in enumerate(self.search_data.urls):
            match_result = find_matching(url, search_string)
            aggregate.put((i, match_result))
        
        aggregate.sort_group_index()

    #TODO: Make more efficient group index grub
    def stdout_print(self, aggregate: AggregateResult) -> None:
        if aggregate.id_count:
            for url_group in self.search_data.url_group:

                find_group_result = ''
                for find_group in aggregate.find_group:

                    link_result = ''
                    for _, id in enumerate(find_group.urls_id):
                        if id >= url_group.min and id < url_group.max:
                            url = self.search_data.urls[id]
                            url_title = self.search_data.urls_title[id]

                            link_info = '\t\t{0}\n\t\t{1}\n\n'.format(url_title, url)
                            link_result += link_info
                    
                    if len(link_result) != 0:
                        find_group_name = '\t- {}\n'.format(find_group.name)
                        find_group_result += (find_group_name + link_result)

                if len(find_group_result) != 0:
                    url_group_name = '-- {}\n'.format(url_group.name)
                    url_group_name += find_group_result
                    sys.stdout.buffer.write(url_group_name.encode('utf-8'))
        else:
            print('No result')

    def set_group_str_info(self, get_group: UrlGroup) -> str:
        result = ''
        result += '-- {}\n'.format(get_group.name)

        start_id = get_group.min
        for i in range(get_group.count):
            id = start_id + i
            url = self.search_data.urls[id]
            url_title = self.search_data.urls_title[id]

            link_info = '\t\t{0}\n\t\t{1}\n\n'.format(url_title, url)
            result += link_info
        
        result += '\n\n'
        return result

    def get_group_data(self, group_list: List[str]) -> None:
        if len(group_list) != 0:
            for get_group_name in group_list:
                for url_group in self.search_data.url_group:
                    if get_group_name == url_group.name:
                        group_result = self.set_group_str_info(url_group)
                        sys.stdout.buffer.write(group_result.encode('utf-8'))
        else:
            for url_group in self.search_data.url_group:
                group_result = self.set_group_str_info(url_group)
                sys.stdout.buffer.write(group_result.encode('utf-8'))
        

    def run(self, title_op: bool, url_op: bool, group_op: Optional[List[str]] = None) -> None:
        if group_op is None:
            if self.search_string is not None:
                aggregate = AggregateResult(self.search_string)
               
                if title_op:
                    self.title_processing(aggregate)
                elif url_op:
                    self.url_processing(aggregate)
                else:
                    self.link_processing(aggregate)

                self.stdout_print(aggregate)
            else:
                print('Error: put some string for search')
        else:
            self.get_group_data(group_op)