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

if __name__ == '__main__':
    returncode = 0
    # Running on a developer machine? Be nice!
    if not mesonlib.is_windows() and 'TRAVIS' not in os.environ:
        os.nice(20)
    print('Running unittests.\n')
    units = ['InternalTests', 'AllPlatformTests']
    if mesonlib.is_linux():
        units += ['LinuxlikeTests']
    elif mesonlib.is_windows():
        units += ['WindowsTests']
    returncode += subprocess.call([sys.executable, 'run_unittests.py', '-v'] + units)
    # Ubuntu packages do not have a binary without -6 suffix.
    if shutil.which('arm-linux-gnueabihf-gcc-6') and not platform.machine().startswith('arm'):
        print('Running cross compilation tests.\n')
        returncode += subprocess.call([sys.executable, 'run_cross_test.py', 'cross/ubuntu-armhf.txt'])
    returncode += subprocess.call([sys.executable, 'run_project_tests.py'] + sys.argv[1:])
    sys.exit(returncode)
