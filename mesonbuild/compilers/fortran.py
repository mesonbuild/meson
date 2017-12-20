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

from ..mesonlib import EnvironmentException, is_osx

from .compilers import (
    GCC_CYGWIN,
    GCC_MINGW,
    GCC_OSX,
    GCC_STANDARD,
    ICC_STANDARD,
    apple_buildtype_linker_args,
    get_gcc_soname_args,
    gnulike_buildtype_args,
    gnulike_buildtype_linker_args,
    Compiler,
    IntelCompiler,
)

class FortranCompiler(Compiler):
    def __init__(self, exelist, version, is_cross, exe_wrapper=None, **kwargs):
        self.language = 'fortran'
        super().__init__(exelist, version, **kwargs)
        self.is_cross = is_cross
        self.exe_wrapper = exe_wrapper
        # Not really correct but I don't have Fortran compilers to test with. Sorry.
        self.gcc_type = GCC_STANDARD
        self.id = "IMPLEMENTATION CLASSES MUST SET THIS"

    def name_string(self):
        return ' '.join(self.exelist)

    def get_pic_args(self):
        if self.gcc_type in (GCC_CYGWIN, GCC_MINGW, GCC_OSX):
            return [] # On Window and OS X, pic is always on.
        return ['-fPIC']

    def get_std_shared_lib_link_args(self):
        return ['-shared']

    def needs_static_linker(self):
        return True

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

    def get_buildtype_linker_args(self, buildtype):
        if is_osx():
            return apple_buildtype_linker_args[buildtype]
        return gnulike_buildtype_linker_args[buildtype]

    def split_shlib_to_parts(self, fname):
        return os.path.split(fname)[0], fname

    def get_soname_args(self, prefix, shlib_name, suffix, path, soversion, is_shared_module):
        return get_gcc_soname_args(self.gcc_type, prefix, shlib_name, suffix, path, soversion, is_shared_module)

    def get_dependency_gen_args(self, outtarget, outfile):
        # Disabled until this is fixed:
        # https://gcc.gnu.org/bugzilla/show_bug.cgi?id=62162
        # return ['-cpp', '-MD', '-MQ', outtarget]
        return []

    def get_output_args(self, target):
        return ['-o', target]

    def get_preprocess_only_args(self):
        return ['-E']

    def get_compile_only_args(self):
        return ['-c']

    def get_linker_exelist(self):
        return self.exelist[:]

    def get_linker_output_args(self, outputname):
        return ['-o', outputname]

    def get_include_args(self, path, is_system):
        return ['-I' + path]

    def get_module_incdir_args(self):
        return ('-I', )

    def get_module_outdir_args(self, path):
        return ['-J' + path]

    def depfile_for_object(self, objfile):
        return objfile + '.' + self.get_depfile_suffix()

    def get_depfile_suffix(self):
        return 'd'

    def get_std_exe_link_args(self):
        return []

    def build_rpath_args(self, build_dir, from_dir, rpath_paths, build_rpath, install_rpath):
        return self.build_unix_rpath_args(build_dir, from_dir, rpath_paths, build_rpath, install_rpath)

    def module_name_to_filename(self, module_name):
        return module_name.lower() + '.mod'

    def get_warn_args(self, level):
        return ['-Wall']

    def get_no_warn_args(self):
        return ['-w']


class GnuFortranCompiler(FortranCompiler):
    def __init__(self, exelist, version, gcc_type, is_cross, exe_wrapper=None, defines=None, **kwargs):
        super().__init__(exelist, version, is_cross, exe_wrapper=None, **kwargs)
        self.gcc_type = gcc_type
        self.defines = defines or {}
        self.id = 'gcc'

    def has_builtin_define(self, define):
        return define in self.defines

    def get_builtin_define(self, define):
        if define in self.defines:
            return self.defines[define]

    def get_always_args(self):
        return ['-pipe']

    def get_coverage_args(self):
        return ['--coverage']

    def get_coverage_link_args(self):
        return ['--coverage']

    def gen_import_library_args(self, implibname):
        """
        The name of the outputted import library

        Used only on Windows
        """
        return ['-Wl,--out-implib=' + implibname]


class G95FortranCompiler(FortranCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrapper=None, **kwags):
        super().__init__(exelist, version, is_cross, exe_wrapper=None, **kwags)
        self.id = 'g95'

    def get_module_outdir_args(self, path):
        return ['-fmod=' + path]

    def get_always_args(self):
        return ['-pipe']

    def get_no_warn_args(self):
        # FIXME: Confirm that there's no compiler option to disable all warnings
        return []

    def gen_import_library_args(self, implibname):
        """
        The name of the outputted import library

        Used only on Windows
        """
        return ['-Wl,--out-implib=' + implibname]


class SunFortranCompiler(FortranCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrapper=None, **kwags):
        super().__init__(exelist, version, is_cross, exe_wrapper=None, **kwags)
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


class IntelFortranCompiler(IntelCompiler, FortranCompiler):
    std_warn_args = ['-warn', 'all']

    def __init__(self, exelist, version, is_cross, exe_wrapper=None, **kwags):
        self.file_suffixes = ('f90', 'f', 'for', 'ftn', 'fpp')
        FortranCompiler.__init__(self, exelist, version, is_cross, exe_wrapper, **kwags)
        # FIXME: Add support for OS X and Windows in detect_fortran_compiler so
        # we are sent the type of compiler
        IntelCompiler.__init__(self, ICC_STANDARD)
        self.id = 'intel'

    def get_module_outdir_args(self, path):
        return ['-module', path]

    def get_warn_args(self, level):
        return IntelFortranCompiler.std_warn_args


class PathScaleFortranCompiler(FortranCompiler):
    std_warn_args = ['-fullwarn']

    def __init__(self, exelist, version, is_cross, exe_wrapper=None, **kwags):
        super().__init__(exelist, version, is_cross, exe_wrapper=None, **kwags)
        self.id = 'pathscale'

    def get_module_outdir_args(self, path):
        return ['-module', path]

    def get_std_warn_args(self, level):
        return PathScaleFortranCompiler.std_warn_args

class PGIFortranCompiler(FortranCompiler):
    std_warn_args = ['-Minform=inform']

    def __init__(self, exelist, version, is_cross, exe_wrapper=None, **kwags):
        super().__init__(exelist, version, is_cross, exe_wrapper=None, **kwags)
        self.id = 'pgi'

    def get_module_incdir_args(self):
        return ('-module', )

    def get_module_outdir_args(self, path):
        return ['-module', path]

    def get_warn_args(self, level):
        return PGIFortranCompiler.std_warn_args

    def get_no_warn_args(self):
        return ['-silent']


class Open64FortranCompiler(FortranCompiler):
    std_warn_args = ['-fullwarn']

    def __init__(self, exelist, version, is_cross, exe_wrapper=None, **kwags):
        super().__init__(exelist, version, is_cross, exe_wrapper=None, **kwags)
        self.id = 'open64'

    def get_module_outdir_args(self, path):
        return ['-module', path]

    def get_warn_args(self, level):
        return Open64FortranCompiler.std_warn_args


class NAGFortranCompiler(FortranCompiler):
    std_warn_args = []

    def __init__(self, exelist, version, is_cross, exe_wrapper=None, **kwags):
        super().__init__(exelist, version, is_cross, exe_wrapper=None, **kwags)
        self.id = 'nagfor'

    def get_module_outdir_args(self, path):
        return ['-mdir', path]

    def get_warn_args(self, level):
        return NAGFortranCompiler.std_warn_args
