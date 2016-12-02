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
from glob import glob
import mesonbuild.environment
from mesonbuild.environment import detect_ninja
from mesonbuild.dependencies import PkgConfigDependency, Qt5Dependency

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

class InternalTests(unittest.TestCase):

    def test_version_number(self):
        searchfunc = mesonbuild.environment.search_version
        self.assertEqual(searchfunc('foobar 1.2.3'), '1.2.3')
        self.assertEqual(searchfunc('1.2.3'), '1.2.3')
        self.assertEqual(searchfunc('foobar 2016.10.28 1.2.3'), '1.2.3')
        self.assertEqual(searchfunc('2016.10.28 1.2.3'), '1.2.3')
        self.assertEqual(searchfunc('foobar 2016.10.128'), 'unknown version')
        self.assertEqual(searchfunc('2016.10.128'), 'unknown version')

class LinuxlikeTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        src_root = os.path.dirname(__file__)
        src_root = os.path.join(os.getcwd(), src_root)
        self.builddir = tempfile.mkdtemp()
        self.meson_command = [sys.executable, os.path.join(src_root, 'meson.py')]
        self.mconf_command = [sys.executable, os.path.join(src_root, 'mesonconf.py')]
        self.mintro_command = [sys.executable, os.path.join(src_root, 'mesonintrospect.py')]
        self.ninja_command = [detect_ninja(), '-C', self.builddir]
        self.common_test_dir = os.path.join(src_root, 'test cases/common')
        self.vala_test_dir = os.path.join(src_root, 'test cases/vala')
        self.framework_test_dir = os.path.join(src_root, 'test cases/frameworks')
        self.unit_test_dir = os.path.join(src_root, 'test cases/unit')
        self.output = b''
        self.orig_env = os.environ.copy()

    def tearDown(self):
        shutil.rmtree(self.builddir)
        os.environ = self.orig_env
        super().tearDown()

    def _run(self, command):
        self.output += subprocess.check_output(command, env=os.environ.copy())

    def init(self, srcdir):
        self._run(self.meson_command + [srcdir, self.builddir])

    def build(self):
        self._run(self.ninja_command)

    def run_target(self, target):
        self.output += subprocess.check_output(self.ninja_command + [target])

    def setconf(self, arg):
        self._run(self.mconf_command + [arg, self.builddir])

    def get_compdb(self):
        with open(os.path.join(self.builddir, 'compile_commands.json')) as ifile:
            return json.load(ifile)

    def get_meson_log(self):
        with open(os.path.join(self.builddir, 'meson-logs', 'meson-log.txt')) as f:
            return f.readlines()

    def introspect(self, arg):
        out = subprocess.check_output(self.mintro_command + [arg, self.builddir])
        return json.loads(out.decode('utf-8'))

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

    def test_vala_c_warnings(self):
        testdir = os.path.join(self.vala_test_dir, '5 target glib')
        self.init(testdir)
        compdb = self.get_compdb()
        vala_command = None
        c_command = None
        for each in compdb:
            if each['file'].endswith('GLib.Thread.c'):
                vala_command = each['command']
            elif each['file'].endswith('retcode.c'):
                c_command = each['command']
            else:
                m = 'Unknown file {!r} in vala_c_warnings test'.format(each['file'])
                raise AssertionError(m)
        self.assertIsNotNone(vala_command)
        self.assertIsNotNone(c_command)
        # -w suppresses all warnings, should be there in Vala but not in C
        self.assertTrue('-w' in vala_command)
        self.assertFalse('-w' in c_command)
        # -Wall enables all warnings, should be there in C but not in Vala
        self.assertFalse('-Wall' in vala_command)
        self.assertTrue('-Wall' in c_command)
        # -Werror converts warnings to errors, should always be there since it's
        # injected by an unrelated piece of code and the project has werror=true
        self.assertTrue('-Werror' in vala_command)
        self.assertTrue('-Werror' in c_command)

    def test_static_compile_order(self):
        testdir = os.path.join(self.common_test_dir, '5 linkstatic')
        self.init(testdir)
        compdb = self.get_compdb()
        # Rules will get written out in this order
        self.assertTrue(compdb[0]['file'].endswith("libfile.c"))
        self.assertTrue(compdb[1]['file'].endswith("libfile2.c"))
        self.assertTrue(compdb[2]['file'].endswith("libfile3.c"))
        self.assertTrue(compdb[3]['file'].endswith("libfile4.c"))
        # FIXME: We don't have access to the linker command

    def test_install_introspection(self):
        testdir = os.path.join(self.common_test_dir, '8 install')
        self.init(testdir)
        intro = self.introspect('--targets')
        if intro[0]['type'] == 'executable':
            intro = intro[::-1]
        self.assertEqual(intro[0]['install_filename'], '/usr/local/libtest/libstat.a')
        self.assertEqual(intro[1]['install_filename'], '/usr/local/bin/prog')

    def test_run_target_files_path(self):
        testdir = os.path.join(self.common_test_dir, '58 run target')
        self.init(testdir)
        self.run_target('check_exists')

    def test_qt5dependency_qmake_detection(self):
        # Verify that qmake is for Qt5
        if not shutil.which('qmake-qt5'):
            if not shutil.which('qmake'):
                raise unittest.SkipTest('QMake not found')
            # For some inexplicable reason qmake --version gives different
            # results when run from the command line vs invoked by Python.
            # Check for both cases in case this behaviour changes in the future.
            output = subprocess.getoutput(['qmake', '--version'])
            if 'Qt version 5' not in output and 'qt5' not in output:
                raise unittest.SkipTest('Qmake found, but it is not for Qt 5.')
        # Disable pkg-config codepath and force searching with qmake/qmake-qt5
        os.environ['PKG_CONFIG_LIBDIR'] = self.builddir
        os.environ['PKG_CONFIG_PATH'] = self.builddir
        testdir = os.path.join(self.framework_test_dir, '4 qt')
        self.init(testdir)
        # Confirm that the dependency was found with qmake
        msg = 'Qt5 native `qmake-qt5` dependency (modules: Core) found: YES\n'
        msg2 = 'Qt5 native `qmake` dependency (modules: Core) found: YES\n'
        mesonlog = self.get_meson_log()
        self.assertTrue(msg in mesonlog or msg2 in mesonlog)

    def get_soname(self, fname):
        output = subprocess.check_output(['readelf', '-a', fname])
        for line in output.decode('utf-8', errors='ignore').split('\n'):
            if 'SONAME' in line:
                return line.split('[')[1].split(']')[0]
        raise RuntimeError('Readelf gave no SONAME.')

    def test_soname(self):
        testdir = os.path.join(self.unit_test_dir, '1 soname')
        self.init(testdir)
        self.build()

        # File without aliases set.
        nover = os.path.join(self.builddir, 'libnover.so')
        self.assertTrue(os.path.exists(nover))
        self.assertFalse(os.path.islink(nover))
        self.assertEqual(self.get_soname(nover), 'libnover.so')
        self.assertEqual(len(glob(nover[:-3] + '*')), 1)

        # File with version set
        verset = os.path.join(self.builddir, 'libverset.so')
        self.assertTrue(os.path.exists(verset + '.4.5.6'))
        self.assertEqual(os.readlink(verset), 'libverset.so.4')
        self.assertEqual(self.get_soname(verset), 'libverset.so.4')
        self.assertEqual(len(glob(verset[:-3] + '*')), 3)

        # File with soversion set
        soverset = os.path.join(self.builddir, 'libsoverset.so')
        self.assertTrue(os.path.exists(soverset + '.1.2.3'))
        self.assertEqual(os.readlink(soverset), 'libsoverset.so.1.2.3')
        self.assertEqual(self.get_soname(soverset), 'libsoverset.so.1.2.3')
        self.assertEqual(len(glob(soverset[:-3] + '*')), 2)

        # File with version and soversion set to same values
        settosame = os.path.join(self.builddir, 'libsettosame.so')
        self.assertTrue(os.path.exists(settosame + '.7.8.9'))
        self.assertEqual(os.readlink(settosame), 'libsettosame.so.7.8.9')
        self.assertEqual(self.get_soname(settosame), 'libsettosame.so.7.8.9')
        self.assertEqual(len(glob(settosame[:-3] + '*')), 2)

        # File with version and soversion set to different values
        bothset = os.path.join(self.builddir, 'libbothset.so')
        self.assertTrue(os.path.exists(bothset + '.1.2.3'))
        self.assertEqual(os.readlink(bothset), 'libbothset.so.1.2.3')
        self.assertEqual(os.readlink(bothset + '.1.2.3'), 'libbothset.so.4.5.6')
        self.assertEqual(self.get_soname(bothset), 'libbothset.so.1.2.3')
        self.assertEqual(len(glob(bothset[:-3] + '*')), 3)

if __name__ == '__main__':
    unittest.main()
