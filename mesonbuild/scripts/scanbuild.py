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

import os
import subprocess
import shutil
import tempfile
from ..environment import detect_ninja
from ..mesonlib import Popen_safe

def scanbuild(exename, srcdir, blddir, privdir, logdir, args):
    with tempfile.TemporaryDirectory(dir=privdir) as scandir:
        meson_cmd = [exename] + args
        build_cmd = [exename, '-o', logdir, detect_ninja(), '-C', scandir]
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
    tools = [
        'scan-build',  # base
        'scan-build-5.0', 'scan-build50',  # latest stable release
        'scan-build-4.0', 'scan-build40',  # old stable releases
        'scan-build-3.9', 'scan-build39',
        'scan-build-3.8', 'scan-build38',
        'scan-build-3.7', 'scan-build37',
        'scan-build-3.6', 'scan-build36',
        'scan-build-3.5', 'scan-build35',
        'scan-build-6.0', 'scan-build-devel',  # development snapshot
    ]
    toolname = 'scan-build'
    for tool in tools:
        try:
            p, out = Popen_safe([tool, '--help'])[:2]
        except (FileNotFoundError, PermissionError):
            continue
        if p.returncode != 0:
            continue
        else:
            toolname = tool
            break

    exename = os.environ.get('SCANBUILD', toolname)
    if not shutil.which(exename):
        print('Scan-build not installed.')
        return 1
    return scanbuild(exename, srcdir, blddir, privdir, logdir, meson_cmd)
