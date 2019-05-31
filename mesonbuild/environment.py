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

import os, platform, re, sys, shlex, shutil, subprocess, typing

from . import coredata
from .linkers import ArLinker, ArmarLinker, VisualStudioLinker, DLinker, CcrxLinker, IntelVisualStudioLinker
from . import mesonlib
from .mesonlib import (
    MesonException, EnvironmentException, MachineChoice, Popen_safe,
    PerMachineDefaultable, PerThreeMachineDefaultable
)
from . import mlog

from .envconfig import (
    BinaryTable, Directories, MachineInfo, MesonConfigFile,
    Properties, known_cpu_families,
)
from . import compilers
from .compilers import (
    Compiler,
    CompilerType,
    is_assembly,
    is_header,
    is_library,
    is_llvm_ir,
    is_object,
    is_source,
)
from functools import lru_cache
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
    FlangFortranCompiler,
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
    IntelClCCompiler,
    IntelClCPPCompiler,
    IntelFortranCompiler,
    IntelClFortranCompiler,
    JavaCompiler,
    MonoCompiler,
    CudaCompiler,
    VisualStudioCsCompiler,
    NAGFortranCompiler,
    Open64FortranCompiler,
    PathScaleFortranCompiler,
    PGICCompiler,
    PGICPPCompiler,
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

CompilersDict = typing.Dict[str, Compiler]

def detect_gcovr(min_version='3.3', new_rootdir_version='4.2', log=False):
    gcovr_exe = 'gcovr'
    try:
        p, found = Popen_safe([gcovr_exe, '--version'])[0:2]
    except (FileNotFoundError, PermissionError):
        # Doesn't exist in PATH or isn't executable
        return None, None
    found = search_version(found)
    if p.returncode == 0 and mesonlib.version_compare(found, '>=' + min_version):
        if log:
            mlog.log('Found gcovr-{} at {}'.format(found, shlex.quote(shutil.which(gcovr_exe))))
        return gcovr_exe, mesonlib.version_compare(found, '>=' + new_rootdir_version)
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

def detect_ninja(version: str = '1.5', log: bool = False) -> str:
    env_ninja = os.environ.get('NINJA', None)
    for n in [env_ninja] if env_ninja else ['ninja', 'ninja-build', 'samu']:
        try:
            p, found = Popen_safe([n, '--version'])[0:2]
        except (FileNotFoundError, PermissionError):
            # Doesn't exist in PATH or isn't executable
            continue
        found = found.strip()
        # Perhaps we should add a way for the caller to know the failure mode
        # (not found or too old)
        if p.returncode == 0 and mesonlib.version_compare(found, '>=' + version):
            n = shutil.which(n)
            if log:
                name = os.path.basename(n)
                if name.endswith('-' + found):
                    name = name[0:-1 - len(found)]
                if name == 'ninja-build':
                    name = 'ninja'
                if name == 'samu':
                    name = 'samurai'
                mlog.log('Found {}-{} at {}'.format(name, found, shlex.quote(n)))
            return n

def detect_native_windows_arch():
    """
    The architecture of Windows itself: x86, amd64 or arm64
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

def detect_windows_arch(compilers: CompilersDict) -> str:
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
    1. Check environment variables that are set by Windows and WOW64 to find out
       if this is x86 (possibly in WOW64), if so use that as our 'native'
       architecture.
    2. If the compiler toolchain target architecture is x86, use that as our
      'native' architecture.
    3. Otherwise, use the actual Windows architecture

    """
    os_arch = detect_native_windows_arch()
    if os_arch == 'x86':
        return os_arch
    # If we're on 64-bit Windows, 32-bit apps can be compiled without
    # cross-compilation. So if we're doing that, just set the native arch as
    # 32-bit and pretend like we're running under WOW64. Else, return the
    # actual Windows architecture that we deduced above.
    for compiler in compilers.values():
        if compiler.id == 'msvc' and (compiler.target == 'x86' or compiler.target == '80x86'):
            return 'x86'
        if compiler.id == 'clang-cl' and compiler.target == 'x86':
            return 'x86'
        if compiler.id == 'gcc' and compiler.has_builtin_define('__i386__'):
            return 'x86'
    return os_arch

def any_compiler_has_define(compilers: CompilersDict, define):
    for c in compilers.values():
        try:
            if c.has_builtin_define(define):
                return True
        except mesonlib.MesonException:
            # Ignore compilers that do not support has_builtin_define.
            pass
    return False

def detect_cpu_family(compilers: CompilersDict) -> str:
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
    elif trial == 'bepc':
        trial = 'x86'
    # OpenBSD's 64 bit arm architecute identifies as 'arm64'
    elif trial == 'arm64':
        trial = 'aarch64'
    elif trial.startswith('arm'):
        trial = 'arm'
    elif trial.startswith('ppc64'):
        trial = 'ppc64'
    elif trial == 'macppc':
        trial = 'ppc'
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
    elif trial == 'parisc64':
        # ATM there is no 64 bit userland for PA-RISC. Thus always
        # report it as 32 bit for simplicity.
        trial = 'parisc'

    if trial not in known_cpu_families:
        mlog.warning('Unknown CPU family {!r}, please report this at '
                     'https://github.com/mesonbuild/meson/issues/new with the'
                     'output of `uname -a` and `cat /proc/cpuinfo`'.format(trial))

    return trial

def detect_cpu(compilers: CompilersDict):
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

def detect_machine_info(compilers: typing.Optional[CompilersDict] = None) -> MachineInfo:
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

# TODO make this compare two `MachineInfo`s purely. How important is the
# `detect_cpu_family({})` distinction? It is the one impediment to that.
def machine_info_can_run(machine_info: MachineInfo):
    """Whether we can run binaries for this machine on the current machine.

    Can almost always run 32-bit binaries on 64-bit natively if the host
    and build systems are the same. We don't pass any compilers to
    detect_cpu_family() here because we always want to know the OS
    architecture, not what the compiler environment tells us.
    """
    if machine_info.system != detect_system():
        return False
    true_build_cpu_family = detect_cpu_family({})
    return \
        (machine_info.cpu_family == true_build_cpu_family) or \
        ((true_build_cpu_family == 'x86_64') and (machine_info.cpu_family == 'x86'))

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
    # We'll demystify it a bit with a verbose definition.
    version_regex = re.compile(r"""
    (?<!                # Zero-width negative lookbehind assertion
        (
            \d          # One digit
            | \.        # Or one period
        )               # One occurrence
    )
    # Following pattern must not follow a digit or period
    (
        \d{1,2}         # One or two digits
        (
            \.\d+       # Period and one or more digits
        )+              # One or more occurrences
        (
            -[a-zA-Z0-9]+   # Hyphen and one or more alphanumeric
        )?              # Zero or one occurrence
    )                   # One occurrence
    """, re.VERBOSE)
    match = version_regex.search(text)
    if match:
        return match.group(0)
    return 'unknown version'

class Environment:
    private_dir = 'meson-private'
    log_dir = 'meson-logs'
    info_dir = 'meson-info'

    def __init__(self, source_dir, build_dir, options):
        self.source_dir = source_dir
        self.build_dir = build_dir

        # Do not try to create build directories when build_dir is none.
        # This reduced mode is used by the --buildoptions introspector
        if build_dir is not None:
            self.scratch_dir = os.path.join(build_dir, Environment.private_dir)
            self.log_dir = os.path.join(build_dir, Environment.log_dir)
            self.info_dir = os.path.join(build_dir, Environment.info_dir)
            os.makedirs(self.scratch_dir, exist_ok=True)
            os.makedirs(self.log_dir, exist_ok=True)
            os.makedirs(self.info_dir, exist_ok=True)
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
        else:
            # Just create a fresh coredata in this case
            self.create_new_coredata(options)

        ## locally bind some unfrozen configuration

        # Stores machine infos, the only *three* machine one because we have a
        # target machine info on for the user (Meson never cares about the
        # target machine.)
        machines = PerThreeMachineDefaultable()

        # Similar to coredata.compilers, but lower level in that there is no
        # meta data, only names/paths.
        binaries = PerMachineDefaultable()

        # Misc other properties about each machine.
        properties = PerMachineDefaultable()

        # Store paths for native and cross build files. There is no target
        # machine information here because nothing is installed for the target
        # architecture, just the build and host architectures
        paths = PerMachineDefaultable()

        ## Setup build machine defaults

        # Will be fully initialized later using compilers later.
        machines.build = detect_machine_info()

        # Just uses hard-coded defaults and environment variables. Might be
        # overwritten by a native file.
        binaries.build = BinaryTable()
        properties.build = Properties()

        ## Read in native file(s) to override build machine configuration

        if self.coredata.config_files is not None:
            config = MesonConfigFile.from_config_parser(
                coredata.load_configs(self.coredata.config_files))
            binaries.build = BinaryTable(config.get('binaries', {}))
            paths.build = Directories(**config.get('paths', {}))

        ## Read in cross file(s) to override host machine configuration

        if self.coredata.cross_files:
            config = MesonConfigFile.from_config_parser(
                coredata.load_configs(self.coredata.cross_files))
            properties.host = Properties(config.get('properties', {}), False)
            binaries.host = BinaryTable(config.get('binaries', {}), False)
            if 'host_machine' in config:
                machines.host = MachineInfo.from_literal(config['host_machine'])
            if 'target_machine' in config:
                machines.target = MachineInfo.from_literal(config['target_machine'])
            paths.host = Directories(**config.get('paths', {}))

        ## "freeze" now initialized configuration, and "save" to the class.

        self.machines = machines.default_missing()
        self.binaries = binaries.default_missing()
        self.properties = properties.default_missing()
        self.paths = paths.default_missing()

        exe_wrapper = self.binaries.host.lookup_entry('exe_wrapper')
        if exe_wrapper is not None:
            from .dependencies import ExternalProgram
            self.exe_wrapper = ExternalProgram.from_bin_list(
                self.binaries.host,
                'exe_wrapper')
        else:
            self.exe_wrapper = None

        self.cmd_line_options = options.cmd_line_options.copy()

        # List of potential compilers.
        if mesonlib.is_windows():
            # Intel C and C++ compiler is icl on Windows, but icc and icpc elsewhere.
            # Search for icl before cl, since Intel "helpfully" provides a
            # cl.exe that returns *exactly the same thing* that microsofts
            # cl.exe does, and if icl is present, it's almost certainly what
            # you want.
            self.default_c = ['icl', 'cl', 'cc', 'gcc', 'clang', 'clang-cl', 'pgcc']
            # There is currently no pgc++ for Windows, only for  Mac and Linux.
            self.default_cpp = ['icl', 'cl', 'c++', 'g++', 'clang++', 'clang-cl']
            self.default_fortran = ['ifort', 'gfortran', 'flang', 'pgfortran', 'g95']
        else:
            self.default_c = ['cc', 'gcc', 'clang', 'pgcc', 'icc']
            self.default_cpp = ['c++', 'g++', 'clang++', 'pgc++', 'icpc']
            self.default_fortran = ['gfortran', 'flang', 'pgfortran', 'ifort', 'g95']
        if mesonlib.is_windows():
            self.default_cs = ['csc', 'mcs']
        else:
            self.default_cs = ['mcs', 'csc']
        self.default_objc = ['cc']
        self.default_objcpp = ['c++']
        self.default_d = ['ldc2', 'ldc', 'gdc', 'dmd']
        self.default_java = ['javac']
        self.default_cuda = ['nvcc']
        self.default_rust = ['rustc']
        self.default_swift = ['swiftc']
        self.default_vala = ['valac']
        self.default_static_linker = ['ar']
        self.default_strip = ['strip']
        self.vs_static_linker = ['lib']
        self.clang_cl_static_linker = ['llvm-lib']
        self.cuda_static_linker = ['nvlink']
        self.gcc_static_linker = ['gcc-ar']
        self.clang_static_linker = ['llvm-ar']
        self.default_cmake = ['cmake']
        self.default_pkgconfig = ['pkg-config']

    def create_new_coredata(self, options):
        # WARNING: Don't use any values from coredata in __init__. It gets
        # re-initialized with project options by the interpreter during
        # build file parsing.
        self.coredata = coredata.CoreData(options)
        # Used by the regenchecker script, which runs meson
        self.coredata.meson_command = mesonlib.meson_command
        self.first_invocation = True

    def is_cross_build(self) -> bool:
        return not self.machines.matches_build_machine(MachineChoice.HOST)

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

    @lru_cache(maxsize=None)
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

    def _get_compilers(self, lang, for_machine):
        '''
        The list of compilers is detected in the exact same way for
        C, C++, ObjC, ObjC++, Fortran, CS so consolidate it here.
        '''
        value = self.binaries[for_machine].lookup_entry(lang)
        if value is not None:
            compilers, ccache = BinaryTable.parse_entry(value)
            # Return value has to be a list of compiler 'choices'
            compilers = [compilers]
        else:
            if not self.machines.matches_build_machine(for_machine):
                raise EnvironmentException('{!r} compiler binary not defined in cross or native file'.format(lang))
            compilers = getattr(self, 'default_' + lang)
            ccache = BinaryTable.detect_ccache()

        if self.machines.matches_build_machine(for_machine):
            exe_wrap = None
        else:
            exe_wrap = self.get_exe_wrapper()

        return compilers, ccache, exe_wrap

    def _handle_exceptions(self, exceptions, binaries, bintype='compiler'):
        errmsg = 'Unknown {}(s): {}'.format(bintype, binaries)
        if exceptions:
            errmsg += '\nThe follow exceptions were encountered:'
            for (c, e) in exceptions.items():
                errmsg += '\nRunning "{0}" gave "{1}"'.format(c, e)
        raise EnvironmentException(errmsg)

    def _detect_c_or_cpp_compiler(self, lang, for_machine):
        popen_exceptions = {}
        compilers, ccache, exe_wrap = self._get_compilers(lang, for_machine)
        is_cross = not self.machines.matches_build_machine(for_machine)

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
            elif 'icl' in compiler[0]:
                # if you pass anything to icl you get stuck in a pager
                arg = ''
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
            if 'Free Software Foundation' in out or 'xt-' in out:
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
                return cls(ccache + compiler, version, compiler_type, for_machine, is_cross, exe_wrap, defines, full_version=full_version)

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
                return cls(ccache + compiler, version, compiler_type, for_machine, is_cross, exe_wrap, full_version=full_version)
            if 'CL.EXE COMPATIBILITY' in out:
                # if this is clang-cl masquerading as cl, detect it as cl, not
                # clang
                arg = '--version'
                try:
                    p, out, err = Popen_safe(compiler + [arg])
                except OSError as e:
                    popen_exceptions[' '.join(compiler + [arg])] = e
                version = search_version(out)
                match = re.search('^Target: (.*?)-', out, re.MULTILINE)
                if match:
                    target = match.group(1)
                else:
                    target = 'unknown target'
                cls = ClangClCCompiler if lang == 'c' else ClangClCPPCompiler
                return cls(compiler, version, for_machine, is_cross, exe_wrap, target)
            if 'clang' in out:
                if 'Apple' in out or self.machines[for_machine].is_darwin():
                    compiler_type = CompilerType.CLANG_OSX
                elif 'windows' in out or self.machines[for_machine].is_windows():
                    compiler_type = CompilerType.CLANG_MINGW
                else:
                    compiler_type = CompilerType.CLANG_STANDARD
                cls = ClangCCompiler if lang == 'c' else ClangCPPCompiler
                return cls(ccache + compiler, version, compiler_type, for_machine, is_cross, exe_wrap, full_version=full_version)
            if 'Intel(R) C++ Intel(R)' in err:
                version = search_version(err)
                target = 'x86' if 'IA-32' in err else 'x86_64'
                cls = IntelClCCompiler if lang == 'c' else IntelClCPPCompiler
                return cls(compiler, version, for_machine, is_cross, exe_wrap, target)
                return cls(ccache + compiler, version, compiler_type, for_machine, is_cross, exe_wrap, full_version=full_version)
            if 'Microsoft' in out or 'Microsoft' in err:
                # Latest versions of Visual Studio print version
                # number to stderr but earlier ones print version
                # on stdout.  Why? Lord only knows.
                # Check both outputs to figure out version.
                for lookat in [err, out]:
                    version = search_version(lookat)
                    if version != 'unknown version':
                        break
                else:
                    m = 'Failed to detect MSVC compiler version: stderr was\n{!r}'
                    raise EnvironmentException(m.format(err))
                match = re.search(' for (.*)$', lookat.split('\n')[0])
                if match:
                    target = match.group(1)
                else:
                    target = 'x86'
                cls = VisualStudioCCompiler if lang == 'c' else VisualStudioCPPCompiler
                return cls(compiler, version, for_machine, is_cross, exe_wrap, target)
            if 'PGI Compilers' in out:
                if self.machines[for_machine].is_darwin():
                    compiler_type = CompilerType.PGI_OSX
                elif self.machines[for_machine].is_windows():
                    compiler_type = CompilerType.PGI_WIN
                else:
                    compiler_type = CompilerType.PGI_STANDARD
                cls = PGICCompiler if lang == 'c' else PGICPPCompiler
                return cls(ccache + compiler, version, compiler_type, for_machine, is_cross, compiler_type, exe_wrap)
            if '(ICC)' in out:
                if self.machines[for_machine].is_darwin():
                    compiler_type = CompilerType.ICC_OSX
                elif self.machines[for_machine].is_windows():
                    # TODO: fix ICC on Windows
                    compiler_type = CompilerType.ICC_WIN
                else:
                    compiler_type = CompilerType.ICC_STANDARD
                cls = IntelCCompiler if lang == 'c' else IntelCPPCompiler
                return cls(ccache + compiler, version, compiler_type, for_machine, is_cross, exe_wrap, full_version=full_version)
            if 'ARM' in out:
                compiler_type = CompilerType.ARM_WIN
                cls = ArmCCompiler if lang == 'c' else ArmCPPCompiler
                return cls(ccache + compiler, version, compiler_type, for_machine, is_cross, exe_wrap, full_version=full_version)
            if 'RX Family' in out:
                compiler_type = CompilerType.CCRX_WIN
                cls = CcrxCCompiler if lang == 'c' else CcrxCPPCompiler
                return cls(ccache + compiler, version, compiler_type, for_machine, is_cross, exe_wrap, full_version=full_version)

        self._handle_exceptions(popen_exceptions, compilers)

    def detect_c_compiler(self, for_machine):
        return self._detect_c_or_cpp_compiler('c', for_machine)

    def detect_cpp_compiler(self, for_machine):
        return self._detect_c_or_cpp_compiler('cpp', for_machine)

    def detect_cuda_compiler(self, for_machine):
        popen_exceptions = {}
        compilers, ccache, exe_wrap = self._get_compilers('cuda', for_machine)
        for compiler in compilers:
            if isinstance(compiler, str):
                compiler = [compiler]
            else:
                raise EnvironmentException()
            arg = '--version'
            try:
                p, out, err = Popen_safe(compiler + [arg])
            except OSError as e:
                popen_exceptions[' '.join(compiler + [arg])] = e
                continue
            # Example nvcc printout:
            #
            #     nvcc: NVIDIA (R) Cuda compiler driver
            #     Copyright (c) 2005-2018 NVIDIA Corporation
            #     Built on Sat_Aug_25_21:08:01_CDT_2018
            #     Cuda compilation tools, release 10.0, V10.0.130
            #
            # search_version() first finds the "10.0" after "release",
            # rather than the more precise "10.0.130" after "V".
            # The patch version number is occasionally important; For
            # instance, on Linux,
            #    - CUDA Toolkit 8.0.44 requires NVIDIA Driver 367.48
            #    - CUDA Toolkit 8.0.61 requires NVIDIA Driver 375.26
            # Luckily, the "V" also makes it very simple to extract
            # the full version:
            version = out.strip().split('V')[-1]
            cls = CudaCompiler
            return cls(ccache + compiler, version, for_machine, exe_wrap)
        raise EnvironmentException('Could not find suitable CUDA compiler: "' + ' '.join(compilers) + '"')

    def detect_fortran_compiler(self, for_machine):
        popen_exceptions = {}
        compilers, ccache, exe_wrap = self._get_compilers('fortran', for_machine)
        is_cross = not self.machines.matches_build_machine(for_machine)
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
                    return cls(compiler, version, compiler_type, for_machine, is_cross, exe_wrap, defines, full_version=full_version)

                if 'G95' in out:
                    return G95FortranCompiler(compiler, version, for_machine, is_cross, exe_wrap, full_version=full_version)

                if 'Sun Fortran' in err:
                    version = search_version(err)
                    return SunFortranCompiler(compiler, version, for_machine, is_cross, exe_wrap, full_version=full_version)

                if 'Intel(R) Visual Fortran' in err:
                    version = search_version(err)
                    target = 'x86' if 'IA-32' in err else 'x86_64'
                    return IntelClFortranCompiler(compiler, version, is_cross, target, exe_wrap)

                if 'ifort (IFORT)' in out:
                    return IntelFortranCompiler(compiler, version, for_machine, is_cross, exe_wrap, full_version=full_version)

                if 'PathScale EKOPath(tm)' in err:
                    return PathScaleFortranCompiler(compiler, version, for_machine, is_cross, exe_wrap, full_version=full_version)

                if 'PGI Compilers' in out:
                    if self.machine[for_machine].is_darwin():
                        compiler_type = CompilerType.PGI_OSX
                    elif self.machines[for_machine].is_windows():
                        compiler_type = CompilerType.PGI_WIN
                    else:
                        compiler_type = CompilerType.PGI_STANDARD
                    return PGIFortranCompiler(compiler, version, compiler_type, for_machine, is_cross, exe_wrap, full_version=full_version)

                if 'flang' in out or 'clang' in out:
                    return FlangFortranCompiler(compiler, version, for_machine, is_cross, exe_wrap, full_version=full_version)

                if 'Open64 Compiler Suite' in err:
                    return Open64FortranCompiler(compiler, version, for_machine, is_cross, exe_wrap, full_version=full_version)

                if 'NAG Fortran' in err:
                    return NAGFortranCompiler(compiler, version, for_machine, is_cross, exe_wrap, full_version=full_version)
        self._handle_exceptions(popen_exceptions, compilers)

    def get_scratch_dir(self):
        return self.scratch_dir

    def detect_objc_compiler(self, for_machine):
        popen_exceptions = {}
        compilers, ccache, exe_wrap = self._get_compilers('objc', for_machine)
        is_cross = not self.machines.matches_build_machine(for_machine)
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
                return GnuObjCCompiler(ccache + compiler, version, compiler_type, for_machine, is_cross, exe_wrap, defines)
            if out.startswith('Apple LLVM') or out.startswith('Apple clang'):
                return ClangObjCCompiler(ccache + compiler, version, CompilerType.CLANG_OSX, for_machine, is_cross, exe_wrap)
            if 'windows' in out:
                return ClangObjCCompiler(ccache + compiler, version, CompilerType.CLANG_MINGW, for_machine, is_cross, exe_wrap)
            if out.startswith(('clang', 'OpenBSD clang')):
                return ClangObjCCompiler(ccache + compiler, version, CompilerType.CLANG_STANDARD, for_machine, is_cross, exe_wrap)
        self._handle_exceptions(popen_exceptions, compilers)

    def detect_objcpp_compiler(self, for_machine):
        popen_exceptions = {}
        compilers, ccache, exe_wrap = self._get_compilers('objcpp', for_machine)
        is_cross = not self.machines.matches_build_machine(for_machine)
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
                return GnuObjCPPCompiler(ccache + compiler, version, compiler_type, for_machine, is_cross, exe_wrap, defines)
            if out.startswith('Apple LLVM') or out.startswith('Apple clang'):
                return ClangObjCPPCompiler(ccache + compiler, version, CompilerType.CLANG_OSX, for_machine, is_cross, exe_wrap)
            if 'windows' in out:
                return ClangObjCPPCompiler(ccache + compiler, version, CompilerType.CLANG_MINGW, for_machine, is_cross, exe_wrap)
            if out.startswith(('clang', 'OpenBSD clang')):
                return ClangObjCPPCompiler(ccache + compiler, version, CompilerType.CLANG_STANDARD, for_machine, is_cross, exe_wrap)
        self._handle_exceptions(popen_exceptions, compilers)

    def detect_java_compiler(self, for_machine):
        exelist = self.binaries.host.lookup_entry('java')
        if exelist is None:
            # TODO support fallback
            exelist = [self.default_java[0]]

        try:
            p, out, err = Popen_safe(exelist + ['-version'])
        except OSError:
            raise EnvironmentException('Could not execute Java compiler "%s"' % ' '.join(exelist))
        if 'javac' in out or 'javac' in err:
            version = search_version(err if 'javac' in err else out)
            if not version or version == 'unknown version':
                parts = (err if 'javac' in err else out).split()
                if len(parts) > 1:
                    version = parts[1]
            return JavaCompiler(exelist, version, for_machine)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_cs_compiler(self, for_machine):
        compilers, ccache, exe_wrap = self._get_compilers('cs', for_machine)
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
                return MonoCompiler(comp, version, for_machine)
            elif "Visual C#" in out:
                return VisualStudioCsCompiler(comp, version, for_machine)

        self._handle_exceptions(popen_exceptions, compilers)

    def detect_vala_compiler(self, for_machine):
        exelist = self.binaries.host.lookup_entry('vala')
        is_cross = not self.machines.matches_build_machine(for_machine)
        if exelist is None:
            # TODO support fallback
            exelist = [self.default_vala[0]]

        try:
            p, out = Popen_safe(exelist + ['--version'])[0:2]
        except OSError:
            raise EnvironmentException('Could not execute Vala compiler "%s"' % ' '.join(exelist))
        version = search_version(out)
        if 'Vala' in out:
            return ValaCompiler(exelist, version, for_machine, is_cross)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_rust_compiler(self, for_machine):
        popen_exceptions = {}
        compilers, ccache, exe_wrap = self._get_compilers('rust', for_machine)
        is_cross = not self.machines.matches_build_machine(for_machine)
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
                return RustCompiler(compiler, version, for_machine, is_cross, exe_wrap)

        self._handle_exceptions(popen_exceptions, compilers)

    def detect_d_compiler(self, for_machine: MachineChoice):
        exelist = self.binaries[for_machine].lookup_entry('d')
        # Search for a D compiler.
        # We prefer LDC over GDC unless overridden with the DC
        # environment variable because LDC has a much more
        # up to date language version at time (2016).
        if exelist is not None:
            if os.path.basename(exelist[-1]).startswith(('ldmd', 'gdmd')):
                raise EnvironmentException(
                    'Meson does not support {} as it is only a DMD frontend for another compiler.'
                    'Please provide a valid value for DC or unset it so that Meson can resolve the compiler by itself.'.format(exelist[-1]))
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
            c_compiler = {'c': self.detect_c_compiler(for_machine)} # MSVC compiler is required for correct platform detection.

        arch = detect_cpu_family(c_compiler)
        if is_msvc and arch == 'x86':
            arch = 'x86_mscoff'

        if 'LLVM D compiler' in out:
            return compilers.LLVMDCompiler(exelist, version, for_machine, arch, full_version=full_version)
        elif 'gdc' in out:
            return compilers.GnuDCompiler(exelist, version, for_machine, arch, full_version=full_version)
        elif 'The D Language Foundation' in out or 'Digital Mars' in out:
            return compilers.DmdDCompiler(exelist, version, for_machine, arch, full_version=full_version)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_swift_compiler(self, for_machine):
        exelist = self.binaries.host.lookup_entry('swift')
        is_cross = not self.machines.matches_build_machine(for_machine)
        if exelist is None:
            # TODO support fallback
            exelist = [self.default_swift[0]]

        try:
            p, _, err = Popen_safe(exelist + ['-v'])
        except OSError:
            raise EnvironmentException('Could not execute Swift compiler "%s"' % ' '.join(exelist))
        version = search_version(err)
        if 'Swift' in err:
            return compilers.SwiftCompiler(exelist, version, for_machine, is_cross)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def compiler_from_language(self, lang: str, for_machine: MachineChoice):
        if lang == 'c':
            comp = self.detect_c_compiler(for_machine)
        elif lang == 'cpp':
            comp = self.detect_cpp_compiler(for_machine)
        elif lang == 'objc':
            comp = self.detect_objc_compiler(for_machine)
        elif lang == 'cuda':
            comp = self.detect_cuda_compiler(for_machine)
        elif lang == 'objcpp':
            comp = self.detect_objcpp_compiler(for_machine)
        elif lang == 'java':
            comp = self.detect_java_compiler(for_machine)
        elif lang == 'cs':
            comp = self.detect_cs_compiler(for_machine)
        elif lang == 'vala':
            comp = self.detect_vala_compiler(for_machine)
        elif lang == 'd':
            comp = self.detect_d_compiler(for_machine)
        elif lang == 'rust':
            comp = self.detect_rust_compiler(for_machine)
        elif lang == 'fortran':
            comp = self.detect_fortran_compiler(for_machine)
        elif lang == 'swift':
            comp = self.detect_swift_compiler(for_machine)
        else:
            comp = None
        return comp

    def detect_compiler_for(self, lang: str, for_machine: MachineChoice):
        comp = self.compiler_from_language(lang, for_machine)
        if comp is not None:
            assert comp.for_machine == for_machine
            self.coredata.process_new_compiler(lang, comp, self)
        return comp

    def detect_static_linker(self, compiler):
        linker = self.binaries[compiler.for_machine].lookup_entry('ar')
        if linker is not None:
            linkers = [linker]
        else:
            evar = 'AR'
            if isinstance(compiler, compilers.CudaCompiler):
                linkers = [self.cuda_static_linker, self.default_static_linker]
            elif evar in os.environ:
                linkers = [shlex.split(os.environ[evar])]
            elif isinstance(compiler, compilers.VisualStudioLikeCompiler):
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
            elif isinstance(compiler, IntelClCCompiler):
                # Intel has it's own linker that acts like microsoft's lib
                linkers = ['xilib']
            else:
                linkers = [self.default_static_linker]
        popen_exceptions = {}
        for linker in linkers:
            if not {'lib', 'lib.exe', 'llvm-lib', 'llvm-lib.exe', 'xilib', 'xilib.exe'}.isdisjoint(linker):
                arg = '/?'
            else:
                arg = '--version'
            try:
                p, out, err = Popen_safe(linker + [arg])
            except OSError as e:
                popen_exceptions[' '.join(linker + [arg])] = e
                continue
            if "xilib: executing 'lib'" in err:
                return IntelVisualStudioLinker(linker, getattr(compiler, 'machine', None))
            if '/OUT:' in out.upper() or '/OUT:' in err.upper():
                return VisualStudioLinker(linker, getattr(compiler, 'machine', None))
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
            if p.returncode == 1 and err.startswith('ar: bad option: --'): # Solaris
                return ArLinker(linker)
        self._handle_exceptions(popen_exceptions, linkers, 'linker')
        raise EnvironmentException('Unknown static linker "%s"' % ' '.join(linkers))

    def get_source_dir(self):
        return self.source_dir

    def get_build_dir(self):
        return self.build_dir

    def get_import_lib_dir(self) -> str:
        "Install dir for the import library (library used for linking)"
        return self.get_libdir()

    def get_shared_module_dir(self) -> str:
        "Install dir for shared modules that are loaded at runtime"
        return self.get_libdir()

    def get_shared_lib_dir(self) -> str:
        "Install dir for the shared library"
        m = self.machines.host
        # Windows has no RPATH or similar, so DLLs must be next to EXEs.
        if m.is_windows() or m.is_cygwin():
            return self.get_bindir()
        return self.get_libdir()

    def get_static_lib_dir(self) -> str:
        "Install dir for the static library"
        return self.get_libdir()

    def get_prefix(self) -> str:
        return self.coredata.get_builtin_option('prefix')

    def get_libdir(self) -> str:
        return self.coredata.get_builtin_option('libdir')

    def get_libexecdir(self) -> str:
        return self.coredata.get_builtin_option('libexecdir')

    def get_bindir(self) -> str:
        return self.coredata.get_builtin_option('bindir')

    def get_includedir(self) -> str:
        return self.coredata.get_builtin_option('includedir')

    def get_mandir(self) -> str:
        return self.coredata.get_builtin_option('mandir')

    def get_datadir(self) -> str:
        return self.coredata.get_builtin_option('datadir')

    def get_compiler_system_dirs(self, for_machine: MachineChoice):
        for comp in self.coredata.compilers[for_machine].values():
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

    def need_exe_wrapper(self, for_machine: MachineChoice = MachineChoice.HOST):
        value = self.properties[for_machine].get('needs_exe_wrapper', None)
        if value is not None:
            return value
        return not machine_info_can_run(self.machines[for_machine])

    def get_exe_wrapper(self):
        if not self.need_exe_wrapper():
            from .dependencies import EmptyExternalProgram
            return EmptyExternalProgram()
        return self.exe_wrapper
