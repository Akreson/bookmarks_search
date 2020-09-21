from urllib import parse
from html.parser import HTMLParser
from file_urls_parser import *

class Tag:
    DT = 'dt'
    DL = 'dl'
    H3 = 'h3'
    H1 = 'h1'
    A = 'a'
    P = 'p'

class ParseState:
    Empty = 0 
    GroupData = 1
    GroupData_Name = 2
    GroupData_Links = 3

    ExitGroup_Name = 4
    EnterGroupData = 5
    ExitGroupData = 6

    SubgroupData = 7
    SubgroupData_Name = 8

    InitGroup = 9
    InitSubGroup = 10

    DataLink = 11

class BookmarksParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.file_url_groups = []
        self.curr_group = None
        self.state = ParseState.Empty

        self.prev_open_tag = None
        self.prev_end_tag = None

        self.open_tag = None
        self.end_tag = None

        self.expected_tag = None
        self.curr_tag_data = None
        self.curr_subgroup_name = ''
    
    def handle_endtag(self, tag):
        if self.end_tag:
            self.prev_end_tag = self.end_tag
            self.end_tag = tag
        else:
            self.end_tag = tag

#TODO: Finish parsing
        if tag == Tag.H3:
            if self.state == ParseState.GroupData_Name:
                self.curr_group = FileUrlGroup(self.curr_subgroup_name + self.curr_tag_data)
                print(self.curr_group.name)
            elif self.state == ParseState.InitSubGroup:
                self.curr_subgroup_name = self.curr_group.name + '.'
                self.state = ParseState.GroupData_Name
        elif tag == Tag.A and self.state == ParseState.DataLink:
            pass
        elif tag == Tag.DL and self.state == ParseState.DataLink:
            self.file_url_groups.append(self.curr_group)
            self.curr_subgroup_name = ''
            self.state = ParseState.InitGroup

    def handle_starttag(self, tag, attrs):
        if self.open_tag:
            self.prev_open_tag = self.open_tag
            self.open_tag = tag
        else:
            self.open_tag = tag

        if tag == Tag.DT:
            if self.state == ParseState.InitGroup:
                self.state = ParseState.GroupData
        elif tag == Tag.H3:
            if self.state == ParseState.GroupData: 
                self.state = ParseState.GroupData_Name
            elif self.state == ParseState.GroupData_Links and self.prev_open_tag == Tag.DT:
                self.state == ParseState.InitSubGroup
        elif tag == Tag.DL:
            if self.end_tag == Tag.H1:
                self.state = ParseState.InitGroup
            if self.state == ParseState.GroupData_Name:
                self.state = ParseState.GroupData_Links
            else:
                self.state = ParseState.Empty
        elif tag == Tag.A and self.prev_open_tag == Tag.DT:
            self.state = ParseState.DataLink
        
    def handle_data(self, data):
       self.curr_tag_data = data

def browser_bm_parse_html(exlcude_group, url_group, urls, html_data):
    bm_parser = BookmarksParser()
    bm_parser.feed(html_data)
    print(len(bm_parser.file_url_groups))

    return bm_parser.file_url_groups

