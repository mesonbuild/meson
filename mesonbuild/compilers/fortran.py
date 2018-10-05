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
from typing import List
import subprocess, os
from pathlib import Path

from .compilers import (
    CompilerType,
    apple_buildtype_linker_args,
    gnulike_buildtype_args,
    gnulike_buildtype_linker_args,
    gnu_optimization_args,
    clike_debug_args,
    Compiler,
    GnuCompiler,
    ClangCompiler,
    ElbrusCompiler,
    IntelGnuLikeCompiler,
    PGICompiler,
    IntelVisualStudioLikeCompiler,
)
from .clike import CLikeCompiler
from .. import mlog

from mesonbuild.mesonlib import (
    EnvironmentException, MachineChoice, is_osx, LibType
)


class FortranCompiler(CLikeCompiler, Compiler):

    def __init__(self, exelist, version, for_machine: MachineChoice, is_cross, exe_wrapper=None, **kwargs):
        self.language = 'fortran'
        Compiler.__init__(self, exelist, version, for_machine, **kwargs)
        CLikeCompiler.__init__(self, is_cross, exe_wrapper)
        self.id = 'unknown'

    def get_display_language(self):
        return 'Fortran'

    def sanity_check(self, work_dir: Path, environment):
        """
        Check to be sure a minimal program can compile and execute
          with this compiler & platform.
        """
        work_dir = Path(work_dir)
        source_name = work_dir / 'sanitycheckf.f90'
        binary_name = work_dir / 'sanitycheckf'
        if binary_name.is_file():
            binary_name.unlink()

        source_name.write_text('print *, "Fortran compilation is working."; end')

        extra_flags = environment.coredata.get_external_args(self.for_machine, self.language)
        extra_flags += environment.coredata.get_external_link_args(self.for_machine, self.language)
        extra_flags += self.get_always_args()
        # %% build the test executable
        pc = subprocess.Popen(self.exelist + extra_flags + [str(source_name), '-o', str(binary_name)])
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('Compiler %s can not compile programs.' % self.name_string())
        if self.is_cross:
            if self.exe_wrapper is None:
                # Can't check if the binaries run so we have to assume they do
                return
            cmdlist = self.exe_wrapper + [str(binary_name)]
        else:
            cmdlist = [str(binary_name)]
        # %% Run the test executable
        try:
            pe = subprocess.Popen(cmdlist, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            pe.wait()
            if pe.returncode != 0:
                raise EnvironmentException('Executables created by Fortran compiler %s are not runnable.' % self.name_string())
        except OSError:
            raise EnvironmentException('Executables created by Fortran compiler %s are not runnable.' % self.name_string())

    def get_std_warn_args(self, level):
        return FortranCompiler.std_warn_args

    def get_buildtype_args(self, buildtype):
        return gnulike_buildtype_args[buildtype]

    def get_optimization_args(self, optimization_level):
        return gnu_optimization_args[optimization_level]

    def get_debug_args(self, is_debug):
        return clike_debug_args[is_debug]

    def get_buildtype_linker_args(self, buildtype):
        if is_osx():
            return apple_buildtype_linker_args[buildtype]
        return gnulike_buildtype_linker_args[buildtype]

    def get_dependency_gen_args(self, outtarget, outfile):
        return []

    def get_preprocess_only_args(self):
        return ['-cpp'] + super().get_preprocess_only_args()

    def get_module_incdir_args(self):
        return ('-I', )

    def get_module_outdir_args(self, path):
        return ['-module', path]

    def compute_parameters_with_absolute_paths(self, parameter_list, build_dir):
        for idx, i in enumerate(parameter_list):
            if i[:2] == '-I' or i[:2] == '-L':
                parameter_list[idx] = i[:2] + os.path.normpath(os.path.join(build_dir, i[2:]))

        return parameter_list

    def module_name_to_filename(self, module_name: str) -> str:
        if '_' in module_name:  # submodule
            s = module_name.lower()
            if self.id in ('gcc', 'intel'):
                filename = s.replace('_', '@') + '.smod'
            elif self.id in ('pgi', 'flang'):
                filename = s.replace('_', '-') + '.mod'
            else:
                filename = s + '.mod'
        else:  # module
            filename = module_name.lower() + '.mod'

        return filename

    def find_library(self, libname, env, extra_dirs, libtype: LibType = LibType.PREFER_SHARED):
        code = '''program main
            call exit(0)
        end program main'''
        return self.find_library_impl(libname, env, extra_dirs, code, libtype)

    def has_multi_arguments(self, args, env):
        for arg in args[:]:
            # some compilers, e.g. GCC, don't warn for unsupported warning-disable
            # flags, so when we are testing a flag like "-Wno-forgotten-towel", also
            # check the equivalent enable flag too "-Wforgotten-towel"
            if arg.startswith('-Wno-'):
                args.append('-W' + arg[5:])
            if arg.startswith('-Wl,'):
                mlog.warning('{} looks like a linker argument, '
                             'but has_argument and other similar methods only '
                             'support checking compiler arguments. Using them '
                             'to check linker arguments are never supported, '
                             'and results are likely to be wrong regardless of '
                             'the compiler you are using. has_link_argument or '
                             'other similar method can be used instead.'
                             .format(arg))
        code = 'program main\ncall exit(0)\nend program main'
        return self.has_arguments(args, env, code, mode='compile')


class GnuFortranCompiler(GnuCompiler, FortranCompiler):
    def __init__(self, exelist, version, compiler_type, for_machine: MachineChoice, is_cross, exe_wrapper=None, defines=None, **kwargs):
        FortranCompiler.__init__(self, exelist, version, for_machine, is_cross, exe_wrapper, **kwargs)
        GnuCompiler.__init__(self, compiler_type, defines)
        default_warn_args = ['-Wall']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}

    def get_dependency_gen_args(self, outtarget, outfile):
        # Disabled until this is fixed:
        # https://gcc.gnu.org/bugzilla/show_bug.cgi?id=62162
        # return ['-cpp', '-MD', '-MQ', outtarget]
        return []

    def get_module_outdir_args(self, path):
        return ['-J' + path]

    def language_stdlib_only_link_flags(self):
        return ['-lgfortran', '-lm']

class ElbrusFortranCompiler(GnuFortranCompiler, ElbrusCompiler):
    def __init__(self, exelist, version, compiler_type, for_machine: MachineChoice, is_cross, exe_wrapper=None, defines=None, **kwargs):
        GnuFortranCompiler.__init__(self, exelist, version, compiler_type, for_machine, is_cross, exe_wrapper, defines, **kwargs)
        ElbrusCompiler.__init__(self, compiler_type, defines)

class G95FortranCompiler(FortranCompiler):
    def __init__(self, exelist, version, for_machine: MachineChoice, is_cross, exe_wrapper=None, **kwags):
        FortranCompiler.__init__(self, exelist, version, for_machine, is_cross, exe_wrapper, **kwags)
        self.id = 'g95'
        default_warn_args = ['-Wall']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-pedantic']}

    def get_module_outdir_args(self, path):
        return ['-fmod=' + path]

    def get_no_warn_args(self):
        # FIXME: Confirm that there's no compiler option to disable all warnings
        return []


class SunFortranCompiler(FortranCompiler):
    def __init__(self, exelist, version, for_machine: MachineChoice, is_cross, exe_wrapper=None, **kwags):
        FortranCompiler.__init__(self, exelist, version, for_machine, is_cross, exe_wrapper, **kwags)
        self.id = 'sun'

    def get_dependency_gen_args(self, outtarget, outfile):
        return ['-fpp']

    def get_always_args(self):
        return []

    def get_warn_args(self, level):
        return []

    def get_module_incdir_args(self):
        return ('-M', )

    def get_module_outdir_args(self, path):
        return ['-moddir=' + path]

    def openmp_flags(self):
        return ['-xopenmp']


class IntelFortranCompiler(IntelGnuLikeCompiler, FortranCompiler):
    def __init__(self, exelist, version, for_machine: MachineChoice, is_cross, exe_wrapper=None, **kwags):
        self.file_suffixes = ('f90', 'f', 'for', 'ftn', 'fpp')
        FortranCompiler.__init__(self, exelist, version, for_machine, is_cross, exe_wrapper, **kwags)
        # FIXME: Add support for OS X and Windows in detect_fortran_compiler so
        # we are sent the type of compiler
        IntelGnuLikeCompiler.__init__(self, CompilerType.ICC_STANDARD)
        self.id = 'intel'
        default_warn_args = ['-warn', 'general', '-warn', 'truncated_source']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args + ['-warn', 'unused'],
                          '3': ['-warn', 'all']}

    def get_preprocess_only_args(self):
        return ['-cpp', '-EP']

    def get_always_args(self):
        """Ifort doesn't have -pipe."""
        val = super().get_always_args()
        val.remove('-pipe')
        return val

    def language_stdlib_only_link_flags(self):
        return ['-lifcore', '-limf']

class IntelClFortranCompiler(IntelVisualStudioLikeCompiler, FortranCompiler):

    file_suffixes = ['f90', 'f', 'for', 'ftn', 'fpp']
    always_args = ['/nologo']

    BUILD_ARGS = {
        'plain': [],
        'debug': ["/Zi", "/Od"],
        'debugoptimized': ["/Zi", "/O1"],
        'release': ["/O2"],
        'minsize': ["/Os"],
        'custom': [],
    }

    def __init__(self, exelist, version, is_cross, target: str, exe_wrapper=None):
        FortranCompiler.__init__(self, exelist, version, is_cross, exe_wrapper)
        IntelVisualStudioLikeCompiler.__init__(self, target)

        default_warn_args = ['/warn:general', '/warn:truncated_source']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args + ['/warn:unused'],
                          '3': ['/warn:all']}

    def get_module_outdir_args(self, path) -> List[str]:
        return ['/module:' + path]

    def get_buildtype_args(self, buildtype: str) -> List[str]:
        return self.BUILD_ARGS[buildtype]


class PathScaleFortranCompiler(FortranCompiler):
    def __init__(self, exelist, version, for_machine: MachineChoice, is_cross, exe_wrapper=None, **kwags):
        FortranCompiler.__init__(self, exelist, version, for_machine, is_cross, exe_wrapper, **kwags)
        self.id = 'pathscale'
        default_warn_args = ['-fullwarn']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args,
                          '3': default_warn_args}

    def openmp_flags(self):
        return ['-mp']


class PGIFortranCompiler(PGICompiler, FortranCompiler):
    def __init__(self, exelist, version, compiler_type, for_machine: MachineChoice, is_cross, exe_wrapper=None, **kwags):
        FortranCompiler.__init__(self, exelist, version, for_machine, is_cross, exe_wrapper, **kwags)
        PGICompiler.__init__(self, compiler_type)

    def language_stdlib_only_link_flags(self) -> List[str]:
        return ['-lpgf90rtl', '-lpgf90', '-lpgf90_rpm1', '-lpgf902',
                '-lpgf90rtl', '-lpgftnrtl', '-lrt']

class FlangFortranCompiler(ClangCompiler, FortranCompiler):
    def __init__(self, exelist, version, for_machine: MachineChoice, is_cross, exe_wrapper=None, **kwags):
        FortranCompiler.__init__(self, exelist, version, for_machine, is_cross, exe_wrapper, **kwags)
        ClangCompiler.__init__(self, CompilerType.CLANG_STANDARD)
        self.id = 'flang'
        default_warn_args = ['-Minform=inform']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args,
                          '3': default_warn_args}

class Open64FortranCompiler(FortranCompiler):
    def __init__(self, exelist, version, for_machine: MachineChoice, is_cross, exe_wrapper=None, **kwags):
        FortranCompiler.__init__(self, exelist, version, for_machine, is_cross, exe_wrapper, **kwags)
        self.id = 'open64'
        default_warn_args = ['-fullwarn']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args,
                          '3': default_warn_args}

    def openmp_flags(self):
        return ['-mp']


class NAGFortranCompiler(FortranCompiler):
    def __init__(self, exelist, version, for_machine: MachineChoice, is_cross, exe_wrapper=None, **kwags):
        FortranCompiler.__init__(self, exelist, version, for_machine, is_cross, exe_wrapper, **kwags)
        self.id = 'nagfor'

    def get_warn_args(self, level):
        return []

    def get_module_outdir_args(self, path):
        return ['-mdir', path]

    def openmp_flags(self):
        return ['-openmp']
