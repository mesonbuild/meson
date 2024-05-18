#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2014 Jussi Pakkanen

import typing as T
from pathlib import Path
import sys
import re
import argparse
import logging


class Token:
    def __init__(self, tid: str, value: str):
        self.tid = tid
        self.value = value
        self.lineno = 0
        self.colno = 0


class Statement:
    def __init__(self, name: str, args: list):
        self.name = name.lower()
        self.args = args


class Lexer:
    def __init__(self) -> None:
        self.token_specification = [
            ('ignore', re.compile(r'[ \t]')),
            ('string', re.compile(r'"([^\\]|(\\.))*?"', re.M)),
            ('varexp', re.compile(r'\${[-_0-9a-z/A-Z.]+}')),
            ('id', re.compile(r'''[,-><${}=+_0-9a-z/A-Z|@.*]+''')),
            ('eol', re.compile(r'\n')),
            ('comment', re.compile(r'#.*')),
            ('lparen', re.compile(r'\(')),
            ('rparen', re.compile(r'\)')),
        ]

    def lex(self, code: str) -> T.Iterator[Token]:
        lineno = 1
        line_start = 0
        loc = 0
        col = 0
        while loc < len(code):
            matched = False
            for (tid, reg) in self.token_specification:
                mo = reg.match(code, loc)
                if mo:
                    col = mo.start() - line_start
                    matched = True
                    loc = mo.end()
                    match_text = mo.group()
                    if tid == 'ignore':
                        continue
                    if tid == 'comment':
                        yield Token('comment', match_text)
                    elif tid == 'lparen':
                        yield Token('lparen', '(')
                    elif tid == 'rparen':
                        yield Token('rparen', ')')
                    elif tid == 'string':
                        yield Token('string', match_text[1:-1])
                    elif tid == 'id':
                        yield Token('id', match_text)
                    elif tid == 'eol':
                        lineno += 1
                        col = 1
                        line_start = mo.end()
                    elif tid == 'varexp':
                        yield Token('varexp', match_text[2:-1])
                    else:
                        raise ValueError(f'lex: unknown element {tid}')
                    break
            if not matched:
                raise ValueError('Lexer got confused line %d column %d' % (lineno, col))


class Parser:
    def __init__(self, code: str) -> None:
        self.stream = Lexer().lex(code)
        self.getsym()

    def getsym(self) -> None:
        try:
            self.current = next(self.stream)
        except StopIteration:
            self.current = Token('eof', '')

    def accept(self, s: str) -> bool:
        if self.current.tid == s:
            self.getsym()
            return True
        return False

    def expect(self, s: str) -> bool:
        if self.accept(s):
            return True
        raise ValueError(f'Expecting {s} got {self.current.tid}.', self.current.lineno, self.current.colno)

    def statement(self) -> Statement:
        cur = self.current
        if self.accept('comment'):
            return Statement('_', [cur.value])
        self.accept('id')
        self.expect('lparen')
        args = self.arguments()
        self.expect('rparen')
        return Statement(cur.value, args)

    def arguments(self) -> T.List[T.Union[Token, T.Any]]:
        args: T.List[T.Union[Token, T.Any]] = []
        if self.accept('lparen'):
            args.append(self.arguments())
            self.expect('rparen')
        arg = self.current
        if self.accept('comment'):
            rest = self.arguments()
            args += rest
        elif self.accept('string') \
                or self.accept('varexp') \
                or self.accept('id'):
            args.append(arg)
            rest = self.arguments()
            args += rest
        return args

    def parse(self) -> T.Iterator[Statement]:
        while not self.accept('eof'):
            yield self.statement()


def token_or_group(arg: T.Union[Token, T.List[Token]]) -> str:
    if isinstance(arg, Token):
        return ' ' + arg.value
    elif isinstance(arg, list):
        line = ' ('
        for a in arg:
            line += ' ' + token_or_group(a)
        line += ' )'
        return line
    raise RuntimeError('Conversion error in token_or_group')


class Converter:
    ignored_funcs = {'cmake_minimum_required': True,
                     'enable_testing': True,
                     'include': True}

    def __init__(self, cmake_root: str):
        self.cmake_root = Path(cmake_root).expanduser()
        self.indent_unit = '  '
        self.indent_level = 0
        self.options: T.List[T.Tuple[str, str, T.Optional[str]]] = []
        logging.basicConfig(filename='cmake_to_meson.log', level=logging.DEBUG,
                            format='%(asctime)s %(levelname)s: %(message)s')

    def convert_args(self, args: T.List[Token], as_array: bool = True) -> str:
        res = []
        if as_array:
            start = '['
            end = ']'
        else:
            start = ''
            end = ''
        for i in args:
            if i.tid == 'id':
                res.append("'%s'" % i.value)
            elif i.tid == 'varexp':
                res.append('%s' % i.value.lower())
            elif i.tid == 'string':
                res.append("'%s'" % i.value)
            else:
                raise ValueError(f'Unknown arg type {i.tid}')
        if len(res) > 1:
            return start + ', '.join(res) + end
        if len(res) == 1:
            return res[0]
        return ''

    def write_entry(self, outfile: T.TextIO, t: Statement) -> None:
        if t.name in Converter.ignored_funcs:
            return
        preincrement = 0
        postincrement = 0
        try:
            line = self.convert_statement(t)
        except Exception as e:
            line = f'# Error converting {t.name}: {e}'
            logging.error(f'Error converting {t.name}: {e}')
        
        self.indent_level += preincrement
        indent = self.indent_level * self.indent_unit
        outfile.write(indent)
        outfile.write(line)
        if not line.endswith('\n'):
            outfile.write('\n')
        self.indent_level += postincrement

    def convert_statement(self, t: Statement) -> str:
        try:
            if t.name == '_':
                return t.args[0]
            elif t.name == 'add_subdirectory':
                return "subdir('{}')".format(t.args[0].value)
            elif t.name in {'pkg_search_module', 'pkg_search_modules'}:
                varname = t.args[0].value.lower()
                mods = ["dependency('{}')".format(i.value) for i in t.args[1:]]
                if len(mods) == 1:
                    return '{} = {}'.format(varname, mods[0])
                else:
                    return '{} = [{}]'.format(varname, ', '.join(mods))
            elif t.name == 'find_package':
                return "{}_dep = dependency('{}')".format(t.args[0].value, t.args[0].value)
            elif t.name == 'find_library':
                return "{} = find_library('{}')".format(t.args[0].value.lower(), t.args[0].value)
            elif t.name == 'add_executable':
                return '{}_exe = executable({})'.format(t.args[0].value, self.convert_args(t.args[1:], False))
            elif t.name == 'add_library':
                return self.convert_add_library(t)
            elif t.name == 'add_test':
                return 'test({})'.format(self.convert_args(t.args, False))
            elif t.name == 'option':
                self.add_option(t)
                return ''
            elif t.name == 'project':
                return self.convert_project(t)
            elif t.name == 'set':
                varname = t.args[0].value.lower()
                return '{} = {}'.format(varname, self.convert_args(t.args[1:]))
            elif t.name == 'if':
                return self.convert_if(t)
            elif t.name == 'elseif':
                return self.convert_elseif(t)
            elif t.name == 'endif':
                return 'endif'
            elif t.name == 'else':
                return 'else'
            else:
                raise ValueError('Unknown CMake command ' + t.name)
        except Exception as e:
            logging.error(f"Failed to convert statement '{t.name}': {e}")
            raise

    def convert_add_library(self, t: Statement) -> str:
        libcmd = 'static_library'
        sharedarg = [x for x in t.args if x.value == 'SHARED']
        if sharedarg:
            libcmd = 'shared_library'
        args = [t.args[0]] + t.args[2:]
        return '{}_lib = {}({})'.format(t.args[0].value, libcmd, self.convert_args(args, False))

    def add_option(self, t: Statement) -> None:
        optname = t.args[0].value
        description = t.args[1].value
        default = t.args[2].value if len(t.args) > 2 else None
        self.options.append((optname, description, default))

    def convert_project(self, t: Statement) -> str:
        pname = t.args[0].value
        args = [pname]
        for l in t.args[1:]:
            l = l.value.lower()
            if l == 'cxx':
                l = 'cpp'
            args.append(l)
        args = ["'{}'".format(i) for i in args]
        return 'project({}, default_options : [\'default_library=static\'])'.format(', '.join(args))

    def convert_if(self, t: Statement) -> str:
        return 'if {}'.format(self.convert_args(t.args, False))

    def convert_elseif(self, t: Statement) -> str:
        return 'elif {}'.format(self.convert_args(t.args, False))

    def convert(self, subdir: Path = None) -> None:
        if not subdir:
            subdir = self.cmake_root
        cfile = Path(subdir).expanduser() / 'CMakeLists.txt'
        try:
            with cfile.open(encoding='utf-8') as f:
                cmakecode = f.read()
        except FileNotFoundError:
            logging.warning('No CMakeLists.txt in %s', subdir)
            return
        p = Parser(cmakecode)
        with (subdir / 'meson.build').open('w', encoding='utf-8') as outfile:
            for t in p.parse():
                if t.name == 'add_subdirectory':
                    self.convert(subdir / t.args[0].value)
                self.write_entry(outfile, t)
        if subdir == self.cmake_root and self.options:
            self.write_options()

    def write_options(self) -> None:
        filename = self.cmake_root / 'meson_options.txt'
        with filename.open('w', encoding='utf-8') as optfile:
            for optname, description, default in self.options:
                typestr = ' type : \'boolean\',' if default in {'ON', 'OFF'} else ' type : \'string\','
                defaultstr = ' value : {},'.format('true' if default == 'ON' else 'false' if default == 'OFF' else default) if default else ''
                line = "option({!r},{}{} description : '{}')\n".format(optname, typestr, defaultstr, description)
                optfile.write(line)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Convert CMakeLists.txt to meson.build and meson_options.txt')
    p.add_argument('cmake_root', help='CMake project root (where top-level CMakeLists.txt is)')
    args = p.parse_args()

    Converter(args.cmake_root).convert()
