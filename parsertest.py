#!/usr/bin/python3

# Copyright 2014 Jussi Pakkanen

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
import sys

class ParseException(Exception):
    def __init__(self, text, lineno, colno):
        super().__init__()
        self.text = text
        self.lineno = lineno
        self.colno = colno

class Token:
    def __init__(self, tid, lineno, colno):
        self.tid = tid
        self.lineno = lineno
        self.colno = colno
    
    def __eq__(self, other):
        if isinstance(other, str):
            return self.tid == other
        return self.tid == other.tid

class Lexer:
    def __init__(self):
        self.keywords = {'true', 'false', 'if', 'else', 'elif',
                         'endif', 'and', 'or', 'not'}
        self.token_specification = [
            # Need to be sorted longest to shortest.
            ('ignore', re.compile(r'[ \t]')),
            ('id', re.compile('[_a-zA-Z][_0-9a-zA-Z]*')),
            ('number', re.compile(r'\d+')),
            ('eol_cont', re.compile(r'\\\n')),
            ('eol', re.compile(r'\n')),
            ('multiline_string', re.compile(r"'''(.|\n)*?'''", re.M)),
            ('comment', re.compile(r'\#.*')),
            ('lparen', re.compile(r'\(')),
            ('rparen', re.compile(r'\)')),
            ('lbracket', re.compile(r'\[')),
            ('lbracket', re.compile(r'\]')),
            ('string', re.compile("'[^']*?'")),
            ('comma', re.compile(r',')),
            ('dot', re.compile(r'\.')),
            ('semicolon', re.compile(r':')),
            ('assign', re.compile(r'==')),
            ('equal', re.compile(r'=')),
            ('nequals', re.compile(r'\!=')),
        ]

    def lex(self, code):
        lineno = 1
        line_start = 0
        loc = 0;
        par_count = 0
        bracket_count = 0
        col = 0
        while(loc < len(code)):
            matched = False
            for (tid, reg) in self.token_specification:
                mo = reg.match(code, loc)
                if mo:
                    curline = lineno
                    col = mo.start()-line_start
                    matched = True
                    loc = mo.end()
                    match_text = mo.group()
                    if tid == 'ignore' or tid == 'comment':
                        break
                    elif tid == 'lparen':
                        par_count += 1
                    elif tid == 'rparen':
                        par_count -= 1
                    elif tid == 'lbracket':
                        bracket_count += 1
                    elif tid == 'rbracket':
                        bracket_count -= 1
                    elif tid == 'multiline_string':
                        tid = 'string'
                        lines = match_text.split('\n')
                        if len(lines) > 1:
                            lineno += len(lines) - 1
                            line_start = mo.end() - len(lines[-1])
                    elif tid == 'eol' or tid == 'eol_cont':
                        lineno += 1
                        line_start = loc
                        if par_count > 0 or bracket_count > 0:
                            break
                    yield Token(tid, curline, col)
            if not matched:
                raise ParseException('lexer', lineno, col)

class Parser:
    def __init__(self, code):
        self.stream = Lexer().lex(code)
        self.getsym()

    def getsym(self):
        self.current = next(self.stream)

    def accept(self, s):
        if self.current.tid == s:
            self.getsym()
            return True
        return False
    
    def expect(self, s):
        if self.accept(s):
            return True
        raise ParseException('Unknown token', self.current.lineno, self.current.colno)

    def parse(self):
        self.codeblock()

    def statement(self):
        if self.accept('lparen'):
            self.statement()
            self.expect('rparen')
        if self.accept('lbracket'):
            self.args()
            self.expect('rbracket')
        self.expression()
        self.rest_statement()

    def args(self):
        self.statement()
        if self.accept('comma'):
            self.args()
        if self.accept('colon'):
            self.statement()
            if self.accept('comma'):
                self.args()

    def rest_statement(self):
        if self.accept('.'):
            self.method_call()

    def method_call(self):
        self.expression()
        self.expect('lparen')
        self.args()
        self.expect('rparen')

    def expression(self):
        #t = self.current
        if self.accept('true'):
            return
        if self.accept('false'):
            return
        if self.accept('id'):
            self.rest_expression()
            return
        if self.accept('number'):
            return
        if self.accept('string'):
            return
        if self.accept('not'):
            self.statement()
            return

    def rest_expression(self):
        if self.accept('lparen'):
            self.args()
            self.expect('rparen')

    def ifelseblock(self):
        if self.current == 'elif':
            self.statement()
            self.expect('eol')
            self.codeblock()

    def elseblock(self):
        if self.current == 'else':
            self.expect('eol')
            self.codeblock()

    def line(self):
        if self.accept('if'):
            self.statement()
            self.ifelseblock()
            self.elseblock()
            self.expect('endif')
        if self.current == 'eol':
            return
        self.statement()

    def codeblock(self):
        if self.accept('eol'):
            return self.codeblock()
        cond = True
        while cond:
            self.line()
            cond = self.expect('eol')

if __name__ == '__main__':
    code = open(sys.argv[1]).read()
#    lex = Lexer()
#    try:
#        for i in lex.lex(code):
#            print('Token:', i.tid, 'Line:', i.lineno, 'Column:', i.colno)
#    except ParseException as e:
#        print('Error line', e.lineno, 'column', e.colno)
    parser = Parser(code)
    try:
        parser.parse()
    except ParseException as e:
        print('Error', e.text, 'line', e.lineno, 'column', e.colno)

