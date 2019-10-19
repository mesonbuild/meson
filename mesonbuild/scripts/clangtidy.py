# Copyright 2019 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pathlib
import subprocess
import shutil
from concurrent.futures import ThreadPoolExecutor

from ..compilers import lang_suffixes

def manual_clangformat(srcdir_name, builddir_name):
    srcdir = pathlib.Path(srcdir_name)
    suffixes = set(lang_suffixes['c']).union(set(lang_suffixes['cpp']))
    suffixes.add('h')
    futures = []
    returncode = 0
    with ThreadPoolExecutor() as e:
        for f in (x for suff in suffixes for x in srcdir.glob('**/*.' + suff)):
            strf = str(f)
            if strf.startswith(builddir_name):
                continue
            futures.append(e.submit(subprocess.run, ['clang-tidy', '-p', builddir_name, strf]))
        [max(returncode, x.result().returncode) for x in futures]
    return returncode

def clangformat(srcdir_name, builddir_name):
    run_clang_tidy = None
    for rct in ('run-clang-tidy', 'run-clang-tidy.py'):
        if shutil.which(rct):
            run_clang_tidy = rct
            break
    if run_clang_tidy:
        return subprocess.run([run_clang_tidy, '-p', builddir_name]).returncode
    else:
        print('Could not find run-clang-tidy, running checks manually.')
        manual_clangformat(srcdir_name, builddir_name)

def run(args):
    srcdir_name = args[0]
    builddir_name = args[1]
    return clangformat(srcdir_name, builddir_name)
