# Copyright 2012-2016 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os, re, subprocess
from . import coredata, mesonlib
from .compilers import *
import configparser

build_filename = 'meson.build'

class EnvironmentException(mesonlib.MesonException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

def find_coverage_tools():
    gcovr_exe = 'gcovr'
    lcov_exe = 'lcov'
    genhtml_exe = 'genhtml'

    if not mesonlib.exe_exists([gcovr_exe, '--version']):
        gcovr_exe = None
    if not mesonlib.exe_exists([lcov_exe, '--version']):
        lcov_exe = None
    if not mesonlib.exe_exists([genhtml_exe, '--version']):
        genhtml_exe = None
    return (gcovr_exe, lcov_exe, genhtml_exe)

def find_valgrind():
    valgrind_exe = 'valgrind'
    if not mesonlib.exe_exists([valgrind_exe, '--version']):
        valgrind_exe = None
    return valgrind_exe

def detect_ninja():
    for n in ['ninja', 'ninja-build']:
        try:
            p = subprocess.Popen([n, '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            continue
        p.communicate()
        if p.returncode == 0:
            return n


class Environment():
    private_dir = 'meson-private'
    log_dir = 'meson-logs'
    coredata_file = os.path.join(private_dir, 'coredata.dat')
    version_regex = '\d+(\.\d+)+(-[a-zA-Z0-9]+)?'
    def __init__(self, source_dir, build_dir, main_script_file, options, original_cmd_line_args):
        assert(os.path.isabs(main_script_file))
        assert(not os.path.islink(main_script_file))
        self.source_dir = source_dir
        self.build_dir = build_dir
        self.meson_script_file = main_script_file
        self.scratch_dir = os.path.join(build_dir, Environment.private_dir)
        self.log_dir = os.path.join(build_dir, Environment.log_dir)
        os.makedirs(self.scratch_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)
        try:
            cdf = os.path.join(self.get_build_dir(), Environment.coredata_file)
            self.coredata = coredata.load(cdf)
            self.first_invocation = False
        except FileNotFoundError:
            self.coredata = coredata.CoreData(options)
            self.first_invocation = True
        if self.coredata.cross_file:
            self.cross_info = CrossBuildInfo(self.coredata.cross_file)
        else:
            self.cross_info = None
        self.cmd_line_options = options
        self.original_cmd_line_args = original_cmd_line_args

        # List of potential compilers.
        if mesonlib.is_windows():
            self.default_c = ['cl', 'cc', 'gcc', 'clang']
            self.default_cpp = ['cl', 'c++', 'g++', 'clang++']
        else:
            self.default_c = ['cc']
            self.default_cpp = ['c++']
        self.default_objc = ['cc']
        self.default_objcpp = ['c++']
        self.default_fortran = ['gfortran', 'g95', 'f95', 'f90', 'f77']
        self.default_static_linker = 'ar'
        self.vs_static_linker = 'lib'

        cross = self.is_cross_build()
        if (not cross and mesonlib.is_windows()) \
        or (cross and self.cross_info.has_host() and self.cross_info.config['host_machine']['system'] == 'windows'):
            self.exe_suffix = 'exe'
            if self.detect_c_compiler(cross).get_id() == 'msvc':
                self.import_lib_suffix = 'lib'
            else:
                # MinGW-GCC doesn't generate and can't link with a .lib
                # It uses the DLL file as the import library
                self.import_lib_suffix = 'dll'
            self.shared_lib_suffix = 'dll'
            self.shared_lib_prefix = ''
            self.static_lib_suffix = 'lib'
            self.static_lib_prefix = ''
            self.object_suffix = 'obj'
        else:
            self.exe_suffix = ''
            if (not cross and mesonlib.is_osx()) or \
            (cross and self.cross_info.has_host() and self.cross_info.config['host_machine']['system'] == 'darwin'):
                self.shared_lib_suffix = 'dylib'
            else:
                self.shared_lib_suffix = 'so'
            self.shared_lib_prefix = 'lib'
            self.static_lib_suffix = 'a'
            self.static_lib_prefix = 'lib'
            self.object_suffix = 'o'
            self.import_lib_suffix = self.shared_lib_suffix

    def is_cross_build(self):
        return self.cross_info is not None

    def dump_coredata(self):
        cdf = os.path.join(self.get_build_dir(), Environment.coredata_file)
        coredata.save(self.coredata, cdf)

    def get_script_dir(self):
        return os.path.join(os.path.dirname(self.meson_script_file), '../scripts')

    def get_log_dir(self):
        return self.log_dir

    def get_coredata(self):
        return self.coredata

    def get_build_command(self):
        return self.meson_script_file

    def is_header(self, fname):
        return is_header(fname)

    def is_source(self, fname):
        return is_source(fname)

    def is_object(self, fname):
        return is_object(fname)

    def is_library(self, fname):
        return is_library(fname)

    def had_argument_for(self, option):
        trial1 = '--' + option
        trial2 = '-D' + option
        previous_is_plaind = False
        for i in self.original_cmd_line_args:
            if i.startswith(trial1) or i.startswith(trial2):
                return True
            if previous_is_plaind and i.startswith(option):
                return True
            previous_is_plaind = i == '-D'
        return False

    def merge_options(self, options):
        for (name, value) in options.items():
            if name not in self.coredata.user_options:
                self.coredata.user_options[name] = value
            else:
                oldval = self.coredata.user_options[name]
                if type(oldval) != type(value):
                    self.coredata.user_options[name] = value

    def detect_c_compiler(self, want_cross):
        evar = 'CC'
        if self.is_cross_build() and want_cross:
            compilers = [self.cross_info.config['binaries']['c']]
            ccache = []
            is_cross = True
            exe_wrap = self.cross_info.config['binaries'].get('exe_wrapper', None)
        elif evar in os.environ:
            compilers = os.environ[evar].split()
            ccache = []
            is_cross = False
            exe_wrap = None
        else:
            compilers = self.default_c
            ccache = self.detect_ccache()
            is_cross = False
            exe_wrap = None
        popen_exceptions = {}
        for compiler in compilers:
            try:
                basename = os.path.basename(compiler).lower()
                if basename == 'cl' or basename == 'cl.exe':
                    arg = '/?'
                else:
                    arg = '--version'
                p = subprocess.Popen([compiler, arg], stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
            except OSError as e:
                popen_exceptions[' '.join([compiler, arg])] = e
                continue
            (out, err) = p.communicate()
            out = out.decode(errors='ignore')
            err = err.decode(errors='ignore')
            vmatch = re.search(Environment.version_regex, out)
            if vmatch:
                version = vmatch.group(0)
            else:
                version = 'unknown version'
            if 'apple' in out and 'Free Software Foundation' in out:
                return GnuCCompiler(ccache + [compiler], version, GCC_OSX, is_cross, exe_wrap)
            if (out.startswith('cc') or 'gcc' in out) and \
                'Free Software Foundation' in out:
                lowerout = out.lower()
                if 'mingw' in lowerout or 'msys' in lowerout or 'mingw' in compiler.lower():
                    gtype = GCC_MINGW
                else:
                    gtype = GCC_STANDARD
                return GnuCCompiler(ccache + [compiler], version, gtype, is_cross, exe_wrap)
            if 'clang' in out:
                if 'Apple' in out:
                    cltype = CLANG_OSX
                else:
                    cltype = CLANG_STANDARD
                return ClangCCompiler(ccache + [compiler], version, cltype, is_cross, exe_wrap)
            if 'Microsoft' in out or 'Microsoft' in err:
                # Visual Studio prints version number to stderr but
                # everything else to stdout. Why? Lord only knows.
                version = re.search(Environment.version_regex, err).group()
                return VisualStudioCCompiler([compiler], version, is_cross, exe_wrap)
        errmsg = 'Unknown compiler(s): "' + ', '.join(compilers) + '"'
        if popen_exceptions:
            errmsg += '\nThe follow exceptions were encountered:'
            for (c, e) in popen_exceptions.items():
                errmsg += '\nRunning "{0}" gave "{1}"'.format(c, e)
        raise EnvironmentException(errmsg)

    def detect_fortran_compiler(self, want_cross):
        evar = 'FC'
        if self.is_cross_build() and want_cross:
            compilers = [self.cross_info['fortran']]
            is_cross = True
            exe_wrap = self.cross_info.get('exe_wrapper', None)
        elif evar in os.environ:
            compilers = os.environ[evar].split()
            is_cross = False
            exe_wrap = None
        else:
            compilers = self.default_fortran
            is_cross = False
            exe_wrap = None
        popen_exceptions = {}
        for compiler in compilers:
            for arg in ['--version', '-V']:
                try:
                    p = subprocess.Popen([compiler, arg],
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
                except OSError as e:
                    popen_exceptions[' '.join([compiler, arg])] = e
                    continue
                (out, err) = p.communicate()
                out = out.decode(errors='ignore')
                err = err.decode(errors='ignore')

                version = 'unknown version'
                vmatch = re.search(Environment.version_regex, out)
                if vmatch:
                    version = vmatch.group(0)

                if 'GNU Fortran' in out:
                    return GnuFortranCompiler([compiler], version, GCC_STANDARD, is_cross, exe_wrap)

                if 'G95' in out:
                    return G95FortranCompiler([compiler], version, is_cross, exe_wrap)

                if 'Sun Fortran' in err:
                    version = 'unknown version'
                    vmatch = re.search(Environment.version_regex, err)
                    if vmatch:
                        version = vmatch.group(0)
                    return SunFortranCompiler([compiler], version, is_cross, exe_wrap)

                if 'ifort (IFORT)' in out:
                    return IntelFortranCompiler([compiler], version, is_cross, exe_wrap)

                if 'PathScale EKOPath(tm)' in err:
                    return PathScaleFortranCompiler([compiler], version, is_cross, exe_wrap)

                if 'pgf90' in out:
                    return PGIFortranCompiler([compiler], version, is_cross, exe_wrap)

                if 'Open64 Compiler Suite' in err:
                    return Open64FortranCompiler([compiler], version, is_cross, exe_wrap)

                if 'NAG Fortran' in err:
                    return NAGFortranCompiler([compiler], version, is_cross, exe_wrap)
        errmsg = 'Unknown compiler(s): "' + ', '.join(compilers) + '"'
        if popen_exceptions:
            errmsg += '\nThe follow exceptions were encountered:'
            for (c, e) in popen_exceptions.items():
                errmsg += '\nRunning "{0}" gave "{1}"'.format(c, e)
        raise EnvironmentException(errmsg)

    def get_scratch_dir(self):
        return self.scratch_dir

    def get_depfixer(self):
        path = os.path.split(__file__)[0]
        return os.path.join(path, 'depfixer.py')

    def detect_cpp_compiler(self, want_cross):
        evar = 'CXX'
        if self.is_cross_build() and want_cross:
            compilers = [self.cross_info.config['binaries']['cpp']]
            ccache = []
            is_cross = True
            exe_wrap = self.cross_info.config['binaries'].get('exe_wrapper', None)
        elif evar in os.environ:
            compilers = os.environ[evar].split()
            ccache = []
            is_cross = False
            exe_wrap = None
        else:
            compilers = self.default_cpp
            ccache = self.detect_ccache()
            is_cross = False
            exe_wrap = None
        popen_exceptions = {}
        for compiler in compilers:
            basename = os.path.basename(compiler).lower()
            if basename == 'cl' or basename == 'cl.exe':
                arg = '/?'
            else:
                arg = '--version'
            try:
                p = subprocess.Popen([compiler, arg],
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
            except OSError as e:
                popen_exceptions[' '.join([compiler, arg])] = e
                continue
            (out, err) = p.communicate()
            out = out.decode(errors='ignore')
            err = err.decode(errors='ignore')
            vmatch = re.search(Environment.version_regex, out)
            if vmatch:
                version = vmatch.group(0)
            else:
                version = 'unknown version'
            if 'apple' in out and 'Free Software Foundation' in out:
                return GnuCPPCompiler(ccache + [compiler], version, GCC_OSX, is_cross, exe_wrap)
            if (out.startswith('c++ ') or 'g++' in out or 'GCC' in out) and \
                'Free Software Foundation' in out:
                lowerout = out.lower()
                if 'mingw' in lowerout or 'msys' in lowerout or 'mingw' in compiler.lower():
                    gtype = GCC_MINGW
                else:
                    gtype = GCC_STANDARD
                return GnuCPPCompiler(ccache + [compiler], version, gtype, is_cross, exe_wrap)
            if 'clang' in out:
                if 'Apple' in out:
                    cltype = CLANG_OSX
                else:
                    cltype = CLANG_STANDARD
                return ClangCPPCompiler(ccache + [compiler], version, cltype, is_cross, exe_wrap)
            if 'Microsoft' in out or 'Microsoft' in err:
                version = re.search(Environment.version_regex, err).group()
                return VisualStudioCPPCompiler([compiler], version, is_cross, exe_wrap)
        errmsg = 'Unknown compiler(s): "' + ', '.join(compilers) + '"'
        if popen_exceptions:
            errmsg += '\nThe follow exceptions were encountered:'
            for (c, e) in popen_exceptions.items():
                errmsg += '\nRunning "{0}" gave "{1}"'.format(c, e)
        raise EnvironmentException(errmsg)

    def detect_objc_compiler(self, want_cross):
        if self.is_cross_build() and want_cross:
            exelist = [self.cross_info['objc']]
            is_cross = True
            exe_wrap = self.cross_info.get('exe_wrapper', None)
        else:
            exelist = self.get_objc_compiler_exelist()
            is_cross = False
            exe_wrap = None
        try:
            p = subprocess.Popen(exelist + ['--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            raise EnvironmentException('Could not execute ObjC compiler "%s"' % ' '.join(exelist))
        (out, err) = p.communicate()
        out = out.decode(errors='ignore')
        err = err.decode(errors='ignore')
        vmatch = re.search(Environment.version_regex, out)
        if vmatch:
            version = vmatch.group(0)
        else:
            version = 'unknown version'
        if (out.startswith('cc ') or 'gcc' in out) and \
            'Free Software Foundation' in out:
            return GnuObjCCompiler(exelist, version, is_cross, exe_wrap)
        if out.startswith('Apple LLVM'):
            return ClangObjCCompiler(exelist, version, CLANG_OSX, is_cross, exe_wrap)
        if 'apple' in out and 'Free Software Foundation' in out:
            return GnuObjCCompiler(exelist, version, is_cross, exe_wrap)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_objcpp_compiler(self, want_cross):
        if self.is_cross_build() and want_cross:
            exelist = [self.cross_info['objcpp']]
            is_cross = True
            exe_wrap = self.cross_info.get('exe_wrapper', None)
        else:
            exelist = self.get_objcpp_compiler_exelist()
            is_cross = False
            exe_wrap = None
        try:
            p = subprocess.Popen(exelist + ['--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            raise EnvironmentException('Could not execute ObjC++ compiler "%s"' % ' '.join(exelist))
        (out, err) = p.communicate()
        out = out.decode(errors='ignore')
        err = err.decode(errors='ignore')
        vmatch = re.search(Environment.version_regex, out)
        if vmatch:
            version = vmatch.group(0)
        else:
            version = 'unknown version'
        if (out.startswith('c++ ') or out.startswith('g++')) and \
            'Free Software Foundation' in out:
            return GnuObjCPPCompiler(exelist, version, is_cross, exe_wrap)
        if out.startswith('Apple LLVM'):
            return ClangObjCPPCompiler(exelist, version, CLANG_OSX, is_cross, exe_wrap)
        if 'apple' in out and 'Free Software Foundation' in out:
            return GnuObjCPPCompiler(exelist, version, is_cross, exe_wrap)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_java_compiler(self):
        exelist = ['javac']
        try:
            p = subprocess.Popen(exelist + ['-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            raise EnvironmentException('Could not execute Java compiler "%s"' % ' '.join(exelist))
        (out, err) = p.communicate()
        out = out.decode(errors='ignore')
        err = err.decode(errors='ignore')
        vmatch = re.search(Environment.version_regex, err)
        if vmatch:
            version = vmatch.group(0)
        else:
            version = 'unknown version'
        if 'javac' in err:
            return JavaCompiler(exelist, version)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_cs_compiler(self):
        exelist = ['mcs']
        try:
            p = subprocess.Popen(exelist + ['--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            raise EnvironmentException('Could not execute C# compiler "%s"' % ' '.join(exelist))
        (out, err) = p.communicate()
        out = out.decode(errors='ignore')
        err = err.decode(errors='ignore')
        vmatch = re.search(Environment.version_regex, out)
        if vmatch:
            version = vmatch.group(0)
        else:
            version = 'unknown version'
        if 'Mono' in out:
            return MonoCompiler(exelist, version)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_vala_compiler(self):
        exelist = ['valac']
        try:
            p = subprocess.Popen(exelist + ['--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            raise EnvironmentException('Could not execute Vala compiler "%s"' % ' '.join(exelist))
        (out, _) = p.communicate()
        out = out.decode(errors='ignore')
        vmatch = re.search(Environment.version_regex, out)
        if vmatch:
            version = vmatch.group(0)
        else:
            version = 'unknown version'
        if 'Vala' in out:
            return ValaCompiler(exelist, version)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_rust_compiler(self):
        exelist = ['rustc']
        try:
            p = subprocess.Popen(exelist + ['--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            raise EnvironmentException('Could not execute Rust compiler "%s"' % ' '.join(exelist))
        (out, _) = p.communicate()
        out = out.decode(errors='ignore')
        vmatch = re.search(Environment.version_regex, out)
        if vmatch:
            version = vmatch.group(0)
        else:
            version = 'unknown version'
        if 'rustc' in out:
            return RustCompiler(exelist, version)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_swift_compiler(self):
        exelist = ['swiftc']
        try:
            p = subprocess.Popen(exelist + ['-v'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            raise EnvironmentException('Could not execute Swift compiler "%s"' % ' '.join(exelist))
        (_, err) = p.communicate()
        err = err.decode(errors='ignore')
        vmatch = re.search(Environment.version_regex, err)
        if vmatch:
            version = vmatch.group(0)
        else:
            version = 'unknown version'
        if 'Swift' in err:
            return SwiftCompiler(exelist, version)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_static_linker(self, compiler):
        if compiler.is_cross:
            linker = self.cross_info.config['binaries']['ar']
        else:
            evar = 'AR'
            if evar in os.environ:
                linker = os.environ[evar].strip()
            elif isinstance(compiler, VisualStudioCCompiler):
                linker= self.vs_static_linker
            else:
                linker = self.default_static_linker
        basename = os.path.basename(linker).lower()
        if basename == 'lib' or basename == 'lib.exe':
            arg = '/?'
        else:
            arg = '--version'
        try:
            p = subprocess.Popen([linker, arg], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            raise EnvironmentException('Could not execute static linker "%s".' % linker)
        (out, err) = p.communicate()
        out = out.decode(errors='ignore')
        err = err.decode(errors='ignore')
        if '/OUT:' in out or '/OUT:' in err:
            return VisualStudioLinker([linker])
        if p.returncode == 0:
            return ArLinker([linker])
        if p.returncode == 1 and err.startswith('usage'): # OSX
            return ArLinker([linker])
        raise EnvironmentException('Unknown static linker "%s"' % linker)

    def detect_ccache(self):
        try:
            has_ccache = subprocess.call(['ccache', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            has_ccache = 1
        if has_ccache == 0:
            cmdlist = ['ccache']
        else:
            cmdlist = []
        return cmdlist

    def get_objc_compiler_exelist(self):
        ccachelist = self.detect_ccache()
        evar = 'OBJCC'
        if evar in os.environ:
            return os.environ[evar].split()
        return ccachelist + self.default_objc

    def get_objcpp_compiler_exelist(self):
        ccachelist = self.detect_ccache()
        evar = 'OBJCXX'
        if evar in os.environ:
            return os.environ[evar].split()
        return ccachelist + self.default_objcpp

    def get_source_dir(self):
        return self.source_dir

    def get_build_dir(self):
        return self.build_dir

    def get_exe_suffix(self):
        return self.exe_suffix

    # On Windows (MSVC) the library has suffix dll
    # but you link against a file that has suffix lib.
    def get_import_lib_suffix(self):
        return self.import_lib_suffix

    def get_shared_lib_prefix(self):
        return self.shared_lib_prefix

    def get_shared_lib_suffix(self):
        return self.shared_lib_suffix

    def get_static_lib_prefix(self):
        return self.static_lib_prefix

    def get_static_lib_suffix(self):
        return self.static_lib_suffix

    def get_object_suffix(self):
        return self.object_suffix

    def get_prefix(self):
        return self.coredata.get_builtin_option('prefix')

    def get_libdir(self):
        return self.coredata.get_builtin_option('libdir')

    def get_libexecdir(self):
        return self.coredata.get_builtin_option('libexecdir')

    def get_bindir(self):
        return self.coredata.get_builtin_option('bindir')

    def get_includedir(self):
        return self.coredata.get_builtin_option('includedir')

    def get_mandir(self):
        return self.coredata.get_builtin_option('mandir')

    def get_datadir(self):
        return self.coredata.get_builtin_option('datadir')

    def find_library(self, libname, dirs):
        if dirs is None:
            dirs = mesonlib.get_library_dirs()
        suffixes = [self.get_shared_lib_suffix(), self.get_static_lib_suffix()]
        prefix = self.get_shared_lib_prefix()
        for d in dirs:
            for suffix in suffixes:
                trial = os.path.join(d, prefix + libname + '.' + suffix)
                if os.path.isfile(trial):
                    return trial


def get_args_from_envvars(lang):
    if lang == 'c':
        compile_args = os.environ.get('CFLAGS', '').split()
        link_args = compile_args + os.environ.get('LDFLAGS', '').split()
        compile_args += os.environ.get('CPPFLAGS', '').split()
    elif lang == 'cpp':
        compile_args = os.environ.get('CXXFLAGS', '').split()
        link_args = compile_args + os.environ.get('LDFLAGS', '').split()
        compile_args += os.environ.get('CPPFLAGS', '').split()
    elif lang == 'objc':
        compile_args = os.environ.get('OBJCFLAGS', '').split()
        link_args = compile_args + os.environ.get('LDFLAGS', '').split()
        compile_args += os.environ.get('CPPFLAGS', '').split()
    elif lang == 'objcpp':
        compile_args = os.environ.get('OBJCXXFLAGS', '').split()
        link_args = compile_args + os.environ.get('LDFLAGS', '').split()
        compile_args += os.environ.get('CPPFLAGS', '').split()
    elif lang == 'fortran':
        compile_args = os.environ.get('FFLAGS', '').split()
        link_args = compile_args + os.environ.get('LDFLAGS', '').split()
    else:
        compile_args = []
        link_args = []
    return (compile_args, link_args)

class CrossBuildInfo():
    def __init__(self, filename):
        self.config = {}
        self.parse_datafile(filename)
        if 'target_machine' in self.config:
            return
        if not 'host_machine' in self.config:
            raise mesonlib.MesonException('Cross info file must have either host or a target machine.')
        if not 'properties' in self.config:
            raise mesonlib.MesonException('Cross file is missing "properties".')
        if not 'binaries' in self.config:
            raise mesonlib.MesonException('Cross file is missing "binaries".')

    def ok_type(self, i):
        return isinstance(i, str) or isinstance(i, int) or isinstance(i, bool)

    def parse_datafile(self, filename):
        config = configparser.ConfigParser()
        config.read(filename)
        # This is a bit hackish at the moment.
        for s in config.sections():
            self.config[s] = {}
            for entry in config[s]:
                value = config[s][entry]
                if ' ' in entry or '\t' in entry or "'" in entry or '"' in entry:
                    raise EnvironmentException('Malformed variable name %s in cross file..' % varname)
                try:
                    res = eval(value, {'true' : True, 'false' : False})
                except Exception:
                    raise EnvironmentException('Malformed value in cross file variable %s.' % varname)
                if self.ok_type(res):
                    self.config[s][entry] = res
                elif isinstance(res, list):
                    for i in res:
                        if not self.ok_type(i):
                            raise EnvironmentException('Malformed value in cross file variable %s.' % varname)
                    self.config[s][entry] = res
                else:
                    raise EnvironmentException('Malformed value in cross file variable %s.' % varname)

    def has_host(self):
        return 'host_machine' in self.config

    def has_target(self):
        return 'target_machine' in self.config

    # Wehn compiling a cross compiler we use the native compiler for everything.
    # But not when cross compiling a cross compiler.
    def need_cross_compiler(self):
        return 'host_machine' in self.config
