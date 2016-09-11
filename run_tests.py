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
import os, subprocess, shutil, sys, signal
from io import StringIO
from ast import literal_eval
import sys, tempfile
from mesonbuild import environment
from mesonbuild import mesonlib
from mesonbuild import mlog
from mesonbuild import mesonmain
from mesonbuild.mesonlib import stringlistify
from mesonbuild.scripts import meson_test, meson_benchmark
import argparse
import xml.etree.ElementTree as ET
import time
import multiprocessing
import concurrent.futures as conc

from mesonbuild.coredata import backendlist

class TestResult:
    def __init__(self, msg, stdo, stde, mlog, conftime=0, buildtime=0, testtime=0):
        self.msg = msg
        self.stdo = stdo
        self.stde = stde
        self.mlog = mlog
        self.conftime = conftime
        self.buildtime = buildtime
        self.testtime = testtime

class AutoDeletedDir():
    def __init__(self, d):
        self.dir = d
    def __enter__(self):
        os.makedirs(self.dir, exist_ok=True)
        return self.dir
    def __exit__(self, _type, value, traceback):
        # On Windows, shutil.rmtree fails sometimes, because 'the directory is not empty'.
        # Retrying fixes this.
        # That's why we don't use tempfile.TemporaryDirectory, but wrap the deletion in the AutoDeletedDir class.
        retries = 5
        for i in range(0, retries):
            try:
                shutil.rmtree(self.dir)
                return
            except OSError:
                if i == retries-1:
                    raise
                time.sleep(0.1 * (2**i))

passing_tests = 0
failing_tests = 0
skipped_tests = 0
failing_logs = []
print_debug = 'MESON_PRINT_TEST_OUTPUT' in os.environ

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

#unity_flags = ['--unity']
unity_flags = []

backend_flags = None
compile_commands = None
test_commands = None
install_commands = None

def setup_commands(backend):
    global backend_flags, compile_commands, test_commands, install_commands
    msbuild_exe = shutil.which('msbuild')
    if backend == 'vs2010' or (backend is None and msbuild_exe is not None):
        backend_flags = ['--backend=vs2010']
        compile_commands = ['msbuild']
        test_commands = ['msbuild', 'RUN_TESTS.vcxproj']
        install_commands = []
    elif backend == 'vs2015':
        backend_flags = ['--backend=vs2015']
        compile_commands = ['msbuild']
        test_commands = ['msbuild', 'RUN_TESTS.vcxproj']
        install_commands = []
    elif backend == 'xcode' or (backend is None and mesonlib.is_osx()):
        backend_flags = ['--backend=xcode']
        compile_commands = ['xcodebuild']
        test_commands = ['xcodebuild', '-target', 'RUN_TESTS']
        install_commands = []
    else:
        backend_flags = []
        ninja_command = environment.detect_ninja()
        if ninja_command is None:
            raise RuntimeError('Could not find Ninja v1.6 or newer')
        if print_debug:
            compile_commands = [ninja_command, '-v']
        else:
            compile_commands = [ninja_command]
        compile_commands += ['-w', 'dupbuild=err']
        test_commands = [ninja_command, 'test', 'benchmark']
        install_commands = [ninja_command, 'install']

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

def platform_fix_exe_name(fname):
    if not fname.endswith('?exe'):
        return fname
    fname = fname[:-4]
    if mesonlib.is_windows():
        return fname + '.exe'
    return fname

def validate_install(srcdir, installdir):
    # List of installed files
    info_file = os.path.join(srcdir, 'installed_files.txt')
    # If this exists, the test does not install any other files
    noinst_file = 'usr/no-installed-files'
    expected = {}
    found = {}
    ret_msg = ''
    # Generate list of expected files
    if os.path.exists(os.path.join(installdir, noinst_file)):
        expected[noinst_file] = False
    elif os.path.exists(info_file):
        with open(info_file) as f:
            for line in f:
                expected[platform_fix_exe_name(line.strip())] = False
    # Check if expected files were found
    for fname in expected:
        if os.path.exists(os.path.join(installdir, fname)):
            expected[fname] = True
    for (fname, found) in expected.items():
        if not found:
            ret_msg += 'Expected file {0} missing.\n'.format(fname)
    # Check if there are any unexpected files
    found = get_relative_files_list_from_dir(installdir)
    for fname in found:
        if fname not in expected and not fname.endswith('.pdb'):
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

def run_configure_inprocess(commandlist):
    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()
    old_stderr = sys.stderr
    sys.stderr = mystderr = StringIO()
    try:
        returncode = mesonmain.run(commandlist[0], commandlist[1:])
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    return (returncode, mystdout.getvalue(), mystderr.getvalue())

def run_test_inprocess(testdir):
    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()
    old_stderr = sys.stderr
    sys.stderr = mystderr = StringIO()
    old_cwd = os.getcwd()
    os.chdir(testdir)
    try:
        returncode_test = meson_test.run(['meson-private/meson_test_setup.dat'])
        returncode_benchmark = meson_benchmark.run(['meson-private/meson_benchmark_setup.dat'])
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        os.chdir(old_cwd)
    return (max(returncode_test, returncode_benchmark), mystdout.getvalue(), mystderr.getvalue())

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

def run_test(skipped, testdir, extra_args, flags, compile_commands, install_commands, should_succeed):
    if skipped:
        return None
    with AutoDeletedDir(tempfile.mkdtemp(prefix='b ', dir='.')) as build_dir:
        with AutoDeletedDir(tempfile.mkdtemp(prefix='i ', dir=os.getcwd())) as install_dir:
            try:
                return _run_test(testdir, build_dir, install_dir, extra_args, flags, compile_commands, install_commands, should_succeed)
            finally:
                mlog.shutdown() # Close the log file because otherwise Windows wets itself.

def _run_test(testdir, test_build_dir, install_dir, extra_args, flags, compile_commands, install_commands, should_succeed):
    test_args = parse_test_args(testdir)
    gen_start = time.time()
    gen_command = [meson_command, '--prefix', '/usr', '--libdir', 'lib', testdir, test_build_dir]\
        + flags + test_args + extra_args
    (returncode, stdo, stde) = run_configure_inprocess(gen_command)
    try:
        logfile = os.path.join(test_build_dir, 'meson-logs/meson-log.txt')
        with open(logfile, errors='ignore') as f:
            mesonlog = f.read()
    except Exception:
        mesonlog = 'No meson-log.txt found.'
    gen_time = time.time() - gen_start
    if not should_succeed:
        if returncode != 0:
            return TestResult('', stdo, stde, mesonlog, gen_time)
        return TestResult('Test that should have failed succeeded', stdo, stde, mesonlog, gen_time)
    if returncode != 0:
        return TestResult('Generating the build system failed.', stdo, stde, mesonlog, gen_time)
    if 'msbuild' in compile_commands[0]:
        sln_name = glob(os.path.join(test_build_dir, '*.sln'))[0]
        comp = compile_commands + [os.path.split(sln_name)[-1]]
    else:
        comp = compile_commands
    build_start = time.time()
    pc = subprocess.Popen(comp, cwd=test_build_dir,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (o, e) = pc.communicate()
    build_time = time.time() - build_start
    stdo += o.decode(sys.stdout.encoding)
    stde += e.decode(sys.stdout.encoding)
    if pc.returncode != 0:
        return TestResult('Compiling source code failed.', stdo, stde, mesonlog, gen_time, build_time)
    test_start = time.time()
    # Note that we don't test that running e.g. 'ninja test' actually
    # works. One hopes that this is a common enough happening that
    # it is picked up immediately on development.
    (returncode, tstdo, tstde) = run_test_inprocess(test_build_dir)
    test_time = time.time() - test_start
    stdo += tstdo
    stde += tstde
    if returncode != 0:
        return TestResult('Running unit tests failed.', stdo, stde, mesonlog, gen_time, build_time, test_time)
    if len(install_commands) == 0:
        return TestResult('', '', '', gen_time, build_time, test_time)
    else:
        env = os.environ.copy()
        env['DESTDIR'] = install_dir
        pi = subprocess.Popen(install_commands, cwd=test_build_dir, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (o, e) = pi.communicate()
        stdo += o.decode(sys.stdout.encoding)
        stde += e.decode(sys.stdout.encoding)
        if pi.returncode != 0:
            return TestResult('Running install failed.', stdo, stde, mesonlog, gen_time, build_time, test_time)
        return TestResult(validate_install(testdir, install_dir), stdo, stde, mesonlog, gen_time, build_time, test_time)

def gather_tests(testdir):
    tests = [t.replace('\\', '/').split('/', 2)[2] for t in glob(os.path.join(testdir, '*'))]
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

def detect_tests_to_run():
    all_tests = []
    all_tests.append(('common', gather_tests('test cases/common'), False))
    all_tests.append(('failing', gather_tests('test cases/failing'), False))
    all_tests.append(('prebuilt', gather_tests('test cases/prebuilt'), False))

    all_tests.append(('platform-osx', gather_tests('test cases/osx'), False if mesonlib.is_osx() else True))
    all_tests.append(('platform-windows', gather_tests('test cases/windows'), False if mesonlib.is_windows() else True))
    all_tests.append(('platform-linux', gather_tests('test cases/linuxlike'), False if not (mesonlib.is_osx() or mesonlib.is_windows()) else True))
    all_tests.append(('framework', gather_tests('test cases/frameworks'), False if not mesonlib.is_osx() and not mesonlib.is_windows() else True))
    all_tests.append(('java', gather_tests('test cases/java'), False if not mesonlib.is_osx() and shutil.which('javac') else True))
    all_tests.append(('C#', gather_tests('test cases/csharp'), False if shutil.which('mcs') else True))
    all_tests.append(('vala', gather_tests('test cases/vala'), False if shutil.which('valac') else True))
    all_tests.append(('rust', gather_tests('test cases/rust'), False if shutil.which('rustc') else True))
    all_tests.append(('d', gather_tests('test cases/d'), False if have_d_compiler() else True))
    all_tests.append(('objective c', gather_tests('test cases/objc'), False if not mesonlib.is_windows() else True))
    all_tests.append(('fortran', gather_tests('test cases/fortran'), False if shutil.which('gfortran') else True))
    all_tests.append(('swift', gather_tests('test cases/swift'), False if shutil.which('swiftc') else True))
    all_tests.append(('python3', gather_tests('test cases/python3'), False if shutil.which('python3') else True))
    return all_tests

def run_tests(extra_args):
    global passing_tests, failing_tests, stop, executor, futures
    all_tests = detect_tests_to_run()
    logfile = open('meson-test-run.txt', 'w', encoding="utf_8")
    junit_root = ET.Element('testsuites')
    conf_time = 0
    build_time = 0
    test_time = 0

    executor = conc.ProcessPoolExecutor(max_workers=multiprocessing.cpu_count())

    for name, test_cases, skipped in all_tests:
        current_suite = ET.SubElement(junit_root, 'testsuite', {'name' : name, 'tests' : str(len(test_cases))})
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
            result = executor.submit(run_test, skipped, t, extra_args, unity_flags + backend_flags, compile_commands, install_commands, name != 'failing')
            futures.append((testname, t, result))
        for (testname, t, result) in futures:
            result = result.result()
            if result is None:
                print('Skipping:', t)
                current_test = ET.SubElement(current_suite, 'testcase', {'name' : testname,
                                                                         'classname' : name})
                ET.SubElement(current_test, 'skipped', {})
                global skipped_tests
                skipped_tests += 1
            else:
                without_install = "" if len(install_commands) > 0 else " (without install)"
                if result.msg != '':
                    print('Failed test%s: %s' % (without_install, t))
                    print('Reason:', result.msg)
                    failing_tests += 1
                    failing_logs.append(result.mlog)
                else:
                    print('Succeeded test%s: %s' % (without_install, t))
                    passing_tests += 1
                conf_time += result.conftime
                build_time += result.buildtime
                test_time += result.testtime
                total_time = conf_time + build_time + test_time
                log_text_file(logfile, t, result.stdo, result.stde)
                current_test = ET.SubElement(current_suite, 'testcase', {'name' : testname,
                                                                         'classname' : name,
                                                                         'time' : '%.3f' % total_time})
                if result.msg != '':
                    ET.SubElement(current_test, 'failure', {'message' : result.msg})
                stdoel = ET.SubElement(current_test, 'system-out')
                stdoel.text = result.stdo
                stdeel = ET.SubElement(current_test, 'system-err')
                stdeel.text = result.stde
    print("\nTotal configuration time: %.2fs" % conf_time)
    print("Total build time: %.2fs" % build_time)
    print("Total test time: %.2fs" % test_time)
    ET.ElementTree(element=junit_root).write('meson-test-run.xml', xml_declaration=True, encoding='UTF-8')

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
        cmd = [compiler, '/nologo', '/Fo'+objectfile, '/c', source]
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
    return (objectfile, stlibfile)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run the test suite of Meson.")
    parser.add_argument('extra_args', nargs='*',
                   help='arguments that are passed directly to Meson (remember to have -- before these).')
    parser.add_argument('--backend', default=None, dest='backend',
                        choices = backendlist)
    options = parser.parse_args()
    setup_commands(options.backend)

    script_dir = os.path.split(__file__)[0]
    if script_dir != '':
        os.chdir(script_dir)
    check_format()
    pbfiles = generate_prebuilt()
    try:
        run_tests(options.extra_args)
    except StopException:
        pass
    for f in pbfiles:
        os.unlink(f)
    print('\nTotal passed tests:', passing_tests)
    print('Total failed tests:', failing_tests)
    print('Total skipped tests:', skipped_tests)
    if failing_tests > 0 and ('TRAVIS' in os.environ or 'APPVEYOR' in os.environ):
        print('\nMesonlogs of failing tests\n')
        for l in failing_logs:
            print(l, '\n')
    sys.exit(failing_tests)

