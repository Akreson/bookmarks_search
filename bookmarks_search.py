import os
import sys
import argparse
import urllib.request
from data_parser import *

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
    cli_args = parse_cmd_args()
    search_data = SearchData(cli_args.file, cli_args.exclude)

    for group in search_data.url_group:
        print(group.name)

    print(cli_args)

if __name__ == "__main__":
    main()