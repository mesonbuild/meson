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

from .c import CCompiler
from .compilers import (
    CompilerType,
    apple_buildtype_linker_args,
    gnulike_buildtype_args,
    gnulike_buildtype_linker_args,
    gnu_optimization_args,
    clike_debug_args,
    Compiler,
    GnuCompiler,
    ElbrusCompiler,
    IntelCompiler,
)

from mesonbuild.mesonlib import EnvironmentException, is_osx
import subprocess, os

class FortranCompiler(Compiler):
    library_dirs_cache = CCompiler.library_dirs_cache
    program_dirs_cache = CCompiler.library_dirs_cache
    find_library_cache = CCompiler.library_dirs_cache

    def __init__(self, exelist, version, is_cross, exe_wrapper=None, **kwargs):
        self.language = 'fortran'
        Compiler.__init__(self, exelist, version, **kwargs)
        cc = CCompiler(exelist, version, is_cross, exe_wrapper, **kwargs)
        self.id = 'unknown'
        self.is_cross = cc.is_cross
        self.exe_wrapper = cc.exe_wrapper

    def get_display_language(self):
        return 'Fortran'

    def needs_static_linker(self):
        return CCompiler.needs_static_linker(self)

    def get_always_args(self):
        return CCompiler.get_always_args(self)

    def get_linker_debug_crt_args(self):
        return CCompiler.get_linker_debug_crt_args(self)

    def get_no_stdinc_args(self):
        return CCompiler.get_no_stdinc_args(self)

    def get_no_stdlib_link_args(self):
        return CCompiler.get_no_stdlib_link_args(self)

    def get_warn_args(self, level):
        return CCompiler.get_warn_args(self, level)

    def get_no_warn_args(self):
        return CCompiler.get_no_warn_args(self)

    def get_soname_args(self, *args):
        return CCompiler.get_soname_args(self, *args)

    def sanity_check(self, work_dir, environment):
        source_name = os.path.join(work_dir, 'sanitycheckf.f90')
        binary_name = os.path.join(work_dir, 'sanitycheckf')
        with open(source_name, 'w') as ofile:
            ofile.write('''program prog
     print *, "Fortran compilation is working."
end program prog
''')
        extra_flags = self.get_cross_extra_flags(environment, link=True)
        pc = subprocess.Popen(self.exelist + extra_flags + [source_name, '-o', binary_name])
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('Compiler %s can not compile programs.' % self.name_string())
        if self.is_cross:
            if self.exe_wrapper is None:
                # Can't check if the binaries run so we have to assume they do
                return
            cmdlist = self.exe_wrapper + [binary_name]
        else:
            cmdlist = [binary_name]
        pe = subprocess.Popen(cmdlist, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        pe.wait()
        if pe.returncode != 0:
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

    def split_shlib_to_parts(self, fname):
        return CCompiler.split_shlib_to_parts(self, fname)

    def build_rpath_args(self, *args):
        return CCompiler.build_rpath_args(self, *args)

    def get_dependency_gen_args(self, outtarget, outfile):
        return []

    def depfile_for_object(self, objfile):
        return CCompiler.depfile_for_object(self, objfile)

    def get_depfile_suffix(self):
        return CCompiler.get_depfile_suffix(self)

    def get_exelist(self):
        return CCompiler.get_exelist(self)

    def get_linker_exelist(self):
        return CCompiler.get_linker_exelist(self)

    def get_preprocess_only_args(self):
        return ['-cpp'] + CCompiler.get_preprocess_only_args(self)

    def get_compile_only_args(self):
        return CCompiler.get_compile_only_args(self)

    def get_no_optimization_args(self):
        return CCompiler.get_no_optimization_args(self)

    def get_compiler_check_args(self):
        return CCompiler.get_compiler_check_args(self)

    def get_allow_undefined_link_args(self):
        return CCompiler.get_allow_undefined_link_args(self)

    def get_output_args(self, target):
        return CCompiler.get_output_args(self, target)

    def get_linker_output_args(self, outputname):
        return CCompiler.get_linker_output_args(self, outputname)

    def get_coverage_args(self):
        return CCompiler.get_coverage_args(self)

    def get_coverage_link_args(self):
        return CCompiler.get_coverage_link_args(self)

    def get_werror_args(self):
        return CCompiler.get_werror_args(self)

    def get_std_exe_link_args(self):
        return CCompiler.get_std_exe_link_args(self)

    def get_include_args(self, path, is_system):
        return CCompiler.get_include_args(self, path, is_system)

    def get_module_incdir_args(self):
        return ('-I', )

    def get_module_outdir_args(self, path):
        return ['-module' + path]

    def module_name_to_filename(self, module_name):
        return module_name.lower() + '.mod'

    def get_std_shared_lib_link_args(self):
        return CCompiler.get_std_shared_lib_link_args(self)

    def _get_search_dirs(self, *args, **kwargs):
        return CCompiler._get_search_dirs(self, *args, **kwargs)

    def get_compiler_dirs(self, *args, **kwargs):
        return CCompiler.get_compiler_dirs(self, *args, **kwargs)

    def get_library_dirs(self, *args, **kwargs):
        return CCompiler.get_library_dirs(self, *args, **kwargs)

    def get_pic_args(self):
        return CCompiler.get_pic_args(self)

    def name_string(self):
        return CCompiler.name_string(self)

    def get_linker_search_args(self, dirname):
        return CCompiler.get_linker_search_args(self, dirname)

    def get_default_include_dirs(self):
        return CCompiler.get_default_include_dirs(self)

    def gen_export_dynamic_link_args(self, env):
        return CCompiler.gen_export_dynamic_link_args(self, env)

    def gen_import_library_args(self, implibname):
        return CCompiler.gen_import_library_args(self, implibname)

    def _get_compiler_check_args(self, env, extra_args, dependencies, mode='compile'):
        return CCompiler._get_compiler_check_args(self, env, extra_args, dependencies, mode='compile')

    def compiles(self, code, env, extra_args=None, dependencies=None, mode='compile'):
        return CCompiler.compiles(self, code, env, extra_args, dependencies, mode)

    def _build_wrapper(self, code, env, extra_args, dependencies=None, mode='compile', want_output=False):
        return CCompiler._build_wrapper(self, code, env, extra_args, dependencies, mode, want_output)

    def links(self, code, env, extra_args=None, dependencies=None):
        return CCompiler.links(self, code, env, extra_args, dependencies)

    def run(self, code, env, extra_args=None, dependencies=None):
        return CCompiler.run(self, code, env, extra_args, dependencies)

    def _get_patterns(self, *args, **kwargs):
        return CCompiler._get_patterns(self, *args, **kwargs)

    def get_library_naming(self, *args, **kwargs):
        return CCompiler.get_library_naming(self, *args, **kwargs)

    def find_library_real(self, *args):
        return CCompiler.find_library_real(self, *args)

    def find_library_impl(self, *args):
        return CCompiler.find_library_impl(self, *args)

    def find_library(self, libname, env, extra_dirs, libtype='default'):
        code = '''program main
            call exit(0)
        end program main'''
        return self.find_library_impl(libname, env, extra_dirs, code, libtype)

    def thread_flags(self, env):
        return CCompiler.thread_flags(self, env)

    def thread_link_flags(self, env):
        return CCompiler.thread_link_flags(self, env)

    def linker_to_compiler_args(self, args):
        return CCompiler.linker_to_compiler_args(self, args)

    def has_arguments(self, args, env, code, mode):
        return CCompiler.has_arguments(self, args, env, code, mode)

    def has_multi_arguments(self, args, env):
        return CCompiler.has_multi_arguments(self, args, env)


class GnuFortranCompiler(GnuCompiler, FortranCompiler):
    def __init__(self, exelist, version, compiler_type, is_cross, exe_wrapper=None, defines=None, **kwargs):
        FortranCompiler.__init__(self, exelist, version, is_cross, exe_wrapper, **kwargs)
        GnuCompiler.__init__(self, compiler_type, defines)
        default_warn_args = ['-Wall']
        self.warn_args = {'1': default_warn_args,
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
    def __init__(self, exelist, version, compiler_type, is_cross, exe_wrapper=None, defines=None, **kwargs):
        GnuFortranCompiler.__init__(self, exelist, version, compiler_type, is_cross, exe_wrapper, defines, **kwargs)
        ElbrusCompiler.__init__(self, compiler_type, defines)

class G95FortranCompiler(FortranCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrapper=None, **kwags):
        FortranCompiler.__init__(self, exelist, version, is_cross, exe_wrapper, **kwags)
        self.id = 'g95'
        default_warn_args = ['-Wall']
        self.warn_args = {'1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-pedantic']}

    def get_module_outdir_args(self, path):
        return ['-fmod=' + path]

    def get_no_warn_args(self):
        # FIXME: Confirm that there's no compiler option to disable all warnings
        return []


class SunFortranCompiler(FortranCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrapper=None, **kwags):
        FortranCompiler.__init__(self, exelist, version, is_cross, exe_wrapper, **kwags)
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


class IntelFortranCompiler(IntelCompiler, FortranCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrapper=None, **kwags):
        self.file_suffixes = ('f90', 'f', 'for', 'ftn', 'fpp')
        FortranCompiler.__init__(self, exelist, version, is_cross, exe_wrapper, **kwags)
        # FIXME: Add support for OS X and Windows in detect_fortran_compiler so
        # we are sent the type of compiler
        IntelCompiler.__init__(self, CompilerType.ICC_STANDARD)
        self.id = 'intel'
        default_warn_args = ['-warn', 'general', '-warn', 'truncated_source']
        self.warn_args = {'1': default_warn_args,
                          '2': default_warn_args + ['-warn', 'unused'],
                          '3': ['-warn', 'all']}

    def get_preprocess_only_args(self):
        return ['-cpp', '-EP']


class PathScaleFortranCompiler(FortranCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrapper=None, **kwags):
        FortranCompiler.__init__(self, exelist, version, is_cross, exe_wrapper, **kwags)
        self.id = 'pathscale'
        default_warn_args = ['-fullwarn']
        self.warn_args = {'1': default_warn_args,
                          '2': default_warn_args,
                          '3': default_warn_args}

    def openmp_flags(self):
        return ['-mp']


class PGIFortranCompiler(FortranCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrapper=None, **kwags):
        FortranCompiler.__init__(self, exelist, version, is_cross, exe_wrapper, **kwags)
        self.id = 'pgi'
        default_warn_args = ['-Minform=inform']
        self.warn_args = {'1': default_warn_args,
                          '2': default_warn_args,
                          '3': default_warn_args}

    def get_module_incdir_args(self):
        return ('-module', )

    def get_no_warn_args(self):
        return ['-silent']

    def openmp_flags(self):
        return ['-fopenmp']


class Open64FortranCompiler(FortranCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrapper=None, **kwags):
        FortranCompiler.__init__(self, exelist, version, is_cross, exe_wrapper, **kwags)
        self.id = 'open64'
        default_warn_args = ['-fullwarn']
        self.warn_args = {'1': default_warn_args,
                          '2': default_warn_args,
                          '3': default_warn_args}

    def openmp_flags(self):
        return ['-mp']


class NAGFortranCompiler(FortranCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrapper=None, **kwags):
        FortranCompiler.__init__(self, exelist, version, is_cross, exe_wrapper, **kwags)
        self.id = 'nagfor'

    def get_warn_args(self, level):
        return []

    def get_module_outdir_args(self, path):
        return ['-mdir', path]

    def openmp_flags(self):
        return ['-openmp']
