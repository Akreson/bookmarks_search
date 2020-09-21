import os
import sys
import json
import argparse
import urllib.request
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
    def __init__(self):
        self.urls = []
        self.url_group = []
        self.exclude_group = []

    def get_file_group_url_info(self, file_desc, file_ext):
        if file_ext == HTML_EXT:
            file_data = file_desc.read()
            file_urls_group = browser_bm_parse_html(self.exclude_group, self.url_group, self.urls, file_data)
        elif file_ext == JSON_EXT:
            file_data = json.load(file_desc)
            file_urls_group = sd_parse_json(self.exclude_group, self.url_group, self.urls, file_data)

        return file_urls_group
    
    def collate_files_urls(self, files_groups, test_groups):
        for test in test_groups:
            present = False
           
            for group in files_groups:
                if test.name == group.name:
                    present = True
                    group.urls += test.urls
            
            if not present:
                files_groups.append(test)

    def pack_to_search_data(self, files_groups):
        for group in files_groups:
            if group.name not in self.exclude_group:
                curr_len = len(self.urls)
                group_min = curr_len
                group_max = group_min + len(group.urls)
                url_group = UrlGroup(group.name, group_min, group_max)
                self.url_group.append(url_group)
                self.urls += group.urls
##TODO Finish

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
    search_data = SearchData()
    cli_args = parse_cmd_args()

    search_data.parse_files(cli_args.file, cli_args.exclude)

    print(cli_args)

if __name__ == "__main__":
    main()