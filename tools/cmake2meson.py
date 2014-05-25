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

import sys, os
import re

class Lexer:
    def __init__(self):
        self.token_specification = [
            # Need to be sorted longest to shortest.
            ('ignore', re.compile(r'[ \t]')),
            ('id', re.compile('[-+_0-9a-z/A-Z.]+')),
            ('eol', re.compile(r'\n')),
            ('comment', re.compile(r'\#.*')),
            ('lparen', re.compile(r'\(')),
            ('rparen', re.compile(r'\)')),
            ('string', re.compile('"[^"]*?"')),
            ('varexp', re.compile(r'\${[-_0-9a-z/A-Z.]+}')),
        ]

    def lex(self, code):
        lineno = 1
        line_start = 0
        loc = 0;
        col = 0
        while(loc < len(code)):
            matched = False
            value = None
            for (tid, reg) in self.token_specification:
                mo = reg.match(code, loc)
                if mo:
                    curline = lineno
                    col = mo.start()-line_start
                    matched = True
                    loc = mo.end()
                    match_text = mo.group()
                    if tid == 'ignore' or tid == 'comment':
                        pass
                    elif tid == 'lparen':
                        yield('lparen')
                    elif tid == 'rparen':
                        yield('rparen')
                    elif tid == 'string':
                        yield('String: ' + match_text[1:-1])
                    elif tid == 'id':
                        yield('Id: ' + match_text)
                    elif tid == 'eol':
                        yield('eol')
                    elif tid == 'varexp':
                        yield('Variable:' + match_text[2:-1])
                    else:
                        raise RuntimeError('Wharrgarbl')
                    break
            if not matched:
                raise RuntimeError('Lexer got confused %d %d' % (lineno, col))

def convert(cmake_root):
    cfile = os.path.join(cmake_root, 'CMakeLists.txt')
    cmakecode = open(cfile).read()
    l = Lexer()
    for t in l.lex(cmakecode):
        print(t)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(sys.argv[0], '<CMake project root>')
    convert(sys.argv[1])

