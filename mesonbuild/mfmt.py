import argparse
import sys
from . import coredata, mparser
from . import mesonlib
from .ast import AstFormatter

def add_arguments(parser: argparse.ArgumentParser) -> None:
    coredata.register_builtin_arguments(parser)
    parser.add_argument('file', help='file to format')
    parser.add_argument('-o', '--output', help='Output file')
    parser.add_argument('-i', '--inplace', action='store_true', help='Edit the file inplace')

def run(options: argparse.Namespace) -> int:
    if options.file == '-':
        code = sys.stdin.read()
    else:
        with open(options.file, encoding='utf-8') as f:
            code = f.read()
    assert isinstance(code, str)
    try:
        parser = mparser.Parser(code, options.file)
        codeblock = parser.parse()
        comments = parser.comments()
    except mesonlib.MesonException as me:
        me.file = options.file
        raise me
    formatter = AstFormatter(comments, code.splitlines())
    codeblock.accept(formatter)
    formatter.end()
    print('This will probably eat some of your comments', file=sys.stderr)
    if not options.inplace:
        output = sys.stdout if options.output is None else open(options.output, 'w', encoding='utf8')
    else:
        output = open(options.file, 'w', encoding='utf8')
    for line in formatter.lines:
        print(line, end='\n', file=output)
    if len(formatter.comments) != 0:
        print('Unable to readd', len(formatter.comments), 'comments', file=sys.stderr)
        for c in formatter.comments:
            print(c.text, file=sys.stderr)
