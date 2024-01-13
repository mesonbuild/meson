# SPDX-License-Identifier: Apache-2.0
# Copyright 2012-2024 The Meson development team

from __future__ import annotations

import typing as T

from ..mesonlib import EnvironmentException
from .compilers import CompileCheckMode, Compiler

if T.TYPE_CHECKING:
    from ..envconfig import MachineInfo
    from ..environment import Environment
    from ..mesonlib import MachineChoice

class OrcCompiler(Compiler):

    language = 'orc'
    id = 'orcc'

    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice,
                 is_cross: bool, info: 'MachineInfo'):
        super().__init__([], exelist, version, for_machine, info, is_cross=is_cross)
        self.version = version

    def needs_static_linker(self) -> bool:
        return False # Because compiles into C.

    def get_optimization_args(self, optimization_level: str) -> T.List[str]:
        return []

    def get_debug_args(self, is_debug: bool) -> T.List[str]:
        return []

    def get_output_args(self, outputname: str) -> T.List[str]:
        return ['-o', outputname]

    def get_compile_only_args(self) -> T.List[str]:
        return [] # Because compiles into C.

    def get_pic_args(self) -> T.List[str]:
        return []

    def get_pie_args(self) -> T.List[str]:
        return []

    def get_pie_link_args(self) -> T.List[str]:
        return []

    def get_always_args(self) -> T.List[str]:
        return []

    def get_warn_args(self, level: str) -> T.List[str]:
        return []

    def get_werror_args(self) -> T.List[str]:
        return []

    def unix_args_to_native(self, args: T.List[str]) -> T.List[str]:
        # Revert the args as orc the arguments are first and finally the source
        rev = args[1:] + args[:1]
        return super().unix_args_to_native(rev)

    def sanity_check(self, work_dir: str, environment: 'Environment') -> None:
        code = '.function orcSanitiyCheck'
        extra_flags: T.List[str] = []
        extra_flags += environment.coredata.get_external_args(self.for_machine, self.language)

        with self.cached_compile(code, environment.coredata, extra_args=extra_flags, mode=CompileCheckMode.COMPILE) as p:
            if p.returncode != 0:
                msg = f'Orc compiler {self.name_string()!r} cannot compile programs'
                raise EnvironmentException(msg)

    def thread_flags(self, env: 'Environment') -> T.List[str]:
        return []

    def thread_link_flags(self, env: 'Environment') -> T.List[str]:
        return []
