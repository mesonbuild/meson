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
    parser.add_argument('-c', '--config', help='Specify config file')

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
    config = {}
    config['max_line_len'] = 80
    config['indent_by'] = '    '
    config['space_array'] = False
    config['kwa_ml'] = False
    config['wide_colon'] = False
    config['no_single_comma_function'] = False
    if options.config is not None:
        with open(options.config, encoding='utf-8') as f:
            for line in f.readlines():
                ls = line.stripped()
                if ls == '' or ls[0] == '#':
                    continue
                if '=' not in ls:
                    continue
                parts = ls.split('=', 1)
                key = parts[0]
                value = parts[1].lower()
                if key == 'max_line_len':
                    config['max_line_len'] = int(value)
                elif key in ('space_array', 'kwa_ml', 'wide_colon', 'no_single_comma_function'):
                    if value in ('false', 'true'):
                        config[key] = value.lower() == 'true'
                    else:
                        print('Unexpected value for key', key, file=sys.stderr)
                else:
                    print("Unknown key", key, file=sys.stderr)

    formatter = AstFormatter(comments, code.splitlines(), config)
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
