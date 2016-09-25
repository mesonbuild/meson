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

import os, re, subprocess, platform
from . import coredata
from . import mesonlib
from . import mlog
from .compilers import *
import configparser
import shutil

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
            p = subprocess.Popen([n, '--version'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            continue
        version = p.communicate()[0].decode(errors='ignore')
        # Perhaps we should add a way for the caller to know the failure mode
        # (not found or too old)
        if p.returncode == 0 and mesonlib.version_compare(version, ">=1.6"):
            return n

def detect_native_windows_arch():
    """
    The architecture of Windows itself: x86 or amd64
    """
    # These env variables are always available. See:
    # https://msdn.microsoft.com/en-us/library/aa384274(VS.85).aspx
    # https://blogs.msdn.microsoft.com/david.wang/2006/03/27/howto-detect-process-bitness/
    arch = os.environ.get('PROCESSOR_ARCHITEW6432', '').lower()
    if not arch:
        try:
            # If this doesn't exist, something is messing with the environment
            arch = os.environ['PROCESSOR_ARCHITECTURE'].lower()
        except KeyError:
            raise InterpreterException('Unable to detect native OS architecture')
    return arch

def detect_windows_arch(compilers):
    """
    Detecting the 'native' architecture of Windows is not a trivial task. We
    cannot trust that the architecture that Python is built for is the 'native'
    one because you can run 32-bit apps on 64-bit Windows using WOW64 and
    people sometimes install 32-bit Python on 64-bit Windows.

    We also can't rely on the architecture of the OS itself, since it's
    perfectly normal to compile and run 32-bit applications on Windows as if
    they were native applications. It's a terrible experience to require the
    user to supply a cross-info file to compile 32-bit applications on 64-bit
    Windows. Thankfully, the only way to compile things with Visual Studio on
    Windows is by entering the 'msvc toolchain' environment, which can be
    easily detected.

    In the end, the sanest method is as follows:
    1. Check if we're in an MSVC toolchain environment, and if so, return the
       MSVC toolchain architecture as our 'native' architecture.
    2. If not, check environment variables that are set by Windows and WOW64 to
       find out the architecture that Windows is built for, and use that as our
       'native' architecture.
    """
    os_arch = detect_native_windows_arch()
    if os_arch != 'amd64':
        return os_arch
    # If we're on 64-bit Windows, 32-bit apps can be compiled without
    # cross-compilation. So if we're doing that, just set the native arch as
    # 32-bit and pretend like we're running under WOW64. Else, return the
    # actual Windows architecture that we deduced above.
    for compiler in compilers.values():
        # Check if we're using and inside an MSVC toolchain environment
        if compiler.id == 'msvc' and 'VCINSTALLDIR' in os.environ:
            # 'Platform' is only set when the target arch is not 'x86'.
            # It's 'x64' when targetting x86_64 and 'arm' when targetting ARM.
            platform = os.environ.get('Platform', 'x86').lower()
            if platform == 'x86':
                return platform
        if compiler.id == 'gcc' and compiler.has_define('__i386__'):
            return 'x86'
    return os_arch

def detect_cpu_family(compilers):
    """
    Python is inconsistent in its platform module.
    It returns different values for the same cpu.
    For x86 it might return 'x86', 'i686' or somesuch.
    Do some canonicalization.
    """
    if mesonlib.is_windows():
        trial = detect_windows_arch(compilers)
    else:
        trial = platform.machine().lower()
    if trial.startswith('i') and trial.endswith('86'):
        return 'x86'
    if trial.startswith('arm'):
        return 'arm'
    if trial in ('amd64', 'x64'):
        return 'x86_64'
    # Add fixes here as bugs are reported.
    return trial

def detect_cpu(compilers):
    if mesonlib.is_windows():
        trial = detect_windows_arch(compilers)
    else:
        trial = platform.machine().lower()
    if trial in ('amd64', 'x64'):
        return 'x86_64'
    # Add fixes here as bugs are reported.
    return trial

def detect_system():
    return platform.system().lower()


def for_windows(is_cross, env):
    """
    Host machine is windows?

    Note: 'host' is the machine on which compiled binaries will run
    """
    if not is_cross:
        return mesonlib.is_windows()
    elif env.cross_info.has_host():
        return env.cross_info.config['host_machine']['system'] == 'windows'
    return False

def for_darwin(is_cross, env):
    """
    Host machine is Darwin (iOS/OS X)?

    Note: 'host' is the machine on which compiled binaries will run
    """
    if not is_cross:
        return mesonlib.is_osx()
    elif env.cross_info.has_host():
        return env.cross_info.config['host_machine']['system'] == 'darwin'
    return False


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
            # WARNING: Don't use any values from coredata in __init__. It gets
            # re-initialized with project options by the interpreter during
            # build file parsing.
            self.coredata = coredata.CoreData(options)
            self.coredata.meson_script_file = self.meson_script_file
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

        # Various prefixes and suffixes for import libraries, shared libraries,
        # static libraries, and executables.
        # Versioning is added to these names in the backends as-needed.
        cross = self.is_cross_build()
        if (not cross and mesonlib.is_windows()) \
        or (cross and self.cross_info.has_host() and self.cross_info.config['host_machine']['system'] == 'windows'):
            self.exe_suffix = 'exe'
            self.object_suffix = 'obj'
            self.win_libdir_layout = True
        else:
            self.exe_suffix = ''
            self.object_suffix = 'o'
            self.win_libdir_layout = False

    def is_cross_build(self):
        return self.cross_info is not None

    def dump_coredata(self, mtime):
        cdf = os.path.join(self.get_build_dir(), Environment.coredata_file)
        coredata.save(self.coredata, cdf)
        os.utime(cdf, times=(mtime, mtime))

    def get_script_dir(self):
        import mesonbuild.scripts
        return os.path.dirname(mesonbuild.scripts.__file__)

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

    @staticmethod
    def get_gnu_compiler_defines(compiler):
        """
        Detect GNU compiler platform type (Apple, MinGW, Unix)
        """
        # Arguments to output compiler pre-processor defines to stdout
        # gcc, g++, and gfortran all support these arguments
        args = compiler + ['-E', '-dM', '-']
        p = subprocess.Popen(args, universal_newlines=True,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        output = p.communicate('')[0]
        if p.returncode != 0:
            raise EnvironmentException('Unable to detect GNU compiler type:\n' + output)
        # Parse several lines of the type:
        # `#define ___SOME_DEF some_value`
        # and extract `___SOME_DEF`
        defines = {}
        for line in output.split('\n'):
            if not line:
                continue
            d, *rest = line.split(' ', 2)
            if d != '#define':
                continue
            if len(rest) == 1:
                defines[rest] = True
            if len(rest) == 2:
                defines[rest[0]] = rest[1]
        return defines

    @staticmethod
    def get_gnu_compiler_type(defines):
        # Detect GCC type (Apple, MinGW, Cygwin, Unix)
        if '__APPLE__' in defines:
            return GCC_OSX
        elif '__MINGW32__' in defines or '__MINGW64__' in defines:
            return GCC_MINGW
        # We ignore Cygwin for now, and treat it as a standard GCC
        return GCC_STANDARD

    def detect_c_compiler(self, want_cross):
        evar = 'CC'
        if self.is_cross_build() and want_cross:
            compilers = [self.cross_info.config['binaries']['c']]
            ccache = []
            is_cross = True
            if self.cross_info.need_exe_wrapper():
                exe_wrap = self.cross_info.config['binaries'].get('exe_wrapper', None)
            else:
                exe_wrap = []
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
            if 'Free Software Foundation' in out:
                defines = self.get_gnu_compiler_defines([compiler])
                if not defines:
                    popen_exceptions[compiler] = 'no pre-processor defines'
                    continue
                gtype = self.get_gnu_compiler_type(defines)
                return GnuCCompiler(ccache + [compiler], version, gtype, is_cross, exe_wrap, defines)
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
            if self.cross_info.need_exe_wrapper():
                exe_wrap = self.cross_info.get('exe_wrapper', None)
            else:
                exe_wrap = []
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
                    defines = self.get_gnu_compiler_defines([compiler])
                    if not defines:
                        popen_exceptions[compiler] = 'no pre-processor defines'
                        continue
                    gtype = self.get_gnu_compiler_type(defines)
                    return GnuFortranCompiler([compiler], version, gtype, is_cross, exe_wrap, defines)

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
            if self.cross_info.need_exe_wrapper():
                exe_wrap = self.cross_info.config['binaries'].get('exe_wrapper', None)
            else:
                exe_wrap = []
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
            if 'Free Software Foundation' in out:
                defines = self.get_gnu_compiler_defines([compiler])
                if not defines:
                    popen_exceptions[compiler] = 'no pre-processor defines'
                    continue
                gtype = self.get_gnu_compiler_type(defines)
                return GnuCPPCompiler(ccache + [compiler], version, gtype, is_cross, exe_wrap, defines)
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
            if self.cross_info.need_exe_wrapper():
                exe_wrap = self.cross_info.get('exe_wrapper', None)
            else:
                exe_wrap = []
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
        if 'Free Software Foundation' in out:
            defines = self.get_gnu_compiler_defines(exelist)
            return GnuObjCCompiler(exelist, version, is_cross, exe_wrap, defines)
        if out.startswith('Apple LLVM'):
            return ClangObjCCompiler(exelist, version, CLANG_OSX, is_cross, exe_wrap)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_objcpp_compiler(self, want_cross):
        if self.is_cross_build() and want_cross:
            exelist = [self.cross_info['objcpp']]
            is_cross = True
            if self.cross_info.need_exe_wrapper():
                exe_wrap = self.cross_info.get('exe_wrapper', None)
            else:
                exe_wrap = []
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
        if 'Free Software Foundation' in out:
            defines = self.get_gnu_compiler_defines(exelist)
            return GnuObjCPPCompiler(exelist, version, is_cross, exe_wrap, defines)
        if out.startswith('Apple LLVM'):
            return ClangObjCPPCompiler(exelist, version, CLANG_OSX, is_cross, exe_wrap)
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

    def detect_d_compiler(self):
        exelist = None
        is_cross = False
        # Search for a D compiler.
        # We prefer LDC over GDC unless overridden with the DC
        # environment variable because LDC has a much more
        # up to date language version at time (2016).
        if 'DC' in os.environ:
            exelist = os.environ['DC'].split()
        elif self.is_cross_build() and want_cross:
            exelist = [self.cross_info.config['binaries']['d']]
            is_cross = True
        elif shutil.which("ldc2"):
            exelist = ['ldc2']
        elif shutil.which("ldc"):
            exelist = ['ldc']
        elif shutil.which("gdc"):
            exelist = ['gdc']
        elif shutil.which("dmd"):
            exelist = ['dmd']
        else:
            raise EnvironmentException('Could not find any supported D compiler.')

        try:
            p = subprocess.Popen(exelist + ['--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            raise EnvironmentException('Could not execute D compiler "%s"' % ' '.join(exelist))
        (out, _) = p.communicate()
        out = out.decode(errors='ignore')
        vmatch = re.search(Environment.version_regex, out)
        if vmatch:
            version = vmatch.group(0)
        else:
            version = 'unknown version'
        if 'LLVM D compiler' in out:
            return LLVMDCompiler(exelist, version, is_cross)
        elif 'gdc' in out:
            return GnuDCompiler(exelist, version, is_cross)
        elif 'Digital Mars' in out:
            return DmdDCompiler(exelist, version, is_cross)
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

    def get_import_lib_dir(self):
        "Install dir for the import library (library used for linking)"
        return self.get_libdir()

    def get_shared_lib_dir(self):
        "Install dir for the shared library"
        if self.win_libdir_layout:
            return self.get_bindir()
        return self.get_libdir()

    def get_static_lib_dir(self):
        "Install dir for the static library"
        return self.get_libdir()

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


def get_args_from_envvars(lang, compiler_is_linker):
    """
    @lang: Language to fetch environment flags for

    Returns a tuple of (compile_flags, link_flags) for the specified language
    from the inherited environment
    """
    def log_var(var, val):
        if val:
            mlog.log('Appending {} from environment: {!r}'.format(var, val))

    if lang not in ('c', 'cpp', 'objc', 'objcpp', 'fortran', 'd'):
        return ([], [])

    # Compile flags
    cflags_mapping = {'c': 'CFLAGS', 'cpp': 'CXXFLAGS',
        'objc': 'OBJCFLAGS', 'objcpp': 'OBJCXXFLAGS',
        'fortran': 'FFLAGS',
        'd': 'DFLAGS'}
    compile_flags = os.environ.get(cflags_mapping[lang], '')
    log_var(cflags_mapping[lang], compile_flags)
    compile_flags = compile_flags.split()

    # Link flags (same for all languages)
    link_flags = os.environ.get('LDFLAGS', '')
    log_var('LDFLAGS', link_flags)
    link_flags = link_flags.split()
    if compiler_is_linker:
        # When the compiler is used as a wrapper around the linker (such as
        # with GCC and Clang), the compile flags can be needed while linking
        # too. This is also what Autotools does. However, we don't want to do
        # this when the linker is stand-alone such as with MSVC C/C++, etc.
        link_flags = compile_flags + link_flags

    # Pre-processof rlags (not for fortran)
    preproc_flags = ''
    if lang in ('c', 'cpp', 'objc', 'objcpp'):
        preproc_flags = os.environ.get('CPPFLAGS', '')
    log_var('CPPFLAGS', preproc_flags)
    compile_flags += preproc_flags.split()

    return (compile_flags, link_flags)

class CrossBuildInfo():
    def __init__(self, filename):
        self.config = {'properties': {}}
        self.parse_datafile(filename)
        if 'target_machine' in self.config:
            return
        if not 'host_machine' in self.config:
            raise mesonlib.MesonException('Cross info file must have either host or a target machine.')
        if not 'binaries' in self.config:
            raise mesonlib.MesonException('Cross file is missing "binaries".')

    def ok_type(self, i):
        return isinstance(i, (str, int, bool))

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

    def has_stdlib(self, language):
        return language + '_stdlib' in self.config['properties']

    def get_stdlib(self, language):
        return self.config['properties'][language + '_stdlib']

    def get_properties(self):
        return self.config['properties']

    # Wehn compiling a cross compiler we use the native compiler for everything.
    # But not when cross compiling a cross compiler.
    def need_cross_compiler(self):
        return 'host_machine' in self.config

    def need_exe_wrapper(self):
        # Can almost always run 32-bit binaries on 64-bit natively if the host
        # and build systems are the same. We don't pass any compilers to
        # detect_cpu_family() here because we always want to know the OS
        # architecture, not what the compiler environment tells us.
        if self.has_host() and detect_cpu_family({}) == 'x86_64' and \
           self.config['host_machine']['cpu_family'] == 'x86' and \
           self.config['host_machine']['system'] == detect_system():
            return False
        return True
