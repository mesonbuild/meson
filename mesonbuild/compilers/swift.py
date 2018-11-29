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

from ..mesonlib import EnvironmentException

from .compilers import Compiler, swift_buildtype_args, clike_debug_args

swift_optimization_args = {'0': [],
                           'g': [],
                           '1': ['-O'],
                           '2': ['-O'],
                           '3': ['-O'],
                           's': ['-O'],
                           }

class SwiftCompiler(Compiler):
    def __init__(self, exelist, version):
        self.language = 'swift'
        super().__init__(exelist, version)
        self.version = version
        self.id = 'llvm'
        self.is_cross = False

    def get_linker_exelist(self):
        return self.exelist[:]

    def name_string(self):
        return ' '.join(self.exelist)

    def needs_static_linker(self):
        return True

    def get_werror_args(self):
        return ['--fatal-warnings']

    def get_dependency_gen_args(self, outtarget, outfile):
        return ['-emit-dependencies']

    def depfile_for_object(self, objfile):
        return os.path.splitext(objfile)[0] + '.' + self.get_depfile_suffix()

    def get_depfile_suffix(self):
        return 'd'

    def get_output_args(self, target):
        return ['-o', target]

    def get_linker_output_args(self, target):
        return ['-o', target]

    def get_header_import_args(self, headername):
        return ['-import-objc-header', headername]

    def get_warn_args(self, level):
        return []

    def get_buildtype_args(self, buildtype):
        return swift_buildtype_args[buildtype]

    def get_buildtype_linker_args(self, buildtype):
        return []

    def get_std_exe_link_args(self):
        return ['-emit-executable']

    def get_module_args(self, modname):
        return ['-module-name', modname]

    def get_mod_gen_args(self):
        return ['-emit-module']

    def build_rpath_args(self, *args):
        return [] # FIXME

    def get_include_args(self, dirname):
        return ['-I' + dirname]

    def get_compile_only_args(self):
        return ['-c']

    def sanity_check(self, work_dir, environment):
        src = 'swifttest.swift'
        source_name = os.path.join(work_dir, src)
        output_name = os.path.join(work_dir, 'swifttest')
        with open(source_name, 'w') as ofile:
            ofile.write('''print("Swift compilation is working.")
''')
        extra_flags = self.get_cross_extra_flags(environment, link=True)
        pc = subprocess.Popen(self.exelist + extra_flags + ['-emit-executable', '-o', output_name, src], cwd=work_dir)
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('Swift compiler %s can not compile programs.' % self.name_string())
        if subprocess.call(output_name) != 0:
            raise EnvironmentException('Executables created by Swift compiler %s are not runnable.' % self.name_string())

    def get_debug_args(self, is_debug):
        return clike_debug_args[is_debug]

    def get_optimization_args(self, optimization_level):
        return swift_optimization_args[optimization_level]
