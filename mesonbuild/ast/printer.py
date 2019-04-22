# Copyright 2019 The Meson development team

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
import re

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
        self.ci = ''
        self.is_newline = True
        self.last_level = 0

    def post_process(self):
        self.result = re.sub(r'\s+\n', '\n', self.result)

    def append(self, data: str, node: mparser.BaseNode):
        level = 0
        if node and hasattr(node, 'level'):
            level = node.level
        else:
            level = self.last_level
        self.last_level = level
        if self.is_newline:
            self.result += ' ' * (level * self.indent)
        self.result += data
        self.is_newline = False

    def append_padded(self, data: str, node: mparser.BaseNode):
        if self.result[-1] not in [' ', '\n']:
            data = ' ' + data
        self.append(data + ' ', node)

    def newline(self):
        self.result += '\n'
        self.is_newline = True

    def visit_BooleanNode(self, node: mparser.BooleanNode):
        self.append('true' if node.value else 'false', node)

    def visit_IdNode(self, node: mparser.IdNode):
        self.append(node.value, node)

    def visit_NumberNode(self, node: mparser.NumberNode):
        self.append(str(node.value), node)

    def visit_StringNode(self, node: mparser.StringNode):
        self.append("'" + node.value + "'", node)

    def visit_ContinueNode(self, node: mparser.ContinueNode):
        self.append('continue', node)

    def visit_BreakNode(self, node: mparser.BreakNode):
        self.append('break', node)

    def visit_ArrayNode(self, node: mparser.ArrayNode):
        self.append('[', node)
        node.args.accept(self)
        self.append(']', node)

    def visit_DictNode(self, node: mparser.DictNode):
        self.append('{', node)
        node.args.accept(self)
        self.append('}', node)

    def visit_OrNode(self, node: mparser.OrNode):
        node.left.accept(self)
        self.append_padded('or', node)
        node.right.accept(self)

    def visit_AndNode(self, node: mparser.AndNode):
        node.left.accept(self)
        self.append_padded('and', node)
        node.right.accept(self)

    def visit_ComparisonNode(self, node: mparser.ComparisonNode):
        node.left.accept(self)
        self.append_padded(mparser.comparison_map[node.ctype], node)
        node.right.accept(self)

    def visit_ArithmeticNode(self, node: mparser.ArithmeticNode):
        node.left.accept(self)
        self.append_padded(arithmic_map[node.operation], node)
        node.right.accept(self)

    def visit_NotNode(self, node: mparser.NotNode):
        self.append_padded('not', node)
        node.value.accept(self)

    def visit_CodeBlockNode(self, node: mparser.CodeBlockNode):
        for i in node.lines:
            i.accept(self)
            self.newline()

    def visit_IndexNode(self, node: mparser.IndexNode):
        self.append('[', node)
        node.index.accept(self)
        self.append(']', node)

    def visit_MethodNode(self, node: mparser.MethodNode):
        node.source_object.accept(self)
        self.append('.' + node.name + '(', node)
        node.args.accept(self)
        self.append(')', node)

    def visit_FunctionNode(self, node: mparser.FunctionNode):
        self.append(node.func_name + '(', node)
        node.args.accept(self)
        self.append(')', node)

    def visit_AssignmentNode(self, node: mparser.AssignmentNode):
        self.append(node.var_name + ' = ', node)
        node.value.accept(self)

    def visit_PlusAssignmentNode(self, node: mparser.PlusAssignmentNode):
        self.append(node.var_name + ' += ', node)
        node.value.accept(self)

    def visit_ForeachClauseNode(self, node: mparser.ForeachClauseNode):
        varnames = [x.value for x in node.varnames]
        self.append_padded('foreach', node)
        self.append_padded(', '.join(varnames), node)
        self.append_padded(':', node)
        node.items.accept(self)
        self.newline()
        node.block.accept(self)
        self.append('endforeach', node)

    def visit_IfClauseNode(self, node: mparser.IfClauseNode):
        prefix = ''
        for i in node.ifs:
            self.append_padded(prefix + 'if', node)
            prefix = 'el'
            i.accept(self)
        if node.elseblock:
            self.append('else', node)
            node.elseblock.accept(self)
        self.append('endif', node)

    def visit_UMinusNode(self, node: mparser.UMinusNode):
        self.append_padded('-', node)
        node.value.accept(self)

    def visit_IfNode(self, node: mparser.IfNode):
        node.condition.accept(self)
        self.newline()
        node.block.accept(self)

    def visit_TernaryNode(self, node: mparser.TernaryNode):
        node.condition.accept(self)
        self.append_padded('?', node)
        node.trueblock.accept(self)
        self.append_padded(':', node)
        node.falseblock.accept(self)

    def visit_ArgumentNode(self, node: mparser.ArgumentNode):
        break_args = (len(node.arguments) + len(node.kwargs)) > self.arg_newline_cutoff
        for i in node.arguments + list(node.kwargs.values()):
            if not isinstance(i, mparser.ElementaryNode):
                break_args = True
        if break_args:
            self.newline()
        for i in node.arguments:
            i.accept(self)
            self.append(', ', node)
            if break_args:
                self.newline()
        for key, val in node.kwargs.items():
            self.append(key, node)
            self.append_padded(':', node)
            val.accept(self)
            self.append(', ', node)
            if break_args:
                self.newline()
        if break_args:
            self.result = re.sub(r', \n$', '\n', self.result)
        else:
            self.result = re.sub(r', $', '', self.result)
