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

class AstVisitor:
    def __init__(self):
        pass

    def visit_default_func(self, node: mparser.BaseNode):
        pass

    def visit_BooleanNode(self, node: mparser.BooleanNode):
        self.visit_default_func(node)

    def visit_IdNode(self, node: mparser.IdNode):
        self.visit_default_func(node)

    def visit_NumberNode(self, node: mparser.NumberNode):
        self.visit_default_func(node)

    def visit_StringNode(self, node: mparser.StringNode):
        self.visit_default_func(node)

    def visit_ContinueNode(self, node: mparser.ContinueNode):
        self.visit_default_func(node)

    def visit_BreakNode(self, node: mparser.BreakNode):
        self.visit_default_func(node)

    def visit_ArrayNode(self, node: mparser.ArrayNode):
        self.visit_default_func(node)
        node.args.accept(self)

    def visit_DictNode(self, node: mparser.DictNode):
        self.visit_default_func(node)
        node.args.accept(self)

    def visit_EmptyNode(self, node: mparser.EmptyNode):
        self.visit_default_func(node)

    def visit_OrNode(self, node: mparser.OrNode):
        self.visit_default_func(node)
        node.left.accept(self)
        node.right.accept(self)

    def visit_AndNode(self, node: mparser.AndNode):
        self.visit_default_func(node)
        node.left.accept(self)
        node.right.accept(self)

    def visit_ComparisonNode(self, node: mparser.ComparisonNode):
        self.visit_default_func(node)
        node.left.accept(self)
        node.right.accept(self)

    def visit_ArithmeticNode(self, node: mparser.ArithmeticNode):
        self.visit_default_func(node)
        node.left.accept(self)
        node.right.accept(self)

    def visit_NotNode(self, node: mparser.NotNode):
        self.visit_default_func(node)
        node.value.accept(self)

    def visit_CodeBlockNode(self, node: mparser.CodeBlockNode):
        self.visit_default_func(node)
        for i in node.lines:
            i.accept(self)

    def visit_IndexNode(self, node: mparser.IndexNode):
        self.visit_default_func(node)
        node.index.accept(self)

    def visit_MethodNode(self, node: mparser.MethodNode):
        self.visit_default_func(node)
        node.source_object.accept(self)
        node.args.accept(self)

    def visit_FunctionNode(self, node: mparser.FunctionNode):
        self.visit_default_func(node)
        node.args.accept(self)

    def visit_AssignmentNode(self, node: mparser.AssignmentNode):
        self.visit_default_func(node)
        node.value.accept(self)

    def visit_PlusAssignmentNode(self, node: mparser.PlusAssignmentNode):
        self.visit_default_func(node)
        node.value.accept(self)

    def visit_ForeachClauseNode(self, node: mparser.ForeachClauseNode):
        self.visit_default_func(node)
        node.items.accept(self)
        node.block.accept(self)

    def visit_IfClauseNode(self, node: mparser.IfClauseNode):
        self.visit_default_func(node)
        for i in node.ifs:
            i.accept(self)
        if node.elseblock:
            node.elseblock.accept(self)

    def visit_UMinusNode(self, node: mparser.UMinusNode):
        self.visit_default_func(node)
        node.value.accept(self)

    def visit_IfNode(self, node: mparser.IfNode):
        self.visit_default_func(node)
        node.condition.accept(self)
        node.block.accept(self)

    def visit_TernaryNode(self, node: mparser.TernaryNode):
        self.visit_default_func(node)
        node.condition.accept(self)
        node.trueblock.accept(self)
        node.falseblock.accept(self)

    def visit_ArgumentNode(self, node: mparser.ArgumentNode):
        self.visit_default_func(node)
        for i in node.arguments:
            i.accept(self)
        for val in node.kwargs.values():
            val.accept(self)
