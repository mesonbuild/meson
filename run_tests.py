#!/usr/bin/env python3

# Copyright 2012-2017 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import shutil
import subprocess
import platform
from mesonbuild import mesonlib
from mesonbuild.environment import detect_ninja
from enum import Enum
from glob import glob

Backend = Enum('Backend', 'ninja vs xcode')

if mesonlib.is_windows():
    exe_suffix = '.exe'
else:
    exe_suffix = ''

def get_backend_args_for_dir(backend, builddir):
    '''
    Visual Studio backend needs to be given the solution to build
    '''
    if backend.startswith('vs'):
        sln_name = glob(os.path.join(builddir, '*.sln'))[0]
        return [os.path.split(sln_name)[-1]]
    return []

def get_build_target_args(backend, target):
    if target is None:
        return []
    if backend.startswith('vs'):
        return ['/target:' + target]
    if backend == 'xcode':
        return ['-target', target]
    return [target]

def get_backend_commands(backend, debug=False):
    install_cmd = []
    uninstall_cmd = []
    if backend.startswith('vs'):
        cmd = ['msbuild']
        clean_cmd = cmd + ['/target:Clean']
        test_cmd = cmd + ['RUN_TESTS.vcxproj']
    elif backend == 'xcode':
        cmd = ['xcodebuild']
        clean_cmd = cmd + ['-alltargets', 'clean']
        test_cmd = cmd + ['-target', 'RUN_TESTS']
    else:
        # We need at least 1.6 because of -w dupbuild=err
        cmd = [detect_ninja('1.6'), '-w', 'dupbuild=err']
        if cmd[0] is None:
            raise RuntimeError('Could not find Ninja v1.6 or newer')
        if debug:
            cmd += ['-v']
        clean_cmd = cmd + ['clean']
        test_cmd = cmd + ['test', 'benchmark']
        install_cmd = cmd + ['install']
        uninstall_cmd = cmd + ['uninstall']
    return cmd, clean_cmd, test_cmd, install_cmd, uninstall_cmd

def get_fake_options(prefix):
    import argparse
    opts = argparse.Namespace()
    opts.cross_file = None
    opts.wrap_mode = None
    opts.prefix = prefix
    return opts

class FakeEnvironment(object):
    def __init__(self):
        self.cross_info = None

    def is_cross_build(self):
        return False

if __name__ == '__main__':
    returncode = 0
    # Iterate over list in reverse order to find the last --backend arg
    backend = Backend.ninja
    for arg in reversed(sys.argv[1:]):
        if arg.startswith('--backend'):
            if arg.startswith('--backend=vs'):
                backend = Backend.vs
            elif arg == '--backend=xcode':
                backend = Backend.xcode
            break
    # Running on a developer machine? Be nice!
    if not mesonlib.is_windows() and 'TRAVIS' not in os.environ:
        os.nice(20)
    print('Running unittests.\n')
    units = ['InternalTests', 'AllPlatformTests']
    if mesonlib.is_linux():
        units += ['LinuxlikeTests']
    elif mesonlib.is_windows():
        units += ['WindowsTests']
    # Unit tests always use the Ninja backend, so just skip them if we're
    # testing the VS backend
    if backend is Backend.ninja:
        returncode += subprocess.call([sys.executable, 'run_unittests.py', '-v'] + units)
    # Ubuntu packages do not have a binary without -6 suffix.
    if shutil.which('arm-linux-gnueabihf-gcc-6') and not platform.machine().startswith('arm'):
        print('Running cross compilation tests.\n')
        returncode += subprocess.call([sys.executable, 'run_cross_test.py', 'cross/ubuntu-armhf.txt'])
    returncode += subprocess.call([sys.executable, 'run_project_tests.py'] + sys.argv[1:])
    sys.exit(returncode)
