# Copyright 2012-2017 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os.path
import subprocess
import textwrap
import typing as T

from .compilers import Compiler
from ..mesonlib import MachineChoice, EnvironmentException

if T.TYPE_CHECKING:
    from ..envconfig import MachineInfo
    from ..environment import Environment
    from ..dependencies import ExternalProgram

zig_optimization_args = {
    '0': [],
    'g': ['-O', 'Debug'],
    '1': ['-O', 'ReleaseSafe'],
    '2': ['-O', 'ReleaseSafe'],
    '3': ['-O', 'ReleaseFast'],
    's': ['-O', 'ReleaseSmall'],
}  # type: T.Dict[str, T.List[str]]


class ZigCompiler(Compiler):
    language = 'zig'

    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice, info: 'MachineInfo',
                 exe_wrapper: T.Optional['ExternalProgram'] = None, is_cross: bool = False):
        super().__init__(exelist, version, for_machine, info, is_cross=is_cross)
        self.id = 'zig'
        self.exe_wrapper = exe_wrapper

    def get_optimization_args(self, optimization_level: str) -> T.List[str]:
        return zig_optimization_args[optimization_level]

    def get_output_args(self, outputname: str) -> T.List[str]:
        return ['-femit-bin=%s' % outputname]

    def get_pic_args(self) -> T.List[str]:
        return ['-fPIC']

    def needs_static_linker(self):
        return False

    def sanity_check(self, work_dir: str, environment: 'Environment') -> None:
        source_name = os.path.join(work_dir, 'sanity.zig')
        output_name = os.path.join(work_dir, 'zigtest')

        with open(source_name, 'w') as ofile:
            ofile.write(textwrap.dedent(
                '''pub fn main() !void {
                }
                '''))

        # Compile the source file to an executable
        pc = subprocess.Popen(self.exelist + ['build-exe', source_name] + self.get_output_args(output_name),
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              cwd=work_dir)
        _stdo, _stde = pc.communicate()
        assert isinstance(_stdo, bytes)
        assert isinstance(_stde, bytes)
        stdo = _stdo.decode('utf-8', errors='replace')
        stde = _stde.decode('utf-8', errors='replace')

        # Check if the build was successful
        if pc.returncode != 0:
            raise EnvironmentException('Zig compiler %s can not compile programs.\n%s\n%s' % (
                self.name_string(),
                stdo,
                stde))

        if self.is_cross:
            if self.exe_wrapper is None:
                # Can't check if the binaries run so we have to assume they do
                return
            cmdlist = self.exe_wrapper.get_command() + [output_name]
        else:
            cmdlist = [output_name]

        # Check if the built executable is runnable
        pe = subprocess.Popen(cmdlist, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        pe.wait()
        if pe.returncode != 0:
            raise EnvironmentException('Executables created by Zig compiler %s are not runnable.' % self.name_string())
