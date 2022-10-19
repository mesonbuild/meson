import argparse
import sys
from . import coredata, mparser
from . import mesonlib
from .ast import AstFormatter

def add_arguments(parser: argparse.ArgumentParser) -> None:
    coredata.register_builtin_arguments(parser)
    parser.add_argument('files', nargs=argparse.REMAINDER,
                        help='files to format')

def run(options: argparse.Namespace) -> int:
    for filename in options.files:
        with open(filename, encoding='utf-8') as f:
            code = f.read()
        assert isinstance(code, str)
        try:
            parser = mparser.Parser(code, filename)
            codeblock = parser.parse()
            comments = parser.comments()
        except mesonlib.MesonException as me:
            me.file = filename
            raise me
        formatter = AstFormatter(comments, code.splitlines())
        codeblock.accept(formatter)
        formatter.end()
        print('This will probably eat some of your comments', file=sys.stderr)
        for line in formatter.lines:
            print(line, end='\n')
        print('Unable to readd', len(formatter.comments), 'comments', file=sys.stderr)
        for c in formatter.comments:
            print(c.text, file=sys.stderr)
