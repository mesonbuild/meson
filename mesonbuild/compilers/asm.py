from __future__ import annotations

import os
import typing as T

from ..linkers import RSPFileSyntax
from ..linkers.linkers import VisualStudioLikeLinkerMixin
from ..mesonlib import EnvironmentException, MesonException, get_meson_command
from ..options import OptionKey
from .compilers import CompileCheckMode, Compiler
from .mixins.metrowerks import (
    MetrowerksCompiler,
    mwasmarm_instruction_set_args,
    mwasmeppc_instruction_set_args,
)
from .mixins.ti import TICompiler

if T.TYPE_CHECKING:
    from ..environment import Environment
    from ..linkers.linkers import DynamicLinker
    from ..mesonlib import MachineChoice

nasm_optimization_args: dict[str, list[str]] = {
    'plain': [],
    '0': ['-O0'],
    'g': ['-O0'],
    '1': ['-O1'],
    '2': ['-Ox'],
    '3': ['-Ox'],
    's': ['-Ox'],
}


class ASMCompiler(Compiler):

    """Shared base class for all ASM Compilers (Assemblers)"""

    _SUPPORTED_ARCHES: set[str] = set()

    def __init__(self, ccache: list[str], exelist: list[str], version: str,
                 for_machine: MachineChoice, env: Environment,
                 linker: DynamicLinker | None = None,
                 full_version: str | None = None):
        info = env.machines[for_machine]
        if self._SUPPORTED_ARCHES and info.cpu_family not in self._SUPPORTED_ARCHES:
            raise EnvironmentException(f'ASM Compiler {self.id} does not support building for {info.cpu_family} CPU family.')
        super().__init__(ccache, exelist, version, for_machine, env, linker, full_version)

    def sanity_check(self, work_dir: str) -> None:
        return None

    def _sanity_check_source_code(self) -> str:
        # TODO: Stub implementation to be replaced in future patch
        return ''


class NasmCompiler(ASMCompiler):
    language = 'nasm'
    id = 'nasm'

    # https://learn.microsoft.com/en-us/cpp/c-runtime-library/crt-library-features
    crt_args: dict[str, list[str]] = {
        'none': [],
        'md': ['/DEFAULTLIB:ucrt.lib', '/DEFAULTLIB:vcruntime.lib', '/DEFAULTLIB:msvcrt.lib'],
        'mdd': ['/DEFAULTLIB:ucrtd.lib', '/DEFAULTLIB:vcruntimed.lib', '/DEFAULTLIB:msvcrtd.lib'],
        'mt': ['/DEFAULTLIB:libucrt.lib', '/DEFAULTLIB:libvcruntime.lib', '/DEFAULTLIB:libcmt.lib'],
        'mtd': ['/DEFAULTLIB:libucrtd.lib', '/DEFAULTLIB:libvcruntimed.lib', '/DEFAULTLIB:libcmtd.lib'],
    }

    _SUPPORTED_ARCHES = {'x86', 'x86_64'}

    def __init__(self, ccache: list[str], exelist: list[str], version: str,
                 for_machine: MachineChoice, env: Environment,
                 linker: DynamicLinker | None = None,
                 full_version: str | None = None):
        super().__init__(ccache, exelist, version, for_machine, env, linker, full_version)
        if isinstance(self.linker, VisualStudioLikeLinkerMixin):
            self.base_options.add(OptionKey('b_vscrt'))

    def needs_static_linker(self) -> bool:
        return True

    def get_always_args(self) -> list[str]:
        if self.info.is_64_bit:
            if self.info.cpu == 'x32':
                cpu = 'x32'
            else:
                cpu = '64'
        else:
            cpu = '32'
        if self.info.is_windows() or self.info.is_cygwin():
            plat = 'win'
            define = f'WIN{cpu}'
        elif self.info.is_darwin():
            plat = 'macho'
            define = 'MACHO'
        elif self.info.is_os2():
            cpu = ''
            if self.environment.coredata.optstore.get_value_for(OptionKey('os2_emxomf')):
                plat = 'obj2'
                define = 'OBJ2'
            else:
                plat = 'aout'
                define = 'AOUT'
        else:
            plat = 'elf'
            define = 'ELF'
        args = ['-f', f'{plat}{cpu}', f'-D{define}']
        if self.info.is_64_bit:
            args.append('-D__x86_64__')
        return args

    def get_werror_args(self) -> list[str]:
        return ['-Werror']

    def get_output_args(self, outputname: str) -> list[str]:
        return ['-o', outputname]

    def unix_args_to_native(self, args: list[str]) -> list[str]:
        outargs: list[str] = []
        for arg in args:
            if arg in {'-mms-bitfields', '-pthread'}:
                continue
            outargs.append(arg)
        return outargs

    def get_optimization_args(self, optimization_level: str) -> list[str]:
        return nasm_optimization_args[optimization_level]

    def get_debug_args(self, is_debug: bool) -> list[str]:
        if is_debug:
            return ['-g']
        return []

    def get_depfile_suffix(self) -> str:
        return 'd'

    def get_dependency_gen_args(self, outtarget: str, outfile: str) -> list[str]:
        return ['-MD', outfile, '-MQ', outtarget]

    def get_pic_args(self) -> list[str]:
        return []

    def get_include_args(self, path: str, is_system: bool) -> list[str]:
        if not path:
            path = '.'
        return ['-I' + path]

    def compute_parameters_with_absolute_paths(self, parameter_list: list[str],
                                               build_dir: str) -> list[str]:
        for idx, i in enumerate(parameter_list):
            if i[:2] == '-I':
                parameter_list[idx] = i[:2] + os.path.normpath(os.path.join(build_dir, i[2:]))
        return parameter_list

    def get_crt_compile_args(self, crt_val: str) -> list[str]:
        return []

    # Linking ASM-only objects into an executable or DLL
    # require this, otherwise it'll fail to find
    # _WinMain or _DllMainCRTStartup.
    def get_crt_link_args(self, crt_val: str) -> list[str]:
        if not isinstance(self.linker, VisualStudioLikeLinkerMixin):
            return []
        return self.crt_args[self.get_crt_val(crt_val)]

    def rsp_file_syntax(self) -> RSPFileSyntax:
        return RSPFileSyntax.NASM

class YasmCompiler(NasmCompiler):
    id = 'yasm'

    def get_optimization_args(self, optimization_level: str) -> list[str]:
        # Yasm is incompatible with Nasm optimization flags.
        return []

    def get_exelist(self, ccache: bool = True) -> list[str]:
        # Wrap yasm executable with an internal script that will write depfile.
        exelist = super().get_exelist(ccache)
        return get_meson_command() + ['--internal', 'yasm'] + exelist

    def get_debug_args(self, is_debug: bool) -> list[str]:
        if is_debug:
            if isinstance(self.linker, VisualStudioLikeLinkerMixin):
                return ['-g', 'cv8']
            if self.info.is_darwin():
                return ['-g', 'null']
            return ['-g', 'dwarf2']
        return []

    def get_dependency_gen_args(self, outtarget: str, outfile: str) -> list[str]:
        return ['--depfile', outfile]

# https://learn.microsoft.com/en-us/cpp/assembler/masm/ml-and-ml64-command-line-reference
class MasmCompiler(ASMCompiler):
    language = 'masm'
    id = 'ml'

    _SUPPORTED_ARCHES = {'x86', 'x86_64'}

    def get_compile_only_args(self) -> list[str]:
        return ['/c']

    @staticmethod
    def get_argument_syntax() -> str:
        return 'msvc'

    def needs_static_linker(self) -> bool:
        return True

    def get_always_args(self) -> list[str]:
        return ['/nologo']

    def get_werror_args(self) -> list[str]:
        return ['/WX']

    def get_output_args(self, outputname: str) -> list[str]:
        return ['/Fo', outputname]

    def get_output_args_for_mode(self, outputname: str, mode: CompileCheckMode) -> list[str]:
        if mode != CompileCheckMode.COMPILE:
            raise MesonException("Linker support for MASM is not implemented")
        return self.get_output_args(outputname)

    def get_optimization_args(self, optimization_level: str) -> list[str]:
        return []

    def get_debug_args(self, is_debug: bool) -> list[str]:
        if is_debug:
            return ['/Zi']
        return []

    def get_pic_args(self) -> list[str]:
        return []

    def get_include_args(self, path: str, is_system: bool) -> list[str]:
        if not path:
            path = '.'
        return ['-I' + path]

    def compute_parameters_with_absolute_paths(self, parameter_list: list[str],
                                               build_dir: str) -> list[str]:
        for idx, i in enumerate(parameter_list):
            if i[:2] == '-I' or i[:2] == '/I':
                parameter_list[idx] = i[:2] + os.path.normpath(os.path.join(build_dir, i[2:]))
        return parameter_list

    def get_crt_compile_args(self, crt_val: str) -> list[str]:
        return []

    def depfile_for_object(self, objfile: str) -> str | None:
        return None


# https://learn.microsoft.com/en-us/cpp/assembler/arm/arm-assembler-command-line-reference
class MasmARMCompiler(ASMCompiler):
    language = 'masm'
    id = 'armasm'
    _SUPPORTED_ARCHES = {'arm', 'aarch64'}

    def needs_static_linker(self) -> bool:
        return True

    def get_always_args(self) -> list[str]:
        return ['-nologo']

    def get_werror_args(self) -> list[str]:
        return []

    def get_output_args(self, outputname: str) -> list[str]:
        return ['-o', outputname]

    def get_optimization_args(self, optimization_level: str) -> list[str]:
        return []

    def get_debug_args(self, is_debug: bool) -> list[str]:
        if is_debug:
            return ['-g']
        return []

    def get_pic_args(self) -> list[str]:
        return []

    def get_include_args(self, path: str, is_system: bool) -> list[str]:
        if not path:
            path = '.'
        return ['-i' + path]

    def compute_parameters_with_absolute_paths(self, parameter_list: list[str],
                                               build_dir: str) -> list[str]:
        for idx, i in enumerate(parameter_list):
            if i[:2] == '-I':
                parameter_list[idx] = i[:2] + os.path.normpath(os.path.join(build_dir, i[2:]))
        return parameter_list

    def get_crt_compile_args(self, crt_val: str) -> list[str]:
        return []

    def get_depfile_format(self) -> str:
        return 'msvc'

    def depfile_for_object(self, objfile: str) -> str | None:
        return None


# https://downloads.ti.com/docs/esd/SPRUI04/
class TILinearAsmCompiler(TICompiler, ASMCompiler):
    language = 'linearasm'
    _SUPPORTED_ARCHES = {'c6000'}

    def __init__(self, ccache: list[str], exelist: list[str], version: str,
                 for_machine: MachineChoice, env: Environment,
                 linker: DynamicLinker | None = None,
                 full_version: str | None = None):
        ASMCompiler.__init__(self, ccache, exelist, version, for_machine, env, linker, full_version)
        TICompiler.__init__(self)

    def needs_static_linker(self) -> bool:
        return True

    def get_always_args(self) -> list[str]:
        return []

    def get_crt_compile_args(self, crt_val: str) -> list[str]:
        return []

    def get_depfile_suffix(self) -> str:
        return 'd'


class MetrowerksAsmCompiler(MetrowerksCompiler, ASMCompiler):
    language = 'nasm'

    def __init__(self, ccache: list[str], exelist: list[str], version: str,
                 for_machine: MachineChoice, env: Environment,
                 linker: DynamicLinker | None = None,
                 full_version: str | None = None):
        ASMCompiler.__init__(self, ccache, exelist, version, for_machine, env, linker, full_version)
        MetrowerksCompiler.__init__(self)

        self.warn_args: dict[str, list[str]] = {
            '0': [],
            '1': [],
            '2': [],
            '3': [],
            'everything': []}
        self.can_compile_suffixes.add('s')

    def get_crt_compile_args(self, crt_val: str) -> list[str]:
        return []

    def get_optimization_args(self, optimization_level: str) -> list[str]:
        return []

    def get_pic_args(self) -> list[str]:
        return []

    def needs_static_linker(self) -> bool:
        return True


class MetrowerksAsmCompilerARM(MetrowerksAsmCompiler):
    id = 'mwasmarm'
    _SUPPORTED_ARCHES = {'arm'}

    def get_instruction_set_args(self, instruction_set: str) -> list[str] | None:
        return mwasmarm_instruction_set_args.get(instruction_set, None)


class MetrowerksAsmCompilerEmbeddedPowerPC(MetrowerksAsmCompiler):
    id = 'mwasmeppc'
    _SUPPORTED_ARCHES = {'ppc'}

    def get_instruction_set_args(self, instruction_set: str) -> list[str] | None:
        return mwasmeppc_instruction_set_args.get(instruction_set, None)
