#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T

from mesonbuild import build
from mesonbuild.mesonlib import File


def determine_key(obj: T.Any) -> T.Optional[str]:
    canonical_string: T.Optional[str] = None
    if isinstance(obj, build.IncludeDirs):
        canonical_string = '|'.join([
            obj.curdir,
            ','.join(sorted(obj.incdirs)),
            str(obj.is_system),
            ','.join(sorted(obj.extra_build_dirs)),
        ])
    elif isinstance(obj, str):
        canonical_string = obj
    elif isinstance(obj, File):
        canonical_string = obj.subdir + obj.fname

    return canonical_string


class ConvertInterpreterInfo:
    """Holds assignment data gathered by the `ConvertInterpreter`.

    For example, for an assignment like `inc_data = include_directories('data')`,
    this class tracks the name 'inc_data' and associates it with the
    corresponding Meson `IncludeDirs` object.
    """

    def __init__(self) -> None:
        self.assignments: T.Dict[str, T.Tuple[str, str]] = {}

    def assign(self, name: str, subdir: str, obj: T.Any) -> None:
        key = determine_key(obj)
        if key not in self.assignments:
            self.assignments[key] = (name, subdir)

    def lookup_assignment(self, obj: T.Any) -> T.Optional[str]:
        key = determine_key(obj)
        if key in self.assignments:
            return self.assignments[key][0]

        return None

    def lookup_full_assignment(self, obj: T.Any) -> T.Optional[T.Tuple[str, str]]:
        key = determine_key(obj)
        if key in self.assignments:
            return self.assignments[key]

        return None
