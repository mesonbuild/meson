#!/usr/bin/env python3

from __future__ import annotations
import argparse
import os
import stat
import typing as T

if T.TYPE_CHECKING:
    from typing_extensions import Protocol

    class Args(Protocol):
        source: str
        dest: T.Optional[str]
        build_mode: T.Optional[str]


def permit_osx_workaround(m1: int,  m2: int) -> bool:
    import platform
    if platform.system().lower() != 'darwin':
        return False
    if m2 % 10000 != 0:
        return False
    if m1//10000 != m2//10000:
        return False
    return True

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('dest', nargs='?', default=None)
    parser.add_argument('--build-mode', action='store', default=None)
    args: Args = parser.parse_args()

    if not args.dest:
        assert os.path.exists(args.source)
        check = args.source
    else:
        m1 = os.stat(args.source).st_mtime_ns
        m2 = os.stat(args.dest).st_mtime_ns
        # Compare only os.stat()
        if m1 != m2:
            # Under macOS the lower four digits sometimes get assigned
            # zero, even though shutil.copy2 should preserve metadata.
            # Just have to accept it, I guess.
            if not permit_osx_workaround(m1, m2):
                raise RuntimeError(f'mtime of {args.source!r} ({m1!r}) != mtime of {args.dest!r} ({m2!r})')
        import filecmp
        if not filecmp.cmp(args.source, args.dest):
            raise RuntimeError(f'{args.source!r} != {args.dest!r}')
        check = args.dest

    if args.build_mode:
        mode = oct(os.stat(check).st_mode)[-3:]
        assert mode == args.build_mode, f'{mode} == {args.build_mode}'


if __name__ == "__main__":
    main()
