from .data_parser import FileUrlGroup
from typing import List, Dict
from .custom_types import JSONVar

#TODO: Handle error!!
#TODO: throw error

def get_max_group_id(groups_dict: Dict[JSONVar, JSONVar]) -> int:
    max_group_id = 0

    if len(groups_dict) > 0:
        for value in groups_dict:
            id = value['id']
            if max_group_id < id:
                max_group_id = id
    
    return max_group_id

def get_sd_url_groups(json_data: str) -> List[FileUrlGroup]:
    groups_dict = json_data['groups']
    max_group_id = get_max_group_id(groups_dict)

    group_list = [None]*(max_group_id + 1)
    for value in groups_dict:
        id = value['id']
        group_list[id] = FileUrlGroup(value['title'])

    return group_list

def fill_groups_urls(
    url_groups: List[FileUrlGroup], json_data: Dict[JSONVar, JSONVar]
) -> None:
    urls_dict = json_data['dials']

    for value in urls_dict:
        group_id = value['idgroup']
        group = url_groups[group_id]
        if group:
            group.urls.append(value['url'])
            group.urls_title.append(value['title'])

def sd_parse_json(json_data: Dict[JSONVar, JSONVar]) -> List[FileUrlGroup]:
    sd_groups = get_sd_url_groups(json_data)
    fill_groups_urls(sd_groups, json_data)
    
    result_list = [group for group in sd_groups if group != None]
    return result_list