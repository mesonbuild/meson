# SPDX-License-Identifier: Apache-2.0
# Copyright 2021 The Meson development team
# Copyright © 2024-2025 Intel Corporation

from __future__ import annotations
import argparse
import difflib
import json
import os
import pickle
import subprocess
import tempfile
import textwrap
import shutil
import sys
from unittest import skipIf, SkipTest
from pathlib import Path

from .baseplatformtests import BasePlatformTests
from .helpers import skip_if_not_language, skip_if_no_cmake, IS_CI
from mesonbuild.mesonlib import EnvironmentVariables, ExecutableSerialisation, MesonException, is_linux, python_command, windows_proof_rmtree
from mesonbuild import mformat
from mesonbuild.mformat import Formatter, match_path
from mesonbuild.interpreterbase import InvalidArguments
from mesonbuild.optinterpreter import OptionInterpreter, OptionException
from mesonbuild.options import OptionStore
from run_tests import Backend

@skipIf(IS_CI and not is_linux(), "Run only on fast platforms")
class PlatformAgnosticTests(BasePlatformTests):
    '''
    Tests that does not need to run on all platforms during CI
    '''

    def test_relative_find_program(self):
        '''
        Tests that find_program() with a relative path does not find the program
        in current workdir.
        '''
        testdir = os.path.join(self.unit_test_dir, '100 relative find program')
        self.init(testdir, workdir=testdir)

    def test_invalid_option_names(self):
        store = OptionStore(False)
        interp = OptionInterpreter(store, '')

        def write_file(code: str):
            with tempfile.NamedTemporaryFile('w', dir=self.builddir, encoding='utf-8', delete=False) as f:
                f.write(code)
                return f.name

        fname = write_file("option('default_library', type: 'string')")
        self.assertRaisesRegex(OptionException, 'Option name default_library is reserved.',
                               interp.process, fname)

        fname = write_file("option('c_anything', type: 'string')")
        self.assertRaisesRegex(OptionException, 'Option name c_anything is reserved.',
                               interp.process, fname)

        fname = write_file("option('b_anything', type: 'string')")
        self.assertRaisesRegex(OptionException, 'Option name b_anything is reserved.',
                               interp.process, fname)

        fname = write_file("option('backend_anything', type: 'string')")
        self.assertRaisesRegex(OptionException, 'Option name backend_anything is reserved.',
                               interp.process, fname)

        fname = write_file("option('foo.bar', type: 'string')")
        self.assertRaisesRegex(InvalidArguments, r'.*option names can only contain letters, numbers, and dashes$',
                               interp.process, fname)

        # platlib is allowed, only python.platlib is reserved.
        fname = write_file("option('platlib', type: 'string')")
        interp.process(fname)

    def test_option_validation(self):
        """Test cases that are not catch by the optinterpreter itself."""
        store = OptionStore(False)
        interp = OptionInterpreter(store, '')

        def write_file(code: str):
            with tempfile.NamedTemporaryFile('w', dir=self.builddir, encoding='utf-8', delete=False) as f:
                f.write(code)
                return f.name

        fname = write_file("option('intminmax', type: 'integer', value: 10, min: 0, max: 5)")
        self.assertRaisesRegex(MesonException, 'Value 10 for option "intminmax" is more than maximum value 5.',
                               interp.process, fname)

        fname = write_file("option('array', type: 'array', choices : ['one', 'two', 'three'], value : ['one', 'four'])")
        self.assertRaisesRegex(MesonException, 'Value "four" for option "array" is not in allowed choices: "one, two, three"',
                               interp.process, fname)

        fname = write_file("option('array', type: 'array', choices : ['one', 'two', 'three'], value : ['four', 'five', 'six'])")
        self.assertRaisesRegex(MesonException, 'Values "four, five, six" for option "array" are not in allowed choices: "one, two, three"',
                               interp.process, fname)

    def test_python_dependency_without_pkgconfig(self):
        testdir = os.path.join(self.unit_test_dir, '102 python without pkgconfig')
        self.init(testdir, override_envvars={'PKG_CONFIG': 'notfound'})

    def test_vala_target_with_internal_glib(self):
        testdir = os.path.join(self.unit_test_dir, '131 vala internal glib')
        for run in [{ 'version': '2.84.4', 'expected': '2.84'}, { 'version': '2.85.2', 'expected': '2.84' }]:
            self.new_builddir()
            self.init(testdir, extra_args=[f'-Dglib-version={run["version"]}'])
            try:
                with open(os.path.join(self.builddir, 'meson-info', 'intro-targets.json'), 'r', encoding='utf-8') as tgt_intro:
                    intro = json.load(tgt_intro)
                    target = list(filter(lambda tgt: tgt['name'] == 'vala-tgt', intro))
                    self.assertLength(target, 1)
                    sources = target[0]['target_sources']
                    vala_sources = filter(lambda src: src.get('language') == 'vala', sources)
                    for src in vala_sources:
                        self.assertIn(('--target-glib', run['expected']), zip(src['parameters'], src['parameters'][1:]))
            except FileNotFoundError:
                self.skipTest('Current backend does not produce introspection data')

    def test_dependency_extra_files_introspection(self):
        '''
        Test that extra_files of an internal dependency are exposed together with the target's own.
        https://github.com/mesonbuild/meson/issues/15863
        '''
        testdir = os.path.join(self.unit_test_dir, '145 dependency extra files')
        self.init(testdir)
        targets = self.introspect('--targets')
        self.assertEqual(len(targets), 1)
        names = sorted(os.path.basename(f) for f in targets[0]['extra_files'])
        self.assertEqual(names, ['dep.txt', 'own.txt'])

    def test_debug_function_outputs_to_meson_log(self):
        testdir = os.path.join(self.unit_test_dir, '104 debug function')
        log_msg = 'This is an example debug output, should only end up in debug log'
        output = self.init(testdir)

        # Check if message is not printed to stdout while configuring
        self.assertNotIn(log_msg, output)

        # Check if message is written to the meson log
        mesonlog = self.get_meson_log_raw()
        self.assertIn(log_msg, mesonlog)

    def test_new_subproject_reconfigure(self):
        testdir = os.path.join(self.unit_test_dir, '108 new subproject on reconfigure')
        self.init(testdir)
        self.build()

        # Enable the subproject "foo" and reconfigure, this is used to fail
        # because per-subproject builtin options were not initialized:
        # https://github.com/mesonbuild/meson/issues/10225.
        self.setconf('-Dfoo=enabled')
        self.build('reconfigure')

    def check_connectivity(self):
        import urllib
        try:
            with urllib.request.urlopen('https://wrapdb.mesonbuild.com'):
                pass
        except urllib.error.URLError as e:
            self.skipTest('No internet connectivity: ' + str(e))

    def test_update_wrapdb(self):
        self.check_connectivity()
        # Write the project into a temporary directory because it will add files
        # into subprojects/ and we don't want to pollute meson source tree.
        with tempfile.TemporaryDirectory() as testdir:
            with Path(testdir, 'meson.build').open('w', encoding='utf-8') as f:
                f.write(textwrap.dedent(
                    '''
                    project('wrap update-db',
                      default_options: ['wrap_mode=forcefallback'])

                    zlib_dep = dependency('zlib')
                    assert(zlib_dep.type_name() == 'internal')
                    '''))
            subprocess.check_call(self.wrap_command + ['update-db'], cwd=testdir)
            self.init(testdir, workdir=testdir)

    def test_none_backend(self):
        testdir = os.path.join(self.python_test_dir, '7 install path')

        self.init(testdir, extra_args=['--backend=none'], override_envvars={'NINJA': 'absolutely false command'})
        self.assertPathDoesNotExist(os.path.join(self.builddir, 'build.ninja'))

        self.run_tests(inprocess=True, override_envvars={})

        out = self._run(self.meson_command + ['install', f'--destdir={self.installdir}'], workdir=self.builddir)
        self.assertNotIn('Only ninja backend is supported to rebuild the project before installation.', out)

        with open(os.path.join(testdir, 'test.json'), 'rb') as f:
            dat = json.load(f)
        for i in dat['installed']:
            self.assertPathExists(os.path.join(self.installdir, i['file']))

    def test_change_backend(self):
        if self.backend != Backend.ninja:
            raise SkipTest('Only useful to test if backend is ninja.')

        testdir = os.path.join(self.python_test_dir, '7 install path')
        self.init(testdir)

        # no-op change works
        with self.subTest('set the option to the same value'):
            self.setconf('--backend=ninja')
            self.init(testdir, extra_args=['--reconfigure', '--backend=ninja'])

        # Change backend option is not allowed
        with self.subTest('Changing the backend'):
            with self.assertRaises(subprocess.CalledProcessError) as cm:
                self.setconf('-Dbackend=none')
            self.assertIn('ERROR: Tried to modify read only option "backend"', cm.exception.stdout)

        # Check that the new value was not written in the store.
        with self.subTest('option is stored correctly'):
            self.assertEqual(self.getconf('backend'), 'ninja')

        # Wipe with a different backend is allowed
        with self.subTest('Changing the backend with wipe'):
            self.init(testdir, extra_args=['--wipe', '--backend=none'])

            self.assertEqual(self.getconf('backend'), 'none')

    def test_validate_dirs(self):
        testdir = os.path.join(self.common_test_dir, '1 trivial')

        # Using parent as source directory should fail
        self.builddir = os.path.dirname(os.getcwd())
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            self.init(testdir)
        self.assertIn('cannot be a parent of source directory', cm.exception.stdout)

        # Reconfigure of empty builddir should work
        self.new_builddir()
        self.init(testdir, extra_args=['--reconfigure'])

        # Reconfigure of not empty builddir should work
        self.new_builddir()
        Path(self.builddir, 'dummy').touch()
        self.init(testdir, extra_args=['--reconfigure', '--buildtype=custom'])

        # Setup a valid builddir should update options but not reconfigure
        self.assertEqual(self.getconf('buildtype'), 'custom')
        o = self.init(testdir, extra_args=['-Dbuildtype=release'])
        self.assertIn('Directory already configured', o)
        self.assertNotIn('The Meson build system', o)
        self.assertEqual(self.getconf('buildtype'), 'release')

        # Wipe of empty builddir should work
        self.new_builddir()
        self.init(testdir, extra_args=['--wipe'])

        # Wipe of partial builddir should work
        self.new_builddir()
        Path(self.builddir, 'meson-private').mkdir()
        Path(self.builddir, 'dummy').touch()
        self.init(testdir, extra_args=['--wipe'])

        # Wipe of not empty builddir should fail
        self.new_builddir()
        Path(self.builddir, 'dummy').touch()
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            self.init(testdir, extra_args=['--wipe'])
        self.assertIn('Directory is not empty', cm.exception.stdout)

    def test_scripts_loaded_modules(self):
        '''
        Simulate a wrapped command, as done for custom_target() that capture
        output. The script will print all python modules loaded and we verify
        that it contains only an acceptable subset. Loading too many modules
        slows down the build when many custom targets get wrapped.

        This list must not be edited without a clear rationale for why it is
        acceptable to do so!
        '''
        es = ExecutableSerialisation(python_command + ['-c', 'exit(0)'], env=EnvironmentVariables())
        p = Path(self.builddir, 'exe.dat')
        with p.open('wb') as f:
            pickle.dump(es, f)
        cmd = self.meson_command + ['--internal', 'test_loaded_modules', '--unpickle', str(p)]
        p = subprocess.run(cmd, stdout=subprocess.PIPE)
        all_modules = json.loads(p.stdout.splitlines()[0])
        meson_modules = [m for m in all_modules if m.startswith('mesonbuild')]
        expected_meson_modules = [
            'mesonbuild',
            'mesonbuild._pathlib',
            'mesonbuild.utils',
            'mesonbuild.utils.core',
            'mesonbuild.mesonmain',
            'mesonbuild.mlog',
            'mesonbuild.scripts',
            'mesonbuild.scripts.meson_exe',
            'mesonbuild.scripts.test_loaded_modules'
        ]
        self.assertEqual(sorted(expected_meson_modules), sorted(meson_modules))

    def test_setup_loaded_modules(self):
        '''
        Execute a very basic meson.build and capture a list of all python
        modules loaded. We verify that it contains only an acceptable subset.
        Loading too many modules slows down `meson setup` startup time and
        gives a perception that meson is slow.

        Adding more modules to the default startup flow is not an unreasonable
        thing to do as new features are added, but keeping track of them is
        good.
        '''
        testdir = os.path.join(self.unit_test_dir, '116 empty project')

        self.init(testdir)
        self._run(self.meson_command + ['--internal', 'regenerate', '--profile-self', testdir, self.builddir])
        with open(os.path.join(self.builddir, 'meson-logs', 'profile-startup-modules.json'), encoding='utf-8') as f:
                data = json.load(f)['meson']

        with open(os.path.join(testdir, 'expected_mods.json'), encoding='utf-8') as f:
            expected = json.load(f)['meson']

        self.assertEqual(data['modules'], expected['modules'])
        self.assertEqual(data['count'], expected['count'])

    def test_meson_package_cache_dir(self):
        # Copy testdir into temporary directory to not pollute meson source tree.
        testdir = os.path.join(self.unit_test_dir, '118 meson package cache dir')
        srcdir = os.path.join(self.builddir, 'srctree')
        shutil.copytree(testdir, srcdir)
        builddir = os.path.join(srcdir, '_build')
        self.change_builddir(builddir)
        self.init(srcdir, override_envvars={'MESON_PACKAGE_CACHE_DIR': os.path.join(srcdir, 'cache_dir')})

    def test_cmake_openssl_not_found_bug(self):
        """Issue #12098"""
        testdir = os.path.join(self.unit_test_dir, '119 openssl cmake bug')
        self.meson_native_files.append(os.path.join(testdir, 'nativefile.ini'))
        out = self.init(testdir, allow_fail=True)
        self.assertNotIn('Unhandled python exception', out)

    @skip_if_no_cmake
    def test_cmake_native_subproject_ctgt(self):
        """Issue #16314"""
        testdir = os.path.join(self.unit_test_dir, '144 cmake native subproject ctgt')
        wrapper = os.path.join(testdir, 'wrapper.py')
        with tempfile.TemporaryDirectory() as d:
            overlay = os.path.join(d, 'wrapper.txt')
            with open(overlay, 'w', encoding='utf-8') as f:
                f.write(f"[binaries]\nexe_wrapper = {[sys.executable, wrapper]!r}\n")
            self.meson_cross_files = [os.path.join(self.src_root, 'cross', 'linux-mingw-w64-64bit.txt'),
                                      overlay]
            self.init(testdir)
            self.build()

    def test_editorconfig_match_path(self):
        '''match_path function used to parse editorconfig in meson format'''
        cases = [
            ('a.txt', '*.txt', True),
            ('a.txt', '?.txt', True),
            ('a.txt', 'a.t?t', True),
            ('a.txt', '*.build', False),

            ('/a.txt', '*.txt', True),
            ('/a.txt', '/*.txt', True),
            ('a.txt', '/*.txt', False),

            ('a/b/c.txt', 'a/b/*.txt', True),
            ('a/b/c.txt', 'a/*/*.txt', True),
            ('a/b/c.txt', '*/*.txt', True),
            ('a/b/c.txt', 'b/*.txt', True),
            ('a/b/c.txt', 'a/*.txt', False),

            ('a/b/c/d.txt', 'a/**/*.txt', True),
            ('a/b/c/d.txt', 'a/*', False),
            ('a/b/c/d.txt', 'a/**', True),

            ('a.txt', '[abc].txt', True),
            ('a.txt', '[!xyz].txt', True),
            ('a.txt', '[xyz].txt', False),
            ('a.txt', '[!abc].txt', False),

            ('a.txt', '{a,b,c}.txt', True),
            ('a.txt', '*.{txt,tex,cpp}', True),
            ('a.hpp', '*.{txt,tex,cpp}', False),

            ('a1.txt', 'a{0..9}.txt', True),
            ('a001.txt', 'a{0..9}.txt', True),
            ('a-1.txt', 'a{-10..10}.txt', True),
            ('a99.txt', 'a{0..9}.txt', False),
            ('a099.txt', 'a{0..9}.txt', False),
            ('a-1.txt', 'a{0..10}.txt', False),
        ]

        for filename, pattern, expected in cases:
            self.assertTrue(match_path(filename, pattern) is expected, f'{filename} -> {pattern}')

    def test_format_invalid_config_key(self) -> None:
        fd, fname = tempfile.mkstemp(suffix='.ini', text=True)
        self.addCleanup(os.unlink, fname)

        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write('not_an_option = 42\n')

        with self.assertRaises(MesonException):
            Formatter(Path(fname), use_editor_config=False, fetch_subdirs=False)

    def test_format_invalid_config_value(self) -> None:
        fd, fname = tempfile.mkstemp(suffix='.ini', text=True)
        self.addCleanup(os.unlink, fname)

        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write('max_line_length = string\n')

        with self.assertRaises(MesonException):
            Formatter(Path(fname), use_editor_config=False, fetch_subdirs=False)

    def test_format_invalid_editorconfig_value(self) -> None:
        dirpath = tempfile.mkdtemp()
        self.addCleanup(windows_proof_rmtree, dirpath)

        editorconfig = Path(dirpath, '.editorconfig')
        with open(editorconfig, 'w', encoding='utf-8') as handle:
            handle.write('[*]\n')
            handle.write('indent_size = string\n')

        formatter = Formatter(None, use_editor_config=True, fetch_subdirs=False)
        with self.assertRaises(MesonException):
            formatter.load_editor_config(editorconfig)

    def check_format_snippets(self, testdir: Path, use_editor_config: bool) -> None:
        """Format each snippet of testdir, and compare with the expected output.

        foo.meson must be formatted as foo.expected.meson, or must be unchanged
        if there is no expected file. Options are read from the
        "# format-test: key = value" comments of the snippet. All snippets
        are checked, and the failures are reported together.
        """
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(windows_proof_rmtree, tmpdir)
        config = Path(tmpdir, 'meson.format')
        failures = []
        for source in sorted(testdir.rglob('*.meson')):
            if source.name.endswith('.expected.meson'):
                continue
            name = source.relative_to(testdir).as_posix()
            code = source.read_text(encoding='utf-8')
            options = [line.partition('format-test:')[2] for line in code.splitlines()
                       if line.startswith('# format-test:')]
            config.write_text('\n'.join(options) + '\n', encoding='utf-8')
            expected_file = source.with_suffix('.expected.meson')
            expected = expected_file.read_text(encoding='utf-8') if expected_file.exists() else code
            expected_name = expected_file.relative_to(testdir).as_posix() if expected_file.exists() else name
            try:
                formatter = Formatter(config, use_editor_config=use_editor_config, fetch_subdirs=False)
                formatted = formatter.format(code, source)
                if formatted == expected:
                    name = f'{expected_name} formatted again'
                    formatted = formatter.format(expected, source)
            except MesonException as e:
                failures.append(f'{name}: {e}\n')
                continue
            if formatted != expected:
                failures.extend(difflib.unified_diff(expected.splitlines(keepends=True), formatted.splitlines(keepends=True),
                                                     expected_name, f'{name} (formatted)'))
        if failures:
            self.fail('formatted snippets differ from expected:\n' + ''.join(failures))

    def test_format_snippets(self) -> None:
        self.check_format_snippets(Path(self.unit_test_dir, '141 format'), use_editor_config=False)

    def test_format_editorconfig(self) -> None:
        testdir = Path(self.unit_test_dir, '142 format editorconfig')
        # enabled from the use_editor_config option of the snippets, then from the -e argument
        self.check_format_snippets(testdir, use_editor_config=False)
        self.check_format_snippets(testdir, use_editor_config=True)

    def test_format_end_of_line(self) -> None:
        dirpath = tempfile.mkdtemp()
        self.addCleanup(windows_proof_rmtree, dirpath)
        source = Path(dirpath, 'source.meson')
        source.write_bytes(b'x=1\ny=2\n')
        output = Path(dirpath, 'output.meson')
        config = Path(dirpath, 'meson.format')
        editorconfig = Path(dirpath, '.editorconfig')

        parser = argparse.ArgumentParser()
        mformat.add_arguments(parser)

        def format_file(*args: str) -> bytes:
            mformat.run(parser.parse_args([*args, '-c', str(config), '-o', str(output), str(source)]))
            return output.read_bytes()

        cases = [('lf', b'\n'), ('crlf', b'\r\n'), ('cr', b'\r'), ('native', os.linesep.encode())]
        for end_of_line, newline in cases:
            expected = b'x = 1' + newline + b'y = 2' + newline
            config.write_text(f'end_of_line = {end_of_line}\n', encoding='utf-8')
            self.assertEqual(expected, format_file(), f'end_of_line = {end_of_line}')

            if end_of_line != 'native':
                config.write_text('', encoding='utf-8')
                editorconfig.write_text(f'root = true\n[*]\nend_of_line = {end_of_line}\n', encoding='utf-8')
                self.assertEqual(expected, format_file('-e'), f'end_of_line = {end_of_line} in .editorconfig')

    def test_format_find_configuration(self) -> None:
        """meson.format is found in the parent directories of the source file"""
        dirpath = tempfile.mkdtemp()
        self.addCleanup(windows_proof_rmtree, dirpath)
        Path(dirpath, 'meson.format').write_text("indent_by = '  '\n", encoding='utf-8')
        source = Path(dirpath, 'subdir', 'meson.build')
        source.parent.mkdir()
        source.write_text('if true\nx = 1\nendif\n', encoding='utf-8')
        output = Path(dirpath, 'output.meson')

        parser = argparse.ArgumentParser()
        mformat.add_arguments(parser)
        mformat.run(parser.parse_args(['-o', str(output), str(source)]))
        self.assertEqual('if true\n  x = 1\nendif\n', output.read_text(encoding='utf-8'))

    def test_format_directive_errors(self) -> None:
        formatter = Formatter(None, use_editor_config=False, fetch_subdirs=False)
        errors = [
            ('x = [1, 2]  # meson-format off\n', 1, 12, 'must be on its own line'),
            ('if true\n    x = 1 # meson-format on\nendif\n', 2, 10, 'must be on its own line'),
            ("x = files(\n    'b.c',\n    # meson-format off\n    'a.c',\n)\n", 3, 4, 'must enclose whole statements'),
            ('x = [\n    # meson-format on\n]\n', 2, 4, 'must enclose whole statements'),
            ('if (true and\n# meson-format off\nfalse)\nendif\n', 2, 0, 'must enclose whole statements'),
            ('x = 1  # fmt: off\n', 1, 7, '"# fmt: off" directive must be on its own line'),
            ('x = [\n    # fmt:on\n]\n', 2, 4, '"# fmt:on" directive must enclose whole statements'),
        ]
        for code, lineno, colno, message in errors:
            with self.subTest(code=code):
                with self.assertRaisesRegex(MesonException, message) as cm:
                    formatter.format(code, Path())
                self.assertEqual((cm.exception.lineno, cm.exception.colno), (lineno, colno))

    def test_format_directives_recursive(self) -> None:
        dirpath = tempfile.mkdtemp()
        self.addCleanup(windows_proof_rmtree, dirpath)

        root = Path(dirpath, 'meson.build')
        root.write_text("project('a')\nsubdir('sub')\n# meson-format off\nx  =  [1,2]\n", encoding='utf-8')
        sub = Path(dirpath, 'sub', 'meson.build')
        sub.parent.mkdir()
        sub.write_text('y  =  [1,2]\n', encoding='utf-8')

        self._run(self.meson_command + ['format', '-r', '-i'], workdir=dirpath)
        self.assertEqual("project('a')\nsubdir('sub')\n# meson-format off\nx  =  [1,2]\n",
                         root.read_text(encoding='utf-8'))
        self.assertEqual('y = [1, 2]\n', sub.read_text(encoding='utf-8'))

    def test_error_configuring_subdir(self):
        testdir = os.path.join(self.common_test_dir, '152 index customtarget')
        out = self.init(os.path.join(testdir, 'subdir'), allow_fail=True)

        self.assertIn('first statement must be a call to project()', out)
        # provide guidance diagnostics by finding a file whose first AST statement is project()
        self.assertIn(f'Did you mean to run meson from the directory: "{testdir}"?', out)

    def test_reconfigure_base_options(self):
        testdir = os.path.join(self.unit_test_dir, '123 reconfigure base options')
        out = self.init(testdir, extra_args=['-Db_ndebug=true'])
        self.assertIn('\nMessage: b_ndebug: true\n', out)
        self.assertIn('\nMessage: c_std: c89\n', out)

        out = self.init(testdir, extra_args=['--reconfigure', '-Db_ndebug=if-release', '-Dsub:b_ndebug=false', '-Dc_std=c99', '-Dsub:c_std=c11'])
        self.assertIn('\n    b_ndebug    : if-release\n', out)
        self.assertIn('\n    c_std       : c99\n', out)
        self.assertIn('\n    sub:b_ndebug: false\n', out)
        self.assertIn('\n    sub:c_std   : c11\n', out)

    def test_setup_with_unknown_option(self):
        testdir = os.path.join(self.common_test_dir, '1 trivial')

        with self.subTest('unknown user option'):
            out = self.init(testdir, extra_args=['-Dnot_an_option=1'], allow_fail=True)
            self.assertIn('ERROR: Unknown option: "not_an_option"', out)

        with self.subTest('unknown builtin option'):
            self.new_builddir()
            out = self.init(testdir, extra_args=['-Db_not_an_option=1'], allow_fail=True)
            self.assertIn('ERROR: Unknown option: "b_not_an_option"', out)


    def test_configure_new_option(self) -> None:
        """Adding a new option without reconfiguring should work."""
        testdir = self.copy_srcdir(os.path.join(self.common_test_dir, '40 options'))
        self.init(testdir)
        with open(os.path.join(testdir, 'meson_options.txt'), 'a', encoding='utf-8') as f:
            f.write("option('new_option', type : 'boolean', value : false)")
        self.setconf('-Dnew_option=true')
        self.assertEqual(self.getconf('new_option'), True)

    def test_configure_removed_option(self) -> None:
        """Removing an options without reconfiguring should still give an error."""
        testdir = self.copy_srcdir(os.path.join(self.common_test_dir, '40 options'))
        self.init(testdir)
        with open(os.path.join(testdir, 'meson_options.txt'), 'r', encoding='utf-8') as f:
            opts = f.readlines()
        with open(os.path.join(testdir, 'meson_options.txt'), 'w', encoding='utf-8') as f:
            for line in opts:
                if line.startswith("option('neg'"):
                    continue
                f.write(line)
        with self.assertRaises(subprocess.CalledProcessError) as e:
            self.setconf('-Dneg_int_opt=0')
        self.assertIn('Unknown option: "neg_int_opt"', e.exception.stdout)

    def test_reconfigure_option(self) -> None:
        testdir = self.copy_srcdir(os.path.join(self.common_test_dir, '40 options'))
        self.init(testdir)
        self.assertEqual(self.getconf('neg_int_opt'), -3)
        with self.assertRaises(subprocess.CalledProcessError):
            self.init(testdir, extra_args=['--reconfigure', '-Dneg_int_opt=0'])
        self.assertEqual(self.getconf('neg_int_opt'), -3)
        self.init(testdir, extra_args=['--reconfigure', '-Dneg_int_opt=-2'])
        self.assertEqual(self.getconf('neg_int_opt'), -2)

    def test_configure_option_changed_constraints(self) -> None:
        """Changing the constraints of an option without reconfiguring should work."""
        testdir = self.copy_srcdir(os.path.join(self.common_test_dir, '40 options'))
        self.init(testdir)
        with open(os.path.join(testdir, 'meson_options.txt'), 'r', encoding='utf-8') as f:
            opts = f.readlines()
        with open(os.path.join(testdir, 'meson_options.txt'), 'w', encoding='utf-8') as f:
            for line in opts:
                if line.startswith("option('neg'"):
                    f.write("option('neg_int_opt', type : 'integer', min : -10, max : 10, value : -3)\n")
                else:
                    f.write(line)
        self.setconf('-Dneg_int_opt=-10')
        self.assertEqual(self.getconf('neg_int_opt'), -10)

    def test_configure_meson_options_txt_to_meson_options(self) -> None:
        """Changing from a meson_options.txt to meson.options should still be detected."""
        testdir = self.copy_srcdir(os.path.join(self.common_test_dir, '40 options'))
        self.init(testdir)
        with open(os.path.join(testdir, 'meson_options.txt'), 'r', encoding='utf-8') as f:
            opts = f.readlines()
        with open(os.path.join(testdir, 'meson_options.txt'), 'w', encoding='utf-8') as f:
            for line in opts:
                if line.startswith("option('neg'"):
                    f.write("option('neg_int_opt', type : 'integer', min : -10, max : 10, value : -3)\n")
                else:
                    f.write(line)
        shutil.move(os.path.join(testdir, 'meson_options.txt'), os.path.join(testdir, 'meson.options'))
        self.setconf('-Dneg_int_opt=-10')
        self.assertEqual(self.getconf('neg_int_opt'), -10)

    def test_configure_options_file_deleted(self) -> None:
        """Deleting all option files should make seting a project option an error."""
        testdir = self.copy_srcdir(os.path.join(self.common_test_dir, '40 options'))
        self.init(testdir)
        os.unlink(os.path.join(testdir, 'meson_options.txt'))
        with self.assertRaises(subprocess.CalledProcessError) as e:
            self.setconf('-Dneg_int_opt=0')
        self.assertIn('Unknown option: "neg_int_opt"', e.exception.stdout)

    def test_configure_options_file_added(self) -> None:
        """A new project option file should be detected."""
        testdir = self.copy_srcdir(os.path.join(self.common_test_dir, '1 trivial'))
        self.init(testdir)
        with open(os.path.join(testdir, 'meson.options'), 'w', encoding='utf-8') as f:
            f.write("option('new_option', type : 'string', value : 'foo')")
        self.setconf('-Dnew_option=bar')
        self.assertEqual(self.getconf('new_option'), 'bar')

    def test_configure_options_file_added_old(self) -> None:
        """A new project option file should be detected."""
        testdir = self.copy_srcdir(os.path.join(self.common_test_dir, '1 trivial'))
        self.init(testdir)
        with open(os.path.join(testdir, 'meson_options.txt'), 'w', encoding='utf-8') as f:
            f.write("option('new_option', type : 'string', value : 'foo')")
        self.setconf('-Dnew_option=bar')
        self.assertEqual(self.getconf('new_option'), 'bar')

    def test_configure_new_option_subproject(self) -> None:
        """Adding a new option to a subproject without reconfiguring should work."""
        testdir = self.copy_srcdir(os.path.join(self.common_test_dir, '43 subproject options'))
        self.init(testdir)
        with open(os.path.join(testdir, 'subprojects/subproject/meson_options.txt'), 'a', encoding='utf-8') as f:
            f.write("option('new_option', type : 'boolean', value : false)")
        self.setconf('-Dsubproject:new_option=true')
        self.assertEqual(self.getconf('subproject:new_option'), True)

    def test_mtest_rebuild_deps(self):
        testdir = os.path.join(self.unit_test_dir, '106 underspecified mtest')
        self.init(testdir)

        with self.assertRaises(subprocess.CalledProcessError):
            self._run(self.mtest_command)
        self.clean()

        with self.assertRaises(subprocess.CalledProcessError):
            self._run(self.mtest_command + ['runner-without-dep'])
        self.clean()

        self._run(self.mtest_command + ['runner-with-exedep'])

    def test_buildtype_debug_optimization_override(self) -> None:
        """Explicitly setting debug or optimization should override buildtype."""
        testdir = os.path.join(self.common_test_dir, '1 trivial')

        for extra_args in [['--debug', '--buildtype=release'],
                           ['-Ddebug=true', '--buildtype=release'],
                           ['-Ddebug=true', '-Dbuildtype=release'],
                           ['--debug', '-Dbuildtype=release']]:
            with self.subTest(extra_args=extra_args):
                self.new_builddir()
                self.init(testdir, extra_args=extra_args)
                opts = self.introspect('--buildoptions')
                self.assertEqual(self.getconf('buildtype', opts), 'release')
                self.assertEqual(self.getconf('debug', opts), True)
                self.assertEqual(self.getconf('optimization', opts), '3')

        for extra_args in [['--optimization=3', '--buildtype=debug'],
                           ['-Doptimization=3', '--buildtype=debug'],
                           ['-Doptimization=3', '-Dbuildtype=debug'],
                           ['--optimization=3', '-Dbuildtype=debug']]:
            with self.subTest(extra_args=extra_args):
                self.new_builddir()
                self.init(testdir, extra_args=extra_args)
                opts = self.introspect('--buildoptions')
                self.assertEqual(self.getconf('buildtype', opts), 'debug')
                self.assertEqual(self.getconf('debug', opts), True)
                self.assertEqual(self.getconf('optimization', opts), '3')

    def test_introspect_dependency_unknown_name(self):
        testdir = os.path.join(self.unit_test_dir, '139 introspection unknown dep')
        testfile = os.path.join(testdir, 'meson.build')
        res = self.introspect_directory(testfile, ['--dependencies'] + self.meson_args)
        self.assertListEqual(res, [])

    def test_setup_mixed_long_short_options(self) -> None:
        """Mixing unity and unity_size as long and short options should work."""
        testdir = self.copy_srcdir(os.path.join(self.common_test_dir, '1 trivial'))
        self.init(testdir, extra_args=['-Dunity=on', '--unity-size=123'])

    def test_minit_executable_with_matching_source(self) -> None:
        """meson init --executable bar with bar.c present must not create a spurious project-name.c"""
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'bar.c').write_text('int main() {}', encoding='utf-8')
            self._run(self.meson_command + ['init', '--name', 'foo', '--executable', 'bar', '--language', 'c'], workdir=d)
            files = {p.name for p in Path(d).iterdir()}
            self.assertIn('meson.build', files)
            self.assertNotIn('foo.c', files, 'spurious foo.c was created')
            meson_build = Path(d, 'meson.build').read_text(encoding='utf-8')
            self.assertNotIn("'foo.c'", meson_build, 'spurious foo.c listed in meson.build')
            self.assertIn("'bar.c'", meson_build, 'existing bar.c not listed in meson.build')

    def test_minit_multi_file_keeps_existing_sources(self) -> None:
        """meson init without --executable must create a new source file alongside existing ones"""
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'bar.c').write_text('int bar() {}', encoding='utf-8')
            Path(d, 'foo.c').write_text('int main() {}', encoding='utf-8')
            self._run(self.meson_command + ['init', '--name', 'foo', '--language', 'c'], workdir=d)
            files = {p.name for p in Path(d).iterdir()}
            self.assertIn('meson.build', files)
            meson_build = Path(d, 'meson.build').read_text(encoding='utf-8')
            self.assertIn("'foo.c'", meson_build, 'existing foo.c not listed in meson.build')
            self.assertIn("'bar.c'", meson_build, 'existing bar.c not listed in meson.build')

    def test_minit_wrong_name_creates_sample(self) -> None:
        """meson init in an empty directory must create a sample source file"""
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'bar.c').write_text('int main() {}', encoding='utf-8')
            self._run(self.meson_command + ['init', '--name', 'foo', '--language', 'c'], workdir=d)
            files = {p.name for p in Path(d).iterdir()}
            self.assertIn('meson.build', files)
            self.assertIn('foo.c', files)
            meson_build = Path(d, 'meson.build').read_text(encoding='utf-8')
            self.assertIn("'foo.c'", meson_build, 'created foo.c not listed in meson.build')
            self.assertNotIn("'bar.c'", meson_build, 'existing bar.c listed in meson.build')

    def test_minit_empty_dir_creates_sample(self) -> None:
        """meson init in an empty directory must create a sample source file"""
        with tempfile.TemporaryDirectory() as d:
            self._run(self.meson_command + ['init', '--name', 'foo', '--language', 'c'], workdir=d)
            files = {p.name for p in Path(d).iterdir()}
            self.assertIn('meson.build', files)
            self.assertIn('foo.c', files)
            meson_build = Path(d, 'meson.build').read_text(encoding='utf-8')
            self.assertIn("'foo.c'", meson_build, 'created foo.c not listed in meson.build')

    def test_readonly_sourcedir(self) -> None:
        """Test building with read-only source directory."""
        testdir = self.copy_srcdir(os.path.join(self.common_test_dir, '233 wrap case'))

        # Make the source directory and all its contents read-only recursively
        # Keep execute permission on directories
        for dir, _, files in os.walk(testdir):
            os.chmod(dir, 0o555)
            for file in files:
                filepath = os.path.join(dir, file)
                os.chmod(filepath, 0o444)

        self.init(testdir)
        self.build()

    @skip_if_not_language('java')
    def test_java_build_subdir_correct_deps(self):
        """Test that jar() with build_subdir sources does not rebuild unnecessarily."""
        testdir = os.path.join(self.src_root, 'test cases', 'java', '11 build subdir')
        self.init(testdir)
        self.build()
        self.assertBuildIsNoop()

    def test_configure_file_relative_path_depfile(self):
        testdir = os.path.join(self.common_test_dir, "14 configure file")
        self.init(testdir)
        self.utime(os.path.join(testdir, 'depfile'))
        ret = self.build(stderr=False)
        self.assertIn('The Meson build system', ret)
