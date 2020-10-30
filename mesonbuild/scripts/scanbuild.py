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

import subprocess
import shutil
import tempfile
from ..environment import detect_ninja, detect_scanbuild
from pathlib import Path
import typing as T


def scanbuild(exelist: T.List[str], srcdir: Path, blddir: Path, privdir: Path, logdir: Path, args: T.List[str]) -> int:
    with tempfile.TemporaryDirectory(dir=str(privdir)) as scandir:
        meson_cmd = exelist + args
        build_cmd = exelist + ['-o', str(logdir)] + detect_ninja() + ['-C', scandir]
        rc = subprocess.call(meson_cmd + [str(srcdir), scandir])
        if rc != 0:
            return rc
        return subprocess.call(build_cmd)


def run(args: T.List[str]) -> int:
    srcdir = Path(args[0])
    blddir = Path(args[1])
    meson_cmd = args[2:]
    privdir = blddir / 'meson-private'
    logdir = blddir / 'meson-logs' / 'scanbuild'
    shutil.rmtree(str(logdir), ignore_errors=True)

    exelist = detect_scanbuild()
    if not exelist:
        print('Could not execute scan-build "%s"' % ' '.join(exelist))
        return 1

    return scanbuild(exelist, srcdir, blddir, privdir, logdir, meson_cmd)
