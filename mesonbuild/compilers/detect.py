# Copyright 2012-2021 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ..mesonlib import (
    MachineChoice, MesonException, EnvironmentException,
    search_version, is_windows, Popen_safe, windows_proof_rm,
)
from ..envconfig import BinaryTable
from .. import mlog

from ..linkers import (
    guess_win_linker,
    guess_nix_linker,
    AIXArLinker,
    ArLinker,
    ArmarLinker,
    ArmClangDynamicLinker,
    ArmDynamicLinker,
    CcrxLinker,
    CcrxDynamicLinker,
    CompCertLinker,
    CompCertDynamicLinker,
    C2000Linker,
    C2000DynamicLinker,
    TILinker,
    TIDynamicLinker,
    DLinker,
    NAGDynamicLinker,
    NvidiaHPC_DynamicLinker,
    PGIDynamicLinker,
    PGIStaticLinker,
    StaticLinker,
    Xc16Linker,
    Xc16DynamicLinker,
    XilinkDynamicLinker,
    CudaLinker,
    IntelVisualStudioLinker,
    VisualStudioLinker,
    VisualStudioLikeLinkerMixin,
    WASMDynamicLinker,
)
from .compilers import Compiler
from .c import (
    CCompiler,
    AppleClangCCompiler,
    ArmCCompiler,
    ArmclangCCompiler,
    ArmLtdClangCCompiler,
    ClangCCompiler,
    ClangClCCompiler,
    GnuCCompiler,
    ElbrusCCompiler,
    EmscriptenCCompiler,
    IntelCCompiler,
    IntelClCCompiler,
    NvidiaHPC_CCompiler,
    PGICCompiler,
    CcrxCCompiler,
    Xc16CCompiler,
    CompCertCCompiler,
    C2000CCompiler,
    TICCompiler,
    VisualStudioCCompiler,
)
from .cpp import (
    CPPCompiler,
    AppleClangCPPCompiler,
    ArmCPPCompiler,
    ArmclangCPPCompiler,
    ArmLtdClangCPPCompiler,
    ClangCPPCompiler,
    ClangClCPPCompiler,
    GnuCPPCompiler,
    ElbrusCPPCompiler,
    EmscriptenCPPCompiler,
    IntelCPPCompiler,
    IntelClCPPCompiler,
    NvidiaHPC_CPPCompiler,
    PGICPPCompiler,
    CcrxCPPCompiler,
    C2000CPPCompiler,
    TICPPCompiler,
    VisualStudioCPPCompiler,
)
from .cs import MonoCompiler, VisualStudioCsCompiler
from .d import (
    DCompiler,
    DmdDCompiler,
    GnuDCompiler,
    LLVMDCompiler,
)
from .cuda import CudaCompiler
from .fortran import (
    FortranCompiler,
    ArmLtdFlangFortranCompiler,
    G95FortranCompiler,
    GnuFortranCompiler,
    ElbrusFortranCompiler,
    FlangFortranCompiler,
    IntelFortranCompiler,
    IntelClFortranCompiler,
    NAGFortranCompiler,
    Open64FortranCompiler,
    PathScaleFortranCompiler,
    NvidiaHPC_FortranCompiler,
    PGIFortranCompiler,
    SunFortranCompiler,
)
from .java import JavaCompiler
from .objc import (
    ObjCCompiler,
    AppleClangObjCCompiler,
    ClangObjCCompiler,
    GnuObjCCompiler,
)
from .objcpp import (
    ObjCPPCompiler,
    AppleClangObjCPPCompiler,
    ClangObjCPPCompiler,
    GnuObjCPPCompiler,
)
from .cython import CythonCompiler
from .rust import RustCompiler, ClippyRustCompiler
from .swift import SwiftCompiler
from .vala import ValaCompiler
from .mixins.visualstudio import VisualStudioLikeCompiler
from .mixins.gnu import GnuCompiler
from .mixins.clang import ClangCompiler

import subprocess
import platform
import re
import shutil
import tempfile
import os
import typing as T

if T.TYPE_CHECKING:
    from ..environment import Environment
    from ..programs import ExternalProgram


# Default compilers and linkers
# =============================

defaults: T.Dict[str, T.List[str]] = {}

# List of potential compilers.
if is_windows():
    # Intel C and C++ compiler is icl on Windows, but icc and icpc elsewhere.
    # Search for icl before cl, since Intel "helpfully" provides a
    # cl.exe that returns *exactly the same thing* that microsofts
    # cl.exe does, and if icl is present, it's almost certainly what
    # you want.
    defaults['c'] = ['icl', 'cl', 'cc', 'gcc', 'clang', 'clang-cl', 'pgcc']
    # There is currently no pgc++ for Windows, only for  Mac and Linux.
    defaults['cpp'] = ['icl', 'cl', 'c++', 'g++', 'clang++', 'clang-cl']
    defaults['fortran'] = ['ifort', 'gfortran', 'flang', 'pgfortran', 'g95']
    # Clang and clang++ are valid, but currently unsupported.
    defaults['objc'] = ['cc', 'gcc']
    defaults['objcpp'] = ['c++', 'g++']
    defaults['cs'] = ['csc', 'mcs']
else:
    if platform.machine().lower() == 'e2k':
        defaults['c'] = ['cc', 'gcc', 'lcc', 'clang']
        defaults['cpp'] = ['c++', 'g++', 'l++', 'clang++']
        defaults['objc'] = ['clang']
        defaults['objcpp'] = ['clang++']
    else:
        defaults['c'] = ['cc', 'gcc', 'clang', 'nvc', 'pgcc', 'icc']
        defaults['cpp'] = ['c++', 'g++', 'clang++', 'nvc++', 'pgc++', 'icpc']
        defaults['objc'] = ['cc', 'gcc', 'clang']
        defaults['objcpp'] = ['c++', 'g++', 'clang++']
    defaults['fortran'] = ['gfortran', 'flang', 'nvfortran', 'pgfortran', 'ifort', 'g95']
    defaults['cs'] = ['mcs', 'csc']
defaults['d'] = ['ldc2', 'ldc', 'gdc', 'dmd']
defaults['java'] = ['javac']
defaults['cuda'] = ['nvcc']
defaults['rust'] = ['rustc']
defaults['swift'] = ['swiftc']
defaults['vala'] = ['valac']
defaults['cython'] = ['cython', 'cython3'] # Official name is cython, but Debian renamed it to cython3.
defaults['static_linker'] = ['ar', 'gar']
defaults['strip'] = ['strip']
defaults['vs_static_linker'] = ['lib']
defaults['clang_cl_static_linker'] = ['llvm-lib']
defaults['cuda_static_linker'] = ['nvlink']
defaults['gcc_static_linker'] = ['gcc-ar']
defaults['clang_static_linker'] = ['llvm-ar']


def compiler_from_language(env: 'Environment', lang: str, for_machine: MachineChoice) -> T.Optional[Compiler]:
    lang_map: T.Dict[str, T.Callable[['Environment', MachineChoice], Compiler]] = {
        'c': detect_c_compiler,
        'cpp': detect_cpp_compiler,
        'objc': detect_objc_compiler,
        'cuda': detect_cuda_compiler,
        'objcpp': detect_objcpp_compiler,
        'java': detect_java_compiler,
        'cs': detect_cs_compiler,
        'vala': detect_vala_compiler,
        'd': detect_d_compiler,
        'rust': detect_rust_compiler,
        'fortran': detect_fortran_compiler,
        'swift': detect_swift_compiler,
        'cython': detect_cython_compiler,
    }
    return lang_map[lang](env, for_machine) if lang in lang_map else None

def detect_compiler_for(env: 'Environment', lang: str, for_machine: MachineChoice) -> T.Optional[Compiler]:
    comp = compiler_from_language(env, lang, for_machine)
    if comp is not None:
        assert comp.for_machine == for_machine
        env.coredata.process_new_compiler(lang, comp, env)
    return comp


# Helpers
# =======

def _get_compilers(env: 'Environment', lang: str, for_machine: MachineChoice) -> T.Tuple[T.List[T.List[str]], T.List[str], T.Optional['ExternalProgram']]:
    '''
    The list of compilers is detected in the exact same way for
    C, C++, ObjC, ObjC++, Fortran, CS so consolidate it here.
    '''
    value = env.lookup_binary_entry(for_machine, lang)
    if value is not None:
        comp, ccache = BinaryTable.parse_entry(value)
        # Return value has to be a list of compiler 'choices'
        compilers = [comp]
    else:
        if not env.machines.matches_build_machine(for_machine):
            raise EnvironmentException(f'{lang!r} compiler binary not defined in cross or native file')
        compilers = [[x] for x in defaults[lang]]
        ccache = BinaryTable.detect_compiler_cache()

    if env.machines.matches_build_machine(for_machine):
        exe_wrap: T.Optional[ExternalProgram] = None
    else:
        exe_wrap = env.get_exe_wrapper()

    return compilers, ccache, exe_wrap

def _handle_exceptions(
        exceptions: T.Mapping[str, T.Union[Exception, str]],
        binaries: T.List[T.List[str]],
        bintype: str = 'compiler') -> T.NoReturn:
    errmsg = f'Unknown {bintype}(s): {binaries}'
    if exceptions:
        errmsg += '\nThe following exception(s) were encountered:'
        for c, e in exceptions.items():
            errmsg += f'\nRunning "{c}" gave "{e}"'
    raise EnvironmentException(errmsg)


# Linker specific
# ===============

def detect_static_linker(env: 'Environment', compiler: Compiler) -> StaticLinker:
    linker = env.lookup_binary_entry(compiler.for_machine, 'ar')
    if linker is not None:
        linkers = [linker]
    else:
        default_linkers = [[l] for l in defaults['static_linker']]
        if isinstance(compiler, CudaCompiler):
            linkers = [defaults['cuda_static_linker']] + default_linkers
        elif isinstance(compiler, VisualStudioLikeCompiler):
            linkers = [defaults['vs_static_linker'], defaults['clang_cl_static_linker']]
        elif isinstance(compiler, GnuCompiler):
            # Use gcc-ar if available; needed for LTO
            linkers = [defaults['gcc_static_linker']] + default_linkers
        elif isinstance(compiler, ClangCompiler):
            # Use llvm-ar if available; needed for LTO
            linkers = [defaults['clang_static_linker']] + default_linkers
        elif isinstance(compiler, DCompiler):
            # Prefer static linkers over linkers used by D compilers
            if is_windows():
                linkers = [defaults['vs_static_linker'], defaults['clang_cl_static_linker'], compiler.get_linker_exelist()]
            else:
                linkers = default_linkers
        elif isinstance(compiler, IntelClCCompiler):
            # Intel has it's own linker that acts like microsoft's lib
            linkers = [['xilib']]
        elif isinstance(compiler, (PGICCompiler, PGIFortranCompiler)) and is_windows():
            linkers = [['ar']]  # For PGI on Windows, "ar" is just a wrapper calling link/lib.
        else:
            linkers = default_linkers
    popen_exceptions = {}
    for linker in linkers:
        linker_name = os.path.basename(linker[0])

        if any(os.path.basename(x) in {'lib', 'lib.exe', 'llvm-lib', 'llvm-lib.exe', 'xilib', 'xilib.exe'} for x in linker):
            arg = '/?'
        elif linker_name in {'ar2000', 'ar2000.exe', 'ar430', 'ar430.exe', 'armar', 'armar.exe'}:
            arg = '?'
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
        if 'ar-Error-Unknown switch: --version' in err:
            return PGIStaticLinker(linker)
        if p.returncode == 0 and 'armar' in linker_name:
            return ArmarLinker(linker)
        if 'DMD32 D Compiler' in out or 'DMD64 D Compiler' in out:
            assert isinstance(compiler, DCompiler)
            return DLinker(linker, compiler.arch)
        if 'LDC - the LLVM D compiler' in out:
            assert isinstance(compiler, DCompiler)
            return DLinker(linker, compiler.arch, rsp_syntax=compiler.rsp_file_syntax())
        if 'GDC' in out and ' based on D ' in out:
            assert isinstance(compiler, DCompiler)
            return DLinker(linker, compiler.arch)
        if err.startswith('Renesas') and 'rlink' in linker_name:
            return CcrxLinker(linker)
        if out.startswith('GNU ar') and 'xc16-ar' in linker_name:
            return Xc16Linker(linker)
        if 'Texas Instruments Incorporated' in out:
            if 'ar2000' in linker_name:
                return C2000Linker(linker)
            else:
                return TILinker(linker)
        if out.startswith('The CompCert'):
            return CompCertLinker(linker)
        if p.returncode == 0:
            return ArLinker(linker)
        if p.returncode == 1 and err.startswith('usage'): # OSX
            return ArLinker(linker)
        if p.returncode == 1 and err.startswith('Usage'): # AIX
            return AIXArLinker(linker)
        if p.returncode == 1 and err.startswith('ar: bad option: --'): # Solaris
            return ArLinker(linker)
    _handle_exceptions(popen_exceptions, linkers, 'linker')


# Compilers
# =========


def _detect_c_or_cpp_compiler(env: 'Environment', lang: str, for_machine: MachineChoice, *, override_compiler: T.Optional[T.List[str]] = None) -> Compiler:
    """Shared implementation for finding the C or C++ compiler to use.

    the override_compiler option is provided to allow compilers which use
    the compiler (GCC or Clang usually) as their shared linker, to find
    the linker they need.
    """
    popen_exceptions: T.Dict[str, T.Union[Exception, str]] = {}
    compilers, ccache, exe_wrap = _get_compilers(env, lang, for_machine)
    if override_compiler is not None:
        compilers = [override_compiler]
    is_cross = env.is_cross_build(for_machine)
    info = env.machines[for_machine]
    cls: T.Union[T.Type[CCompiler], T.Type[CPPCompiler]]

    for compiler in compilers:
        if isinstance(compiler, str):
            compiler = [compiler]
        compiler_name = os.path.basename(compiler[0])

        if any(os.path.basename(x) in {'cl', 'cl.exe', 'clang-cl', 'clang-cl.exe'} for x in compiler):
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
                def sanitize(p: str) -> str:
                    return os.path.normcase(os.path.abspath(p))

                watcom_cls = [sanitize(os.path.join(os.environ['WATCOM'], 'BINNT', 'cl')),
                              sanitize(os.path.join(os.environ['WATCOM'], 'BINNT', 'cl.exe')),
                              sanitize(os.path.join(os.environ['WATCOM'], 'BINNT64', 'cl')),
                              sanitize(os.path.join(os.environ['WATCOM'], 'BINNT64', 'cl.exe'))]
                found_cl = sanitize(shutil.which('cl'))
                if found_cl in watcom_cls:
                    mlog.debug('Skipping unsupported cl.exe clone at:', found_cl)
                    continue
            arg = '/?'
        elif 'armcc' in compiler_name:
            arg = '--vsn'
        elif 'ccrx' in compiler_name:
            arg = '-v'
        elif 'xc16' in compiler_name:
            arg = '--version'
        elif 'ccomp' in compiler_name:
            arg = '-version'
        elif compiler_name in {'cl2000', 'cl2000.exe', 'cl430', 'cl430.exe', 'armcl', 'armcl.exe'}:
            # TI compiler
            arg = '-version'
        elif compiler_name in {'icl', 'icl.exe'}:
            # if you pass anything to icl you get stuck in a pager
            arg = ''
        else:
            arg = '--version'

        try:
            p, out, err = Popen_safe(compiler + [arg])
        except OSError as e:
            popen_exceptions[' '.join(compiler + [arg])] = e
            continue

        if 'ccrx' in compiler_name:
            out = err

        full_version = out.split('\n', 1)[0]
        version = search_version(out)

        guess_gcc_or_lcc: T.Optional[str] = None
        if 'Free Software Foundation' in out or 'xt-' in out:
            guess_gcc_or_lcc = 'gcc'
        if 'e2k' in out and 'lcc' in out:
            guess_gcc_or_lcc = 'lcc'
        if 'Microchip Technology' in out:
            # this output has "Free Software Foundation" in its version
            guess_gcc_or_lcc = None

        if guess_gcc_or_lcc:
            defines = _get_gnu_compiler_defines(compiler)
            if not defines:
                popen_exceptions[' '.join(compiler)] = 'no pre-processor defines'
                continue

            if guess_gcc_or_lcc == 'lcc':
                version = _get_lcc_version_from_defines(defines)
                cls = ElbrusCCompiler if lang == 'c' else ElbrusCPPCompiler
            else:
                version = _get_gnu_version_from_defines(defines)
                cls = GnuCCompiler if lang == 'c' else GnuCPPCompiler

            linker = guess_nix_linker(env, compiler, cls, for_machine)

            return cls(
                ccache + compiler, version, for_machine, is_cross,
                info, exe_wrap, defines=defines, full_version=full_version,
                linker=linker)

        if 'Emscripten' in out:
            cls = EmscriptenCCompiler if lang == 'c' else EmscriptenCPPCompiler
            env.coredata.add_lang_args(cls.language, cls, for_machine, env)

            # emcc requires a file input in order to pass arguments to the
            # linker. It'll exit with an error code, but still print the
            # linker version. Old emcc versions ignore -Wl,--version completely,
            # however. We'll report "unknown version" in that case.
            with tempfile.NamedTemporaryFile(suffix='.c') as f:
                cmd = compiler + [cls.LINKER_PREFIX + "--version", f.name]
                _, o, _ = Popen_safe(cmd)

            linker = WASMDynamicLinker(
                compiler, for_machine, cls.LINKER_PREFIX,
                [], version=search_version(o))
            return cls(
                ccache + compiler, version, for_machine, is_cross, info,
                exe_wrap, linker=linker, full_version=full_version)

        if 'Arm C/C++/Fortran Compiler' in out:
            arm_ver_match = re.search(r'version (\d+)\.(\d+) \(build number (\d+)\)', out)
            arm_ver_major = arm_ver_match.group(1)
            arm_ver_minor = arm_ver_match.group(2)
            arm_ver_build = arm_ver_match.group(3)
            version = '.'.join([arm_ver_major, arm_ver_minor, arm_ver_build])
            if lang == 'c':
                cls = ArmLtdClangCCompiler
            elif lang == 'cpp':
                cls = ArmLtdClangCPPCompiler
            linker = guess_nix_linker(env, compiler, cls, for_machine)
            return cls(
                ccache + compiler, version, for_machine, is_cross, info,
                exe_wrap, linker=linker)
        if 'armclang' in out:
            # The compiler version is not present in the first line of output,
            # instead it is present in second line, startswith 'Component:'.
            # So, searching for the 'Component' in out although we know it is
            # present in second line, as we are not sure about the
            # output format in future versions
            arm_ver_match = re.search('.*Component.*', out)
            if arm_ver_match is None:
                popen_exceptions[' '.join(compiler)] = 'version string not found'
                continue
            arm_ver_str = arm_ver_match.group(0)
            # Override previous values
            version = search_version(arm_ver_str)
            full_version = arm_ver_str
            cls = ArmclangCCompiler if lang == 'c' else ArmclangCPPCompiler
            linker = ArmClangDynamicLinker(for_machine, version=version)
            env.coredata.add_lang_args(cls.language, cls, for_machine, env)
            return cls(
                ccache + compiler, version, for_machine, is_cross, info,
                exe_wrap, full_version=full_version, linker=linker)
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
            linker = guess_win_linker(env, ['lld-link'], cls, for_machine)
            return cls(
                compiler, version, for_machine, is_cross, info, target,
                exe_wrap, linker=linker)
        if 'clang' in out or 'Clang' in out:
            linker = None

            defines = _get_clang_compiler_defines(compiler)

            # Even if the for_machine is darwin, we could be using vanilla
            # clang.
            if 'Apple' in out:
                cls = AppleClangCCompiler if lang == 'c' else AppleClangCPPCompiler
            else:
                cls = ClangCCompiler if lang == 'c' else ClangCPPCompiler

            if 'windows' in out or env.machines[for_machine].is_windows():
                # If we're in a MINGW context this actually will use a gnu
                # style ld, but for clang on "real" windows we'll use
                # either link.exe or lld-link.exe
                try:
                    linker = guess_win_linker(env, compiler, cls, for_machine, invoked_directly=False)
                except MesonException:
                    pass
            if linker is None:
                linker = guess_nix_linker(env, compiler, cls, for_machine)

            return cls(
                ccache + compiler, version, for_machine, is_cross, info,
                exe_wrap, defines=defines, full_version=full_version, linker=linker)

        if 'Intel(R) C++ Intel(R)' in err:
            version = search_version(err)
            target = 'x86' if 'IA-32' in err else 'x86_64'
            cls = IntelClCCompiler if lang == 'c' else IntelClCPPCompiler
            env.coredata.add_lang_args(cls.language, cls, for_machine, env)
            linker = XilinkDynamicLinker(for_machine, [], version=version)
            return cls(
                compiler, version, for_machine, is_cross, info, target,
                exe_wrap, linker=linker)
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
                raise EnvironmentException(f'Failed to detect MSVC compiler version: stderr was\n{err!r}')
            cl_signature = lookat.split('\n')[0]
            match = re.search(r'.*(x86|x64|ARM|ARM64)([^_A-Za-z0-9]|$)', cl_signature)
            if match:
                target = match.group(1)
            else:
                m = f'Failed to detect MSVC compiler target architecture: \'cl /?\' output is\n{cl_signature}'
                raise EnvironmentException(m)
            cls = VisualStudioCCompiler if lang == 'c' else VisualStudioCPPCompiler
            linker = guess_win_linker(env, ['link'], cls, for_machine)
            # As of this writing, CCache does not support MSVC but sccache does.
            if 'sccache' in ccache:
                final_compiler = ccache + compiler
            else:
                final_compiler = compiler
            return cls(
                final_compiler, version, for_machine, is_cross, info, target,
                exe_wrap, full_version=cl_signature, linker=linker)
        if 'PGI Compilers' in out:
            cls = PGICCompiler if lang == 'c' else PGICPPCompiler
            env.coredata.add_lang_args(cls.language, cls, for_machine, env)
            linker = PGIDynamicLinker(compiler, for_machine, cls.LINKER_PREFIX, [], version=version)
            return cls(
                ccache + compiler, version, for_machine, is_cross,
                info, exe_wrap, linker=linker)
        if 'NVIDIA Compilers and Tools' in out:
            cls = NvidiaHPC_CCompiler if lang == 'c' else NvidiaHPC_CPPCompiler
            env.coredata.add_lang_args(cls.language, cls, for_machine, env)
            linker = NvidiaHPC_DynamicLinker(compiler, for_machine, cls.LINKER_PREFIX, [], version=version)
            return cls(
                ccache + compiler, version, for_machine, is_cross,
                info, exe_wrap, linker=linker)
        if '(ICC)' in out:
            cls = IntelCCompiler if lang == 'c' else IntelCPPCompiler
            l = guess_nix_linker(env, compiler, cls, for_machine)
            return cls(
                ccache + compiler, version, for_machine, is_cross, info,
                exe_wrap, full_version=full_version, linker=l)
        if 'TMS320C2000 C/C++' in out or 'MSP430 C/C++' in out or 'TI ARM C/C++ Compiler' in out:
            lnk: T.Union[T.Type[C2000DynamicLinker], T.Type[TIDynamicLinker]]
            if 'TMS320C2000 C/C++' in out:
                cls = C2000CCompiler if lang == 'c' else C2000CPPCompiler
                lnk = C2000DynamicLinker
            else:
                cls = TICCompiler if lang == 'c' else TICPPCompiler
                lnk = TIDynamicLinker

            env.coredata.add_lang_args(cls.language, cls, for_machine, env)
            linker = lnk(compiler, for_machine, version=version)
            return cls(
                ccache + compiler, version, for_machine, is_cross, info,
                exe_wrap, full_version=full_version, linker=linker)
        if 'ARM' in out:
            cls = ArmCCompiler if lang == 'c' else ArmCPPCompiler
            env.coredata.add_lang_args(cls.language, cls, for_machine, env)
            linker = ArmDynamicLinker(for_machine, version=version)
            return cls(
                ccache + compiler, version, for_machine, is_cross,
                info, exe_wrap, full_version=full_version, linker=linker)
        if 'RX Family' in out:
            cls = CcrxCCompiler if lang == 'c' else CcrxCPPCompiler
            env.coredata.add_lang_args(cls.language, cls, for_machine, env)
            linker = CcrxDynamicLinker(for_machine, version=version)
            return cls(
                ccache + compiler, version, for_machine, is_cross, info,
                exe_wrap, full_version=full_version, linker=linker)

        if 'Microchip Technology' in out:
            cls = Xc16CCompiler if lang == 'c' else Xc16CCompiler
            env.coredata.add_lang_args(cls.language, cls, for_machine, env)
            linker = Xc16DynamicLinker(for_machine, version=version)
            return cls(
                ccache + compiler, version, for_machine, is_cross, info,
                exe_wrap, full_version=full_version, linker=linker)

        if 'CompCert' in out:
            cls = CompCertCCompiler
            env.coredata.add_lang_args(cls.language, cls, for_machine, env)
            linker = CompCertDynamicLinker(for_machine, version=version)
            return cls(
                ccache + compiler, version, for_machine, is_cross, info,
                exe_wrap, full_version=full_version, linker=linker)

    _handle_exceptions(popen_exceptions, compilers)
    raise EnvironmentException(f'Unknown compiler {compilers}')

def detect_c_compiler(env: 'Environment', for_machine: MachineChoice) -> Compiler:
    return _detect_c_or_cpp_compiler(env, 'c', for_machine)

def detect_cpp_compiler(env: 'Environment', for_machine: MachineChoice) -> Compiler:
    return _detect_c_or_cpp_compiler(env, 'cpp', for_machine)

def detect_cuda_compiler(env: 'Environment', for_machine: MachineChoice) -> Compiler:
    popen_exceptions = {}
    is_cross = env.is_cross_build(for_machine)
    compilers, ccache, exe_wrap = _get_compilers(env, 'cuda', for_machine)
    info = env.machines[for_machine]
    for compiler in compilers:
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
        cpp_compiler = detect_cpp_compiler(env, for_machine)
        cls = CudaCompiler
        env.coredata.add_lang_args(cls.language, cls, for_machine, env)
        linker = CudaLinker(compiler, for_machine, CudaCompiler.LINKER_PREFIX, [], version=CudaLinker.parse_version())
        return cls(ccache + compiler, version, for_machine, is_cross, exe_wrap, host_compiler=cpp_compiler, info=info, linker=linker)
    raise EnvironmentException(f'Could not find suitable CUDA compiler: "{"; ".join([" ".join(c) for c in compilers])}"')

def detect_fortran_compiler(env: 'Environment', for_machine: MachineChoice) -> Compiler:
    popen_exceptions: T.Dict[str, T.Union[Exception, str]] = {}
    compilers, ccache, exe_wrap = _get_compilers(env, 'fortran', for_machine)
    is_cross = env.is_cross_build(for_machine)
    info = env.machines[for_machine]
    cls: T.Type[FortranCompiler]
    for compiler in compilers:
        for arg in ['--version', '-V']:
            try:
                p, out, err = Popen_safe(compiler + [arg])
            except OSError as e:
                popen_exceptions[' '.join(compiler + [arg])] = e
                continue

            version = search_version(out)
            full_version = out.split('\n', 1)[0]

            guess_gcc_or_lcc: T.Optional[str] = None
            if 'GNU Fortran' in out:
                guess_gcc_or_lcc = 'gcc'
            if 'e2k' in out and 'lcc' in out:
                guess_gcc_or_lcc = 'lcc'

            if guess_gcc_or_lcc:
                defines = _get_gnu_compiler_defines(compiler)
                if not defines:
                    popen_exceptions[' '.join(compiler)] = 'no pre-processor defines'
                    continue
                if guess_gcc_or_lcc == 'lcc':
                    version = _get_lcc_version_from_defines(defines)
                    cls = ElbrusFortranCompiler
                    linker = guess_nix_linker(env, compiler, cls, for_machine)
                    return cls(
                        compiler, version, for_machine, is_cross, info,
                        exe_wrap, defines, full_version=full_version, linker=linker)
                else:
                    version = _get_gnu_version_from_defines(defines)
                    cls = GnuFortranCompiler
                    linker = guess_nix_linker(env, compiler, cls, for_machine)
                    return cls(
                        compiler, version, for_machine, is_cross, info,
                        exe_wrap, defines, full_version=full_version, linker=linker)

            if 'Arm C/C++/Fortran Compiler' in out:
                cls = ArmLtdFlangFortranCompiler
                arm_ver_match = re.search(r'version (\d+)\.(\d+) \(build number (\d+)\)', out)
                arm_ver_major = arm_ver_match.group(1)
                arm_ver_minor = arm_ver_match.group(2)
                arm_ver_build = arm_ver_match.group(3)
                version = '.'.join([arm_ver_major, arm_ver_minor, arm_ver_build])
                linker = guess_nix_linker(env, compiler, cls, for_machine)
                return cls(
                    ccache + compiler, version, for_machine, is_cross, info,
                    exe_wrap, linker=linker)
            if 'G95' in out:
                cls = G95FortranCompiler
                linker = guess_nix_linker(env, compiler, cls, for_machine)
                return G95FortranCompiler(
                    compiler, version, for_machine, is_cross, info,
                    exe_wrap, full_version=full_version, linker=linker)

            if 'Sun Fortran' in err:
                version = search_version(err)
                cls = SunFortranCompiler
                linker = guess_nix_linker(env, compiler, cls, for_machine)
                return SunFortranCompiler(
                    compiler, version, for_machine, is_cross, info,
                    exe_wrap, full_version=full_version, linker=linker)

            if 'Intel(R) Visual Fortran' in err or 'Intel(R) Fortran' in err:
                version = search_version(err)
                target = 'x86' if 'IA-32' in err else 'x86_64'
                cls = IntelClFortranCompiler
                env.coredata.add_lang_args(cls.language, cls, for_machine, env)
                linker = XilinkDynamicLinker(for_machine, [], version=version)
                return cls(
                    compiler, version, for_machine, is_cross, info,
                    target, exe_wrap, linker=linker)

            if 'ifort (IFORT)' in out:
                linker = guess_nix_linker(env, compiler, IntelFortranCompiler, for_machine)
                return IntelFortranCompiler(
                    compiler, version, for_machine, is_cross, info,
                    exe_wrap, full_version=full_version, linker=linker)

            if 'PathScale EKOPath(tm)' in err:
                return PathScaleFortranCompiler(
                    compiler, version, for_machine, is_cross, info,
                    exe_wrap, full_version=full_version)

            if 'PGI Compilers' in out:
                cls = PGIFortranCompiler
                env.coredata.add_lang_args(cls.language, cls, for_machine, env)
                linker = PGIDynamicLinker(compiler, for_machine,
                                          cls.LINKER_PREFIX, [], version=version)
                return cls(
                    compiler, version, for_machine, is_cross, info, exe_wrap,
                    full_version=full_version, linker=linker)

            if 'NVIDIA Compilers and Tools' in out:
                cls = NvidiaHPC_FortranCompiler
                env.coredata.add_lang_args(cls.language, cls, for_machine, env)
                linker = PGIDynamicLinker(compiler, for_machine,
                                          cls.LINKER_PREFIX, [], version=version)
                return cls(
                    compiler, version, for_machine, is_cross, info, exe_wrap,
                    full_version=full_version, linker=linker)

            if 'flang' in out or 'clang' in out:
                linker = guess_nix_linker(env,
                                          compiler, FlangFortranCompiler, for_machine)
                return FlangFortranCompiler(
                    compiler, version, for_machine, is_cross, info,
                    exe_wrap, full_version=full_version, linker=linker)

            if 'Open64 Compiler Suite' in err:
                linker = guess_nix_linker(env,
                                          compiler, Open64FortranCompiler, for_machine)
                return Open64FortranCompiler(
                    compiler, version, for_machine, is_cross, info,
                    exe_wrap, full_version=full_version, linker=linker)

            if 'NAG Fortran' in err:
                full_version = err.split('\n', 1)[0]
                version = full_version.split()[-1]
                cls = NAGFortranCompiler
                env.coredata.add_lang_args(cls.language, cls, for_machine, env)
                linker = NAGDynamicLinker(
                    compiler, for_machine, cls.LINKER_PREFIX, [],
                    version=version)
                return cls(
                    compiler, version, for_machine, is_cross, info,
                    exe_wrap, full_version=full_version, linker=linker)

    _handle_exceptions(popen_exceptions, compilers)
    raise EnvironmentException('Unreachable code (exception to make mypy happy)')

def detect_objc_compiler(env: 'Environment', for_machine: MachineChoice) -> 'Compiler':
    return _detect_objc_or_objcpp_compiler(env, for_machine, True)

def detect_objcpp_compiler(env: 'Environment', for_machine: MachineChoice) -> 'Compiler':
    return _detect_objc_or_objcpp_compiler(env, for_machine, False)

def _detect_objc_or_objcpp_compiler(env: 'Environment', for_machine: MachineChoice, objc: bool) -> 'Compiler':
    popen_exceptions: T.Dict[str, T.Union[Exception, str]] = {}
    compilers, ccache, exe_wrap = _get_compilers(env, 'objc' if objc else 'objcpp', for_machine)
    is_cross = env.is_cross_build(for_machine)
    info = env.machines[for_machine]
    comp: T.Union[T.Type[ObjCCompiler], T.Type[ObjCPPCompiler]]

    for compiler in compilers:
        arg = ['--version']
        try:
            p, out, err = Popen_safe(compiler + arg)
        except OSError as e:
            popen_exceptions[' '.join(compiler + arg)] = e
            continue
        version = search_version(out)
        if 'Free Software Foundation' in out:
            defines = _get_gnu_compiler_defines(compiler)
            if not defines:
                popen_exceptions[' '.join(compiler)] = 'no pre-processor defines'
                continue
            version = _get_gnu_version_from_defines(defines)
            comp = GnuObjCCompiler if objc else GnuObjCPPCompiler
            linker = guess_nix_linker(env, compiler, comp, for_machine)
            return comp(
                ccache + compiler, version, for_machine, is_cross, info,
                exe_wrap, defines, linker=linker)
        if 'clang' in out:
            linker = None
            defines = _get_clang_compiler_defines(compiler)
            if not defines:
                popen_exceptions[' '.join(compiler)] = 'no pre-processor defines'
                continue
            if 'Apple' in out:
                comp = AppleClangObjCCompiler if objc else AppleClangObjCPPCompiler
            else:
                comp = ClangObjCCompiler if objc else ClangObjCPPCompiler
            if 'windows' in out or env.machines[for_machine].is_windows():
                # If we're in a MINGW context this actually will use a gnu style ld
                try:
                    linker = guess_win_linker(env, compiler, comp, for_machine)
                except MesonException:
                    pass

            if not linker:
                linker = guess_nix_linker(env, compiler, comp, for_machine)
            return comp(
                ccache + compiler, version, for_machine,
                is_cross, info, exe_wrap, linker=linker, defines=defines)
    _handle_exceptions(popen_exceptions, compilers)
    raise EnvironmentException('Unreachable code (exception to make mypy happy)')

def detect_java_compiler(env: 'Environment', for_machine: MachineChoice) -> Compiler:
    exelist = env.lookup_binary_entry(for_machine, 'java')
    info = env.machines[for_machine]
    if exelist is None:
        # TODO support fallback
        exelist = [defaults['java'][0]]

    try:
        p, out, err = Popen_safe(exelist + ['-version'])
    except OSError:
        raise EnvironmentException('Could not execute Java compiler "{}"'.format(' '.join(exelist)))
    if 'javac' in out or 'javac' in err:
        version = search_version(err if 'javac' in err else out)
        if not version or version == 'unknown version':
            parts = (err if 'javac' in err else out).split()
            if len(parts) > 1:
                version = parts[1]
        comp_class = JavaCompiler
        env.coredata.add_lang_args(comp_class.language, comp_class, for_machine, env)
        return comp_class(exelist, version, for_machine, info)
    raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

def detect_cs_compiler(env: 'Environment', for_machine: MachineChoice) -> Compiler:
    compilers, ccache, exe_wrap = _get_compilers(env, 'cs', for_machine)
    popen_exceptions = {}
    info = env.machines[for_machine]
    for comp in compilers:
        try:
            p, out, err = Popen_safe(comp + ['--version'])
        except OSError as e:
            popen_exceptions[' '.join(comp + ['--version'])] = e
            continue

        version = search_version(out)
        cls: T.Union[T.Type[MonoCompiler], T.Type[VisualStudioCsCompiler]]
        if 'Mono' in out:
            cls = MonoCompiler
        elif "Visual C#" in out:
            cls = VisualStudioCsCompiler
        else:
            continue
        env.coredata.add_lang_args(cls.language, cls, for_machine, env)
        return cls(comp, version, for_machine, info)

    _handle_exceptions(popen_exceptions, compilers)
    raise EnvironmentException('Unreachable code (exception to make mypy happy)')

def detect_cython_compiler(env: 'Environment', for_machine: MachineChoice) -> Compiler:
    """Search for a cython compiler."""
    compilers, _, _ = _get_compilers(env, 'cython', for_machine)
    is_cross = env.is_cross_build(for_machine)
    info = env.machines[for_machine]

    popen_exceptions: T.Dict[str, Exception] = {}
    for comp in compilers:
        try:
            err = Popen_safe(comp + ['-V'])[2]
        except OSError as e:
            popen_exceptions[' '.join(comp + ['-V'])] = e
            continue

        version = search_version(err)
        if 'Cython' in err:
            comp_class = CythonCompiler
            env.coredata.add_lang_args(comp_class.language, comp_class, for_machine, env)
            return comp_class(comp, version, for_machine, info, is_cross=is_cross)
    _handle_exceptions(popen_exceptions, compilers)
    raise EnvironmentException('Unreachable code (exception to make mypy happy)')

def detect_vala_compiler(env: 'Environment', for_machine: MachineChoice) -> Compiler:
    exelist = env.lookup_binary_entry(for_machine, 'vala')
    is_cross = env.is_cross_build(for_machine)
    info = env.machines[for_machine]
    if exelist is None:
        # TODO support fallback
        exelist = [defaults['vala'][0]]

    try:
        p, out = Popen_safe(exelist + ['--version'])[0:2]
    except OSError:
        raise EnvironmentException('Could not execute Vala compiler "{}"'.format(' '.join(exelist)))
    version = search_version(out)
    if 'Vala' in out:
        comp_class = ValaCompiler
        env.coredata.add_lang_args(comp_class.language, comp_class, for_machine, env)
        return comp_class(exelist, version, for_machine, is_cross, info)
    raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

def detect_rust_compiler(env: 'Environment', for_machine: MachineChoice) -> RustCompiler:
    popen_exceptions = {}  # type: T.Dict[str, Exception]
    compilers, _, exe_wrap = _get_compilers(env, 'rust', for_machine)
    is_cross = env.is_cross_build(for_machine)
    info = env.machines[for_machine]

    cc = detect_c_compiler(env, for_machine)
    is_link_exe = isinstance(cc.linker, VisualStudioLikeLinkerMixin)
    override = env.lookup_binary_entry(for_machine, 'rust_ld')

    for compiler in compilers:
        arg = ['--version']
        try:
            out = Popen_safe(compiler + arg)[1]
        except OSError as e:
            popen_exceptions[' '.join(compiler + arg)] = e
            continue

        version = search_version(out)
        cls: T.Type[RustCompiler] = RustCompiler

        # Clippy is a wrapper around rustc, but it doesn't have rustc in it's
        # output. We can otherwise treat it as rustc.
        if 'clippy' in out:
            out = 'rustc'
            cls = ClippyRustCompiler

        if 'rustc' in out:
            # On Linux and mac rustc will invoke gcc (clang for mac
            # presumably) and it can do this windows, for dynamic linking.
            # this means the easiest way to C compiler for dynamic linking.
            # figure out what linker to use is to just get the value of the
            # C compiler and use that as the basis of the rust linker.
            # However, there are two things we need to change, if CC is not
            # the default use that, and second add the necessary arguments
            # to rust to use -fuse-ld

            if any(a.startswith('linker=') for a in compiler):
                mlog.warning(
                    'Please do not put -C linker= in your compiler '
                    'command, set rust_ld=command in your cross file '
                    'or use the RUST_LD environment variable, otherwise meson '
                    'will override your selection.')

            compiler = compiler.copy()  # avoid mutating the original list

            if override is None:
                extra_args: T.Dict[str, T.Union[str, bool]] = {}
                always_args: T.List[str] = []
                if is_link_exe:
                    compiler.extend(cls.use_linker_args(cc.linker.exelist[0]))
                    extra_args['direct'] = True
                    extra_args['machine'] = cc.linker.machine
                else:
                    exelist = cc.linker.exelist + cc.linker.get_always_args()
                    if 'ccache' in exelist[0]:
                        del exelist[0]
                    c = exelist.pop(0)
                    compiler.extend(cls.use_linker_args(c))

                    # Also ensure that we pass any extra arguments to the linker
                    for l in exelist:
                        compiler.extend(['-C', f'link-arg={l}'])

                # This trickery with type() gets us the class of the linker
                # so we can initialize a new copy for the Rust Compiler
                # TODO rewrite this without type: ignore
                if is_link_exe:
                    linker = type(cc.linker)(for_machine, always_args, exelist=cc.linker.exelist,   # type: ignore
                                             version=cc.linker.version, **extra_args)               # type: ignore
                else:
                    linker = type(cc.linker)(compiler, for_machine, cc.LINKER_PREFIX,
                                             always_args=always_args, version=cc.linker.version,
                                             **extra_args)
            elif 'link' in override[0]:
                linker = guess_win_linker(env,
                                          override, cls, for_machine, use_linker_prefix=False)
                # rustc takes linker arguments without a prefix, and
                # inserts the correct prefix itself.
                assert isinstance(linker, VisualStudioLikeLinkerMixin)
                linker.direct = True
                compiler.extend(cls.use_linker_args(linker.exelist[0]))
            else:
                # On linux and macos rust will invoke the c compiler for
                # linking, on windows it will use lld-link or link.exe.
                # we will simply ask for the C compiler that corresponds to
                # it, and use that.
                cc = _detect_c_or_cpp_compiler(env, 'c', for_machine, override_compiler=override)
                linker = cc.linker

                # Of course, we're not going to use any of that, we just
                # need it to get the proper arguments to pass to rustc
                c = linker.exelist[1] if linker.exelist[0].endswith('ccache') else linker.exelist[0]
                compiler.extend(cls.use_linker_args(c))

            env.coredata.add_lang_args(cls.language, cls, for_machine, env)
            return cls(
                compiler, version, for_machine, is_cross, info, exe_wrap,
                linker=linker)

    _handle_exceptions(popen_exceptions, compilers)
    raise EnvironmentException('Unreachable code (exception to make mypy happy)')

def detect_d_compiler(env: 'Environment', for_machine: MachineChoice) -> Compiler:
    info = env.machines[for_machine]

    # Detect the target architecture, required for proper architecture handling on Windows.
    # MSVC compiler is required for correct platform detection.
    c_compiler = {'c': detect_c_compiler(env, for_machine)}
    is_msvc = isinstance(c_compiler['c'], VisualStudioCCompiler)
    if not is_msvc:
        c_compiler = {}

    # Import here to avoid circular imports
    from ..environment import detect_cpu_family
    arch = detect_cpu_family(c_compiler)
    if is_msvc and arch == 'x86':
        arch = 'x86_mscoff'

    popen_exceptions = {}
    is_cross = env.is_cross_build(for_machine)
    compilers, ccache, exe_wrap = _get_compilers(env, 'd', for_machine)
    for exelist in compilers:
        # Search for a D compiler.
        # We prefer LDC over GDC unless overridden with the DC
        # environment variable because LDC has a much more
        # up to date language version at time (2016).
        if os.path.basename(exelist[-1]).startswith(('ldmd', 'gdmd')):
            raise EnvironmentException(
                f'Meson does not support {exelist[-1]} as it is only a DMD frontend for another compiler.'
                'Please provide a valid value for DC or unset it so that Meson can resolve the compiler by itself.')
        try:
            p, out = Popen_safe(exelist + ['--version'])[0:2]
        except OSError as e:
            popen_exceptions[' '.join(exelist + ['--version'])] = e
            continue
        version = search_version(out)
        full_version = out.split('\n', 1)[0]

        if 'LLVM D compiler' in out:
            # LDC seems to require a file
            # We cannot use NamedTemproraryFile on windows, its documented
            # to not work for our uses. So, just use mkstemp and only have
            # one path for simplicity.
            o, f = tempfile.mkstemp('.d')
            os.close(o)

            try:
                if info.is_windows() or info.is_cygwin():
                    objfile = os.path.basename(f)[:-1] + 'obj'
                    linker = guess_win_linker(env,
                                              exelist,
                                              LLVMDCompiler, for_machine,
                                              use_linker_prefix=True, invoked_directly=False,
                                              extra_args=[f])
                else:
                    # LDC writes an object file to the current working directory.
                    # Clean it up.
                    objfile = os.path.basename(f)[:-1] + 'o'
                    linker = guess_nix_linker(env,
                                              exelist, LLVMDCompiler, for_machine,
                                              extra_args=[f])
            finally:
                windows_proof_rm(f)
                windows_proof_rm(objfile)

            return LLVMDCompiler(
                exelist, version, for_machine, info, arch,
                full_version=full_version, linker=linker, version_output=out)
        elif 'gdc' in out:
            linker = guess_nix_linker(env, exelist, GnuDCompiler, for_machine)
            return GnuDCompiler(
                exelist, version, for_machine, info, arch,
                exe_wrapper=exe_wrap, is_cross=is_cross,
                full_version=full_version, linker=linker)
        elif 'The D Language Foundation' in out or 'Digital Mars' in out:
            # DMD seems to require a file
            # We cannot use NamedTemproraryFile on windows, its documented
            # to not work for our uses. So, just use mkstemp and only have
            # one path for simplicity.
            o, f = tempfile.mkstemp('.d')
            os.close(o)

            # DMD as different detection logic for x86 and x86_64
            arch_arg = '-m64' if arch == 'x86_64' else '-m32'

            try:
                if info.is_windows() or info.is_cygwin():
                    objfile = os.path.basename(f)[:-1] + 'obj'
                    linker = guess_win_linker(env,
                                              exelist, DmdDCompiler, for_machine,
                                              invoked_directly=False, extra_args=[f, arch_arg])
                else:
                    objfile = os.path.basename(f)[:-1] + 'o'
                    linker = guess_nix_linker(env,
                                              exelist, DmdDCompiler, for_machine,
                                              extra_args=[f, arch_arg])
            finally:
                windows_proof_rm(f)
                windows_proof_rm(objfile)

            return DmdDCompiler(
                exelist, version, for_machine, info, arch,
                full_version=full_version, linker=linker)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    _handle_exceptions(popen_exceptions, compilers)
    raise EnvironmentException('Unreachable code (exception to make mypy happy)')

def detect_swift_compiler(env: 'Environment', for_machine: MachineChoice) -> Compiler:
    exelist = env.lookup_binary_entry(for_machine, 'swift')
    is_cross = env.is_cross_build(for_machine)
    info = env.machines[for_machine]
    if exelist is None:
        # TODO support fallback
        exelist = [defaults['swift'][0]]

    try:
        p, _, err = Popen_safe(exelist + ['-v'])
    except OSError:
        raise EnvironmentException('Could not execute Swift compiler "{}"'.format(' '.join(exelist)))
    version = search_version(err)
    if 'Swift' in err:
        # As for 5.0.1 swiftc *requires* a file to check the linker:
        with tempfile.NamedTemporaryFile(suffix='.swift') as f:
            linker = guess_nix_linker(env,
                                      exelist, SwiftCompiler, for_machine,
                                      extra_args=[f.name])
        return SwiftCompiler(
            exelist, version, for_machine, is_cross, info, linker=linker)

    raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')


# GNU/Clang defines and version
# =============================

def _get_gnu_compiler_defines(compiler: T.List[str]) -> T.Dict[str, str]:
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
    defines: T.Dict[str, str] = {}
    for line in output.split('\n'):
        if not line:
            continue
        d, *rest = line.split(' ', 2)
        if d != '#define':
            continue
        if len(rest) == 1:
            defines[rest[0]] = ''
        if len(rest) == 2:
            defines[rest[0]] = rest[1]
    return defines

def _get_clang_compiler_defines(compiler: T.List[str]) -> T.Dict[str, str]:
    """
    Get the list of Clang pre-processor defines
    """
    args = compiler + ['-E', '-dM', '-']
    p, output, error = Popen_safe(args, write='', stdin=subprocess.PIPE)
    if p.returncode != 0:
        raise EnvironmentException('Unable to get clang pre-processor defines:\n' + output + error)
    defines: T.Dict[str, str] = {}
    for line in output.split('\n'):
        if not line:
            continue
        d, *rest = line.split(' ', 2)
        if d != '#define':
            continue
        if len(rest) == 1:
            defines[rest[0]] = ''
        if len(rest) == 2:
            defines[rest[0]] = rest[1]
    return defines

def _get_gnu_version_from_defines(defines: T.Dict[str, str]) -> str:
    dot = '.'
    major = defines.get('__GNUC__', '0')
    minor = defines.get('__GNUC_MINOR__', '0')
    patch = defines.get('__GNUC_PATCHLEVEL__', '0')
    return dot.join((major, minor, patch))

def _get_lcc_version_from_defines(defines: T.Dict[str, str]) -> str:
    dot = '.'
    generation_and_major = defines.get('__LCC__', '100')
    generation = generation_and_major[:1]
    major = generation_and_major[1:]
    minor = defines.get('__LCC_MINOR__', '0')
    return dot.join((generation, major, minor))
