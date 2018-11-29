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

import os.path, shutil, subprocess

from ..mesonlib import EnvironmentException

from .compilers import Compiler, java_buildtype_args

class JavaCompiler(Compiler):
    def __init__(self, exelist, version):
        self.language = 'java'
        super().__init__(exelist, version)
        self.id = 'unknown'
        self.javarunner = 'java'

    def get_soname_args(self, *args):
        return []

    def get_werror_args(self):
        return ['-Werror']

    def split_shlib_to_parts(self, fname):
        return None, fname

    def build_rpath_args(self, build_dir, from_dir, rpath_paths, build_rpath, install_rpath):
        return []

    def get_dependency_gen_args(self, outtarget, outfile):
        return []

    def get_linker_exelist(self):
        return self.exelist[:]

    def get_compile_only_args(self):
        return []

    def get_output_args(self, subdir):
        if subdir == '':
            subdir = './'
        return ['-d', subdir, '-s', subdir]

    def get_linker_output_args(self, outputname):
        return []

    def get_coverage_args(self):
        return []

    def get_coverage_link_args(self):
        return []

    def get_std_exe_link_args(self):
        return []

    def get_include_args(self, path):
        return []

    def get_pic_args(self):
        return []

    def name_string(self):
        return ' '.join(self.exelist)

    def get_pch_use_args(self, pch_dir, header):
        return []

    def get_pch_name(self, header_name):
        return ''

    def get_buildtype_args(self, buildtype):
        return java_buildtype_args[buildtype]

    def sanity_check(self, work_dir, environment):
        src = 'SanityCheck.java'
        obj = 'SanityCheck'
        source_name = os.path.join(work_dir, src)
        with open(source_name, 'w') as ofile:
            ofile.write('''class SanityCheck {
  public static void main(String[] args) {
    int i;
  }
}
''')
        pc = subprocess.Popen(self.exelist + [src], cwd=work_dir)
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('Java compiler %s can not compile programs.' % self.name_string())
        runner = shutil.which(self.javarunner)
        if runner:
            cmdlist = [runner, obj]
            pe = subprocess.Popen(cmdlist, cwd=work_dir)
            pe.wait()
            if pe.returncode != 0:
                raise EnvironmentException('Executables created by Java compiler %s are not runnable.' % self.name_string())
        else:
            m = "Java Virtual Machine wasn't found, but it's needed by Meson. " \
                "Please install a JRE.\nIf you have specific needs where this " \
                "requirement doesn't make sense, please open a bug at " \
                "https://github.com/mesonbuild/meson/issues/new and tell us " \
                "all about it."
            raise EnvironmentException(m)

    def needs_static_linker(self):
        return False
