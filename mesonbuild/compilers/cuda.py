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

from .. import mlog
from ..mesonlib import EnvironmentException, Popen_safe
from .compilers import Compiler, cuda_buildtype_args

class CudaCompiler(Compiler):
    def __init__(self, exelist, version, is_cross, exe_wrapper=None):
        # If a child ObjCPP class has already set it, don't set it ourselves
        if not hasattr(self, 'language'):
            self.language = 'cuda'
        super().__init__(exelist, version)
        self.is_cross = is_cross
        self.exe_wrapper = exe_wrapper
        self.id = 'nvcc'
        default_warn_args = []
        self.warn_args = {'1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}

    def needs_static_linker(self):
        return False

    def get_display_language(self):
        return 'Cuda'

    def get_no_stdinc_args(self):
        return ['']

    def sanity_check(self, work_dir, environment):
        source_name = os.path.join(work_dir, 'sanitycheckcuda.cu')
        binary_name = os.path.join(work_dir, 'sanitycheckcuda')
        extra_flags = self.get_cross_extra_flags(environment, link=False)
        if self.is_cross:
            extra_flags += self.get_compile_only_args()

        code = '''
        #include <stdio.h>
        int main(int argc,char** argv){
            return 0;
        }
        '''

        with open(source_name, 'w') as ofile:
            ofile.write(code)
        pc = subprocess.Popen(self.exelist + extra_flags + [source_name, '-o', binary_name])
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('Cuda compiler %s can not compile programs.' % self.name_string())
        if self.is_cross:
            # Can't check if the binaries run so we have to assume they do
            return
        pe = subprocess.Popen(binary_name)
        pe.wait()
        if pe.returncode != 0:
            raise EnvironmentException('Executables created by ObjC compiler %s are not runnable.' % self.name_string())

    def get_compiler_check_args(self):
        return super().get_compiler_check_args() + []

    def has_header_symbol(self, hname, symbol, prefix, env, extra_args=None, dependencies=None):
        if super().has_header_symbol(hname, symbol, prefix, env, extra_args, dependencies):
            return True
        if extra_args is None:
            extra_args = []
        fargs = {'prefix': prefix, 'header': hname, 'symbol': symbol}
        t = '''{prefix}
        #include <{header}>
        using {symbol};
        int main () {{ return 0; }}'''
        return self.compiles(t.format(**fargs), env, extra_args, dependencies)

    def sanity_check_impl(self, work_dir, environment, sname, code):
        mlog.debug('Sanity testing ' + self.get_display_language() + ' compiler:', ' '.join(self.exelist))
        mlog.debug('Is cross compiler: %s.' % str(self.is_cross))

        extra_flags = []
        source_name = os.path.join(work_dir, sname)
        binname = sname.rsplit('.', 1)[0]
        if self.is_cross:
            binname += '_cross'
            if self.exe_wrapper is None:
                # Linking cross built apps is painful. You can't really
                # tell if you should use -nostdlib or not and for example
                # on OSX the compiler binary is the same but you need
                # a ton of compiler flags to differentiate between
                # arm and x86_64. So just compile.
                extra_flags += self.get_cross_extra_flags(environment, link=False)
                extra_flags += self.get_compile_only_args()
            else:
                extra_flags += self.get_cross_extra_flags(environment, link=True)
        # Is a valid executable output for all toolchains and platforms
        binname += '.exe'
        # Write binary check source
        binary_name = os.path.join(work_dir, binname)
        with open(source_name, 'w') as ofile:
            ofile.write(code)
        # Compile sanity check
        cmdlist = self.exelist + extra_flags + [source_name] + self.get_output_args(binary_name)
        pc, stdo, stde = Popen_safe(cmdlist, cwd=work_dir)
        mlog.debug('Sanity check compiler command line:', ' '.join(cmdlist))
        mlog.debug('Sanity check compile stdout:')
        mlog.debug(stdo)
        mlog.debug('-----\nSanity check compile stderr:')
        mlog.debug(stde)
        mlog.debug('-----')
        if pc.returncode != 0:
            raise EnvironmentException('Compiler {0} can not compile programs.'.format(self.name_string()))
        # Run sanity check
        if self.is_cross:
            if self.exe_wrapper is None:
                # Can't check if the binaries run so we have to assume they do
                return
            cmdlist = self.exe_wrapper + [binary_name]
        else:
            cmdlist = [binary_name]
        mlog.debug('Running test binary command: ' + ' '.join(cmdlist))
        pe = subprocess.Popen(cmdlist)
        pe.wait()
        if pe.returncode != 0:
            raise EnvironmentException('Executables created by {0} compiler {1} are not runnable.'.format(self.language, self.name_string()))

    def get_output_args(self, target):
        return ['-o', target]

    def name_string(self):
        return ' '.join(self.exelist)

    def get_dependency_gen_args(self, outtarget, outfile):
        return []

    def get_compile_only_args(self):
        return ['-c']

    def get_no_optimization_args(self):
        return ['-O0']

    def get_linker_exelist(self):
        return self.exelist[:]

    def get_linker_output_args(self, outputname):
        return ['-o', outputname]

    def get_warn_args(self, level):
        return self.warn_args[level]

    def get_buildtype_args(self, buildtype):
        return cuda_buildtype_args[buildtype]

    def get_include_args(self, path, is_system):
        if path == '':
            path = '.'
        return ['-I' + path]

    def depfile_for_object(self, objfile):
        return objfile + '.' + self.get_depfile_suffix()

    def get_depfile_suffix(self):
        return 'd'

    def get_buildtype_linker_args(self, buildtype):
        return []

    def get_std_exe_link_args(self):
        return []

    def build_rpath_args(self, build_dir, from_dir, rpath_paths, build_rpath, install_rpath):
        return []

    def get_linker_search_args(self, dirname):
        return ['/LIBPATH:' + dirname]

    def linker_to_compiler_args(self, args):
        return ['/link'] + args
