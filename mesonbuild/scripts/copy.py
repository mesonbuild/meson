# SPDX-License-Identifier: Apache-2.0
# Copyright © 2021-2023 Intel Corporation
from __future__ import annotations

"""Helper script to copy files at build time.

This is easier than trying to detect whether to use copy, cp, or something else.
"""

import os
import shutil
import typing as T


def run(args: T.List[str]) -> int:
    try:
        # The destination may be in a subdirectory that does not exist yet (for
        # example when copying structured sources into the build tree). Ninja
        # creates output directories on its own, but other backends do not, so
        # make sure the destination directory exists.
        os.makedirs(os.path.dirname(args[1]) or '.', exist_ok=True)
        shutil.copy2(args[0], args[1])
    except Exception:
        return 1
    return 0
