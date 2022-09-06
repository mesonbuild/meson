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

# ignore all lints for this file, since it is run by python2 as well

# type: ignore
# pylint: disable=deprecated-module

import json, os, subprocess, sys
from compileall import compile_file

destdir = os.environ.get('DESTDIR')
quiet = int(os.environ.get('MESON_INSTALL_QUIET', 0))

def destdir_join(d1, d2):
    if not d1:
        return d2
    # c:\destdir + c:\prefix must produce c:\destdir\prefix
    parts = os.path.splitdrive(d2)
    return d1 + parts[1]

def compileall(files):
    for f in files:
        if destdir is not None:
            ddir = os.path.dirname(f)
            fullpath = destdir_join(destdir, f)
        else:
            ddir = None
            fullpath = f

        if os.path.isdir(fullpath):
            for root, _, files in os.walk(fullpath):
                ddir = os.path.dirname(os.path.splitdrive(f)[0] + root[len(destdir):])
                for dirf in files:
                    if dirf.endswith('.py'):
                        fullpath = os.path.join(root, dirf)
                        compile_file(fullpath, ddir, force=True, quiet=quiet)
        else:
            compile_file(fullpath, ddir, force=True, quiet=quiet)

def run(manifest):
    data_file = os.path.join(os.path.dirname(__file__), manifest)
    with open(data_file, 'rb') as f:
        dat = json.load(f)
    compileall(dat)

if __name__ == '__main__':
    manifest = sys.argv[1]
    run(manifest)
    if len(sys.argv) > 2:
        optlevel = int(sys.argv[2])
        # python2 only needs one or the other
        if optlevel == 1 or (sys.version_info >= (3,) and optlevel > 0):
            subprocess.check_call([sys.executable, '-O'] + sys.argv[:2])
        if optlevel == 2:
            subprocess.check_call([sys.executable, '-OO'] + sys.argv[:2])
