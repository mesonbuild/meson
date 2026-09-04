# SPDX-License-Identifier: Apache-2.0
# Copyright 2025-2026 The Meson development team

"""Representations specific to the Small Device C Compiler (SDCC)."""

from __future__ import annotations

import os
import typing as T

if T.TYPE_CHECKING:
    from ...build import BuildTarget
    from ...compilers.compilers import Compiler
else:
    Compiler = object

sdcc_optimization_args: dict[str, list[str]] = {
    'plain': [],
    '0': [],
    'g': [],
    '1': [],
    '2': ['--opt-code-speed'],
    '3': ['--opt-code-speed'],
    's': ['--opt-code-size'],
}

sdcc_debug_args: dict[bool, list[str]] = {
    False: [],
    True: ['--debug'],
}


class SdccCompiler(Compiler):

    id = 'sdcc'

    def __init__(self) -> None:
        self.warn_args: dict[str, list[str]] = {
            '0': [],
            '1': [],
            '2': [],
            '3': [],
            'everything': [],
        }

    def get_always_args(self) -> list[str]:
        return []

    def get_pic_args(self) -> list[str]:
        return []

    def get_dependency_gen_args(self, outtarget: str, outfile: str) -> list[str]:
        # SDCC's own -M flags suppress codegen; -Wp routes them to sdcpp, which also compiles.
        return ['-Wp,-MD', '-Wp,-MF', '-Wp,' + outfile, '-Wp,-MQ', '-Wp,' + outtarget]

    def get_no_optimization_args(self) -> list[str]:
        return []

    def get_object_suffix(self, target: BuildTarget, source: str) -> str:
        return 'rel'

    def _sanity_check_filenames(self) -> tuple[str, str | None, str]:
        cross_or_not = '_cross' if self.is_cross else ''
        return ('sanity_check_for_c.c', None, f'sanity_check_for_c{cross_or_not}.ihx')

    def get_optimization_args(self, optimization_level: str) -> list[str]:
        return sdcc_optimization_args[optimization_level]

    def get_debug_args(self, is_debug: bool) -> list[str]:
        return sdcc_debug_args[is_debug]

    def get_preprocess_only_args(self) -> list[str]:
        return ['-E']

    def get_werror_args(self) -> list[str]:
        return ['--Werror']

    def get_no_stdinc_args(self) -> list[str]:
        return ['--nostdinc']

    def get_no_stdlib_link_args(self) -> list[str]:
        return ['--nostdlib']

    def get_include_args(self, path: str, is_system: bool) -> list[str]:
        if not path:
            path = '.'
        return ['-I' + path]

    def thread_flags(self) -> list[str]:
        return []

    def compute_parameters_with_absolute_paths(self, parameter_list: list[str],
                                               build_dir: str) -> list[str]:
        for idx, i in enumerate(parameter_list):
            if i[:2] in {'-I', '-L'}:
                parameter_list[idx] = i[:2] + os.path.normpath(os.path.join(build_dir, i[2:]))
        return parameter_list
