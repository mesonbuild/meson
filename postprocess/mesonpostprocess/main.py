#!/usr/bin/env python3

# Copyright 2020 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .modules import (
    FixUnusedImports,
    TypeHintsRemover,
    ConvertFStrings,
    CodeFormater,
    PostProcessBase,
)

from pathlib import Path
import argparse
import os
import shutil
import typing as T

SKIP_DIRS = [
    '__pycache__',
    '.mypy_cache', '.pytest_cache',
    '.git',
    '.dub', 'meson.egg-info',
    'meson/build', 'meson/dist',
    'meson-logs', 'meson-private',
    '.eggs',
    '.vscode', '.idea', '.cproject', '.pydevproject', '.project',
    'work area',
    'install dir'
]

def main() -> int:
    parser = argparse.ArgumentParser('Meson code post-processor')
    parser.add_argument('--all', '-a', action='store_true', help='Execute all actions')
    parser.add_argument('--verbose', '-V', action='count', default=0, help='Set verbose output level')
    parser.add_argument('out', metavar='DIR', type=str, help='Output directory for the converted files')
    args = parser.parse_args()

    actions: T.List[PostProcessBase] = []
    sources: T.List[T.Tuple[Path, Path]] = []
    ncopied = 0
    missing_imports: T.List[T.Tuple[str, str]] = []

    def add_action(a: PostProcessBase) -> None:
        nonlocal actions, missing_imports
        if not a.check():
            print(f'ERROR: Failed to load the {a.name} postprocessor')
            missing_imports += a.imports
        actions += [a]

    # Add post processors

    if missing_imports:
        print('')
        print('Failed to import the following modules:')
        for i in missing_imports:
            print(f'  - {i[0]:<12} url: {i[1]}')
        print('')
        print(f'Try: pip install {" ".join([x[0] for x in missing_imports])}')
        return 2

    meson_root = Path(__file__).parent.parent.parent.absolute()
    outdir = Path(args.out).absolute()
    if outdir.exists():
        print(f'ERROR: {outdir} already exists.')
        return 1

    print(f'Output will be written to {outdir}')
    print(f'Scanning files in {meson_root} ...')

    # Start by scanning the meson root
    for root, _, files in os.walk(meson_root):
        r_posix = Path(root).as_posix()
        if any({r_posix.endswith(f'/{x}') or f'/{x}/' in r_posix for x in SKIP_DIRS}):
            continue

        for f in files:
            src = Path(root, f)
            dst = Path(outdir, Path(root).relative_to(meson_root), f)

            # Always make sure the directory structure exists
            if not dst.parent.exists():
                dst.parent.mkdir(parents=True)

            if f.endswith('.py'):
                # Remember python files to convert
                sources += [(src, dst)]
            else:
                # Copy none python files
                if args.verbose >= 2:
                    print(f'  -- Copying {src.relative_to(meson_root)}')

                shutil.copy2(src, dst)
                ncopied += 1

    # Process python files
    print('Processing python files...')

    try:
        from tqdm import tqdm  # type: ignore
        src_iter: T.Iterable[T.Tuple[Path, Path]] = tqdm(sources, unit='files', leave=False)
    except ImportError:
        print('WARNING: Failed to import tqdm! ==> No progress bar.')
        src_iter = sources

    for src, dst in src_iter:
        raw = src.read_text()

        if args.verbose >= 1:
            print(f'  -- Processing {src.relative_to(meson_root)}')

        # Skip empty files
        if not raw:
            dst.touch(mode=src.stat().st_mode)
            continue

        for a in actions:
            new_str = a.apply(raw)
            if not new_str:
                print(f'ERROR: applying {a.name} returned an empty string for {src.relative_to(meson_root)}')
                continue
            raw = new_str

        dst.write_text(raw)
        dst.chmod(src.stat().st_mode)

    print(f'Done. Statistics:')
    print(f'  -- files processed: {len(sources)}')
    print(f'  -- files copied:    {ncopied}')
    print(f'  -- actions applied: {len(actions)}')
    return 0
