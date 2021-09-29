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

import argparse
import subprocess
import itertools
import fnmatch
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from ..environment import detect_clangformat
from ..compilers import lang_suffixes
import typing as T

def parse_pattern_file(fname: Path) -> T.List[str]:
    patterns = []
    try:
        with fname.open(encoding='utf-8') as f:
            for line in f:
                pattern = line.strip()
                if pattern and not pattern.startswith('#'):
                    patterns.append(pattern)
    except FileNotFoundError:
        pass
    return patterns

def run_clang_format(exelist: T.List[str], fname: Path, check: bool) -> subprocess.CompletedProcess:
    if check:
        original = fname.read_bytes()
    before = fname.stat().st_mtime
    args = ['-style=file', '-i', str(fname)]
    ret = subprocess.run(exelist + args)
    after = fname.stat().st_mtime
    if before != after:
        print('File reformatted: ', fname)
        if check:
            # Restore the original if only checking.
            fname.write_bytes(original)
            ret.returncode = 1
    return ret

def clangformat(exelist: T.List[str], srcdir: Path, builddir: Path, check: bool) -> int:
    patterns = parse_pattern_file(srcdir / '.clang-format-include')
    if not patterns:
        patterns = ['**/*']
    globs = [srcdir.glob(p) for p in patterns]
    patterns = parse_pattern_file(srcdir / '.clang-format-ignore')
    ignore = [str(builddir / '*')]
    ignore.extend([str(srcdir / p) for p in patterns])
    suffixes = set(lang_suffixes['c']).union(set(lang_suffixes['cpp']))
    suffixes.add('h')
    suffixes = {f'.{s}' for s in suffixes}
    futures = []
    returncode = 0
    with ThreadPoolExecutor() as e:
        for f in itertools.chain(*globs):
            strf = str(f)
            if f.is_dir() or f.suffix not in suffixes or \
                any(fnmatch.fnmatch(strf, i) for i in ignore):
                continue
            futures.append(e.submit(run_clang_format, exelist, f, check))
        returncode = max([x.result().returncode for x in futures])
    return returncode

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

    return clangformat(exelist, srcdir, builddir, options.check)
