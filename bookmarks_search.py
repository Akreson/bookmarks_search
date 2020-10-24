import time
import sys
import argparse
from lib.data_parser import SearchData
from lib.processing import DataProcess

def uint_check(value):
    int_value = int(value)
    if int_value < 0:
        raise argparse.ArgumentTypeError("%s is an invalid positive int value" % value)
    return int_value
        
def parse_cmd_args() -> argparse.Namespace:
    cli_parser = argparse.ArgumentParser()
    cli_parser.add_argument('-f', '--file', action='store', nargs='+', required=True,
        help='''set file for parse (must be saved file from browser bookmarks .html file
            or from browser ext. SpeedDeal .json)''')
    cli_parser.add_argument('-s', '--string', action='store', nargs='+',
        help='string for search in url links')
    cli_parser.add_argument('-g', '--group', action='store', nargs='+',
        help='group of bookmarks in provided file')
    cli_parser.add_argument('-ex', '--exclude', action='store', nargs='+',
        help='exclude group from search')
    cli_parser.add_argument('-title', action='store_true',
        help='string will be searching in bookmarks title')
    cli_parser.add_argument('-url', action='store_true',
        help='string will be searching in url')
    cli_parser.add_argument('-gg', '--get-group', action='store',  nargs='*', default=[],
        help='get indicated group')
    cli_parser.add_argument('--max-worker', action='store', nargs='?', type=uint_check, default=4,
        help='max. workers that will be process downloaded page, default max. value 4')
    cli_parser.add_argument('--max-queue', action='store', nargs='?', type=uint_check, default=200,
        help="max. length of processing links asynchronous, default max. value 200, don't used with -title flag")
    cli_parser.add_argument('--max-wait', action='store', nargs='?', type=uint_check, default=0,
        help="max. wait time for http request")

    cli_args = cli_parser.parse_args()
    return cli_args


def main():
    start_time = time.time()

    cli_args = parse_cmd_args()
    search_data = SearchData(cli_args.file, cli_args.group, cli_args.exclude)
    data_process = DataProcess(search_data, cli_args.string, cli_args.max_worker, cli_args.max_queue, cli_args.max_wait)
    data_process.run(cli_args.title, cli_args.url, cli_args.get_group)
    
    print(time.time() - start_time)

if __name__ == "__main__":
    main()