#!/usr/bin/env python3

# Copyright 2012-2015 The Meson development team

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
import os, subprocess, shutil, sys, platform, signal
import environment
import mesonlib
import argparse
import xml.etree.ElementTree as ET

from meson import backendlist

passing_tests = 0
failing_tests = 0
print_debug = 'MESON_PRINT_TEST_OUTPUT' in os.environ

test_build_dir = 'work area'
install_dir = os.path.join(os.path.split(os.path.abspath(__file__))[0], 'install dir')
meson_command = './meson.py'

class StopException(Exception):
    def __init__(self):
        super(Exception, self).__init__('Stopped by user')

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
    elif backend == 'xcode' or (backend is None and mesonlib.is_osx()):
        backend_flags = ['--backend=xcode']
        compile_commands = ['xcodebuild']
        test_commands = ['xcodebuild', '-target', 'RUN_TESTS']
        install_commands = []
    else:
        backend_flags = []
        ninja_command = environment.detect_ninja()
        if ninja_command is None:
            raise RuntimeError('Could not find Ninja executable.')
        if print_debug:
            compile_commands = [ninja_command, '-v']
        else:
            compile_commands = [ninja_command]
        test_commands = [ninja_command, 'test']
        install_commands = [ninja_command, 'install']

def platform_fix_filename(fname):
    if platform.system() == 'Darwin':
        if fname.endswith('.so'):
            return fname[:-2] + 'dylib'
        return fname.replace('.so.', '.dylib.')
    elif platform.system() == 'Windows':
        if fname.endswith('.so'):
            (p, f) = os.path.split(fname)
            f = f[3:-2] + 'dll'
            return os.path.join(p, f)
        if fname.endswith('.a'):
            return fname[:-1] + 'lib'
    return fname

def validate_install(srcdir, installdir):
    if platform.system() == 'Windows':
        # Don't really know how Windows installs should work
        # so skip.
        return ''
    info_file = os.path.join(srcdir, 'installed_files.txt')
    expected = {}
    found = {}
    if os.path.exists(info_file):
        for line in open(info_file):
            expected[platform_fix_filename(line.strip())] = True
    for root, _, files in os.walk(installdir):
        for fname in files:
            found_name = os.path.join(root, fname)[len(installdir)+1:]
            found[found_name] = True
    expected = set(expected)
    found = set(found)
    missing = expected - found
    for fname in missing:
        return 'Expected file %s missing.' % fname
    extra = found - expected
    for fname in extra:
        return 'Found extra file %s.' % fname
    return ''

def log_text_file(logfile, testdir, msg, stdo, stde):
    global passing_tests, failing_tests, stop
    if msg != '':
        print('Fail:', msg)
        failing_tests += 1
    else:
        print('Success')
        passing_tests += 1
    logfile.write('%s\nstdout\n\n---\n' % testdir)
    logfile.write(stdo)
    logfile.write('\n\n---\n\nstderr\n\n---\n')
    logfile.write(stde)
    logfile.write('\n\n---\n\n')
    if print_debug:
        print(stdo)
        print(stde, file=sys.stderr)
    if stop:
        raise StopException()

def run_test(testdir, should_succeed):
    global compile_commands
    shutil.rmtree(test_build_dir)
    shutil.rmtree(install_dir)
    os.mkdir(test_build_dir)
    os.mkdir(install_dir)
    print('Running test: ' + testdir)
    gen_command = [sys.executable, meson_command, '--prefix', '/usr', '--libdir', 'lib', testdir, test_build_dir]\
        + unity_flags + backend_flags
    p = subprocess.Popen(gen_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdo, stde) = p.communicate()
    stdo = stdo.decode('utf-8')
    stde = stde.decode('utf-8')
    if not should_succeed:
        if p.returncode != 0:
            return ('', stdo, stde)
        return ('Test that should have failed succeeded', stdo, stde)
    if p.returncode != 0:
        return ('Generating the build system failed.', stdo, stde)
    if 'msbuild' in compile_commands[0]:
        sln_name = glob(os.path.join(test_build_dir, '*.sln'))[0]
        comp = compile_commands + [os.path.split(sln_name)[-1]]
    else:
        comp = compile_commands
    pc = subprocess.Popen(comp, cwd=test_build_dir,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (o, e) = pc.communicate()
    stdo += o.decode('utf-8')
    stde += e.decode('utf-8')
    if pc.returncode != 0:
        return ('Compiling source code failed.', stdo, stde)
    pt = subprocess.Popen(test_commands, cwd=test_build_dir,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (o, e) = pt.communicate()
    stdo += o.decode('utf-8')
    stde += e.decode('utf-8')
    if pt.returncode != 0:
        return ('Running unit tests failed.', stdo, stde)
    if len(install_commands) == 0:
        print("Skipping install test")
        return ('', '', '')
    else:
        env = os.environ.copy()
        env['DESTDIR'] = install_dir
        pi = subprocess.Popen(install_commands, cwd=test_build_dir, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (o, e) = pi.communicate()
        stdo += o.decode('utf-8')
        stde += e.decode('utf-8')
        if pi.returncode != 0:
            return ('Running install failed.', stdo, stde)
        return (validate_install(testdir, install_dir), stdo, stde)

def gather_tests(testdir):
    tests = [t.replace('\\', '/').split('/', 2)[2] for t in glob(os.path.join(testdir, '*'))]
    testlist = [(int(t.split()[0]), t) for t in tests]
    testlist.sort()
    tests = [os.path.join(testdir, t[1]) for t in testlist]
    return tests

def detect_tests_to_run():
    all_tests = []
    all_tests.append(('common', gather_tests('test cases/common')))
    all_tests.append(('failing', gather_tests('test cases/failing')))
    all_tests.append(('prebuilt object', gather_tests('test cases/prebuilt object')))

    if mesonlib.is_osx():
        all_tests.append(('platform', gather_tests('test cases/osx')))
    elif mesonlib.is_windows():
        all_tests.append(('platform', gather_tests('test cases/windows')))
    else:
        all_tests.append(('platform', gather_tests('test cases/linuxlike')))
    if not mesonlib.is_osx() and not mesonlib.is_windows():
        all_tests.append(('framework', gather_tests('test cases/frameworks')))
    else:
        all_tests.append(('framework', []))
    if not mesonlib.is_osx() and shutil.which('javac'):
        all_tests.append(('java', gather_tests('test cases/java')))
    else:
        all_tests.append(('java'), [])
    if shutil.which('mcs'):
        all_tests.append(('C#', gather_tests('test cases/csharp')))
    else:
        all_tests.append(('C#', []))
    if shutil.which('valac'):
        all_tests.append(('vala', gather_tests('test cases/vala')))
    else:
        all_tests.append(('vala', []))
    if shutil.which('rustc'):
        all_tests.append(('rust', gather_tests('test cases/rust')))
    else:
        all_tests.append(('rust', []))
    if not mesonlib.is_windows():
        all_tests.append(('objective c', gather_tests('test cases/objc')))
    else:
        all_tests.append(('objective c', []))
    if shutil.which('gfortran'):
        all_tests.append(('fortran', gather_tests('test cases/fortran')))
    else:
        all_tests.append(('fortran', []))
    return all_tests

def run_tests():
    all_tests = detect_tests_to_run()
    logfile = open('meson-test-run.txt', 'w')
    junit_root = ET.Element('testsuites')
    try:
        os.mkdir(test_build_dir)
    except OSError:
        pass
    try:
        os.mkdir(install_dir)
    except OSError:
        pass

    for name, test_cases in all_tests:
        if len(test_cases) == 0:
            print('\nNot running %s tests.\n' % name)
        else:
            current_suite = ET.SubElement(junit_root, 'testsuite', {'name' : name})
            print('\nRunning %s tests.\n' % name)
            for t in test_cases:
                (msg, stdo, stde) = run_test(t, name != 'failing')
                log_text_file(logfile, t, msg, stdo, stde)
                current_test = ET.SubElement(current_suite, 'testcase', {'name' : os.path.split(t)[-1]})
                if msg != '':
                    failure = ET.SubElement(current_test, 'failure')
                    failure.text = msg
                stdoel = ET.SubElement(current_test, 'system-out')
                stdoel.text = stdo
                stdeel = ET.SubElement(current_test, 'system-err')
                stdeel.text = stde
    ET.ElementTree(element=junit_root).write('meson-test-run.xml', xml_declaration=True, encoding='UTF-8')

def check_file(fname):
    linenum = 1
    for line in open(fname, 'rb').readlines():
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
            if file.endswith('.py') or file.endswith('.build'):
                fullname = os.path.join(root, file)
                check_file(fullname)

def generate_prebuilt_object():
    source = 'test cases/prebuilt object/1 basic/source.c'
    objectbase = 'test cases/prebuilt object/1 basic/prebuilt.'
    if shutil.which('cl'):
        objectfile = objectbase + 'obj'
        cmd = ['cl', '/nologo', '/Fo'+objectfile, '/c', source]
    else:
        if mesonlib.is_windows():
            objectfile = objectbase + 'obj'
        else:
            objectfile = objectbase + 'o'
        cmd = ['cc', '-c', source, '-o', objectfile]
    subprocess.check_call(cmd)
    return objectfile

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run the test suite of Meson.")
    parser.add_argument('--backend', default=None, dest='backend',
                      choices = backendlist)
    options = parser.parse_args()
    setup_commands(options.backend)

    script_dir = os.path.split(__file__)[0]
    if script_dir != '':
        os.chdir(script_dir)
    check_format()
    pbfile = generate_prebuilt_object()
    try:
        run_tests()
    except StopException:
        pass
    os.unlink(pbfile)
    print('\nTotal passed tests:', passing_tests)
    print('Total failed tests:', failing_tests)
    sys.exit(failing_tests)

