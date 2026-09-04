# SPDX-License-Identifier: Apache-2.0
# Copyright © 2021-2023 Intel Corporation

"""Helper script to copy files at build time.

This is easier than trying to detect whether to use copy, cp, or something else.
"""

from __future__ import annotations

import shutil


def run(args: list[str]) -> int:
    try:
        shutil.copy2(args[0], args[1])
    except Exception:
        return 1
    return 0
