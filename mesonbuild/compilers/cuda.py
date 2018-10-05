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

import re, os.path

from .. import mlog
from ..mesonlib import EnvironmentException, MachineChoice, Popen_safe
from .compilers import (Compiler, cuda_buildtype_args, cuda_optimization_args,
                        cuda_debug_args, CompilerType, get_gcc_soname_args)

class CudaCompiler(Compiler):
    def __init__(self, exelist, version, for_machine: MachineChoice, is_cross, exe_wrapper=None):
        if not hasattr(self, 'language'):
            self.language = 'cuda'
        super().__init__(exelist, version, for_machine)
        self.is_cross = is_cross
        self.exe_wrapper = exe_wrapper
        self.id = 'nvcc'
        default_warn_args = []
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args + ['-Xcompiler=-Wextra'],
                          '3': default_warn_args + ['-Xcompiler=-Wextra',
                                                    '-Xcompiler=-Wpedantic']}

    def needs_static_linker(self):
        return False

    def get_always_args(self):
        return []

    def get_display_language(self):
        return 'Cuda'

    def get_no_stdinc_args(self):
        return []

    def thread_link_flags(self, environment):
        return ['-Xcompiler=-pthread']

    def sanity_check(self, work_dir, environment):
        mlog.debug('Sanity testing ' + self.get_display_language() + ' compiler:', ' '.join(self.exelist))
        mlog.debug('Is cross compiler: %s.' % str(self.is_cross))

        sname = 'sanitycheckcuda.cu'
        code = r'''
        #include <cuda_runtime.h>
        #include <stdio.h>

        __global__ void kernel (void) {}

        int main(void){
            struct cudaDeviceProp prop;
            int count, i;
            cudaError_t ret = cudaGetDeviceCount(&count);
            if(ret != cudaSuccess){
                fprintf(stderr, "%d\n", (int)ret);
            }else{
                for(i=0;i<count;i++){
                    if(cudaGetDeviceProperties(&prop, i) == cudaSuccess){
                        fprintf(stdout, "%d.%d\n", prop.major, prop.minor);
                    }
                }
            }
            fflush(stderr);
            fflush(stdout);
            return 0;
        }
        '''
        binname = sname.rsplit('.', 1)[0]
        binname += '_cross' if self.is_cross else ''
        source_name = os.path.join(work_dir, sname)
        binary_name = os.path.join(work_dir, binname + '.exe')
        with open(source_name, 'w') as ofile:
            ofile.write(code)

        # The Sanity Test for CUDA language will serve as both a sanity test
        # and a native-build GPU architecture detection test, useful later.
        #
        # For this second purpose, NVCC has very handy flags, --run and
        # --run-args, that allow one to run an application with the
        # environment set up properly. Of course, this only works for native
        # builds; For cross builds we must still use the exe_wrapper (if any).
        self.detected_cc = ''
        flags = ['-w', '-cudart', 'static', source_name]
        if self.is_cross and self.exe_wrapper is None:
            # Linking cross built apps is painful. You can't really
            # tell if you should use -nostdlib or not and for example
            # on OSX the compiler binary is the same but you need
            # a ton of compiler flags to differentiate between
            # arm and x86_64. So just compile.
            flags += self.get_compile_only_args()
        flags += self.get_output_args(binary_name)

        # Compile sanity check
        cmdlist = self.exelist + flags
        mlog.debug('Sanity check compiler command line: ', ' '.join(cmdlist))
        pc, stdo, stde = Popen_safe(cmdlist, cwd=work_dir)
        mlog.debug('Sanity check compile stdout: ')
        mlog.debug(stdo)
        mlog.debug('-----\nSanity check compile stderr:')
        mlog.debug(stde)
        mlog.debug('-----')
        if pc.returncode != 0:
            raise EnvironmentException('Compiler {0} can not compile programs.'.format(self.name_string()))

        # Run sanity check (if possible)
        if self.is_cross:
            if self.exe_wrapper is None:
                return
            else:
                cmdlist = self.exe_wrapper + [binary_name]
        else:
            cmdlist = self.exelist + ['--run', '"' + binary_name + '"']
        mlog.debug('Sanity check run command line: ', ' '.join(cmdlist))
        pe, stdo, stde = Popen_safe(cmdlist, cwd=work_dir)
        mlog.debug('Sanity check run stdout: ')
        mlog.debug(stdo)
        mlog.debug('-----\nSanity check run stderr:')
        mlog.debug(stde)
        mlog.debug('-----')
        pe.wait()
        if pe.returncode != 0:
            raise EnvironmentException('Executables created by {0} compiler {1} are not runnable.'.format(self.language, self.name_string()))

        # Interpret the result of the sanity test.
        # As mentionned above, it is not only a sanity test but also a GPU
        # architecture detection test.
        if stde == '':
            self.detected_cc = stdo
        else:
            mlog.debug('cudaGetDeviceCount() returned ' + stde)

    def get_compiler_check_args(self):
        return super().get_compiler_check_args() + []

    def has_header_symbol(self, hname, symbol, prefix, env, extra_args=None, dependencies=None):
        result, cached = super().has_header_symbol(hname, symbol, prefix, env, extra_args, dependencies)
        if result:
            return True, cached
        if extra_args is None:
            extra_args = []
        fargs = {'prefix': prefix, 'header': hname, 'symbol': symbol}
        t = '''{prefix}
        #include <{header}>
        using {symbol};
        int main () {{ return 0; }}'''
        return self.compiles(t.format(**fargs), env, extra_args, dependencies)

    @staticmethod
    def _cook_link_args(args):
        """
        Converts GNU-style arguments -Wl,-arg,-arg
        to NVCC-style arguments -Xlinker=-arg,-arg
        """
        return [re.sub('^-Wl,', '-Xlinker=', arg) for arg in args]

    def get_output_args(self, target):
        return ['-o', target]

    def name_string(self):
        return ' '.join(self.exelist)

    def get_soname_args(self, *args):
        rawargs = get_gcc_soname_args(CompilerType.GCC_STANDARD, *args)
        return self._cook_link_args(rawargs)

    def get_dependency_gen_args(self, outtarget, outfile):
        return []

    def get_compile_only_args(self):
        return ['-c']

    def get_no_optimization_args(self):
        return ['-O0']

    def get_optimization_args(self, optimization_level):
        return cuda_optimization_args[optimization_level]

    def get_debug_args(self, is_debug):
        return cuda_debug_args[is_debug]

    def get_werror_args(self):
        return ['-Werror=cross-execution-space-call,deprecated-declarations,reorder']

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

    def get_std_shared_lib_link_args(self):
        return ['-shared']

    def depfile_for_object(self, objfile):
        return objfile + '.' + self.get_depfile_suffix()

    def get_depfile_suffix(self):
        return 'd'

    def get_buildtype_linker_args(self, buildtype):
        return []

    def get_std_exe_link_args(self):
        return []

    def build_rpath_args(self, build_dir, from_dir, rpath_paths, build_rpath, install_rpath):
        rawargs = self.build_unix_rpath_args(build_dir, from_dir, rpath_paths, build_rpath, install_rpath)
        return self._cook_link_args(rawargs)

    def get_linker_search_args(self, dirname):
        return ['-L' + dirname]

    def linker_to_compiler_args(self, args):
        return args

    def get_pic_args(self):
        return ['-Xcompiler=-fPIC']

    def compute_parameters_with_absolute_paths(self, parameter_list, build_dir):
        return []
