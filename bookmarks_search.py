import os
import sys
import argparse
import multiprocessing
import itertools
import asyncio
import queue
import re
import time

import aiohttp

from data_parser import SearchData

proc_context = multiprocessing.get_context('spawn')

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

class Worker:
    def __init__(self, result_q, task_q):
        self.task_q = task_q
        self.result_q = result_q
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
            count_match = len(match_pos)
            if count_match != 0:
                result_msg.append((i, count_match))
        
        if len(result_msg):
            self.result_q.put((link_index, result_msg))

    def run(self):

        running = True
        while running:
            try:
                task = self.task_q.get()
            except queue.Empty:
                time.sleep(0.005)
                continue
            
            task_type, task_payload = task

            if task_type == WorkerCommand.Task:
                self.dispatch_task(task_payload)
            elif task_type == WorkerCommand.JobInfo:
                self.string_list = task_payload
            elif task_type == WorkerCommand.End:
                self.result_q.put((WorkerCommand.End, 0))
                running = False

class DataProcess:
    def __init__(self, search_data, max_async_task = 200):
        self.worker_count = min(os.cpu_count() - 1, 4)
        self.worker_proc = []
        self.scheduler = Scheduler()
        self.search_data = search_data

        self.max_async_task = min(max_async_task, len(self.search_data.urls))
        self.last_pushed_url_count = self.max_async_task

        self.init()
    
    def init(self):
        for _ in range(self.worker_count):
            self.worker_proc.append(self.create_worker())

        for worker in self.worker_proc:
            worker.task_q.put((WorkerCommand.JobInfo, list(self.search_data.strings_to_find)))
            
        self.scheduler.register_queue(self.worker_proc)

#NOTE: Test code
        time.sleep(1)
        test_count = 0
        while True:
            if not len(self.worker_proc):
                break
            print('{0} {1}'.format(test_count, len(self.worker_proc)))
            
            for worker in self.worker_proc:
                try:
                    result = worker.result_q.get()
                    test_count += 1
                    print('{0} {1}'.format(result, worker.process.is_alive()))
                    self.worker_proc.remove(worker)
                except queue.Empty:
                    continue
        print('End')

    def create_worker(self):
        result_q = proc_context.Queue()
        task_q = proc_context.Queue()
        worker = Worker(result_q, task_q)
        worker.start()

        return worker

    def send_worker_end(self):
        for worker in self.worker_proc:
            worker.task_q.put((WorkerCommand.End, 0))

    async def process_link(self, session, link_index):
        link_url = self.search_data.urls[link_index]

        async with session.get(link_url) as response:
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

        async with aiohttp.ClientSession as session:
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

    def run(self):
        asyncio.run(self.start_processing())


def main():
    cli_args = parse_cmd_args()
    search_data = SearchData(cli_args.file, cli_args.exclude, cli_args.string)
    data_process = DataProcess(search_data)
    #data_process.run()

    #for group in search_data.url_group:
    #    print(group.name)

    print(cli_args)

if __name__ == "__main__":
    main()