# Copyright 2014-2016 The Meson development team

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
from .mesonlib import MesonException

class ParseException(MesonException):
    def __init__(self, text, lineno, colno):
        super().__init__(text)
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
                         'endif', 'and', 'or', 'not', 'foreach', 'endforeach'}
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
            ('dblquote', re.compile(r'"')),
            ('string', re.compile(r"'([^'\\]|(\\.))*'")),
            ('comma', re.compile(r',')),
            ('plusassign', re.compile(r'\+=')),
            ('dot', re.compile(r'\.')),
            ('plus', re.compile(r'\+')),
            ('dash', re.compile(r'-')),
            ('star', re.compile(r'\*')),
            ('percent', re.compile(r'\%')),
            ('fslash', re.compile(r'/')),
            ('colon', re.compile(r':')),
            ('equal', re.compile(r'==')),
            ('nequal', re.compile(r'\!=')),
            ('assign', re.compile(r'=')),
            ('le', re.compile(r'<=')),
            ('lt', re.compile(r'<')),
            ('ge', re.compile(r'>=')),
            ('gt', re.compile(r'>')),
            ('questionmark', re.compile(r'\?')),
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
                    elif tid == 'dblquote':
                        raise ParseException('Double quotes are not supported. Use single quotes.', lineno, col)
                    elif tid == 'string':
                        value = match_text[1:-1].replace(r"\'", "'").replace(r" \\ ".strip(), r" \ ".strip())\
                        .replace("\\n", "\n")
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
                    break
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

    def __str__(self):
        return "Id node: '%s' (%d, %d)." % (self.value, self.lineno, self.colno)

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

    def __str__(self):
        return "String node: '%s' (%d, %d)." % (self.value, self.lineno, self.colno)

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

class ComparisonNode:
    def __init__(self, lineno, colno, ctype, left, right):
        self.lineno = lineno
        self.colno = colno
        self.left = left
        self.right = right
        self.ctype = ctype

class ArithmeticNode:
    def __init__(self, lineno, colno, operation, left, right):
        self.lineno = lineno
        self.colno = colno
        self.left = left
        self.right = right
        self.operation = operation

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

class IndexNode:
    def __init__(self, iobject, index):
        self.iobject = iobject
        self.index = index
        self.lineno = iobject.lineno
        self.colno = iobject.colno

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

class PlusAssignmentNode:
    def __init__(self, lineno, colno, var_name, value):
        self.lineno = lineno
        self.colno = colno
        self.var_name = var_name
        assert(isinstance(var_name, str))
        self.value = value

class ForeachClauseNode():
    def __init__(self, lineno, colno, varname, items, block):
        self.lineno = lineno
        self.colno = colno
        self.varname = varname
        self.items = items
        self.block = block

class IfClauseNode():
    def __init__(self, lineno, colno):
        self.lineno = lineno
        self.colno = colno
        self.ifs = []
        self.elseblock = EmptyNode()

class UMinusNode():
    def __init__(self, lineno, colno, value):
        self.lineno = lineno
        self.colno = colno
        self.value = value

class IfNode():
    def __init__(self, lineno, colno, condition, block):
        self.lineno = lineno
        self.colno = colno
        self.condition = condition
        self.block = block

class TernaryNode():
    def __init__(self, lineno, colno, condition, trueblock, falseblock):
        self.lineno = lineno
        self.colno = colno
        self.condition = condition
        self.trueblock = trueblock
        self.falseblock = falseblock

class ArgumentNode():
    def __init__(self, token):
        self.lineno = token.lineno
        self.colno = token.colno
        self.arguments = []
        self.kwargs = {}
        self.order_error = False

    def prepend(self, statement):
        if self.num_kwargs() > 0:
            self.order_error = True
        if not isinstance(statement, EmptyNode):
            self.arguments = [statement] + self.arguments

    def append(self, statement):
        if self.num_kwargs() > 0:
            self.order_error = True
        if not isinstance(statement, EmptyNode):
            self.arguments = self.arguments + [statement]

    def set_kwarg(self, name, value):
        self.kwargs[name] = value

    def num_args(self):
        return len(self.arguments)

    def num_kwargs(self):
        return len(self.kwargs)

    def incorrect_order(self):
        return self.order_error

    def __len__(self):
        return self.num_args() # Fixme

comparison_map = {'equal': '==',
                  'nequal': '!=',
                  'lt': '<',
                  'le': '<=',
                  'gt': '>',
                  'ge': '>='
                  }

# Recursive descent parser for Meson's definition language.
# Very basic apart from the fact that we have many precedence
# levels so there are not enough words to describe them all.
# Enter numbering:
#
# 1 assignment
# 2 or
# 3 and
# 4 comparison
# 5 arithmetic
# 6 negation
# 7 funcall, method call
# 8 parentheses
# 9 plain token

class Parser:
    def __init__(self, code):
        self.stream = Lexer().lex(code)
        self.getsym()
        self.in_ternary = False

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
        if self.accept('plusassign'):
            value = self.e1()
            if not isinstance(left, IdNode):
                raise ParseException('Plusassignment target must be an id.', left.lineno, left.colno)
            return PlusAssignmentNode(left.lineno, left.colno, left.value, value)
        elif self.accept('assign'):
            value = self.e1()
            if not isinstance(left, IdNode):
                raise ParseException('Assignment target must be an id.',
                                     left.lineno, left.colno)
            return AssignmentNode(left.lineno, left.colno, left.value, value)
        elif self.accept('questionmark'):
            if self.in_ternary:
                raise ParseException('Nested ternary operators are not allowed.',
                                     left.lineno, left.colno)
            self.in_ternary = True
            trueblock = self.e1()
            self.expect('colon')
            falseblock = self.e1()
            self.in_ternary = False
            return TernaryNode(left.lineno, left.colno, left, trueblock, falseblock)
        return left

    def e2(self):
        left = self.e3()
        while self.accept('or'):
            left = OrNode(left.lineno, left.colno, left, self.e3())
        return left

    def e3(self):
        left = self.e4()
        while self.accept('and'):
            left = AndNode(left.lineno, left.colno, left, self.e4())
        return left

    def e4(self):
        left = self.e5()
        for nodename, operator_type in comparison_map.items():
            if self.accept(nodename):
                return ComparisonNode(left.lineno, left.colno, operator_type, left, self.e5())
        return left

    def e5(self):
        return self.e5add()

    def e5add(self):
        left = self.e5sub()
        if self.accept('plus'):
            return ArithmeticNode(left.lineno, left.colno, 'add', left, self.e5add())
        return left

    def e5sub(self):
        left = self.e5mod()
        if self.accept('dash'):
            return ArithmeticNode(left.lineno, left.colno, 'sub', left, self.e5sub())
        return left

    def e5mod(self):
        left = self.e5mul()
        if self.accept('percent'):
            return ArithmeticNode(left.lineno, left.colno, 'mod', left, self.e5mod())
        return left

    def e5mul(self):
        left = self.e5div()
        if self.accept('star'):
            return ArithmeticNode(left.lineno, left.colno, 'mul', left, self.e5mul())
        return left

    def e5div(self):
        left = self.e6()
        if self.accept('fslash'):
            return ArithmeticNode(left.lineno, left.colno, 'div', left, self.e5div())
        return left

    def e6(self):
        if self.accept('not'):
            return NotNode(self.current.lineno, self.current.colno, self.e7())
        if self.accept('dash'):
            return UMinusNode(self.current.lineno, self.current.colno, self.e7())
        return self.e7()

    def e7(self):
        left = self.e8()
        if self.accept('lparen'):
            args = self.args()
            self.expect('rparen')
            if not isinstance(left, IdNode):
                raise ParseException('Function call must be applied to plain id',
                                     left.lineno, left.colno)
            left = FunctionNode(left.lineno, left.colno, left.value, args)
        go_again = True
        while go_again:
            go_again = False
            if self.accept('dot'):
                go_again = True
                left = self.method_call(left)
            if self.accept('lbracket'):
                go_again = True
                left = self.index_call(left)
        return left

    def e8(self):
        if self.accept('lparen'):
            e = self.statement()
            self.expect('rparen')
            return e
        elif self.accept('lbracket'):
            args = self.args()
            self.expect('rbracket')
            return ArrayNode(args)
        else:
            return self.e9()

    def e9(self):
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
        a = ArgumentNode(s)

        while not isinstance(s, EmptyNode):
            if self.accept('comma'):
                a.append(s)
            elif self.accept('colon'):
                if not isinstance(s, IdNode):
                    raise ParseException('Keyword argument must be a plain identifier.',
                                         s.lineno, s.colno)
                a.set_kwarg(s.value, self.statement())
                if not self.accept('comma'):
                    return a
            else:
                a.append(s)
                return a
            s = self.statement()
        return a

    def method_call(self, source_object):
        methodname = self.e9()
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

    def index_call(self, source_object):
        index_statement = self.statement()
        self.expect('rbracket')
        return IndexNode(source_object, index_statement)

    def foreachblock(self):
        t = self.current
        self.expect('id')
        varname = t
        self.expect('colon')
        items = self.statement()
        block = self.codeblock()
        return ForeachClauseNode(varname.lineno, varname.colno, varname, items, block)

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
        if self.accept('foreach'):
            block = self.foreachblock()
            self.expect('endforeach')
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
