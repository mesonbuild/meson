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

import subprocess, os.path
import typing as T

from ..mesonlib import EnvironmentException, MachineChoice, Popen_safe
from .compilers import Compiler, rust_buildtype_args, clike_debug_args

if T.TYPE_CHECKING:
    from ..envconfig import MachineInfo
    from ..environment import Environment  # noqa: F401

rust_optimization_args = {'0': [],
                          'g': ['-C', 'opt-level=0'],
                          '1': ['-C', 'opt-level=1'],
                          '2': ['-C', 'opt-level=2'],
                          '3': ['-C', 'opt-level=3'],
                          's': ['-C', 'opt-level=s'],
                          }

class RustCompiler(Compiler):

    # rustc doesn't invoke the compiler itself, it doesn't need a LINKER_PREFIX
    language = 'rust'

    def __init__(self, exelist, version, for_machine: MachineChoice,
                 is_cross, info: 'MachineInfo', exe_wrapper=None, **kwargs):
        super().__init__(exelist, version, for_machine, info, **kwargs)
        self.exe_wrapper = exe_wrapper
        self.id = 'rustc'
        self.is_cross = is_cross

    def needs_static_linker(self):
        return False

    def name_string(self):
        return ' '.join(self.exelist)

    def sanity_check(self, work_dir, environment):
        source_name = os.path.join(work_dir, 'sanity.rs')
        output_name = os.path.join(work_dir, 'rusttest')
        with open(source_name, 'w') as ofile:
            ofile.write('''fn main() {
}
''')
        pc = subprocess.Popen(self.exelist + ['-o', output_name, source_name],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              cwd=work_dir)
        stdo, stde = pc.communicate()
        stdo = stdo.decode('utf-8', errors='replace')
        stde = stde.decode('utf-8', errors='replace')
        if pc.returncode != 0:
            raise EnvironmentException('Rust compiler %s can not compile programs.\n%s\n%s' % (
                self.name_string(),
                stdo,
                stde))
        if self.is_cross:
            if self.exe_wrapper is None:
                # Can't check if the binaries run so we have to assume they do
                return
            cmdlist = self.exe_wrapper + [output_name]
        else:
            cmdlist = [output_name]
        pe = subprocess.Popen(cmdlist, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        pe.wait()
        if pe.returncode != 0:
            raise EnvironmentException('Executables created by Rust compiler %s are not runnable.' % self.name_string())

    def get_dependency_gen_args(self, outfile):
        return ['--dep-info', outfile]

    def get_buildtype_args(self, buildtype):
        return rust_buildtype_args[buildtype]

    def get_sysroot(self):
        cmd = self.exelist + ['--print', 'sysroot']
        p, stdo, stde = Popen_safe(cmd)
        return stdo.split('\n')[0]

    def get_debug_args(self, is_debug):
        return clike_debug_args[is_debug]

    def get_optimization_args(self, optimization_level):
        return rust_optimization_args[optimization_level]

    def compute_parameters_with_absolute_paths(self, parameter_list, build_dir):
        for idx, i in enumerate(parameter_list):
            if i[:2] == '-L':
                for j in ['dependency', 'crate', 'native', 'framework', 'all']:
                    combined_len = len(j) + 3
                    if i[:combined_len] == '-L{}='.format(j):
                        parameter_list[idx] = i[:combined_len] + os.path.normpath(os.path.join(build_dir, i[combined_len:]))
                        break

        return parameter_list

    def get_std_exe_link_args(self):
        return []

    # Rust does not have a use_linker_args because it dispatches to a gcc-like
    # C compiler for dynamic linking, as such we invoke the C compiler's
    # use_linker_args method instead.
