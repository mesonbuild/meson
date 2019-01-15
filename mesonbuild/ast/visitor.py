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

class AstVisitor:
    def __init__(self):
        pass

    def visit_BooleanNode(self, node: mparser.BooleanNode):
        pass

    def visit_IdNode(self, node: mparser.IdNode):
        pass

    def visit_NumberNode(self, node: mparser.NumberNode):
        pass

    def visit_StringNode(self, node: mparser.StringNode):
        pass

    def visit_ContinueNode(self, node: mparser.ContinueNode):
        pass

    def visit_BreakNode(self, node: mparser.BreakNode):
        pass

    def visit_ArrayNode(self, node: mparser.ArrayNode):
        node.args.accept(self)

    def visit_DictNode(self, node: mparser.DictNode):
        node.args.accept(self)

    def visit_EmptyNode(self, node: mparser.EmptyNode):
        pass

    def visit_OrNode(self, node: mparser.OrNode):
        node.left.accept(self)
        node.right.accept(self)

    def visit_AndNode(self, node: mparser.AndNode):
        node.left.accept(self)
        node.right.accept(self)

    def visit_ComparisonNode(self, node: mparser.ComparisonNode):
        node.left.accept(self)
        node.right.accept(self)

    def visit_ArithmeticNode(self, node: mparser.ArithmeticNode):
        node.left.accept(self)
        node.right.accept(self)

    def visit_NotNode(self, node: mparser.NotNode):
        node.value.accept(self)

    def visit_CodeBlockNode(self, node: mparser.CodeBlockNode):
        for i in node.lines:
            i.accept(self)

    def visit_IndexNode(self, node: mparser.IndexNode):
        node.index.accept(self)

    def visit_MethodNode(self, node: mparser.MethodNode):
        node.source_object.accept(self)
        node.args.accept(self)

    def visit_FunctionNode(self, node: mparser.FunctionNode):
        node.args.accept(self)

    def visit_AssignmentNode(self, node: mparser.AssignmentNode):
        node.value.accept(self)

    def visit_PlusAssignmentNode(self, node: mparser.PlusAssignmentNode):
        node.value.accept(self)

    def visit_ForeachClauseNode(self, node: mparser.ForeachClauseNode):
        node.items.accept(self)
        node.block.accept(self)

    def visit_IfClauseNode(self, node: mparser.IfClauseNode):
        for i in node.ifs:
            i.accept(self)
        if node.elseblock:
            node.elseblock.accept(self)

    def visit_UMinusNode(self, node: mparser.UMinusNode):
        node.value.accept(self)

    def visit_IfNode(self, node: mparser.IfNode):
        node.condition.accept(self)
        node.block.accept(self)

    def visit_TernaryNode(self, node: mparser.TernaryNode):
        node.condition.accept(self)
        node.trueblock.accept(self)
        node.falseblock.accept(self)

    def visit_ArgumentNode(self, node: mparser.ArgumentNode):
        for i in node.arguments:
            i.accept(self)
        for i in node.commas:
            pass
        for val in node.kwargs.values():
            val.accept(self)
