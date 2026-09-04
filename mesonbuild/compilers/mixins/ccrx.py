# SPDX-License-Identifier: Apache-2.0
# Copyright 2012-2019 The Meson development team

"""Representations specific to the Renesas CC-RX compiler family."""

from __future__ import annotations

import os
import typing as T

from ...mesonlib import EnvironmentException

if T.TYPE_CHECKING:
    from ...compilers.compilers import Compiler
    from ...envconfig import MachineInfo
else:
    # This is a bit clever, for mypy we pretend that these mixins descend from
    # Compiler, so we get all of the methods and attributes defined for us, but
    # for runtime we make them descend from object (which all classes normally
    # do). This gives up DRYer type checking, with no runtime impact
    Compiler = object

ccrx_optimization_args: dict[str, list[str]] = {
    '0': ['-optimize=0'],
    'g': ['-optimize=0'],
    '1': ['-optimize=1'],
    '2': ['-optimize=2'],
    '3': ['-optimize=max'],
    's': ['-optimize=2', '-size']
}

ccrx_debug_args: dict[bool, list[str]] = {
    False: [],
    True: ['-debug']
}


class CcrxCompiler(Compiler):

    if T.TYPE_CHECKING:
        is_cross = True

    id = 'ccrx'

    def __init__(self) -> None:
        if not self.is_cross:
            raise EnvironmentException('ccrx supports only cross-compilation.')
        # Assembly
        self.can_compile_suffixes.add('src')
        default_warn_args: list[str] = []
        self.warn_args: dict[str, list[str]] = {
            '0': [],
            '1': default_warn_args,
            '2': default_warn_args + [],
            '3': default_warn_args + [],
            'everything': default_warn_args + []}

    def get_pic_args(self) -> list[str]:
        # PIC support is not enabled by default for CCRX,
        # if users want to use it, they need to add the required arguments explicitly
        return []

    def get_pch_suffix(self) -> str:
        return 'pch'

    def get_pch_use_args(self, pch_dir: str, header: str) -> list[str]:
        return []

    def thread_flags(self) -> list[str]:
        return []

    def get_coverage_args(self) -> list[str]:
        return []

    def get_no_stdinc_args(self) -> list[str]:
        return []

    def get_no_stdlib_link_args(self) -> list[str]:
        return []

    def get_optimization_args(self, optimization_level: str) -> list[str]:
        return ccrx_optimization_args[optimization_level]

    def get_debug_args(self, is_debug: bool) -> list[str]:
        return ccrx_debug_args[is_debug]

    @classmethod
    def _unix_args_to_native(cls, args: list[str], info: MachineInfo) -> list[str]:
        result: list[str] = []
        for i in args:
            if i.startswith('-D'):
                i = '-define=' + i[2:]
            if i.startswith('-I'):
                i = '-include=' + i[2:]
            if i.startswith('-Wl,-rpath='):
                continue
            elif i == '--print-search-dirs':
                continue
            elif i.startswith('-L'):
                continue
            elif not i.startswith('-lib=') and i.endswith(('.a', '.lib')):
                i = '-lib=' + i
            result.append(i)
        return result

    def compute_parameters_with_absolute_paths(self, parameter_list: list[str], build_dir: str) -> list[str]:
        for idx, i in enumerate(parameter_list):
            if i[:9] == '-include=':
                parameter_list[idx] = i[:9] + os.path.normpath(os.path.join(build_dir, i[9:]))

        return parameter_list
