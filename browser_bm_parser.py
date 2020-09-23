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

    InitGroup = 4
    InitSubGroup = 5

    DataLink = 6

class BookmarksParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.file_url_groups = []
        self.state = ParseState.Empty
        self.default_name = 'Default'
        self.curr_group = FileUrlGroup(self.default_name)

        self.prev_open_tag = None
        self.prev_end_tag = None

        self.open_tag = None
        self.end_tag = None

        self.expected_tag = None
        self.curr_tag_data = None
        self.curr_subgroup_name = ''

    def inti_curr_group(self):
        self.curr_group = FileUrlGroup(self.default_name)
    
    def set_end_tag(self, tag):
        if self.end_tag:
            self.prev_end_tag = self.end_tag
            self.end_tag = tag
        else:
            self.end_tag = tag

    def set_open_tag(self, tag):
        if self.open_tag:
            self.prev_open_tag = self.open_tag
            self.open_tag = tag
        else:
            self.open_tag = tag
    
    def get_curr_group_name(self):
        return self.curr_subgroup_name + self.curr_tag_data
    
    def handle_endtag(self, tag):
        self.set_end_tag(tag)

        if tag == Tag.H3:
            if self.state == ParseState.GroupData_Name:
                self.curr_group.name = self.get_curr_group_name()
                #print('{0} {1}'.format(self.curr_group.name, self.state))
            elif self.state == ParseState.InitSubGroup:
                self.state = ParseState.GroupData_Links
                self.curr_subgroup_name = self.curr_group.name + '.'

                if len(self.curr_group.urls):
                    self.file_url_groups.append(self.curr_group)
                    self.curr_group = FileUrlGroup(self.get_curr_group_name())
                else:
                    self.curr_group.name = self.get_curr_group_name()
                #print('--Set SUB_group NAME {0} {1}'.format(self.curr_subgroup_name, self.curr_group.name))
        elif tag == Tag.DL:
            if self.state == ParseState.DataLink:
                self.file_url_groups.append(self.curr_group)
                self.state = ParseState.InitGroup
                self.curr_group = FileUrlGroup(self.default_name)
                #print('--EXIT group {}'.format(self.state))
            elif self.state == ParseState.GroupData_Links:
                self.state = ParseState.InitGroup
                self.curr_group = FileUrlGroup(self.default_name)
            elif self.state == ParseState.InitGroup:
                self.curr_subgroup_name = ''

    def handle_starttag(self, tag, attrs):
        self.set_open_tag(tag)

        if tag == Tag.DT:
            if self.state == ParseState.InitGroup or self.state == ParseState.Empty:
                self.state = ParseState.GroupData
                #print('--Enter group DATA {0} {1}'.format(tag, self.state))
        elif tag == Tag.H3:
            if self.state == ParseState.GroupData: 
                self.state = ParseState.GroupData_Name
                #print('--Set group NAME {0} {1}'.format(tag, self.state))
            elif self.state == ParseState.GroupData_Links or self.state == ParseState.DataLink:
                self.state = ParseState.InitSubGroup
                #print('--Enter SUB_group NAME {0} {1}'.format(tag, self.state))
        elif tag == Tag.DL:
            if self.state == ParseState.GroupData_Name:
                self.state = ParseState.GroupData_Links
        elif tag == Tag.A and self.prev_open_tag == Tag.DT:
            self.state = ParseState.DataLink

            for (attribute, value) in attrs:
                if attribute == 'href':
                    self.curr_group.urls.append(value)
        
    def handle_data(self, data):
       self.curr_tag_data = data

def browser_bm_parse_html(html_data):
    bm_parser = BookmarksParser()
    bm_parser.feed(html_data)

    return bm_parser.file_url_groups

