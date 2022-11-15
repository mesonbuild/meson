import argparse
import os
import sys
from . import coredata, mparser
from . import mesonlib
from .ast import AstFormatter
from pathlib import Path

def add_arguments(parser: argparse.ArgumentParser) -> None:
    coredata.register_builtin_arguments(parser)
    parser.add_argument('file', help='file to format')
    parser.add_argument('-o', '--output', help='Output file')
    parser.add_argument('-i', '--inplace', action='store_true', help='Edit the file inplace')
    parser.add_argument('-c', '--config', help='Specify config file')
    parser.add_argument('-R', '--recurse', action='store_true', help='Recursively format meson files in a given directory')
    parser.add_argument('-q', '--quiet', action='store_true', help='Don\'t print comments that couldn\'t be readded')
    parser.add_argument('-v', '--verbose', action='store_true', help='Don\'t print comments that couldn\'t be readded')

def parse_fmt_config(file: str):
    config = {}
    config['max_line_len'] = 80
    config['indent_by'] = '    '
    config['space_array'] = False
    config['kwa_ml'] = False
    config['wide_colon'] = False
    config['no_single_comma_function'] = False
    if file is not None:
        with open(file, encoding='utf-8') as f:
            for line in f.readlines():
                ls = line.lstrip()
                if ls == '' or ls[0] == '#':
                    continue
                if '=' not in ls:
                    continue
                parts = ls.split('=', 1)
                key = parts[0].strip()
                value = parts[1].lower()
                if key == 'max_line_len':
                    config['max_line_len'] = int(value)
                elif key in ('space_array', 'kwa_ml', 'wide_colon', 'no_single_comma_function'):
                    if value.strip() in ('false', 'true'):
                        config[key] = value.strip().lower() == 'true'
                    else:
                        print('Unexpected value for key', key, file=sys.stderr)
                elif key == 'indent_by':
                    config['indent_by'] = value.replace('\n', '')
                else:
                    print("Unknown key", key, file=sys.stderr)
    return config

def format_code(options: argparse.Namespace, file: str, output: str, code: str) -> int:
    try:
        parser = mparser.Parser(code, file)
        codeblock = parser.parse()
        comments = parser.comments()
    except mesonlib.MesonException as me:
        me.file = file
        raise me
    if options.verbose:
        n_comments = len(comments)
        print("Found", n_comments, "comments in file", file=sys.stderr)
    config = parse_fmt_config(options.config)
    formatter = AstFormatter(comments, code.splitlines(), config)
    codeblock.accept(formatter)
    formatter.end()
    if not options.inplace:
        real_output = sys.stdout if output is None else open(output, 'w', encoding='utf8')
    else:
        real_output = open(file, 'w', encoding='utf8')
    for line in formatter.lines:
        print(line, end='\n', file=real_output)
    if len(formatter.comments) != 0 and not options.quiet:
        print('Unable to readd', len(formatter.comments), 'comments', file=sys.stderr)
        for c in formatter.comments:
            print(c.text, file=sys.stderr)
    return 0

def run(options: argparse.Namespace) -> int:
    if options.file == '-':
        code = sys.stdin.read()
        return format_code(options, '-', options.output, code)
    else:
        if os.path.isdir(options.file):
            if not options.recurse:
                print('A directory was passed, but no -R/--recurse was specified', file=sys.stderr)
                return -1
            else:
                # Always do inplace editing
                options.inplace = True
                for path in Path(options.file).rglob('meson.build'):
                    full_path = str(path)
                    with open(full_path, encoding='utf-8') as f:
                        code = f.read()
                    format_code(options, full_path, full_path, code)
                return 0
        else:
            with open(options.file, encoding='utf-8') as f:
                code = f.read()
                return format_code(options, options.file, options.output, code)
