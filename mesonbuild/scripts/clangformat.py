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
from __future__ import annotations

import argparse
import difflib
from pathlib import Path

from .run_tool import run_tool
from ..environment import detect_clangformat
from ..mesonlib import Popen_safe
from .. import mlog
import typing as T

def run_clang_format(fname: Path, exelist: T.List[str], check: bool) -> int:
    cmd = exelist + [str(fname)]
    try:
        p, o, e = Popen_safe(cmd)
    except UnicodeDecodeError as e:
        mlog.warning(f'Cannot format {str(fname)}: {str(e)}')
        return 1
    if p.returncode != 0:
        return p.returncode

    original = fname.read_text(encoding='utf-8')
    if check:
        old = original.splitlines(keepends=True)
        new = o.splitlines(keepends=True)
        diff = difflib.unified_diff(old, new,
                                    fromfile=f'{fname}\t(original)',
                                    tofile=f'{fname}\t(reformatted)')
        lines = []
        for l in diff:
            if l.startswith('---') or l.startswith('+++'):
                lines.append(mlog.bold(l))
            elif l.startswith('@@'):
                lines.append(mlog.cyan(l))
            elif l.startswith('+'):
                lines.append(mlog.green(l))
            elif l.startswith('-'):
                lines.append(mlog.red(l))
            else:
                lines.append(l)
        if lines:
            mlog.log(*lines, sep='')
            return 1
    elif o != original:
        fname.write_text(o, encoding='utf-8')
        mlog.log('File reformatted:', fname)

    return 0

def run(args: T.List[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('sourcedir')
    parser.add_argument('builddir')
    options = parser.parse_args(args)

    srcdir = Path(options.sourcedir)
    builddir = Path(options.builddir)

    exelist = detect_clangformat()
    if not exelist:
        print('Could not execute clang-format "%s"' % ' '.join(exelist))
        return 1

    return run_tool('clang-format', srcdir, builddir, run_clang_format, exelist, options.check)
