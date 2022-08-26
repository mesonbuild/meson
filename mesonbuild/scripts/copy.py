# SPDX-License-Identifer: Apache-2.0
# Copyright © 2021 Intel Corporation

"""Helper script to copy files at build time.

This is easier than trying to detect whether to use copy, cp, or something else.
"""

from __future__ import annotations

import argparse
import shutil
import typing as T

if T.TYPE_CHECKING:
    from typing_extensions import Protocol

    class Args(Protocol):
        source: str
        dest: str


def run(raw_args: T.List[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('dest')
    args: Args = parser.parse_args(raw_args)

    try:
        shutil.copy2(args.source, args.dest)
    except Exception:
        return 1
    return 0
