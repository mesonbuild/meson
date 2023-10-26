# Copyright 2021 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
import pickle
import tempfile
import subprocess
import textwrap
from unittest import skipIf, SkipTest
from pathlib import Path

from .baseplatformtests import BasePlatformTests
from .helpers import is_ci
from mesonbuild.mesonlib import EnvironmentVariables, ExecutableSerialisation, is_linux, python_command
from mesonbuild.optinterpreter import OptionInterpreter, OptionException
from run_tests import Backend

@skipIf(is_ci() and not is_linux(), "Run only on fast platforms")
class PlatformAgnosticTests(BasePlatformTests):
    '''
    Tests that does not need to run on all platforms during CI
    '''

    def test_relative_find_program(self):
        '''
        Tests that find_program() with a relative path does not find the program
        in current workdir.
        '''
        testdir = os.path.join(self.unit_test_dir, '101 relative find program')
        self.init(testdir, workdir=testdir)

    def test_invalid_option_names(self):
        interp = OptionInterpreter('')

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
        self.assertRaisesRegex(OptionException, 'Option names can only contain letters, numbers or dashes.',
                               interp.process, fname)

        # platlib is allowed, only python.platlib is reserved.
        fname = write_file("option('platlib', type: 'string')")
        interp.process(fname)

    def test_python_dependency_without_pkgconfig(self):
        testdir = os.path.join(self.unit_test_dir, '103 python without pkgconfig')
        self.init(testdir, override_envvars={'PKG_CONFIG': 'notfound'})

    def test_debug_function_outputs_to_meson_log(self):
        testdir = os.path.join(self.unit_test_dir, '105 debug function')
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
            with urllib.request.urlopen('https://wrapdb.mesonbuild.com') as p:
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
        self.setconf(f'--backend=ninja')
        self.init(testdir, extra_args=['--reconfigure', '--backend=ninja'])

        # Change backend option is not allowed
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            self.setconf('-Dbackend=none')
        self.assertIn("ERROR: Tried modify read only option 'backend'", cm.exception.stdout)

        # Reconfigure with a different backend is not allowed
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            self.init(testdir, extra_args=['--reconfigure', '--backend=none'])
        self.assertIn("ERROR: Tried modify read only option 'backend'", cm.exception.stdout)

        # Wipe with a different backend is allowed
        self.init(testdir, extra_args=['--wipe', '--backend=none'])

    def test_validate_dirs(self):
        testdir = os.path.join(self.common_test_dir, '1 trivial')

        # Using parent as builddir should fail
        self.builddir = os.path.dirname(self.builddir)
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            self.init(testdir)
        self.assertIn('cannot be a parent of source directory', cm.exception.stdout)

        # Reconfigure of empty builddir should work
        self.new_builddir()
        self.init(testdir, extra_args=['--reconfigure'])

        # Reconfigure of not empty builddir should work
        self.new_builddir()
        Path(self.builddir, 'dummy').touch()
        self.init(testdir, extra_args=['--reconfigure'])

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
        testdir = os.path.join(self.unit_test_dir, '114 empty project')

        self.init(testdir)
        self._run(self.meson_command + ['--internal', 'regenerate', '--profile-self', testdir, self.builddir])
        with open(os.path.join(self.builddir, 'meson-logs', 'profile-startup-modules.json'), encoding='utf-8') as f:
                data = json.load(f)['meson']

        with open(os.path.join(testdir, 'expected_mods.json'), encoding='utf-8') as f:
            expected = json.load(f)['meson']['modules']

        self.assertEqual(data['modules'], expected)
        self.assertEqual(data['count'], 68)

    def test_cmake_openssl_not_found_bug(self):
        """Issue #12098"""
        testdir = os.path.join(self.unit_test_dir, '117 openssl cmake bug')
        self.meson_native_files.append(os.path.join(testdir, 'nativefile.ini'))
        out = self.init(testdir, allow_fail=True)
        self.assertNotIn('Unhandled python exception', out)
