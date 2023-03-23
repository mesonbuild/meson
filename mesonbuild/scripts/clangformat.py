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
import shutil
import shlex
from pathlib import Path

from . import run_tool
from ..compilers import cpp_suffixes, c_suffixes
from ..environment import detect_clangformat
from ..mesonlib import Popen_safe
from .. import mlog
import typing as T

def add_arguments(parser: 'argparse.ArgumentParser') -> None:
    parser.add_argument('--check', action='store_true',
                        help='Dry run, print diff and return an error if any file needs reformatting.')
    parser.add_argument('--sourcedir', default='.',
                        help='The source directory (Optional if files are specified).')
    parser.add_argument('--builddir', default=None,
                        help='Directory to ignore, usually the build directory (Optional).')
    parser.add_argument('--tool', default=None,
                        help='Command to reformat a single file passed as extra argument. ' +
                             'Must print formatted file on stdout. (Default clang-format).')
    parser.add_argument('files', nargs='*', type=Path,
                        help='Files to reformat (defaults to all source files).')

def run_formatter(fname: Path, exelist: T.List[str], check: bool) -> int:
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

def run_cli(options: T.Any) -> int:
    '''Run from "meson format"'''
    if options.tool:
        exelist = shlex.split(options.tool)
        name = Path(exelist[0]).stem
        argv0 = shutil.which(exelist[0])
        if not argv0:
            mlog.error(f'Could not find {options.tool}')
            return 1
        exelist = [argv0] + exelist[1:]
    else:
        name = 'clang-format'
        exelist = detect_clangformat()
        if not exelist:
            mlog.error(f'Could not find {name}')
            return 1
        exelist.append('-style=file')

    if options.files:
        globs = [options.files]
        ignore: T.Set[str] = set()
    else:
        srcdir = Path(options.sourcedir)
        globs, ignore = run_tool.defaults(name, srcdir)
        if options.builddir:
            ignore.add(str(Path(options.builddir, '*')))

    suffixes = c_suffixes | cpp_suffixes
    return run_tool.run(globs, ignore, suffixes, run_formatter, exelist, options.check)

def run(args: T.List[str]) -> int:
    '''Run from "ninja clang-format"'''
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    options = parser.parse_args(args)
    return run_cli(options)
