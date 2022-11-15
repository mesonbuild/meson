# Copyright 2022 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This class contains the basic functionality needed to format code
import re
from .. import mparser
from . import AstVisitor
import typing as T

arithmic_map = {
    'add': '+',
    'sub': '-',
    'mod': '%',
    'mul': '*',
    'div': '/'
}

class AstFormatter(AstVisitor):
    def __init__(self, comments: T.List[mparser.Comment], lines: T.List[str], config):
        self.lines = []
        self.indentstr = config['indent_by']
        self.currindent = ''
        self.currline = ''
        self.comments = comments
        self.old_lines = lines
        self.config = config

    def end(self):
        self.lines.append(self.currline)
        for i, l in enumerate(self.lines):
            if l.strip() == '':
                self.lines[i] = ''

    def append(self, to_append):
        self.currline += to_append

    def force_linebreak(self):
        if self.currline.strip() != '':
            self.lines.append(self.currline)
            self.currline = self.currindent

    def get_length(self, node: mparser.BaseNode):
        add_extra = 0
        if isinstance(node, mparser.StringNode):
            add_extra += 2 + len(node.value)
        elif isinstance(node, mparser.MethodNode):
            add_extra += node.args.end_colno + 3
        elif isinstance(node, mparser.IdNode):
            add_extra += len(node.value)
        elif isinstance(node, (mparser.PlusAssignmentNode, mparser.AssignmentNode)):
            rhs = node.value
            if isinstance(rhs, mparser.StringNode):
                add_extra += 2 + len(rhs.value) + rhs.colno
            elif isinstance(rhs, mparser.MethodNode):
                add_extra += rhs.args.end_colno + 3
            elif isinstance(rhs, mparser.IdNode):
                add_extra += rhs.end_colno + len(rhs.value)
            elif isinstance(rhs, mparser.BooleanNode):
                add_extra += rhs.end_colno + (4 if rhs.value else 5)
            else:
                add_extra += rhs.end_colno
        elif isinstance(node, mparser.BooleanNode):
            add_extra += node.end_colno + (4 if node.value else 5)
        elif isinstance(node, mparser.ArithmeticNode):
            add_extra += self.get_length(node.right)
        else:
            add_extra += node.end_colno
        return add_extra

    def check_adjacent_comment(self, node: mparser.BaseNode, append: str):
        idx = 0
        to_readd = None
        for c in self.comments:
            if c.lineno == node.lineno and (c.lineno == node.lineno if node.end_lineno is not None else True):
                # Check if the node is really the "biggest" one, i.e. after the node on the line,
                # there is only the comment.
                # TODO: Does not seem to work all the time
                add_extra = self.get_length(node)
                diffstr = self.old_lines[c.lineno - 1][node.end_colno + add_extra:c.colno].strip()
                bound_matches = diffstr in ('', ',')
                if not bound_matches:
                    continue
                to_readd = c
                break
            idx += 1
        self.append(append)
        if to_readd is None:
            return
        self.append(' ')
        self.append(c.text)
        self.comments.remove(c)

    def check_comment(self, node: mparser.BaseNode):
        to_readd = None
        idx = 0
        tmp_lineno = node.lineno - 1
        while tmp_lineno > 0 and self.old_lines[tmp_lineno - 1].strip() == '':
            tmp_lineno -= 1
        for c in self.comments:
            if c.lineno == tmp_lineno:
                to_readd = c
                break
            if c.lineno == node.lineno - 1 and self.old_lines[c.lineno - 1].strip().startswith('#'):
                to_readd = c
                break
            idx += 1
        if to_readd is None:
            return
        block_idx = idx
        while block_idx >= 0 and self.comments[block_idx - 1].lineno + 1 == self.comments[block_idx].lineno:
            block_idx -= 1
        old_line = self.comments[block_idx].lineno
        assert block_idx <= idx
        assert old_line <= self.comments[idx].lineno
        while block_idx > 0:
            prev_comment = self.comments[block_idx - 1]
            assert prev_comment.lineno < old_line
            to_break = False
            for lidx in range(prev_comment.lineno, old_line):
                if self.old_lines[lidx].strip() == '' or self.old_lines[lidx].strip().startswith('#'):
                    continue
                to_break = True
                break
            if to_break:
                break
            block_idx -= 1
            old_line = self.comments[block_idx].lineno
            assert old_line <= self.comments[idx].lineno
        for i in range(block_idx, idx + 1):
            for x in range(old_line, self.comments[i].lineno - 1):
                self.lines.append('')
            self.lines.append(self.currindent + self.comments[i].text)
            old_line = self.comments[i].lineno
        for i in range(block_idx, idx + 1):
            self.comments.remove(self.comments[block_idx])
        for i in range(0, node.lineno - tmp_lineno - 1):
            self.lines.append('')

    def check_post_comment(self, node: mparser.BaseNode):
        to_readd = None
        idx = 0
        last_line = AstFormatter.extract_last_line(node)
        for c in self.comments:
            if c.lineno == last_line + 1 and self.old_lines[c.lineno - 1].strip().startswith('#'):
                to_readd = c
                break
            idx += 1
        if to_readd is None:
            return
        block_idx = idx
        while block_idx < len(self.comments) - 1 and self.comments[block_idx + 1].lineno == self.comments[block_idx].lineno + 1:
            block_idx += 1
        for i in range(idx, block_idx + 1):
            self.lines.append(self.currindent + self.comments[idx].text)
            del self.comments[idx]

    def eventual_linebreak(self):
        if len(self.currline.strip()) != 0:
            self.force_linebreak()

    def visit_BooleanNode(self, node: mparser.BooleanNode) -> None:
        self.append('true' if node.value else 'false')

    def visit_IdNode(self, node: mparser.IdNode) -> None:
        assert isinstance(node.value, str)
        self.append(node.value)

    def visit_NumberNode(self, node: mparser.NumberNode) -> None:
        self.append(str(node.value))

    def escape(self, val: str) -> str:
        return val.translate(str.maketrans({'\'': '\\\'',
                                            '\\': '\\\\',
                                            '\n': '\\n'}))

    def visit_StringNode(self, node: mparser.StringNode) -> None:
        assert isinstance(node.value, str)
        self.append("'" + self.escape(node.value) + "'")

    def visit_FormatStringNode(self, node: mparser.FormatStringNode) -> None:
        assert isinstance(node.value, str)
        self.append("f'" + node.value + "'")

    def visit_ContinueNode(self, node: mparser.ContinueNode) -> None:
        self.force_linebreak()
        self.append('continue')
        self.force_linebreak()

    def visit_BreakNode(self, node: mparser.BreakNode) -> None:
        self.force_linebreak()
        self.append('break')
        self.force_linebreak()

    def visit_ArrayNode(self, node: mparser.ArrayNode) -> None:
        self.append('[')
        num_elements = len(node.args.arguments)
        if self.config['space_array'] and num_elements != 0:
            self.append(' ')
        node.args.accept(self)
        if self.config['space_array'] and num_elements != 0:
            self.append(' ')
        self.append(']')

    def visit_DictNode(self, node: mparser.DictNode) -> None:
        self.append('{')
        node.args.accept(self)
        self.append('}')

    def visit_OrNode(self, node: mparser.OrNode) -> None:
        node.left.accept(self)
        self.append(' or ')
        node.right.accept(self)

    def visit_AndNode(self, node: mparser.AndNode) -> None:
        node.left.accept(self)
        self.append(' and ')
        node.right.accept(self)

    def visit_ComparisonNode(self, node: mparser.ComparisonNode) -> None:
        node.left.accept(self)
        self.append(' ' + (node.ctype if node.ctype != 'notin' else 'not in') + ' ')
        node.right.accept(self)

    def visit_ArithmeticNode(self, node: mparser.ArithmeticNode) -> None:
        node.left.accept(self)
        self.append(' ' + arithmic_map[node.operation] + ' ')
        node.right.accept(self)

    def visit_NotNode(self, node: mparser.NotNode) -> None:
        self.append('not ')
        node.value.accept(self)

    def visit_CodeBlockNode(self, node: mparser.CodeBlockNode) -> None:
        idx = 0
        lastline = -1
        self.check_comment(node)
        for i in node.lines:
            if lastline != -1:
                if i.lineno > lastline + 1 and self.old_lines[lastline + 1].strip() != ')':
                    self.lines.append(self.currline)
                    self.currline = self.currindent
            self.check_comment(i)
            i.accept(self)
            self.check_adjacent_comment(i, '')
            lastline = AstFormatter.extract_last_line(i)
            idx += 1
            if i != len(node.lines) - 1:
                self.force_linebreak()
        if len(node.lines) != 0:
            self.check_post_comment(node.lines[len(node.lines) - 1])

    def visit_IndexNode(self, node: mparser.IndexNode) -> None:
        node.iobject.accept(self)
        self.append('[')
        if self.config['space_array']:
            self.append(' ')
        node.index.accept(self)
        if self.config['space_array']:
            self.append(' ')
        self.append(']')

    def visit_ArgumentsCall(self, args: mparser.ArgumentNode) -> None:
        tmp = self.currindent
        indent_len = len(tmp) + len(self.config['indent_by'])
        self.currindent = ' ' * indent_len
        n_linebreaks = 0
        broke_up_total = False
        for i, arg in enumerate(args.arguments):
            broke_up = False
            estimated_len = 0
            if isinstance(arg, mparser.IdNode):
                estimated_len = len(arg.value)
            elif isinstance(arg, mparser.StringNode):
                estimated_len = len(arg.value) + 2
            elif isinstance(arg, mparser.NumberNode):
                estimated_len = len(str(arg.value))
            elif isinstance(arg, mparser.MethodNode) and isinstance(arg.source_object, mparser.StringNode):
                estimated_len = len(arg.source_object.value) + 2 + len(arg.name)
            if len(args.arguments) + len(args.kwargs) != 1 or len(self.currline) + estimated_len > self.config['max_line_len']:
                if len(self.currline) > self.config['max_line_len']:
                    self.force_linebreak()
                    n_linebreaks += 1
                    broke_up = True
                    broke_up_total = True
            if not broke_up and i != 0:
                self.append(' ')
            if i != 0:
                self.check_comment(arg)
            else:
                tmp2 = self.currindent
                self.currindent = tmp
                self.check_comment(arg)
                self.currindent = tmp2
            if isinstance(arg, mparser.ArrayNode) and len(args.arguments) == 1:
                self.visit_ArrayNodeAssignment(arg)
            else:
                arg.accept(self)
            if i != len(args.arguments) - 1 or len(args.kwargs) != 0:
                self.currindent = ' ' * indent_len
                self.append(',')
        max_len = 0
        for i, kwarg in enumerate(args.kwargs):
            max_len = max(max_len, len(kwarg.value))
        max_len += 1
        wide_colon = self.config['wide_colon']
        kwa_ml = self.config['kwa_ml'] or (len(args.arguments) == 0 and len(args.kwargs) > 0)
        for i, kwarg in enumerate(args.kwargs):
            broke_up = False
            if ((i == 0 and len(args.arguments) != 0) and len(args.kwargs) > 1) or kwa_ml:
                self.force_linebreak()
                n_linebreaks += 1
                broke_up = True
                broke_up_total = True
            self.check_comment(kwarg)
            self.currindent = ' ' * indent_len
            name = kwarg.value
            padding = ' ' * (max_len - len(name))
            if not wide_colon:
                padding = ''
            if not broke_up and (i == 0 and len(args.arguments) != 0):
                self.append(' ')
            self.append(name + padding + ': ')
            kw = args.kwargs[kwarg]
            if isinstance(kw, mparser.ArrayNode) and len(kw.args.arguments) != 0:
                self.visit_ArrayNodeAssignment(kw)
            else:
                kw.accept(self)
            if n_linebreaks != 0 or i < len(args.kwargs) - 1:
                self.append(',')
            if broke_up or broke_up_total:
                self.check_adjacent_comment(kw, '')
            if i == len(args.kwargs) - 1:
                self.currindent = tmp
                if n_linebreaks != 0:
                    self.force_linebreak()
            else:
                self.force_linebreak()
                n_linebreaks += 1
        self.currindent = tmp
        if len(args.arguments) + len(args.kwargs) > 1 and n_linebreaks != 0:
            self.force_linebreak()

    def visit_MethodNode(self, node: mparser.MethodNode) -> None:
        node.source_object.accept(self)
        self.append('.' + node.name + '(')
        if len(node.args.arguments) != 0 or len(node.args.kwargs) != 0:
            args = node.args
            self.visit_ArgumentsCall(args)
        self.append(')')

    def visit_FunctionNode(self, node: mparser.FunctionNode) -> None:
        self.append(node.func_name + '(')
        if len(node.args.arguments) != 0 or len(node.args.kwargs) != 0:
            args = node.args
            self.visit_ArgumentsCall(args)
        self.append(')')

    def visit_ArrayNodeAssignment(self, node: mparser.ArrayNode) -> None:
        assert isinstance(node, mparser.ArrayNode)
        if len(node.args.arguments) == 1 and node.lineno == node.end_lineno:
            node.accept(self)
            return
        self.append('[')
        tmp = self.currindent
        self.currindent = tmp + self.indentstr
        self.force_linebreak()
        for i, e in enumerate(node.args.arguments):
            self.currindent = tmp + self.indentstr
            self.check_comment(e)
            e.accept(self)
            self.check_adjacent_comment(e, ',')
            if i == len(node.args.arguments) - 1:
                self.currindent = tmp
                self.force_linebreak()
                n = len(self.comments)
                self.check_post_comment(e)
                n1 = len(self.comments)
                if n != n1:
                    for i in range(0, n - n1):
                        self.lines[-i - 1] = self.indentstr + self.lines[-i - 1]
            else:
                self.force_linebreak()
        self.append(']')
        self.currindent = tmp

    def visit_DictNodeAssignment(self, node: mparser.DictNode) -> None:
        assert isinstance(node, mparser.DictNode)
        self.append('{')
        tmp = self.currindent
        self.currindent = tmp + self.indentstr
        self.force_linebreak()
        align = 1
        for _, e in enumerate(node.args.kwargs):
            align = max(align, len(e.value))
        wide_colon = self.config['wide_colon']
        for i, e in enumerate(node.args.kwargs):
            self.currindent = tmp + self.indentstr
            self.check_comment(e)
            e.accept(self)
            if wide_colon:
                self.append(' ' * (align - len(e.value) + 1))
            self.append(': ')
            node.args.kwargs[e].accept(self)
            self.check_adjacent_comment(e, ',')
            if i == len(node.args.kwargs) - 1:
                self.currindent = tmp
            self.force_linebreak()
        self.append('}')
        self.currindent = tmp
        self.force_linebreak()

    def visit_AssignmentNode(self, node: mparser.AssignmentNode) -> None:
        self.append(node.var_name + ' = ')
        if isinstance(node.value, mparser.ArrayNode) and len(node.value.args.arguments) != 0:
            self.visit_ArrayNodeAssignment(node.value)
        elif isinstance(node.value, mparser.DictNode) and len(node.value.args.kwargs) != 0:
            self.visit_DictNodeAssignment(node.value)
        else:
            node.value.accept(self)

    def visit_PlusAssignmentNode(self, node: mparser.PlusAssignmentNode) -> None:
        self.append(node.var_name + ' += ')
        if isinstance(node.value, mparser.ArrayNode) and len(node.value.args.arguments) != 0:
            self.visit_ArrayNodeAssignment(node.value)
        elif isinstance(node.value, mparser.DictNode) and len(node.value.args.kwargs) != 0:
            self.visit_DictNodeAssignment(node.value)
        else:
            node.value.accept(self)

    def visit_ForeachClauseNode(self, node: mparser.ForeachClauseNode) -> None:
        self.eventual_linebreak()
        varnames = list(node.varnames)
        tmp = self.currindent
        self.check_comment(node)
        self.append('foreach ')
        self.append(', '.join(varnames))
        self.append(' : ')
        if isinstance(node.items, mparser.ArrayNode) and len(node.items.args.arguments) != 0:
            self.currindent += self.indentstr
            self.visit_ArrayNodeAssignment(node.items)
            self.currindent = tmp
        elif isinstance(node.items, mparser.DictNode) and len(node.items.args.kwargs) != 0:
            self.currindent += self.indentstr
            self.visit_DictNodeAssignment(node.items)
            self.currindent = tmp
        else:
            node.items.accept(self)
        self.currindent += self.indentstr
        self.force_linebreak()
        node.block.accept(self)
        self.currindent = tmp
        self.force_linebreak()
        self.currline = self.currindent
        self.append('endforeach')

    def visit_IfClauseNode(self, node: mparser.IfClauseNode) -> None:
        prefix = ''
        tmp = self.currindent
        for i in node.ifs:
            self.check_comment(i)
            self.currindent = tmp
            self.currline = self.currindent
            self.append(prefix + 'if ')
            prefix = 'el'
            i.accept(self)
            self.currindent = tmp
            self.currline = self.currindent
        if not isinstance(node.elseblock, mparser.EmptyNode):
            self.check_comment(node.elseblock)
            self.append('else')
            self.currindent += self.indentstr
            self.force_linebreak()
            node.elseblock.accept(self)
            self.currindent = tmp
            self.force_linebreak()
        self.currindent = tmp
        self.currline = self.currindent
        self.append('endif')

    @staticmethod
    def extract_last_line(node: mparser.BaseNode) -> int:
        if isinstance(node, mparser.IfClauseNode):
            if not isinstance(node.elseblock, mparser.EmptyNode):
                return AstFormatter.extract_last_line(node.elseblock) + 1
            return AstFormatter.extract_last_line(node.ifs[-1].block) + 1
        elif isinstance(node, mparser.ForeachClauseNode):
            return AstFormatter.extract_last_line(node.block) + 1
        elif isinstance(node, mparser.CodeBlockNode):
            if len(node.lines) != 0:
                return max(AstFormatter.extract_last_line(node.lines[-1]), node.end_lineno)
        elif isinstance(node, (mparser.AssignmentNode, mparser.PlusAssignmentNode)):
            return AstFormatter.extract_last_line(node.value)
        elif isinstance(node, mparser.MethodNode):
            return AstFormatter.extract_last_line(node.args)
        elif isinstance(node, mparser.ArgumentNode):
            max_line = node.end_lineno
            for arg in node.arguments:
                max_line = max(max_line, AstFormatter.extract_last_line(arg))
            for key, val in node.kwargs.items():
                max_line = max(max_line, AstFormatter.extract_last_line(val))
            return max_line
        return node.end_lineno

    def visit_UMinusNode(self, node: mparser.UMinusNode) -> None:
        self.append('-')
        node.value.accept(self)

    def visit_IfNode(self, node: mparser.IfNode) -> None:
        self.check_comment(node)
        node.condition.accept(self)
        tmp = self.currindent
        self.currindent += self.indentstr
        self.force_linebreak()
        node.block.accept(self)
        self.currindent = tmp

    def visit_TernaryNode(self, node: mparser.TernaryNode) -> None:
        node.condition.accept(self)
        self.append(' ? ')
        node.trueblock.accept(self)
        self.append(' : ')
        node.falseblock.accept(self)

    def visit_ArgumentNode(self, node: mparser.ArgumentNode) -> None:
        for i in node.arguments:
            i.accept(self)
            self.append(', ')
        wide_colon = self.config['wide_colon']
        tmp = self.currindent
        self.currindent += self.indentstr
        idx = 0
        for key, val in node.kwargs.items():
            self.force_linebreak()
            self.check_comment(key)
            key.accept(self)
            if not wide_colon:
                self.append(': ')
            else:
                self.append(' : ')
            val.accept(self)
            if idx == len(node.kwargs) - 1:
                self.currindent = tmp
                self.force_linebreak()
            else:
                self.append(',')
            idx += 1
        self.currindent = tmp
        self.currline = re.sub(r', $', '', self.currline)

    def visit_ParenthesizedNode(self, node: mparser.ParenthesizedNode) -> None:
        self.append('(')
        node.inner.accept(self)
        self.append(')')
