#!/usr/bin/env python3 -tt

# Copyright 2012 Jussi Pakkanen

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
import os, subprocess, shutil, sys
import environment

test_build_dir = 'work area'
install_dir = os.path.join(os.path.split(os.path.abspath(__file__))[0], 'install dir')
use_shell = len(sys.argv) > 1
meson_command = './meson.py'
if use_shell:
    backend_flags = ['--backend', 'shell']
    compile_commands = ['compile.sh']
    test_commands = ['run_tests.sh']
    install_commands = ['install.sh']
else:
    backend_flags = []
    compile_commands = ['ninja']
    test_commands = ['ninja', 'test']
    install_commands = ['ninja', 'install']

def run_test(testdir):
    shutil.rmtree(test_build_dir)
    shutil.rmtree(install_dir)
    os.mkdir(test_build_dir)
    os.mkdir(install_dir)
    print('Running test: ' + testdir)
    gen_command = [sys.executable, meson_command, '--prefix', install_dir, testdir, test_build_dir] + backend_flags
    p = subprocess.Popen(gen_command)
    p.wait()
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

def gather_tests(testdir):
    tests = [t.replace('\\', '/').split('/', 2)[2] for t in glob(os.path.join(testdir, '*'))]
    testlist = [(int(t.split()[0]), t) for t in tests]
    testlist.sort()
    tests = [os.path.join(testdir, t[1]) for t in testlist]
    return tests

def run_tests():
    commontests = gather_tests('test cases/common')
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
    print('\nRunning platform dependent tests.\n')
    [run_test(t) for t in platformtests]
    print('\nRunning framework tests.\n')
    [run_test(t) for t in frameworktests]

if __name__ == '__main__':
    script_dir = os.path.split(__file__)[0]
    if script_dir != '':
        os.chdir(script_dir)
    run_tests()
