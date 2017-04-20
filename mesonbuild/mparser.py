# Copyright 2014-2017 The Meson development team

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
from . import mlog

class ParseException(MesonException):
    def __init__(self, text, line, lineno, colno):
        # Format as error message, followed by the line with the error, followed by a caret to show the error column.
        super().__init__("%s\n%s\n%s" % (text, line, '%s^' % (' ' * colno)))
        self.lineno = lineno
        self.colno = colno

class BlockParseException(MesonException):
    def __init__(self, text, line, lineno, colno, start_line, start_lineno, start_colno):
        # This can be formatted in two ways - one if the block start and end are on the same line, and a different way if they are on different lines.

        if lineno == start_lineno:
            # If block start and end are on the same line, it is formatted as:
            # Error message
            # Followed by the line with the error
            # Followed by a caret to show the block start
            # Followed by underscores
            # Followed by a caret to show the block end.
            super().__init__("%s\n%s\n%s" % (text, line, '%s^%s^' % (' ' * start_colno, '_' * (colno - start_colno - 1))))
        else:
            # If block start and end are on different lines, it is formatted as:
            # Error message
            # Followed by the line with the error
            # Followed by a caret to show the error column.
            # Followed by a message saying where the block started.
            # Followed by the line of the block start.
            # Followed by a caret for the block start.
            super().__init__("%s\n%s\n%s\nFor a block that started at %d,%d\n%s\n%s" % (text, line, '%s^' % (' ' * colno), start_lineno, start_colno, start_line, "%s^" % (' ' * start_colno)))
        self.lineno = lineno
        self.colno = colno

class Token:
    def __init__(self, tid, subdir, line_start, lineno, colno, bytespan, value):
        self.tid = tid
        self.subdir = subdir
        self.line_start = line_start
        self.lineno = lineno
        self.colno = colno
        self.bytespan = bytespan
        self.value = value

    def __eq__(self, other):
        if isinstance(other, str):
            return self.tid == other
        return self.tid == other.tid

class Lexer:
    def __init__(self, code):
        self.code = code
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
            ('comment', re.compile(r'#.*')),
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
            ('percent', re.compile(r'%')),
            ('fslash', re.compile(r'/')),
            ('colon', re.compile(r':')),
            ('equal', re.compile(r'==')),
            ('nequal', re.compile(r'!=')),
            ('assign', re.compile(r'=')),
            ('le', re.compile(r'<=')),
            ('lt', re.compile(r'<')),
            ('ge', re.compile(r'>=')),
            ('gt', re.compile(r'>')),
            ('questionmark', re.compile(r'\?')),
        ]

    def getline(self, line_start):
        return self.code[line_start:self.code.find('\n', line_start)]

    def lex(self, subdir):
        line_start = 0
        lineno = 1
        loc = 0
        par_count = 0
        bracket_count = 0
        col = 0
        while loc < len(self.code):
            matched = False
            value = None
            for (tid, reg) in self.token_specification:
                mo = reg.match(self.code, loc)
                if mo:
                    curline = lineno
                    curline_start = line_start
                    col = mo.start() - line_start
                    matched = True
                    span_start = loc
                    loc = mo.end()
                    span_end = loc
                    bytespan = (span_start, span_end)
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
                        raise ParseException('Double quotes are not supported. Use single quotes.', self.getline(line_start), lineno, col)
                    elif tid == 'string':
                        value = match_text[1:-1]\
                            .replace(r"\'", "'")\
                            .replace(r" \\ ".strip(), r" \ ".strip())\
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
                    yield Token(tid, subdir, curline_start, curline, col, bytespan, value)
                    break
            if not matched:
                raise ParseException('lexer', self.getline(line_start), lineno, col)

class ElementaryNode:
    def __init__(self, token):
        self.lineno = token.lineno
        self.subdir = token.subdir
        self.colno = token.colno
        self.value = token.value
        self.bytespan = token.bytespan

class BooleanNode(ElementaryNode):
    def __init__(self, token, value):
        super().__init__(token)
        self.value = value
        assert(isinstance(self.value, bool))

class IdNode(ElementaryNode):
    def __init__(self, token):
        super().__init__(token)
        assert(isinstance(self.value, str))

    def __str__(self):
        return "Id node: '%s' (%d, %d)." % (self.value, self.lineno, self.colno)

class NumberNode(ElementaryNode):
    def __init__(self, token):
        super().__init__(token)
        assert(isinstance(self.value, int))

class StringNode(ElementaryNode):
    def __init__(self, token):
        super().__init__(token)
        assert(isinstance(self.value, str))

    def __str__(self):
        return "String node: '%s' (%d, %d)." % (self.value, self.lineno, self.colno)

class ArrayNode:
    def __init__(self, args):
        self.subdir = args.subdir
        self.lineno = args.lineno
        self.colno = args.colno
        self.args = args

class EmptyNode:
    def __init__(self, lineno, colno):
        self.subdir = ''
        self.lineno = lineno
        self.colno = colno
        self.value = None

class OrNode:
    def __init__(self, left, right):
        self.subdir = left.subdir
        self.lineno = left.lineno
        self.colno = left.colno
        self.left = left
        self.right = right

class AndNode:
    def __init__(self, left, right):
        self.subdir = left.subdir
        self.lineno = left.lineno
        self.colno = left.colno
        self.left = left
        self.right = right

class ComparisonNode:
    def __init__(self, ctype, left, right):
        self.lineno = left.lineno
        self.colno = left.colno
        self.subdir = left.subdir
        self.left = left
        self.right = right
        self.ctype = ctype

class ArithmeticNode:
    def __init__(self, operation, left, right):
        self.subdir = left.subdir
        self.lineno = left.lineno
        self.colno = left.colno
        self.left = left
        self.right = right
        self.operation = operation

class NotNode:
    def __init__(self, location_node, value):
        self.subdir = location_node.subdir
        self.lineno = location_node.lineno
        self.colno = location_node.colno
        self.value = value

class CodeBlockNode:
    def __init__(self, location_node):
        self.subdir = location_node.subdir
        self.lineno = location_node.lineno
        self.colno = location_node.colno
        self.lines = []

class IndexNode:
    def __init__(self, iobject, index):
        self.iobject = iobject
        self.index = index
        self.subdir = iobject.subdir
        self.lineno = iobject.lineno
        self.colno = iobject.colno

class MethodNode:
    def __init__(self, subdir, lineno, colno, source_object, name, args):
        self.subdir = subdir
        self.lineno = lineno
        self.colno = colno
        self.source_object = source_object
        self.name = name
        assert(isinstance(self.name, str))
        self.args = args

class FunctionNode:
    def __init__(self, subdir, lineno, colno, func_name, args):
        self.subdir = subdir
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

class ForeachClauseNode:
    def __init__(self, lineno, colno, varname, items, block):
        self.lineno = lineno
        self.colno = colno
        self.varname = varname
        self.items = items
        self.block = block

class IfClauseNode:
    def __init__(self, lineno, colno):
        self.lineno = lineno
        self.colno = colno
        self.ifs = []
        self.elseblock = EmptyNode(lineno, colno)

class UMinusNode:
    def __init__(self, current_location, value):
        self.subdir = current_location.subdir
        self.lineno = current_location.lineno
        self.colno = current_location.colno
        self.value = value

class IfNode:
    def __init__(self, lineno, colno, condition, block):
        self.lineno = lineno
        self.colno = colno
        self.condition = condition
        self.block = block

class TernaryNode:
    def __init__(self, lineno, colno, condition, trueblock, falseblock):
        self.lineno = lineno
        self.colno = colno
        self.condition = condition
        self.trueblock = trueblock
        self.falseblock = falseblock

class ArgumentNode:
    def __init__(self, token):
        self.lineno = token.lineno
        self.colno = token.colno
        self.subdir = token.subdir
        self.arguments = []
        self.commas = []
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
            self.arguments += [statement]

    def set_kwarg(self, name, value):
        if name in self.kwargs:
            mlog.warning('Keyword argument "%s" defined multiple times. This will be a an error in future Meson releases.' % name)
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
    def __init__(self, code, subdir):
        self.lexer = Lexer(code)
        self.stream = self.lexer.lex(subdir)
        self.current = Token('eof', '', 0, 0, 0, (0, 0), None)
        self.getsym()
        self.in_ternary = False

    def getsym(self):
        try:
            self.current = next(self.stream)
        except StopIteration:
            self.current = Token('eof', '', self.current.line_start, self.current.lineno, self.current.colno + self.current.bytespan[1] - self.current.bytespan[0], (0, 0), None)

    def getline(self):
        return self.lexer.getline(self.current.line_start)

    def accept(self, s):
        if self.current.tid == s:
            self.getsym()
            return True
        return False

    def expect(self, s):
        if self.accept(s):
            return True
        raise ParseException('Expecting %s got %s.' % (s, self.current.tid), self.getline(), self.current.lineno, self.current.colno)

    def block_expect(self, s, block_start):
        if self.accept(s):
            return True
        raise BlockParseException('Expecting %s got %s.' % (s, self.current.tid), self.getline(), self.current.lineno, self.current.colno, self.lexer.getline(block_start.line_start), block_start.lineno, block_start.colno)

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
                raise ParseException('Plusassignment target must be an id.', self.getline(), left.lineno, left.colno)
            return PlusAssignmentNode(left.lineno, left.colno, left.value, value)
        elif self.accept('assign'):
            value = self.e1()
            if not isinstance(left, IdNode):
                raise ParseException('Assignment target must be an id.',
                                     self.getline(), left.lineno, left.colno)
            return AssignmentNode(left.lineno, left.colno, left.value, value)
        elif self.accept('questionmark'):
            if self.in_ternary:
                raise ParseException('Nested ternary operators are not allowed.',
                                     self.getline(), left.lineno, left.colno)
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
            left = OrNode(left, self.e3())
        return left

    def e3(self):
        left = self.e4()
        while self.accept('and'):
            left = AndNode(left, self.e4())
        return left

    def e4(self):
        left = self.e5()
        for nodename, operator_type in comparison_map.items():
            if self.accept(nodename):
                return ComparisonNode(operator_type, left, self.e5())
        return left

    def e5(self):
        return self.e5add()

    def e5add(self):
        left = self.e5sub()
        if self.accept('plus'):
            return ArithmeticNode('add', left, self.e5add())
        return left

    def e5sub(self):
        left = self.e5mod()
        if self.accept('dash'):
            return ArithmeticNode('sub', left, self.e5sub())
        return left

    def e5mod(self):
        left = self.e5mul()
        if self.accept('percent'):
            return ArithmeticNode('mod', left, self.e5mod())
        return left

    def e5mul(self):
        left = self.e5div()
        if self.accept('star'):
            return ArithmeticNode('mul', left, self.e5mul())
        return left

    def e5div(self):
        left = self.e6()
        if self.accept('fslash'):
            return ArithmeticNode('div', left, self.e5div())
        return left

    def e6(self):
        if self.accept('not'):
            return NotNode(self.current, self.e7())
        if self.accept('dash'):
            return UMinusNode(self.current, self.e7())
        return self.e7()

    def e7(self):
        left = self.e8()
        block_start = self.current
        if self.accept('lparen'):
            args = self.args()
            self.block_expect('rparen', block_start)
            if not isinstance(left, IdNode):
                raise ParseException('Function call must be applied to plain id',
                                     self.getline(), left.lineno, left.colno)
            left = FunctionNode(left.subdir, left.lineno, left.colno, left.value, args)
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
        block_start = self.current
        if self.accept('lparen'):
            e = self.statement()
            self.block_expect('rparen', block_start)
            return e
        elif self.accept('lbracket'):
            args = self.args()
            self.block_expect('rbracket', block_start)
            return ArrayNode(args)
        else:
            return self.e9()

    def e9(self):
        t = self.current
        if self.accept('true'):
            return BooleanNode(t, True)
        if self.accept('false'):
            return BooleanNode(t, False)
        if self.accept('id'):
            return IdNode(t)
        if self.accept('number'):
            return NumberNode(t)
        if self.accept('string'):
            return StringNode(t)
        return EmptyNode(self.current.lineno, self.current.colno)

    def args(self):
        s = self.statement()
        a = ArgumentNode(s)

        while not isinstance(s, EmptyNode):
            potential = self.current
            if self.accept('comma'):
                a.commas.append(potential)
                a.append(s)
            elif self.accept('colon'):
                if not isinstance(s, IdNode):
                    raise ParseException('Keyword argument must be a plain identifier.',
                                         self.getline(), s.lineno, s.colno)
                a.set_kwarg(s.value, self.statement())
                potential = self.current
                if not self.accept('comma'):
                    return a
                a.commas.append(potential)
            else:
                a.append(s)
                return a
            s = self.statement()
        return a

    def method_call(self, source_object):
        methodname = self.e9()
        if not(isinstance(methodname, IdNode)):
            raise ParseException('Method name must be plain id',
                                 self.getline(), self.current.lineno, self.current.colno)
        self.expect('lparen')
        args = self.args()
        self.expect('rparen')
        method = MethodNode(methodname.subdir, methodname.lineno, methodname.colno, source_object, methodname.value, args)
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
        block_start = self.current
        if self.current == 'eol':
            return EmptyNode(self.current.lineno, self.current.colno)
        if self.accept('if'):
            block = self.ifblock()
            self.block_expect('endif', block_start)
            return block
        if self.accept('foreach'):
            block = self.foreachblock()
            self.block_expect('endforeach', block_start)
            return block
        return self.statement()

    def codeblock(self):
        block = CodeBlockNode(self.current)
        cond = True
        while cond:
            curline = self.line()
            if not isinstance(curline, EmptyNode):
                block.lines.append(curline)
            cond = self.accept('eol')
        return block
