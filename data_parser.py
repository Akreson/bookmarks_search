import os
import sys
import json
from browser_bm_parser import *
from speed_dial_parser import *

JSON_EXT = '.json'
HTML_EXT = '.html'

class UrlGroup:
    def __init__(self, name, min = 0, max = 0):
        self.min = min
        self.max = max
        self.name = name

class SearchData:
    def __init__(self, files, exclude_groups):
        self.urls = []
        self.url_group = []
        self.exclude_group = []
        
        self.parse_files(files, exclude_groups)

    def is_valid_group(self, group_name):
        name = group_name.split('.')
        name_len = len(name)

        if len(self.exclude_group): 
            for exclude_name in self.exclude_group:
                exclude = exclude_name.split('.')
                exclude_len = len(exclude)

                if name_len == 1:
                    if name[0] in exclude:
                        return False
                elif name_len >= exclude_len:
                    valid = True
                    for i in range(exclude_len):
                        if name[i] == exclude[i]:
                            valid = False
                            break
                    
                    return valid

        return True

    def get_file_group_url_info(self, file_desc, file_ext):
        if file_ext == HTML_EXT:
            file_data = file_desc.read()
            file_urls_group = browser_bm_parse_html(file_data)
        elif file_ext == JSON_EXT:
            file_data = json.load(file_desc)
            file_urls_group = sd_parse_json(file_data)

        return file_urls_group
    
    def collate_files_urls(self, files_groups, test_groups):
        for test in test_groups:
            present = False
           
            for group in files_groups:
                if test.name == group.name:
                    present = True
                    group.urls += test.urls
            
            if not present and self.is_valid_group(test.name):
                files_groups.append(test)

    def pack_to_search_data(self, files_groups):
        for group in files_groups:
            curr_len = len(self.urls)
            group_min = curr_len
            group_max = group_min + len(group.urls)
            url_group = UrlGroup(group.name, group_min, group_max)
            self.url_group.append(url_group)
            self.urls += group.urls

    def parse_files_urls(self, files_to_parse):
        files_groups = []

        for file in files_to_parse:
            with open(file, encoding='utf-8') as f:
                file_ext = os.path.splitext(file)[1]
                get_file_groups = self.get_file_group_url_info(f, file_ext)
                self.collate_files_urls(files_groups, get_file_groups)

        self.pack_to_search_data(files_groups)

    def parse_files(self, files, exclude_groups):
        if exclude_groups:
            self.exclude_group = list(exclude_groups)
            
        files_to_parse = []

        for file in files:
            if os.path.exists(file):
                extension = os.path.splitext(file)[1]
                if extension == JSON_EXT or extension == HTML_EXT:
                    files_to_parse.append(file)
                else:
                    print('{} has unsupported file format'.format(file))
            else:
                print('{} not exist'.format(file))
        
        if len(files_to_parse) != 0:
            self.parse_files_urls(files_to_parse)
        else:
            sys.exit()