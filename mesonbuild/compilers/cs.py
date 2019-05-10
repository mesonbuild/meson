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

import os.path, subprocess, re

from ..mesonlib import EnvironmentException
from ..mesonlib import is_windows
from ..mesonlib import (
    EnvironmentException, Popen_safe
)

from .compilers import Compiler, mono_buildtype_args

cs_optimization_args = {'0': [],
                        'g': [],
                        '1': ['-optimize+'],
                        '2': ['-optimize+'],
                        '3': ['-optimize+'],
                        's': ['-optimize+'],
                        }

class CsCompiler(Compiler):
    def __init__(self, exelist, version, comp_id, runner=None):
        self.language = 'cs'
        super().__init__(exelist, version)
        self.id = comp_id
        self.is_cross = False
        self.runner = runner

    def get_display_language(self):
        return 'C sharp'

    def get_always_args(self):
        return ['/nologo']

    def get_linker_always_args(self):
        return ['/nologo']

    def get_output_args(self, fname):
        return ['-out:' + fname]

    def get_link_args(self, fname):
        return ['-r:' + fname]

    def get_runtime_assembly_arg(self, asm):
        return []
    
    def get_soname_args(self, *args):
        return []

    def get_werror_args(self):
        return ['-warnaserror']

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

    def compute_parameters_with_absolute_paths(self, parameter_list, build_dir):
        for idx, i in enumerate(parameter_list):
            if i[:2] == '-L':
                parameter_list[idx] = i[:2] + os.path.normpath(os.path.join(build_dir, i[2:]))
            if i[:5] == '-lib:':
                parameter_list[idx] = i[:5] + os.path.normpath(os.path.join(build_dir, i[5:]))

        return parameter_list

    def name_string(self):
        return ' '.join(self.exelist)

    def get_pch_use_args(self, pch_dir, header):
        return []

    def get_pch_name(self, header_name):
        return ''

    def sanity_check(self, work_dir, environment):
        config = 'sanity.runtimeconfig.json'
        src = 'sanity.cs'
        obj = 'sanity.exe'
        source_name = os.path.join(work_dir, src)
        with open(source_name, 'w') as ofile:
            ofile.write('''public class Sanity {
    static public void Main () {
    }
}
''')
        config_name = os.path.join(work_dir, config)
        with open(config_name, 'w') as ofile:
            ofile.write('''{
  "runtimeOptions": {
    "tfm": "netcoreapp2.0",
    "framework": {
      "name": "Microsoft.NETCore.App",
      "version": "2.0.0"
    },
    "configProperties": {
      "System.GC.Server": true
    }
  }
}
''')
        pc = subprocess.Popen(self.exelist + self.get_always_args() + [src], cwd=work_dir)
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('Mono compiler %s can not compile programs.' % self.name_string())
        if self.runner:
            cmdlist = [self.runner, obj]
        else:
            cmdlist = [os.path.join(work_dir, obj)]
        pe = subprocess.Popen(cmdlist, cwd=work_dir)
        pe.wait()
        if pe.returncode != 0:
            raise EnvironmentException('Executables created by Mono compiler %s are not runnable.' % self.name_string())

    def needs_static_linker(self):
        return False

    def get_buildtype_args(self, buildtype):
        return mono_buildtype_args[buildtype]

    def get_debug_args(self, is_debug):
        return ['-debug'] if is_debug else []

    def get_optimization_args(self, optimization_level):
        return cs_optimization_args[optimization_level]

class MonoCompiler(CsCompiler):
    def __init__(self, exelist, version):
        super().__init__(exelist, version, 'mono',
                         'mono')


class VisualStudioCsCompiler(CsCompiler):
    def __init__(self, exelist, version):
        super().__init__(exelist, version, 'csc', 'dotnet')
        try:
            p, out, err = Popen_safe([self.runner, '--list-runtimes'])
        except OSError as e:
            raise EnvironmentException('Runner for dotnet doesn\'t include runtime information')
        dir_regex = '[^\[]+\[(.*?)\]'
        dir_match = re.search(dir_regex, out)
        if dir_match:
            self.runtimes_path = dir_match.group(1)
        else:
            raise EnvironmentException('Runner for dotnet doesn\'t include runtime information')
        version_regex = '[^ ]+[ ](\d+\.\d+\.\d+)'
        version_match = re.search(version_regex, out)
        if version_match:
            self.runtime_version = version_match.group(1)
        else:
            raise EnvironmentException('Runner for dotnet doesn\'t include runtime information')

    def get_runtime_assembly_arg(self, asm):
        return ['-r:' + self.runtimes_path + '/' + self.runtime_version + '/' + asm + '.dll']
        
    def get_always_args(self):
        return ['/nologo', '-r:' + self.runtimes_path + '/' + self.runtime_version + '/System.Private.CoreLib.dll']
        
    def get_buildtype_args(self, buildtype):
        res = mono_buildtype_args[buildtype]
        if not is_windows():
            tmp = []
            for flag in res:
                if flag == '-debug':
                    flag = '-debug:portable'
                tmp.append(flag)
            res = tmp
        return res
