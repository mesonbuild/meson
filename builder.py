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
          'LBRACKET',
          'RBRACKET',
          'LBRACE',
          'RBRACE',
          'ATOM',
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
t_LBRACKET = '\['
t_RBRACKET = '\]'
t_LBRACE = '\{'
t_RBRACE = '\}'
t_ATOM = '[a-zA-Z][_0-9a-zA-Z]*'
t_COMMENT = '\#[^\n]*'
t_COMMA = ','
t_DOT = '\.'
t_STRING = "'[^']*'"

t_ignore = ' \t'

def t_EOL(t):
    r'\n'
    t.lexer.lineno += 1
    return t

def t_EOL_CONTINUE(t):
    r'\\[ \t]*\n'
    t.lexer.lineno += 1

def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

# Yacc part

def p_codeblock(t):
    'codeblock : statement EOL codeblock'
    print('Codeblock')
    pass

def p_codeblock_last(t):
    'codeblock : statement EOL'
    print('Single line')
    pass

#def p_codeblock_empty(t):
#    'codeblock :'
#    pass

def p_expression_atom(t):
    'expression : ATOM'
    print('Atom: ' + t[1])
    pass

def p_expression_string(t):
    'expression : STRING'
    print('String: ' + t[1])
    pass

def p_statement_assign(t):
    'statement : expression EQUALS statement'
    pass

def p_statement_func_call(t):
    'statement : expression LPAREN args RPAREN'
    print('Function call: ' + str(t[1])) # t[1])
    pass

def p_statement_method_call(t):
    'statement : expression DOT expression LPAREN args RPAREN'
    print('Method call: ' + str(t[1]))
    pass

def p_statement_expression(t):
    'statement : expression'
    #print('s-e: ' + t[1])
    pass

def p_args_multiple(t):
    'args : statement COMMA args'
    pass

def p_args_single(t):
    'args : statement'
    pass

def p_args_none(t):
    'args :'
    pass

def p_error(t):
    print('Parser errored out at: ' + t.value)

def test_lexer():
    s = """hello = (something) # this = (that)
    two = ['file1', 'file2']
    function(h) { stuff }
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

def test_parser():
    code = """funccall('something')
    method.call(abc)
    """
    lexer = lex.lex()
    parser = yacc.yacc()
    result = parser.parse(code)
    print(result)

if __name__ == '__main__':
    #test_lexer()
    test_parser()
