#!/usr/bin/python3 -tt

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

test_build_dir = 'work area'
install_dir = os.path.join(os.path.split(os.path.abspath(__file__))[0], 'install dir')
use_shell = len(sys.argv) > 1
builder_command = './builder.py'
if use_shell:
    generator_flags = ['--generator', 'shell']
    compile_commands = ['compile.sh']
    test_commands = ['run_tests.sh']
    install_commands = ['install.sh']
else:
    generator_flags = []
    compile_commands = ['ninja']
    test_commands = ['ninja', 'test']
    install_commands = ['ninja', 'install']

def run_test(testdir):
    shutil.rmtree(test_build_dir)
    shutil.rmtree(install_dir)
    os.mkdir(test_build_dir)
    os.mkdir(install_dir)
    print('Running test: ' + testdir)
    gen_command = [builder_command, '--prefix', install_dir, testdir, test_build_dir] + generator_flags
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

def run_tests():
    tests = [t.split('/', 1)[1] for t in glob('test cases/*')]
    testlist = [(int(t.split()[0]), t) for t in tests]
    testlist.sort()
    tests = [os.path.join('test cases', t[1]) for t in testlist]
    try:
        os.mkdir(test_build_dir)
    except OSError:
        pass
    [run_test(t) for t in tests]

if __name__ == '__main__':
    os.chdir(os.path.split(__file__)[0])
    run_tests()
