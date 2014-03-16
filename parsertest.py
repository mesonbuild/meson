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
    def __init__(self, tid, lineno, colno, value):
        self.tid = tid
        self.lineno = lineno
        self.colno = colno
        self.value = value
    
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
            ('rbracket', re.compile(r'\]')),
            ('string', re.compile("'[^']*?'")),
            ('comma', re.compile(r',')),
            ('dot', re.compile(r'\.')),
            ('colon', re.compile(r':')),
            ('equal', re.compile(r'==')),
            ('nequal', re.compile(r'\!=')),
            ('assign', re.compile(r'=')),
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
                        break
                    elif tid == 'lparen':
                        par_count += 1
                    elif tid == 'rparen':
                        par_count -= 1
                    elif tid == 'lbracket':
                        bracket_count += 1
                    elif tid == 'rbracket':
                        bracket_count -= 1
                    elif tid == 'string':
                        value = match_text[1:-1]
                    elif tid == 'multiline_string':
                        tid = 'string'
                        value = match_text[3:-3]
                        lines = match_text.split('\n')
                        if len(lines) > 1:
                            lineno += len(lines) - 1
                            line_start = mo.end() - len(lines[-1])
                    elif tid == 'number':
                        value = int(match_text)
                    elif tid == 'eol' or tid == 'eol_cont':
                        lineno += 1
                        line_start = loc
                        if par_count > 0 or bracket_count > 0:
                            break
                    elif tid == 'id':
                        if match_text in self.keywords:
                            tid = match_text
                        else:
                            value = match_text
                    yield Token(tid, curline, col, value)
            if not matched:
                raise ParseException('lexer', lineno, col)

class BooleanNode:
    def __init__(self, token, value):
        self.lineno = token.lineno
        self.colno = token.colno
        self.value = value
        assert(isinstance(self.value, bool))

class IdNode:
    def __init__(self, token):
        self.lineno = token.lineno
        self.colno = token.colno
        self.value = token.value
        assert(isinstance(self.value, str))

class NumberNode:
    def __init__(self, token):
        self.lineno = token.lineno
        self.colno = token.colno
        self.value = token.value
        assert(isinstance(self.value, int))

class StringNode:
    def __init__(self, token):
        self.lineno = token.lineno
        self.colno = token.colno
        self.value = token.value
        assert(isinstance(self.value, str))

class ArrayNode:
    def __init__(self, args):
        self.lineno = args.lineno
        self.colno = args.colno
        self.args = args

class EmptyNode:
    def __init__(self):
        self.lineno = 0
        self.colno = 0
        self.value = None

class OrNode:
    def __init__(self, lineno, colno, left, right):
        self.lineno = lineno
        self.colno = colno
        self.left = left
        self.right = right

class AndNode:
    def __init__(self, lineno, colno, left, right):
        self.lineno = lineno
        self.colno = colno
        self.left = left
        self.right = right

class EqualNode:
    def __init__(self, lineno, colno, left, right):
        self.lineno = lineno
        self.colno = colno
        self.left = left
        self.right = right

class NEqualNode:
    def __init__(self, lineno, colno, left, right):
        self.lineno = lineno
        self.colno = colno
        self.left = left
        self.right = right

class NotNode:
    def __init__(self, lineno, colno, value):
        self.lineno = lineno
        self.colno = colno
        self.value = value

class CodeBlockNode:
    def __init__(self, lineno, colno):
        self.lineno = lineno
        self.colno = colno
        self.lines = []

class MethodNode:
    def __init__(self, lineno, colno, source_object, name, args):
        self.lineno = lineno
        self.colno = colno
        self.source_object = source_object
        self.name = name
        assert(isinstance(self.name, str))
        self.args = args

class FunctionNode:
    def __init__(self, lineno, colno, func_name, args):
        self.lineno = lineno
        self.colno = colno
        self.func_name = func_name
        assert(isinstance(func_name, str))
        self.args = args

class AssignmentNode:
    def __init__(self, lineno, colno, var_name, value):
        self.lineno = lineno
        self.colno = colno
        self.var_name = var_name
        assert(isinstance(var_name, str))
        self.value = value

class IfClauseNode():
    def __init__(self, lineno, colno):
        self.lineno = lineno
        self.colno = colno
        self.ifs = []
        self.elseblock = EmptyNode()

class IfNode():
    def __init__(self, lineno, colno, condition, block):
        self.lineno = lineno
        self.colno = colno
        self.condition = condition
        self.block = block

class ArgumentNode():
    def __init__(self, token):
        self.lineno = token.lineno
        self.colno = token.colno
        self.arguments = []
        self.kwargs = {}
        self.order_error = False

    def prepend(self, statement):
        if not isinstance(statement, EmptyNode):
            self.arguments = [statement] + self.arguments

    def append(self, statement):
        if not isinstance(statement, EmptyNode):
            self.arguments = self.arguments + [statement]

    def set_kwarg(self, name, value):
        if self.num_args() > 0:
            self.order_error = True
        self.kwargs[name] = value

    def num_args(self):
        return len(self.arguments)

    def num_kwargs(self):
        return len(self.kwargs)

    def incorrect_order(self):
        return self.order_error

    def __len__(self):
        return self.num_args() # Fixme

# Recursive descent parser for Meson's definition language.
# Very basic apart from the fact that we have many precedence
# levels so there are not enough words to describe them all.
# Enter numbering:
#
# 1 assignment
# 2 or
# 3 and
# 4 equality
# comparison, plus and multiplication would go here
# 5 negation
# 6 funcall, method call
# 7 parentheses 
# 8 plain token

class Parser:
    def __init__(self, code):
        self.stream = Lexer().lex(code)
        self.getsym()

    def getsym(self):
        try:
            self.current = next(self.stream)
        except StopIteration:
            self.current = Token('eof', 0, 0, None)

    def accept(self, s):
        if self.current.tid == s:
            self.getsym()
            return True
        return False

    def expect(self, s):
        if self.accept(s):
            return True
        raise ParseException('Expecting %s got %s.' % (s, self.current.tid), self.current.lineno, self.current.colno)

    def parse(self):
        block = self.codeblock()
        self.expect('eof')
        return block

    def statement(self):
        return self.e1()

    def e1(self):
        left = self.e2()
        if self.accept('assign'):
            value = self.e1()
            if not isinstance(left, IdNode):
                raise ParseException('Assignment target must be an id.',
                                     left.lineno, left.colno)
            return AssignmentNode(left.lineno, left.colno, left.value, value)
        return left

    def e2(self):
        left = self.e3()
        if self.accept('or'):
            return OrNode(left.lineno, left.colno, left, self.e3())
        return left

    def e3(self):
        left = self.e4()
        if self.accept('and'):
            return AndNode(left.lineno, left.colno, left, self.e4())
        return left

    def e4(self):
        left = self.e5()
        if self.accept('equal'):
            return EqualNode(left.lineno, left.colno, left, self.e5())
        if self.accept('nequal'):
            return NEqualNode(left.lineno, left.colno, left, self.e5())
        return left

    def e5(self):
        if self.accept('not'):
            return NotNode(self.current.lineno, self.current.colno, self.e6())
        return self.e6()

    def e6(self):
        left = self.e7()
        if self.accept('dot'):
            return self.method_call(left)
        elif self.accept('lparen'):
            args = self.args()
            self.expect('rparen')
            if not isinstance(left, IdNode):
                raise ParseException('Function call must be applied to plain id',
                                     left.lineno, left.colno)
            return FunctionNode(left.lineno, left.colno, left.value, args)
        return left

    def e7(self):
        if self.accept('lparen'):
            e = self.statement()
            self.expect('rparen')
            return e
        elif self.accept('lbracket'):
            args = self.args()
            self.expect('rbracket')
            return ArrayNode(args)
        else:
            return self.e8()

    def e8(self):
        t = self.current
        if self.accept('true'):
            return BooleanNode(t, True);
        if self.accept('false'):
            return BooleanNode(t, False)
        if self.accept('id'):
            return IdNode(t)
        if self.accept('number'):
            return NumberNode(t)
        if self.accept('string'):
            return StringNode(t)
        return EmptyNode()

    def args(self):
        s = self.statement()
        if isinstance(s, EmptyNode):
            ArgumentNode(s)

        if self.accept('comma'):
            rest = self.args()
            rest.prepend(s)
            return rest
        if self.accept('colon'):
            if not isinstance(s, IdNode):
                raise ParseException('Keyword argument must be a plain identifier.',
                                     s.lineno, s.colno)
            value = self.statement()
            if self.accept('comma'):
                a = self.args()
            else:
                a = ArgumentNode(self.current)
            a.set_kwarg(s.value, value)
            return a
        a = ArgumentNode(self.current)
        a.append(s)
        return a

    def method_call(self, source_object):
        methodname = self.e8()
        if not(isinstance(methodname, IdNode)):
            raise ParseException('Method name must be plain id',
                                 self.current.lineno, self.current.colno)
        self.expect('lparen')
        args = self.args()
        self.expect('rparen')
        method = MethodNode(methodname.lineno, methodname.colno, source_object, methodname.value, args)
        if self.accept('dot'):
            return self.method_call(method)
        return method

    def ifblock(self):
        condition = self.statement()
        clause = IfClauseNode(condition.lineno, condition.colno)
        block = self.codeblock()
        clause.ifs.append(IfNode(clause.lineno, clause.colno, condition, block))
        self.elseifblock(clause)
        clause.elseblock = self.elseblock()
        return clause

    def elseifblock(self, clause):
        while self.accept('elif'):
            s = self.statement()
            self.expect('eol')
            b = self.codeblock()
            clause.ifs.append(IfNode(s.lineno, s.colno, s, b))

    def elseblock(self):
        if self.accept('else'):
            self.expect('eol')
            return self.codeblock()

    def line(self):
        if self.current == 'eol':
            return EmptyNode()
        if self.accept('if'):
            block = self.ifblock()
            self.expect('endif')
            return block
        return self.statement()

    def codeblock(self):
        block = CodeBlockNode(self.current.lineno, self.current.colno)
        cond = True
        while cond:
            curline = self.line()
            if not isinstance(curline, EmptyNode):
                block.lines.append(curline)
            cond = self.accept('eol')
        return block

if __name__ == '__main__':
    for code in sys.argv[1:]:
        parser = Parser(open(code).read())
        try:
            print(code)
            parser.parse()
        except ParseException as e:
            print('Error', e.text, 'line', e.lineno, 'column', e.colno)

