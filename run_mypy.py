#!/usr/bin/env python3

import sys
import subprocess
import argparse
from pathlib import Path
import typing as T


def check_mypy() -> None:
    try:
        import mypy
    except ImportError:
        raise SystemExit('Failed import mypy')

def main() -> int:
    check_mypy()

    root = Path(__file__).absolute().parent
    args: T.List[str] = []

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
        [sys.executable, '-m', 'mypy'] + args,
        cwd=root,
    )
    return p.returncode

if __name__ == '__main__':
    raise SystemExit(main())
