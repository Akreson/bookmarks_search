from typing import List 
from .custom_types import WorkerTaskResult

def get_set_bit(num: int, max_range: int) -> List[int]:
    return [i for i in range(max_range) if num & (1 << i)]

class AggregateGroup:
    def __init__(self):
        self.name = ''
        self.urls_id = []
        self.last_stopped = 0

class AggregateResult:
    def __init__(self, find_string_groups: List[str]) -> None:
        self.id_count = 0
        self.prime_group_count = len(find_string_groups)
        self.find_group = [None]*(2**self.prime_group_count)

        self.init_coll_group(find_string_groups)
    
    def init_coll_group(self, find_string_groups: List[str]) -> None:
        aggregate_group_count = len(self.find_group)

        for i in range(1, aggregate_group_count):
            agg_group = AggregateGroup()

            find_string_groups_id = get_set_bit(i, self.prime_group_count)
            for num, id in enumerate(find_string_groups_id):
                group_separator = ''
                if num > 0:
                    group_separator = ', '

                group = find_string_groups[id]
                agg_group.name += (group_separator + group)

            self.find_group[i] = agg_group

    def put(self, task_data: WorkerTaskResult) -> None:
        link_id, task_results = task_data

        group_id = 0
        for result in task_results:
            group_id |= 1 << result[0]

        if group_id != 0:
            group = self.find_group[group_id]
            if group:
                group.urls_id.append(link_id)
                self.id_count += 1
    
    def sort_group_index(self) -> None:
        new_group = [group for group in self.find_group if group != None]
        self.find_group = new_group

        for group in self.find_group:
            group.urls_id.sort()