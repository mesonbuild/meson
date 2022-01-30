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

import shutil
import re
import os
import argparse
import subprocess
from pathlib import Path

from .run_tool import run_tool
import typing as T

def run_clang_tidy(fname: Path, builddir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(['clang-tidy', '-p', str(builddir), str(fname)])
    
def clangtidy(srcdir: Path, builddir: Path) -> int:
    run_clang_tidy_exist = None
    for rct in ('run-clang-tidy', 'run-clang-tidy.py'):
        if shutil.which(rct):
            run_clang_tidy_exist = rct
            break
    if run_clang_tidy_exist:
        builddir_name =  str(builddir)
        return subprocess.run([run_clang_tidy_exist, '-p', builddir_name, '^(?!' + re.escape(builddir_name + os.path.sep) + ').*$']).returncode
    else:
        print('Could not find run-clang-tidy, running checks manually.')
        return run_tool('clang-tidy', srcdir, builddir, run_clang_tidy, builddir)

def run(args: T.List[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('sourcedir')
    parser.add_argument('builddir')
    options = parser.parse_args(args)

    srcdir = Path(options.sourcedir)
    builddir = Path(options.builddir)
    
    return clangtidy(srcdir, builddir)

