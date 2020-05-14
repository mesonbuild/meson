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

This is now just a wrapper around run_project_tests.py with specific arguments
'''

import argparse
import subprocess
from mesonbuild import mesonlib
from mesonbuild.coredata import version as meson_version


def runtests(cross_file, failfast):
    tests = ['--only', 'common']
    cmd = mesonlib.python_command + ['run_project_tests.py', '--backend', 'ninja'] + (['--failfast'] if failfast else []) + tests + ['--cross-file', cross_file]
    return subprocess.call(cmd)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--failfast', action='store_true')
    parser.add_argument('cross_file')
    options = parser.parse_args()
    return runtests(options.cross_file, options.failfast)

if __name__ == '__main__':
    print('Meson build system', meson_version, 'Cross Tests')
    raise SystemExit(main())
