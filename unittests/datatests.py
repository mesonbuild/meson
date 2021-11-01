# Copyright 2016-2021 The Meson development team

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
import unittest
from itertools import chain
from pathlib import Path

import mesonbuild.mlog
import mesonbuild.depfile
import mesonbuild.dependencies.base
import mesonbuild.dependencies.factory
import mesonbuild.envconfig
import mesonbuild.environment
import mesonbuild.coredata
import mesonbuild.modules.gnome
from mesonbuild.interpreter import Interpreter
from mesonbuild.ast import AstInterpreter
from mesonbuild.mesonlib import (
    MachineChoice, OptionKey
)
from mesonbuild.compilers import (
    detect_c_compiler, detect_cpp_compiler
)
import mesonbuild.modules.pkgconfig


from run_tests import (
    FakeBuild, get_fake_env
)

from .helpers import *

@unittest.skipIf(is_tarball(), 'Skipping because this is a tarball release')
class DataTests(unittest.TestCase):

    def test_snippets(self):
        hashcounter = re.compile('^ *(#)+')
        snippet_dir = Path('docs/markdown/snippets')
        self.assertTrue(snippet_dir.is_dir())
        for f in snippet_dir.glob('*'):
            self.assertTrue(f.is_file())
            if f.parts[-1].endswith('~'):
                continue
            if f.suffix == '.md':
                in_code_block = False
                with f.open(encoding='utf-8') as snippet:
                    for line in snippet:
                        if line.startswith('    '):
                            continue
                        if line.startswith('```'):
                            in_code_block = not in_code_block
                        if in_code_block:
                            continue
                        m = re.match(hashcounter, line)
                        if m:
                            self.assertEqual(len(m.group(0)), 2, 'All headings in snippets must have two hash symbols: ' + f.name)
                self.assertFalse(in_code_block, 'Unclosed code block.')
            else:
                if f.name != 'add_release_note_snippets_here':
                    self.assertTrue(False, 'A file without .md suffix in snippets dir: ' + f.name)

    def test_compiler_options_documented(self):
        '''
        Test that C and C++ compiler options and base options are documented in
        Builtin-Options.md. Only tests the default compiler for the current
        platform on the CI.
        '''
        md = None
        with open('docs/markdown/Builtin-options.md', encoding='utf-8') as f:
            md = f.read()
        self.assertIsNotNone(md)
        env = get_fake_env()
        # FIXME: Support other compilers
        cc = detect_c_compiler(env, MachineChoice.HOST)
        cpp = detect_cpp_compiler(env, MachineChoice.HOST)
        for comp in (cc, cpp):
            for opt in comp.get_options():
                self.assertIn(str(opt), md)
            for opt in comp.base_options:
                self.assertIn(str(opt), md)
        self.assertNotIn('b_unknown', md)

    @staticmethod
    def _get_section_content(name, sections, md):
        for section in sections:
            if section and section.group(1) == name:
                try:
                    next_section = next(sections)
                    end = next_section.start()
                except StopIteration:
                    end = len(md)
                # Extract the content for this section
                return md[section.end():end]
        raise RuntimeError(f'Could not find "{name}" heading')

    def test_builtin_options_documented(self):
        '''
        Test that universal options and base options are documented in
        Builtin-Options.md.
        '''
        from itertools import tee
        md = None
        with open('docs/markdown/Builtin-options.md', encoding='utf-8') as f:
            md = f.read()
        self.assertIsNotNone(md)

        found_entries = set()
        sections = re.finditer(r"^## (.+)$", md, re.MULTILINE)
        # Extract the content for this section
        content = self._get_section_content("Universal options", sections, md)
        subsections = tee(re.finditer(r"^### (.+)$", content, re.MULTILINE))
        subcontent1 = self._get_section_content("Directories", subsections[0], content)
        subcontent2 = self._get_section_content("Core options", subsections[1], content)
        subcontent3 = self._get_section_content("Module options", sections, md)
        for subcontent in (subcontent1, subcontent2, subcontent3):
            # Find the option names
            options = set()
            # Match either a table row or a table heading separator: | ------ |
            rows = re.finditer(r"^\|(?: (\w+) .* | *-+ *)\|", subcontent, re.MULTILINE)
            # Skip the header of the first table
            next(rows)
            # Skip the heading separator of the first table
            next(rows)
            for m in rows:
                value = m.group(1)
                # End when the `buildtype` table starts
                if value is None:
                    break
                options.add(value)
            self.assertEqual(len(found_entries & options), 0)
            found_entries |= options

        self.assertEqual(found_entries, {
            *(str(k.evolve(module=None)) for k in mesonbuild.coredata.BUILTIN_OPTIONS),
            *(str(k.evolve(module=None)) for k in mesonbuild.coredata.BUILTIN_OPTIONS_PER_MACHINE),
        })

        # Check that `buildtype` table inside `Core options` matches how
        # setting of builtin options behaves
        #
        # Find all tables inside this subsection
        tables = re.finditer(r"^\| (\w+) .* \|\n\| *[-|\s]+ *\|$", subcontent2, re.MULTILINE)
        # Get the table we want using the header of the first column
        table = self._get_section_content('buildtype', tables, subcontent2)
        # Get table row data
        rows = re.finditer(r"^\|(?: (\w+)\s+\| (\w+)\s+\| (\w+) .* | *-+ *)\|", table, re.MULTILINE)
        env = get_fake_env()
        for m in rows:
            buildtype, debug, opt = m.groups()
            if debug == 'true':
                debug = True
            elif debug == 'false':
                debug = False
            else:
                raise RuntimeError(f'Invalid debug value {debug!r} in row:\n{m.group()}')
            env.coredata.set_option(OptionKey('buildtype'), buildtype)
            self.assertEqual(env.coredata.options[OptionKey('buildtype')].value, buildtype)
            self.assertEqual(env.coredata.options[OptionKey('optimization')].value, opt)
            self.assertEqual(env.coredata.options[OptionKey('debug')].value, debug)

    def test_cpu_families_documented(self):
        with open("docs/markdown/Reference-tables.md", encoding='utf-8') as f:
            md = f.read()
        self.assertIsNotNone(md)

        sections = re.finditer(r"^## (.+)$", md, re.MULTILINE)
        content = self._get_section_content("CPU families", sections, md)
        # Find the list entries
        arches = [m.group(1) for m in re.finditer(r"^\| (\w+) +\|", content, re.MULTILINE)]
        # Drop the header
        arches = set(arches[1:])
        self.assertEqual(arches, set(mesonbuild.environment.known_cpu_families))

    def test_markdown_files_in_sitemap(self):
        '''
        Test that each markdown files in docs/markdown is referenced in sitemap.txt
        '''
        with open("docs/sitemap.txt", encoding='utf-8') as f:
            md = f.read()
        self.assertIsNotNone(md)
        toc = list(m.group(1) for m in re.finditer(r"^\s*(\w.*)$", md, re.MULTILINE))
        markdownfiles = [f.name for f in Path("docs/markdown").iterdir() if f.is_file() and f.suffix == '.md']
        exceptions = ['_Sidebar.md']
        for f in markdownfiles:
            if f not in exceptions and not f.startswith('_include'):
                self.assertIn(f, toc)

    def test_modules_in_navbar(self):
        '''
        Test that each module is referenced in navbar_links.html
        '''
        with open("docs/theme/extra/templates/navbar_links.html", encoding='utf-8') as f:
            html = f.read().lower()
        self.assertIsNotNone(html)
        for f in Path('mesonbuild/modules').glob('*.py'):
            if f.name in {'modtest.py', 'qt.py', '__init__.py'}:
                continue
            name = f'{f.stem}-module.html'
            name = name.replace('unstable_', '')
            name = name.replace('python3', 'python-3')
            name = name.replace('_', '-')
            self.assertIn(name, html)

    def test_vim_syntax_highlighting(self):
        '''
        Ensure that vim syntax highlighting files were updated for new
        functions in the global namespace in build files.
        '''
        env = get_fake_env()
        interp = Interpreter(FakeBuild(env), mock=True)
        with open('data/syntax-highlighting/vim/syntax/meson.vim', encoding='utf-8') as f:
            res = re.search(r'syn keyword mesonBuiltin(\s+\\\s\w+)+', f.read(), re.MULTILINE)
            defined = set([a.strip() for a in res.group().split('\\')][1:])
            self.assertEqual(defined, set(chain(interp.funcs.keys(), interp.builtin.keys())))

    def test_all_functions_defined_in_ast_interpreter(self):
        '''
        Ensure that the all functions defined in the Interpreter are also defined
        in the AstInterpreter (and vice versa).
        '''
        env = get_fake_env()
        interp = Interpreter(FakeBuild(env), mock=True)
        astint = AstInterpreter('.', '', '')
        self.assertEqual(set(interp.funcs.keys()), set(astint.funcs.keys()))
