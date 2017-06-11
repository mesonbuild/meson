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

from glob import glob
import itertools
import os, subprocess, shutil, sys, signal
from io import StringIO
from ast import literal_eval
from enum import Enum
import tempfile
import mesontest
from mesonbuild import environment
from mesonbuild import mesonlib
from mesonbuild import mlog
from mesonbuild import mesonmain
from mesonbuild.mesonlib import stringlistify, Popen_safe
from mesonbuild.coredata import backendlist
import argparse
import xml.etree.ElementTree as ET
import time
import multiprocessing
import concurrent.futures as conc
import re
from run_unittests import get_fake_options, run_configure_inprocess

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

class DummyFuture(conc.Future):
    '''
    Dummy Future implementation that executes the provided function when you
    ask for the result. Used on platforms where sem_open() is not available:
    MSYS2, OpenBSD, etc: https://bugs.python.org/issue3770
    '''
    def set_function(self, fn, *args, **kwargs):
        self.fn = fn
        self.fn_args = args
        self.fn_kwargs = kwargs

    def result(self, **kwargs):
        try:
            result = self.fn(*self.fn_args, **self.fn_kwargs)
        except BaseException as e:
            self.set_exception(e)
        else:
            self.set_result(result)
        return super().result(**kwargs)


class DummyExecutor(conc.Executor):
    '''
    Dummy single-thread 'concurrent' executor for use on platforms where
    sem_open is not available: https://bugs.python.org/issue3770
    '''

    def __init__(self):
        from threading import Lock
        self._shutdown = False
        self._shutdownLock = Lock()

    def submit(self, fn, *args, **kwargs):
        with self._shutdownLock:
            if self._shutdown:
                raise RuntimeError('Cannot schedule new futures after shutdown')
            f = DummyFuture()
            f.set_function(fn, *args, **kwargs)
            return f

    def shutdown(self, wait=True):
        with self._shutdownLock:
            self._shutdown = True


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
do_debug = not {'MESON_PRINT_TEST_OUTPUT', 'TRAVIS', 'APPVEYOR'}.isdisjoint(os.environ)
no_meson_log_msg = 'No meson-log.txt found.'

meson_command = os.path.join(os.getcwd(), 'meson')
if not os.path.exists(meson_command):
    meson_command += '.py'
    if not os.path.exists(meson_command):
        raise RuntimeError('Could not find main Meson script to run.')

class StopException(Exception):
    def __init__(self):
        super().__init__('Stopped by user')

stop = False
def stop_handler(signal, frame):
    global stop
    stop = True
signal.signal(signal.SIGINT, stop_handler)
signal.signal(signal.SIGTERM, stop_handler)

# Needed when running cross tests because we don't generate prebuilt files
compiler = None

def setup_commands(optbackend):
    global do_debug, backend, backend_flags
    global compile_commands, clean_commands, test_commands, install_commands, uninstall_commands
    backend = optbackend
    msbuild_exe = shutil.which('msbuild')
    # Auto-detect backend if unspecified
    if backend is None:
        if msbuild_exe is not None:
            backend = 'vs' # Meson will auto-detect VS version to use
        elif mesonlib.is_osx():
            backend = 'xcode'
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

def platform_fix_name(fname):
    if '?lib' in fname:
        if mesonlib.is_cygwin():
            fname = re.sub(r'\?lib(.*)\.dll$', r'cyg\1.dll', fname)
        else:
            fname = re.sub(r'\?lib', 'lib', fname)

    if fname.endswith('?exe'):
        fname = fname[:-4]
        if mesonlib.is_windows() or mesonlib.is_cygwin():
            return fname + '.exe'

    return fname

def validate_install(srcdir, installdir, compiler):
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
                expected[platform_fix_name(line.strip())] = False
    # Check if expected files were found
    for fname in expected:
        if os.path.exists(os.path.join(installdir, fname)):
            expected[fname] = True
    for (fname, found) in expected.items():
        if not found:
            # Ignore missing PDB files if we aren't using cl
            if fname.endswith('.pdb') and compiler != 'cl':
                continue
            ret_msg += 'Expected file {0} missing.\n'.format(fname)
    # Check if there are any unexpected files
    found = get_relative_files_list_from_dir(installdir)
    for fname in found:
        # Windows-specific tests check for the existence of installed PDB
        # files, but common tests do not, for obvious reasons. Ignore any
        # extra PDB files found.
        if fname not in expected and not fname.endswith('.pdb') and compiler == 'cl':
            ret_msg += 'Extra file {0} found.\n'.format(fname)
    return ret_msg

def log_text_file(logfile, testdir, stdo, stde):
    global stop, executor, futures
    logfile.write('%s\nstdout\n\n---\n' % testdir)
    logfile.write(stdo)
    logfile.write('\n\n---\n\nstderr\n\n---\n')
    logfile.write(stde)
    logfile.write('\n\n---\n\n')
    if print_debug:
        print(stdo)
        print(stde, file=sys.stderr)
    if stop:
        print("Aborting..")
        for f in futures:
            f[2].cancel()
        executor.shutdown()
        raise StopException()

def run_test_inprocess(testdir):
    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()
    old_stderr = sys.stderr
    sys.stderr = mystderr = StringIO()
    old_cwd = os.getcwd()
    os.chdir(testdir)
    test_log_fname = 'meson-logs/testlog.txt'
    try:
        returncode_test = mesontest.run(['--no-rebuild'])
        if os.path.exists(test_log_fname):
            test_log = open(test_log_fname, errors='ignore').read()
        else:
            test_log = ''
        returncode_benchmark = mesontest.run(['--no-rebuild', '--benchmark', '--logbase', 'benchmarklog'])
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

def run_test(skipped, testdir, extra_args, compiler, backend, flags, commands, should_fail):
    if skipped:
        return None
    with AutoDeletedDir(tempfile.mkdtemp(prefix='b ', dir='.')) as build_dir:
        with AutoDeletedDir(tempfile.mkdtemp(prefix='i ', dir=os.getcwd())) as install_dir:
            try:
                return _run_test(testdir, build_dir, install_dir, extra_args, compiler, backend, flags, commands, should_fail)
            finally:
                mlog.shutdown() # Close the log file because otherwise Windows wets itself.

def _run_test(testdir, test_build_dir, install_dir, extra_args, compiler, backend, flags, commands, should_fail):
    compile_commands, clean_commands, install_commands, uninstall_commands = commands
    test_args = parse_test_args(testdir)
    gen_start = time.time()
    # Configure in-process
    gen_command = [meson_command, '--prefix', '/usr', '--libdir', 'lib', testdir, test_build_dir]\
        + flags + test_args + extra_args
    (returncode, stdo, stde) = run_configure_inprocess(gen_command)
    try:
        logfile = os.path.join(test_build_dir, 'meson-logs/meson-log.txt')
        with open(logfile, errors='ignore') as f:
            mesonlog = f.read()
    except Exception:
        mesonlog = no_meson_log_msg
    gen_time = time.time() - gen_start
    if should_fail == 'meson':
        if returncode != 0:
            return TestResult('', BuildStep.configure, stdo, stde, mesonlog, gen_time)
        return TestResult('Test that should have failed succeeded', BuildStep.configure, stdo, stde, mesonlog, gen_time)
    if returncode != 0:
        return TestResult('Generating the build system failed.', BuildStep.configure, stdo, stde, mesonlog, gen_time)
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
    return TestResult(validate_install(testdir, install_dir, compiler), BuildStep.validate, stdo, stde, mesonlog, gen_time, build_time, test_time)

def gather_tests(testdir):
    tests = [t.replace('\\', '/').split('/', 2)[2] for t in glob(testdir + '/*')]
    testlist = [(int(t.split()[0]), t) for t in tests]
    testlist.sort()
    tests = [os.path.join(testdir, t[1]) for t in testlist]
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
        env = environment.Environment(None, build_dir, None, get_fake_options('/'), [])
        objc_comp = env.detect_objc_compiler(False)
        if not objc_comp:
            return False
        try:
            objc_comp.sanity_check(env.get_scratch_dir(), env)
        except:
            return False
        objcpp_comp = env.detect_objc_compiler(False)
        if not objcpp_comp:
            return False
        try:
            objcpp_comp.sanity_check(env.get_scratch_dir(), env)
        except:
            return False
    return True

def have_java():
    if shutil.which('javac') and shutil.which('java'):
        return True
    return False

def detect_tests_to_run():
    # Name, subdirectory, skip condition.
    all_tests = [
        ('common', 'common', False),
        ('failing-meson', 'failing', False),
        ('failing-build', 'failing build', False),
        ('failing-tests', 'failing tests', False),
        ('prebuilt', 'prebuilt', False),

        ('platform-osx', 'osx', not mesonlib.is_osx()),
        ('platform-windows', 'windows', not mesonlib.is_windows() and not mesonlib.is_cygwin()),
        ('platform-linux', 'linuxlike', mesonlib.is_osx() or mesonlib.is_windows()),

        ('java', 'java', backend is not Backend.ninja or mesonlib.is_osx() or not have_java()),
        ('C#', 'csharp', backend is not Backend.ninja or not shutil.which('mcs')),
        ('vala', 'vala', backend is not Backend.ninja or not shutil.which('valac')),
        ('rust', 'rust', backend is not Backend.ninja or not shutil.which('rustc')),
        ('d', 'd', backend is not Backend.ninja or not have_d_compiler()),
        ('objective c', 'objc', backend not in (Backend.ninja, Backend.xcode) or mesonlib.is_windows() or not have_objc_compiler()),
        ('fortran', 'fortran', backend is not Backend.ninja or not shutil.which('gfortran')),
        ('swift', 'swift', backend not in (Backend.ninja, Backend.xcode) or not shutil.which('swiftc')),
        ('python3', 'python3', backend is not Backend.ninja),
    ]
    gathered_tests = [(name, gather_tests('test cases/' + subdir), skip) for name, subdir, skip in all_tests]
    if mesonlib.is_windows():
        # TODO: Set BOOST_ROOT in .appveyor.yml
        gathered_tests += [('framework', ['test cases/frameworks/1 boost'], 'BOOST_ROOT' not in os.environ)]
    elif mesonlib.is_osx() or mesonlib.is_cygwin():
        gathered_tests += [('framework', gather_tests('test cases/frameworks'), True)]
    else:
        gathered_tests += [('framework', gather_tests('test cases/frameworks'), False)]
    return gathered_tests

def run_tests(all_tests, log_name_base, extra_args):
    global stop, executor, futures
    txtname = log_name_base + '.txt'
    xmlname = log_name_base + '.xml'
    logfile = open(txtname, 'w', encoding="utf_8")
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
    try:
        executor = conc.ProcessPoolExecutor(max_workers=num_workers)
    except ImportError:
        print('Platform doesn\'t ProcessPoolExecutor, falling back to single-threaded testing\n')
        executor = DummyExecutor()

    for name, test_cases, skipped in all_tests:
        current_suite = ET.SubElement(junit_root, 'testsuite', {'name': name, 'tests': str(len(test_cases))})
        if skipped:
            print('\nNot running %s tests.\n' % name)
        else:
            print('\nRunning %s tests.\n' % name)
        futures = []
        for t in test_cases:
            # Jenkins screws us over by automatically sorting test cases by name
            # and getting it wrong by not doing logical number sorting.
            (testnum, testbase) = os.path.split(t)[-1].split(' ', 1)
            testname = '%.3d %s' % (int(testnum), testbase)
            should_fail = False
            if name.startswith('failing'):
                should_fail = name.split('failing-')[1]
            result = executor.submit(run_test, skipped, t, extra_args, compiler, backend, backend_flags, commands, should_fail)
            futures.append((testname, t, result))
        for (testname, t, result) in futures:
            sys.stdout.flush()
            result = result.result()
            if result is None or 'MESON_SKIP_TEST' in result.stdo:
                print('Skipping:', t)
                current_test = ET.SubElement(current_suite, 'testcase', {'name': testname,
                                                                         'classname': name})
                ET.SubElement(current_test, 'skipped', {})
                skipped_tests += 1
            else:
                without_install = "" if len(install_commands) > 0 else " (without install)"
                if result.msg != '':
                    print('Failed test{} during {}: {!r}'.format(without_install, result.step.name, t))
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
                    print('Succeeded test%s: %s' % (without_install, t))
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
        if b'\t' in line:
            print("File %s contains a literal tab on line %d. Only spaces are permitted." % (fname, linenum))
            sys.exit(1)
        if b'\r' in line:
            print("File %s contains DOS line ending on line %d. Only unix-style line endings are permitted." % (fname, linenum))
            sys.exit(1)
        linenum += 1

def check_format():
    for (root, _, files) in os.walk('.'):
        for file in files:
            if file.endswith('.py') or file.endswith('.build') or file == 'meson_options.txt':
                fullname = os.path.join(root, file)
                check_file(fullname)

def pbcompile(compiler, source, objectfile):
    if compiler == 'cl':
        cmd = [compiler, '/nologo', '/Fo' + objectfile, '/c', source]
    else:
        cmd = [compiler, '-c', source, '-o', objectfile]
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def generate_pb_object(compiler, object_suffix):
    source = 'test cases/prebuilt/1 object/source.c'
    objectfile = 'test cases/prebuilt/1 object/prebuilt.' + object_suffix
    pbcompile(compiler, source, objectfile)
    return objectfile

def generate_pb_static(compiler, object_suffix, static_suffix):
    source = 'test cases/prebuilt/2 static/libdir/best.c'
    objectfile = 'test cases/prebuilt/2 static/libdir/best.' + object_suffix
    stlibfile = 'test cases/prebuilt/2 static/libdir/libbest.' + static_suffix
    pbcompile(compiler, source, objectfile)
    if compiler == 'cl':
        linker = ['lib', '/NOLOGO', '/OUT:' + stlibfile, objectfile]
    else:
        linker = ['ar', 'csr', stlibfile, objectfile]
    subprocess.check_call(linker)
    os.unlink(objectfile)
    return stlibfile

def generate_prebuilt():
    global compiler
    static_suffix = 'a'
    if shutil.which('cl'):
        compiler = 'cl'
        static_suffix = 'lib'
    elif shutil.which('cc'):
        compiler = 'cc'
    elif shutil.which('gcc'):
        compiler = 'gcc'
    else:
        raise RuntimeError("Could not find C compiler.")
    if mesonlib.is_windows():
        object_suffix = 'obj'
    else:
        object_suffix = 'o'
    objectfile = generate_pb_object(compiler, object_suffix)
    stlibfile = generate_pb_static(compiler, object_suffix, static_suffix)
    return objectfile, stlibfile

def check_meson_commands_work():
    global backend, meson_command, compile_commands, test_commands, install_commands
    testdir = 'test cases/common/1 trivial'
    with AutoDeletedDir(tempfile.mkdtemp(prefix='b ', dir='.')) as build_dir:
        print('Checking that configuring works...')
        gen_cmd = [sys.executable, meson_command, testdir, build_dir] + backend_flags
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

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run the test suite of Meson.")
    parser.add_argument('extra_args', nargs='*',
                        help='arguments that are passed directly to Meson (remember to have -- before these).')
    parser.add_argument('--backend', default=None, dest='backend',
                        choices=backendlist)
    options = parser.parse_args()
    setup_commands(options.backend)

    script_dir = os.path.split(__file__)[0]
    if script_dir != '':
        os.chdir(script_dir)
    check_format()
    check_meson_commands_work()
    pbfiles = generate_prebuilt()
    try:
        all_tests = detect_tests_to_run()
        (passing_tests, failing_tests, skipped_tests) = run_tests(all_tests, 'meson-test-run', options.extra_args)
    except StopException:
        pass
    for f in pbfiles:
        os.unlink(f)
    print('\nTotal passed tests:', passing_tests)
    print('Total failed tests:', failing_tests)
    print('Total skipped tests:', skipped_tests)
    if failing_tests > 0:
        print('\nMesonlogs of failing tests\n')
        for l in failing_logs:
            print(l, '\n')
    for name, dirs, skip in all_tests:
        dirs = (os.path.basename(x) for x in dirs)
        for k, g in itertools.groupby(dirs, key=lambda x: x.split()[0]):
            tests = list(g)
            if len(tests) != 1:
                print('WARNING: The %s suite contains duplicate "%s" tests: "%s"' % (name, k, '", "'.join(tests)))
    sys.exit(failing_tests)
