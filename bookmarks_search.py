import os
import sys
import argparse
import multiprocessing
import itertools
import asyncio
import queue
import re
import time
import math

import aiohttp

from data_parser import SearchData

proc_context = multiprocessing.get_context('spawn')

def get_set_bit(num, max_range):
    return [i for i in range(max_range) if num & (1 << i)]

class AggregateGroup:
    def __init__(self):
        self.name = ''
        self.urls_id = []
        self.last_stopped = 0

class AggregateResult:
    def __init__(self, find_string_groups):
        self.id_count = 0
        self.prime_group_count = len(find_string_groups)
        self.find_group = [None]*(2**self.prime_group_count)

        self.init_coll_group(find_string_groups)
    
    def init_coll_group(self, find_string_groups):

        aggregate_group_count = len(self.find_group)
        for i in range(1, aggregate_group_count):
            agg_group = AggregateGroup()

            find_string_groups_id = get_set_bit(i, self.prime_group_count)
            for i, id in enumerate(find_string_groups_id):
                group_separator = ''
                if i > 0:
                    group_separator = ', '

                group = find_string_groups[id]
                agg_group.name += (group + group_separator)

            self.find_group[i] = agg_group

    def put(self, task_data):
        link_id, task_results = task_data

        group_id = 0
        for result in task_results:
            group_id |= 1 << result[0]

        if group_id != 0:
            group = self.find_group[group_id]
            if group:
                group.urls_id.append(link_id)
                self.id_count += 1
    
    def sort_group_index(self):

        new_group = [group for group in self.find_group if group != None]
        self.find_group = new_group

        for group in self.find_group:
            group.urls_id.sort()

class Scheduler:
    def __init__(self):
        self.queue = None
    
    def register_queue(self, queue):
        self.queue = itertools.cycle(queue)
    
    def next(self):
        return next(self.queue)

class WorkerCommand:
    End = 0
    Task = 1
    JobInfo = 2

#NOTE: Worker message:
# (WorkerCommand.End, 0)
# (WorkerCommand.Task, (link id, [(group_id, match_count), ...]list of tuple))

class Worker:
    def __init__(self, result_q, task_q):
        self.result_q = result_q
        self.task_q = task_q
        self.find_string = []

        self.process = proc_context.Process(target=self.run)

    def start(self):
        self.process.start()

    def dispatch_task(self, task_payload):
        link_index = task_payload[0]
        html = task_payload[1]

        result_msg = []
        for i, string in enumerate(self.find_string):
            match_pos = [m.start() for m in re.finditer(string, html)]

            #NOTE: count_match not used for now
            count_match = len(match_pos)
            if count_match != 0:
                result_msg.append((i, count_match))
                    
        if len(result_msg):
            #print('-Put to result queue')
            self.result_q.put((WorkerCommand.Task, (link_index, list(result_msg))))

    def run(self):

        running = True
        while running:
            try:
                task = self.task_q.get()
            except self.task_q.Empty:
                time.sleep(0.005)
                continue
            
            task_type, task_payload = task
            if task_type == WorkerCommand.Task:
                self.dispatch_task(task_payload)
            elif task_type == WorkerCommand.JobInfo:
                self.find_string = task_payload
            elif task_type == WorkerCommand.End:
                self.result_q.put((WorkerCommand.End, 0))
                #print('-Worker END')
                running = False

class DataProcess:
    def __init__(self, search_data, max_async_task = 200):
        self.worker_count = min(os.cpu_count() - 1, 4)
        self.worker_proc = []
        self.scheduler = Scheduler()
        self.search_data = search_data

        self.max_async_task = min(max_async_task, len(self.search_data.urls))
        self.last_pushed_url_count = self.max_async_task

        print(len(self.search_data.urls))

        self.init()
    
    def init(self):
        for _ in range(self.worker_count):
            self.worker_proc.append(self.create_worker())

        for worker in self.worker_proc:
            worker.task_q.put((WorkerCommand.JobInfo, list(self.search_data.strings_to_find)))
            
        self.scheduler.register_queue(self.worker_proc)

    def create_worker(self):
        result_q = proc_context.Queue()
        task_q = proc_context.Queue()
        worker = Worker(result_q, task_q)
        worker.start()

        return worker

    def wait_workers(self):
        wait = True

        while wait:
            wait = False

            for worker in self.worker_proc:
                if worker.process.is_alive():
                    wait = True
            
            if wait:
                time.sleep(0.01)

    def send_worker_end(self):
        for worker in self.worker_proc:
            worker.task_q.put((WorkerCommand.End, 0))

    async def process_link(self, session, link_index):
        link_url = self.search_data.urls[link_index]
        async with session.get(link_url) as response:
            #print('{0}\n{1}'.format(link_url, response.status))
            if response.status >= 200 and response.status <= 299:
                html = await response.text()
                
                worker_task = (WorkerCommand.Task, (link_index, html))
                worker = self.scheduler.next()
                worker.task_q.put_nowait(worker_task)
    
    def push_init_pending_links(self, session, pending_task):
        for i in range(self.max_async_task):
            task = asyncio.create_task(self.process_link(session, i))
            pending_task.append(task)

    async def start_processing(self):
        pending_task = []

        async with aiohttp.ClientSession() as session:
            self.push_init_pending_links(session, pending_task)
            
            while pending_task:
                done, _ = await asyncio.wait(pending_task, return_when=asyncio.FIRST_COMPLETED)

                for future in done:
                    pending_task.remove(future)

                    if self.last_pushed_url_count < len(self.search_data.urls):
                        task = asyncio.create_task(self.process_link(session, self.last_pushed_url_count))
                        pending_task.append(task)
                        self.last_pushed_url_count += 1
        
        self.send_worker_end()

    def aggregate_processing(self, aggregate_result):
        for worker in self.worker_proc:
            while True:
                try:
                    task_comm, task_payload = worker.result_q.get()
                except worker.result_q.Empty:
                    #print('-EMPTY')
                    break
                
                if task_comm == WorkerCommand.Task:
                    #print('-TASK RES')
                    aggregate_result.put(task_payload)
                elif task_comm == WorkerCommand.End:
                    #print('-END COMMAND')
                    break
        
        aggregate_result.sort_group_index()
    
    def stdout_print(self, aggregate_result):
        if aggregate_result.id_count:
            for url_group in self.search_data.url_group:
                url_group_name = '-- {}\n'.format(url_group.name).encode('utf-8')
                sys.stdout.buffer.write(url_group_name)

                for find_group in aggregate_result.find_group:
                    find_group_name = '\t- {}\n'.format(find_group.name).encode('utf-8')
                    sys.stdout.buffer.write(find_group_name)

                    for i, id in enumerate(find_group.urls_id[find_group.last_stopped:]):
                        if id < url_group.max:
                            url = self.search_data.urls[id]
                            url_title = self.search_data.urls_title[id]

                            link_info = '\t\t{0}\n\t\t{1}\n\n'.format(url_title, url).encode('utf-8')
                            sys.stdout.buffer.write(link_info)
                        else:
                            find_group.last_stoped = i

        else:
            print('No result')
            
    def run(self):
        asyncio.run(self.start_processing())

        aggregate_result = AggregateResult(self.search_data.strings_to_find)

        self.wait_workers()

        self.aggregate_processing(aggregate_result)
        self.stdout_print(aggregate_result)


def parse_cmd_args():
    cli_parser = argparse.ArgumentParser()
    cli_parser.add_argument('-f', '--file', action='store', nargs='+', required=True,
        help='''set file for parse (must be saved file from browser bookmarks .html file
            or from browser ext. SpeedDeal .json)''')
    cli_parser.add_argument('-s', '--string', action='store', nargs='+', required=True,
        help='string for search in url links')
    cli_parser.add_argument('-g', '--group', action='store', nargs='+',
        help='group of bookmarks in provided file')
    cli_parser.add_argument('-ex', '--exclude', action='store', nargs='+',
        help='exclude group from search')

    cli_args = cli_parser.parse_args()
    return cli_args

def main():
    cli_args = parse_cmd_args()
    search_data = SearchData(cli_args.file, cli_args.group, cli_args.exclude, cli_args.string)

    for group in search_data.url_group:
        print(group.name)

    data_process = DataProcess(search_data)
    data_process.run()

if __name__ == "__main__":
    main()