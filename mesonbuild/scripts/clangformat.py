# Copyright 2018 The Meson development team

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
from concurrent.futures import ThreadPoolExecutor

from ..compilers import lang_suffixes

def clangformat(srcdir_name, builddir_name):
    srcdir = pathlib.Path(srcdir_name)
    suffixes = set(lang_suffixes['c']).union(set(lang_suffixes['cpp']))
    futures = []
    with ThreadPoolExecutor() as e:
        for f in (x for suff in suffixes for x in srcdir.glob('**/*.' + suff)):
            strf = str(f)
            if strf.startswith(builddir_name):
                continue
            futures.append(e.submit(subprocess.check_call, ['clang-format', '-style=file', '-i', strf]))
        [x.result() for x in futures]
    return 0

def run(args):
    srcdir_name = args[0]
    builddir_name = args[1]
    return clangformat(srcdir_name, builddir_name)
