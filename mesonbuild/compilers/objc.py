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

import os.path, subprocess
import typing as T

from ..mesonlib import EnvironmentException, MachineChoice

from .compilers import Compiler
from .mixins.clike import CLikeCompiler
from .mixins.gnu import GnuCompiler
from .mixins.clang import ClangCompiler

if T.TYPE_CHECKING:
    from ..envconfig import MachineInfo


class ObjCCompiler(CLikeCompiler, Compiler):

    language = 'objc'

    def __init__(self, exelist, version, for_machine: MachineChoice,
                 is_cross: bool, info: 'MachineInfo',
                 exe_wrap: T.Optional[str], **kwargs):
        Compiler.__init__(self, exelist, version, for_machine, info, **kwargs)
        CLikeCompiler.__init__(self, is_cross, exe_wrap)

    @staticmethod
    def get_display_language():
        return 'Objective-C'

    def sanity_check(self, work_dir, environment):
        # TODO try to use sanity_check_impl instead of duplicated code
        source_name = os.path.join(work_dir, 'sanitycheckobjc.m')
        binary_name = os.path.join(work_dir, 'sanitycheckobjc')
        extra_flags = []
        extra_flags += environment.coredata.get_external_args(self.for_machine, self.language)
        if self.is_cross:
            extra_flags += self.get_compile_only_args()
        else:
            extra_flags += environment.coredata.get_external_link_args(self.for_machine, self.language)
        with open(source_name, 'w') as ofile:
            ofile.write('#import<stddef.h>\n'
                        'int main(void) { return 0; }\n')
        pc = subprocess.Popen(self.exelist + extra_flags + [source_name, '-o', binary_name])
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('ObjC compiler %s can not compile programs.' % self.name_string())
        if self.is_cross:
            # Can't check if the binaries run so we have to assume they do
            return
        pe = subprocess.Popen(binary_name)
        pe.wait()
        if pe.returncode != 0:
            raise EnvironmentException('Executables created by ObjC compiler %s are not runnable.' % self.name_string())


class GnuObjCCompiler(GnuCompiler, ObjCCompiler):
    def __init__(self, exelist, version, for_machine: MachineChoice,
                 is_cross, info: 'MachineInfo', exe_wrapper=None,
                 defines=None, **kwargs):
        ObjCCompiler.__init__(self, exelist, version, for_machine, is_cross,
                              info, exe_wrapper, **kwargs)
        GnuCompiler.__init__(self, defines)
        default_warn_args = ['-Wall', '-Winvalid-pch']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}


class ClangObjCCompiler(ClangCompiler, ObjCCompiler):
    def __init__(self, exelist, version, for_machine: MachineChoice,
                 is_cross, info: 'MachineInfo', exe_wrapper=None,
                 **kwargs):
        ObjCCompiler.__init__(self, exelist, version, for_machine, is_cross,
                              info, exe_wrapper, **kwargs)
        ClangCompiler.__init__(self, [])
        default_warn_args = ['-Wall', '-Winvalid-pch']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}
