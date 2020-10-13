import os
import sys
import json

JSON_EXT = '.json'
HTML_EXT = '.html'

class FileUrlGroup:
    def __init__(self, name):
        self.name = name
        self.urls = []
        self.urls_title = []

from browser_bm_parser import browser_bm_parse_html
from speed_dial_parser import sd_parse_json

class UrlGroup:
    def __init__(self, name, min = 0, max = 0):
        self.min = min
        self.max = max
        self.name = name

class SearchData:
    def __init__(self, files, get_group, exclude_groups):
        self.urls = []
        self.urls_title = []
        self.url_group = []
        self.exclude_group = exclude_groups
        self.get_group = get_group

        self.parse_files(files)

    def group_name_match(self, name, group_list):
        name_len = len(name)
        
        for group_name in group_list:
            group = group_name.split('.')
            group_len = len(group)

            if name_len == 1:
                if name[0] in group:
                    return True
            elif group_len == 1:
                if group[0] in name:
                    return True
            elif name_len >= group_len:
                valid = True
                for i in range(group_len):
                    if name[i] != group[i]:
                        valid = False
                        break
                
                return valid

    def is_valid_group(self, group_name):
        name = group_name.split('.')

        if (self.get_group is not None) and len(self.get_group):
            return self.group_name_match(name, self.get_group)
        elif (self.exclude_group is not None) and len(self.exclude_group):
            return not self.group_name_match(name, self.exclude_group)

        return True
    
    def check_group_presence(self, test_groups):
        if (self.get_group is not None) and len(self.get_group):
            check_pass = False
            for group in test_groups:
                if group.name in self.get_group:
                    check_pass = True
                    break
            
            return check_pass
        else:
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

        if not self.check_group_presence(test_groups):
            print("Don't have this link group(s) {}".format(self.get_group))
            sys.exit()
                
        for test in test_groups:
            present = False
           
            for group in files_groups:
                if test.name == group.name:
                    present = True
                    group.urls += test.urls
                    group.urls_title += test.urls_title
            
            if not present and self.is_valid_group(test.name):
                files_groups.append(test)

    def pack_to_search_data(self, files_link_groups):
        for group in files_link_groups:
            curr_len = len(self.urls)
            group_min = curr_len
            group_max = group_min + len(group.urls)
            url_group = UrlGroup(group.name, group_min, group_max)
            self.url_group.append(url_group)
            self.urls += group.urls
            self.urls_title += group.urls_title

    def parse_files_urls(self, files_to_parse):
        files_groups = []

        for file in files_to_parse:
            with open(file, encoding='utf-8') as f:
                file_ext = os.path.splitext(file)[1]
                get_file_groups = self.get_file_group_url_info(f, file_ext)
                self.collate_files_urls(files_groups, get_file_groups)

        self.pack_to_search_data(files_groups)

    def parse_files(self, files):
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