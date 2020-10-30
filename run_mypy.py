#!/usr/bin/env python3

import sys
import subprocess
import argparse
from pathlib import Path
import typing as T

modules = [
    # fully typed submodules
    'mesonbuild/ast',
    'mesonbuild/cmake',
    'mesonbuild/compilers',
    'mesonbuild/scripts',
    'mesonbuild/wrap',

    # specific files
    'mesonbuild/_pathlib.py',
    'mesonbuild/arglist.py',
    # 'mesonbuild/coredata.py',
    'mesonbuild/dependencies/boost.py',
    'mesonbuild/dependencies/hdf5.py',
    'mesonbuild/dependencies/mpi.py',
    'mesonbuild/envconfig.py',
    'mesonbuild/interpreterbase.py',
    'mesonbuild/linkers.py',
    'mesonbuild/mcompile.py',
    'mesonbuild/mesonlib.py',
    'mesonbuild/minit.py',
    'mesonbuild/mintro.py',
    'mesonbuild/mlog.py',
    'mesonbuild/modules/fs.py',
    'mesonbuild/mparser.py',
    'mesonbuild/msetup.py',
    'mesonbuild/mtest.py',

    'run_mypy.py',
    'tools'
]

def check_mypy() -> None:
    try:
        import mypy
    except ImportError:
        print('Failed import mypy')
        sys.exit(1)

def main() -> int:
    check_mypy()

    root = Path(__file__).absolute().parent
    args = []  # type: T.List[str]

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('-p', '--pretty', action='store_true', help='pretty print mypy errors')
    parser.add_argument('-C', '--clear', action='store_true', help='clear the terminal before running mypy')

    opts = parser.parse_args()
    if opts.pretty:
        args.append('--pretty')

    if opts.clear:
        print('\x1bc', end='', flush=True)

    print('Running mypy (this can take some time) ...')
    p = subprocess.run(
        [sys.executable, '-m', 'mypy'] + args + modules,
        cwd=root,
    )
    return p.returncode

if __name__ == '__main__':
    sys.exit(main())
