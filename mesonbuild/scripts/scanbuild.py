# Copyright 2016 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys, os
import subprocess
import shutil
import tempfile

def scanbuild(srcdir, blddir, privdir, logdir, args):
    with tempfile.TemporaryDirectory(dir=privdir) as scandir:
        meson_cmd = ['scan-build'] + args
        build_cmd = ['scan-build', '-o', logdir, 'ninja']
        rc = subprocess.call(meson_cmd + [srcdir, scandir])
        if rc != 0:
            return rc
        return subprocess.call(build_cmd)

def run(args):
    srcdir = args[0]
    blddir = args[1]
    meson_cmd = args[2:]
    privdir = os.path.join(blddir, 'meson-private')
    logdir = os.path.join(blddir, 'meson-logs/scanbuild')
    shutil.rmtree(logdir, ignore_errors=True)
    if not shutil.which('scan-build'):
        print('Scan-build not installed')
        return 1
    return scanbuild(srcdir, blddir, privdir, logdir, meson_cmd)
