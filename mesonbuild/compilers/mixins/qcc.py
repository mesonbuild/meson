# SPDX-License-Identifier: Apache-2.0
# Copyright 2025 The Meson development team

from __future__ import annotations

"""Mixin for the QNX qcc/q++ compiler driver.

qcc/q++ invoke cc1/cc1plus directly rather than wrapping gcc/g++, so
compile-phase behavior matches gcc/g++, but several gcc *driver*-level
conveniences aren't replicated and need explicit handling here.
"""

import typing as T

from ..compilers import CompileCheckMode
from ...mesonlib import EnvironmentException, MesonException
from ...options import OptionKey

if T.TYPE_CHECKING:
    from ...build import BuildTarget
    from .clike import CLikeCompiler
    CompilerBase = CLikeCompiler
else:
    CompilerBase = object


class QccCompiler(CompilerBase):

    id = 'qcc'

    def get_dependency_gen_args(self, outtarget: str, outfile: str) -> T.List[str]:
        # qcc redefines plain '-M' as "generate a linker mapfile", so route
        # dependency-file flags through the '-Wc,' passthrough to
        # cc1/cc1plus instead. '-MP' also sidesteps a cc1 crash when '-MMD'
        # is immediately followed by '-MF <file>'.
        return ['-Wc,-MQ,' + outtarget, '-Wc,-MMD', '-Wc,-MP', '-Wc,-MF,' + outfile]

    def get_preprocess_only_args(self) -> T.List[str]:
        # qcc's driver silently drops bare '-P' and redirects cc1's output
        # to a '<source>.i' file instead of stdout; '-Wp,-P' avoids both.
        return ['-E', '-Wp,-P']

    def get_thinlto_cache_args(self, path: str) -> T.List[str]:
        # '-flto-incremental=' (b_thinlto_cache) is rejected by cc1 as
        # unrecognized; plain LTO is unaffected and needs no override.
        raise EnvironmentException(
            "The 'qcc' compiler family does not support ThinLTO incremental caching (b_thinlto_cache)")

    def get_coverage_args(self) -> T.List[str]:
        return ['-fprofile-arcs', '-ftest-coverage']

    def get_coverage_link_args(self) -> T.List[str]:
        return ['-fprofile-arcs', '-ftest-coverage']

    def get_profile_generate_args(self) -> T.List[str]:
        return ['-fprofile-generate', '-fprofile-arcs']

    def openmp_link_flags(self) -> T.List[str]:
        return self.openmp_flags() + ['-lgomp']

    # Maps a '-fsanitize=' value to its runtime library. No 'thread' entry:
    # the SDP ships no libtsan.
    _SANITIZER_RUNTIME_LIBS: T.Dict[str, str] = {
        'address': 'asan',
        'undefined': 'ubsan',
        'leak': 'lsan',
    }

    def sanitizer_link_args(self, target: T.Optional['BuildTarget'], value: T.List[str]) -> T.List[str]:
        # qcc's driver doesn't auto-link a sanitizer runtime for
        # '-fsanitize=<name>' like gcc's driver does.
        args = super().sanitizer_link_args(target, value)
        linked_a_runtime = False
        for v in value:
            lib = self._SANITIZER_RUNTIME_LIBS.get(v)
            if lib:
                args = args + [f'-l{lib}']
                linked_a_runtime = True
        if linked_a_runtime:
            # On SDP 8.0 (gcc 12.2.0 backend), the sanitizer runtimes pull in
            # libgcc_eh.a, whose __gthread_once references pthread_once. A
            # shared-library target with no other pthread-touching code has
            # nothing yet marking libc as needed at that point, so plain
            # '-lc' placed after Meson's default '-Wl,--as-needed' gets
            # silently dropped and the link fails with an undefined
            # pthread_once. Toggling --as-needed off just for this explicit
            # -lc keeps it unconditionally, regardless of link-line order.
            args = args + ['-Wl,--no-as-needed', '-lc', '-Wl,--as-needed']
        return args

    def get_default_include_dirs(self) -> T.List[str]:
        # qcc/q++ print no banner for plain '-v'; '-vv' is required.
        from .gnu import gnulike_default_include_dirs
        return gnulike_default_include_dirs(
            tuple(self.get_exelist(ccache=False)), self.language, verbosity_arg='-vv').copy()

    @classmethod
    def use_linker_args(cls, linker: str, version: str) -> T.List[str]:
        # '-fuse-ld=' reaches cc1/cc1plus, which never invokes a linker
        # itself; no qcc-specific linker-selection mechanism exists.
        raise MesonException(
            f"Selecting an alternate linker ({linker!r}) is not supported "
            "for the 'qcc' compiler family: '-fuse-ld=' is not meaningful "
            'to cc1/cc1plus (which never invokes a linker themselves), and '
            'no qcc-documented equivalent exists.')

    def _sanity_check_compile_args(self, sourcename: str, binname: str) -> T.Tuple[T.List[str], T.List[str]]:
        # The base/CLikeCompiler combination produces a command with '-c' mixed into an already link-shaped invocation,
        # which qcc's driver rejects outright.
        # Build a clean, mode-consistent command instead.
        if self.is_cross and not self.environment.has_exe_wrapper():
            mode = CompileCheckMode.COMPILE
        else:
            mode = CompileCheckMode.LINK

        cargs = list(T.cast('T.List[str]', self.environment.coredata.optstore.get_value_for(
            OptionKey(f'{self.language}_args', machine=self.for_machine))))
        args = self.exelist_no_ccache + self.get_always_args()

        if mode is CompileCheckMode.COMPILE:
            command = args + self.get_compile_only_args() + self.get_output_args(binname) + [sourcename] + cargs
            linker_args: T.List[str] = []
        else:
            largs = list(T.cast('T.List[str]', self.environment.coredata.optstore.get_value_for(
                OptionKey(f'{self.language}_link_args', machine=self.for_machine))))
            command = args + self.get_output_args(binname) + [sourcename] + cargs
            linker_args = self.linker_to_compiler_args(largs)

        return command, linker_args

    def sanity_check(self, work_dir: str) -> None:
        try:
            super().sanity_check(work_dir)
        except EnvironmentException as e:
            hint = ('This can happen if the QNX SDP environment has not '
                    'been set up (source qnxsdp-env.sh) or if the QNX SDP '
                    'license is missing/expired/not activated (qcc/q++ '
                    'exit codes 129-133).')
            raise EnvironmentException(f'{e} {hint}')
