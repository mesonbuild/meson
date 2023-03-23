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
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from ..compilers import cpp_suffixes, c_suffixes
from . import run_tool
import typing as T

def run_clang_tidy(fname: Path, builddir: Path) -> int:
    return subprocess.run(['clang-tidy', '-p', str(builddir), str(fname)]).returncode

def run(args: T.List[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--sourcedir')
    parser.add_argument('--builddir')
    options = parser.parse_args(args)

    srcdir = Path(options.sourcedir)
    builddir = Path(options.builddir)

    globs, ignore = run_tool.defaults('clang-tidy', srcdir)
    ignore.add(str(builddir / '*'))
    suffixes = c_suffixes | cpp_suffixes
    return run_tool.run(globs, ignore, suffixes, run_clang_tidy, builddir)
