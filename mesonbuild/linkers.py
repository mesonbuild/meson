# Copyright 2012-2019 The Meson development team

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
import shlex
from typing import List, TYPE_CHECKING, Optional

from . import mesonlib
from . import mlog

if TYPE_CHECKING:
    from .compilers import compilers


class StaticLinker:
    def can_linker_accept_rsp(self):
        """
        Determines whether the linker can accept arguments using the @rsp syntax.
        """
        return mesonlib.is_windows()

    def get_base_link_args(self, options):
        """Like compilers.get_base_link_args, but for the static linker."""
        return []


class VisualStudioLinker(StaticLinker):
    always_args = ['/NOLOGO']

    def __init__(self, exelist, machine):
        self.exelist = exelist
        self.machine = machine

    def get_exelist(self):
        return self.exelist[:]

    def get_std_link_args(self):
        return []

    def get_buildtype_linker_args(self, buildtype):
        return []

    def get_output_args(self, target):
        args = []
        if self.machine:
            args += ['/MACHINE:' + self.machine]
        args += ['/OUT:' + target]
        return args

    def get_coverage_link_args(self):
        return []

    def get_always_args(self):
        return VisualStudioLinker.always_args[:]

    def get_linker_always_args(self):
        return VisualStudioLinker.always_args[:]

    def build_rpath_args(self, build_dir, from_dir, rpath_paths, build_rpath, install_rpath):
        return []

    def thread_link_flags(self, env):
        return []

    def openmp_flags(self):
        return []

    def get_option_link_args(self, options):
        return []

    @classmethod
    def unix_args_to_native(cls, args):
        from .compilers import VisualStudioCCompiler
        return VisualStudioCCompiler.unix_args_to_native(args)

    def get_link_debugfile_args(self, targetfile):
        # Static libraries do not have PDB files
        return []


class ArLinker(StaticLinker):

    def __init__(self, exelist):
        self.exelist = exelist
        self.id = 'ar'
        pc, stdo = mesonlib.Popen_safe(self.exelist + ['-h'])[0:2]
        # Enable deterministic builds if they are available.
        if '[D]' in stdo:
            self.std_args = ['csrD']
        else:
            self.std_args = ['csr']

    def can_linker_accept_rsp(self):
        return mesonlib.is_windows()

    def build_rpath_args(self, build_dir, from_dir, rpath_paths, build_rpath, install_rpath):
        return []

    def get_exelist(self):
        return self.exelist[:]

    def get_std_link_args(self):
        return self.std_args

    def get_output_args(self, target):
        return [target]

    def get_buildtype_linker_args(self, buildtype):
        return []

    def get_linker_always_args(self):
        return []

    def get_coverage_link_args(self):
        return []

    def get_always_args(self):
        return []

    def thread_link_flags(self, env):
        return []

    def openmp_flags(self):
        return []

    def get_option_link_args(self, options):
        return []

    @classmethod
    def unix_args_to_native(cls, args):
        return args[:]

    def get_link_debugfile_args(self, targetfile):
        return []


class ArmarLinker(ArLinker):

    def __init__(self, exelist):
        self.exelist = exelist
        self.id = 'armar'
        self.std_args = ['-csr']

    def can_linker_accept_rsp(self):
        # armar cann't accept arguments using the @rsp syntax
        return False


class DLinker(StaticLinker):
    def __init__(self, exelist, arch):
        self.exelist = exelist
        self.id = exelist[0]
        self.arch = arch

    def can_linker_accept_rsp(self):
        return mesonlib.is_windows()

    def build_rpath_args(self, build_dir, from_dir, rpath_paths, build_rpath, install_rpath):
        return []

    def get_exelist(self):
        return self.exelist[:]

    def get_std_link_args(self):
        return ['-lib']

    def get_output_args(self, target):
        return ['-of=' + target]

    def get_buildtype_linker_args(self, buildtype):
        return []

    def get_linker_always_args(self):
        if mesonlib.is_windows():
            if self.arch == 'x86_64':
                return ['-m64']
            elif self.arch == 'x86_mscoff' and self.id == 'dmd':
                return ['-m32mscoff']
            return ['-m32']
        return []

    def get_coverage_link_args(self):
        return []

    def get_always_args(self):
        return []

    def thread_link_flags(self, env):
        return []

    def openmp_flags(self):
        return []

    def get_option_link_args(self, options):
        return []

    @classmethod
    def unix_args_to_native(cls, args):
        return args[:]

    def get_link_debugfile_args(self, targetfile):
        return []

class CcrxLinker(StaticLinker):

    def __init__(self, exelist):
        self.exelist = exelist
        self.id = 'rlink'
        pc, stdo = Popen_safe(self.exelist + ['-h'])[0:2]
        self.std_args = []

    def can_linker_accept_rsp(self):
        return False

    def build_rpath_args(self, build_dir, from_dir, rpath_paths, build_rpath, install_rpath):
        return []

    def get_exelist(self):
        return self.exelist[:]

    def get_std_link_args(self):
        return self.std_args

    def get_output_args(self, target):
        return ['-output=%s' % target]

    def get_buildtype_linker_args(self, buildtype):
        return []


    def get_linker_always_args(self):
        return ['-nologo', '-form=library']

    def get_coverage_link_args(self):
        return []

    def get_always_args(self):
        return []

    def thread_link_flags(self, env):
        return []

    def openmp_flags(self):
        return []

    def get_option_link_args(self, options):
        return []

    @classmethod
    def unix_args_to_native(cls, args):
        return args[:]

    def get_link_debugfile_args(self, targetfile):
        return []


class DynamicLinker:

    """Base class for dynamic linkers."""

    _buildtype_args = {
        'plain': [],
        'debug': [],
        'debugoptimized': [],
        'release': [],
        'minsize': [],
        'custom': [],
    }

    def __init__(self, id: str, exe: str, compiler_type: 'compilers.CompilerType'):
        self.id = id
        self.exe = exe
        self.compiler_type = compiler_type

    def can_linker_accept_rsp(self) -> bool:
        """Determines whether the linker can accept arguments using the @rsp
        syntax.
        """
        return mesonlib.is_windows()

    def get_linker_always_args(self) -> List[str]:
        """Get arguments always required by the linker."""
        return []

    def get_option_link_args(self, options) -> List[str]:
        return []

    def get_args_from_envvars(self) -> List[str]:
        def log_var(var, val: Optional[str]) -> None:
            if val:
                mlog.log('Appending {} from environment: {!r}'.format(var, val))
            else:
                mlog.debug('No {} in the environment, not changing global flags.'.format(var))

        link_flags = os.environ.get('LDFLAGS')
        log_var('LDFLAGS', link_flags)
        if link_flags:
            return shlex.split(link_flags)
        return []

    def get_std_shared_lib_link_args(self) -> List[str]:
        return []

    def get_std_shared_module_link_args(self) -> List[str]:
        return self.get_std_shared_lib_link_args()

    def get_link_whole_for(self, args: List[str]) -> List[str]:
        if isinstance(args, list) and not args:
            return []
        raise mesonlib.EnvironmentException('Language %s does not support linking whole archives.' % self.get_display_language())

    def get_pie_link_args(self) -> List[str]:
        """Arguments required by the dynamic linker for -fPIE executables."""
        return []

    def get_lto_link_args(self) -> List[str]:
        """Arguments required by the dynamic linker for LTO/IPO."""
        return []

    def gen_export_dynamic_link_args(self, env) -> List[str]:
        return []

    def get_asneeded_args(self) -> List[str]:
        return []

    def get_buildtype_linker_args(self, buildtype: str) -> List[str]:
        return self._buildtype_args[buildtype]

    def get_linker_exelist(self) -> List[str]:
        return self.exe.copy()

    def get_allow_undefined_link_args(self) -> List[str]:
        return []

    def get_linker_lib_prefix(self) -> str:
        return ''

    def get_linker_search_args(self, dirname: str) -> List[str]:
        return []

    def get_linker_output_args(self, outputname: str) -> List[str]:
        return []

    def linker_to_compiler_args(self, args: List[str]) -> List[str]:
        return args

    def get_linker_debug_crt_args(self) -> List[str]:
        """Arguments needed to select a debug crt for the linker.

        This is only needed for MSVC

        Sometimes we need to manually select the CRT (C runtime) to use with
        MSVC. One example is when trying to link with static libraries since
        MSVC won't auto-select a CRT for us in that case and will error out
        asking us to select one.
        """
        # TODO: this really belongs in the static linker, no?
        return []

    def get_no_stdlib_link_args(self) -> List[str]:
        return []

    def get_coverage_link_args(self) -> List[str]:
        return []


class UnixLikeDynamicLinker(DynamicLinker):

    def get_std_shared_lib_link_args(self):
        return ['-shared']

    def get_pie_link_args(self, buildtype):
        return ['-pie']

    def get_allow_undefined_link_args(self):
        if self.compiler_type.is_windows_compiler:
            return []
        return ['-Wl,--allow-shlib-undefined']

    def get_linker_output_args(self, outputname: str) -> List[str]:
        return ['-o', outputname]

    def get_linker_search_args(self, dirname: str) -> List[str]:
        return ['-L' + dirname]


class GNULikeDynamicLinker(UnixLikeDynamicLinker):

    """Base class for GNU ld, gold, and llvm's lld when acting like GNU ld."""

    _buildtype_args = {
        'plain': [],
        'debug': [],
        'debugoptimized': [],
        'release': ['-Wl,-O1'],
        'minsize': [],
        'custom': [],
    }

    def get_asneeded_args(self) -> List[str]:
        return ['-Wl,--as-needed']

    def get_std_shared_module_link_args(self, options) -> List[str]:
        return ['-shared']

    def get_link_whole_for(self, args: List[str]) -> List[str]:
        return ['-Wl,--whole-archive'] + args + ['-Wl,--no-whole-archive']

    def get_lto_link_args(self) -> List[str]:
        return ['-flto']

    def get_no_stdlib_link_args(self) -> List[str]:
        return ['-nostdlib']

    def get_option_link_args(self, options) -> List[str]:
        if self.compiler_type.is_windows_compiler:
            return options['c_winlibs'].value[:]
        return []

    def get_coverage_link_args(self):
        # XXX: Is this really a gnuism?
        return ['--coverage']


class GNUBFDDynamicLinker(GNULikeDynamicLinker):

    """Concrete implementation of ld.bfd."""

    def __init__(self, exe: str, compiler_type: 'compilers.CompilerType'):
        super().__init__('bfd', exe, compiler_type)


class GNUGoldDDynamicLinker(GNULikeDynamicLinker):

    """Concrete implementation of ld.gold."""

    def __init__(self, exe: str, compiler_type: 'compilers.CompilerType'):
        super().__init__('gold', exe, compiler_type)


class LLDUnixDynamicLinker(GNULikeDynamicLinker):

    """Concrete implementation of lld (Unix-like)."""

    def __init__(self, exe: str, compiler_type: 'compilers.CompilerType'):
        super().__init__('lld', exe, compiler_type)


class MSVCLikeDynamicLinker(DynamicLinker):

    """Shared base class for MSVC linke.exe and other linkers acting like it."""

    _buildtype_args = {
        'plain': [],
        'debug': [],
        'debugoptimized': [],
        # The otherwise implicit REF and ICF linker optimisations are
        # disabled by /DEBUG.  REF implies ICF.
        'release': ['/OPT:REF'],
        'minsize': ['/INCREMENTAL:NO', '/OPT:REF'],
        'custom': [],
    }

    def get_allow_undefined_link_args(self) -> List[str]:
        return ['/FORCE:UNRESOLVED']

    def get_linker_always_args(self) -> List[str]:
        return ['/nologo']

    def get_linker_output_args(self, outputname: str) -> List[str]:
        return ['/OUT:' + outputname]

    def get_linker_search_args(self, dirname: str) -> List[str]:
        return ['/LIBPATH:' + dirname]

    def get_linker_output_args(self, outputname: str) -> List[str]:
        return ['/MACHINE:' + self.machine, '/OUT:' + outputname]

    def linker_to_compiler_args(self, args: List[str]) -> List[str]:
        return ['/link'] + args

    def get_option_link_args(self, options):
        return options['c_winlibs'].value[:]

    def get_std_shared_lib_link_args(self) -> List[str]:
        return ['/DLL']

    def get_link_whole_for(self, args) -> List[str]:
        # Only since VS2015
        args = mesonlib.listify(args)
        return ['/WHOLEARCHIVE:' + x for x in args]

    def get_linker_debug_crt_args(self) -> List[str]:
        return ['/MDd']


class MSVCDynamicLinker(MSVCLikeDynamicLinker):

    """Concrete implementation of MSVC's link.exe."""

    buildtype_args = {
        'plain': [],
        'debug': [],
        'debugoptimized': [],
        # The otherwise implicit REF and ICF linker optimisations are disabled
        # by /DEBUG. REF implies ICF.
        'release': ['/OPT:REF'],
        'minsize': ['/INCREMENTAL:NO', '/OPT:REF'],
        'custom': [],
    }

    def __init__(self, exe: str, compiler_type: 'compilers.CompilerType'):
        super().__init__('link', exe, compiler_type)


class LLDWinDynamicLinker(MSVCLikeDynamicLinker):

    """Concrete implementation of LLVMs lld-link (link.exe like)."""

    def __init__(self, exe: str, compiler_type: 'compilers.CompilerType'):
        super().__init__('lld-link', exe, compiler_type)


class AppleDynamicLinker(UnixLikeDynamicLinker):

    """Concrete implementation of the Apple Linker."""

    def __init__(self, exe: str, compiler_type: 'compilers.CompilerType'):
        super().__init__('apple', exe, compiler_type)

    def get_asneeded_args(self) -> List[str]:
        return ['-Wl,-dead_strip_dylibs']

    def get_std_shared_module_link_args(self, options) -> List[str]:
        return ['-bundle', '-Wl,-undefined,dynamic_lookup']

    def get_link_whole_for(self, args: List[str]) -> List[str]:
        result = []
        for a in args:
            result.extend(['-Wl,-force_load', a])
        return result

    def get_allow_undefined_link_args(self) -> List[str]:
        return ['-Wl,-undefined,dynamic_lookup']

    def get_linker_always_args(self) -> List[str]:
        return super().get_linker_always_args() + ['-Wl,-headerpad_max_install_names']


class ArmNixBaseDynamicLinker(UnixLikeDynamicLinker):

    """SHared base class for arm linkers on Unix-like systems."""

    def get_std_shared_lib_link_args(self) -> List[str]:
        return []

    def get_linker_exelist(self) -> List[str]:
        return ['armlink']


class ArmNixDynamicLinker(ArmNixBaseDynamicLinker):

    """Concrente implementation of the Arm linker for Unix-like systems."""

    def __init__(self, exe: str, compiler_type: 'compilers.CompilerType'):
        super().__init__('arm', exe, compiler_type)

    def get_export_dynamic_link_args(self, env) -> List[str]:
        return ['--export_dynamic']


class ArmclangNixDynamicLinker(ArmNixBaseDynamicLinker):

    """Concrete implementation of the Armclang linker for Unix-like systems."""

    def __init__(self, exe: str, compiler_type: 'compilers.CompilerType'):
        super().__init__('armclang', exe, compiler_type)


class DMDDynamicLinker(DynamicLinker):

    """Linker for DMD D language compiler."""

    def __init__(self, exe: str, compiler_type: 'compilers.CompilerType'):
        super().__init__('dmd', exe, compiler_type)

    def std_shared_lib_link_args(self) -> List[str]:
        return ['-shared', '-defaultlib=libphobos2.so']


class CcrxDynamicLinker(DynamicLinker):

    """Linker for Renesas CCRX."""

    def __init__(self, exe: str, compiler_type: 'compilers.CompilerType'):
        super().__init__('ccrx', exe, compiler_type)

    def get_linker_lib_prefix(self) -> str:
        return '-lib='

    def get_linker_exelist(self) -> List[str]:
        return ['rlink.exe']

    def get_output_args(self, target: str) -> List[str]:
        return ['-output={}'.format(target)]

    def get_linker_output_args(self, outputname: str) -> List[str]:
        return ['-output=' + outputname]


class PGIDynamiclinker(DynamicLinker):

    """PGI Linker."""
