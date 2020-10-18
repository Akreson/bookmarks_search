from data_parser import FileUrlGroup
from typing import (
    Set,
    List,
    Dict,
    Tuple,
    Optional,

    TypeVar
)

JSONVar = TypeVar("JsonVar", str, int, float)

#TODO: Handle error!!
#TODO: throw error

def get_max_group_id(groups_dict: Dict[JSONVar, JSONVar]) -> int:
    max_group_id = 0

    if len(groups_dict) > 0:
        for (_, value) in groups_dict.items():
            id = value['id']
            if max_group_id < id:
                max_group_id = id
    
    return max_group_id

def get_sd_url_groups(json_data: str) -> List[FileUrlGroup]:
    groups_dict = json_data['groups']
    max_group_id = get_max_group_id(groups_dict)

    group_list = [None]*(max_group_id + 1)
    for _, value in groups_dict.items():
        id = value['id']
        group_list[id] = FileUrlGroup(value['title'])

    return group_list

def fill_groups_urls(
    url_groups: List[FileUrlGroup], json_data: Dict[JSONVar, JSONVar]
) -> None:
    urls_dict = json_data['dials']

    for (_, value) in urls_dict.items():
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