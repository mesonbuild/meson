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

"""Abstractions for the Elbrus family of compilers."""

import os
import typing

from .gnu import GnuCompiler
from ...mesonlib import Popen_safe

if typing.TYPE_CHECKING:
    from ..compilers import CompilerType
    from ...environment import Environment


class ElbrusCompiler(GnuCompiler):
    # Elbrus compiler is nearly like GCC, but does not support
    # PCH, LTO, sanitizers and color output as of version 1.21.x.
    def __init__(self, compiler_type: 'CompilerType', defines: typing.Dict[str, str]):
        GnuCompiler.__init__(self, compiler_type, defines)
        self.id = 'lcc'
        self.base_options = ['b_pgo', 'b_coverage',
                             'b_ndebug', 'b_staticpic',
                             'b_lundef', 'b_asneeded']

    # FIXME: use _build_wrapper to call this so that linker flags from the env
    # get applied
    def get_library_dirs(self, env: 'Environment', elf_class: typing.Optional[int] = None) -> typing.List[str]:
        os_env = os.environ.copy()
        os_env['LC_ALL'] = 'C'
        stdo = Popen_safe(self.exelist + ['--print-search-dirs'], env=os_env)[1]
        for line in stdo.split('\n'):
            if line.startswith('libraries:'):
                # lcc does not include '=' in --print-search-dirs output.
                libstr = line.split(' ', 1)[1]
                return [os.path.realpath(p) for p in libstr.split(':')]
        return []

    def get_program_dirs(self, env: 'Environment') -> typing.List[str]:
        os_env = os.environ.copy()
        os_env['LC_ALL'] = 'C'
        stdo = Popen_safe(self.exelist + ['--print-search-dirs'], env=os_env)[1]
        for line in stdo.split('\n'):
            if line.startswith('programs:'):
                # lcc does not include '=' in --print-search-dirs output.
                libstr = line.split(' ', 1)[1]
                return [os.path.realpath(p) for p in libstr.split(':')]
        return []
