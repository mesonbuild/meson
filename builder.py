#!/usr/bin/python3 -tt

# Copyright 2012 Jussi Pakkanen

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import ply.lex as lex
import ply.yacc as yacc

tokens = ['LPAREN',
          'RPAREN',
          'VARIABLE',
          'COMMENT',
          'EQUALS',
          'COMMA',
          'DOT',
          'STRING',
          'EOL_CONTINUE',
          'EOL',
          ]

t_EQUALS = '='
t_LPAREN = '\('
t_RPAREN = '\)'
t_VARIABLE = '[a-zA-Z][_0-9a-zA-Z]*'
t_COMMENT = '\#[^\n]*'
t_COMMA = ','
t_DOT = '\.'
t_STRING = "'[^']*'"
t_EOL_CONTINUE = r'\\\n'
t_EOL = r'\n'

t_ignore = ' \t'

def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

def test_lexer():
    s = """hello = (something) # this = (that)
    function(h)
    obj.method(lll, \\
    'string')
    """
    lexer = lex.lex()
    lexer.input(s)
    while True:
        tok = lexer.token()
        if not tok:
            break
        print(tok)

if __name__ == '__main__':
    test_lexer()