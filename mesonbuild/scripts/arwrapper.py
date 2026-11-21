# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson development team

from __future__ import annotations

'''Delete the archive given as first argument and execute
the archiver given in the rest of the arguments.'''

import os, subprocess, sys
import typing as T

def run(args: T.List[str]) -> int:
    archive = args[0]
    command = args[1:]

    try:
        os.unlink(archive)
    except FileNotFoundError:
        pass
    return subprocess.call(command)

if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
