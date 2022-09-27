import argparse
from . import coredata, mlog

def add_arguments(parser: argparse.ArgumentParser) -> None:
    coredata.register_builtin_arguments(parser)
    parser.add_argument('FILE', nargs=argparse.REMAINDER,
                        help='files to format')

def run(options: argparse.Namespace) -> int:
    pass
