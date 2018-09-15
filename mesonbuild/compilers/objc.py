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

from ..mesonlib import EnvironmentException

from .c import CCompiler
from .compilers import ClangCompiler, GnuCompiler

class ObjCCompiler(CCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrap):
        self.language = 'objc'
        CCompiler.__init__(self, exelist, version, is_cross, exe_wrap)

    def get_display_language(self):
        return 'Objective-C'

    def sanity_check(self, work_dir, environment):
        # TODO try to use sanity_check_impl instead of duplicated code
        source_name = os.path.join(work_dir, 'sanitycheckobjc.m')
        binary_name = os.path.join(work_dir, 'sanitycheckobjc')
        extra_flags = self.get_cross_extra_flags(environment, link=False)
        if self.is_cross:
            extra_flags += self.get_compile_only_args()
        with open(source_name, 'w') as ofile:
            ofile.write('#import<stdio.h>\n'
                        'int main(int argc, char **argv) { return 0; }\n')
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
    def __init__(self, exelist, version, compiler_type, is_cross, exe_wrapper=None, defines=None):
        ObjCCompiler.__init__(self, exelist, version, is_cross, exe_wrapper)
        GnuCompiler.__init__(self, compiler_type, defines)
        default_warn_args = ['-Wall', '-Winvalid-pch']
        self.warn_args = {'1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}


class ClangObjCCompiler(ClangCompiler, ObjCCompiler):
    def __init__(self, exelist, version, compiler_type, is_cross, exe_wrapper=None):
        ObjCCompiler.__init__(self, exelist, version, is_cross, exe_wrapper)
        ClangCompiler.__init__(self, compiler_type)
        default_warn_args = ['-Wall', '-Winvalid-pch']
        self.warn_args = {'1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}
        self.base_options = ['b_pch', 'b_lto', 'b_pgo', 'b_sanitize', 'b_coverage']
