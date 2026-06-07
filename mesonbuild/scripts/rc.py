# SPDX-License-Identifier: Apache-2.0

"""Wrapper for manually generating depfiles of resource files."""

from __future__ import annotations

import argparse
import subprocess
import sys
import typing as T


parser = argparse.ArgumentParser()
parser.add_argument('--rc', nargs='+', required=True)
parser.add_argument('--cl', nargs='+', required=True)
parser.add_argument('--Xarg', action='append')


def run(args: T.List[str]) -> int:
    options, rc_args = parser.parse_known_args(args)
    target = rc_args[-1] if rc_args else None

    rc = options.rc
    cl = options.cl

    # Use preprocessor to display include files
    include_args = [a for a in rc_args if a.startswith(('/I', '-I'))]
    cmd = [*cl, *include_args, *options.Xarg]
    if target:
        cmd += [target]
    result = subprocess.call(cmd, stdout=subprocess.DEVNULL)
    if result != 0:
        print('Error running preprocessor to find resource dependencies', file=sys.stderr)
        # continue anyway. the resource compiler should catch the error later

    cmd = [*rc, *rc_args]
    return subprocess.call(cmd)
