# SPDX-License-Identifier: Apache-2.0

"""Wrapper for manually generating depfiles of resource files."""

from __future__ import annotations

import argparse
import subprocess
import sys
import typing as T


parser = argparse.ArgumentParser()
parser.add_argument('--cl', required=True)
parser.add_argument('--Xarg', action='append')


def run(args: T.List[str]) -> int:
    # --rc is not a real argument, everything after it is kept verbatim
    sep = args.index('--rc')
    options = parser.parse_args(args[:sep])
    rc, *rc_args = args[sep + 1:]
    target = rc_args[-1] if rc_args else None

    # Use preprocessor to display include files
    include_args = [a for a in rc_args if a.startswith(('/I', '-I'))]
    cmd = [options.cl, *include_args, *options.Xarg]
    if target:
        cmd += [target]
    result = subprocess.call(cmd, stdout=subprocess.DEVNULL)
    if result != 0:
        print('Error running preprocessor to find resource dependencies', file=sys.stderr)
        # continue anyway. the resource compiler should catch the error later

    cmd = [rc, *rc_args]
    return subprocess.call(cmd)
