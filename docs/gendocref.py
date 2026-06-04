#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2021 The Meson development team

from mesonbuild import build
import inspect

if __name__ == '__main__':
    for member in inspect.getmembers(build):
        print(f"{member[0]} {member[1]}")
