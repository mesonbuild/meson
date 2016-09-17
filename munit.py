#!/usr/bin/env python3
# Copyright 2016 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest, os, shutil
import subprocess
import re

def get_soname(fname):
    # HACK, fix to not use shell.
    raw_out = subprocess.check_output(['readelf', '-a', fname])
    pattern = re.compile(b'soname: \[(.*?)\]')
    for line in raw_out.split(b'\n'):
        m = pattern.search(line)
        if m is not None:
            return m.group(1)

class LinuxlikeTests(unittest.TestCase):
    
    def setUp(self):
        super().setUp()
        src_root = os.path.split(__file__)[0]
        self.builddir = 'unittestdir' # fixme to be unique
        self.meson_command = [os.path.join(src_root, 'meson.py')]
        self.ninja_command = ['ninja', '-C', self.builddir]
        self.common_test_dir = os.path.join(src_root, 'test cases/common')
        os.mkdir(self.builddir)

    def tearDown(self):
        shutil.rmtree(self.builddir)
        super().tearDown()

    def test_basic_soname(self):
        testdir = os.path.join(self.common_test_dir, '4 shared')
        subprocess.check_call(self.meson_command + [testdir, self.builddir])
        subprocess.check_call(self.ninja_command)
        lib1 = os.path.join(self.builddir, 'libmylib.so')
        soname = get_soname(lib1)
        self.assertEqual(soname, b'libmylib.so')

    def test_custom_soname(self):
        testdir = os.path.join(self.common_test_dir, '27 library versions')
        subprocess.check_call(self.meson_command + [testdir, self.builddir])
        subprocess.check_call(self.ninja_command)
        lib1 = os.path.join(self.builddir, 'prefixsomelib.suffix')
        soname = get_soname(lib1)
        self.assertEqual(soname, b'prefixsomelib.suffix')

if __name__ == '__main__':
    unittest.main()
