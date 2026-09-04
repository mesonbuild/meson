# SPDX-License-Identifier: Apache-2.0
# Copyright 2012-2019 The Meson development team

"""Representations specific to the CompCert C compiler family."""

from __future__ import annotations

import os
import re
import typing as T

if T.TYPE_CHECKING:
    from ...compilers.compilers import Compiler
    from ...envconfig import MachineInfo
else:
    # This is a bit clever, for mypy we pretend that these mixins descend from
    # Compiler, so we get all of the methods and attributes defined for us, but
    # for runtime we make them descend from object (which all classes normally
    # do). This gives up DRYer type checking, with no runtime impact
    Compiler = object

ccomp_optimization_args: dict[str, list[str]] = {
    'plain': [],
    '0': ['-O0'],
    'g': ['-O0'],
    '1': ['-O1'],
    '2': ['-O2'],
    '3': ['-O3'],
    's': ['-Os']
}

ccomp_debug_args: dict[bool, list[str]] = {
    False: [],
    True: ['-g']
}

# As of CompCert 20.04, these arguments should be passed to the underlying gcc linker (via -WUl,<arg>)
# There are probably (many) more, but these are those used by picolibc
ccomp_args_to_wul: list[str] = [
        r"^-ffreestanding$",
        r"^-r$"
]

class CompCertCompiler(Compiler):

    id = 'ccomp'

    def __init__(self) -> None:
        # Assembly
        self.can_compile_suffixes.add('s')
        self.can_compile_suffixes.add('sx')
        default_warn_args: list[str] = []
        self.warn_args: dict[str, list[str]] = {
            '0': [],
            '1': default_warn_args,
            '2': default_warn_args + [],
            '3': default_warn_args + [],
            'everything': default_warn_args + []}

    def get_always_args(self) -> list[str]:
        return []

    def get_pic_args(self) -> list[str]:
        # As of now, CompCert does not support PIC
        return []

    def get_pch_suffix(self) -> str:
        return 'pch'

    def get_pch_use_args(self, pch_dir: str, header: str) -> list[str]:
        return []

    @classmethod
    def _unix_args_to_native(cls, args: list[str], info: MachineInfo) -> list[str]:
        "Always returns a copy that can be independently mutated"
        patched_args: list[str] = []
        for arg in args:
            added = 0
            for ptrn in ccomp_args_to_wul:
                if re.match(ptrn, arg):
                    patched_args.append('-WUl,' + arg)
                    added = 1
            if not added:
                patched_args.append(arg)
        return patched_args

    def thread_flags(self) -> list[str]:
        return []

    def get_preprocess_only_args(self) -> list[str]:
        return ['-E']

    def get_compile_only_args(self) -> list[str]:
        return ['-c']

    def get_coverage_args(self) -> list[str]:
        return []

    def get_no_stdinc_args(self) -> list[str]:
        return ['-nostdinc']

    def get_no_stdlib_link_args(self) -> list[str]:
        return ['-nostdlib']

    def get_optimization_args(self, optimization_level: str) -> list[str]:
        return ccomp_optimization_args[optimization_level]

    def get_debug_args(self, is_debug: bool) -> list[str]:
        return ccomp_debug_args[is_debug]

    def compute_parameters_with_absolute_paths(self, parameter_list: list[str], build_dir: str) -> list[str]:
        for idx, i in enumerate(parameter_list):
            if i[:9] == '-I':
                parameter_list[idx] = i[:9] + os.path.normpath(os.path.join(build_dir, i[9:]))

        return parameter_list
