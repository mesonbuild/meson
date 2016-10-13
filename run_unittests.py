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

import unittest, os, sys, shutil, time
import subprocess
import re, json
import tempfile
from mesonbuild.environment import detect_ninja
from mesonbuild.dependencies import PkgConfigDependency

def get_soname(fname):
    # HACK, fix to not use shell.
    raw_out = subprocess.check_output(['readelf', '-a', fname])
    pattern = re.compile(b'soname: \[(.*?)\]')
    for line in raw_out.split(b'\n'):
        m = pattern.search(line)
        if m is not None:
            return m.group(1)

class FakeEnvironment(object):
    def __init__(self):
        self.cross_info = None
    
    def is_cross_build(self):
        return False

class LinuxlikeTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        src_root = os.path.dirname(__file__)
        self.builddir = tempfile.mkdtemp()
        self.meson_command = [sys.executable, os.path.join(src_root, 'meson.py')]
        self.mconf_command = [sys.executable, os.path.join(src_root, 'mesonconf.py')]
        self.ninja_command = [detect_ninja(), '-C', self.builddir]
        self.common_test_dir = os.path.join(src_root, 'test cases/common')
        self.output = b''
        self.orig_env = os.environ.copy()

    def tearDown(self):
        shutil.rmtree(self.builddir)
        os.environ = self.orig_env
        super().tearDown()

    def init(self, srcdir):
        self.output += subprocess.check_output(self.meson_command + [srcdir, self.builddir])

    def build(self):
        self.output += subprocess.check_output(self.ninja_command)

    def setconf(self, arg):
        self.output += subprocess.check_output(self.mconf_command + [arg, self.builddir])

    def get_compdb(self):
        with open(os.path.join(self.builddir, 'compile_commands.json')) as ifile:
            return json.load(ifile)

    def test_basic_soname(self):
        testdir = os.path.join(self.common_test_dir, '4 shared')
        self.init(testdir)
        self.build()
        lib1 = os.path.join(self.builddir, 'libmylib.so')
        soname = get_soname(lib1)
        self.assertEqual(soname, b'libmylib.so')

    def test_custom_soname(self):
        testdir = os.path.join(self.common_test_dir, '27 library versions')
        self.init(testdir)
        self.build()
        lib1 = os.path.join(self.builddir, 'prefixsomelib.suffix')
        soname = get_soname(lib1)
        self.assertEqual(soname, b'prefixsomelib.suffix')

    def test_pic(self):
        testdir = os.path.join(self.common_test_dir, '3 static')
        self.init(testdir)
        compdb = self.get_compdb()
        self.assertTrue('-fPIC' in compdb[0]['command'])
        # This is needed to increase the difference between build.ninja's
        # timestamp and coredata.dat's timestamp due to a Ninja bug.
        # https://github.com/ninja-build/ninja/issues/371
        time.sleep(1)
        self.setconf('-Db_staticpic=false')
        # Regenerate build
        self.build()
        compdb = self.get_compdb()
        self.assertTrue('-fPIC' not in compdb[0]['command'])

    def test_pkgconfig_gen(self):
        testdir = os.path.join(self.common_test_dir, '51 pkgconfig-gen')
        self.init(testdir)
        env = FakeEnvironment()
        kwargs = {'required': True, 'silent': True}
        os.environ['PKG_CONFIG_LIBDIR'] = os.path.join(self.builddir, 'meson-private')
        simple_dep = PkgConfigDependency('libfoo', env, kwargs)
        self.assertTrue(simple_dep.found())
        self.assertEqual(simple_dep.get_version(), '1.0')
        self.assertTrue('-lfoo' in simple_dep.get_link_args())

if __name__ == '__main__':
    unittest.main()
