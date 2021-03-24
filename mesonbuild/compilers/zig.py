# Copyright 2012-2021 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import os
import subprocess
import textwrap
import typing as T

from ..mesonlib import MachineChoice, EnvironmentException, MesonException
from .compilers import Compiler

if T.TYPE_CHECKING:
    from .._typing import ImmutableListProtocol
    from ..envconfig import MachineInfo
    from ..environment import Environment
    from ..linkers.linkers import DynamicLinker
    from ..programs import ExternalProgram


_OPTIMIZATION_ARGS: T.Mapping[str, ImmutableListProtocol[str]] = {
    '0': [],
    'g': ['-O', 'Debug'],
    '1': ['-O', 'ReleaseSafe'],
    '2': ['-O', 'ReleaseSafe'],
    '3': ['-O', 'ReleaseFast'],
    's': ['-O', 'ReleaseSmall'],
}


class ZigCompiler(Compiler):
    language = 'zig'

    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice, info: 'MachineInfo',
                 linker: DynamicLinker, exe_wrapper: T.Optional['ExternalProgram'] = None, is_cross: bool = False):
        super().__init__([], exelist + ['build-obj'], version, for_machine, info, linker, is_cross=is_cross)
        self.id = 'zig'
        self.exe_wrapper = exe_wrapper

    def depfile_for_object(self, objfile: str) -> T.Optional[str]:
        # not implemented currently: https://github.com/ziglang/zig/issues/16850
        return None

    def compute_parameters_with_absolute_paths(self, parameter_list: T.List[str], build_dir: str) -> T.List[str]:
        for idx, i in enumerate(parameter_list):
            if i[:2] == '-I' or i[:2] == '-L':
                parameter_list[idx] = i[:2] + os.path.normpath(os.path.join(build_dir, i[2:]))

        return parameter_list

    def get_buildtype_args(self, buildtype: str) -> T.List[str]:
        return []

    def get_optimization_args(self, optimization_level: str) -> T.List[str]:
        return _OPTIMIZATION_ARGS[optimization_level].copy()

    def get_output_args(self, outputname: str) -> T.List[str]:
        return [f'-femit-bin={outputname}']

    def get_pic_args(self) -> T.List[str]:
        return ['-fPIC']

    def get_win_subsystem_args(self, value: str) -> T.List[str]:
        return ['--subsystem', value]

    def get_colorout_args(self, colortype: str) -> T.List[str]:
        if colortype == 'auto':
            return ['--color', 'auto']
        elif colortype == 'always':
            return ['--color', 'on']
        elif colortype == 'never':
            return ['--color', 'off']
        else:
            raise MesonException(f'Invalid color type for zig {colortype}')

    def get_include_args(self, path: str, is_system: bool) -> T.List[str]:
        if not path:
            path = '.'
        if is_system:
            return ['-isystem' + path]
        return ['-I' + path]

    def needs_static_linker(self) -> bool:
        return True

    def sanity_check(self, work_dir: str, environment: 'Environment') -> None:
        source_name = os.path.join(work_dir, 'sanity.zig')
        output_name = os.path.join(work_dir, 'zigtest')

        with open(source_name, 'w', encoding='utf-8') as ofile:
            ofile.write(textwrap.dedent(
                '''pub fn main() !void {
                }
                '''))

        # Compile the source file to an executable
        # Drop the added `build-obj`
        pc = subprocess.Popen(self.exelist[:-1] + ['build-exe', source_name] + self.get_output_args(output_name),
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              cwd=work_dir)
        _stdo, _stde = pc.communicate()
        stdo = _stdo.decode('utf-8', errors='replace')
        stde = _stde.decode('utf-8', errors='replace')

        # Check if the build was successful
        if pc.returncode != 0:
            raise EnvironmentException(f'Zig compiler {self.name_string()} can not compile programs.\n{stdo}\n{stde}')

        if self.is_cross:
            if self.exe_wrapper is None:
                # Can't check if the binaries run so we have to assume they do
                return
            cmdlist = self.exe_wrapper.get_command() + [output_name]
        else:
            cmdlist = [output_name]

        # Check if the built executable is runnable
        pe = subprocess.Popen(cmdlist, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if pe.wait() != 0:
            raise EnvironmentException(f'Executables created by Zig compiler {self.name_string()} are not runnable.')
