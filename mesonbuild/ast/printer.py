# Copyright 2018 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This class contains the basic functionality needed to run any interpreter
# or an interpreter-based tool

from .. import mparser
from . import AstVisitor

arithmic_map = {
    'add': '+',
    'sub': '-',
    'mod': '%',
    'mul': '*',
    'div': '/'
}

class AstPrinter(AstVisitor):
    def __init__(self, indent: int = 2, arg_newline_cutoff: int = 5):
        self.result = ''
        self.indent = indent
        self.arg_newline_cutoff = arg_newline_cutoff
        self.level = 0
        self.ci = ''
        self.is_newline = True

    def inc_indent(self):
        self.level += self.indent

    def dec_indent(self):
        self.level -= self.indent

    def append(self, data: str):
        if self.is_newline:
            self.result += ' ' * self.level
        self.result += data
        self.is_newline = False

    def appendS(self, data: str):
        if self.result[-1] not in [' ', '\n']:
            data = ' ' + data
        self.append(data + ' ')

    def newline(self):
        self.result += '\n'
        self.is_newline = True

    def visit_BooleanNode(self, node: mparser.BooleanNode):
        self.append('true' if node.value else 'false')

    def visit_IdNode(self, node: mparser.IdNode):
        self.append(node.value)

    def visit_NumberNode(self, node: mparser.NumberNode):
        self.append(str(node.value))

    def visit_StringNode(self, node: mparser.StringNode):
        self.append("'" + node.value + "'")

    def visit_ContinueNode(self, node: mparser.ContinueNode):
        self.append('continue')

    def visit_BreakNode(self, node: mparser.BreakNode):
        self.append('break')

    def visit_ArrayNode(self, node: mparser.ArrayNode):
        self.append('[')
        self.inc_indent()
        node.args.accept(self)
        self.dec_indent()
        self.append(']')

    def visit_DictNode(self, node: mparser.DictNode):
        self.append('{')
        self.inc_indent()
        node.args.accept(self)
        self.dec_indent()
        self.append('}')

    def visit_OrNode(self, node: mparser.OrNode):
        node.left.accept(self)
        self.appendS('or')
        node.right.accept(self)

    def visit_AndNode(self, node: mparser.AndNode):
        node.left.accept(self)
        self.appendS('and')
        node.right.accept(self)

    def visit_ComparisonNode(self, node: mparser.ComparisonNode):
        node.left.accept(self)
        self.appendS(mparser.comparison_map[node.ctype])
        node.right.accept(self)

    def visit_ArithmeticNode(self, node: mparser.ArithmeticNode):
        node.left.accept(self)
        self.appendS(arithmic_map[node.operation])
        node.right.accept(self)

    def visit_NotNode(self, node: mparser.NotNode):
        self.appendS('not')
        node.value.accept(self)

    def visit_CodeBlockNode(self, node: mparser.CodeBlockNode):
        for i in node.lines:
            i.accept(self)
            self.newline()

    def visit_IndexNode(self, node: mparser.IndexNode):
        self.append('[')
        node.index.accept(self)
        self.append(']')

    def visit_MethodNode(self, node: mparser.MethodNode):
        node.source_object.accept(self)
        self.append('.' + node.name + '(')
        self.inc_indent()
        node.args.accept(self)
        self.dec_indent()
        self.append(')')

    def visit_FunctionNode(self, node: mparser.FunctionNode):
        self.append(node.func_name + '(')
        self.inc_indent()
        node.args.accept(self)
        self.dec_indent()
        self.append(')')

    def visit_AssignmentNode(self, node: mparser.AssignmentNode):
        self.append(node.var_name + ' = ')
        node.value.accept(self)

    def visit_PlusAssignmentNode(self, node: mparser.PlusAssignmentNode):
        self.append(node.var_name + ' += ')
        node.value.accept(self)

    def visit_ForeachClauseNode(self, node: mparser.ForeachClauseNode):
        varnames = [x.value for x in node.varnames]
        self.appendS('foreach')
        self.appendS(', '.join(varnames))
        self.appendS(':')
        node.items.accept(self)
        self.newline()
        self.inc_indent()
        node.block.accept(self)
        self.dec_indent()
        self.append('endforeach')

    def visit_IfClauseNode(self, node: mparser.IfClauseNode):
        prefix = ''
        for i in node.ifs:
            self.appendS(prefix + 'if')
            prefix = 'el'
            i.accept(self)
        if node.elseblock:
            self.append('else')
            self.indent()
            self.inc_indent()
            node.elseblock.accept(self)
            self.dec_indent()
        self.append('endif')

    def visit_UMinusNode(self, node: mparser.UMinusNode):
        self.appendS('-')
        node.value.accept(self)

    def visit_IfNode(self, node: mparser.IfNode):
        node.condition.accept(self)
        self.newline()
        self.inc_indent()
        node.block.accept(self)
        self.dec_indent()

    def visit_TernaryNode(self, node: mparser.TernaryNode):
        node.condition.accept(self)
        self.appendS('?')
        node.trueblock.accept(self)
        self.appendS(':')
        node.falseblock.accept(self)

    def visit_ArgumentNode(self, node: mparser.ArgumentNode):
        break_args = True if (len(node.arguments) + len(node.kwargs)) > self.arg_newline_cutoff else False
        for i in node.arguments + list(node.kwargs.values()):
            if not isinstance(i, mparser.ElementaryNode):
                break_args = True
        if break_args:
            self.newline()
        for i in node.arguments:
            i.accept(self)
            self.append(',')
            if break_args:
                self.newline()
        for key, val in node.kwargs.items():
            self.append(key)
            self.appendS(':')
            val.accept(self)
            self.append(',')
            if break_args:
                self.newline()
