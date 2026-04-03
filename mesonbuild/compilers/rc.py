# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
import typing as T

from .compilers import Compiler
from ..mesonlib import get_meson_command

if T.TYPE_CHECKING:
    from ..environment import Environment
    from ..linkers.linkers import DynamicLinker
    from ..mesonlib import MachineChoice


class RCCompiler(Compiler):

    """Base class for Windows Resource Compilers."""

    language = 'rc'

    def __init__(self, exelist: T.List[str], version: str,
                 for_machine: 'MachineChoice', env: 'Environment',
                 linker: T.Optional['DynamicLinker'] = None,
                 full_version: T.Optional[str] = None):
        super().__init__([], exelist, version, for_machine, env, linker, full_version)

    def needs_static_linker(self) -> bool:
        return False

    def can_linker_accept_rsp(self) -> bool:
        return False

    def sanity_check(self, work_dir: str) -> None:
        return None

    def _sanity_check_source_code(self) -> str:
        return ''

    def get_optimization_args(self, optimization_level: str) -> T.List[str]:
        return []

    def get_debug_args(self, is_debug: bool) -> T.List[str]:
        return []

    def get_pic_args(self) -> T.List[str]:
        return []

    def get_werror_args(self) -> T.List[str]:
        return []

    def get_crt_compile_args(self, crt_val: str, env: 'Environment') -> T.List[str]:
        return []

    def get_compile_only_args(self) -> T.List[str]:
        return []


class VisualStudioLikeResourceCompiler(RCCompiler):

    """Base for resource compilers with MSVC-style CLI (/I, /fo, /nologo)."""

    def get_object_suffix(self) -> T.Optional[str]:
        return 'res'

    def get_always_args(self) -> T.List[str]:
        return ['/nologo']

    def get_output_args(self, outputname: str) -> T.List[str]:
        return ['/fo' + outputname]

    def get_include_args(self, path: str, is_system: bool) -> T.List[str]:
        if not path:
            path = '.'
        return ['/I', path]

    def get_depfile_format(self) -> str:
        return 'msvc'

    def depfile_for_object(self, objfile: str) -> T.Optional[str]:
        # Dependency tracking is handled by the --internal rc wrapper
        # using cl.exe /showIncludes, which uses msvc depfile format.
        # The wrapper outputs deps to stdout, not to a separate file.
        return None

    def compute_parameters_with_absolute_paths(self, parameter_list: T.List[str],
                                               build_dir: str) -> T.List[str]:
        for idx, i in enumerate(parameter_list):
            if i[:2] == '/I' and len(i) > 2:
                parameter_list[idx] = '/I' + os.path.normpath(os.path.join(build_dir, i[2:]))
            elif i == '/I' and idx + 1 < len(parameter_list):
                parameter_list[idx + 1] = os.path.normpath(os.path.join(build_dir, parameter_list[idx + 1]))
        return parameter_list


class GnuLikeResourceCompiler(RCCompiler):

    """Base for resource compilers with GNU-style CLI (-I, -o)."""

    def get_always_args(self) -> T.List[str]:
        return []

    def get_output_args(self, outputname: str) -> T.List[str]:
        return ['-o', outputname]

    def get_include_args(self, path: str, is_system: bool) -> T.List[str]:
        if not path:
            path = '.'
        return ['-I' + path]

    def compute_parameters_with_absolute_paths(self, parameter_list: T.List[str],
                                               build_dir: str) -> T.List[str]:
        for idx, i in enumerate(parameter_list):
            if i[:2] == '-I':
                parameter_list[idx] = i[:2] + os.path.normpath(os.path.join(build_dir, i[2:]))
        return parameter_list


class WindowsResourceCompiler(VisualStudioLikeResourceCompiler):

    """Microsoft rc.exe."""

    id = 'rc'

    def __init__(self, exelist: T.List[str], version: str,
                 for_machine: 'MachineChoice', env: 'Environment',
                 cl_path: T.Optional[str] = None,
                 linker: T.Optional['DynamicLinker'] = None,
                 full_version: T.Optional[str] = None):
        super().__init__(exelist, version, for_machine, env, linker, full_version)
        self.cl_path = cl_path

    def get_exelist(self, ccache: bool = True) -> T.List[str]:
        exelist = super().get_exelist(ccache)
        if self.cl_path:
            return get_meson_command() + ['--internal', 'rc',
                                          '--cl', self.cl_path,
                                          '--rc'] + exelist
        return exelist


class LlvmRcCompiler(VisualStudioLikeResourceCompiler):

    """LLVM llvm-rc."""

    id = 'llvm-rc'


class WindresCompiler(GnuLikeResourceCompiler):

    """GNU windres."""

    id = 'windres'

    def get_depfile_suffix(self) -> str:
        return 'd'

    def get_dependency_gen_args(self, outtarget: str, outfile: str) -> T.List[str]:
        return ['--preprocessor-arg=-MD',
                '--preprocessor-arg=-MQ' + outtarget,
                '--preprocessor-arg=-MF' + outfile]


class LlvmWindresCompiler(GnuLikeResourceCompiler):

    """LLVM llvm-windres."""

    id = 'llvm-windres'

    def get_depfile_suffix(self) -> str:
        return 'd'

    def get_dependency_gen_args(self, outtarget: str, outfile: str) -> T.List[str]:
        return ['--preprocessor-arg=-MD',
                '--preprocessor-arg=-MQ' + outtarget,
                '--preprocessor-arg=-MF' + outfile]


class WineResourceCompiler(GnuLikeResourceCompiler):

    """Wine Resource Compiler."""

    id = 'wrc'

    def depfile_for_object(self, objfile: str) -> T.Optional[str]:
        return None
