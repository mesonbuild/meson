# SPDX-License-Identifier: Apache-2.0
# Copyright 2012-2019 The Meson development team

"""Representations specific to the Texas Instruments compiler family."""

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

ti_optimization_args: dict[str, list[str]] = {
    'plain': [],
    '0': ['-O0'],
    'g': ['-Ooff'],
    '1': ['-O1'],
    '2': ['-O2'],
    '3': ['-O3'],
    's': ['-O4']
}

ti_debug_args: dict[bool, list[str]] = {
    False: [],
    True: ['-g']
}


class TICompiler(Compiler):

    id = 'ti'

    if T.TYPE_CHECKING:
        # Older versions of mypy can't figure this out for some reason.
        is_cross: bool

    def __init__(self) -> None:
        if not self.is_cross:
            raise EnvironmentException('TI compilers only support cross-compilation.')

        self.can_compile_suffixes.add('asm')    # Assembly
        self.can_compile_suffixes.add('cla')    # Control Law Accelerator (CLA) used in C2000

        default_warn_args: list[str] = []
        self.warn_args: dict[str, list[str]] = {
            '0': [],
            '1': default_warn_args,
            '2': default_warn_args + [],
            '3': default_warn_args + [],
            'everything': default_warn_args + []}

    def get_pic_args(self) -> list[str]:
        # PIC support is not enabled by default for TI compilers,
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
        return ti_optimization_args[optimization_level]

    def get_debug_args(self, is_debug: bool) -> list[str]:
        return ti_debug_args[is_debug]

    def get_compile_only_args(self) -> list[str]:
        return []

    def get_no_optimization_args(self) -> list[str]:
        return ['-Ooff']

    def get_output_args(self, outputname: str) -> list[str]:
        return [f'--output_file={outputname}']

    def get_werror_args(self) -> list[str]:
        return ['--emit_warnings_as_errors']

    def get_include_args(self, path: str, is_system: bool) -> list[str]:
        if path == '':
            path = '.'
        return ['-I' + path]

    @classmethod
    def _unix_args_to_native(cls, args: list[str], info: MachineInfo) -> list[str]:
        result: list[str] = []
        for i in args:
            if i.startswith('-Wl,-rpath='):
                continue
            if i == '--print-search-dirs':
                continue
            if i.startswith('-L'):
                continue
            result.append(i)
        return result

    def compute_parameters_with_absolute_paths(self, parameter_list: list[str], build_dir: str) -> list[str]:
        for idx, i in enumerate(parameter_list):
            if i[:15] == '--include_path=':
                parameter_list[idx] = i[:15] + os.path.normpath(os.path.join(build_dir, i[15:]))
            if i[:2] == '-I':
                parameter_list[idx] = i[:2] + os.path.normpath(os.path.join(build_dir, i[2:]))

        return parameter_list

    def get_dependency_gen_args(self, outtarget: str, outfile: str) -> list[str]:
        return ['--preproc_with_compile', f'--preproc_dependency={outfile}']
