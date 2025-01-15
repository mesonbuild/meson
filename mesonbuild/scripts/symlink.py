# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 Marco Rebhan <me@dblsaiko.net>

from __future__ import annotations

"""
Helper script to link files at build time.
"""

import os
import typing as T


def run(args: T.List[str]) -> int:
    if len(args) != 2:
        return 1

    src, dst = args

    try:
        try:
            os.remove(dst)
        except FileNotFoundError:
            pass

        os.symlink(src, dst)
    except OSError as e:
        print(f'symlink: cannot create link \'{dst}\' -> \'{src}\': {e.strerror}')
        return 1

    return 0
