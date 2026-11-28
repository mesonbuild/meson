# SPDX-License-Identifier: Apache-2.0
# Copyright 2024 The Meson development team

from __future__ import annotations

import difflib
import re
import typing as T
from configparser import ConfigParser, MissingSectionHeaderError, ParsingError
from copy import deepcopy
from dataclasses import dataclass, field, fields, asdict, replace
from functools import partial
from pathlib import Path
import sys

from . import mparser
from .mesonlib import MesonException, pathname_sort_key
from .ast.postprocess import AstConditionLevel
from .ast.printer import RawPrinter
from .ast.visitor import FullAstVisitor
from .environment import build_filename

if T.TYPE_CHECKING:
    import argparse
    from typing_extensions import Literal


class DefaultConfigParser(ConfigParser):

    def __init__(self, delimiters: T.Tuple[str, ...] = ('=', ':')):
        super().__init__(delimiters=delimiters, interpolation=None)

    def read_default(self, filename: Path) -> None:
        if not filename.exists():
            raise MesonException(f'Configuration file {filename} not found')
        try:
            super().read(filename, encoding='utf-8')
        except MissingSectionHeaderError:
            self.read_string(f'[{self.default_section}]\n' + filename.read_text(encoding='utf-8'))

    def getstr(self, section: str, key: str, fallback: T.Optional[str] = None) -> T.Optional[str]:
        value: T.Optional[str] = self.get(section, key, fallback=fallback)
        if value:
            value = value.strip('"').strip("'")
        return value


# "# fmt: off|on" is accepted for compatibility with muon
FORMAT_DIRECTIVE = re.compile(r'^\s*#\s*(?:meson-format\s+|fmt:\s*)(off|on)\s*$')


class FormatDirectiveFinder(FullAstVisitor):
    '''Collect "# meson-format off|on" and "# fmt: off|on" comments standing on their own line'''

    def __init__(self) -> None:
        self.depth = 0
        self.directives: list[tuple[int, str]] = []

    def visit_SymbolNode(self, node: mparser.SymbolNode) -> None:
        if node.value in {')', ']', '}'}:
            self.depth -= 1
        elif node.value in {'(', '[', '{'}:
            self.depth += 1
        super().visit_SymbolNode(node)

    def visit_WhitespaceNode(self, node: mparser.WhitespaceNode) -> None:
        for i, line in enumerate(node.value.split('\n')):
            m = FORMAT_DIRECTIVE.match(line)
            if not m:
                continue
            lineno = node.lineno + i
            colno = line.index('#') + (node.colno if i == 0 else 0)
            if i == 0 and node.colno != 0:
                raise MesonException(f'"{line.strip()}" directive must be on its own line',
                                     file=node.filename, lineno=lineno, colno=colno)
            if self.depth:
                raise MesonException(f'"{line.strip()}" directive must enclose whole statements, '
                                     'it cannot be inside parentheses, brackets or braces',
                                     file=node.filename, lineno=lineno, colno=colno)
            self.directives.append((lineno - 1, m.group(1)))


def find_format_directives(ast: mparser.BaseNode) -> list[tuple[int, str]]:
    finder = FormatDirectiveFinder()
    ast.accept(finder)
    return sorted(finder.directives)


def restore_disabled_regions(code: str, orig_directives: list[tuple[int, str]],
                             formatted: str, fmt_directives: list[tuple[int, str]]) -> str:
    '''Replace regions between "# meson-format off" and "# meson-format on"
    directives in the formatted code with the original code.'''
    orig_lines = code.splitlines(keepends=True)
    fmt_lines = formatted.splitlines(keepends=True)
    if [k for _, k in orig_directives] != [k for _, k in fmt_directives]:
        raise MesonException('format directives were moved by the formatter; '
                             'they must be on their own line and enclose whole statements')

    result: list[str] = []
    enabled = True
    fmt_pos = 0
    off_pos = 0
    for (orig_idx, kind), (fmt_idx, _) in zip(orig_directives, fmt_directives):
        if kind == 'off' and enabled:
            result += fmt_lines[fmt_pos:fmt_idx + 1]
            off_pos = orig_idx + 1
            enabled = False
        elif kind == 'on' and not enabled:
            result += orig_lines[off_pos:orig_idx]
            fmt_pos = fmt_idx
            enabled = True

    if enabled:
        result += fmt_lines[fmt_pos:]
    else:
        result += orig_lines[off_pos:]
    return ''.join(result)


def match_path(filename: str, pattern: str) -> bool:
    '''recursive glob match for editorconfig sections'''
    index = 0
    num_ranges: T.List[T.Tuple[int, int]] = []

    def curl_replace(m: re.Match) -> str:
        nonlocal index

        if '\\.\\.' in m[1]:
            index += 1
            low, high = m[1].split('\\.\\.')
            num_ranges.append((int(low), int(high)))
            return f'(?P<num{index}>-?[0-9]+)'
        else:
            return T.cast(str, m[1].replace(',', '|'))

    pattern_re = pattern.replace('.', '\\.')
    pattern_re = re.sub(r'(?<!\\)\?', '.', pattern_re)  # ? -> .
    pattern_re = re.sub(r'(?<![\\\*])\*(?!\*)', '([^/]*)', pattern_re)  # * -> ([^/]*)
    pattern_re = re.sub(r'(?<!\\)\*\*', '(.*)', pattern_re)  # ** -> (.*)
    pattern_re = re.sub(r'(?<!\\)\[!(.*?[^\\])\]', r'([^\1])', pattern_re)  # [!name] -> [^name]
    pattern_re = re.sub(r'(?<!\\)\{(.*?[^\\])}', curl_replace, pattern_re)  # {}
    if pattern.startswith('/'):
        pattern_re = '^' + pattern_re
    pattern_re += '$'

    m = re.search(pattern_re, filename)
    if m is None:
        return False

    for i in range(index):
        try:
            val = int(m[f'num{i+1}'])
            if not num_ranges[i][0] <= val <= num_ranges[i][1]:
                return False
        except ValueError:
            return False

    return True


@dataclass
class EditorConfig:

    # FIXME: these literals are not type-checked

    indent_style: T.Optional[Literal['space', 'tab']] = field(default=None, metadata={'getter': DefaultConfigParser.get})
    indent_size: T.Optional[int] = field(default=None, metadata={'getter': DefaultConfigParser.getint})
    tab_width: T.Optional[int] = field(default=None, metadata={'getter': DefaultConfigParser.getint})
    end_of_line: T.Optional[Literal['lf', 'cr', 'crlf']] = field(default=None, metadata={'getter': DefaultConfigParser.get})
    charset: T.Optional[Literal['latin1', 'utf-8', 'utf-8-bom', 'utf-16be', 'utf-16le']] = field(default=None, metadata={'getter': DefaultConfigParser.get})
    trim_trailing_whitespace: T.Optional[bool] = field(default=None, metadata={'getter': DefaultConfigParser.getboolean})
    insert_final_newline: T.Optional[bool] = field(default=None, metadata={'getter': DefaultConfigParser.getboolean})
    max_line_length: T.Optional[T.Union[Literal['off'], int]] = field(default=None, metadata={'getter': DefaultConfigParser.get})


@dataclass
class FormatterConfig:

    # Config keys compatible with muon
    max_line_length: T.Optional[int] = field(
        default=None,
        metadata={'getter': DefaultConfigParser.getint,
                  'default': 80,
                  })
    indent_by: T.Optional[str] = field(
        default=None,
        metadata={'getter': DefaultConfigParser.getstr,
                  'default': '    ',
                  })
    space_array: T.Optional[bool] = field(
        default=None,
        metadata={'getter': DefaultConfigParser.getboolean,
                  'default': False,
                  })
    kwargs_force_multiline: T.Optional[bool] = field(
        default=None,  # kwa_ml
        metadata={'getter': DefaultConfigParser.getboolean,
                  'default': False,
                  })
    wide_colon: T.Optional[bool] = field(
        default=None,
        metadata={'getter': DefaultConfigParser.getboolean,
                  'default': False,
                  })
    no_single_comma_function: T.Optional[bool] = field(
        default=None,
        metadata={'getter': DefaultConfigParser.getboolean,
                  'default': False,
                  })

    # Additional config keys
    end_of_line: T.Optional[Literal['cr', 'lf', 'crlf', 'native']] = field(
        default=None,
        metadata={'getter': DefaultConfigParser.getstr,
                  'default': 'native',
                  })
    indent_before_comments: T.Optional[str] = field(
        default=None,
        metadata={'getter': DefaultConfigParser.getstr,
                  'default': '  ',
                  })
    simplify_string_literals: T.Optional[bool] = field(
        default=None,
        metadata={'getter': DefaultConfigParser.getboolean,
                  'default': True,
                  })
    insert_final_newline: T.Optional[bool] = field(
        default=None,
        metadata={'getter': DefaultConfigParser.getboolean,
                  'default': True,
                  })
    tab_width: T.Optional[int] = field(
        default=None,
        metadata={'getter': DefaultConfigParser.getint,
                  'default': 4,
                  }
    )
    sort_files: T.Optional[bool] = field(
        default=None,
        metadata={'getter': DefaultConfigParser.getboolean,
                  'default': False,
                  })
    group_arg_value: T.Optional[bool] = field(
        default=None,
        metadata={'getter': DefaultConfigParser.getboolean,
                  'default': False,
                  })
    use_editor_config: T.Optional[bool] = field(
        default=None,
        metadata={'getter': DefaultConfigParser.getboolean,
                  'default': False,
                  })
    sticky_parens: T.Optional[bool] = field(
        default=None,
        metadata={'getter': DefaultConfigParser.getboolean,
                  'default': False,
                  })

    @property
    def paren_levels(self) -> int:
        """Number of indentation levels for continuation lines in multiline parentheses"""
        return 2 if self.sticky_parens else 1

    @classmethod
    def default(cls) -> FormatterConfig:
        defaults = {f.name: f.metadata['default'] for f in fields(cls)}
        return cls(**defaults)

    def update(self, config: FormatterConfig) -> FormatterConfig:
        """Returns copy of self updated with other config"""
        new_config = deepcopy(self)
        for key, value in asdict(config).items():
            if value is not None:
                setattr(new_config, key, value)
        return new_config

    def with_editorconfig(self, editorconfig: EditorConfig) -> FormatterConfig:
        """Returns copy of self updated with editorconfig"""
        config = deepcopy(self)

        if editorconfig.indent_style == 'space':
            indent_size = editorconfig.indent_size or 4
            config.indent_by = indent_size * ' '
        elif editorconfig.indent_style == 'tab':
            config.indent_by = '\t'
        elif editorconfig.indent_size:
            config.indent_by = editorconfig.indent_size * ' '

        if editorconfig.max_line_length == 'off':
            config.max_line_length = None
        elif editorconfig.max_line_length:
            config.max_line_length = int(editorconfig.max_line_length)

        if editorconfig.end_of_line:
            config.end_of_line = editorconfig.end_of_line
        if editorconfig.insert_final_newline:
            config.insert_final_newline = editorconfig.insert_final_newline
        if editorconfig.tab_width:
            config.tab_width = editorconfig.tab_width

        return config

    @property
    def newline(self) -> T.Optional[str]:
        if self.end_of_line == 'crlf':
            return '\r\n'
        if self.end_of_line == 'lf':
            return '\n'
        if self.end_of_line == 'cr':
            return '\r'
        return None


class MultilineArgumentDetector(FullAstVisitor):

    def __init__(self, config: FormatterConfig):
        self.config = config
        self.is_multiline = False

    def enter_node(self, node: mparser.BaseNode) -> None:
        if node.whitespaces and '#' in node.whitespaces.value:
            self.is_multiline = True

        elif isinstance(node, mparser.StringNode) and node.is_multiline:
            self.is_multiline = True

    def visit_ArgumentNode(self, node: mparser.ArgumentNode) -> None:
        if node.is_multiline:
            self.is_multiline = True

        nargs = len(node)
        if nargs and nargs == len(node.commas):
            self.is_multiline = True

        if self.is_multiline:
            return

        if self.config.kwargs_force_multiline and node.kwargs:
            self.is_multiline = True

        super().visit_ArgumentNode(node)


class MultilineParenthesesDetector(FullAstVisitor):

    def __init__(self) -> None:
        self.last_whitespaces: T.Optional[mparser.WhitespaceNode] = None

    def enter_node(self, node: mparser.BaseNode) -> None:
        self.last_whitespaces = None

    def exit_node(self, node: mparser.BaseNode) -> None:
        if node.whitespaces and node.whitespaces.value:
            self.last_whitespaces = node.whitespaces

    @classmethod
    def ends_with(cls, node: mparser.BaseNode, text: str) -> bool:
        detector = cls()
        node.accept(detector)
        return detector.last_whitespaces is not None and text in detector.last_whitespaces.value

    @classmethod
    def operators_contain(cls, node: mparser.BaseNode, text: str,
                          operators: T.Tuple[T.Type[mparser.BinaryOperatorNode], ...] = (mparser.OrNode, mparser.AndNode)) -> bool:
        """Detect text in whitespaces between operands of a chain of operators"""
        if isinstance(node, operators):
            return (cls.operators_contain(node.left, text, operators)
                    or (node.operator.whitespaces and text in node.operator.whitespaces.value)
                    or cls.operators_contain(node.right, text, operators))
        return cls.ends_with(node, text)


class TrimWhitespaces(FullAstVisitor):

    def __init__(self, config: FormatterConfig):
        self.config = config

        self.in_block_comments = False
        self.in_arguments = 0

    def visit_default_func(self, node: mparser.BaseNode) -> None:
        self.enter_node(node)
        node.whitespaces.accept(self)

    def enter_node(self, node: mparser.BaseNode) -> None:
        if isinstance(node, mparser.WhitespaceNode):
            return
        if not node.whitespaces:
            # Ensure every node has a whitespace node
            node.whitespaces = mparser.WhitespaceNode(mparser.Token('whitespace', node.filename, 0, 0, 0, (0, 0), ''))
            node.whitespaces.condition_level = node.condition_level

    def exit_node(self, node: mparser.BaseNode) -> None:
        pass

    def move_whitespaces(self, from_node: mparser.BaseNode, to_node: mparser.BaseNode) -> None:
        to_node.whitespaces.value = from_node.whitespaces.value + to_node.whitespaces.value
        to_node.whitespaces.is_continuation = from_node.whitespaces.is_continuation
        from_node.whitespaces = None
        to_node.whitespaces.accept(self)

    def add_space_after(self, node: mparser.BaseNode) -> None:
        if not node.whitespaces.value:
            node.whitespaces.value = ' '
        elif '#' not in node.whitespaces.value:
            node.whitespaces.value = ' '

    def add_nl_after(self, node: mparser.BaseNode, force: bool = False) -> None:
        if not node.whitespaces.value:
            node.whitespaces.value = '\n'
        elif force and not node.whitespaces.value.endswith('\n'):
            node.whitespaces.value += '\n'

    def sort_arguments(self, node: mparser.ArgumentNode) -> None:
        def sort_key(arg: mparser.BaseNode) -> tuple[tuple[bool, tuple[int | str, ...]], ...]:
            if isinstance(arg, mparser.StringNode):
                val = arg.raw_value
            else:
                val = getattr(node, 'value', '')
            return pathname_sort_key(val)

        node.arguments.sort(key=sort_key)

    def visit_EmptyNode(self, node: mparser.EmptyNode) -> None:
        self.enter_node(node)
        self.in_block_comments = True
        node.whitespaces.accept(self)
        self.in_block_comments = False

    def visit_WhitespaceNode(self, node: mparser.WhitespaceNode) -> None:
        lines = node.value.splitlines(keepends=True)
        node.value = ''
        in_block_comments = self.in_block_comments
        with_comments = ['#' in line for line in lines] + [False]
        for i, line in enumerate(lines):
            has_nl = line.endswith('\n')
            line = line.strip()
            if line.startswith('\\'):
                node.value += ' '  # add space before \
                node.is_continuation = True
            elif line.startswith('#'):
                if not in_block_comments:
                    node.value += self.config.indent_before_comments
            node.value += line
            if has_nl and (line or with_comments[i+1] or not self.in_arguments):
                node.value += '\n'
            in_block_comments = True
        if node.value.endswith('\n') and node.is_continuation:
            node.value += self.config.indent_by

    def visit_SymbolNode(self, node: mparser.SymbolNode) -> None:
        super().visit_SymbolNode(node)
        if node.value in "([{" and not node.whitespaces.value.strip('\n'):
            node.whitespaces.value = ''
        node.whitespaces.accept(self)

    def visit_StringNode(self, node: mparser.StringNode) -> None:
        self.enter_node(node)

        if self.config.simplify_string_literals:
            if node.is_multiline and not any(x in node.value for x in ['\n', "'"]):
                node.is_multiline = False
                node.value = node.escape()

            if node.is_fstring and '@' not in node.value:
                node.is_fstring = False

        node.whitespaces.accept(self)

    def visit_UnaryOperatorNode(self, node: mparser.UnaryOperatorNode) -> None:
        super().visit_UnaryOperatorNode(node)
        self.move_whitespaces(node.value, node)

    def visit_NotNode(self, node: mparser.NotNode) -> None:
        super().visit_UnaryOperatorNode(node)
        if not node.operator.whitespaces.value:
            node.operator.whitespaces.value = ' '
        self.move_whitespaces(node.value, node)

    def visit_BinaryOperatorNode(self, node: mparser.BinaryOperatorNode) -> None:
        super().visit_BinaryOperatorNode(node)
        self.add_space_after(node.left)
        self.add_space_after(node.operator)
        self.move_whitespaces(node.right, node)

    def visit_ArrayNode(self, node: mparser.ArrayNode) -> None:
        super().visit_ArrayNode(node)
        self.move_whitespaces(node.rbracket, node)

        if node.lbracket.whitespaces.value:
            node.args.is_multiline = True
        if node.args.arguments and self.config.space_array:
            # ArgumentFormatter replaces the spaces with newlines if node is multiline
            self.add_space_after(node.lbracket)
            self.add_space_after(node.args)
        if not node.args.arguments:
            self.move_whitespaces(node.lbracket, node.args)

    def visit_DictNode(self, node: mparser.DictNode) -> None:
        super().visit_DictNode(node)
        self.move_whitespaces(node.rcurl, node)

        if node.lcurl.whitespaces.value:
            node.args.is_multiline = True

    def visit_CodeBlockNode(self, node: mparser.CodeBlockNode) -> None:
        self.enter_node(node)
        if node.pre_whitespaces:
            self.in_block_comments = True
            node.pre_whitespaces.accept(self)
            self.in_block_comments = False
        else:
            node.pre_whitespaces = mparser.WhitespaceNode(mparser.Token('whitespace', node.filename, 0, 0, 0, (0, 0), ''))
        node.pre_whitespaces.block_indent = True

        for i in node.lines:
            i.accept(self)
        self.exit_node(node)

        if node.lines:
            self.move_whitespaces(node.lines[-1], node)
        else:
            node.whitespaces.value = node.pre_whitespaces.value + node.whitespaces.value
            node.pre_whitespaces.value = ''
            self.in_block_comments = True
            node.whitespaces.accept(self)
            self.in_block_comments = False

        if node.condition_level == 0 and self.config.insert_final_newline:
            self.add_nl_after(node, force=True)

        indent = node.condition_level * self.config.indent_by
        if indent and node.lines:
            node.pre_whitespaces.value += indent
        for line in node.lines[:-1]:
            line.whitespaces.value += indent

    def visit_IndexNode(self, node: mparser.IndexNode) -> None:
        super().visit_IndexNode(node)
        self.move_whitespaces(node.rbracket, node)

    def visit_MethodNode(self, node: mparser.MethodNode) -> None:
        super().visit_MethodNode(node)
        self.move_whitespaces(node.rpar, node)

        if node.lpar.whitespaces.value:
            node.args.is_multiline = True

    def visit_FunctionNode(self, node: mparser.FunctionNode) -> None:
        if node.func_name.value == 'files':
            if len(node.args.arguments) == 1 and not node.args.kwargs:
                arg = node.args.arguments[0]
                if isinstance(arg, mparser.ArrayNode):
                    if not arg.lbracket.whitespaces or not arg.lbracket.whitespaces.value.strip():
                        # files([...]) -> files(...)
                        node.args = arg.args

            if self.config.sort_files:
                self.sort_arguments(node.args)

        super().visit_FunctionNode(node)
        self.move_whitespaces(node.rpar, node)

        if node.lpar.whitespaces.value:
            node.args.is_multiline = True

    def visit_AssignmentNode(self, node: mparser.AssignmentNode) -> None:
        super().visit_AssignmentNode(node)
        self.add_space_after(node.var_name)
        self.add_space_after(node.operator)
        self.move_whitespaces(node.value, node)

    def visit_ForeachClauseNode(self, node: mparser.ForeachClauseNode) -> None:
        super().visit_ForeachClauseNode(node)
        self.add_space_after(node.foreach_)
        self.add_space_after(node.varnames[-1])
        for comma in node.commas:
            self.add_space_after(comma)
        self.add_space_after(node.colon)

        node.block.whitespaces.value += node.condition_level * self.config.indent_by
        # After the last statement, whitespaces begin on the line of that statement
        node.block.whitespaces.block_indent = not node.block.lines

        self.move_whitespaces(node.endforeach, node)

    def visit_IfClauseNode(self, node: mparser.IfClauseNode) -> None:
        super().visit_IfClauseNode(node)
        self.move_whitespaces(node.endif, node)

        for if_node in node.ifs:
            if_node.whitespaces.value += node.condition_level * self.config.indent_by
        if isinstance(node.elseblock, mparser.ElseNode):
            node.elseblock.whitespaces.value += node.condition_level * self.config.indent_by

    def visit_IfNode(self, node: mparser.IfNode) -> None:
        super().visit_IfNode(node)
        self.add_space_after(node.if_)
        # After the last statement, whitespaces begin on the line of that statement
        self.in_block_comments = not node.block.lines
        self.move_whitespaces(node.block, node)
        self.in_block_comments = False
        node.whitespaces.condition_level = node.condition_level + 1
        node.whitespaces.block_indent = not node.block.lines

    def visit_ElseNode(self, node: mparser.ElseNode) -> None:
        super().visit_ElseNode(node)
        # After the last statement, whitespaces begin on the line of that statement
        self.in_block_comments = not node.block.lines
        self.move_whitespaces(node.block, node)
        self.in_block_comments = False
        node.whitespaces.condition_level = node.condition_level + 1
        node.whitespaces.block_indent = not node.block.lines

    def visit_TernaryNode(self, node: mparser.TernaryNode) -> None:
        super().visit_TernaryNode(node)
        self.add_space_after(node.condition)
        self.add_space_after(node.questionmark)
        self.add_space_after(node.trueblock)
        self.add_space_after(node.colon)
        self.move_whitespaces(node.falseblock, node)

    def visit_ArgumentNode(self, node: mparser.ArgumentNode) -> None:
        if not node.is_multiline:
            ml_detector = MultilineArgumentDetector(self.config)
            node.accept(ml_detector)
            if ml_detector.is_multiline:
                node.is_multiline = True

        self.in_arguments += 1
        super().visit_ArgumentNode(node)
        self.in_arguments -= 1

        if not node.arguments and not node.kwargs:
            node.whitespaces.accept(self)
            return

        last_node: mparser.BaseNode
        has_trailing_comma = len(node.commas) == len(node.arguments) + len(node.kwargs)
        if has_trailing_comma:
            last_node = node.commas[-1]
        elif node.kwargs:
            for last_node in node.kwargs.values():
                pass
        else:
            last_node = node.arguments[-1]

        self.move_whitespaces(last_node, node)

        if '#' not in node.whitespaces.value:
            # ArgumentFormatter adds the newline if node is multiline
            node.whitespaces.value = ''

    def visit_ParenthesizedNode(self, node: mparser.ParenthesizedNode) -> None:
        self.enter_node(node)

        if node.lpar.whitespaces and '#' in node.lpar.whitespaces.value:
            node.is_multiline = True

        elif not node.is_multiline:
            if MultilineParenthesesDetector.ends_with(node.inner, '\n'):
                # We keep it multiline if last parenthesis is on a separate line
                node.is_multiline = True
            elif MultilineParenthesesDetector.operators_contain(node.inner, '#', (mparser.BinaryOperatorNode,)):
                # A comment between operands forces a newline
                node.is_multiline = True
            elif self.config.sticky_parens and MultilineParenthesesDetector.operators_contain(node.inner, '\n'):
                # Closing parenthesis is never on a separate line with sticky parens
                node.is_multiline = True

        node.lpar.accept(self)
        node.inner.accept(self)

        inner_ws = node.inner.whitespaces.value
        if (node.is_multiline and self.config.sticky_parens and '#' in inner_ws and inner_ws.count('\n') == 1
                and not (node.rpar.whitespaces and '#' in node.rpar.whitespaces.value)):
            # The comment of last operand is moved to the end of the line of the closing parenthesis,
            # by ArgumentFormatter, which knows where that line ends
            node.moved_comment = inner_ws.strip()
            node.inner.whitespaces.value = ''

        node.rpar.accept(self)
        self.move_whitespaces(node.rpar, node)


@dataclass(slots=True, eq=False)
class SetAttr:
    """Reversible assignment of an attribute"""

    obj: object
    name: str
    old: T.Any
    new: T.Any

    def apply(self) -> None:
        setattr(self.obj, self.name, self.new)

    def undo(self) -> None:
        setattr(self.obj, self.name, self.old)


@dataclass(frozen=True, slots=True)
class FormatLayout:
    """Layout of a whitespace, decided by ArgumentFormatter before the whitespace is visited"""

    kind: Literal['space', 'newline', 'last_line']  # last_line: only indent the line following the whitespace
    indent: int = 0


@dataclass(slots=True)
class FormatterState:
    """State of ArgumentFormatter, restored when rewinding"""

    level: int = 0
    indent_after: bool = False
    is_function_arguments: bool = False
    bracket_depth: int = 0  # line breaks are only allowed inside brackets
    paren_inner: T.Optional[mparser.BaseNode] = None  # content of current multiline parentheses
    chain_level: int = 0  # operator level of the chain of operators being visited
    split_chain: bool = False
    chain_indent: int = 0  # indentation level of operators of a split chain
    chain_point: T.Optional[RewindPoint] = None  # rewind point of the chain of operators being visited
    column: int = 0
    pending_comment: T.Optional[str] = None  # comment to insert at the end of current line
    line_start: T.Optional[mparser.WhitespaceNode] = None  # whitespace ending with the indentation of current line
    line_has_code: bool = False
    moved_comments: int = 0


Breakable = T.Union[mparser.ArgumentNode, mparser.ParenthesizedNode, mparser.BinaryOperatorNode]


@dataclass(slots=True, eq=False)
class RewindPoint:
    """Where ArgumentFormatter can restart visiting, after deciding to split a node"""

    target: T.Optional[Breakable]  # node that can be split, if any
    log_length: int
    state: FormatterState
    closed_order: int = 0  # 0 while the node is visited, then order in which nodes were closed
    first_operand_end: int = 0  # for a chain of operators, column where its first operand ends


class Rewind(Exception):

    def __init__(self, point: RewindPoint):
        super().__init__()
        self.point = point


class ArgumentFormatter(FullAstVisitor):

    def __init__(self, config: FormatterConfig):
        self.config = config
        self.state = FormatterState()
        self.log: T.List[SetAttr] = []
        self.points: T.List[RewindPoint] = []  # open points, and points closed on current line
        self.closed_count = 0

        indent = re.escape(config.indent_by)
        # every line break with its indentation, except before an empty line
        self.indent_re = re.compile(rf'\n(?:{indent})*(?![ \t]*\n)')
        self.last_indent_re = re.compile(rf'\n(?:{indent})*$')  # last line break with its indentation

    def record(self, change: SetAttr) -> None:
        change.apply()
        self.log.append(change)

    def set_attr(self, obj: object, name: str, value: T.Any) -> None:
        """Assign an attribute of an AST node; every change to the AST must go through this"""
        old = getattr(obj, name)
        if old is not value and not (isinstance(old, str) and old == value):
            self.record(SetAttr(obj, name, old, value))

    def set_whitespaces(self, node: mparser.BaseNode, value: str) -> None:
        self.set_attr(node.whitespaces, 'value', value)

    # Layout decisions are recorded on the whitespace node before it is visited,
    # and applied by visit_WhitespaceNode after the whitespace is formatted.

    def add_space_after(self, node: mparser.BaseNode) -> None:
        self.set_attr(node.whitespaces, 'format_layout', FormatLayout('space'))

    def add_nl_after(self, node: mparser.BaseNode, indent: int) -> None:
        self.set_attr(node.whitespaces, 'format_layout', FormatLayout('newline', indent))

    def indent_last_line(self, node: mparser.BaseNode, indent: int) -> None:
        """Indent the line following node, without changing indentation of comments"""
        self.set_attr(node.whitespaces, 'format_layout', FormatLayout('last_line', indent))

    def apply_layout(self, node: mparser.WhitespaceNode, layout: FormatLayout, value: str) -> str:
        if layout.kind == 'space':
            return value or ' '
        indent_by = (node.condition_level + layout.indent) * self.config.indent_by
        if layout.kind == 'newline':
            if not value or value == ' ':
                value = '\n'
            if indent_by:
                value = self.indent_re.sub('\n' + indent_by, value)
            return value
        return self.last_indent_re.sub('\n' + indent_by, value)

    def advance(self, column: int, text: str) -> int:
        """Column after printing text (without line break) from column"""
        if '\t' in text:
            # Tabs advance to the next tab stop: expand them from the start of the current tab stop
            offset = column % self.config.tab_width
            return column + len((' ' * offset + text).expandtabs(self.config.tab_width)) - offset
        return column + len(text)

    def measure(self, text: str, is_code: bool = True) -> None:
        """Advance the column over printed text, and split a node at the end of a line that is too long"""
        for i, line in enumerate(text.split('\n')):
            if i:
                # Decide at the end of the line, when all nodes on that line are known
                if self.config.max_line_length is not None and self.state.column > self.config.max_line_length:
                    self.split_line()
                # Points closed on previous line are no more candidates
                self.points = [p for p in self.points if not p.closed_order]
                self.state.column = 0
                self.state.line_has_code = False
            self.state.column = self.advance(self.state.column, line)
        if is_code and text:
            self.state.line_has_code = True
            if '\n' in text:
                self.state.line_start = None  # line starts inside a multiline string

    def split_line(self) -> None:
        """Choose a node to split, and rewind to restart visiting from it"""
        # Outermost open node is preferred: splitting it shortens the line, even if it begins on a previous line
        for point in self.points:
            if not point.closed_order and point.target and not point.target.is_multiline:
                point.target.is_multiline = True
                raise Rewind(point)

        # Otherwise, the node closed last on current line, visited again from its innermost open parent.
        # Splitting a chain of operators cannot make the line fit if its first operand is already too long.
        closed = [p for p in self.points if p.closed_order and p.target and not p.target.is_multiline
                  and self.config.max_line_length is not None and p.first_operand_end <= self.config.max_line_length]
        if closed:
            point = max(closed, key=lambda p: p.closed_order)
            index = self.points.index(point)
            parent = next((p for p in reversed(self.points[:index]) if not p.closed_order), None)
            if parent:
                assert point.target is not None
                point.target.is_multiline = True
                raise Rewind(parent)

    def rewind_point(self, target: T.Optional[Breakable], visit: T.Callable[[], None]) -> None:
        """Call visit, and call it again each time a node is split while visiting it"""
        # Terminates: each Rewind sets is_multiline on one more node (split_line), and it is never unset
        while True:
            point = RewindPoint(target, len(self.log), replace(self.state))
            self.points.append(point)
            try:
                visit()
                break
            except Rewind as e:
                if e.point is not point:
                    raise
                while len(self.log) > point.log_length:
                    self.log.pop().undo()
                self.state = point.state
                del self.points[self.points.index(point):]
        self.closed_count += 1
        point.closed_order = self.closed_count

    def visit_default_func(self, node: mparser.BaseNode) -> None:
        self.enter_node(node)
        assert hasattr(node, 'value')
        self.measure(str(node.value))
        self.exit_node(node)

    def visit_BooleanNode(self, node: mparser.BooleanNode) -> None:
        self.enter_node(node)
        self.measure('true' if node.value else 'false')
        self.exit_node(node)

    def visit_NumberNode(self, node: mparser.NumberNode) -> None:
        self.enter_node(node)
        self.measure(node.raw_value)
        self.exit_node(node)

    def visit_StringNode(self, node: mparser.StringNode) -> None:
        self.enter_node(node)
        prefix = 'f' if node.is_fstring else ''
        if node.is_multiline:
            self.measure(f"{prefix}'''{node.value}'''")
        else:
            self.measure(f"{prefix}'{node.raw_value}'")
        self.exit_node(node)

    def visit_ContinueNode(self, node: mparser.ContinueNode) -> None:
        self.enter_node(node)
        self.measure('continue')
        self.exit_node(node)

    def visit_BreakNode(self, node: mparser.BreakNode) -> None:
        self.enter_node(node)
        self.measure('break')
        self.exit_node(node)

    def visit_EmptyNode(self, node: mparser.EmptyNode) -> None:
        self.enter_node(node)
        self.exit_node(node)

    def visit_CodeBlockNode(self, node: mparser.CodeBlockNode) -> None:
        self.enter_node(node)
        if node.pre_whitespaces:
            node.pre_whitespaces.accept(self)
        for i, line in enumerate(node.lines):
            # Each statement is a rewind point, to visit again a node closed on current line
            self.rewind_point(None, partial(self.visit_statement, node, line, i == len(node.lines) - 1))
        if not node.lines:
            self.exit_node(node)

    def visit_statement(self, block: mparser.CodeBlockNode, line: mparser.BaseNode, is_last: bool) -> None:
        line.accept(self)
        if is_last:
            # TrimWhitespaces moved the end of the last statement line to the block
            self.exit_node(block)

    def visit_ArrayNode(self, node: mparser.ArrayNode) -> None:
        self.rewind_point(node.args if len(node.args) else None, lambda: self.format_array(node))

    def format_array(self, node: mparser.ArrayNode) -> None:
        self.enter_node(node)
        self.state.bracket_depth += 1
        if node.args.is_multiline:
            self.state.level += 1
            if node.args.arguments:
                self.add_nl_after(node.lbracket, indent=self.state.level)
        node.lbracket.accept(self)
        self.state.is_function_arguments = False
        node.args.accept(self)
        if node.args.is_multiline:
            self.state.level -= 1
        self.state.bracket_depth -= 1
        node.rbracket.accept(self)
        self.exit_node(node)

    def visit_DictNode(self, node: mparser.DictNode) -> None:
        self.rewind_point(node.args if len(node.args) else None, lambda: self.format_dict(node))

    def format_dict(self, node: mparser.DictNode) -> None:
        self.enter_node(node)
        self.state.bracket_depth += 1
        if node.args.is_multiline:
            self.state.level += 1
            if node.args.kwargs:
                self.add_nl_after(node.lcurl, indent=self.state.level)
        node.lcurl.accept(self)
        self.state.is_function_arguments = False
        node.args.accept(self)
        if node.args.is_multiline:
            self.state.level -= 1
        self.state.bracket_depth -= 1
        node.rcurl.accept(self)
        self.exit_node(node)

    def visit_MethodNode(self, node: mparser.MethodNode) -> None:
        self.enter_node(node)
        node.source_object.accept(self)
        is_cont = node.source_object.whitespaces and node.source_object.whitespaces.is_continuation
        if is_cont:
            self.state.level += 1
        node.dot.accept(self)
        node.name.accept(self)
        # Rewind point is after the source object, which is not changed by splitting the arguments
        self.rewind_point(node.args if len(node.args) else None, lambda: self.format_call_arguments(node))
        if is_cont:
            self.state.level -= 1
        self.exit_node(node)

    def visit_FunctionNode(self, node: mparser.FunctionNode) -> None:
        self.enter_node(node)
        node.func_name.accept(self)
        self.rewind_point(node.args if len(node.args) else None, lambda: self.format_call_arguments(node))
        self.exit_node(node)

    def format_call_arguments(self, node: T.Union[mparser.FunctionNode, mparser.MethodNode]) -> None:
        if node.args.is_multiline:
            self.state.level += 1
            self.add_nl_after(node.lpar, indent=self.state.level)
        node.lpar.accept(self)
        self.state.is_function_arguments = True
        self.state.bracket_depth += 1
        node.args.accept(self)
        self.state.bracket_depth -= 1
        if node.args.is_multiline:
            self.state.level -= 1
        node.rpar.accept(self)

    def visit_WhitespaceNode(self, node: mparser.WhitespaceNode) -> None:
        lines = node.value.splitlines(keepends=True)
        if lines:
            indent = (node.condition_level + self.state.level) * self.config.indent_by
            value = '' if node.block_indent else lines.pop(0)
            for line in lines:
                if '#' in line and not line.startswith(indent):
                    value += indent
                value += line
            if node.is_continuation or (self.state.indent_after and value.endswith('\n')):
                value += indent
        else:
            value = node.value
        if node.format_layout:
            value = self.apply_layout(node, node.format_layout, value)
            self.set_attr(node, 'format_layout', None)
        if self.state.pending_comment:
            value = self.insert_pending_comment(value)
        value = self.move_long_comment(value)
        self.set_attr(node, 'value', value)
        # Comments are not counted in line length: splitting the line rarely makes them fit
        self.measure('\n'.join(line.split('#', 1)[0].rstrip(' \t') if '#' in line else line for line in value.split('\n')),
                     is_code=False)
        if '\n' in value or self.state.line_start is None:
            self.state.line_start = node

    def move_long_comment(self, value: str) -> str:
        """Move the comment ending a line that is too long above that line"""
        line, newline, rest = value.partition('\n')
        if '#' not in line or not newline or not self.state.line_has_code or self.state.line_start is None:
            return value
        if self.config.max_line_length is None or self.advance(self.state.column, line) <= self.config.max_line_length:
            return value
        code, _, comment = line.partition('#')
        # The whitespace starting the line ends with the indentation of the line
        start = self.state.line_start.value
        indent = start.rpartition('\n')[2]
        self.set_attr(self.state.line_start, 'value', f'{start}#{comment}\n{indent}')
        self.state.moved_comments += 1
        return code.rstrip(' \t') + newline + rest

    def insert_pending_comment(self, value: str) -> str:
        """Insert the pending comment at the end of the first line of value, if value ends that line"""
        line, newline, rest = value.partition('\n')
        if not newline or '\\' in line:
            return value  # line continues after this whitespace
        comment = self.config.indent_before_comments + self.state.pending_comment
        self.state.pending_comment = None
        if '#' in line:
            # Keep the comment already on this line, on its own line with the indentation of the next one
            line, _, other = line.partition('#')
            indent = rest[:len(rest) - len(rest.lstrip(' \t'))]
            rest = f'{indent}#{other}\n{rest}'
        return line.rstrip(' \t') + comment + '\n' + rest

    def visit_ArgumentNode(self, node: mparser.ArgumentNode) -> None:
        is_function_arguments = self.state.is_function_arguments

        for colon in node.colons:
            self.add_space_after(colon)

        if self.config.wide_colon:
            for key in node.kwargs:
                self.add_space_after(key)

        arguments_count = len(node.arguments) + len(node.kwargs)
        has_trailing_comma = node.commas and len(node.commas) == arguments_count
        if node.is_multiline:
            need_comma = True
            if arguments_count == 1 and is_function_arguments:
                need_comma = not self.config.no_single_comma_function

            if need_comma and not has_trailing_comma:
                comma = mparser.SymbolNode(mparser.Token('comma', node.filename, 0, 0, 0, (0, 0), ','))
                comma.condition_level = node.condition_level
                comma.whitespaces = mparser.WhitespaceNode(mparser.Token('whitespace', node.filename, 0, 0, 0, (0, 0), ''))
                self.set_attr(node, 'commas', node.commas + [comma])
            elif has_trailing_comma and not need_comma:
                self.set_attr(node, 'commas', node.commas[:-1])

            arg_index = 0
            if self.config.group_arg_value:
                for arg in node.arguments[:-1]:
                    group_args = False
                    if isinstance(arg, mparser.StringNode) and arg.value.startswith('--') and arg.value != '--':
                        next_arg = node.arguments[arg_index + 1]
                        # any node is a value, except strings starting with '-' (another option)
                        if not (isinstance(next_arg, mparser.StringNode) and next_arg.value.startswith('-')):
                            group_args = True
                    if group_args:
                        # keep '--arg', 'value' on same line
                        self.add_space_after(node.commas[arg_index])
                    elif arg_index < len(node.commas):
                        self.add_nl_after(node.commas[arg_index], self.state.level)
                    arg_index += 1

            for comma in node.commas[arg_index:-1]:
                self.add_nl_after(comma, self.state.level)
            if node.arguments or node.kwargs:
                # Closing bracket on its own line; comments before it keep the indentation of the arguments
                if node.whitespaces.value in {'', ' '}:
                    self.set_whitespaces(node, '\n')
                self.indent_last_line(node, self.state.level - 1)

        else:
            if has_trailing_comma and not (node.commas[-1].whitespaces and node.commas[-1].whitespaces.value):
                self.set_attr(node, 'commas', node.commas[:-1])

            for comma in node.commas:
                self.add_space_after(comma)

        # Like in multiline parentheses, a line broken inside an argument (e.g. by a comment
        # between operands) continues at the indentation of the argument
        current_indent_after = self.state.indent_after
        if node.is_multiline and (node.arguments or node.kwargs):
            self.state.indent_after = True
        super().visit_ArgumentNode(node)
        self.state.indent_after = current_indent_after

    def visit_ParenthesizedNode(self, node: mparser.ParenthesizedNode) -> None:
        # Sticky parentheses can only be split on operators
        can_split = not self.config.sticky_parens or self.operator_level(node.inner) > 0
        self.rewind_point(node if can_split else None, lambda: self.format_parentheses(node))

    def format_parentheses(self, node: mparser.ParenthesizedNode) -> None:
        self.enter_node(node)
        current_paren_inner = self.state.paren_inner
        if node.is_multiline:
            self.state.level += self.config.paren_levels
            current_indent_after = self.state.indent_after
            self.state.indent_after = True
            self.state.paren_inner = node.inner
            # Operators of multiline parentheses are split with them: and / or, or any operator with sticky parentheses
            operator_level = self.operator_level(node.inner)
            if operator_level == 1 or (operator_level and self.config.sticky_parens):
                T.cast('mparser.BinaryOperatorNode', node.inner).is_multiline = True

        if not node.is_multiline:
            self.set_whitespaces(node.inner, '')
        elif not self.config.sticky_parens:
            if not node.inner.whitespaces.value:
                self.set_whitespaces(node.inner, '\n')
        else:
            # Closing parenthesis is never on a separate line with sticky parens
            if '#' not in node.lpar.whitespaces.value:
                self.set_whitespaces(node.lpar, '')
            if '#' not in node.inner.whitespaces.value:
                self.set_whitespaces(node.inner, '')

        if node.is_multiline:
            if not self.config.sticky_parens or '#' in node.lpar.whitespaces.value:
                self.add_nl_after(node.lpar, indent=self.state.level)
            self.indent_last_line(node.inner, indent=self.state.level - self.config.paren_levels)

        node.lpar.accept(self)
        self.state.bracket_depth += 1
        node.inner.accept(self)
        self.state.bracket_depth -= 1
        if node.is_multiline:
            self.state.level -= self.config.paren_levels
            self.state.indent_after = current_indent_after
        self.state.paren_inner = current_paren_inner
        node.rpar.accept(self)
        if node.moved_comment:
            self.state.pending_comment = node.moved_comment
        self.exit_node(node)

    @staticmethod
    def operator_level(node: mparser.BaseNode) -> int:
        """Precedence level of a chain of operators split together, or 0 if node is not such an operator"""
        if isinstance(node, (mparser.OrNode, mparser.AndNode)):
            return 1
        if isinstance(node, mparser.ArithmeticNode):
            return 2 if node.operation in {'+', '-'} else 3
        return 0

    def visit_OrNode(self, node: mparser.OrNode) -> None:
        self.visit_operator(node)

    def visit_AndNode(self, node: mparser.AndNode) -> None:
        self.visit_operator(node)

    def visit_ArithmeticNode(self, node: mparser.ArithmeticNode) -> None:
        self.visit_operator(node)

    def visit_operator(self, node: mparser.BinaryOperatorNode) -> None:
        level = self.operator_level(node)
        if level == self.state.chain_level:
            self.format_operator(node)  # part of the chain being visited
        else:
            self.rewind_point(node if self.state.bracket_depth else None, lambda: self.format_chain(node, level))

    def format_chain(self, node: mparser.BinaryOperatorNode, level: int) -> None:
        """Visit a chain of operators of same level; when split, there is one operand per line"""
        chain_level, split_chain, chain_indent = self.state.chain_level, self.state.split_chain, self.state.chain_indent
        chain_point, self.state.chain_point = self.state.chain_point, self.points[-1]
        self.state.chain_level = level
        self.state.split_chain = node.is_multiline
        # Operators are indented one more level than the line of the first operand,
        # except when the chain is the content of multiline parentheses, already indented
        self.state.chain_indent = self.state.level + (0 if node is self.state.paren_inner else 1)
        self.format_operator(node)
        self.state.chain_level, self.state.split_chain, self.state.chain_indent = chain_level, split_chain, chain_indent
        self.state.chain_point = chain_point

    def format_operator(self, node: mparser.BinaryOperatorNode) -> None:
        self.enter_node(node)
        if self.state.split_chain:
            self.add_nl_after(node.left, indent=self.state.chain_indent)
        self.visit_operand(node.left)
        assert self.state.chain_point is not None
        if not self.state.chain_point.first_operand_end:
            self.state.chain_point.first_operand_end = self.state.column
        level = self.state.level
        if self.state.split_chain:
            self.state.level = self.state.chain_indent
        node.operator.accept(self)
        self.visit_operand(node.right)
        self.state.level = level
        self.exit_node(node)

    def visit_operand(self, node: mparser.BaseNode) -> None:
        if self.operator_level(node) == self.state.chain_level:
            node.accept(self)
        else:
            # The operand begins a new chain
            chain_level, self.state.chain_level = self.state.chain_level, 0
            node.accept(self)
            self.state.chain_level = chain_level


class SubdirFetcher(FullAstVisitor):

    def __init__(self, current_dir: Path, fetch_subprojects: bool):
        self.current_dir = current_dir
        self.fetch_subprojects = fetch_subprojects
        self.subdirs: T.List[Path] = []

    def visit_FunctionNode(self, node: mparser.FunctionNode) -> None:
        if self.fetch_subprojects and node.func_name.value == 'subproject':
            if node.args.arguments and isinstance(node.args.arguments[0], mparser.StringNode):
                subdir = node.args.arguments[0].value
                self.subdirs.append(self.current_dir / 'subprojects' / subdir)
        if node.func_name.value == 'subdir':
            if node.args.arguments and isinstance(node.args.arguments[0], mparser.StringNode):
                subdir = node.args.arguments[0].value
                self.subdirs.append(self.current_dir / subdir)
        super().visit_FunctionNode(node)


class Formatter:

    def __init__(self, configuration_file: T.Optional[Path], use_editor_config: bool, fetch_subdirs: bool, fetch_subprojects: bool = False):
        self.fetch_subdirs = fetch_subdirs
        self.fetch_subprojects = fetch_subprojects
        self.use_editor_config = use_editor_config
        self.config = self.load_configuration(configuration_file)
        self.current_config = self.config

        self.current_dir = Path()
        self.subdirs: T.List[Path] = []

    def load_editor_config(self, source_file: Path) -> EditorConfig:
        # See https://editorconfig.org/
        config = EditorConfig()

        if source_file == Path('STDIN'):
            raise MesonException('Using editorconfig with stdin requires --source-file-path argument')

        try:
            source_file_path = source_file.resolve()
        except FileNotFoundError:
            raise MesonException(f'Unable to resolve path for "{source_file}"')

        for p in source_file_path.parents:
            editorconfig_file = p / '.editorconfig'
            if not editorconfig_file.exists():
                continue

            cp = DefaultConfigParser(delimiters=('=',))
            cp.read_default(editorconfig_file)

            sections = [section for section in cp.sections() if match_path(source_file.as_posix(), section)]
            for f in fields(config):
                if getattr(config, f.name) is not None:
                    continue  # value already set from higher file

                getter = f.metadata['getter']
                for section in sections:
                    try:
                        value = getter(cp, section, f.name, fallback=None)
                    except ValueError as e:
                        raise MesonException(f'Invalid type for key "{f.name}" in "{editorconfig_file}" file:\n{e}') from e
                    if value is not None:
                        setattr(config, f.name, value)

            # Root is not required except in the top level .editorconfig.
            if cp.getboolean(cp.default_section, 'root', fallback=False):
                break

        return config

    def load_configuration(self, configuration_file: T.Optional[Path]) -> FormatterConfig:
        config = FormatterConfig()
        if configuration_file:
            cp = DefaultConfigParser()
            try:
                cp.read_default(configuration_file)
            except ParsingError as e:
                raise MesonException(f'Unable to parse configuration file "{configuration_file}":\n{e}') from e

            extra_keys = sorted(set(cp.defaults()).difference(f.name for f in fields(config)))
            if extra_keys:
                raise MesonException(f'Unknown config keys: "{", ".join(extra_keys)}" in configuration file "{configuration_file}"')

            for f in fields(config):
                getter = f.metadata['getter']
                try:
                    value = getter(cp, cp.default_section, f.name, fallback=None)
                except ValueError as e:
                    raise MesonException(
                        f'Error parsing "{str(configuration_file)}", option "{f.name}", error: "{e!s}"')
                if value is not None:
                    setattr(config, f.name, value)

            if config.use_editor_config:
                self.use_editor_config = True

        return config

    def format(self, code: str, source_file: Path) -> str:
        self.current_dir = source_file.parent
        self.current_config = FormatterConfig.default()
        if self.use_editor_config:
            self.current_config = self.current_config.with_editorconfig(self.load_editor_config(source_file))
        self.current_config = self.current_config.update(self.config)

        ast = mparser.Parser(code, source_file.as_posix()).parse()
        directives = find_format_directives(ast)
        if self.fetch_subdirs:
            subdir_fetcher = SubdirFetcher(self.current_dir, self.fetch_subprojects)
            ast.accept(subdir_fetcher)
            self.subdirs = subdir_fetcher.subdirs

        formatted, moved_comments = self.format_ast(ast)
        if moved_comments:
            # Format again, as the moved comments may have forced line breaks or multiline arguments.
            # Moved comments are on their own line, and are never moved again.
            formatted, moved_comments = self.format_ast(mparser.Parser(formatted, source_file.as_posix()).parse())
            # assert not moved_comments
        if not directives:
            return formatted

        formatted_ast = mparser.Parser(formatted, source_file.as_posix()).parse()
        return restore_disabled_regions(code, directives, formatted, find_format_directives(formatted_ast))

    def format_ast(self, ast: mparser.CodeBlockNode) -> T.Tuple[str, int]:
        """Format the ast; returns the formatted code, and the number of comments moved to their own line"""
        ast.accept(AstConditionLevel())
        ast.accept(TrimWhitespaces(self.current_config))
        formatter = ArgumentFormatter(self.current_config)
        ast.accept(formatter)
        if formatter.state.pending_comment:
            # No line break after the last statement
            ast.whitespaces.value += self.current_config.indent_before_comments + formatter.state.pending_comment

        printer = RawPrinter()
        ast.accept(printer)
        return printer.result, formatter.state.moved_comments


def add_arguments(parser: argparse.ArgumentParser) -> None:
    inplace_group = parser.add_mutually_exclusive_group()
    inplace_group.add_argument(
        '-q', '--check-only',
        action='store_true',
        help='silently exit with 1 if files would be modified by meson format'
    )
    inplace_group.add_argument(
        '-d', '--check-diff',
        action='store_true',
        default=False,
        help='exit with 1 and show diff if files would be modified by meson format'
    )
    inplace_group.add_argument(
        '-i', '--inplace',
        action='store_true',
        help='format files in-place'
    )
    parser.add_argument(
        '-r', '--recursive',
        action='store_true',
        help='recurse subdirs (requires --check-only, --check-diff or --inplace option)',
    )
    parser.add_argument(
        '-s', '--subprojects',
        action='store_true',
        help='recurse subprojects (requires --recursive)',
    )
    parser.add_argument(
        '-c', '--configuration',
        metavar='meson.format',
        type=Path,
        help='read configuration from meson.format'
    )
    parser.add_argument(
        '-e', '--editor-config',
        action='store_true',
        default=False,
        help='try to read configuration from .editorconfig'
    )
    parser.add_argument(
        '-o', '--output',
        type=Path,
        help='output file (implies having exactly one input)'
    )
    parser.add_argument(
        '--source-file-path',
        type=Path,
        help='path to use, when reading from stdin'
    )
    parser.add_argument(
        'sources',
        nargs='*',
        type=Path,
        help='meson source files'
    )

def get_meson_format(sources: T.List[Path]) -> T.Optional[Path]:
    for src_file in sources:
        for parent in src_file.resolve().parents:
            target = parent / 'meson.format'
            if target.is_file():
                return target
    return None

def run(options: argparse.Namespace) -> int:
    if options.output and len(options.sources) != 1:
        raise MesonException('--output argument implies having exactly one source file')
    if options.recursive and not (options.inplace or options.check_only or options.check_diff):
        raise MesonException('--recursive argument requires one of --inplace, --check-diff or --check-only')
    if options.subprojects and not options.recursive:
        raise MesonException('--subprojects argument requires --recursive option')

    from_stdin = len(options.sources) == 1 and options.sources[0].name == '-' and options.sources[0].parent == Path()
    if options.recursive and from_stdin:
        raise MesonException('--recursive argument is not compatible with stdin input')
    if options.inplace and from_stdin:
        raise MesonException('--inplace argument is not compatible with stdin input')
    if options.source_file_path and not from_stdin:
        raise MesonException('--source-file-path argument is only compatible with stdin input')
    if from_stdin and options.editor_config and not options.source_file_path:
        raise MesonException('using --editor-config with stdin input requires --source-file-path argument')

    sources: T.List[Path] = options.sources.copy() or [Path(build_filename)]

    if not options.configuration:
        options.configuration = get_meson_format(sources)

    formatter = Formatter(options.configuration, options.editor_config, options.recursive, options.subprojects)
    err = 0

    while sources:
        src_file = sources.pop(0)
        if src_file.is_dir():
            src_file = src_file / build_filename

        try:
            if from_stdin:
                src_file = options.source_file_path or Path('STDIN')  # used for error messages and introspection
                code = sys.stdin.read()
            else:
                code = src_file.read_text(encoding='utf-8')
        except IOError as e:
            raise MesonException(f'Unable to read from {src_file}') from e

        formatted = formatter.format(code, src_file)
        if options.recursive:
            sources.extend(formatter.subdirs)

        if options.inplace:
            try:
                with src_file.open('w', encoding='utf-8', newline=formatter.current_config.newline) as sf:
                    sf.write(formatted)
            except IOError as e:
                raise MesonException(f'Unable to write to {src_file}') from e
        elif options.check_only or options.check_diff:
            if code != formatted:
                err = 1
                if options.check_diff:
                    diff = difflib.unified_diff(code.splitlines(), formatted.splitlines(),
                                                str(src_file), str(src_file),
                                                '(original)', '(reformatted)',
                                                lineterm='')
                    print('\n'.join(diff))
                else:
                    break
        elif options.output:
            try:
                with options.output.open('w', encoding='utf-8', newline=formatter.current_config.newline) as of:
                    of.write(formatted)
            except IOError as e:
                raise MesonException(f'Unable to write to {options.output}') from e
        else:
            print(formatted, end='')

    return err

# TODO: remove empty newlines when more than N (2...)
# TODO: align series of assignments
# TODO: align comments

# Differences from muon format:
# - By default, uses two spaces before comment, and added option for that
# - Muon will mix CRLF and LF on Windows files...
# - Support for end_of_line char
# - Support for max_line_length, end_of_line, insert_final_newline, tab_width in .editorconfig
# - Option to simplify string literals
# - Option to recognize and parse meson.build in subdirs
# - Correctly compute line length when using tabs
# - By default, arguments in files() are sorted naturally
# - Option to group '--arg', 'value' on same line in multiline arguments
# - '# meson-format off|on' directives, in addition to muon's '# fmt: off|on';
#   they must be on their own line and enclose whole statements
# - Option to keep parentheses on the same line as the expression (sticky_parens)
