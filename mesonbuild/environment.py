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

import configparser, os, platform, re, sys, shlex, shutil, subprocess

from . import coredata
from .linkers import ArLinker, ArmarLinker, VisualStudioLinker, DLinker, CcrxLinker
from . import mesonlib
from .mesonlib import MesonException, EnvironmentException, PerMachine, Popen_safe
from . import mlog

from . import compilers
from .compilers import (
    CompilerType,
    is_assembly,
    is_header,
    is_library,
    is_llvm_ir,
    is_object,
    is_source,
)
from .compilers import (
    ArmCCompiler,
    ArmCPPCompiler,
    ArmclangCCompiler,
    ArmclangCPPCompiler,
    ClangCCompiler,
    ClangCPPCompiler,
    ClangObjCCompiler,
    ClangObjCPPCompiler,
    ClangClCCompiler,
    ClangClCPPCompiler,
    G95FortranCompiler,
    GnuCCompiler,
    GnuCPPCompiler,
    GnuFortranCompiler,
    GnuObjCCompiler,
    GnuObjCPPCompiler,
    ElbrusCCompiler,
    ElbrusCPPCompiler,
    ElbrusFortranCompiler,
    IntelCCompiler,
    IntelCPPCompiler,
    IntelFortranCompiler,
    JavaCompiler,
    MonoCompiler,
    VisualStudioCsCompiler,
    NAGFortranCompiler,
    Open64FortranCompiler,
    PathScaleFortranCompiler,
    PGIFortranCompiler,
    RustCompiler,
    CcrxCCompiler,
    CcrxCPPCompiler,
    SunFortranCompiler,
    ValaCompiler,
    VisualStudioCCompiler,
    VisualStudioCPPCompiler,
)

build_filename = 'meson.build'

known_cpu_families = (
    'aarch64',
    'arc',
    'arm',
    'e2k',
    'ia64',
    'mips',
    'mips64',
    'parisc',
    'ppc',
    'ppc64',
    'riscv32',
    'riscv64',
    'rx',
    's390x',
    'sparc',
    'sparc64',
    'x86',
    'x86_64'
)

def detect_gcovr(version='3.1', log=False):
    gcovr_exe = 'gcovr'
    try:
        p, found = Popen_safe([gcovr_exe, '--version'])[0:2]
    except (FileNotFoundError, PermissionError):
        # Doesn't exist in PATH or isn't executable
        return None, None
    found = search_version(found)
    if p.returncode == 0:
        if log:
            mlog.log('Found gcovr-{} at {}'.format(found, shlex.quote(shutil.which(gcovr_exe))))
        return gcovr_exe, mesonlib.version_compare(found, '>=' + version)
    return None, None

def find_coverage_tools():
    gcovr_exe, gcovr_new_rootdir = detect_gcovr()

    lcov_exe = 'lcov'
    genhtml_exe = 'genhtml'

    if not mesonlib.exe_exists([lcov_exe, '--version']):
        lcov_exe = None
    if not mesonlib.exe_exists([genhtml_exe, '--version']):
        genhtml_exe = None

    return gcovr_exe, gcovr_new_rootdir, lcov_exe, genhtml_exe

def detect_ninja(version='1.5', log=False):
    for n in ['ninja', 'ninja-build', 'samu']:
        try:
            p, found = Popen_safe([n, '--version'])[0:2]
        except (FileNotFoundError, PermissionError):
            # Doesn't exist in PATH or isn't executable
            continue
        found = found.strip()
        # Perhaps we should add a way for the caller to know the failure mode
        # (not found or too old)
        if p.returncode == 0 and mesonlib.version_compare(found, '>=' + version):
            if log:
                mlog.log('Found ninja-{} at {}'.format(found, shlex.quote(shutil.which(n))))
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
            if float(compiler.get_toolset_version()) < 10.0:
                # On MSVC 2008 and earlier, check 'BUILD_PLAT', where
                # 'Win32' means 'x86'
                platform = os.environ.get('BUILD_PLAT', os_arch)
                if platform == 'Win32':
                    return 'x86'
            elif 'VSCMD_ARG_TGT_ARCH' in os.environ:
                # On MSVC 2017 'Platform' is not set in VsDevCmd.bat
                return os.environ['VSCMD_ARG_TGT_ARCH']
            else:
                # Starting with VS 2017, `Platform` is not always set (f.ex.,
                # if you use VsDevCmd.bat directly instead of vcvars*.bat), but
                # `VSCMD_ARG_HOST_ARCH` is always set, so try that first.
                if 'VSCMD_ARG_HOST_ARCH' in os.environ:
                    platform = os.environ['VSCMD_ARG_HOST_ARCH'].lower()
                # On VS 2010-2015, 'Platform' is only set when the
                # target arch is not 'x86'.  It's 'x64' when targeting
                # x86_64 and 'arm' when targeting ARM.
                else:
                    platform = os.environ.get('Platform', 'x86').lower()
            if platform == 'x86':
                return platform
        if compiler.id == 'clang-cl' and not compiler.is_64:
            return 'x86'
        if compiler.id == 'gcc' and compiler.has_builtin_define('__i386__'):
            return 'x86'
    return os_arch

def any_compiler_has_define(compilers, define):
    for c in compilers.values():
        try:
            if c.has_builtin_define(define):
                return True
        except mesonlib.MesonException:
            # Ignore compilers that do not support has_builtin_define.
            pass
    return False

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
        trial = 'x86'
    elif trial.startswith('arm'):
        trial = 'arm'
    elif trial.startswith('ppc64'):
        trial = 'ppc64'
    elif trial == 'powerpc':
        trial = 'ppc'
        # FreeBSD calls both ppc and ppc64 "powerpc".
        # https://github.com/mesonbuild/meson/issues/4397
        try:
            p, stdo, _ = Popen_safe(['uname', '-p'])
        except (FileNotFoundError, PermissionError):
            # Not much to go on here.
            if sys.maxsize > 2**32:
                trial = 'ppc64'
        if 'powerpc64' in stdo:
            trial = 'ppc64'
    elif trial in ('amd64', 'x64'):
        trial = 'x86_64'

    # On Linux (and maybe others) there can be any mixture of 32/64 bit code in
    # the kernel, Python, system, 32-bit chroot on 64-bit host, etc. The only
    # reliable way to know is to check the compiler defines.
    if trial == 'x86_64':
        if any_compiler_has_define(compilers, '__i386__'):
            trial = 'x86'
    elif trial == 'aarch64':
        if any_compiler_has_define(compilers, '__arm__'):
            trial = 'arm'
    # Add more quirks here as bugs are reported. Keep in sync with detect_cpu()
    # below.

    if trial not in known_cpu_families:
        mlog.warning('Unknown CPU family {!r}, please report this at '
                     'https://github.com/mesonbuild/meson/issues/new with the'
                     'output of `uname -a` and `cat /proc/cpuinfo`'.format(trial))

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
        if any_compiler_has_define(compilers, '__i386__'):
            trial = 'i686' # All 64 bit cpus have at least this level of x86 support.
    elif trial == 'aarch64':
        # Same check as above for cpu_family
        if any_compiler_has_define(compilers, '__arm__'):
            trial = 'arm'
    elif trial == 'e2k':
        # Make more precise CPU detection for Elbrus platform.
        trial = platform.processor().lower()
    # Add more quirks here as bugs are reported. Keep in sync with
    # detect_cpu_family() above.
    return trial

def detect_system():
    system = platform.system().lower()
    if system.startswith('cygwin'):
        return 'cygwin'
    return system

def detect_msys2_arch():
    if 'MSYSTEM_CARCH' in os.environ:
        return os.environ['MSYSTEM_CARCH']
    return None

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

    def __init__(self, source_dir, build_dir, options):
        self.source_dir = source_dir
        self.build_dir = build_dir
        self.scratch_dir = os.path.join(build_dir, Environment.private_dir)
        self.log_dir = os.path.join(build_dir, Environment.log_dir)
        os.makedirs(self.scratch_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)
        try:
            self.coredata = coredata.load(self.get_build_dir())
            self.first_invocation = False
        except FileNotFoundError:
            self.create_new_coredata(options)
        except MesonException as e:
            # If we stored previous command line options, we can recover from
            # a broken/outdated coredata.
            if os.path.isfile(coredata.get_cmd_line_file(self.build_dir)):
                mlog.warning('Regenerating configuration from scratch.')
                mlog.log('Reason:', mlog.red(str(e)))
                coredata.read_cmd_line_file(self.build_dir, options)
                self.create_new_coredata(options)
            else:
                raise e
        self.exe_wrapper = None

        self.machines = MachineInfos()
        # Will be fully initialized later using compilers later.
        self.machines.detect_build()
        if self.coredata.cross_file:
            self.cross_info = CrossBuildInfo(self.coredata.cross_file)
            if 'exe_wrapper' in self.cross_info.config['binaries']:
                from .dependencies import ExternalProgram
                self.exe_wrapper = ExternalProgram.from_bin_list(
                    self.cross_info.config['binaries'], 'exe_wrapper')
            if 'host_machine' in self.cross_info.config:
                self.machines.host = MachineInfo.from_literal(
                    self.cross_info.config['host_machine'])
            if 'target_machine' in self.cross_info.config:
                self.machines.target = MachineInfo.from_literal(
                    self.cross_info.config['target_machine'])
        else:
            self.cross_info = None
        self.machines.default_missing()

        if self.coredata.config_files:
            self.config_info = coredata.ConfigData(
                coredata.load_configs(self.coredata.config_files))
        else:
            self.config_info = coredata.ConfigData()

        self.cmd_line_options = options.cmd_line_options.copy()

        # List of potential compilers.
        if mesonlib.is_windows():
            self.default_c = ['cl', 'cc', 'gcc', 'clang', 'clang-cl']
            self.default_cpp = ['cl', 'c++', 'g++', 'clang++', 'clang-cl']
        else:
            self.default_c = ['cc', 'gcc', 'clang']
            self.default_cpp = ['c++', 'g++', 'clang++']
        if mesonlib.is_windows():
            self.default_cs = ['csc', 'mcs']
        else:
            self.default_cs = ['mcs', 'csc']
        self.default_objc = ['cc']
        self.default_objcpp = ['c++']
        self.default_d = ['ldc2', 'ldc', 'gdc', 'dmd']
        self.default_fortran = ['gfortran', 'g95', 'f95', 'f90', 'f77', 'ifort']
        self.default_java = ['javac']
        self.default_rust = ['rustc']
        self.default_swift = ['swiftc']
        self.default_vala = ['valac']
        self.default_static_linker = ['ar']
        self.vs_static_linker = ['lib']
        self.clang_cl_static_linker = ['llvm-lib']
        self.gcc_static_linker = ['gcc-ar']
        self.clang_static_linker = ['llvm-ar']

        # Various prefixes and suffixes for import libraries, shared libraries,
        # static libraries, and executables.
        # Versioning is added to these names in the backends as-needed.
        cross = self.is_cross_build()
        if mesonlib.for_windows(cross, self):
            self.exe_suffix = 'exe'
            self.object_suffix = 'obj'
            self.win_libdir_layout = True
        elif mesonlib.for_cygwin(cross, self):
            self.exe_suffix = 'exe'
            self.object_suffix = 'o'
            self.win_libdir_layout = True
        else:
            self.exe_suffix = ''
            self.object_suffix = 'o'
            self.win_libdir_layout = False
        if 'STRIP' in os.environ:
            self.native_strip_bin = shlex.split(
                os.environ[BinaryTable.evarMap['strip']])
        else:
            self.native_strip_bin = ['strip']

    def create_new_coredata(self, options):
        # WARNING: Don't use any values from coredata in __init__. It gets
        # re-initialized with project options by the interpreter during
        # build file parsing.
        self.coredata = coredata.CoreData(options)
        # Used by the regenchecker script, which runs meson
        self.coredata.meson_command = mesonlib.meson_command
        self.first_invocation = True

    def is_cross_build(self):
        return self.cross_info is not None

    def dump_coredata(self):
        return coredata.save(self.coredata, self.get_build_dir())

    def get_script_dir(self):
        import mesonbuild.scripts
        return os.path.dirname(mesonbuild.scripts.__file__)

    def get_log_dir(self):
        return self.log_dir

    def get_coredata(self):
        return self.coredata

    def get_build_command(self, unbuffered=False):
        cmd = mesonlib.meson_command[:]
        if unbuffered and 'python' in os.path.basename(cmd[0]):
            cmd.insert(1, '-u')
        return cmd

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

    @staticmethod
    def get_gnu_compiler_defines(compiler):
        """
        Detect GNU compiler platform type (Apple, MinGW, Unix)
        """
        # Arguments to output compiler pre-processor defines to stdout
        # gcc, g++, and gfortran all support these arguments
        args = compiler + ['-E', '-dM', '-']
        p, output, error = Popen_safe(args, write='', stdin=subprocess.PIPE)
        if p.returncode != 0:
            raise EnvironmentException('Unable to detect GNU compiler type:\n' + output + error)
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
    def get_lcc_version_from_defines(defines):
        dot = '.'
        generation_and_major = defines.get('__LCC__', '100')
        generation = generation_and_major[:1]
        major = generation_and_major[1:]
        minor = defines.get('__LCC_MINOR__', '0')
        return dot.join((generation, major, minor))

    @staticmethod
    def get_gnu_compiler_type(defines):
        # Detect GCC type (Apple, MinGW, Cygwin, Unix)
        if '__APPLE__' in defines:
            return CompilerType.GCC_OSX
        elif '__MINGW32__' in defines or '__MINGW64__' in defines:
            return CompilerType.GCC_MINGW
        elif '__CYGWIN__' in defines:
            return CompilerType.GCC_CYGWIN
        return CompilerType.GCC_STANDARD

    def _get_compilers(self, lang, want_cross):
        '''
        The list of compilers is detected in the exact same way for
        C, C++, ObjC, ObjC++, Fortran, CS so consolidate it here.
        '''
        is_cross = False
        exe_wrap = None
        evar = BinaryTable.evarMap[lang]

        if self.is_cross_build() and want_cross:
            if lang not in self.cross_info.config['binaries']:
                raise EnvironmentException('{!r} compiler binary not defined in cross file'.format(lang))
            compilers, ccache = BinaryTable.parse_entry(
                mesonlib.stringlistify(self.cross_info.config['binaries'][lang]))
            BinaryTable.warn_about_lang_pointing_to_cross(compilers[0], evar)
            # Return value has to be a list of compiler 'choices'
            compilers = [compilers]
            is_cross = True
            exe_wrap = self.get_exe_wrapper()
        elif evar in os.environ:
            compilers, ccache = BinaryTable.parse_entry(
                shlex.split(os.environ[evar]))
            # Return value has to be a list of compiler 'choices'
            compilers = [compilers]
        elif lang in self.config_info.binaries:
            compilers, ccache = BinaryTable.parse_entry(
                mesonlib.stringlistify(self.config_info.binaries[lang]))
            compilers = [compilers]
        else:
            compilers = getattr(self, 'default_' + lang)
            ccache = BinaryTable.detect_ccache()
        return compilers, ccache, is_cross, exe_wrap

    def _handle_exceptions(self, exceptions, binaries, bintype='compiler'):
        errmsg = 'Unknown {}(s): {}'.format(bintype, binaries)
        if exceptions:
            errmsg += '\nThe follow exceptions were encountered:'
            for (c, e) in exceptions.items():
                errmsg += '\nRunning "{0}" gave "{1}"'.format(c, e)
        raise EnvironmentException(errmsg)

    def _detect_c_or_cpp_compiler(self, lang, want_cross):
        popen_exceptions = {}
        compilers, ccache, is_cross, exe_wrap = self._get_compilers(lang, want_cross)
        for compiler in compilers:
            if isinstance(compiler, str):
                compiler = [compiler]
            if not set(['cl', 'cl.exe', 'clang-cl', 'clang-cl.exe']).isdisjoint(compiler):
                # Watcom C provides it's own cl.exe clone that mimics an older
                # version of Microsoft's compiler. Since Watcom's cl.exe is
                # just a wrapper, we skip using it if we detect its presence
                # so as not to confuse Meson when configuring for MSVC.
                #
                # Additionally the help text of Watcom's cl.exe is paged, and
                # the binary will not exit without human intervention. In
                # practice, Meson will block waiting for Watcom's cl.exe to
                # exit, which requires user input and thus will never exit.
                if 'WATCOM' in os.environ:
                    def sanitize(p):
                        return os.path.normcase(os.path.abspath(p))

                    watcom_cls = [sanitize(os.path.join(os.environ['WATCOM'], 'BINNT', 'cl')),
                                  sanitize(os.path.join(os.environ['WATCOM'], 'BINNT', 'cl.exe'))]
                    found_cl = sanitize(shutil.which('cl'))
                    if found_cl in watcom_cls:
                        continue
                arg = '/?'
            elif 'armcc' in compiler[0]:
                arg = '--vsn'
            elif 'ccrx' in compiler[0]:
                arg = '-v'
            else:
                arg = '--version'
            try:
                p, out, err = Popen_safe(compiler + [arg])
            except OSError as e:
                popen_exceptions[' '.join(compiler + [arg])] = e
                continue

            if 'ccrx' in compiler[0]:
                out = err

            full_version = out.split('\n', 1)[0]
            version = search_version(out)

            guess_gcc_or_lcc = False
            if 'Free Software Foundation' in out:
                guess_gcc_or_lcc = 'gcc'
            if 'e2k' in out and 'lcc' in out:
                guess_gcc_or_lcc = 'lcc'

            if guess_gcc_or_lcc:
                defines = self.get_gnu_compiler_defines(compiler)
                if not defines:
                    popen_exceptions[' '.join(compiler)] = 'no pre-processor defines'
                    continue
                compiler_type = self.get_gnu_compiler_type(defines)
                if guess_gcc_or_lcc == 'lcc':
                    version = self.get_lcc_version_from_defines(defines)
                    cls = ElbrusCCompiler if lang == 'c' else ElbrusCPPCompiler
                else:
                    version = self.get_gnu_version_from_defines(defines)
                    cls = GnuCCompiler if lang == 'c' else GnuCPPCompiler
                return cls(ccache + compiler, version, compiler_type, is_cross, exe_wrap, defines, full_version=full_version)

            if 'armclang' in out:
                # The compiler version is not present in the first line of output,
                # instead it is present in second line, startswith 'Component:'.
                # So, searching for the 'Component' in out although we know it is
                # present in second line, as we are not sure about the
                # output format in future versions
                arm_ver_str = re.search('.*Component.*', out)
                if arm_ver_str is None:
                    popen_exceptions[' '.join(compiler)] = 'version string not found'
                    continue
                arm_ver_str = arm_ver_str.group(0)
                # Override previous values
                version = search_version(arm_ver_str)
                full_version = arm_ver_str
                compiler_type = CompilerType.ARM_WIN
                cls = ArmclangCCompiler if lang == 'c' else ArmclangCPPCompiler
                return cls(ccache + compiler, version, compiler_type, is_cross, exe_wrap, full_version=full_version)
            if 'CL.EXE COMPATIBILITY' in out:
                # if this is clang-cl masquerading as cl, detect it as cl, not
                # clang
                arg = '--version'
                try:
                    p, out, err = Popen_safe(compiler + [arg])
                except OSError as e:
                    popen_exceptions[' '.join(compiler + [arg])] = e
                version = search_version(out)
                is_64 = 'Target: x86_64' in out
                cls = ClangClCCompiler if lang == 'c' else ClangClCPPCompiler
                return cls(compiler, version, is_cross, exe_wrap, is_64)
            if 'clang' in out:
                if 'Apple' in out or mesonlib.for_darwin(want_cross, self):
                    compiler_type = CompilerType.CLANG_OSX
                elif 'windows' in out or mesonlib.for_windows(want_cross, self):
                    compiler_type = CompilerType.CLANG_MINGW
                else:
                    compiler_type = CompilerType.CLANG_STANDARD
                cls = ClangCCompiler if lang == 'c' else ClangCPPCompiler
                return cls(ccache + compiler, version, compiler_type, is_cross, exe_wrap, full_version=full_version)
            if 'Microsoft' in out or 'Microsoft' in err:
                # Latest versions of Visual Studio print version
                # number to stderr but earlier ones print version
                # on stdout.  Why? Lord only knows.
                # Check both outputs to figure out version.
                version = search_version(err)
                if version == 'unknown version':
                    version = search_version(out)
                if version == 'unknown version':
                    m = 'Failed to detect MSVC compiler arch: stderr was\n{!r}'
                    raise EnvironmentException(m.format(err))
                is_64 = err.split('\n')[0].endswith(' x64')
                cls = VisualStudioCCompiler if lang == 'c' else VisualStudioCPPCompiler
                return cls(compiler, version, is_cross, exe_wrap, is_64)
            if '(ICC)' in out:
                if mesonlib.for_darwin(want_cross, self):
                    compiler_type = CompilerType.ICC_OSX
                elif mesonlib.for_windows(want_cross, self):
                    # TODO: fix ICC on Windows
                    compiler_type = CompilerType.ICC_WIN
                else:
                    compiler_type = CompilerType.ICC_STANDARD
                cls = IntelCCompiler if lang == 'c' else IntelCPPCompiler
                return cls(ccache + compiler, version, compiler_type, is_cross, exe_wrap, full_version=full_version)
            if 'ARM' in out:
                compiler_type = CompilerType.ARM_WIN
                cls = ArmCCompiler if lang == 'c' else ArmCPPCompiler
                return cls(ccache + compiler, version, compiler_type, is_cross, exe_wrap, full_version=full_version)
            if 'RX Family' in out:
                compiler_type = CompilerType.CCRX_WIN
                cls = CcrxCCompiler if lang == 'c' else CcrxCPPCompiler
                return cls(ccache + compiler, version, compiler_type, is_cross, exe_wrap, full_version=full_version)

        self._handle_exceptions(popen_exceptions, compilers)

    def detect_c_compiler(self, want_cross):
        return self._detect_c_or_cpp_compiler('c', want_cross)

    def detect_cpp_compiler(self, want_cross):
        return self._detect_c_or_cpp_compiler('cpp', want_cross)

    def detect_fortran_compiler(self, want_cross):
        popen_exceptions = {}
        compilers, ccache, is_cross, exe_wrap = self._get_compilers('fortran', want_cross)
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
                full_version = out.split('\n', 1)[0]

                guess_gcc_or_lcc = False
                if 'GNU Fortran' in out:
                    guess_gcc_or_lcc = 'gcc'
                if 'e2k' in out and 'lcc' in out:
                    guess_gcc_or_lcc = 'lcc'

                if guess_gcc_or_lcc:
                    defines = self.get_gnu_compiler_defines(compiler)
                    if not defines:
                        popen_exceptions[' '.join(compiler)] = 'no pre-processor defines'
                        continue
                    compiler_type = self.get_gnu_compiler_type(defines)
                    if guess_gcc_or_lcc == 'lcc':
                        version = self.get_lcc_version_from_defines(defines)
                        cls = ElbrusFortranCompiler
                    else:
                        version = self.get_gnu_version_from_defines(defines)
                        cls = GnuFortranCompiler
                    return cls(compiler, version, compiler_type, is_cross, exe_wrap, defines, full_version=full_version)

                if 'G95' in out:
                    return G95FortranCompiler(compiler, version, is_cross, exe_wrap, full_version=full_version)

                if 'Sun Fortran' in err:
                    version = search_version(err)
                    return SunFortranCompiler(compiler, version, is_cross, exe_wrap, full_version=full_version)

                if 'ifort (IFORT)' in out:
                    return IntelFortranCompiler(compiler, version, is_cross, exe_wrap, full_version=full_version)

                if 'PathScale EKOPath(tm)' in err:
                    return PathScaleFortranCompiler(compiler, version, is_cross, exe_wrap, full_version=full_version)

                if 'PGI Compilers' in out:
                    return PGIFortranCompiler(compiler, version, is_cross, exe_wrap, full_version=full_version)

                if 'Open64 Compiler Suite' in err:
                    return Open64FortranCompiler(compiler, version, is_cross, exe_wrap, full_version=full_version)

                if 'NAG Fortran' in err:
                    return NAGFortranCompiler(compiler, version, is_cross, exe_wrap, full_version=full_version)
        self._handle_exceptions(popen_exceptions, compilers)

    def get_scratch_dir(self):
        return self.scratch_dir

    def detect_objc_compiler(self, want_cross):
        popen_exceptions = {}
        compilers, ccache, is_cross, exe_wrap = self._get_compilers('objc', want_cross)
        for compiler in compilers:
            if isinstance(compiler, str):
                compiler = [compiler]
            arg = ['--version']
            try:
                p, out, err = Popen_safe(compiler + arg)
            except OSError as e:
                popen_exceptions[' '.join(compiler + arg)] = e
                continue
            version = search_version(out)
            if 'Free Software Foundation' in out or ('e2k' in out and 'lcc' in out):
                defines = self.get_gnu_compiler_defines(compiler)
                if not defines:
                    popen_exceptions[' '.join(compiler)] = 'no pre-processor defines'
                    continue
                compiler_type = self.get_gnu_compiler_type(defines)
                version = self.get_gnu_version_from_defines(defines)
                return GnuObjCCompiler(ccache + compiler, version, compiler_type, is_cross, exe_wrap, defines)
            if out.startswith('Apple LLVM'):
                return ClangObjCCompiler(ccache + compiler, version, CompilerType.CLANG_OSX, is_cross, exe_wrap)
            if out.startswith('clang'):
                return ClangObjCCompiler(ccache + compiler, version, CompilerType.CLANG_STANDARD, is_cross, exe_wrap)
        self._handle_exceptions(popen_exceptions, compilers)

    def detect_objcpp_compiler(self, want_cross):
        popen_exceptions = {}
        compilers, ccache, is_cross, exe_wrap = self._get_compilers('objcpp', want_cross)
        for compiler in compilers:
            if isinstance(compiler, str):
                compiler = [compiler]
            arg = ['--version']
            try:
                p, out, err = Popen_safe(compiler + arg)
            except OSError as e:
                popen_exceptions[' '.join(compiler + arg)] = e
                continue
            version = search_version(out)
            if 'Free Software Foundation' in out or ('e2k' in out and 'lcc' in out):
                defines = self.get_gnu_compiler_defines(compiler)
                if not defines:
                    popen_exceptions[' '.join(compiler)] = 'no pre-processor defines'
                    continue
                compiler_type = self.get_gnu_compiler_type(defines)
                version = self.get_gnu_version_from_defines(defines)
                return GnuObjCPPCompiler(ccache + compiler, version, compiler_type, is_cross, exe_wrap, defines)
            if out.startswith('Apple LLVM'):
                return ClangObjCPPCompiler(ccache + compiler, version, CompilerType.CLANG_OSX, is_cross, exe_wrap)
            if out.startswith('clang'):
                return ClangObjCPPCompiler(ccache + compiler, version, CompilerType.CLANG_STANDARD, is_cross, exe_wrap)
        self._handle_exceptions(popen_exceptions, compilers)

    def detect_java_compiler(self):
        if 'java' in self.config_info.binaries:
            exelist = mesonlib.stringlistify(self.config_info.binaries['java'])
        else:
            # TODO support fallback
            exelist = [self.default_java[0]]

        try:
            p, out, err = Popen_safe(exelist + ['-version'])
        except OSError:
            raise EnvironmentException('Could not execute Java compiler "%s"' % ' '.join(exelist))
        if 'javac' in out or 'javac' in err:
            version = search_version(err if 'javac' in err else out)
            return JavaCompiler(exelist, version)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_cs_compiler(self):
        compilers, ccache, is_cross, exe_wrap = self._get_compilers('cs', False)
        popen_exceptions = {}
        for comp in compilers:
            if not isinstance(comp, list):
                comp = [comp]
            try:
                p, out, err = Popen_safe(comp + ['--version'])
            except OSError as e:
                popen_exceptions[' '.join(comp + ['--version'])] = e
                continue

            version = search_version(out)
            if 'Mono' in out:
                return MonoCompiler(comp, version)
            elif "Visual C#" in out:
                return VisualStudioCsCompiler(comp, version)

        self._handle_exceptions(popen_exceptions, compilers)

    def detect_vala_compiler(self):
        if 'VALAC' in os.environ:
            exelist = shlex.split(os.environ['VALAC'])
        elif 'vala' in self.config_info.binaries:
            exelist = mesonlib.stringlistify(self.config_info.binaries['vala'])
        else:
            # TODO support fallback
            exelist = [self.default_vala[0]]
        try:
            p, out = Popen_safe(exelist + ['--version'])[0:2]
        except OSError:
            raise EnvironmentException('Could not execute Vala compiler "%s"' % ' '.join(exelist))
        version = search_version(out)
        if 'Vala' in out:
            return ValaCompiler(exelist, version)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_rust_compiler(self, want_cross):
        popen_exceptions = {}
        compilers, ccache, is_cross, exe_wrap = self._get_compilers('rust', want_cross)
        for compiler in compilers:
            if isinstance(compiler, str):
                compiler = [compiler]
            arg = ['--version']
            try:
                p, out = Popen_safe(compiler + arg)[0:2]
            except OSError as e:
                popen_exceptions[' '.join(compiler + arg)] = e
                continue

            version = search_version(out)

            if 'rustc' in out:
                return RustCompiler(compiler, version, is_cross, exe_wrap)

        self._handle_exceptions(popen_exceptions, compilers)

    def detect_d_compiler(self, want_cross):
        is_cross = False
        # Search for a D compiler.
        # We prefer LDC over GDC unless overridden with the DC
        # environment variable because LDC has a much more
        # up to date language version at time (2016).
        if 'DC' in os.environ:
            exelist = shlex.split(os.environ['DC'])
            if os.path.basename(exelist[-1]).startswith(('ldmd', 'gdmd')):
                    raise EnvironmentException('Meson doesn\'t support %s as it\'s only a DMD frontend for another compiler. Please provide a valid value for DC or unset it so that Meson can resolve the compiler by itself.' % exelist[-1])
        elif self.is_cross_build() and want_cross:
            exelist = mesonlib.stringlistify(self.cross_info.config['binaries']['d'])
            is_cross = True
        elif 'd' in self.config_info.binaries:
            exelist = mesonlib.stringlistify(self.config_info.binaries['d'])
        else:
            for d in self.default_d:
                if shutil.which(d):
                    exelist = [d]
                    break
            else:
                raise EnvironmentException('Could not find any supported D compiler.')

        try:
            p, out = Popen_safe(exelist + ['--version'])[0:2]
        except OSError:
            raise EnvironmentException('Could not execute D compiler "%s"' % ' '.join(exelist))
        version = search_version(out)
        full_version = out.split('\n', 1)[0]

        # Detect the target architecture, required for proper architecture handling on Windows.
        c_compiler = {}
        is_msvc = mesonlib.is_windows() and 'VCINSTALLDIR' in os.environ
        if is_msvc:
            c_compiler = {'c': self.detect_c_compiler(want_cross)} # MSVC compiler is required for correct platform detection.

        arch = detect_cpu_family(c_compiler)
        if is_msvc and arch == 'x86':
            arch = 'x86_mscoff'

        if 'LLVM D compiler' in out:
            return compilers.LLVMDCompiler(exelist, version, is_cross, arch, full_version=full_version)
        elif 'gdc' in out:
            return compilers.GnuDCompiler(exelist, version, is_cross, arch, full_version=full_version)
        elif 'The D Language Foundation' in out or 'Digital Mars' in out:
            return compilers.DmdDCompiler(exelist, version, is_cross, arch, full_version=full_version)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_swift_compiler(self):
        if 'swift' in self.config_info.binaries:
            exelist = mesonlib.stringlistify(self.config_info.binaries['swift'])
        else:
            # TODO support fallback
            exelist = [self.default_swift[0]]
        try:
            p, _, err = Popen_safe(exelist + ['-v'])
        except OSError:
            raise EnvironmentException('Could not execute Swift compiler "%s"' % ' '.join(exelist))
        version = search_version(err)
        if 'Swift' in err:
            return compilers.SwiftCompiler(exelist, version)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_static_linker(self, compiler):
        if compiler.is_cross:
            linker = self.cross_info.config['binaries']['ar']
            if isinstance(linker, str):
                linker = [linker]
            linkers = [linker]
        else:
            evar = BinaryTable.evarMap['ar']
            if evar in os.environ:
                linkers = [shlex.split(os.environ[evar])]
            elif isinstance(compiler, compilers.VisualStudioCCompiler):
                linkers = [self.vs_static_linker, self.clang_cl_static_linker]
            elif isinstance(compiler, compilers.GnuCompiler):
                # Use gcc-ar if available; needed for LTO
                linkers = [self.gcc_static_linker, self.default_static_linker]
            elif isinstance(compiler, compilers.ClangCompiler):
                # Use llvm-ar if available; needed for LTO
                linkers = [self.clang_static_linker, self.default_static_linker]
            elif isinstance(compiler, compilers.DCompiler):
                # Prefer static linkers over linkers used by D compilers
                if mesonlib.is_windows():
                    linkers = [self.vs_static_linker, self.clang_cl_static_linker, compiler.get_linker_exelist()]
                else:
                    linkers = [self.default_static_linker, compiler.get_linker_exelist()]
            else:
                linkers = [self.default_static_linker]
        popen_exceptions = {}
        for linker in linkers:
            if not set(['lib', 'lib.exe', 'llvm-lib', 'llvm-lib.exe']).isdisjoint(linker):
                arg = '/?'
            else:
                arg = '--version'
            try:
                p, out, err = Popen_safe(linker + [arg])
            except OSError as e:
                popen_exceptions[' '.join(linker + [arg])] = e
                continue
            if '/OUT:' in out.upper() or '/OUT:' in err.upper():
                return VisualStudioLinker(linker)
            if p.returncode == 0 and ('armar' in linker or 'armar.exe' in linker):
                return ArmarLinker(linker)
            if 'DMD32 D Compiler' in out or 'DMD64 D Compiler' in out:
                return DLinker(linker, compiler.arch)
            if 'LDC - the LLVM D compiler' in out:
                return DLinker(linker, compiler.arch)
            if 'GDC' in out and ' based on D ' in out:
                return DLinker(linker, compiler.arch)
            if err.startswith('Renesas') and ('rlink' in linker or 'rlink.exe' in linker):
                return CcrxLinker(linker)
            if p.returncode == 0:
                return ArLinker(linker)
            if p.returncode == 1 and err.startswith('usage'): # OSX
                return ArLinker(linker)
            if p.returncode == 1 and err.startswith('Usage'): # AIX
                return ArLinker(linker)
        self._handle_exceptions(popen_exceptions, linkers, 'linker')
        raise EnvironmentException('Unknown static linker "%s"' % ' '.join(linkers))

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

    def get_compiler_system_dirs(self):
        for comp in self.coredata.compilers.values():
            if isinstance(comp, compilers.ClangCompiler):
                index = 1
                break
            elif isinstance(comp, compilers.GnuCompiler):
                index = 2
                break
        else:
            # This option is only supported by gcc and clang. If we don't get a
            # GCC or Clang compiler return and empty list.
            return []

        p, out, _ = Popen_safe(comp.get_exelist() + ['-print-search-dirs'])
        if p.returncode != 0:
            raise mesonlib.MesonException('Could not calculate system search dirs')
        out = out.split('\n')[index].lstrip('libraries: =').split(':')
        return [os.path.normpath(p) for p in out]

    def get_exe_wrapper(self):
        if not self.cross_info.need_exe_wrapper():
            from .dependencies import EmptyExternalProgram
            return EmptyExternalProgram()
        return self.exe_wrapper


class CrossBuildInfo:
    def __init__(self, filename):
        self.config = {'properties': {}}
        self.parse_datafile(filename)
        if 'host_machine' not in self.config and 'target_machine' not in self.config:
            raise mesonlib.MesonException('Cross info file must have either host or a target machine.')
        if 'host_machine' in self.config and 'binaries' not in self.config:
            raise mesonlib.MesonException('Cross file with "host_machine" is missing "binaries".')

    def ok_type(self, i):
        return isinstance(i, (str, int, bool))

    def parse_datafile(self, filename):
        config = configparser.ConfigParser()
        try:
            with open(filename, 'r') as f:
                config.read_file(f, filename)
        except FileNotFoundError:
            raise EnvironmentException('File not found: %s.' % filename)
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

    def get_host_system(self):
        "Name of host system like 'linux', or None"
        if self.has_host():
            return self.config['host_machine']['system']
        return None

    def get_properties(self):
        return self.config['properties']

    def get_root(self):
        return self.get_properties().get('root', None)

    def get_sys_root(self):
        return self.get_properties().get('sys_root', None)

    # When compiling a cross compiler we use the native compiler for everything.
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

    def __eq__(self, other):
        if self.__class__ is not other.__class__:
            return NotImplemented
        return \
            self.system == other.system and \
            self.cpu_family == other.cpu_family and \
            self.cpu == other.cpu and \
            self.endian == other.endian

    def __ne__(self, other):
        if self.__class__ is not other.__class__:
            return NotImplemented
        return not self.__eq__(other)

    @staticmethod
    def detect(compilers = None):
        """Detect the machine we're running on

        If compilers are not provided, we cannot know as much. None out those
        fields to avoid accidentally depending on partial knowledge. The
        underlying ''detect_*'' method can be called to explicitly use the
        partial information.
        """
        return MachineInfo(
            detect_system(),
            detect_cpu_family(compilers) if compilers is not None else None,
            detect_cpu(compilers) if compilers is not None else None,
            sys.byteorder)

    @staticmethod
    def from_literal(literal):
        minimum_literal = {'cpu', 'cpu_family', 'endian', 'system'}
        if set(literal) < minimum_literal:
            raise EnvironmentException(
                'Machine info is currently {}\n'.format(literal) +
                'but is missing {}.'.format(minimum_literal - set(literal)))

        cpu_family = literal['cpu_family']
        if cpu_family not in known_cpu_families:
            mlog.warning('Unknown CPU family %s, please report this at https://github.com/mesonbuild/meson/issues/new' % cpu_family)

        endian = literal['endian']
        if endian not in ('little', 'big'):
            mlog.warning('Unknown endian %s' % endian)

        return MachineInfo(
            literal['system'],
            cpu_family,
            literal['cpu'],
            endian)

    def is_windows(self):
        """
        Machine is windows?
        """
        return self.system == 'windows'

    def is_cygwin(self):
        """
        Machine is cygwin?
        """
        return self.system == 'cygwin'

    def is_linux(self):
        """
        Machine is linux?
        """
        return self.system == 'linux'

    def is_darwin(self):
        """
        Machine is Darwin (iOS/OS X)?
        """
        return self.system in ('darwin', 'ios')

    def is_android(self):
        """
        Machine is Android?
        """
        return self.system == 'android'

    def is_haiku(self):
        """
        Machine is Haiku?
        """
        return self.system == 'haiku'

    def is_openbsd(self):
        """
        Machine is OpenBSD?
        """
        return self.system == 'openbsd'

    # Various prefixes and suffixes for import libraries, shared libraries,
    # static libraries, and executables.
    # Versioning is added to these names in the backends as-needed.

    def get_exe_suffix(self):
        if self.is_windows() or self.is_cygwin():
            return 'exe'
        else:
            return ''

    def get_object_suffix(self):
        if self.is_windows():
            return 'obj'
        else:
            return 'o'

    def libdir_layout_is_win(self):
        return self.is_windows() \
            or self.is_cygwin()

class MachineInfos(PerMachine):
    def __init__(self):
        super().__init__(None, None, None)

    def default_missing(self):
        """Default host to buid and target to host.

        This allows just specifying nothing in the native case, just host in the
        cross non-compiler case, and just target in the native-built
        cross-compiler case.
        """
        if self.host is None:
            self.host = self.build
        if self.target is None:
            self.target = self.host

    def miss_defaulting(self):
        """Unset definition duplicated from their previous to None

        This is the inverse of ''default_missing''. By removing defaulted
        machines, we can elaborate the original and then redefault them and thus
        avoid repeating the elaboration explicitly.
        """
        if self.target == self.host:
            self.target = None
        if self.host == self.build:
            self.host = None

    def detect_build(self, compilers = None):
        self.build = MachineInfo.detect(compilers)

class BinaryTable:
    # Map from language identifiers to environment variables.
    evarMap = {
        # Compilers
        'c': 'CC',
        'cpp': 'CXX',
        'cs': 'CSC',
        'd': 'DC',
        'fortran': 'FC',
        'objc': 'OBJC',
        'objcpp': 'OBJCXX',
        'rust': 'RUSTC',
        'vala': 'VALAC',

        # Binutils
        'strip': 'STRIP',
        'ar': 'AR',
    }

    @classmethod
    def detect_ccache(cls):
        try:
            has_ccache = subprocess.call(['ccache', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            has_ccache = 1
        if has_ccache == 0:
            cmdlist = ['ccache']
        else:
            cmdlist = []
        return cmdlist

    @classmethod
    def warn_about_lang_pointing_to_cross(cls, compiler_exe, evar):
        evar_str = os.environ.get(evar, 'WHO_WOULD_CALL_THEIR_COMPILER_WITH_THIS_NAME')
        if evar_str == compiler_exe:
            mlog.warning('''Env var %s seems to point to the cross compiler.
This is probably wrong, it should always point to the native compiler.''' % evar)

    @classmethod
    def parse_entry(cls, entry):
        compiler = mesonlib.stringlistify(entry)
        # Ensure ccache exists and remove it if it doesn't
        if compiler[0] == 'ccache':
            compiler = compiler[1:]
            ccache = cls.detect_ccache()
        else:
            ccache = []
        # Return value has to be a list of compiler 'choices'
        return compiler, ccache
