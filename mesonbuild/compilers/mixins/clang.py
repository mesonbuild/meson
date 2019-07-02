# Copyright 2019 The meson development team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Abstractions for the LLVM/Clang compiler family."""

import os
import typing

from .gnu import GnuLikeCompiler
from ..compilers import clike_optimization_args
from ... import mesonlib

if typing.TYPE_CHECKING:
    from ..compilers import CompilerType
    from ...environment import Environment
    from ...dependencies import Dependency  # noqa: F401

clang_color_args = {
    'auto': ['-Xclang', '-fcolor-diagnostics'],
    'always': ['-Xclang', '-fcolor-diagnostics'],
    'never': ['-Xclang', '-fno-color-diagnostics'],
}  # type: typing.Dict[str, typing.List[str]]


class ClangCompiler(GnuLikeCompiler):
    def __init__(self, compiler_type: 'CompilerType'):
        super().__init__(compiler_type)
        self.id = 'clang'
        self.base_options.append('b_colorout')
        if self.compiler_type.is_osx_compiler:
            self.base_options.append('b_bitcode')
        # All Clang backends can also do LLVM IR
        self.can_compile_suffixes.add('ll')

    def get_colorout_args(self, colortype: str) -> typing.List[str]:
        return clang_color_args[colortype][:]

    def get_optimization_args(self, optimization_level: str) -> typing.List[str]:
        return clike_optimization_args[optimization_level]

    def get_pch_suffix(self) -> str:
        return 'pch'

    def get_pch_use_args(self, pch_dir: str, header: str) -> typing.List[str]:
        # Workaround for Clang bug http://llvm.org/bugs/show_bug.cgi?id=15136
        # This flag is internal to Clang (or at least not documented on the man page)
        # so it might change semantics at any time.
        return ['-include-pch', os.path.join(pch_dir, self.get_pch_name(header))]

    def has_multi_arguments(self, args: typing.List[str], env: 'Environment') -> typing.List[str]:
        myargs = ['-Werror=unknown-warning-option', '-Werror=unused-command-line-argument']
        if mesonlib.version_compare(self.version, '>=3.6.0'):
            myargs.append('-Werror=ignored-optimization-argument')
        return super().has_multi_arguments(
            myargs + args,
            env)

    def has_function(self, funcname: str, prefix: str, env: 'Environment', *,
                     extra_args: typing.Optional[typing.List[str]] = None,
                     dependencies: typing.Optional[typing.List['Dependency']] = None) -> bool:
        if extra_args is None:
            extra_args = []
        # Starting with XCode 8, we need to pass this to force linker
        # visibility to obey OS X/iOS/tvOS minimum version targets with
        # -mmacosx-version-min, -miphoneos-version-min, -mtvos-version-min etc.
        # https://github.com/Homebrew/homebrew-core/issues/3727
        if self.compiler_type.is_osx_compiler and mesonlib.version_compare(self.version, '>=8.0'):
            extra_args.append('-Wl,-no_weak_imports')
        return super().has_function(funcname, prefix, env, extra_args=extra_args,
                                    dependencies=dependencies)

    def openmp_flags(self) -> typing.List[str]:
        if mesonlib.version_compare(self.version, '>=3.8.0'):
            return ['-fopenmp']
        elif mesonlib.version_compare(self.version, '>=3.7.0'):
            return ['-fopenmp=libomp']
        else:
            # Shouldn't work, but it'll be checked explicitly in the OpenMP dependency.
            return []
