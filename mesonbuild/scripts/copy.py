# SPDX-License-Identifer: Apache-2.0
# Copyright © 2021 Intel Corporation

"""Helper script to copy files at build time.

This is easier than trying to detect whether to use copy, cp, or something else.
"""

from __future__ import annotations

import argparse
import os
import shutil
import typing as T

if T.TYPE_CHECKING:
    from typing_extensions import Protocol

    class Args(Protocol):
        source: str
        dest: str
        file_mode: int


def run(raw_args: T.List[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('dest')
    parser.add_argument('--file-mode', action='store', help='permission bits as suitable to pass to `os.chmod`', type=int)
    args: Args = parser.parse_args(raw_args)

    try:
        shutil.copy2(args.source, args.dest)
        if args.file_mode:
            os.chmod(args.dest, args.file_mode)
    except Exception:
        return 1
    return 0
