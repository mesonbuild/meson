#!/usr/bin/env python3

# Copyright 2012-2016 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import itertools
import os
import subprocess
import shutil
import sys
import signal
from io import StringIO
from ast import literal_eval
from enum import Enum
import tempfile
from pathlib import Path, PurePath
from mesonbuild import build
from mesonbuild import environment
from mesonbuild import mesonlib
from mesonbuild import mlog
from mesonbuild import mtest
from mesonbuild.mesonlib import stringlistify, Popen_safe
from mesonbuild.coredata import backendlist
import argparse
import xml.etree.ElementTree as ET
import time
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
import re
from run_tests import get_fake_options, run_configure, get_meson_script
from run_tests import get_backend_commands, get_backend_args_for_dir, Backend
from run_tests import ensure_backend_detects_changes


class BuildStep(Enum):
    configure = 1
    build = 2
    test = 3
    install = 4
    clean = 5
    validate = 6


class TestResult:
    def __init__(self, msg, step, stdo, stde, mlog, conftime=0, buildtime=0, testtime=0):
        self.msg = msg
        self.step = step
        self.stdo = stdo
        self.stde = stde
        self.mlog = mlog
        self.conftime = conftime
        self.buildtime = buildtime
        self.testtime = testtime


class AutoDeletedDir:
    def __init__(self, d):
        self.dir = d

    def __enter__(self):
        os.makedirs(self.dir, exist_ok=True)
        return self.dir

    def __exit__(self, _type, value, traceback):
        # We don't use tempfile.TemporaryDirectory, but wrap the
        # deletion in the AutoDeletedDir class because
        # it fails on Windows due antivirus programs
        # holding files open.
        mesonlib.windows_proof_rmtree(self.dir)

failing_logs = []
print_debug = 'MESON_PRINT_TEST_OUTPUT' in os.environ
under_ci = not {'TRAVIS', 'APPVEYOR'}.isdisjoint(os.environ)
do_debug = under_ci or print_debug
no_meson_log_msg = 'No meson-log.txt found.'

system_compiler = None

class StopException(Exception):
    def __init__(self):
        super().__init__('Stopped by user')

stop = False
def stop_handler(signal, frame):
    global stop
    stop = True
signal.signal(signal.SIGINT, stop_handler)
signal.signal(signal.SIGTERM, stop_handler)

def setup_commands(optbackend):
    global do_debug, backend, backend_flags
    global compile_commands, clean_commands, test_commands, install_commands, uninstall_commands
    backend = optbackend
    msbuild_exe = shutil.which('msbuild')
    # Auto-detect backend if unspecified
    if backend is None:
        if msbuild_exe is not None:
            backend = 'vs' # Meson will auto-detect VS version to use
        else:
            backend = 'ninja'
    # Set backend arguments for Meson
    if backend.startswith('vs'):
        backend_flags = ['--backend=' + backend]
        backend = Backend.vs
    elif backend == 'xcode':
        backend_flags = ['--backend=xcode']
        backend = Backend.xcode
    elif backend == 'ninja':
        backend_flags = ['--backend=ninja']
        backend = Backend.ninja
    else:
        raise RuntimeError('Unknown backend: {!r}'.format(backend))
    compile_commands, clean_commands, test_commands, install_commands, \
        uninstall_commands = get_backend_commands(backend, do_debug)

def get_relative_files_list_from_dir(fromdir):
    paths = []
    for (root, _, files) in os.walk(fromdir):
        reldir = os.path.relpath(root, start=fromdir)
        for f in files:
            path = os.path.join(reldir, f).replace('\\', '/')
            if path.startswith('./'):
                path = path[2:]
            paths.append(path)
    return paths

def platform_fix_name(fname, compiler, env):
    if '?lib' in fname:
        if mesonlib.for_cygwin(env.is_cross_build(), env):
            fname = re.sub(r'lib/\?lib(.*)\.so$', r'bin/cyg\1.dll', fname)
            fname = re.sub(r'\?lib(.*)\.dll$', r'cyg\1.dll', fname)
        else:
            fname = re.sub(r'\?lib', 'lib', fname)

    if fname.endswith('?exe'):
        fname = fname[:-4]
        if mesonlib.for_windows(env.is_cross_build(), env) or mesonlib.for_cygwin(env.is_cross_build(), env):
            return fname + '.exe'

    if fname.startswith('?msvc:'):
        fname = fname[6:]
        if compiler != 'cl':
            return None

    if fname.startswith('?gcc:'):
        fname = fname[5:]
        if compiler == 'cl':
            return None

    if fname.startswith('?cygwin:'):
        fname = fname[8:]
        if compiler == 'cl' or not mesonlib.for_cygwin(env.is_cross_build(), env):
            return None

    return fname

def validate_install(srcdir, installdir, compiler, env):
    # List of installed files
    info_file = os.path.join(srcdir, 'installed_files.txt')
    # If this exists, the test does not install any other files
    noinst_file = 'usr/no-installed-files'
    expected = {}
    ret_msg = ''
    # Generate list of expected files
    if os.path.exists(os.path.join(installdir, noinst_file)):
        expected[noinst_file] = False
    elif os.path.exists(info_file):
        with open(info_file) as f:
            for line in f:
                line = platform_fix_name(line.strip(), compiler, env)
                if line:
                    expected[line] = False
    # Check if expected files were found
    for fname in expected:
        file_path = os.path.join(installdir, fname)
        if os.path.exists(file_path) or os.path.islink(file_path):
            expected[fname] = True
    for (fname, found) in expected.items():
        if not found:
            ret_msg += 'Expected file {0} missing.\n'.format(fname)
    # Check if there are any unexpected files
    found = get_relative_files_list_from_dir(installdir)
    for fname in found:
        if fname not in expected:
            ret_msg += 'Extra file {0} found.\n'.format(fname)
    return ret_msg

def log_text_file(logfile, testdir, stdo, stde):
    global stop, executor, futures
    logfile.write('%s\nstdout\n\n---\n' % testdir.as_posix())
    logfile.write(stdo)
    logfile.write('\n\n---\n\nstderr\n\n---\n')
    logfile.write(stde)
    logfile.write('\n\n---\n\n')
    if print_debug:
        try:
            print(stdo)
        except UnicodeError:
            sanitized_out = stdo.encode('ascii', errors='replace').decode()
            print(sanitized_out)
        try:
            print(stde, file=sys.stderr)
        except UnicodeError:
            sanitized_err = stde.encode('ascii', errors='replace').decode()
            print(sanitized_err, file=sys.stderr)
    if stop:
        print("Aborting..")
        for f in futures:
            f[2].cancel()
        executor.shutdown()
        raise StopException()


def bold(text):
    return mlog.bold(text).get_text(mlog.colorize_console)


def green(text):
    return mlog.green(text).get_text(mlog.colorize_console)


def red(text):
    return mlog.red(text).get_text(mlog.colorize_console)


def yellow(text):
    return mlog.yellow(text).get_text(mlog.colorize_console)


def run_test_inprocess(testdir):
    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()
    old_stderr = sys.stderr
    sys.stderr = mystderr = StringIO()
    old_cwd = os.getcwd()
    os.chdir(testdir)
    test_log_fname = Path('meson-logs', 'testlog.txt')
    try:
        returncode_test = mtest.run(['--no-rebuild'])
        if test_log_fname.exists():
            test_log = test_log_fname.open(errors='ignore').read()
        else:
            test_log = ''
        returncode_benchmark = mtest.run(['--no-rebuild', '--benchmark', '--logbase', 'benchmarklog'])
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        os.chdir(old_cwd)
    return max(returncode_test, returncode_benchmark), mystdout.getvalue(), mystderr.getvalue(), test_log

def parse_test_args(testdir):
    args = []
    try:
        with open(os.path.join(testdir, 'test_args.txt'), 'r') as f:
            content = f.read()
            try:
                args = literal_eval(content)
            except Exception:
                raise Exception('Malformed test_args file.')
            args = stringlistify(args)
    except FileNotFoundError:
        pass
    return args

# Build directory name must be the same so CCache works over
# consecutive invocations.
def create_deterministic_builddir(src_dir):
    import hashlib
    rel_dirname = 'b ' + hashlib.sha256(src_dir.encode(errors='ignore')).hexdigest()[0:10]
    os.mkdir(rel_dirname)
    abs_pathname = os.path.join(os.getcwd(), rel_dirname)
    return abs_pathname

def run_test(skipped, testdir, extra_args, compiler, backend, flags, commands, should_fail):
    if skipped:
        return None
    with AutoDeletedDir(create_deterministic_builddir(testdir)) as build_dir:
        with AutoDeletedDir(tempfile.mkdtemp(prefix='i ', dir=os.getcwd())) as install_dir:
            try:
                return _run_test(testdir, build_dir, install_dir, extra_args, compiler, backend, flags, commands, should_fail)
            finally:
                mlog.shutdown() # Close the log file because otherwise Windows wets itself.

def pass_prefix_to_test(dirname):
    if '39 prefix absolute' in dirname:
        return False
    return True

def pass_libdir_to_test(dirname):
    if '8 install' in dirname:
        return False
    if '38 libdir must be inside prefix' in dirname:
        return False
    if '196 install_mode' in dirname:
        return False
    return True

def _run_test(testdir, test_build_dir, install_dir, extra_args, compiler, backend, flags, commands, should_fail):
    compile_commands, clean_commands, install_commands, uninstall_commands = commands
    test_args = parse_test_args(testdir)
    gen_start = time.time()
    # Configure in-process
    if pass_prefix_to_test(testdir):
        gen_args = ['--prefix', '/usr']
    else:
        gen_args = []
    if pass_libdir_to_test(testdir):
        gen_args += ['--libdir', 'lib']
    gen_args += [testdir, test_build_dir] + flags + test_args + extra_args
    (returncode, stdo, stde) = run_configure(gen_args)
    try:
        logfile = Path(test_build_dir, 'meson-logs', 'meson-log.txt')
        mesonlog = logfile.open(errors='ignore', encoding='utf-8').read()
    except Exception:
        mesonlog = no_meson_log_msg
    gen_time = time.time() - gen_start
    if should_fail == 'meson':
        if returncode == 1:
            return TestResult('', BuildStep.configure, stdo, stde, mesonlog, gen_time)
        elif returncode != 0:
            return TestResult('Test exited with unexpected status {}'.format(returncode), BuildStep.configure, stdo, stde, mesonlog, gen_time)
        else:
            return TestResult('Test that should have failed succeeded', BuildStep.configure, stdo, stde, mesonlog, gen_time)
    if returncode != 0:
        return TestResult('Generating the build system failed.', BuildStep.configure, stdo, stde, mesonlog, gen_time)
    builddata = build.load(test_build_dir)
    # Touch the meson.build file to force a regenerate so we can test that
    # regeneration works before a build is run.
    ensure_backend_detects_changes(backend)
    os.utime(os.path.join(testdir, 'meson.build'))
    # Build with subprocess
    dir_args = get_backend_args_for_dir(backend, test_build_dir)
    build_start = time.time()
    pc, o, e = Popen_safe(compile_commands + dir_args, cwd=test_build_dir)
    build_time = time.time() - build_start
    stdo += o
    stde += e
    if should_fail == 'build':
        if pc.returncode != 0:
            return TestResult('', BuildStep.build, stdo, stde, mesonlog, gen_time)
        return TestResult('Test that should have failed to build succeeded', BuildStep.build, stdo, stde, mesonlog, gen_time)
    if pc.returncode != 0:
        return TestResult('Compiling source code failed.', BuildStep.build, stdo, stde, mesonlog, gen_time, build_time)
    # Touch the meson.build file to force a regenerate so we can test that
    # regeneration works after a build is complete.
    ensure_backend_detects_changes(backend)
    os.utime(os.path.join(testdir, 'meson.build'))
    test_start = time.time()
    # Test in-process
    (returncode, tstdo, tstde, test_log) = run_test_inprocess(test_build_dir)
    test_time = time.time() - test_start
    stdo += tstdo
    stde += tstde
    mesonlog += test_log
    if should_fail == 'test':
        if returncode != 0:
            return TestResult('', BuildStep.test, stdo, stde, mesonlog, gen_time)
        return TestResult('Test that should have failed to run unit tests succeeded', BuildStep.test, stdo, stde, mesonlog, gen_time)
    if returncode != 0:
        return TestResult('Running unit tests failed.', BuildStep.test, stdo, stde, mesonlog, gen_time, build_time, test_time)
    # Do installation, if the backend supports it
    if install_commands:
        env = os.environ.copy()
        env['DESTDIR'] = install_dir
        # Install with subprocess
        pi, o, e = Popen_safe(install_commands, cwd=test_build_dir, env=env)
        stdo += o
        stde += e
        if pi.returncode != 0:
            return TestResult('Running install failed.', BuildStep.install, stdo, stde, mesonlog, gen_time, build_time, test_time)
    # Clean with subprocess
    env = os.environ.copy()
    pi, o, e = Popen_safe(clean_commands + dir_args, cwd=test_build_dir, env=env)
    stdo += o
    stde += e
    if pi.returncode != 0:
        return TestResult('Running clean failed.', BuildStep.clean, stdo, stde, mesonlog, gen_time, build_time, test_time)
    if not install_commands:
        return TestResult('', BuildStep.install, '', '', mesonlog, gen_time, build_time, test_time)
    return TestResult(validate_install(testdir, install_dir, compiler, builddata.environment),
                      BuildStep.validate, stdo, stde, mesonlog, gen_time, build_time, test_time)

def gather_tests(testdir: Path):
    tests = [t.name for t in testdir.glob('*')]
    testlist = [(int(t.split()[0]), t) for t in tests]
    testlist.sort()
    tests = [testdir / t[1] for t in testlist]
    return tests

def have_d_compiler():
    if shutil.which("ldc2"):
        return True
    elif shutil.which("ldc"):
        return True
    elif shutil.which("gdc"):
        return True
    elif shutil.which("dmd"):
        return True
    return False

def have_objc_compiler():
    with AutoDeletedDir(tempfile.mkdtemp(prefix='b ', dir='.')) as build_dir:
        env = environment.Environment(None, build_dir, get_fake_options('/'))
        try:
            objc_comp = env.detect_objc_compiler(False)
        except mesonlib.MesonException:
            return False
        if not objc_comp:
            return False
        try:
            objc_comp.sanity_check(env.get_scratch_dir(), env)
        except mesonlib.MesonException:
            return False
    return True

def have_objcpp_compiler():
    with AutoDeletedDir(tempfile.mkdtemp(prefix='b ', dir='.')) as build_dir:
        env = environment.Environment(None, build_dir, get_fake_options('/'))
        try:
            objcpp_comp = env.detect_objcpp_compiler(False)
        except mesonlib.MesonException:
            return False
        if not objcpp_comp:
            return False
        try:
            objcpp_comp.sanity_check(env.get_scratch_dir(), env)
        except mesonlib.MesonException:
            return False
    return True

def have_java():
    if shutil.which('javac') and shutil.which('java'):
        return True
    return False

def skippable(suite, test):
    if not under_ci:
        return True

    if not suite.endswith('frameworks'):
        return True

    # gtk-doc test may be skipped, pending upstream fixes for spaces in
    # filenames landing in the distro used for CI
    if test.endswith('10 gtk-doc'):
        return True

    # No frameworks test should be skipped on linux CI, as we expect all
    # prerequisites to be installed
    if mesonlib.is_linux():
        return False

    # Boost test should only be skipped for windows CI build matrix entries
    # which don't define BOOST_ROOT
    if test.endswith('1 boost'):
        if mesonlib.is_windows():
            return 'BOOST_ROOT' not in os.environ
        return False

    # Other framework tests are allowed to be skipped on other platforms
    return True

def skip_csharp(backend):
    if backend is not Backend.ninja:
        return True
    if not shutil.which('resgen'):
        return True
    if shutil.which('mcs'):
        return False
    if shutil.which('csc'):
        # Only support VS2017 for now. Earlier versions fail
        # under CI in mysterious ways.
        try:
            stdo = subprocess.check_output(['csc', '/version'])
        except subprocess.CalledProcessError:
            return True
        # Having incrementing version numbers would be too easy.
        # Microsoft reset the versioning back to 1.0 (from 4.x)
        # when they got the Roslyn based compiler. Thus there
        # is NO WAY to reliably do version number comparisons.
        # Only support the version that ships with VS2017.
        return not stdo.startswith(b'2.')
    return True

def detect_tests_to_run():
    # Name, subdirectory, skip condition.
    all_tests = [
        ('common', 'common', False),
        ('failing-meson', 'failing', False),
        ('failing-build', 'failing build', False),
        ('failing-test',  'failing test', False),

        ('platform-osx', 'osx', not mesonlib.is_osx()),
        ('platform-windows', 'windows', not mesonlib.is_windows() and not mesonlib.is_cygwin()),
        ('platform-linux', 'linuxlike', mesonlib.is_osx() or mesonlib.is_windows()),

        ('java', 'java', backend is not Backend.ninja or mesonlib.is_osx() or not have_java()),
        ('C#', 'csharp', skip_csharp(backend)),
        ('vala', 'vala', backend is not Backend.ninja or not shutil.which('valac')),
        ('rust', 'rust', backend is not Backend.ninja or not shutil.which('rustc')),
        ('d', 'd', backend is not Backend.ninja or not have_d_compiler()),
        ('objective c', 'objc', backend not in (Backend.ninja, Backend.xcode) or mesonlib.is_windows() or not have_objc_compiler()),
        ('objective c++', 'objcpp', backend not in (Backend.ninja, Backend.xcode) or mesonlib.is_windows() or not have_objcpp_compiler()),
        ('fortran', 'fortran', backend is not Backend.ninja or not shutil.which('gfortran')),
        ('swift', 'swift', backend not in (Backend.ninja, Backend.xcode) or not shutil.which('swiftc')),
        ('python3', 'python3', backend is not Backend.ninja),
        ('fpga', 'fpga', shutil.which('yosys') is None),
        ('frameworks', 'frameworks', False),
        ('nasm', 'nasm', False),
    ]
    gathered_tests = [(name, gather_tests(Path('test cases', subdir)), skip) for name, subdir, skip in all_tests]
    return gathered_tests

def run_tests(all_tests, log_name_base, extra_args):
    global logfile
    txtname = log_name_base + '.txt'
    with open(txtname, 'w', encoding='utf-8', errors='ignore') as lf:
        logfile = lf
        return _run_tests(all_tests, log_name_base, extra_args)

def _run_tests(all_tests, log_name_base, extra_args):
    global stop, executor, futures, system_compiler
    xmlname = log_name_base + '.xml'
    junit_root = ET.Element('testsuites')
    conf_time = 0
    build_time = 0
    test_time = 0
    passing_tests = 0
    failing_tests = 0
    skipped_tests = 0
    commands = (compile_commands, clean_commands, install_commands, uninstall_commands)

    try:
        # This fails in some CI environments for unknown reasons.
        num_workers = multiprocessing.cpu_count()
    except Exception as e:
        print('Could not determine number of CPUs due to the following reason:' + str(e))
        print('Defaulting to using only one process')
        num_workers = 1
    # Due to Ninja deficiency, almost 50% of build time
    # is spent waiting. Do something useful instead.
    #
    # Remove this once the following issue has been resolved:
    # https://github.com/mesonbuild/meson/pull/2082
    num_workers *= 2
    executor = ProcessPoolExecutor(max_workers=num_workers)

    for name, test_cases, skipped in all_tests:
        current_suite = ET.SubElement(junit_root, 'testsuite', {'name': name, 'tests': str(len(test_cases))})
        print()
        if skipped:
            print(bold('Not running %s tests.' % name))
        else:
            print(bold('Running %s tests.' % name))
        print()
        futures = []
        for t in test_cases:
            # Jenkins screws us over by automatically sorting test cases by name
            # and getting it wrong by not doing logical number sorting.
            (testnum, testbase) = t.name.split(' ', 1)
            testname = '%.3d %s' % (int(testnum), testbase)
            should_fail = False
            if name.startswith('failing'):
                should_fail = name.split('failing-')[1]
            result = executor.submit(run_test, skipped, t.as_posix(), extra_args, system_compiler, backend, backend_flags, commands, should_fail)
            futures.append((testname, t, result))
        for (testname, t, result) in futures:
            sys.stdout.flush()
            result = result.result()
            if (result is None) or (('MESON_SKIP_TEST' in result.stdo) and (skippable(name, t.as_posix()))):
                print(yellow('Skipping:'), t.as_posix())
                current_test = ET.SubElement(current_suite, 'testcase', {'name': testname,
                                                                         'classname': name})
                ET.SubElement(current_test, 'skipped', {})
                skipped_tests += 1
            else:
                without_install = "" if len(install_commands) > 0 else " (without install)"
                if result.msg != '':
                    print(red('Failed test{} during {}: {!r}'.format(without_install, result.step.name, t.as_posix())))
                    print('Reason:', result.msg)
                    failing_tests += 1
                    if result.step == BuildStep.configure and result.mlog != no_meson_log_msg:
                        # For configure failures, instead of printing stdout,
                        # print the meson log if available since it's a superset
                        # of stdout and often has very useful information.
                        failing_logs.append(result.mlog)
                    else:
                        failing_logs.append(result.stdo)
                    failing_logs.append(result.stde)
                else:
                    print('Succeeded test%s: %s' % (without_install, t.as_posix()))
                    passing_tests += 1
                conf_time += result.conftime
                build_time += result.buildtime
                test_time += result.testtime
                total_time = conf_time + build_time + test_time
                log_text_file(logfile, t, result.stdo, result.stde)
                current_test = ET.SubElement(current_suite, 'testcase', {'name': testname,
                                                                         'classname': name,
                                                                         'time': '%.3f' % total_time})
                if result.msg != '':
                    ET.SubElement(current_test, 'failure', {'message': result.msg})
                stdoel = ET.SubElement(current_test, 'system-out')
                stdoel.text = result.stdo
                stdeel = ET.SubElement(current_test, 'system-err')
                stdeel.text = result.stde
    print("\nTotal configuration time: %.2fs" % conf_time)
    print("Total build time: %.2fs" % build_time)
    print("Total test time: %.2fs" % test_time)
    ET.ElementTree(element=junit_root).write(xmlname, xml_declaration=True, encoding='UTF-8')
    return passing_tests, failing_tests, skipped_tests

def check_file(fname):
    linenum = 1
    with open(fname, 'rb') as f:
        lines = f.readlines()
    for line in lines:
        if line.startswith(b'\t'):
            print("File %s contains a literal tab on line %d. Only spaces are permitted." % (fname, linenum))
            sys.exit(1)
        if b'\r' in line:
            print("File %s contains DOS line ending on line %d. Only unix-style line endings are permitted." % (fname, linenum))
            sys.exit(1)
        linenum += 1

def check_format():
    check_suffixes = {'.c',
                      '.cpp',
                      '.cxx',
                      '.cc',
                      '.rs',
                      '.f90',
                      '.vala',
                      '.d',
                      '.s',
                      '.m',
                      '.mm',
                      '.asm',
                      '.java',
                      '.txt',
                      '.py',
                      '.swift',
                      '.build',
                      '.md',
                      }
    for (root, _, files) in os.walk('.'):
        if '.dub' in root: # external deps are here
            continue
        for fname in files:
            if os.path.splitext(fname)[1].lower() in check_suffixes:
                bn = os.path.basename(fname)
                if bn == 'sitemap.txt' or bn == 'meson-test-run.txt':
                    continue
                fullname = os.path.join(root, fname)
                check_file(fullname)

def check_meson_commands_work():
    global backend, compile_commands, test_commands, install_commands
    testdir = PurePath('test cases', 'common', '1 trivial').as_posix()
    meson_commands = mesonlib.python_command + [get_meson_script()]
    with AutoDeletedDir(tempfile.mkdtemp(prefix='b ', dir='.')) as build_dir:
        print('Checking that configuring works...')
        gen_cmd = meson_commands + [testdir, build_dir] + backend_flags
        pc, o, e = Popen_safe(gen_cmd)
        if pc.returncode != 0:
            raise RuntimeError('Failed to configure {!r}:\n{}\n{}'.format(testdir, e, o))
        print('Checking that building works...')
        dir_args = get_backend_args_for_dir(backend, build_dir)
        pc, o, e = Popen_safe(compile_commands + dir_args, cwd=build_dir)
        if pc.returncode != 0:
            raise RuntimeError('Failed to build {!r}:\n{}\n{}'.format(testdir, e, o))
        print('Checking that testing works...')
        pc, o, e = Popen_safe(test_commands, cwd=build_dir)
        if pc.returncode != 0:
            raise RuntimeError('Failed to test {!r}:\n{}\n{}'.format(testdir, e, o))
        if install_commands:
            print('Checking that installing works...')
            pc, o, e = Popen_safe(install_commands, cwd=build_dir)
            if pc.returncode != 0:
                raise RuntimeError('Failed to install {!r}:\n{}\n{}'.format(testdir, e, o))


def detect_system_compiler():
    global system_compiler
    if shutil.which('cl'):
        system_compiler = 'cl'
    elif shutil.which('cc'):
        system_compiler = 'cc'
    elif shutil.which('gcc'):
        system_compiler = 'gcc'
    else:
        raise RuntimeError("Could not find C compiler.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run the test suite of Meson.")
    parser.add_argument('extra_args', nargs='*',
                        help='arguments that are passed directly to Meson (remember to have -- before these).')
    parser.add_argument('--backend', default=None, dest='backend',
                        choices=backendlist)
    options = parser.parse_args()
    setup_commands(options.backend)

    detect_system_compiler()
    script_dir = os.path.split(__file__)[0]
    if script_dir != '':
        os.chdir(script_dir)
    check_format()
    check_meson_commands_work()
    try:
        all_tests = detect_tests_to_run()
        (passing_tests, failing_tests, skipped_tests) = run_tests(all_tests, 'meson-test-run', options.extra_args)
    except StopException:
        pass
    print('\nTotal passed tests:', green(str(passing_tests)))
    print('Total failed tests:', red(str(failing_tests)))
    print('Total skipped tests:', yellow(str(skipped_tests)))
    if failing_tests > 0:
        print('\nMesonlogs of failing tests\n')
        for l in failing_logs:
            try:
                print(l, '\n')
            except UnicodeError:
                print(l.encode('ascii', errors='replace').decode(), '\n')
    for name, dirs, skip in all_tests:
        dirs = (x.name for x in dirs)
        for k, g in itertools.groupby(dirs, key=lambda x: x.split()[0]):
            tests = list(g)
            if len(tests) != 1:
                print('WARNING: The %s suite contains duplicate "%s" tests: "%s"' % (name, k, '", "'.join(tests)))
    sys.exit(failing_tests)
