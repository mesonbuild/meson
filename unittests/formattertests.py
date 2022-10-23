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

    def test_indentation(self):
        (formatter, old_lines) = FormatterTests.fill_formatter('indentation.test')
        for i, line in enumerate(formatter.lines):
            self.assertEqual(old_lines[i], line)
        assert(len(formatter.comments) == 0)

    @staticmethod
    def fill_formatter(file: str) -> (mesonbuild.ast.AstFormatter, T.List[str]):
        path = './test cases/formatting/' + file
        with open(path, encoding='utf-8') as f:
            code = f.read()
        old_lines = code.splitlines()
        parser = mesonbuild.mparser.Parser(code, path)
        codeblock = parser.parse()
        comments = parser.comments()
        formatter = mesonbuild.ast.AstFormatter(comments, old_lines)
        codeblock.accept(formatter)
        formatter.end()
        return (formatter, old_lines)
    
