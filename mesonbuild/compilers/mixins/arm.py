# Copyright 2012-2019 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Representations specific to the arm family of compilers."""

import os
import typing

from ...mesonlib import EnvironmentException
from ..compilers import clike_debug_args

if typing.TYPE_CHECKING:
    from ..compilers import CompilerType
    from ...environment import Environment

arm_buildtype_args = {
    'plain': [],
    'debug': ['-O0', '--debug'],
    'debugoptimized': ['-O1', '--debug'],
    'release': ['-O3', '-Otime'],
    'minsize': ['-O3', '-Ospace'],
    'custom': [],
}  # type: typing.Dict[str, typing.List[str]]

arm_buildtype_linker_args = {
    'plain': [],
    'debug': [],
    'debugoptimized': [],
    'release': [],
    'minsize': [],
    'custom': [],
}  # type: typing.Dict[str, typing.List[str]]

arm_optimization_args = {
    '0': ['-O0'],
    'g': ['-g'],
    '1': ['-O1'],
    '2': ['-O2'],
    '3': ['-O3'],
    's': [],
}  # type: typing.Dict[str, typing.List[str]]


class ArmCompiler:
    # Functionality that is common to all ARM family compilers.
    def __init__(self, compiler_type: 'CompilerType'):
        if not self.is_cross:
            raise EnvironmentException('armcc supports only cross-compilation.')
        self.id = 'arm'
        self.compiler_type = compiler_type
        default_warn_args = []  # type: typing.List[str]
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args + [],
                          '3': default_warn_args + []}
        # Assembly
        self.can_compile_suffixes.add('s')

    def can_linker_accept_rsp(self) -> bool:
        return False

    def get_pic_args(self) -> typing.List[str]:
        # FIXME: Add /ropi, /rwpi, /fpic etc. qualifiers to --apcs
        return []

    def get_buildtype_args(self, buildtype: str) -> typing.List[str]:
        return arm_buildtype_args[buildtype]

    def get_buildtype_linker_args(self, buildtype: str) -> typing.List[str]:
        return arm_buildtype_linker_args[buildtype]

    # Override CCompiler.get_always_args
    def get_always_args(self) -> typing.List[str]:
        return []

    # Override CCompiler.get_dependency_gen_args
    def get_dependency_gen_args(self, outtarget: str, outfile: str) -> typing.List[str]:
        return []

    # Override CCompiler.get_std_shared_lib_link_args
    def get_std_shared_lib_link_args(self) -> typing.List[str]:
        return []

    def get_pch_use_args(self, pch_dir: str, header: str) -> typing.List[str]:
        # FIXME: Add required arguments
        # NOTE from armcc user guide:
        # "Support for Precompiled Header (PCH) files is deprecated from ARM Compiler 5.05
        # onwards on all platforms. Note that ARM Compiler on Windows 8 never supported
        # PCH files."
        return []

    def get_pch_suffix(self) -> str:
        # NOTE from armcc user guide:
        # "Support for Precompiled Header (PCH) files is deprecated from ARM Compiler 5.05
        # onwards on all platforms. Note that ARM Compiler on Windows 8 never supported
        # PCH files."
        return 'pch'

    def thread_flags(self, env: 'Environment') -> typing.List[str]:
        return []

    def thread_link_flags(self, env: 'Environment') -> typing.List[str]:
        return []

    def get_linker_exelist(self) -> typing.List[str]:
        args = ['armlink']
        return args

    def get_coverage_args(self) -> typing.List[str]:
        return []

    def get_coverage_link_args(self) -> typing.List[str]:
        return []

    def get_optimization_args(self, optimization_level: str) -> typing.List[str]:
        return arm_optimization_args[optimization_level]

    def get_debug_args(self, is_debug: bool) -> typing.List[str]:
        return clike_debug_args[is_debug]

    def compute_parameters_with_absolute_paths(self, parameter_list: typing.List[str], build_dir: str) -> typing.List[str]:
        for idx, i in enumerate(parameter_list):
            if i[:2] == '-I' or i[:2] == '-L':
                parameter_list[idx] = i[:2] + os.path.normpath(os.path.join(build_dir, i[2:]))

        return parameter_list