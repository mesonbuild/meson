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

import os
import tempfile
import subprocess
import textwrap
from unittest import skipIf
from pathlib import Path

from .baseplatformtests import BasePlatformTests
from .helpers import is_ci
from mesonbuild.mesonlib import is_linux
from mesonbuild.optinterpreter import OptionInterpreter, OptionException

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
        testdir = os.path.join(self.unit_test_dir, '100 relative find program')
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
        testdir = os.path.join(self.unit_test_dir, '102 python without pkgconfig')
        self.init(testdir, override_envvars={'PKG_CONFIG': 'notfound'})

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
        testdir = os.path.join(self.unit_test_dir, '107 new subproject on reconfigure')
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
