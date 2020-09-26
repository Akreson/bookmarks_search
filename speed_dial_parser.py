from file_urls_parser import *

#TODO: Handle error!!
#TODO: throw error

def get_max_group_id(groups_dict):
    max_group_id = 0

    if len(groups_dict) > 0:
        for (_, value) in groups_dict.items():
            id = value['id']
            if max_group_id < id:
                max_group_id = id
    
    return max_group_id

def get_sd_url_groups(json_data):
    groups_dict = json_data['groups']
    max_group_id = get_max_group_id(groups_dict)

    group_list = [None]*(max_group_id + 1)
    for _, value in groups_dict.items():
        id = value['id']
        group_list[id] = FileUrlGroup(value['title'])

    return group_list

def fill_groups_urls(url_groups, json_data):
    urls_dict = json_data['dials']

    for (_, value) in urls_dict.items():
        group_id = value['idgroup']
        group = url_groups[group_id]
        if group != None:
            group.urls.append(value['url']) 


def sd_parse_json(json_data):
    sd_groups = get_sd_url_groups(json_data)
    fill_groups_urls(sd_groups, json_data)
    
    result_list = [group for group in sd_groups if group != None]
    return result_list