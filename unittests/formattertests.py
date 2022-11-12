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

import mesonbuild.mparser
from mesonbuild.ast import AstFormatter


import os
import sys
import typing as T
import unittest

class FormatterTests(unittest.TestCase):
    def test_readding_comments(self):
        (formatter, old_lines) = FormatterTests.fill_formatter('comments.test')
        for i, line in enumerate(formatter.lines):
            self.assertEqual(old_lines[i], line)
        assert(len(formatter.comments) == 0)
        self.assert_idempotency(formatter.lines)

    def test_indentation(self):
        (formatter, old_lines) = FormatterTests.fill_formatter('indentation.test')
        for i, line in enumerate(formatter.lines):
            self.assertEqual(old_lines[i], line)
        assert(len(formatter.comments) == 0)
        self.assert_idempotency(formatter.lines)

    def test_generics(self):
        (formatter, old_lines) = FormatterTests.fill_formatter('generics.test')
        for i, line in enumerate(formatter.lines):
            self.assertEqual(old_lines[i], line)
        assert(len(formatter.comments) == 0)
        self.assert_idempotency(formatter.lines)

    def test_space_array(self):
        config = {}
        config['space_array'] = True
        (formatter, old_lines) = FormatterTests.fill_formatter('space_array.test', config)
        for i, line in enumerate(formatter.lines):
            self.assertEqual(old_lines[i], line)
        assert(len(formatter.comments) == 0)
        self.assert_idempotency(formatter.lines, config)

    def test_wide_colon(self):
        config = {}
        config['wide_colon'] = True
        (formatter, old_lines) = FormatterTests.fill_formatter('wide_colon.test', config)
        for i, line in enumerate(formatter.lines):
            self.assertEqual(old_lines[i], line)
        assert(len(formatter.comments) == 0)
        self.assert_idempotency(formatter.lines, config)

    def assert_idempotency(self, new_lines, extra_config = {}):
        config = {}
        config['max_line_len'] = 80
        config['indent_by'] = '    '
        config['space_array'] = False
        config['kwa_ml'] = False
        config['wide_colon'] = False
        config['no_single_comma_function'] = False
        config.update(extra_config)
        parser = mesonbuild.mparser.Parser('\n'.join(new_lines), '-')
        codeblock = parser.parse()
        comments = parser.comments()
        formatter = mesonbuild.ast.AstFormatter(comments, new_lines, config)
        codeblock.accept(formatter)
        formatter.end()
        assert(len(formatter.comments) == 0)
        for i, line in enumerate(formatter.lines):
            self.assertEqual(new_lines[i], line)

    @staticmethod
    def fill_formatter(file: str, extra_config={}) -> (mesonbuild.ast.AstFormatter, T.List[str]):
        path = './test cases/formatting/' + file
        config = {}
        config['max_line_len'] = 80
        config['indent_by'] = '    '
        config['space_array'] = False
        config['kwa_ml'] = False
        config['wide_colon'] = False
        config['no_single_comma_function'] = False
        config.update(extra_config)
        with open(path, encoding='utf-8') as f:
            code = f.read()
        old_lines = code.splitlines()
        parser = mesonbuild.mparser.Parser(code, path)
        codeblock = parser.parse()
        comments = parser.comments()
        formatter = mesonbuild.ast.AstFormatter(comments, old_lines, config)
        codeblock.accept(formatter)
        formatter.end()
        return (formatter, old_lines)
    
