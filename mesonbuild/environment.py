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

import os
import platform
import re

from .compilers import *
from .mesonlib import EnvironmentException, Popen_safe
import configparser
import shlex
import shutil

build_filename = 'meson.build'

# Environment variables that each lang uses.
cflags_mapping = {'c': 'CFLAGS',
                  'cpp': 'CXXFLAGS',
                  'objc': 'OBJCFLAGS',
                  'objcpp': 'OBJCXXFLAGS',
                  'fortran': 'FFLAGS',
                  'd': 'DFLAGS',
                  'vala': 'VALAFLAGS'}


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
    return gcovr_exe, lcov_exe, genhtml_exe

def detect_ninja(version='1.5'):
    for n in ['ninja', 'ninja-build']:
        try:
            p, found = Popen_safe([n, '--version'])[0:2]
        except (FileNotFoundError, PermissionError):
            # Doesn't exist in PATH or isn't executable
            continue
        # Perhaps we should add a way for the caller to know the failure mode
        # (not found or too old)
        if p.returncode == 0 and mesonlib.version_compare(found, '>=' + version):
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
            raise EnvironmentException('Unable to detect native OS architecture')
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
        if compiler.id == 'gcc' and compiler.has_builtin_define('__i386__'):
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
        trial = 'x86_64'
    if trial == 'x86_64':
        # On Linux (and maybe others) there can be any mixture of 32/64 bit
        # code in the kernel, Python, system etc. The only reliable way
        # to know is to check the compiler defines.
        for c in compilers.values():
            try:
                if c.has_builtin_define('__i386__'):
                    return 'x86'
            except mesonlib.MesonException:
                # Ignore compilers that do not support has_builtin_define.
                pass
        return 'x86_64'
    # Add fixes here as bugs are reported.
    return trial

def detect_cpu(compilers):
    if mesonlib.is_windows():
        trial = detect_windows_arch(compilers)
    else:
        trial = platform.machine().lower()
    if trial in ('amd64', 'x64'):
        trial = 'x86_64'
    if trial == 'x86_64':
        # Same check as above for cpu_family
        for c in compilers.values():
            try:
                if c.has_builtin_define('__i386__'):
                    return 'i686' # All 64 bit cpus have at least this level of x86 support.
            except mesonlib.MesonException:
                pass
        return 'x86_64'
    # Add fixes here as bugs are reported.
    return trial

def detect_system():
    system = platform.system().lower()
    if system.startswith('cygwin'):
        return 'cygwin'
    return system


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


def for_cygwin(is_cross, env):
    """
    Host machine is cygwin?

    Note: 'host' is the machine on which compiled binaries will run
    """
    if not is_cross:
        return mesonlib.is_cygwin()
    elif env.cross_info.has_host():
        return env.cross_info.config['host_machine']['system'] == 'cygwin'
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


def search_version(text):
    # Usually of the type 4.1.4 but compiler output may contain
    # stuff like this:
    # (Sourcery CodeBench Lite 2014.05-29) 4.8.3 20140320 (prerelease)
    # Limiting major version number to two digits seems to work
    # thus far. When we get to GCC 100, this will break, but
    # if we are still relevant when that happens, it can be
    # considered an achievement in itself.
    #
    # This regex is reaching magic levels. If it ever needs
    # to be updated, do not complexify but convert to something
    # saner instead.
    version_regex = '(?<!(\d|\.))(\d{1,2}(\.\d+)+(-[a-zA-Z0-9]+)?)'
    match = re.search(version_regex, text)
    if match:
        return match.group(0)
    return 'unknown version'

class Environment:
    private_dir = 'meson-private'
    log_dir = 'meson-logs'
    coredata_file = os.path.join(private_dir, 'coredata.dat')

    def __init__(self, source_dir, build_dir, main_script_launcher, options, original_cmd_line_args):
        self.source_dir = source_dir
        self.build_dir = build_dir
        self.meson_script_launcher = main_script_launcher
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
            self.coredata.meson_script_launcher = self.meson_script_launcher
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
        self.default_fortran = ['gfortran', 'g95', 'f95', 'f90', 'f77', 'ifort']
        self.default_static_linker = ['ar']
        self.vs_static_linker = ['lib']
        self.gcc_static_linker = ['gcc-ar']
        self.clang_static_linker = ['llvm-ar']

        # Various prefixes and suffixes for import libraries, shared libraries,
        # static libraries, and executables.
        # Versioning is added to these names in the backends as-needed.
        cross = self.is_cross_build()
        if (not cross and mesonlib.is_windows()) \
                or (cross and self.cross_info.has_host() and self.cross_info.config['host_machine']['system'] == 'windows'):
            self.exe_suffix = 'exe'
            self.object_suffix = 'obj'
            self.win_libdir_layout = True
        elif (not cross and mesonlib.is_cygwin()) \
                or (cross and self.cross_info.has_host() and self.cross_info.config['host_machine']['system'] == 'cygwin'):
            self.exe_suffix = 'exe'
            self.object_suffix = 'o'
            self.win_libdir_layout = True
        else:
            self.exe_suffix = ''
            self.object_suffix = 'o'
            self.win_libdir_layout = False
        if 'STRIP' in os.environ:
            self.native_strip_bin = shlex.split('STRIP')
        else:
            self.native_strip_bin = ['strip']

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
        return self.meson_script_launcher

    def is_header(self, fname):
        return is_header(fname)

    def is_source(self, fname):
        return is_source(fname)

    def is_assembly(self, fname):
        return is_assembly(fname)

    def is_llvm_ir(self, fname):
        return is_llvm_ir(fname)

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
        p, output = Popen_safe(args, write='', stdin=subprocess.PIPE)[0:2]
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
    def get_gnu_version_from_defines(defines):
        dot = '.'
        major = defines.get('__GNUC__', '0')
        minor = defines.get('__GNUC_MINOR__', '0')
        patch = defines.get('__GNUC_PATCHLEVEL__', '0')
        return dot.join((major, minor, patch))

    @staticmethod
    def get_gnu_compiler_type(defines):
        # Detect GCC type (Apple, MinGW, Cygwin, Unix)
        if '__APPLE__' in defines:
            return GCC_OSX
        elif '__MINGW32__' in defines or '__MINGW64__' in defines:
            return GCC_MINGW
        elif '__CYGWIN__' in defines:
            return GCC_CYGWIN
        return GCC_STANDARD

    def _get_compilers(self, lang, evar, want_cross):
        '''
        The list of compilers is detected in the exact same way for
        C, C++, ObjC, ObjC++, Fortran so consolidate it here.
        '''
        if self.is_cross_build() and want_cross:
            compilers = mesonlib.stringlistify(self.cross_info.config['binaries'][lang])
            # Ensure ccache exists and remove it if it doesn't
            if compilers[0] == 'ccache':
                compilers = compilers[1:]
                ccache = self.detect_ccache()
            else:
                ccache = []
            # Return value has to be a list of compiler 'choices'
            compilers = [compilers]
            is_cross = True
            if self.cross_info.need_exe_wrapper():
                exe_wrap = self.cross_info.config['binaries'].get('exe_wrapper', None)
            else:
                exe_wrap = []
        elif evar in os.environ:
            compilers = shlex.split(os.environ[evar])
            # Ensure ccache exists and remove it if it doesn't
            if compilers[0] == 'ccache':
                compilers = compilers[1:]
                ccache = self.detect_ccache()
            else:
                ccache = []
            # Return value has to be a list of compiler 'choices'
            compilers = [compilers]
            is_cross = False
            exe_wrap = None
        else:
            compilers = getattr(self, 'default_' + lang)
            ccache = self.detect_ccache()
            is_cross = False
            exe_wrap = None
        return compilers, ccache, is_cross, exe_wrap

    def _handle_exceptions(self, exceptions, binaries, bintype='compiler'):
        errmsg = 'Unknown {}(s): {}'.format(bintype, binaries)
        if exceptions:
            errmsg += '\nThe follow exceptions were encountered:'
            for (c, e) in exceptions.items():
                errmsg += '\nRunning "{0}" gave "{1}"'.format(c, e)
        raise EnvironmentException(errmsg)

    def _detect_c_or_cpp_compiler(self, lang, evar, want_cross):
        popen_exceptions = {}
        compilers, ccache, is_cross, exe_wrap = self._get_compilers(lang, evar, want_cross)
        for compiler in compilers:
            if isinstance(compiler, str):
                compiler = [compiler]
            if 'cl' in compiler or 'cl.exe' in compiler:
                arg = '/?'
            else:
                arg = '--version'
            try:
                p, out, err = Popen_safe(compiler + [arg])
            except OSError as e:
                popen_exceptions[' '.join(compiler + [arg])] = e
                continue
            version = search_version(out)
            if 'Free Software Foundation' in out:
                defines = self.get_gnu_compiler_defines(compiler)
                if not defines:
                    popen_exceptions[compiler] = 'no pre-processor defines'
                    continue
                gtype = self.get_gnu_compiler_type(defines)
                version = self.get_gnu_version_from_defines(defines)
                cls = GnuCCompiler if lang == 'c' else GnuCPPCompiler
                return cls(ccache + compiler, version, gtype, is_cross, exe_wrap, defines)
            if 'clang' in out:
                if 'Apple' in out or for_darwin(want_cross, self):
                    cltype = CLANG_OSX
                elif 'windows' in out or for_windows(want_cross, self):
                    cltype = CLANG_WIN
                else:
                    cltype = CLANG_STANDARD
                cls = ClangCCompiler if lang == 'c' else ClangCPPCompiler
                return cls(ccache + compiler, version, cltype, is_cross, exe_wrap)
            if 'Microsoft' in out or 'Microsoft' in err:
                # Visual Studio prints version number to stderr but
                # everything else to stdout. Why? Lord only knows.
                version = search_version(err)
                cls = VisualStudioCCompiler if lang == 'c' else VisualStudioCPPCompiler
                return cls(compiler, version, is_cross, exe_wrap)
            if '(ICC)' in out:
                # TODO: add microsoft add check OSX
                inteltype = ICC_STANDARD
                cls = IntelCCompiler if lang == 'c' else IntelCPPCompiler
                return cls(ccache + compiler, version, inteltype, is_cross, exe_wrap)
        self._handle_exceptions(popen_exceptions, compilers)

    def detect_c_compiler(self, want_cross):
        return self._detect_c_or_cpp_compiler('c', 'CC', want_cross)

    def detect_cpp_compiler(self, want_cross):
        return self._detect_c_or_cpp_compiler('cpp', 'CXX', want_cross)

    def detect_fortran_compiler(self, want_cross):
        popen_exceptions = {}
        compilers, ccache, is_cross, exe_wrap = self._get_compilers('fortran', 'FC', want_cross)
        for compiler in compilers:
            if isinstance(compiler, str):
                compiler = [compiler]
            for arg in ['--version', '-V']:
                try:
                    p, out, err = Popen_safe(compiler + [arg])
                except OSError as e:
                    popen_exceptions[' '.join(compiler + [arg])] = e
                    continue

                version = search_version(out)

                if 'GNU Fortran' in out:
                    defines = self.get_gnu_compiler_defines(compiler)
                    if not defines:
                        popen_exceptions[compiler] = 'no pre-processor defines'
                        continue
                    gtype = self.get_gnu_compiler_type(defines)
                    version = self.get_gnu_version_from_defines(defines)
                    return GnuFortranCompiler(compiler, version, gtype, is_cross, exe_wrap, defines)

                if 'G95' in out:
                    return G95FortranCompiler(compiler, version, is_cross, exe_wrap)

                if 'Sun Fortran' in err:
                    version = search_version(err)
                    return SunFortranCompiler(compiler, version, is_cross, exe_wrap)

                if 'ifort (IFORT)' in out:
                    return IntelFortranCompiler(compiler, version, is_cross, exe_wrap)

                if 'PathScale EKOPath(tm)' in err:
                    return PathScaleFortranCompiler(compiler, version, is_cross, exe_wrap)

                if 'PGI Compilers' in out:
                    return PGIFortranCompiler(compiler, version, is_cross, exe_wrap)

                if 'Open64 Compiler Suite' in err:
                    return Open64FortranCompiler(compiler, version, is_cross, exe_wrap)

                if 'NAG Fortran' in err:
                    return NAGFortranCompiler(compiler, version, is_cross, exe_wrap)
        self._handle_exceptions(popen_exceptions, compilers)

    def get_scratch_dir(self):
        return self.scratch_dir

    def get_depfixer(self):
        path = os.path.split(__file__)[0]
        return os.path.join(path, 'depfixer.py')

    def detect_objc_compiler(self, want_cross):
        popen_exceptions = {}
        compilers, ccache, is_cross, exe_wrap = self._get_compilers('objc', 'OBJC', want_cross)
        for compiler in compilers:
            if isinstance(compiler, str):
                compiler = [compiler]
            arg = ['--version']
            try:
                p, out, err = Popen_safe(compiler + arg)
            except OSError as e:
                popen_exceptions[' '.join(compiler + arg)] = e
            version = search_version(out)
            if 'Free Software Foundation' in out:
                defines = self.get_gnu_compiler_defines(compiler)
                if not defines:
                    popen_exceptions[compiler] = 'no pre-processor defines'
                    continue
                gtype = self.get_gnu_compiler_type(defines)
                version = self.get_gnu_version_from_defines(defines)
                return GnuObjCCompiler(ccache + compiler, version, gtype, is_cross, exe_wrap, defines)
            if out.startswith('Apple LLVM'):
                return ClangObjCCompiler(ccache + compiler, version, CLANG_OSX, is_cross, exe_wrap)
            if out.startswith('clang'):
                return ClangObjCCompiler(ccache + compiler, version, CLANG_STANDARD, is_cross, exe_wrap)
        self._handle_exceptions(popen_exceptions, compilers)

    def detect_objcpp_compiler(self, want_cross):
        popen_exceptions = {}
        compilers, ccache, is_cross, exe_wrap = self._get_compilers('objcpp', 'OBJCXX', want_cross)
        for compiler in compilers:
            if isinstance(compiler, str):
                compiler = [compiler]
            arg = ['--version']
            try:
                p, out, err = Popen_safe(compiler + arg)
            except OSError as e:
                popen_exceptions[' '.join(compiler + arg)] = e
            version = search_version(out)
            if 'Free Software Foundation' in out:
                defines = self.get_gnu_compiler_defines(compiler)
                if not defines:
                    popen_exceptions[compiler] = 'no pre-processor defines'
                    continue
                gtype = self.get_gnu_compiler_type(defines)
                version = self.get_gnu_version_from_defines(defines)
                return GnuObjCPPCompiler(ccache + compiler, version, gtype, is_cross, exe_wrap, defines)
            if out.startswith('Apple LLVM'):
                return ClangObjCPPCompiler(ccache + compiler, version, CLANG_OSX, is_cross, exe_wrap)
            if out.startswith('clang'):
                return ClangObjCPPCompiler(ccache + compiler, version, CLANG_STANDARD, is_cross, exe_wrap)
        self._handle_exceptions(popen_exceptions, compilers)

    def detect_java_compiler(self):
        exelist = ['javac']
        try:
            p, out, err = Popen_safe(exelist + ['-version'])
        except OSError:
            raise EnvironmentException('Could not execute Java compiler "%s"' % ' '.join(exelist))
        version = search_version(err)
        if 'javac' in err:
            return JavaCompiler(exelist, version)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_cs_compiler(self):
        exelist = ['mcs']
        try:
            p, out, err = Popen_safe(exelist + ['--version'])
        except OSError:
            raise EnvironmentException('Could not execute C# compiler "%s"' % ' '.join(exelist))
        version = search_version(out)
        if 'Mono' in out:
            return MonoCompiler(exelist, version)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_vala_compiler(self):
        exelist = ['valac']
        try:
            p, out = Popen_safe(exelist + ['--version'])[0:2]
        except OSError:
            raise EnvironmentException('Could not execute Vala compiler "%s"' % ' '.join(exelist))
        version = search_version(out)
        if 'Vala' in out:
            return ValaCompiler(exelist, version)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_rust_compiler(self):
        exelist = ['rustc']
        try:
            p, out = Popen_safe(exelist + ['--version'])[0:2]
        except OSError:
            raise EnvironmentException('Could not execute Rust compiler "%s"' % ' '.join(exelist))
        version = search_version(out)
        if 'rustc' in out:
            return RustCompiler(exelist, version)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_d_compiler(self, want_cross):
        is_cross = False
        # Search for a D compiler.
        # We prefer LDC over GDC unless overridden with the DC
        # environment variable because LDC has a much more
        # up to date language version at time (2016).
        if 'DC' in os.environ:
            exelist = shlex.split(os.environ['DC'])
        elif self.is_cross_build() and want_cross:
            exelist = mesonlib.stringlistify(self.cross_info.config['binaries']['d'])
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
            p, out = Popen_safe(exelist + ['--version'])[0:2]
        except OSError:
            raise EnvironmentException('Could not execute D compiler "%s"' % ' '.join(exelist))
        version = search_version(out)
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
            p, _, err = Popen_safe(exelist + ['-v'])
        except OSError:
            raise EnvironmentException('Could not execute Swift compiler "%s"' % ' '.join(exelist))
        version = search_version(err)
        if 'Swift' in err:
            return SwiftCompiler(exelist, version)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_static_linker(self, compiler):
        if compiler.is_cross:
            linker = self.cross_info.config['binaries']['ar']
            if isinstance(linker, str):
                linker = [linker]
            linkers = [linker]
        else:
            evar = 'AR'
            if evar in os.environ:
                linkers = [shlex.split(os.environ[evar])]
            elif isinstance(compiler, VisualStudioCCompiler):
                linkers = [self.vs_static_linker]
            elif isinstance(compiler, GnuCompiler):
                # Use gcc-ar if available; needed for LTO
                linkers = [self.gcc_static_linker, self.default_static_linker]
            elif isinstance(compiler, ClangCompiler):
                # Use llvm-ar if available; needed for LTO
                linkers = [self.clang_static_linker, self.default_static_linker]
            else:
                linkers = [self.default_static_linker]
        popen_exceptions = {}
        for linker in linkers:
            if 'lib' in linker or 'lib.exe' in linker:
                arg = '/?'
            else:
                arg = '--version'
            try:
                p, out, err = Popen_safe(linker + [arg])
            except OSError as e:
                popen_exceptions[' '.join(linker + [arg])] = e
                continue
            if '/OUT:' in out or '/OUT:' in err:
                return VisualStudioLinker(linker)
            if p.returncode == 0:
                return ArLinker(linker)
            if p.returncode == 1 and err.startswith('usage'): # OSX
                return ArLinker(linker)
        self._handle_exceptions(popen_exceptions, linkers, 'linker')
        raise EnvironmentException('Unknown static linker "%s"' % ' '.join(linkers))

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

    def get_source_dir(self):
        return self.source_dir

    def get_build_dir(self):
        return self.build_dir

    def get_exe_suffix(self):
        return self.exe_suffix

    def get_import_lib_dir(self):
        "Install dir for the import library (library used for linking)"
        return self.get_libdir()

    def get_shared_module_dir(self):
        "Install dir for shared modules that are loaded at runtime"
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


def get_args_from_envvars(compiler):
    """
    @compiler: Compiler to fetch environment flags for

    Returns a tuple of (compile_flags, link_flags) for the specified language
    from the inherited environment
    """
    def log_var(var, val):
        if val:
            mlog.log('Appending {} from environment: {!r}'.format(var, val))

    lang = compiler.get_language()
    compiler_is_linker = False
    if hasattr(compiler, 'get_linker_exelist'):
        compiler_is_linker = (compiler.get_exelist() == compiler.get_linker_exelist())

    if lang not in cflags_mapping:
        return [], [], []

    compile_flags = os.environ.get(cflags_mapping[lang], '')
    log_var(cflags_mapping[lang], compile_flags)
    compile_flags = shlex.split(compile_flags)

    # Link flags (same for all languages)
    link_flags = os.environ.get('LDFLAGS', '')
    log_var('LDFLAGS', link_flags)
    link_flags = shlex.split(link_flags)
    if compiler_is_linker:
        # When the compiler is used as a wrapper around the linker (such as
        # with GCC and Clang), the compile flags can be needed while linking
        # too. This is also what Autotools does. However, we don't want to do
        # this when the linker is stand-alone such as with MSVC C/C++, etc.
        link_flags = compile_flags + link_flags

    # Pre-processor flags (not for fortran or D)
    preproc_flags = ''
    if lang in ('c', 'cpp', 'objc', 'objcpp'):
        preproc_flags = os.environ.get('CPPFLAGS', '')
    log_var('CPPFLAGS', preproc_flags)
    preproc_flags = shlex.split(preproc_flags)
    compile_flags += preproc_flags

    return preproc_flags, compile_flags, link_flags

class CrossBuildInfo:
    def __init__(self, filename):
        self.config = {'properties': {}}
        self.parse_datafile(filename)
        if 'target_machine' in self.config:
            return
        if 'host_machine' not in self.config:
            raise mesonlib.MesonException('Cross info file must have either host or a target machine.')
        if 'binaries' not in self.config:
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
                    raise EnvironmentException('Malformed variable name %s in cross file..' % entry)
                try:
                    res = eval(value, {'__builtins__': None}, {'true': True, 'false': False})
                except Exception:
                    raise EnvironmentException('Malformed value in cross file variable %s.' % entry)
                if self.ok_type(res):
                    self.config[s][entry] = res
                elif isinstance(res, list):
                    for i in res:
                        if not self.ok_type(i):
                            raise EnvironmentException('Malformed value in cross file variable %s.' % entry)
                    self.config[s][entry] = res
                else:
                    raise EnvironmentException('Malformed value in cross file variable %s.' % entry)

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
        value = self.config['properties'].get('needs_exe_wrapper', None)
        if value is not None:
            return value
        # Can almost always run 32-bit binaries on 64-bit natively if the host
        # and build systems are the same. We don't pass any compilers to
        # detect_cpu_family() here because we always want to know the OS
        # architecture, not what the compiler environment tells us.
        if self.has_host() and detect_cpu_family({}) == 'x86_64' and \
           self.config['host_machine']['cpu_family'] == 'x86' and \
           self.config['host_machine']['system'] == detect_system():
            return False
        return True


class MachineInfo:
    def __init__(self, system, cpu_family, cpu, endian):
        self.system = system
        self.cpu_family = cpu_family
        self.cpu = cpu
        self.endian = endian
