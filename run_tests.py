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
import os, subprocess, shutil

test_build_dir = 'test build area'
builder_command = './runbuilder.py'

def run_test(testdir):
    shutil.rmtree(test_build_dir)
    os.mkdir(test_build_dir)
    print('Running test: ' + testdir)
    p = subprocess.Popen([builder_command, testdir, test_build_dir])
    p.wait()
    if p.returncode != 0:
        raise RuntimeError('Test failed.')

def run_tests():
    tests = glob('test cases/*')
    tests.sort()
    try:
        os.mkdir(test_build_dir)
    except OSError:
        pass
    [run_test(t) for t in tests]


if __name__ == '__main__':
    os.chdir(os.path.split(__file__)[0])
    run_tests()
