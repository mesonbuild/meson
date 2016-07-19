#!/usr/bin/env python3

# Copyright 2013-2016 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''Runs the basic test suite through a cross compiler.
Not part of the main test suite because of two reasons:

1) setup of the cross build is platform specific
2) it can be slow (e.g. when invoking test apps via wine)

Eventually migrate to something fancier.'''

import os, subprocess, shutil, sys
import mesonbuild.environment as environment

from run_tests import gather_tests

test_build_dir = 'work area'
install_dir = os.path.join(os.path.split(os.path.abspath(__file__))[0], 'install dir')
meson_command = './meson.py'

extra_flags = ['--cross-file', sys.argv[1]]
ninja_command = environment.detect_ninja()
if ninja_command is None:
    raise RuntimeError('Could not find Ninja v1.6 or newer')
compile_commands = [ninja_command]
test_commands = [ninja_command, 'test']
install_commands = [ninja_command, 'install']

def run_test(testdir, should_succeed=True):
    shutil.rmtree(test_build_dir)
    shutil.rmtree(install_dir)
    os.mkdir(test_build_dir)
    os.mkdir(install_dir)
    print('Running test: ' + testdir)
    gen_command = [sys.executable, meson_command, '--prefix', '/usr', '--libdir', 'lib', testdir, test_build_dir] + extra_flags
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
    install_env = os.environ.copy()
    install_env['DESTDIR'] = install_dir
    pi = subprocess.Popen(install_commands, cwd=test_build_dir, env=install_env)
    pi.wait()
    if pi.returncode != 0:
        raise RuntimeError('Running install failed.')

def run_tests():
    commontests = gather_tests('test cases/common')
    try:
        os.mkdir(test_build_dir)
    except OSError:
        pass
    try:
        os.mkdir(install_dir)
    except OSError:
        pass
    print('\nRunning cross compilation tests.\n')
    [run_test(t) for t in commontests]

if __name__ == '__main__':
    script_dir = os.path.split(__file__)[0]
    if script_dir != '':
        os.chdir(script_dir)
    run_tests()
