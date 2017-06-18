#!/usr/bin/env python3
# Copyright 2016-2017 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import stat
import shlex
import subprocess
import re, json
import tempfile
import os
import shutil
import sys
import unittest
from configparser import ConfigParser
from glob import glob
from pathlib import PurePath

import mesonbuild.mlog
import mesonbuild.compilers
import mesonbuild.environment
import mesonbuild.mesonlib
from mesonbuild.mesonlib import is_windows, is_osx, is_cygwin, windows_proof_rmtree
from mesonbuild.environment import Environment
from mesonbuild.dependencies import DependencyException
from mesonbuild.dependencies import PkgConfigDependency, ExternalProgram

from run_tests import exe_suffix, get_fake_options, FakeEnvironment
from run_tests import get_builddir_target_args, get_backend_commands, Backend
from run_tests import ensure_backend_detects_changes, run_configure_inprocess


def get_dynamic_section_entry(fname, entry):
    try:
        raw_out = subprocess.check_output(['readelf', '-d', fname],
                                          universal_newlines=True)
    except FileNotFoundError:
        # FIXME: Try using depfixer.py:Elf() as a fallback
        raise unittest.SkipTest('readelf not found')
    pattern = re.compile(entry + r': \[(.*?)\]')
    for line in raw_out.split('\n'):
        m = pattern.search(line)
        if m is not None:
            return m.group(1)
    raise RuntimeError('Could not determine {}:\n\n'.format(entry) + raw_out)

def get_soname(fname):
    return get_dynamic_section_entry(fname, 'soname')

def get_rpath(fname):
    return get_dynamic_section_entry(fname, r'(?:rpath|runpath)')


class InternalTests(unittest.TestCase):

    def test_version_number(self):
        searchfunc = mesonbuild.environment.search_version
        self.assertEqual(searchfunc('foobar 1.2.3'), '1.2.3')
        self.assertEqual(searchfunc('1.2.3'), '1.2.3')
        self.assertEqual(searchfunc('foobar 2016.10.28 1.2.3'), '1.2.3')
        self.assertEqual(searchfunc('2016.10.28 1.2.3'), '1.2.3')
        self.assertEqual(searchfunc('foobar 2016.10.128'), 'unknown version')
        self.assertEqual(searchfunc('2016.10.128'), 'unknown version')

    def test_mode_symbolic_to_bits(self):
        modefunc = mesonbuild.mesonlib.FileMode.perms_s_to_bits
        self.assertEqual(modefunc('---------'), 0)
        self.assertEqual(modefunc('r--------'), stat.S_IRUSR)
        self.assertEqual(modefunc('---r-----'), stat.S_IRGRP)
        self.assertEqual(modefunc('------r--'), stat.S_IROTH)
        self.assertEqual(modefunc('-w-------'), stat.S_IWUSR)
        self.assertEqual(modefunc('----w----'), stat.S_IWGRP)
        self.assertEqual(modefunc('-------w-'), stat.S_IWOTH)
        self.assertEqual(modefunc('--x------'), stat.S_IXUSR)
        self.assertEqual(modefunc('-----x---'), stat.S_IXGRP)
        self.assertEqual(modefunc('--------x'), stat.S_IXOTH)
        self.assertEqual(modefunc('--S------'), stat.S_ISUID)
        self.assertEqual(modefunc('-----S---'), stat.S_ISGID)
        self.assertEqual(modefunc('--------T'), stat.S_ISVTX)
        self.assertEqual(modefunc('--s------'), stat.S_ISUID | stat.S_IXUSR)
        self.assertEqual(modefunc('-----s---'), stat.S_ISGID | stat.S_IXGRP)
        self.assertEqual(modefunc('--------t'), stat.S_ISVTX | stat.S_IXOTH)
        self.assertEqual(modefunc('rwx------'), stat.S_IRWXU)
        self.assertEqual(modefunc('---rwx---'), stat.S_IRWXG)
        self.assertEqual(modefunc('------rwx'), stat.S_IRWXO)
        # We could keep listing combinations exhaustively but that seems
        # tedious and pointless. Just test a few more.
        self.assertEqual(modefunc('rwxr-xr-x'),
                         stat.S_IRWXU |
                         stat.S_IRGRP | stat.S_IXGRP |
                         stat.S_IROTH | stat.S_IXOTH)
        self.assertEqual(modefunc('rw-r--r--'),
                         stat.S_IRUSR | stat.S_IWUSR |
                         stat.S_IRGRP |
                         stat.S_IROTH)
        self.assertEqual(modefunc('rwsr-x---'),
                         stat.S_IRWXU | stat.S_ISUID |
                         stat.S_IRGRP | stat.S_IXGRP)

    def test_compiler_args_class(self):
        cargsfunc = mesonbuild.compilers.CompilerArgs
        c = mesonbuild.environment.CCompiler([], 'fake', False)
        # Test that bad initialization fails
        self.assertRaises(TypeError, cargsfunc, [])
        self.assertRaises(TypeError, cargsfunc, [], [])
        self.assertRaises(TypeError, cargsfunc, c, [], [])
        # Test that empty initialization works
        a = cargsfunc(c)
        self.assertEqual(a, [])
        # Test that list initialization works
        a = cargsfunc(['-I.', '-I..'], c)
        self.assertEqual(a, ['-I.', '-I..'])
        # Test that there is no de-dup on initialization
        self.assertEqual(cargsfunc(['-I.', '-I.'], c), ['-I.', '-I.'])

        ## Test that appending works
        a.append('-I..')
        self.assertEqual(a, ['-I..', '-I.'])
        a.append('-O3')
        self.assertEqual(a, ['-I..', '-I.', '-O3'])

        ## Test that in-place addition works
        a += ['-O2', '-O2']
        self.assertEqual(a, ['-I..', '-I.', '-O3', '-O2', '-O2'])
        # Test that removal works
        a.remove('-O2')
        self.assertEqual(a, ['-I..', '-I.', '-O3', '-O2'])
        # Test that de-dup happens on addition
        a += ['-Ifoo', '-Ifoo']
        self.assertEqual(a, ['-Ifoo', '-I..', '-I.', '-O3', '-O2'])

        # .extend() is just +=, so we don't test it

        ## Test that addition works
        # Test that adding a list with just one old arg works and yields the same array
        a = a + ['-Ifoo']
        self.assertEqual(a, ['-Ifoo', '-I..', '-I.', '-O3', '-O2'])
        # Test that adding a list with one arg new and one old works
        a = a + ['-Ifoo', '-Ibaz']
        self.assertEqual(a, ['-Ifoo', '-Ibaz', '-I..', '-I.', '-O3', '-O2'])
        # Test that adding args that must be prepended and appended works
        a = a + ['-Ibar', '-Wall']
        self.assertEqual(a, ['-Ibar', '-Ifoo', '-Ibaz', '-I..', '-I.', '-O3', '-O2', '-Wall'])

        ## Test that reflected addition works
        # Test that adding to a list with just one old arg works and yields the same array
        a = ['-Ifoo'] + a
        self.assertEqual(a, ['-Ibar', '-Ifoo', '-Ibaz', '-I..', '-I.', '-O3', '-O2', '-Wall'])
        # Test that adding to a list with just one new arg that is not pre-pended works
        a = ['-Werror'] + a
        self.assertEqual(a, ['-Ibar', '-Ifoo', '-Ibaz', '-I..', '-I.', '-Werror', '-O3', '-O2', '-Wall'])
        # Test that adding to a list with two new args preserves the order
        a = ['-Ldir', '-Lbah'] + a
        self.assertEqual(a, ['-Ibar', '-Ifoo', '-Ibaz', '-I..', '-I.', '-Ldir', '-Lbah', '-Werror', '-O3', '-O2', '-Wall'])
        # Test that adding to a list with old args does nothing
        a = ['-Ibar', '-Ibaz', '-Ifoo'] + a
        self.assertEqual(a, ['-Ibar', '-Ifoo', '-Ibaz', '-I..', '-I.', '-Ldir', '-Lbah', '-Werror', '-O3', '-O2', '-Wall'])

        ## Test that adding libraries works
        l = cargsfunc(c, ['-Lfoodir', '-lfoo'])
        self.assertEqual(l, ['-Lfoodir', '-lfoo'])
        # Adding a library and a libpath appends both correctly
        l += ['-Lbardir', '-lbar']
        self.assertEqual(l, ['-Lbardir', '-Lfoodir', '-lfoo', '-lbar'])
        # Adding the same library again does nothing
        l += ['-lbar']
        self.assertEqual(l, ['-Lbardir', '-Lfoodir', '-lfoo', '-lbar'])

        ## Test that 'direct' append and extend works
        l = cargsfunc(c, ['-Lfoodir', '-lfoo'])
        self.assertEqual(l, ['-Lfoodir', '-lfoo'])
        # Direct-adding a library and a libpath appends both correctly
        l.extend_direct(['-Lbardir', '-lbar'])
        self.assertEqual(l, ['-Lfoodir', '-lfoo', '-Lbardir', '-lbar'])
        # Direct-adding the same library again still adds it
        l.append_direct('-lbar')
        self.assertEqual(l, ['-Lfoodir', '-lfoo', '-Lbardir', '-lbar', '-lbar'])

    def test_commonpath(self):
        from os.path import sep
        commonpath = mesonbuild.mesonlib.commonpath
        self.assertRaises(ValueError, commonpath, [])
        self.assertEqual(commonpath(['/usr', '/usr']), sep + 'usr')
        self.assertEqual(commonpath(['/usr', '/usr/']), sep + 'usr')
        self.assertEqual(commonpath(['/usr', '/usr/bin']), sep + 'usr')
        self.assertEqual(commonpath(['/usr/', '/usr/bin']), sep + 'usr')
        self.assertEqual(commonpath(['/usr/./', '/usr/bin']), sep + 'usr')
        self.assertEqual(commonpath(['/usr/bin', '/usr/bin']), sep + 'usr' + sep + 'bin')
        self.assertEqual(commonpath(['/usr//bin', '/usr/bin']), sep + 'usr' + sep + 'bin')
        self.assertEqual(commonpath(['/usr/./bin', '/usr/bin']), sep + 'usr' + sep + 'bin')
        self.assertEqual(commonpath(['/usr/local', '/usr/lib']), sep + 'usr')
        self.assertEqual(commonpath(['/usr', '/bin']), sep)
        self.assertEqual(commonpath(['/usr', 'bin']), '')
        self.assertEqual(commonpath(['blam', 'bin']), '')
        prefix = '/some/path/to/prefix'
        libdir = '/some/path/to/prefix/libdir'
        self.assertEqual(commonpath([prefix, libdir]), str(PurePath(prefix)))

    def test_string_templates_substitution(self):
        dictfunc = mesonbuild.mesonlib.get_filenames_templates_dict
        substfunc = mesonbuild.mesonlib.substitute_values
        ME = mesonbuild.mesonlib.MesonException

        # Identity
        self.assertEqual(dictfunc([], []), {})

        # One input, no outputs
        inputs = ['bar/foo.c.in']
        outputs = []
        ret = dictfunc(inputs, outputs)
        d = {'@INPUT@': inputs, '@INPUT0@': inputs[0],
             '@PLAINNAME@': 'foo.c.in', '@BASENAME@': 'foo.c'}
        # Check dictionary
        self.assertEqual(ret, d)
        # Check substitutions
        cmd = ['some', 'ordinary', 'strings']
        self.assertEqual(substfunc(cmd, d), cmd)
        cmd = ['@INPUT@.out', 'ordinary', 'strings']
        self.assertEqual(substfunc(cmd, d), [inputs[0] + '.out'] + cmd[1:])
        cmd = ['@INPUT0@.out', '@PLAINNAME@.ok', 'strings']
        self.assertEqual(substfunc(cmd, d),
                         [inputs[0] + '.out'] + [d['@PLAINNAME@'] + '.ok'] + cmd[2:])
        cmd = ['@INPUT@', '@BASENAME@.hah', 'strings']
        self.assertEqual(substfunc(cmd, d),
                         inputs + [d['@BASENAME@'] + '.hah'] + cmd[2:])
        cmd = ['@OUTPUT@']
        self.assertRaises(ME, substfunc, cmd, d)

        # One input, one output
        inputs = ['bar/foo.c.in']
        outputs = ['out.c']
        ret = dictfunc(inputs, outputs)
        d = {'@INPUT@': inputs, '@INPUT0@': inputs[0],
             '@PLAINNAME@': 'foo.c.in', '@BASENAME@': 'foo.c',
             '@OUTPUT@': outputs, '@OUTPUT0@': outputs[0], '@OUTDIR@': '.'}
        # Check dictionary
        self.assertEqual(ret, d)
        # Check substitutions
        cmd = ['some', 'ordinary', 'strings']
        self.assertEqual(substfunc(cmd, d), cmd)
        cmd = ['@INPUT@.out', '@OUTPUT@', 'strings']
        self.assertEqual(substfunc(cmd, d),
                         [inputs[0] + '.out'] + outputs + cmd[2:])
        cmd = ['@INPUT0@.out', '@PLAINNAME@.ok', '@OUTPUT0@']
        self.assertEqual(substfunc(cmd, d),
                         [inputs[0] + '.out', d['@PLAINNAME@'] + '.ok'] + outputs)
        cmd = ['@INPUT@', '@BASENAME@.hah', 'strings']
        self.assertEqual(substfunc(cmd, d),
                         inputs + [d['@BASENAME@'] + '.hah'] + cmd[2:])

        # One input, one output with a subdir
        outputs = ['dir/out.c']
        ret = dictfunc(inputs, outputs)
        d = {'@INPUT@': inputs, '@INPUT0@': inputs[0],
             '@PLAINNAME@': 'foo.c.in', '@BASENAME@': 'foo.c',
             '@OUTPUT@': outputs, '@OUTPUT0@': outputs[0], '@OUTDIR@': 'dir'}
        # Check dictionary
        self.assertEqual(ret, d)

        # Two inputs, no outputs
        inputs = ['bar/foo.c.in', 'baz/foo.c.in']
        outputs = []
        ret = dictfunc(inputs, outputs)
        d = {'@INPUT@': inputs, '@INPUT0@': inputs[0], '@INPUT1@': inputs[1]}
        # Check dictionary
        self.assertEqual(ret, d)
        # Check substitutions
        cmd = ['some', 'ordinary', 'strings']
        self.assertEqual(substfunc(cmd, d), cmd)
        cmd = ['@INPUT@', 'ordinary', 'strings']
        self.assertEqual(substfunc(cmd, d), inputs + cmd[1:])
        cmd = ['@INPUT0@.out', 'ordinary', 'strings']
        self.assertEqual(substfunc(cmd, d), [inputs[0] + '.out'] + cmd[1:])
        cmd = ['@INPUT0@.out', '@INPUT1@.ok', 'strings']
        self.assertEqual(substfunc(cmd, d), [inputs[0] + '.out', inputs[1] + '.ok'] + cmd[2:])
        cmd = ['@INPUT0@', '@INPUT1@', 'strings']
        self.assertEqual(substfunc(cmd, d), inputs + cmd[2:])
        # Many inputs, can't use @INPUT@ like this
        cmd = ['@INPUT@.out', 'ordinary', 'strings']
        self.assertRaises(ME, substfunc, cmd, d)
        # Not enough inputs
        cmd = ['@INPUT2@.out', 'ordinary', 'strings']
        self.assertRaises(ME, substfunc, cmd, d)
        # Too many inputs
        cmd = ['@PLAINNAME@']
        self.assertRaises(ME, substfunc, cmd, d)
        cmd = ['@BASENAME@']
        self.assertRaises(ME, substfunc, cmd, d)
        # No outputs
        cmd = ['@OUTPUT@']
        self.assertRaises(ME, substfunc, cmd, d)
        cmd = ['@OUTPUT0@']
        self.assertRaises(ME, substfunc, cmd, d)
        cmd = ['@OUTDIR@']
        self.assertRaises(ME, substfunc, cmd, d)

        # Two inputs, one output
        outputs = ['dir/out.c']
        ret = dictfunc(inputs, outputs)
        d = {'@INPUT@': inputs, '@INPUT0@': inputs[0], '@INPUT1@': inputs[1],
             '@OUTPUT@': outputs, '@OUTPUT0@': outputs[0], '@OUTDIR@': 'dir'}
        # Check dictionary
        self.assertEqual(ret, d)
        # Check substitutions
        cmd = ['some', 'ordinary', 'strings']
        self.assertEqual(substfunc(cmd, d), cmd)
        cmd = ['@OUTPUT@', 'ordinary', 'strings']
        self.assertEqual(substfunc(cmd, d), outputs + cmd[1:])
        cmd = ['@OUTPUT@.out', 'ordinary', 'strings']
        self.assertEqual(substfunc(cmd, d), [outputs[0] + '.out'] + cmd[1:])
        cmd = ['@OUTPUT0@.out', '@INPUT1@.ok', 'strings']
        self.assertEqual(substfunc(cmd, d), [outputs[0] + '.out', inputs[1] + '.ok'] + cmd[2:])
        # Many inputs, can't use @INPUT@ like this
        cmd = ['@INPUT@.out', 'ordinary', 'strings']
        self.assertRaises(ME, substfunc, cmd, d)
        # Not enough inputs
        cmd = ['@INPUT2@.out', 'ordinary', 'strings']
        self.assertRaises(ME, substfunc, cmd, d)
        # Not enough outputs
        cmd = ['@OUTPUT2@.out', 'ordinary', 'strings']
        self.assertRaises(ME, substfunc, cmd, d)

        # Two inputs, two outputs
        outputs = ['dir/out.c', 'dir/out2.c']
        ret = dictfunc(inputs, outputs)
        d = {'@INPUT@': inputs, '@INPUT0@': inputs[0], '@INPUT1@': inputs[1],
             '@OUTPUT@': outputs, '@OUTPUT0@': outputs[0], '@OUTPUT1@': outputs[1],
             '@OUTDIR@': 'dir'}
        # Check dictionary
        self.assertEqual(ret, d)
        # Check substitutions
        cmd = ['some', 'ordinary', 'strings']
        self.assertEqual(substfunc(cmd, d), cmd)
        cmd = ['@OUTPUT@', 'ordinary', 'strings']
        self.assertEqual(substfunc(cmd, d), outputs + cmd[1:])
        cmd = ['@OUTPUT0@', '@OUTPUT1@', 'strings']
        self.assertEqual(substfunc(cmd, d), outputs + cmd[2:])
        cmd = ['@OUTPUT0@.out', '@INPUT1@.ok', '@OUTDIR@']
        self.assertEqual(substfunc(cmd, d), [outputs[0] + '.out', inputs[1] + '.ok', 'dir'])
        # Many inputs, can't use @INPUT@ like this
        cmd = ['@INPUT@.out', 'ordinary', 'strings']
        self.assertRaises(ME, substfunc, cmd, d)
        # Not enough inputs
        cmd = ['@INPUT2@.out', 'ordinary', 'strings']
        self.assertRaises(ME, substfunc, cmd, d)
        # Not enough outputs
        cmd = ['@OUTPUT2@.out', 'ordinary', 'strings']
        self.assertRaises(ME, substfunc, cmd, d)
        # Many outputs, can't use @OUTPUT@ like this
        cmd = ['@OUTPUT@.out', 'ordinary', 'strings']
        self.assertRaises(ME, substfunc, cmd, d)

    def test_needs_exe_wrapper_override(self):
        config = ConfigParser()
        config['binaries'] = {
            'c': '\'/usr/bin/gcc\'',
        }
        config['host_machine'] = {
            'system': '\'linux\'',
            'cpu_family': '\'arm\'',
            'cpu': '\'armv7\'',
            'endian': '\'little\'',
        }
        # Can not be used as context manager because we need to
        # open it a second time and this is not possible on
        # Windows.
        configfile = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        configfilename = configfile.name
        config.write(configfile)
        configfile.flush()
        configfile.close()
        detected_value = mesonbuild.environment.CrossBuildInfo(configfile.name).need_exe_wrapper()
        os.unlink(configfilename)

        desired_value = not detected_value
        config['properties'] = {
            'needs_exe_wrapper': 'true' if desired_value else 'false'
        }

        configfile = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        configfilename = configfile.name
        config.write(configfile)
        configfile.close()
        forced_value = mesonbuild.environment.CrossBuildInfo(configfile.name).need_exe_wrapper()
        os.unlink(configfilename)

        self.assertEqual(forced_value, desired_value)


class BasePlatformTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        src_root = os.path.dirname(__file__)
        src_root = os.path.join(os.getcwd(), src_root)
        self.src_root = src_root
        # In case the directory is inside a symlinked directory, find the real
        # path otherwise we might not find the srcdir from inside the builddir.
        self.builddir = os.path.realpath(tempfile.mkdtemp())
        self.logdir = os.path.join(self.builddir, 'meson-logs')
        self.prefix = '/usr'
        self.libdir = os.path.join(self.prefix, 'lib')
        self.installdir = os.path.join(self.builddir, 'install')
        self.distdir = os.path.join(self.builddir, 'meson-dist')
        # Get the backend
        # FIXME: Extract this from argv?
        self.backend = getattr(Backend, os.environ.get('MESON_UNIT_TEST_BACKEND', 'ninja'))
        self.meson_args = [os.path.join(src_root, 'meson.py'), '--backend=' + self.backend.name]
        self.meson_command = [sys.executable] + self.meson_args
        self.mconf_command = [sys.executable, os.path.join(src_root, 'mesonconf.py')]
        self.mintro_command = [sys.executable, os.path.join(src_root, 'mesonintrospect.py')]
        self.mtest_command = [sys.executable, os.path.join(src_root, 'mesontest.py'), '-C', self.builddir]
        # Backend-specific build commands
        self.build_command, self.clean_command, self.test_command, self.install_command, \
            self.uninstall_command = get_backend_commands(self.backend)
        # Test directories
        self.common_test_dir = os.path.join(src_root, 'test cases/common')
        self.vala_test_dir = os.path.join(src_root, 'test cases/vala')
        self.framework_test_dir = os.path.join(src_root, 'test cases/frameworks')
        self.unit_test_dir = os.path.join(src_root, 'test cases/unit')
        # Misc stuff
        self.orig_env = os.environ.copy()
        if self.backend is Backend.ninja:
            self.no_rebuild_stdout = 'ninja: no work to do.'
        else:
            # VS doesn't have a stable output when no changes are done
            # XCode backend is untested with unit tests, help welcome!
            self.no_rebuild_stdout = 'UNKNOWN BACKEND {!r}'.format(self.backend.name)

    def _print_meson_log(self):
        log = os.path.join(self.logdir, 'meson-log.txt')
        if not os.path.isfile(log):
            print("{!r} doesn't exist".format(log))
            return
        with open(log, 'r', encoding='utf-8') as f:
            print(f.read())

    def tearDown(self):
        windows_proof_rmtree(self.builddir)
        os.environ = self.orig_env
        super().tearDown()

    def _run(self, command, workdir=None):
        '''
        Run a command while printing the stdout and stderr to stdout,
        and also return a copy of it
        '''
        p = subprocess.Popen(command, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, env=os.environ.copy(),
                             universal_newlines=True, cwd=workdir)
        output = p.communicate()[0]
        print(output)
        if p.returncode != 0:
            if 'MESON_SKIP_TEST' in output:
                raise unittest.SkipTest('Project requested skipping.')
            raise subprocess.CalledProcessError(p.returncode, command)
        return output

    def init(self, srcdir, extra_args=None, default_args=True, inprocess=False):
        self.assertTrue(os.path.exists(srcdir))
        if extra_args is None:
            extra_args = []
        if not isinstance(extra_args, list):
            extra_args = [extra_args]
        args = [srcdir, self.builddir]
        if default_args:
            args += ['--prefix', self.prefix,
                     '--libdir', self.libdir]
        self.privatedir = os.path.join(self.builddir, 'meson-private')
        if inprocess:
            try:
                out = run_configure_inprocess(self.meson_args + args + extra_args)[1]
            except:
                self._print_meson_log()
                raise
            finally:
                # Close log file to satisfy Windows file locking
                mesonbuild.mlog.shutdown()
                mesonbuild.mlog.log_dir = None
                mesonbuild.mlog.log_file = None
        else:
            try:
                out = self._run(self.meson_command + args + extra_args)
            except unittest.SkipTest:
                raise unittest.SkipTest('Project requested skipping: ' + srcdir)
            except:
                self._print_meson_log()
                raise
        return out

    def build(self, target=None, extra_args=None):
        if extra_args is None:
            extra_args = []
        # Add arguments for building the target (if specified),
        # and using the build dir (if required, with VS)
        args = get_builddir_target_args(self.backend, self.builddir, target)
        return self._run(self.build_command + args + extra_args, workdir=self.builddir)

    def clean(self):
        dir_args = get_builddir_target_args(self.backend, self.builddir, None)
        self._run(self.clean_command + dir_args, workdir=self.builddir)

    def run_tests(self):
        self._run(self.test_command, workdir=self.builddir)

    def install(self):
        if self.backend is not Backend.ninja:
            raise unittest.SkipTest('{!r} backend can\'t install files'.format(self.backend.name))
        os.environ['DESTDIR'] = self.installdir
        self._run(self.install_command, workdir=self.builddir)

    def uninstall(self):
        self._run(self.uninstall_command, workdir=self.builddir)

    def run_target(self, target):
        '''
        Run a Ninja target while printing the stdout and stderr to stdout,
        and also return a copy of it
        '''
        return self.build(target=target)

    def setconf(self, arg, will_build=True):
        if will_build:
            ensure_backend_detects_changes(self.backend)
        self._run(self.mconf_command + [arg, self.builddir])

    def wipe(self):
        windows_proof_rmtree(self.builddir)

    def utime(self, f):
        ensure_backend_detects_changes(self.backend)
        os.utime(f)

    def get_compdb(self):
        if self.backend is not Backend.ninja:
            raise unittest.SkipTest('Compiler db not available with {} backend'.format(self.backend.name))
        with open(os.path.join(self.builddir, 'compile_commands.json')) as ifile:
            contents = json.load(ifile)
        # If Ninja is using .rsp files, generate them, read their contents, and
        # replace it as the command for all compile commands in the parsed json.
        if len(contents) > 0 and contents[0]['command'].endswith('.rsp'):
            # Pretend to build so that the rsp files are generated
            self.build(extra_args=['-d', 'keeprsp', '-n'])
            for each in contents:
                # Extract the actual command from the rsp file
                compiler, rsp = each['command'].split(' @')
                rsp = os.path.join(self.builddir, rsp)
                # Replace the command with its contents
                with open(rsp, 'r', encoding='utf-8') as f:
                    each['command'] = compiler + ' ' + f.read()
        return contents

    def get_meson_log(self):
        with open(os.path.join(self.builddir, 'meson-logs', 'meson-log.txt')) as f:
            return f.readlines()

    def get_meson_log_compiler_checks(self):
        '''
        Fetch a list command-lines run by meson for compiler checks.
        Each command-line is returned as a list of arguments.
        '''
        log = self.get_meson_log()
        prefix = 'Command line:'
        cmds = [l[len(prefix):].split() for l in log if l.startswith(prefix)]
        return cmds

    def introspect(self, arg):
        out = subprocess.check_output(self.mintro_command + [arg, self.builddir],
                                      universal_newlines=True)
        return json.loads(out)

    def assertPathEqual(self, path1, path2):
        '''
        Handles a lot of platform-specific quirks related to paths such as
        separator, case-sensitivity, etc.
        '''
        self.assertEqual(PurePath(path1), PurePath(path2))

    def assertPathBasenameEqual(self, path, basename):
        msg = '{!r} does not end with {!r}'.format(path, basename)
        # We cannot use os.path.basename because it returns '' when the path
        # ends with '/' for some silly reason. This is not how the UNIX utility
        # `basename` works.
        path_basename = PurePath(path).parts[-1]
        self.assertEqual(PurePath(path_basename), PurePath(basename), msg)

    def assertBuildIsNoop(self):
        ret = self.build()
        if self.backend is Backend.ninja:
            self.assertEqual(ret.split('\n')[-2], self.no_rebuild_stdout)
        elif self.backend is Backend.vs:
            # Ensure that some target said that no rebuild was done
            self.assertIn('CustomBuild:\n  All outputs are up-to-date.', ret)
            self.assertIn('ClCompile:\n  All outputs are up-to-date.', ret)
            self.assertIn('Link:\n  All outputs are up-to-date.', ret)
            # Ensure that no targets were built
            clre = re.compile('ClCompile:\n [^\n]*cl', flags=re.IGNORECASE)
            linkre = re.compile('Link:\n [^\n]*link', flags=re.IGNORECASE)
            self.assertNotRegex(ret, clre)
            self.assertNotRegex(ret, linkre)
        elif self.backend is Backend.xcode:
            raise unittest.SkipTest('Please help us fix this test on the xcode backend')
        else:
            raise RuntimeError('Invalid backend: {!r}'.format(self.backend.name))

    def assertRebuiltTarget(self, target):
        ret = self.build()
        if self.backend is Backend.ninja:
            self.assertIn('Linking target {}'.format(target), ret)
        elif self.backend is Backend.vs:
            # Ensure that this target was rebuilt
            clre = re.compile('ClCompile:\n [^\n]*cl[^\n]*' + target, flags=re.IGNORECASE)
            linkre = re.compile('Link:\n [^\n]*link[^\n]*' + target, flags=re.IGNORECASE)
            self.assertRegex(ret, clre)
            self.assertRegex(ret, linkre)
        elif self.backend is Backend.xcode:
            raise unittest.SkipTest('Please help us fix this test on the xcode backend')
        else:
            raise RuntimeError('Invalid backend: {!r}'.format(self.backend.name))


class AllPlatformTests(BasePlatformTests):
    '''
    Tests that should run on all platforms
    '''
    def test_default_options_prefix(self):
        '''
        Tests that setting a prefix in default_options in project() works.
        Can't be an ordinary test because we pass --prefix to meson there.
        https://github.com/mesonbuild/meson/issues/1349
        '''
        testdir = os.path.join(self.common_test_dir, '94 default options')
        self.init(testdir, default_args=False)
        opts = self.introspect('--buildoptions')
        for opt in opts:
            if opt['name'] == 'prefix':
                prefix = opt['value']
        self.assertEqual(prefix, '/absoluteprefix')

    def test_absolute_prefix_libdir(self):
        '''
        Tests that setting absolute paths for --prefix and --libdir work. Can't
        be an ordinary test because these are set via the command-line.
        https://github.com/mesonbuild/meson/issues/1341
        https://github.com/mesonbuild/meson/issues/1345
        '''
        testdir = os.path.join(self.common_test_dir, '94 default options')
        prefix = '/someabs'
        libdir = 'libdir'
        extra_args = ['--prefix=' + prefix,
                      # This can just be a relative path, but we want to test
                      # that passing this as an absolute path also works
                      '--libdir=' + prefix + '/' + libdir]
        self.init(testdir, extra_args, default_args=False)
        opts = self.introspect('--buildoptions')
        for opt in opts:
            if opt['name'] == 'prefix':
                self.assertEqual(prefix, opt['value'])
            elif opt['name'] == 'libdir':
                self.assertEqual(libdir, opt['value'])

    def test_libdir_must_be_inside_prefix(self):
        '''
        Tests that libdir is forced to be inside prefix no matter how it is set.
        Must be a unit test for obvious reasons.
        '''
        testdir = os.path.join(self.common_test_dir, '1 trivial')
        # libdir being inside prefix is ok
        args = ['--prefix', '/opt', '--libdir', '/opt/lib32']
        self.init(testdir, args)
        self.wipe()
        # libdir not being inside prefix is not ok
        args = ['--prefix', '/usr', '--libdir', '/opt/lib32']
        self.assertRaises(subprocess.CalledProcessError, self.init, testdir, args)
        self.wipe()
        # libdir must be inside prefix even when set via mesonconf
        self.init(testdir)
        self.assertRaises(subprocess.CalledProcessError, self.setconf, '-Dlibdir=/opt', False)

    def test_static_library_overwrite(self):
        '''
        Tests that static libraries are never appended to, always overwritten.
        Has to be a unit test because this involves building a project,
        reconfiguring, and building it again so that `ar` is run twice on the
        same static library.
        https://github.com/mesonbuild/meson/issues/1355
        '''
        testdir = os.path.join(self.common_test_dir, '3 static')
        env = Environment(testdir, self.builddir, self.meson_command,
                          get_fake_options(self.prefix), [])
        cc = env.detect_c_compiler(False)
        static_linker = env.detect_static_linker(cc)
        if is_windows():
            raise unittest.SkipTest('https://github.com/mesonbuild/meson/issues/1526')
        if not isinstance(static_linker, mesonbuild.compilers.ArLinker):
            raise unittest.SkipTest('static linker is not `ar`')
        # Configure
        self.init(testdir)
        # Get name of static library
        targets = self.introspect('--targets')
        self.assertEqual(len(targets), 1)
        libname = targets[0]['filename']
        # Build and get contents of static library
        self.build()
        before = self._run(['ar', 't', os.path.join(self.builddir, libname)]).split()
        # Filter out non-object-file contents
        before = [f for f in before if f.endswith(('.o', '.obj'))]
        # Static library should contain only one object
        self.assertEqual(len(before), 1, msg=before)
        # Change the source to be built into the static library
        self.setconf('-Dsource=libfile2.c')
        self.build()
        after = self._run(['ar', 't', os.path.join(self.builddir, libname)]).split()
        # Filter out non-object-file contents
        after = [f for f in after if f.endswith(('.o', '.obj'))]
        # Static library should contain only one object
        self.assertEqual(len(after), 1, msg=after)
        # and the object must have changed
        self.assertNotEqual(before, after)

    def test_static_compile_order(self):
        '''
        Test that the order of files in a compiler command-line while compiling
        and linking statically is deterministic. This can't be an ordinary test
        case because we need to inspect the compiler database.
        https://github.com/mesonbuild/meson/pull/951
        '''
        testdir = os.path.join(self.common_test_dir, '5 linkstatic')
        self.init(testdir)
        compdb = self.get_compdb()
        # Rules will get written out in this order
        self.assertTrue(compdb[0]['file'].endswith("libfile.c"))
        self.assertTrue(compdb[1]['file'].endswith("libfile2.c"))
        self.assertTrue(compdb[2]['file'].endswith("libfile3.c"))
        self.assertTrue(compdb[3]['file'].endswith("libfile4.c"))
        # FIXME: We don't have access to the linker command

    def test_run_target_files_path(self):
        '''
        Test that run_targets are run from the correct directory
        https://github.com/mesonbuild/meson/issues/957
        '''
        testdir = os.path.join(self.common_test_dir, '58 run target')
        self.init(testdir)
        self.run_target('check_exists')

    def test_install_introspection(self):
        '''
        Tests that the Meson introspection API exposes install filenames correctly
        https://github.com/mesonbuild/meson/issues/829
        '''
        if self.backend is not Backend.ninja:
            raise unittest.SkipTest('{!r} backend can\'t install files'.format(self.backend.name))
        testdir = os.path.join(self.common_test_dir, '8 install')
        self.init(testdir)
        intro = self.introspect('--targets')
        if intro[0]['type'] == 'executable':
            intro = intro[::-1]
        self.assertPathEqual(intro[0]['install_filename'], '/usr/lib/libstat.a')
        self.assertPathEqual(intro[1]['install_filename'], '/usr/bin/prog' + exe_suffix)

    def test_uninstall(self):
        exename = os.path.join(self.installdir, 'usr/bin/prog' + exe_suffix)
        testdir = os.path.join(self.common_test_dir, '8 install')
        self.init(testdir)
        self.assertFalse(os.path.exists(exename))
        self.install()
        self.assertTrue(os.path.exists(exename))
        self.uninstall()
        self.assertFalse(os.path.exists(exename))

    def test_testsetups(self):
        if not shutil.which('valgrind'):
                raise unittest.SkipTest('Valgrind not installed.')
        testdir = os.path.join(self.unit_test_dir, '2 testsetups')
        self.init(testdir)
        self.build()
        # Run tests without setup
        self.run_tests()
        with open(os.path.join(self.logdir, 'testlog.txt')) as f:
            basic_log = f.read()
        # Run buggy test with setup that has env that will make it fail
        self.assertRaises(subprocess.CalledProcessError,
                          self._run, self.mtest_command + ['--setup=valgrind'])
        with open(os.path.join(self.logdir, 'testlog-valgrind.txt')) as f:
            vg_log = f.read()
        self.assertFalse('TEST_ENV is set' in basic_log)
        self.assertFalse('Memcheck' in basic_log)
        self.assertTrue('TEST_ENV is set' in vg_log)
        self.assertTrue('Memcheck' in vg_log)
        # Run buggy test with setup without env that will pass
        self._run(self.mtest_command + ['--setup=wrapper'])
        # Setup with no properties works
        self._run(self.mtest_command + ['--setup=empty'])
        # Setup with only env works
        self._run(self.mtest_command + ['--setup=onlyenv'])
        # Setup with only a timeout works
        self._run(self.mtest_command + ['--setup=timeout'])

    def assertFailedTestCount(self, failure_count, command):
        try:
            self._run(command)
            self.assertEqual(0, failure_count, 'Expected %d tests to fail.' % failure_count)
        except subprocess.CalledProcessError as e:
            self.assertEqual(e.returncode, failure_count)

    def test_suite_selection(self):
        testdir = os.path.join(self.unit_test_dir, '4 suite selection')
        self.init(testdir)
        self.build()

        self.assertFailedTestCount(3, self.mtest_command)

        self.assertFailedTestCount(0, self.mtest_command + ['--suite', ':success'])
        self.assertFailedTestCount(3, self.mtest_command + ['--suite', ':fail'])
        self.assertFailedTestCount(3, self.mtest_command + ['--no-suite', ':success'])
        self.assertFailedTestCount(0, self.mtest_command + ['--no-suite', ':fail'])

        self.assertFailedTestCount(1, self.mtest_command + ['--suite', 'mainprj'])
        self.assertFailedTestCount(0, self.mtest_command + ['--suite', 'subprjsucc'])
        self.assertFailedTestCount(1, self.mtest_command + ['--suite', 'subprjfail'])
        self.assertFailedTestCount(1, self.mtest_command + ['--suite', 'subprjmix'])
        self.assertFailedTestCount(2, self.mtest_command + ['--no-suite', 'mainprj'])
        self.assertFailedTestCount(3, self.mtest_command + ['--no-suite', 'subprjsucc'])
        self.assertFailedTestCount(2, self.mtest_command + ['--no-suite', 'subprjfail'])
        self.assertFailedTestCount(2, self.mtest_command + ['--no-suite', 'subprjmix'])

        self.assertFailedTestCount(1, self.mtest_command + ['--suite', 'mainprj:fail'])
        self.assertFailedTestCount(0, self.mtest_command + ['--suite', 'mainprj:success'])
        self.assertFailedTestCount(2, self.mtest_command + ['--no-suite', 'mainprj:fail'])
        self.assertFailedTestCount(3, self.mtest_command + ['--no-suite', 'mainprj:success'])

        self.assertFailedTestCount(1, self.mtest_command + ['--suite', 'subprjfail:fail'])
        self.assertFailedTestCount(0, self.mtest_command + ['--suite', 'subprjfail:success'])
        self.assertFailedTestCount(2, self.mtest_command + ['--no-suite', 'subprjfail:fail'])
        self.assertFailedTestCount(3, self.mtest_command + ['--no-suite', 'subprjfail:success'])

        self.assertFailedTestCount(0, self.mtest_command + ['--suite', 'subprjsucc:fail'])
        self.assertFailedTestCount(0, self.mtest_command + ['--suite', 'subprjsucc:success'])
        self.assertFailedTestCount(3, self.mtest_command + ['--no-suite', 'subprjsucc:fail'])
        self.assertFailedTestCount(3, self.mtest_command + ['--no-suite', 'subprjsucc:success'])

        self.assertFailedTestCount(1, self.mtest_command + ['--suite', 'subprjmix:fail'])
        self.assertFailedTestCount(0, self.mtest_command + ['--suite', 'subprjmix:success'])
        self.assertFailedTestCount(2, self.mtest_command + ['--no-suite', 'subprjmix:fail'])
        self.assertFailedTestCount(3, self.mtest_command + ['--no-suite', 'subprjmix:success'])

        self.assertFailedTestCount(2, self.mtest_command + ['--suite', 'subprjfail', '--suite', 'subprjmix:fail'])
        self.assertFailedTestCount(3, self.mtest_command + ['--suite', 'subprjfail', '--suite', 'subprjmix', '--suite', 'mainprj'])
        self.assertFailedTestCount(2, self.mtest_command + ['--suite', 'subprjfail', '--suite', 'subprjmix', '--suite', 'mainprj', '--no-suite', 'subprjmix:fail'])
        self.assertFailedTestCount(1, self.mtest_command + ['--suite', 'subprjfail', '--suite', 'subprjmix', '--suite', 'mainprj', '--no-suite', 'subprjmix:fail', 'mainprj-failing_test'])

        self.assertFailedTestCount(1, self.mtest_command + ['--no-suite', 'subprjfail:fail', '--no-suite', 'subprjmix:fail'])

    def test_build_by_default(self):
        testdir = os.path.join(self.common_test_dir, '137 build by default')
        self.init(testdir)
        self.build()
        genfile = os.path.join(self.builddir, 'generated.dat')
        exe = os.path.join(self.builddir, 'fooprog' + exe_suffix)
        self.assertTrue(os.path.exists(genfile))
        self.assertFalse(os.path.exists(exe))
        self.build(target=('fooprog' + exe_suffix))
        self.assertTrue(os.path.exists(exe))

    def test_internal_include_order(self):
        testdir = os.path.join(self.common_test_dir, '138 include order')
        self.init(testdir)
        execmd = fxecmd = None
        for cmd in self.get_compdb():
            if 'someexe' in cmd['command']:
                execmd = cmd['command']
                continue
            if 'somefxe' in cmd['command']:
                fxecmd = cmd['command']
                continue
        if not execmd or not fxecmd:
            raise Exception('Could not find someexe and somfxe commands')
        # Check include order for 'someexe'
        incs = [a for a in shlex.split(execmd) if a.startswith("-I")]
        self.assertEqual(len(incs), 8)
        # target private dir
        self.assertPathEqual(incs[0], "-Isub4/someexe@exe")
        # target build subdir
        self.assertPathEqual(incs[1], "-Isub4")
        # target source subdir
        self.assertPathBasenameEqual(incs[2], 'sub4')
        # include paths added via per-target c_args: ['-I'...]
        self.assertPathBasenameEqual(incs[3], 'sub3')
        # target include_directories: build dir
        self.assertPathEqual(incs[4], "-Isub2")
        # target include_directories: source dir
        self.assertPathBasenameEqual(incs[5], 'sub2')
        # target internal dependency include_directories: build dir
        self.assertPathEqual(incs[6], "-Isub1")
        # target internal dependency include_directories: source dir
        self.assertPathBasenameEqual(incs[7], 'sub1')
        # Check include order for 'somefxe'
        incs = [a for a in shlex.split(fxecmd) if a.startswith('-I')]
        self.assertEqual(len(incs), 9)
        # target private dir
        self.assertPathEqual(incs[0], '-Isomefxe@exe')
        # target build dir
        self.assertPathEqual(incs[1], '-I.')
        # target source dir
        self.assertPathBasenameEqual(incs[2], os.path.basename(testdir))
        # target internal dependency correct include_directories: build dir
        self.assertPathEqual(incs[3], "-Isub4")
        # target internal dependency correct include_directories: source dir
        self.assertPathBasenameEqual(incs[4], 'sub4')
        # target internal dependency dep include_directories: build dir
        self.assertPathEqual(incs[5], "-Isub1")
        # target internal dependency dep include_directories: source dir
        self.assertPathBasenameEqual(incs[6], 'sub1')
        # target internal dependency wrong include_directories: build dir
        self.assertPathEqual(incs[7], "-Isub2")
        # target internal dependency wrong include_directories: source dir
        self.assertPathBasenameEqual(incs[8], 'sub2')

    def test_compiler_detection(self):
        '''
        Test that automatic compiler detection and setting from the environment
        both work just fine. This is needed because while running project tests
        and other unit tests, we always read CC/CXX/etc from the environment.
        '''
        gnu = mesonbuild.compilers.GnuCompiler
        clang = mesonbuild.compilers.ClangCompiler
        intel = mesonbuild.compilers.IntelCompiler
        msvc = mesonbuild.compilers.VisualStudioCCompiler
        ar = mesonbuild.compilers.ArLinker
        lib = mesonbuild.compilers.VisualStudioLinker
        langs = [('c', 'CC'), ('cpp', 'CXX')]
        if not is_windows():
            langs += [('objc', 'OBJC'), ('objcpp', 'OBJCXX')]
        testdir = os.path.join(self.unit_test_dir, '5 compiler detection')
        env = Environment(testdir, self.builddir, self.meson_command,
                          get_fake_options(self.prefix), [])
        for lang, evar in langs:
            # Detect with evar and do sanity checks on that
            if evar in os.environ:
                ecc = getattr(env, 'detect_{}_compiler'.format(lang))(False)
                elinker = env.detect_static_linker(ecc)
                # Pop it so we don't use it for the next detection
                evalue = os.environ.pop(evar)
                # Very rough/strict heuristics. Would never work for actual
                # compiler detection, but should be ok for the tests.
                if os.path.basename(evalue).startswith('g'):
                    self.assertIsInstance(ecc, gnu)
                    self.assertIsInstance(elinker, ar)
                elif 'clang' in os.path.basename(evalue):
                    self.assertIsInstance(ecc, clang)
                    self.assertIsInstance(elinker, ar)
                elif os.path.basename(evalue).startswith('ic'):
                    self.assertIsInstance(ecc, intel)
                    self.assertIsInstance(elinker, ar)
                elif os.path.basename(evalue).startswith('cl'):
                    self.assertIsInstance(ecc, msvc)
                    self.assertIsInstance(elinker, lib)
                else:
                    raise AssertionError('Unknown compiler {!r}'.format(evalue))
                # Check that we actually used the evalue correctly as the compiler
                self.assertEqual(ecc.get_exelist(), shlex.split(evalue))
            # Do auto-detection of compiler based on platform, PATH, etc.
            cc = getattr(env, 'detect_{}_compiler'.format(lang))(False)
            linker = env.detect_static_linker(cc)
            # Check compiler type
            if isinstance(cc, gnu):
                self.assertIsInstance(linker, ar)
                if is_osx():
                    self.assertEqual(cc.gcc_type, mesonbuild.compilers.GCC_OSX)
                elif is_windows():
                    self.assertEqual(cc.gcc_type, mesonbuild.compilers.GCC_MINGW)
                elif is_cygwin():
                    self.assertEqual(cc.gcc_type, mesonbuild.compilers.GCC_CYGWIN)
                else:
                    self.assertEqual(cc.gcc_type, mesonbuild.compilers.GCC_STANDARD)
            if isinstance(cc, clang):
                self.assertIsInstance(linker, ar)
                if is_osx():
                    self.assertEqual(cc.clang_type, mesonbuild.compilers.CLANG_OSX)
                elif is_windows():
                    # Not implemented yet
                    self.assertEqual(cc.clang_type, mesonbuild.compilers.CLANG_WIN)
                else:
                    self.assertEqual(cc.clang_type, mesonbuild.compilers.CLANG_STANDARD)
            if isinstance(cc, intel):
                self.assertIsInstance(linker, ar)
                if is_osx():
                    self.assertEqual(cc.icc_type, mesonbuild.compilers.ICC_OSX)
                elif is_windows():
                    self.assertEqual(cc.icc_type, mesonbuild.compilers.ICC_WIN)
                else:
                    self.assertEqual(cc.icc_type, mesonbuild.compilers.ICC_STANDARD)
            if isinstance(cc, msvc):
                self.assertTrue(is_windows())
                self.assertIsInstance(linker, lib)
                self.assertEqual(cc.id, 'msvc')
            # Set evar ourselves to a wrapper script that just calls the same
            # exelist + some argument. This is meant to test that setting
            # something like `ccache gcc -pipe` or `distcc ccache gcc` works.
            wrapper = os.path.join(testdir, 'compiler wrapper.py')
            wrappercc = [sys.executable, wrapper] + cc.get_exelist() + cc.get_always_args()
            wrappercc_s = ''
            for w in wrappercc:
                wrappercc_s += shlex.quote(w) + ' '
            os.environ[evar] = wrappercc_s
            wcc = getattr(env, 'detect_{}_compiler'.format(lang))(False)
            # Check static linker too
            wrapperlinker = [sys.executable, wrapper] + linker.get_exelist() + linker.get_always_args()
            wrapperlinker_s = ''
            for w in wrapperlinker:
                wrapperlinker_s += shlex.quote(w) + ' '
            os.environ['AR'] = wrapperlinker_s
            wlinker = env.detect_static_linker(wcc)
            # Must be the same type since it's a wrapper around the same exelist
            self.assertIs(type(cc), type(wcc))
            self.assertIs(type(linker), type(wlinker))
            # Ensure that the exelist is correct
            self.assertEqual(wcc.get_exelist(), wrappercc)
            self.assertEqual(wlinker.get_exelist(), wrapperlinker)

    def test_always_prefer_c_compiler_for_asm(self):
        testdir = os.path.join(self.common_test_dir, '141 c cpp and asm')
        # Skip if building with MSVC
        env = Environment(testdir, self.builddir, self.meson_command,
                          get_fake_options(self.prefix), [])
        if env.detect_c_compiler(False).get_id() == 'msvc':
            raise unittest.SkipTest('MSVC can\'t compile assembly')
        self.init(testdir)
        commands = {'c-asm': {}, 'cpp-asm': {}, 'cpp-c-asm': {}, 'c-cpp-asm': {}}
        for cmd in self.get_compdb():
            # Get compiler
            split = shlex.split(cmd['command'])
            if split[0] == 'ccache':
                compiler = split[1]
            else:
                compiler = split[0]
            # Classify commands
            if 'Ic-asm' in cmd['command']:
                if cmd['file'].endswith('.S'):
                    commands['c-asm']['asm'] = compiler
                elif cmd['file'].endswith('.c'):
                    commands['c-asm']['c'] = compiler
                else:
                    raise AssertionError('{!r} found in cpp-asm?'.format(cmd['command']))
            elif 'Icpp-asm' in cmd['command']:
                if cmd['file'].endswith('.S'):
                    commands['cpp-asm']['asm'] = compiler
                elif cmd['file'].endswith('.cpp'):
                    commands['cpp-asm']['cpp'] = compiler
                else:
                    raise AssertionError('{!r} found in cpp-asm?'.format(cmd['command']))
            elif 'Ic-cpp-asm' in cmd['command']:
                if cmd['file'].endswith('.S'):
                    commands['c-cpp-asm']['asm'] = compiler
                elif cmd['file'].endswith('.c'):
                    commands['c-cpp-asm']['c'] = compiler
                elif cmd['file'].endswith('.cpp'):
                    commands['c-cpp-asm']['cpp'] = compiler
                else:
                    raise AssertionError('{!r} found in c-cpp-asm?'.format(cmd['command']))
            elif 'Icpp-c-asm' in cmd['command']:
                if cmd['file'].endswith('.S'):
                    commands['cpp-c-asm']['asm'] = compiler
                elif cmd['file'].endswith('.c'):
                    commands['cpp-c-asm']['c'] = compiler
                elif cmd['file'].endswith('.cpp'):
                    commands['cpp-c-asm']['cpp'] = compiler
                else:
                    raise AssertionError('{!r} found in cpp-c-asm?'.format(cmd['command']))
            else:
                raise AssertionError('Unknown command {!r} found'.format(cmd['command']))
        # Check that .S files are always built with the C compiler
        self.assertEqual(commands['c-asm']['asm'], commands['c-asm']['c'])
        self.assertEqual(commands['c-asm']['asm'], commands['cpp-asm']['asm'])
        self.assertEqual(commands['cpp-asm']['asm'], commands['c-cpp-asm']['c'])
        self.assertEqual(commands['c-cpp-asm']['asm'], commands['c-cpp-asm']['c'])
        self.assertEqual(commands['cpp-c-asm']['asm'], commands['cpp-c-asm']['c'])
        self.assertNotEqual(commands['cpp-asm']['asm'], commands['cpp-asm']['cpp'])
        self.assertNotEqual(commands['c-cpp-asm']['c'], commands['c-cpp-asm']['cpp'])
        self.assertNotEqual(commands['cpp-c-asm']['c'], commands['cpp-c-asm']['cpp'])
        # Check that the c-asm target is always linked with the C linker
        build_ninja = os.path.join(self.builddir, 'build.ninja')
        with open(build_ninja, 'r', encoding='utf-8') as f:
            contents = f.read()
            m = re.search('build c-asm.*: c_LINKER', contents)
        self.assertIsNotNone(m, msg=contents)

    def test_preprocessor_checks_CPPFLAGS(self):
        '''
        Test that preprocessor compiler checks read CPPFLAGS but not CFLAGS
        '''
        testdir = os.path.join(self.common_test_dir, '140 get define')
        define = 'MESON_TEST_DEFINE_VALUE'
        # NOTE: this list can't have \n, ' or "
        # \n is never substituted by the GNU pre-processor via a -D define
        # ' and " confuse shlex.split() even when they are escaped
        # % and # confuse the MSVC preprocessor
        value = 'spaces and fun!@$^&*()-=_+{}[]:;<>?,./~`'
        os.environ['CPPFLAGS'] = '-D{}="{}"'.format(define, value)
        os.environ['CFLAGS'] = '-DMESON_FAIL_VALUE=cflags-read'.format(define)
        self.init(testdir, ['-D{}={}'.format(define, value)])

    def test_custom_target_exe_data_deterministic(self):
        testdir = os.path.join(self.common_test_dir, '117 custom target capture')
        self.init(testdir)
        meson_exe_dat1 = glob(os.path.join(self.privatedir, 'meson_exe*.dat'))
        self.wipe()
        self.init(testdir)
        meson_exe_dat2 = glob(os.path.join(self.privatedir, 'meson_exe*.dat'))
        self.assertListEqual(meson_exe_dat1, meson_exe_dat2)

    def test_source_changes_cause_rebuild(self):
        '''
        Test that changes to sources and headers cause rebuilds, but not
        changes to unused files (as determined by the dependency file) in the
        input files list.
        '''
        testdir = os.path.join(self.common_test_dir, '22 header in file list')
        self.init(testdir)
        self.build()
        # Immediately rebuilding should not do anything
        self.assertBuildIsNoop()
        # Changing mtime of header.h should rebuild everything
        self.utime(os.path.join(testdir, 'header.h'))
        self.assertRebuiltTarget('prog')

    def test_custom_target_changes_cause_rebuild(self):
        '''
        Test that in a custom target, changes to the input files, the
        ExternalProgram, and any File objects on the command-line cause
        a rebuild.
        '''
        testdir = os.path.join(self.common_test_dir, '64 custom header generator')
        self.init(testdir)
        self.build()
        # Immediately rebuilding should not do anything
        self.assertBuildIsNoop()
        # Changing mtime of these should rebuild everything
        for f in ('input.def', 'makeheader.py', 'somefile.txt'):
            self.utime(os.path.join(testdir, f))
            self.assertRebuiltTarget('prog')

    def test_static_library_lto(self):
        '''
        Test that static libraries can be built with LTO and linked to
        executables. On Linux, this requires the use of gcc-ar.
        https://github.com/mesonbuild/meson/issues/1646
        '''
        testdir = os.path.join(self.common_test_dir, '5 linkstatic')
        self.init(testdir, extra_args='-Db_lto=true')
        self.build()
        self.run_tests()

    def test_dist(self):
        if not shutil.which('git'):
            raise unittest.SkipTest('Git not found')
        try:
            self.dist_impl()
        except PermissionError:
            # When run under Windows CI, something (virus scanner?)
            # holds on to the git files so cleaning up the dir
            # fails sometimes.
            pass

    def dist_impl(self):
        # Create this on the fly because having rogue .git directories inside
        # the source tree leads to all kinds of trouble.
        with tempfile.TemporaryDirectory() as project_dir:
            with open(os.path.join(project_dir, 'meson.build'), 'w') as ofile:
                ofile.write('''project('disttest', 'c', version : '1.4.3')
e = executable('distexe', 'distexe.c')
test('dist test', e)
''')
            with open(os.path.join(project_dir, 'distexe.c'), 'w') as ofile:
                ofile.write('''#include<stdio.h>

int main(int argc, char **argv) {
    printf("I am a distribution test.\\n");
    return 0;
}
''')
            subprocess.check_call(['git', 'init'], cwd=project_dir)
            subprocess.check_call(['git', 'config',
                                   'user.name', 'Author Person'], cwd=project_dir)
            subprocess.check_call(['git', 'config',
                                   'user.email', 'teh_coderz@example.com'], cwd=project_dir)
            subprocess.check_call(['git', 'add', 'meson.build', 'distexe.c'], cwd=project_dir)
            subprocess.check_call(['git', 'commit', '-a', '-m', 'I am a project'], cwd=project_dir)
            self.init(project_dir)
            self.build('dist')
            distfile = os.path.join(self.distdir, 'disttest-1.4.3.tar.xz')
            checksumfile = distfile + '.sha256sum'
            self.assertTrue(os.path.exists(distfile))
            self.assertTrue(os.path.exists(checksumfile))

    def test_rpath_uses_ORIGIN(self):
        '''
        Test that built targets use $ORIGIN in rpath, which ensures that they
        are relocatable and ensures that builds are reproducible since the
        build directory won't get embedded into the built binaries.
        '''
        if is_windows() or is_cygwin():
            raise unittest.SkipTest('Windows PE/COFF binaries do not use RPATH')
        testdir = os.path.join(self.common_test_dir, '46 library chain')
        self.init(testdir)
        self.build()
        for each in ('prog', 'subdir/liblib1.so', 'subdir/subdir2/liblib2.so',
                     'subdir/subdir3/liblib3.so'):
            rpath = get_rpath(os.path.join(self.builddir, each))
            self.assertTrue(rpath)
            for path in rpath.split(':'):
                self.assertTrue(path.startswith('$ORIGIN'), msg=(each, path))

    def test_dash_d_dedup(self):
        testdir = os.path.join(self.unit_test_dir, '10 d dedup')
        self.init(testdir)
        cmd = self.get_compdb()[0]['command']
        self.assertTrue('-D FOO -D BAR' in cmd or
                        '"-D" "FOO" "-D" "BAR"' in cmd or
                        '/D FOO /D BAR' in cmd or
                        '"/D" "FOO" "/D" "BAR"' in cmd)


class FailureTests(BasePlatformTests):
    '''
    Tests that test failure conditions. Build files here should be dynamically
    generated and static tests should go into `test cases/failing*`.
    This is useful because there can be many ways in which a particular
    function can fail, and creating failing tests for all of them is tedious
    and slows down testing.
    '''
    dnf = "[Dd]ependency.*not found"

    def setUp(self):
        super().setUp()
        self.srcdir = os.path.realpath(tempfile.mkdtemp())
        self.mbuild = os.path.join(self.srcdir, 'meson.build')

    def tearDown(self):
        super().tearDown()
        windows_proof_rmtree(self.srcdir)

    def assertMesonRaises(self, contents, match, extra_args=None, langs=None):
        '''
        Assert that running meson configure on the specified @contents raises
        a error message matching regex @match.
        '''
        if langs is None:
            langs = []
        with open(self.mbuild, 'w') as f:
            f.write("project('failure test', 'c', 'cpp')\n")
            for lang in langs:
                f.write("add_languages('{}', required : false)\n".format(lang))
            f.write(contents)
        # Force tracebacks so we can detect them properly
        os.environ['MESON_FORCE_BACKTRACE'] = '1'
        with self.assertRaisesRegex(DependencyException, match, msg=contents):
            # Must run in-process or we'll get a generic CalledProcessError
            self.init(self.srcdir, extra_args=extra_args, inprocess=True)

    def assertMesonOutputs(self, contents, match, extra_args=None, langs=None):
        '''
        Assert that running meson configure on the specified @contents outputs
        something that matches regex @match.
        '''
        if langs is None:
            langs = []
        with open(self.mbuild, 'w') as f:
            f.write("project('output test', 'c', 'cpp')\n")
            for lang in langs:
                f.write("add_languages('{}', required : false)\n".format(lang))
            f.write(contents)
        # Run in-process for speed and consistency with assertMesonRaises
        out = self.init(self.srcdir, extra_args=extra_args, inprocess=True)
        self.assertRegex(out, match)

    def test_dependency(self):
        if not shutil.which('pkg-config'):
            raise unittest.SkipTest('pkg-config not found')
        a = (("dependency('zlib', method : 'fail')", "'fail' is invalid"),
             ("dependency('zlib', static : '1')", "[Ss]tatic.*boolean"),
             ("dependency('zlib', version : 1)", "[Vv]ersion.*string or list"),
             ("dependency('zlib', required : 1)", "[Rr]equired.*boolean"),
             ("dependency('zlib', method : 1)", "[Mm]ethod.*string"),
             ("dependency('zlibfail')", self.dnf),)
        for contents, match in a:
            self.assertMesonRaises(contents, match)

    def test_apple_frameworks_dependency(self):
        if not is_osx():
            raise unittest.SkipTest('only run on macOS')
        self.assertMesonRaises("dependency('appleframeworks')",
                               "requires at least one module")

    def test_sdl2_notfound_dependency(self):
        # Want to test failure, so skip if available
        if shutil.which('sdl2-config'):
            raise unittest.SkipTest('sdl2-config found')
        self.assertMesonRaises("dependency('sdl2', method : 'sdlconfig')", self.dnf)
        self.assertMesonRaises("dependency('sdl2', method : 'pkg-config')", self.dnf)

    def test_gnustep_notfound_dependency(self):
        # Want to test failure, so skip if available
        if shutil.which('gnustep-config'):
            raise unittest.SkipTest('gnustep-config found')
        self.assertMesonRaises("dependency('gnustep')",
                               "(requires a Objc compiler|{})".format(self.dnf),
                               langs = ['objc'])

    def test_wx_notfound_dependency(self):
        # Want to test failure, so skip if available
        if shutil.which('wx-config-3.0') or shutil.which('wx-config'):
            raise unittest.SkipTest('wx-config or wx-config-3.0 found')
        self.assertMesonRaises("dependency('wxwidgets')", self.dnf)
        self.assertMesonOutputs("dependency('wxwidgets', required : false)",
                                "nor wx-config found")

    def test_wx_dependency(self):
        if not shutil.which('wx-config-3.0') and not shutil.which('wx-config'):
            raise unittest.SkipTest('Neither wx-config nor wx-config-3.0 found')
        self.assertMesonRaises("dependency('wxwidgets', modules : 1)",
                               "module argument is not a string")

    def test_llvm_dependency(self):
        self.assertMesonRaises("dependency('llvm', modules : 'fail')",
                               "(required.*fail|{})".format(self.dnf))

    def test_boost_notfound_dependency(self):
        # Can be run even if Boost is found or not
        self.assertMesonRaises("dependency('boost', modules : 1)",
                               "module.*not a string")
        self.assertMesonRaises("dependency('boost', modules : 'fail')",
                               "(fail.*not found|{})".format(self.dnf))

    def test_boost_BOOST_ROOT_dependency(self):
        # Test BOOST_ROOT; can be run even if Boost is found or not
        os.environ['BOOST_ROOT'] = 'relative/path'
        self.assertMesonRaises("dependency('boost')",
                               "(BOOST_ROOT.*absolute|{})".format(self.dnf))


class WindowsTests(BasePlatformTests):
    '''
    Tests that should run on Cygwin, MinGW, and MSVC
    '''
    def setUp(self):
        super().setUp()
        self.platform_test_dir = os.path.join(self.src_root, 'test cases/windows')

    def test_find_program(self):
        '''
        Test that Windows-specific edge-cases in find_program are functioning
        correctly. Cannot be an ordinary test because it involves manipulating
        PATH to point to a directory with Python scripts.
        '''
        testdir = os.path.join(self.platform_test_dir, '9 find program')
        # Find `cmd` and `cmd.exe`
        prog1 = ExternalProgram('cmd')
        self.assertTrue(prog1.found(), msg='cmd not found')
        prog2 = ExternalProgram('cmd.exe')
        self.assertTrue(prog2.found(), msg='cmd.exe not found')
        self.assertPathEqual(prog1.get_path(), prog2.get_path())
        # Find cmd with an absolute path that's missing the extension
        cmd_path = prog2.get_path()[:-4]
        prog = ExternalProgram(cmd_path)
        self.assertTrue(prog.found(), msg='{!r} not found'.format(cmd_path))
        # Finding a script with no extension inside a directory works
        prog = ExternalProgram(os.path.join(testdir, 'test-script'))
        self.assertTrue(prog.found(), msg='test-script not found')
        # Finding a script with an extension inside a directory works
        prog = ExternalProgram(os.path.join(testdir, 'test-script-ext.py'))
        self.assertTrue(prog.found(), msg='test-script-ext.py not found')
        # Finding a script in PATH w/o extension works and adds the interpreter
        os.environ['PATH'] += os.pathsep + testdir
        prog = ExternalProgram('test-script-ext')
        self.assertTrue(prog.found(), msg='test-script-ext not found in PATH')
        self.assertPathEqual(prog.get_command()[0], sys.executable)
        self.assertPathBasenameEqual(prog.get_path(), 'test-script-ext.py')
        # Finding a script in PATH with extension works and adds the interpreter
        prog = ExternalProgram('test-script-ext.py')
        self.assertTrue(prog.found(), msg='test-script-ext.py not found in PATH')
        self.assertPathEqual(prog.get_command()[0], sys.executable)
        self.assertPathBasenameEqual(prog.get_path(), 'test-script-ext.py')


class LinuxlikeTests(BasePlatformTests):
    '''
    Tests that should run on Linux and *BSD
    '''
    def test_basic_soname(self):
        '''
        Test that the soname is set correctly for shared libraries. This can't
        be an ordinary test case because we need to run `readelf` and actually
        check the soname.
        https://github.com/mesonbuild/meson/issues/785
        '''
        testdir = os.path.join(self.common_test_dir, '4 shared')
        self.init(testdir)
        self.build()
        lib1 = os.path.join(self.builddir, 'libmylib.so')
        soname = get_soname(lib1)
        self.assertEqual(soname, 'libmylib.so')

    def test_custom_soname(self):
        '''
        Test that the soname is set correctly for shared libraries when
        a custom prefix and/or suffix is used. This can't be an ordinary test
        case because we need to run `readelf` and actually check the soname.
        https://github.com/mesonbuild/meson/issues/785
        '''
        testdir = os.path.join(self.common_test_dir, '27 library versions')
        self.init(testdir)
        self.build()
        lib1 = os.path.join(self.builddir, 'prefixsomelib.suffix')
        soname = get_soname(lib1)
        self.assertEqual(soname, 'prefixsomelib.suffix')

    def test_pic(self):
        '''
        Test that -fPIC is correctly added to static libraries when b_staticpic
        is true and not when it is false. This can't be an ordinary test case
        because we need to inspect the compiler database.
        '''
        testdir = os.path.join(self.common_test_dir, '3 static')
        self.init(testdir)
        compdb = self.get_compdb()
        self.assertIn('-fPIC', compdb[0]['command'])
        self.setconf('-Db_staticpic=false')
        # Regenerate build
        self.build()
        compdb = self.get_compdb()
        self.assertNotIn('-fPIC', compdb[0]['command'])

    def test_pkgconfig_gen(self):
        '''
        Test that generated pkg-config files can be found and have the correct
        version and link args. This can't be an ordinary test case because we
        need to run pkg-config outside of a Meson build file.
        https://github.com/mesonbuild/meson/issues/889
        '''
        testdir = os.path.join(self.common_test_dir, '51 pkgconfig-gen')
        self.init(testdir)
        env = FakeEnvironment()
        kwargs = {'required': True, 'silent': True}
        os.environ['PKG_CONFIG_LIBDIR'] = self.privatedir
        simple_dep = PkgConfigDependency('libfoo', env, kwargs)
        self.assertTrue(simple_dep.found())
        self.assertEqual(simple_dep.get_version(), '1.0')
        self.assertIn('-lfoo', simple_dep.get_link_args())
        self.assertEqual(simple_dep.get_pkgconfig_variable('foo'), 'bar')
        self.assertPathEqual(simple_dep.get_pkgconfig_variable('datadir'), '/usr/data')

    def test_vala_c_warnings(self):
        '''
        Test that no warnings are emitted for C code generated by Vala. This
        can't be an ordinary test case because we need to inspect the compiler
        database.
        https://github.com/mesonbuild/meson/issues/864
        '''
        testdir = os.path.join(self.vala_test_dir, '5 target glib')
        self.init(testdir)
        compdb = self.get_compdb()
        vala_command = None
        c_command = None
        for each in compdb:
            if each['file'].endswith('GLib.Thread.c'):
                vala_command = each['command']
            elif each['file'].endswith('GLib.Thread.vala'):
                continue
            elif each['file'].endswith('retcode.c'):
                c_command = each['command']
            else:
                m = 'Unknown file {!r} in vala_c_warnings test'.format(each['file'])
                raise AssertionError(m)
        self.assertIsNotNone(vala_command)
        self.assertIsNotNone(c_command)
        # -w suppresses all warnings, should be there in Vala but not in C
        self.assertIn(" -w ", vala_command)
        self.assertNotIn(" -w ", c_command)
        # -Wall enables all warnings, should be there in C but not in Vala
        self.assertNotIn(" -Wall ", vala_command)
        self.assertIn(" -Wall ", c_command)
        # -Werror converts warnings to errors, should always be there since it's
        # injected by an unrelated piece of code and the project has werror=true
        self.assertIn(" -Werror ", vala_command)
        self.assertIn(" -Werror ", c_command)

    def test_qt5dependency_pkgconfig_detection(self):
        '''
        Test that qt4 and qt5 detection with pkgconfig works.
        '''
        # Verify Qt4 or Qt5 can be found with pkg-config
        if not shutil.which('pkg-config'):
            raise unittest.SkipTest('pkg-config not found')
        qt4 = subprocess.call(['pkg-config', '--exists', 'QtCore'])
        qt5 = subprocess.call(['pkg-config', '--exists', 'Qt5Core'])
        if qt4 != 0 or qt5 != 0:
            raise unittest.SkipTest('Qt not found with pkg-config')
        testdir = os.path.join(self.framework_test_dir, '4 qt')
        self.init(testdir, ['-Dmethod=pkg-config'])
        # Confirm that the dependency was found with qmake
        msg = 'Qt4 native `pkg-config` dependency (modules: Core, Gui) found: YES\n'
        msg2 = 'Qt5 native `pkg-config` dependency (modules: Core, Gui) found: YES\n'
        mesonlog = self.get_meson_log()
        self.assertTrue(msg in mesonlog or msg2 in mesonlog)

    def test_qt5dependency_qmake_detection(self):
        '''
        Test that qt5 detection with qmake works. This can't be an ordinary
        test case because it involves setting the environment.
        '''
        # Verify that qmake is for Qt5
        if not shutil.which('qmake-qt5'):
            if not shutil.which('qmake'):
                raise unittest.SkipTest('QMake not found')
            # For some inexplicable reason qmake --version gives different
            # results when run from the command line vs invoked by Python.
            # Check for both cases in case this behavior changes in the future.
            output = subprocess.getoutput(['qmake', '--version'])
            if 'Qt version 5' not in output and 'qt5' not in output:
                raise unittest.SkipTest('Qmake found, but it is not for Qt 5.')
        # Disable pkg-config codepath and force searching with qmake/qmake-qt5
        testdir = os.path.join(self.framework_test_dir, '4 qt')
        self.init(testdir, ['-Dmethod=qmake'])
        # Confirm that the dependency was found with qmake
        msg = 'Qt5 native `qmake-qt5` dependency (modules: Core) found: YES\n'
        msg2 = 'Qt5 native `qmake` dependency (modules: Core) found: YES\n'
        mesonlog = self.get_meson_log()
        self.assertTrue(msg in mesonlog or msg2 in mesonlog)

    def _test_soname_impl(self, libpath, install):
        testdir = os.path.join(self.unit_test_dir, '1 soname')
        self.init(testdir)
        self.build()
        if install:
            self.install()

        # File without aliases set.
        nover = os.path.join(libpath, 'libnover.so')
        self.assertTrue(os.path.exists(nover))
        self.assertFalse(os.path.islink(nover))
        self.assertEqual(get_soname(nover), 'libnover.so')
        self.assertEqual(len(glob(nover[:-3] + '*')), 1)

        # File with version set
        verset = os.path.join(libpath, 'libverset.so')
        self.assertTrue(os.path.exists(verset + '.4.5.6'))
        self.assertEqual(os.readlink(verset), 'libverset.so.4')
        self.assertEqual(get_soname(verset), 'libverset.so.4')
        self.assertEqual(len(glob(verset[:-3] + '*')), 3)

        # File with soversion set
        soverset = os.path.join(libpath, 'libsoverset.so')
        self.assertTrue(os.path.exists(soverset + '.1.2.3'))
        self.assertEqual(os.readlink(soverset), 'libsoverset.so.1.2.3')
        self.assertEqual(get_soname(soverset), 'libsoverset.so.1.2.3')
        self.assertEqual(len(glob(soverset[:-3] + '*')), 2)

        # File with version and soversion set to same values
        settosame = os.path.join(libpath, 'libsettosame.so')
        self.assertTrue(os.path.exists(settosame + '.7.8.9'))
        self.assertEqual(os.readlink(settosame), 'libsettosame.so.7.8.9')
        self.assertEqual(get_soname(settosame), 'libsettosame.so.7.8.9')
        self.assertEqual(len(glob(settosame[:-3] + '*')), 2)

        # File with version and soversion set to different values
        bothset = os.path.join(libpath, 'libbothset.so')
        self.assertTrue(os.path.exists(bothset + '.1.2.3'))
        self.assertEqual(os.readlink(bothset), 'libbothset.so.1.2.3')
        self.assertEqual(os.readlink(bothset + '.1.2.3'), 'libbothset.so.4.5.6')
        self.assertEqual(get_soname(bothset), 'libbothset.so.1.2.3')
        self.assertEqual(len(glob(bothset[:-3] + '*')), 3)

    def test_soname(self):
        self._test_soname_impl(self.builddir, False)

    def test_installed_soname(self):
        self._test_soname_impl(self.installdir + self.libdir, True)

    def test_compiler_check_flags_order(self):
        '''
        Test that compiler check flags override all other flags. This can't be
        an ordinary test case because it needs the environment to be set.
        '''
        Oflag = '-O3'
        os.environ['CFLAGS'] = os.environ['CXXFLAGS'] = Oflag
        testdir = os.path.join(self.common_test_dir, '43 has function')
        self.init(testdir)
        cmds = self.get_meson_log_compiler_checks()
        for cmd in cmds:
            if cmd[0] == 'ccache':
                cmd = cmd[1:]
            # Verify that -I flags from the `args` kwarg are first
            # This is set in the '43 has function' test case
            self.assertEqual(cmd[1], '-I/tmp')
            # Verify that -O3 set via the environment is overriden by -O0
            Oargs = [arg for arg in cmd if arg.startswith('-O')]
            self.assertEqual(Oargs, [Oflag, '-O0'])

    def _test_stds_impl(self, testdir, compiler, p):
        lang_std = p + '_std'
        # Check that all the listed -std=xxx options for this compiler work
        # just fine when used
        for v in compiler.get_options()[lang_std].choices:
            std_opt = '{}={}'.format(lang_std, v)
            self.init(testdir, ['-D' + std_opt])
            cmd = self.get_compdb()[0]['command']
            if v != 'none':
                cmd_std = " -std={} ".format(v)
                self.assertIn(cmd_std, cmd)
            try:
                self.build()
            except:
                print('{} was {!r}'.format(lang_std, v))
                raise
            self.wipe()
        # Check that an invalid std option in CFLAGS/CPPFLAGS fails
        # Needed because by default ICC ignores invalid options
        cmd_std = '-std=FAIL'
        env_flags = p.upper() + 'FLAGS'
        os.environ[env_flags] = cmd_std
        self.init(testdir)
        cmd = self.get_compdb()[0]['command']
        qcmd_std = " {} ".format(cmd_std)
        self.assertIn(qcmd_std, cmd)
        with self.assertRaises(subprocess.CalledProcessError,
                               msg='{} should have failed'.format(qcmd_std)):
            self.build()

    def test_compiler_c_stds(self):
        '''
        Test that C stds specified for this compiler can all be used. Can't be
        an ordinary test because it requires passing options to meson.
        '''
        testdir = os.path.join(self.common_test_dir, '1 trivial')
        env = Environment(testdir, self.builddir, self.meson_command,
                          get_fake_options(self.prefix), [])
        cc = env.detect_c_compiler(False)
        self._test_stds_impl(testdir, cc, 'c')

    def test_compiler_cpp_stds(self):
        '''
        Test that C++ stds specified for this compiler can all be used. Can't
        be an ordinary test because it requires passing options to meson.
        '''
        testdir = os.path.join(self.common_test_dir, '2 cpp')
        env = Environment(testdir, self.builddir, self.meson_command,
                          get_fake_options(self.prefix), [])
        cpp = env.detect_cpp_compiler(False)
        self._test_stds_impl(testdir, cpp, 'cpp')

    def test_unity_subproj(self):
        testdir = os.path.join(self.common_test_dir, '49 subproject')
        self.init(testdir, extra_args='--unity=subprojects')
        self.assertTrue(os.path.exists(os.path.join(self.builddir, 'subprojects/sublib/simpletest@exe/simpletest-unity.c')))
        self.assertTrue(os.path.exists(os.path.join(self.builddir, 'subprojects/sublib/sublib@sha/sublib-unity.c')))
        self.assertFalse(os.path.exists(os.path.join(self.builddir, 'user@exe/user-unity.c')))
        self.build()

    def test_installed_modes(self):
        '''
        Test that files installed by these tests have the correct permissions.
        Can't be an ordinary test because our installed_files.txt is very basic.
        '''
        # Test file modes
        testdir = os.path.join(self.common_test_dir, '12 data')
        self.init(testdir)
        self.install()

        f = os.path.join(self.installdir, 'etc', 'etcfile.dat')
        found_mode = stat.filemode(os.stat(f).st_mode)
        want_mode = 'rw------T'
        self.assertEqual(want_mode, found_mode[1:])

        f = os.path.join(self.installdir, 'usr', 'bin', 'runscript.sh')
        statf = os.stat(f)
        found_mode = stat.filemode(statf.st_mode)
        want_mode = 'rwxr-sr-x'
        self.assertEqual(want_mode, found_mode[1:])
        if os.getuid() == 0:
            # The chown failed nonfatally if we're not root
            self.assertEqual(0, statf.st_uid)
            self.assertEqual(0, statf.st_gid)

        f = os.path.join(self.installdir, 'usr', 'share', 'progname',
                         'fileobject_datafile.dat')
        orig = os.path.join(testdir, 'fileobject_datafile.dat')
        statf = os.stat(f)
        statorig = os.stat(orig)
        found_mode = stat.filemode(statf.st_mode)
        orig_mode = stat.filemode(statorig.st_mode)
        self.assertEqual(orig_mode[1:], found_mode[1:])
        self.assertEqual(os.getuid(), statf.st_uid)
        if os.getuid() == 0:
            # The chown failed nonfatally if we're not root
            self.assertEqual(0, statf.st_gid)

        self.wipe()
        # Test directory modes
        testdir = os.path.join(self.common_test_dir, '66 install subdir')
        self.init(testdir)
        self.install()

        f = os.path.join(self.installdir, 'usr', 'share', 'sub1')
        statf = os.stat(f)
        found_mode = stat.filemode(statf.st_mode)
        want_mode = 'rwxr-x--t'
        self.assertEqual(want_mode, found_mode[1:])
        if os.getuid() == 0:
            # The chown failed nonfatally if we're not root
            self.assertEqual(0, statf.st_uid)

    def test_cpp_std_override(self):
        testdir = os.path.join(self.unit_test_dir, '6 std override')
        self.init(testdir)
        compdb = self.get_compdb()
        for i in compdb:
            if 'prog03' in i['file']:
                c03_comp = i['command']
            if 'prog11' in i['file']:
                c11_comp = i['command']
            if 'progp' in i['file']:
                plain_comp = i['command']
        self.assertNotEqual(len(plain_comp), 0)
        self.assertIn('-std=c++03', c03_comp)
        self.assertNotIn('-std=c++11', c03_comp)
        self.assertIn('-std=c++11', c11_comp)
        self.assertNotIn('-std=c++03', c11_comp)
        self.assertNotIn('-std=c++03', plain_comp)
        self.assertNotIn('-std=c++11', plain_comp)
        # Now werror
        self.assertIn('-Werror', plain_comp)
        self.assertNotIn('-Werror', c03_comp)

    def test_run_installed(self):
        testdir = os.path.join(self.unit_test_dir, '7 run installed')
        self.init(testdir)
        self.build()
        self.install()
        installed_exe = os.path.join(self.installdir, 'usr/bin/prog')
        installed_libdir = os.path.join(self.installdir, 'usr/foo')
        installed_lib = os.path.join(installed_libdir, 'libfoo.so')
        self.assertTrue(os.path.isfile(installed_exe))
        self.assertTrue(os.path.isdir(installed_libdir))
        self.assertTrue(os.path.isfile(installed_lib))
        # Must fail when run without LD_LIBRARY_PATH to ensure that
        # rpath has been properly stripped rather than pointing to the builddir.
        self.assertNotEqual(subprocess.call(installed_exe, stderr=subprocess.DEVNULL), 0)
        # When LD_LIBRARY_PATH is set it should start working.
        # For some reason setting LD_LIBRARY_PATH in os.environ fails
        # when all tests are run (but works when only this test is run),
        # but doing this explicitly works.
        env = os.environ.copy()
        env['LD_LIBRARY_PATH'] = installed_libdir
        self.assertEqual(subprocess.call(installed_exe, env=env), 0)

    def test_order_of_l_arguments(self):
        testdir = os.path.join(self.unit_test_dir, '9 -L -l order')
        os.environ['PKG_CONFIG_PATH'] = testdir
        self.init(testdir)
        # NOTE: .pc file has -Lfoo -lfoo -Lbar -lbar but pkg-config reorders
        # the flags before returning them to -Lfoo -Lbar -lfoo -lbar
        # but pkgconf seems to not do that. Sigh. Support both.
        expected_order = [('-L/me/first', '-lfoo1'),
                          ('-L/me/second', '-lfoo2'),
                          ('-L/me/first', '-L/me/second'),
                          ('-lfoo1', '-lfoo2'),
                          ('-L/me/second', '-L/me/third'),
                          ('-L/me/third', '-L/me/fourth',),
                          ('-L/me/third', '-lfoo3'),
                          ('-L/me/fourth', '-lfoo4'),
                          ('-lfoo3', '-lfoo4'),
                          ]
        with open(os.path.join(self.builddir, 'build.ninja')) as ifile:
            for line in ifile:
                if expected_order[0][0] in line:
                    for first, second in expected_order:
                        self.assertLess(line.index(first), line.index(second))
                    return
        raise RuntimeError('Linker entries not found in the Ninja file.')

class LinuxArmCrossCompileTests(BasePlatformTests):
    '''
    Tests that verify cross-compilation to Linux/ARM
    '''
    def setUp(self):
        super().setUp()
        src_root = os.path.dirname(__file__)
        self.meson_command += ['--cross=' + os.path.join(src_root, 'cross', 'ubuntu-armhf.txt')]

    def test_cflags_cross_environment_pollution(self):
        '''
        Test that the CFLAGS environment variable does not pollute the cross
        environment. This can't be an ordinary test case because we need to
        inspect the compiler database.
        '''
        testdir = os.path.join(self.common_test_dir, '3 static')
        os.environ['CFLAGS'] = '-DBUILD_ENVIRONMENT_ONLY'
        self.init(testdir)
        compdb = self.get_compdb()
        self.assertNotIn('-DBUILD_ENVIRONMENT_ONLY', compdb[0]['command'])

class RewriterTests(unittest.TestCase):

    def setUp(self):
        super().setUp()
        src_root = os.path.dirname(__file__)
        self.testroot = os.path.realpath(tempfile.mkdtemp())
        self.rewrite_command = [sys.executable, os.path.join(src_root, 'mesonrewriter.py')]
        self.tmpdir = os.path.realpath(tempfile.mkdtemp())
        self.workdir = os.path.join(self.tmpdir, 'foo')
        self.test_dir = os.path.join(src_root, 'test cases/rewrite')

    def tearDown(self):
        windows_proof_rmtree(self.tmpdir)

    def read_contents(self, fname):
        with open(os.path.join(self.workdir, fname)) as f:
            return f.read()

    def check_effectively_same(self, mainfile, truth):
        mf = self.read_contents(mainfile)
        t = self.read_contents(truth)
        # Rewriting is not guaranteed to do a perfect job of
        # maintaining whitespace.
        self.assertEqual(mf.replace(' ', ''), t.replace(' ', ''))

    def prime(self, dirname):
        shutil.copytree(os.path.join(self.test_dir, dirname), self.workdir)

    def test_basic(self):
        self.prime('1 basic')
        subprocess.check_call(self.rewrite_command + ['remove',
                                                      '--target=trivialprog',
                                                      '--filename=notthere.c',
                                                      '--sourcedir', self.workdir],
                              universal_newlines=True)
        self.check_effectively_same('meson.build', 'removed.txt')
        subprocess.check_call(self.rewrite_command + ['add',
                                                      '--target=trivialprog',
                                                      '--filename=notthere.c',
                                                      '--sourcedir', self.workdir],
                              universal_newlines=True)
        self.check_effectively_same('meson.build', 'added.txt')
        subprocess.check_call(self.rewrite_command + ['remove',
                                                      '--target=trivialprog',
                                                      '--filename=notthere.c',
                                                      '--sourcedir', self.workdir],
                              universal_newlines=True)
        self.check_effectively_same('meson.build', 'removed.txt')

    def test_subdir(self):
        self.prime('2 subdirs')
        top = self.read_contents('meson.build')
        s2 = self.read_contents('sub2/meson.build')
        subprocess.check_call(self.rewrite_command + ['remove',
                                                      '--target=something',
                                                      '--filename=second.c',
                                                      '--sourcedir', self.workdir],
                              universal_newlines=True)
        self.check_effectively_same('sub1/meson.build', 'sub1/after.txt')
        self.assertEqual(top, self.read_contents('meson.build'))
        self.assertEqual(s2, self.read_contents('sub2/meson.build'))


def unset_envs():
    # For unit tests we must fully control all commend lines
    # so that there are no unexpected changes coming from the
    # environment, for example when doing a package build.
    varnames = ['CPPFLAGS', 'LDFLAGS'] + list(mesonbuild.environment.cflags_mapping.values())
    for v in varnames:
        if v in os.environ:
            del os.environ[v]

if __name__ == '__main__':
    unset_envs()
    unittest.main(buffer=True)
