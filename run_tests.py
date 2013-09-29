#!/usr/bin/env python3

# Copyright 2012-2013 Jussi Pakkanen

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
import os, subprocess, shutil, sys, platform
import environment

test_build_dir = 'work area'
install_dir = os.path.join(os.path.split(os.path.abspath(__file__))[0], 'install dir')
meson_command = './meson.py'
if True: # Currently we have only one backend.
    backend_flags = []
    ninja_command = environment.detect_ninja()
    if ninja_command is None:
        raise RuntimeError('Could not find Ninja executable.')
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
         return
    info_file = os.path.join(srcdir, 'installed_files.txt')
    expected = {}
    found = {}
    if os.path.exists(info_file):
        for line in open(info_file):
            expected[platform_fix_filename(line.strip())] = True
    for root, dirs, files in os.walk(installdir):
        for fname in files:
            found_name = os.path.join(root, fname)[len(installdir)+1:]
            found[found_name] = True
    expected = set(expected)
    found = set(found)
    missing = expected - found
    for fname in missing:
        raise RuntimeError('Expected file %s missing.' % fname)
    extra = found - expected
    for fname in extra:
        raise RuntimeError('Found extra file %s.' % fname)

def run_test(testdir, should_succeed=True):
    shutil.rmtree(test_build_dir)
    shutil.rmtree(install_dir)
    os.mkdir(test_build_dir)
    os.mkdir(install_dir)
    print('Running test: ' + testdir)
    gen_command = [sys.executable, meson_command, '--prefix', install_dir, testdir, test_build_dir] + backend_flags
    p = subprocess.Popen(gen_command)
    p.wait()
    if not should_succeed:
        if p.returncode != 0:
            return
        raise RuntimeError('Test that should fail succeeded.')
    if p.returncode != 0:
        raise RuntimeError('Generating the build system failed.')
    pc = subprocess.Popen(compile_commands, cwd=test_build_dir)
    pc.wait()
    if pc.returncode != 0:
        raise RuntimeError('Compiling source code failed.')
    pt = subprocess.Popen(test_commands, cwd=test_build_dir)
    pt.wait()
    if pt.returncode != 0:
        raise RuntimeError('Running unit tests failed.')
    pi = subprocess.Popen(install_commands, cwd=test_build_dir)
    pi.wait()
    if pi.returncode != 0:
        raise RuntimeError('Running install failed.')
    validate_install(testdir, install_dir)

def gather_tests(testdir):
    tests = [t.replace('\\', '/').split('/', 2)[2] for t in glob(os.path.join(testdir, '*'))]
    testlist = [(int(t.split()[0]), t) for t in tests]
    testlist.sort()
    tests = [os.path.join(testdir, t[1]) for t in testlist]
    return tests

def run_tests():
    commontests = gather_tests('test cases/common')
    failtests = gather_tests('test cases/failing')
    if environment.is_osx():
        platformtests = gather_tests('test cases/osx')
    elif environment.is_windows():
        platformtests = gather_tests('test cases/windows')
    else:
        platformtests = gather_tests('test cases/linuxlike')
    if not environment.is_osx() and not environment.is_windows():
        frameworktests = gather_tests('test cases/frameworks')
    else:
        frameworktests = []
    if not environment.is_windows():
        objctests = gather_tests('test cases/objc')
    else:
        objctests = []
    try:
        os.mkdir(test_build_dir)
    except OSError:
        pass
    try:
        os.mkdir(install_dir)
    except OSError:
        pass
    print('\nRunning common tests.\n')
    [run_test(t) for t in commontests]
    print('\nRunning failing tests.\n')
    [run_test(t, False) for t in failtests]
    if len(platformtests) > 0:
        print('\nRunning platform dependent tests.\n')
        [run_test(t) for t in platformtests]
    else:
        print('\nNo platform specific tests.\n')
    if len(frameworktests) > 0:
        print('\nRunning framework tests.\n')
        [run_test(t) for t in frameworktests]
    else:
        print('\nNo framework tests on this platform.\n')
    if len(objctests) > 0:
        print('\nRunning extra language tests.\n')
        [run_test(t) for t in objctests]
    else:
        print('\nNo extra language tests on this platform.\n')

def check_file(fname):
    if fname.endswith('parsetab.py'): # Autogenerated
        return True
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
    for (root, dirs, files) in os.walk('.'):
        for file in files:
            if file.endswith('.py') or file.endswith('.build'):
                fullname = os.path.join(root, file)
                check_file(fullname)

if __name__ == '__main__':
    script_dir = os.path.split(__file__)[0]
    if script_dir != '':
        os.chdir(script_dir)
    check_format()
    run_tests()
