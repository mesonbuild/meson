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

import os
import unittest
import pathlib
import subprocess

from run_tests import (
    Backend
)

from .allplatformstests import git_init

from .baseplatformtests import BasePlatformTests
from mesonbuild.mesonlib import TemporaryDirectoryWinProof

class PythonTests(BasePlatformTests):
    '''
    Tests that verify compilation of python extension modules
    '''

    def test_versions(self):
        if self.backend is not Backend.ninja:
            raise unittest.SkipTest(f'Skipping python tests with {self.backend.name} backend')

        testdir = os.path.join(self.src_root, 'test cases', 'unit', '39 python extmodule')

        # No python version specified, this will use meson's python
        self.init(testdir)
        self.build()
        self.run_tests()
        self.wipe()

        # When specifying a known name, (python2 / python3) the module
        # will also try 'python' as a fallback and use it if the major
        # version matches
        try:
            self.init(testdir, extra_args=['-Dpython=python2'])
            self.build()
            self.run_tests()
        except unittest.SkipTest:
            # python2 is not necessarily installed on the test machine,
            # if it is not, or the python headers can't be found, the test
            # will raise MESON_SKIP_TEST, we could check beforehand what version
            # of python is available, but it's a bit of a chicken and egg situation,
            # as that is the job of the module, so we just ask for forgiveness rather
            # than permission.
            pass

        self.wipe()

        for py in ('pypy', 'pypy3'):
            try:
                self.init(testdir, extra_args=['-Dpython=%s' % py])
            except unittest.SkipTest:
                # Same as above, pypy2 and pypy3 are not expected to be present
                # on the test system, the test project only raises in these cases
                continue

            # We have a pypy, this is expected to work
            self.build()
            self.run_tests()
            self.wipe()

        # The test is configured to error out with MESON_SKIP_TEST
        # in case it could not find python
        with self.assertRaises(unittest.SkipTest):
            self.init(testdir, extra_args=['-Dpython=not-python'])
        self.wipe()

        # While dir is an external command on both Windows and Linux,
        # it certainly isn't python
        with self.assertRaises(unittest.SkipTest):
            self.init(testdir, extra_args=['-Dpython=dir'])
        self.wipe()

    def test_dist(self):
        with TemporaryDirectoryWinProof() as dirstr:
            dirobj = pathlib.Path(dirstr)
            mesonfile = dirobj / 'meson.build'
            mesonfile.write_text('''project('test', 'c', version: '1')
pymod = import('python')
python = pymod.find_installation('python3', required: true)
''', encoding='utf-8')
            git_init(dirstr)
            self.init(dirstr)
            subprocess.check_call(self.meson_command + ['dist', '-C', self.builddir], stdout=subprocess.DEVNULL)
