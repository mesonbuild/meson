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

import subprocess
import re
import os
import shutil
from unittest import mock, SkipTest, skipUnless, skipIf
from glob import glob

import mesonbuild.mlog
import mesonbuild.depfile
import mesonbuild.dependencies.factory
import mesonbuild.envconfig
import mesonbuild.environment
import mesonbuild.coredata
import mesonbuild.modules.gnome
from mesonbuild.mesonlib import (
    MachineChoice, is_windows, is_cygwin, python_command, version_compare,
    EnvironmentException, OptionKey
)
from mesonbuild.compilers import (
    detect_c_compiler, detect_d_compiler, compiler_from_language,
)
from mesonbuild.programs import ExternalProgram
import mesonbuild.dependencies.base
import mesonbuild.modules.pkgconfig


from run_tests import (
    Backend, get_fake_env
)

from .baseplatformtests import BasePlatformTests
from .helpers import *

@skipUnless(is_windows() or is_cygwin(), "requires Windows (or Windows via Cygwin)")
class WindowsTests(BasePlatformTests):
    '''
    Tests that should run on Cygwin, MinGW, and MSVC
    '''

    def setUp(self):
        super().setUp()
        self.platform_test_dir = os.path.join(self.src_root, 'test cases/windows')

    @skipIf(is_cygwin(), 'Test only applicable to Windows')
    @mock.patch.dict(os.environ)
    def test_find_program(self):
        '''
        Test that Windows-specific edge-cases in find_program are functioning
        correctly. Cannot be an ordinary test because it involves manipulating
        PATH to point to a directory with Python scripts.
        '''
        testdir = os.path.join(self.platform_test_dir, '8 find program')
        # Find `cmd` and `cmd.exe`
        prog1 = ExternalProgram('cmd')
        self.assertTrue(prog1.found(), msg='cmd not found')
        prog2 = ExternalProgram('cmd.exe')
        self.assertTrue(prog2.found(), msg='cmd.exe not found')
        self.assertPathEqual(prog1.get_path(), prog2.get_path())
        # Find cmd.exe with args without searching
        prog = ExternalProgram('cmd', command=['cmd', '/C'])
        self.assertTrue(prog.found(), msg='cmd not found with args')
        self.assertPathEqual(prog.get_command()[0], 'cmd')
        # Find cmd with an absolute path that's missing the extension
        cmd_path = prog2.get_path()[:-4]
        prog = ExternalProgram(cmd_path)
        self.assertTrue(prog.found(), msg=f'{cmd_path!r} not found')
        # Finding a script with no extension inside a directory works
        prog = ExternalProgram(os.path.join(testdir, 'test-script'))
        self.assertTrue(prog.found(), msg='test-script not found')
        # Finding a script with an extension inside a directory works
        prog = ExternalProgram(os.path.join(testdir, 'test-script-ext.py'))
        self.assertTrue(prog.found(), msg='test-script-ext.py not found')
        # Finding a script in PATH
        os.environ['PATH'] += os.pathsep + testdir
        # If `.PY` is in PATHEXT, scripts can be found as programs
        if '.PY' in [ext.upper() for ext in os.environ['PATHEXT'].split(';')]:
            # Finding a script in PATH w/o extension works and adds the interpreter
            prog = ExternalProgram('test-script-ext')
            self.assertTrue(prog.found(), msg='test-script-ext not found in PATH')
            self.assertPathEqual(prog.get_command()[0], python_command[0])
            self.assertPathBasenameEqual(prog.get_path(), 'test-script-ext.py')
        # Finding a script in PATH with extension works and adds the interpreter
        prog = ExternalProgram('test-script-ext.py')
        self.assertTrue(prog.found(), msg='test-script-ext.py not found in PATH')
        self.assertPathEqual(prog.get_command()[0], python_command[0])
        self.assertPathBasenameEqual(prog.get_path(), 'test-script-ext.py')
        # Using a script with an extension directly via command= works and adds the interpreter
        prog = ExternalProgram('test-script-ext.py', command=[os.path.join(testdir, 'test-script-ext.py'), '--help'])
        self.assertTrue(prog.found(), msg='test-script-ext.py with full path not picked up via command=')
        self.assertPathEqual(prog.get_command()[0], python_command[0])
        self.assertPathEqual(prog.get_command()[2], '--help')
        self.assertPathBasenameEqual(prog.get_path(), 'test-script-ext.py')
        # Using a script without an extension directly via command= works and adds the interpreter
        prog = ExternalProgram('test-script', command=[os.path.join(testdir, 'test-script'), '--help'])
        self.assertTrue(prog.found(), msg='test-script with full path not picked up via command=')
        self.assertPathEqual(prog.get_command()[0], python_command[0])
        self.assertPathEqual(prog.get_command()[2], '--help')
        self.assertPathBasenameEqual(prog.get_path(), 'test-script')
        # Ensure that WindowsApps gets removed from PATH
        path = os.environ['PATH']
        if 'WindowsApps' not in path:
            username = os.environ['USERNAME']
            appstore_dir = fr'C:\Users\{username}\AppData\Local\Microsoft\WindowsApps'
            path = os.pathsep + appstore_dir
        path = ExternalProgram._windows_sanitize_path(path)
        self.assertNotIn('WindowsApps', path)

    def test_ignore_libs(self):
        '''
        Test that find_library on libs that are to be ignored returns an empty
        array of arguments. Must be a unit test because we cannot inspect
        ExternalLibraryHolder from build files.
        '''
        testdir = os.path.join(self.platform_test_dir, '1 basic')
        env = get_fake_env(testdir, self.builddir, self.prefix)
        cc = detect_c_compiler(env, MachineChoice.HOST)
        if cc.get_argument_syntax() != 'msvc':
            raise SkipTest('Not using MSVC')
        # To force people to update this test, and also test
        self.assertEqual(set(cc.ignore_libs), {'c', 'm', 'pthread', 'dl', 'rt', 'execinfo'})
        for l in cc.ignore_libs:
            self.assertEqual(cc.find_library(l, env, []), [])

    def test_rc_depends_files(self):
        testdir = os.path.join(self.platform_test_dir, '5 resources')

        # resource compiler depfile generation is not yet implemented for msvc
        env = get_fake_env(testdir, self.builddir, self.prefix)
        depfile_works = detect_c_compiler(env, MachineChoice.HOST).get_id() not in {'msvc', 'clang-cl', 'intel-cl'}

        self.init(testdir)
        self.build()
        # Immediately rebuilding should not do anything
        self.assertBuildIsNoop()
        # Test compile_resources(depend_file:)
        # Changing mtime of sample.ico should rebuild prog
        self.utime(os.path.join(testdir, 'res', 'sample.ico'))
        self.assertRebuiltTarget('prog')
        # Test depfile generation by compile_resources
        # Changing mtime of resource.h should rebuild myres.rc and then prog
        if depfile_works:
            self.utime(os.path.join(testdir, 'inc', 'resource', 'resource.h'))
            self.assertRebuiltTarget('prog')
        self.wipe()

        if depfile_works:
            testdir = os.path.join(self.platform_test_dir, '12 resources with custom targets')
            self.init(testdir)
            self.build()
            # Immediately rebuilding should not do anything
            self.assertBuildIsNoop()
            # Changing mtime of resource.h should rebuild myres_1.rc and then prog_1
            self.utime(os.path.join(testdir, 'res', 'resource.h'))
            self.assertRebuiltTarget('prog_1')

    def test_msvc_cpp17(self):
        testdir = os.path.join(self.unit_test_dir, '44 vscpp17')

        env = get_fake_env(testdir, self.builddir, self.prefix)
        cc = detect_c_compiler(env, MachineChoice.HOST)
        if cc.get_argument_syntax() != 'msvc':
            raise SkipTest('Test only applies to MSVC-like compilers')

        try:
            self.init(testdir)
        except subprocess.CalledProcessError:
            # According to Python docs, output is only stored when
            # using check_output. We don't use it, so we can't check
            # that the output is correct (i.e. that it failed due
            # to the right reason).
            return
        self.build()

    def test_install_pdb_introspection(self):
        testdir = os.path.join(self.platform_test_dir, '1 basic')

        env = get_fake_env(testdir, self.builddir, self.prefix)
        cc = detect_c_compiler(env, MachineChoice.HOST)
        if cc.get_argument_syntax() != 'msvc':
            raise SkipTest('Test only applies to MSVC-like compilers')

        self.init(testdir)
        installed = self.introspect('--installed')
        files = [os.path.basename(path) for path in installed.values()]

        self.assertIn('prog.pdb', files)

    def _check_ld(self, name: str, lang: str, expected: str) -> None:
        if not shutil.which(name):
            raise SkipTest(f'Could not find {name}.')
        envvars = [mesonbuild.envconfig.ENV_VAR_PROG_MAP[f'{lang}_ld']]

        # Also test a deprecated variable if there is one.
        if f'{lang}_ld' in mesonbuild.envconfig.DEPRECATED_ENV_PROG_MAP:
            envvars.append(
                mesonbuild.envconfig.DEPRECATED_ENV_PROG_MAP[f'{lang}_ld'])

        for envvar in envvars:
            with mock.patch.dict(os.environ, {envvar: name}):
                env = get_fake_env()
                try:
                    comp = compiler_from_language(env, lang, MachineChoice.HOST)
                except EnvironmentException:
                    raise SkipTest(f'Could not find a compiler for {lang}')
                self.assertEqual(comp.linker.id, expected)

    def test_link_environment_variable_lld_link(self):
        env = get_fake_env()
        comp = detect_c_compiler(env, MachineChoice.HOST)
        if comp.get_argument_syntax() == 'gcc':
            raise SkipTest('GCC cannot be used with link compatible linkers.')
        self._check_ld('lld-link', 'c', 'lld-link')

    def test_link_environment_variable_link(self):
        env = get_fake_env()
        comp = detect_c_compiler(env, MachineChoice.HOST)
        if comp.get_argument_syntax() == 'gcc':
            raise SkipTest('GCC cannot be used with link compatible linkers.')
        self._check_ld('link', 'c', 'link')

    def test_link_environment_variable_optlink(self):
        env = get_fake_env()
        comp = detect_c_compiler(env, MachineChoice.HOST)
        if comp.get_argument_syntax() == 'gcc':
            raise SkipTest('GCC cannot be used with link compatible linkers.')
        self._check_ld('optlink', 'c', 'optlink')

    @skip_if_not_language('rust')
    def test_link_environment_variable_rust(self):
        self._check_ld('link', 'rust', 'link')

    @skip_if_not_language('d')
    def test_link_environment_variable_d(self):
        env = get_fake_env()
        comp = detect_d_compiler(env, MachineChoice.HOST)
        if comp.id == 'dmd':
            raise SkipTest('meson cannot reliably make DMD use a different linker.')
        self._check_ld('lld-link', 'd', 'lld-link')

    def test_pefile_checksum(self):
        try:
            import pefile
        except ImportError:
            if is_ci():
                raise
            raise SkipTest('pefile module not found')
        testdir = os.path.join(self.common_test_dir, '6 linkshared')
        self.init(testdir, extra_args=['--buildtype=release'])
        self.build()
        # Test that binaries have a non-zero checksum
        env = get_fake_env()
        cc = detect_c_compiler(env, MachineChoice.HOST)
        cc_id = cc.get_id()
        ld_id = cc.get_linker_id()
        dll = glob(os.path.join(self.builddir, '*mycpplib.dll'))[0]
        exe = os.path.join(self.builddir, 'cppprog.exe')
        for f in (dll, exe):
            pe = pefile.PE(f)
            msg = f'PE file: {f!r}, compiler: {cc_id!r}, linker: {ld_id!r}'
            if cc_id == 'clang-cl':
                # Latest clang-cl tested (7.0) does not write checksums out
                self.assertFalse(pe.verify_checksum(), msg=msg)
            else:
                # Verify that a valid checksum was written by all other compilers
                self.assertTrue(pe.verify_checksum(), msg=msg)

    def test_qt5dependency_vscrt(self):
        '''
        Test that qt5 dependencies use the debug module suffix when b_vscrt is
        set to 'mdd'
        '''
        # Verify that the `b_vscrt` option is available
        env = get_fake_env()
        cc = detect_c_compiler(env, MachineChoice.HOST)
        if OptionKey('b_vscrt') not in cc.base_options:
            raise SkipTest('Compiler does not support setting the VS CRT')
        # Verify that qmake is for Qt5
        if not shutil.which('qmake-qt5'):
            if not shutil.which('qmake') and not is_ci():
                raise SkipTest('QMake not found')
            output = subprocess.getoutput('qmake --version')
            if 'Qt version 5' not in output and not is_ci():
                raise SkipTest('Qmake found, but it is not for Qt 5.')
        # Setup with /MDd
        testdir = os.path.join(self.framework_test_dir, '4 qt')
        self.init(testdir, extra_args=['-Db_vscrt=mdd'])
        # Verify that we're linking to the debug versions of Qt DLLs
        build_ninja = os.path.join(self.builddir, 'build.ninja')
        with open(build_ninja, encoding='utf-8') as f:
            contents = f.read()
            m = re.search('build qt5core.exe: cpp_LINKER.*Qt5Cored.lib', contents)
        self.assertIsNotNone(m, msg=contents)

    def test_compiler_checks_vscrt(self):
        '''
        Test that the correct VS CRT is used when running compiler checks
        '''
        # Verify that the `b_vscrt` option is available
        env = get_fake_env()
        cc = detect_c_compiler(env, MachineChoice.HOST)
        if OptionKey('b_vscrt') not in cc.base_options:
            raise SkipTest('Compiler does not support setting the VS CRT')

        def sanitycheck_vscrt(vscrt):
            checks = self.get_meson_log_sanitychecks()
            self.assertGreater(len(checks), 0)
            for check in checks:
                self.assertIn(vscrt, check)

        testdir = os.path.join(self.common_test_dir, '1 trivial')
        self.init(testdir)
        sanitycheck_vscrt('/MDd')

        self.new_builddir()
        self.init(testdir, extra_args=['-Dbuildtype=debugoptimized'])
        sanitycheck_vscrt('/MD')

        self.new_builddir()
        self.init(testdir, extra_args=['-Dbuildtype=release'])
        sanitycheck_vscrt('/MD')

        self.new_builddir()
        self.init(testdir, extra_args=['-Db_vscrt=md'])
        sanitycheck_vscrt('/MD')

        self.new_builddir()
        self.init(testdir, extra_args=['-Db_vscrt=mdd'])
        sanitycheck_vscrt('/MDd')

        self.new_builddir()
        self.init(testdir, extra_args=['-Db_vscrt=mt'])
        sanitycheck_vscrt('/MT')

        self.new_builddir()
        self.init(testdir, extra_args=['-Db_vscrt=mtd'])
        sanitycheck_vscrt('/MTd')

    def test_modules(self):
        if self.backend is not Backend.ninja:
            raise SkipTest(f'C++ modules only work with the Ninja backend (not {self.backend.name}).')
        if 'VSCMD_VER' not in os.environ:
            raise SkipTest('C++ modules is only supported with Visual Studio.')
        if version_compare(os.environ['VSCMD_VER'], '<16.10.0'):
            raise SkipTest('C++ modules are only supported with VS 2019 Preview or newer.')
        self.init(os.path.join(self.unit_test_dir, '85 cpp modules'))
        self.build()

    def test_non_utf8_fails(self):
        # FIXME: VS backend does not use flags from compiler.get_always_args()
        # and thus it's missing /utf-8 argument. Was that intentional? This needs
        # to be revisited.
        if self.backend is not Backend.ninja:
            raise SkipTest(f'This test only pass with ninja backend (not {self.backend.name}).')
        testdir = os.path.join(self.platform_test_dir, '18 msvc charset')
        env = get_fake_env(testdir, self.builddir, self.prefix)
        cc = detect_c_compiler(env, MachineChoice.HOST)
        if cc.get_argument_syntax() != 'msvc':
            raise SkipTest('Not using MSVC')
        self.init(testdir, extra_args=['-Dtest-failure=true'])
        self.assertRaises(subprocess.CalledProcessError, self.build)

    @unittest.skipIf(is_cygwin(), "Needs visual studio")
    def test_vsenv_option(self):
        if self.backend is not Backend.ninja:
            raise SkipTest('Only ninja backend is valid for test')
        env = os.environ.copy()
        env['MESON_FORCE_VSENV_FOR_UNITTEST'] = '1'
        # Remove ninja from PATH to ensure that the one provided by Visual
        # Studio is picked, as a regression test for
        # https://github.com/mesonbuild/meson/issues/9774
        env['PATH'] = get_path_without_cmd('ninja', env['PATH'])
        testdir = os.path.join(self.common_test_dir, '1 trivial')
        out = self.init(testdir, extra_args=['--vsenv'], override_envvars=env)
        self.assertIn('Activating VS', out)
        self.assertRegex(out, 'Visual Studio environment is needed to run Ninja')
        # All these directly call ninja with the full path, so we need to patch
        # it out to use meson subcommands
        with mock.patch.object(self, 'build_command', self.meson_command + ['compile']):
            out = self.build(override_envvars=env)
            self.assertIn('Activating VS', out)
        with mock.patch.object(self, 'test_command', self.meson_command + ['test']):
            out = self.run_tests(override_envvars=env)
            self.assertIn('Activating VS', out)
        with mock.patch.object(self, 'install_command', self.meson_command + ['install']):
            out = self.install(override_envvars=env)
            self.assertIn('Activating VS', out)
