# SPDX-License-Identifier: Apache-2.0
# Copyright 2019 The Meson development team
# Copyright © 2023 Intel Corporation

"""Mixins for compilers that *are* linkers.

While many compilers (such as gcc and clang) are used by meson to dispatch
linker commands and other (like MSVC) are not, a few (such as DMD) actually
are both the linker and compiler in one binary. This module provides mixin
classes for those cases.
"""

from __future__ import annotations

import typing as T

from ...mesonlib import EnvironmentException, MesonException, is_windows
from ..compilers import CompileCheckMode

if T.TYPE_CHECKING:
    from ...build import BuildTarget
    from ...compilers.compilers import Compiler
    from ...options import OptionStore
else:
    # This is a bit clever, for mypy we pretend that these mixins descend from
    # Compiler, so we get all of the methods and attributes defined for us, but
    # for runtime we make them descend from object (which all classes normally
    # do). This gives up DRYer type checking, with no runtime impact
    Compiler = object


class BasicLinkerIsCompilerMixin(Compiler):

    """Provides a baseline of methods that a linker would implement.

    In every case this provides a "no" or "empty" answer. If a compiler
    implements any of these it needs a different mixin or to override that
    functionality itself.
    """

    def sanitizer_link_args(self, target: BuildTarget, value: list[str]) -> list[str]:
        return []

    def get_lto_link_args(self, *, target: BuildTarget | None = None, threads: int = 0,
                          mode: str = 'default', thinlto_cache_dir: str | None = None) -> list[str]:
        return []

    def can_linker_accept_rsp(self) -> bool:
        return is_windows()

    def get_linker_exelist(self) -> list[str]:
        return self.exelist.copy()

    def get_linker_output_args(self, outputname: str) -> list[str]:
        return []

    def get_linker_always_args(self) -> list[str]:
        return []

    def _sanity_check_mode(self) -> CompileCheckMode:
        # These compilers produce an executable in one step, there is no
        # separate link phase that could be skipped.
        return CompileCheckMode.LINK

    def get_linker_lib_prefix(self) -> str:
        return ''

    def get_option_link_args(self, target: BuildTarget, subproject: str | None = None) -> list[str]:
        return []

    def has_multi_link_args(self, args: list[str]) -> tuple[bool, bool]:
        return False, False

    def get_link_debugfile_args(self, targetfile: str) -> list[str]:
        return []

    def get_std_shared_lib_link_args(self) -> list[str]:
        return []

    def get_std_shared_module_args(self, options: OptionStore) -> list[str]:
        return self.get_std_shared_lib_link_args()

    def get_link_whole_for(self, args: list[str]) -> list[str]:
        raise EnvironmentException(f'Linker {self.id} does not support link_whole')

    def get_allow_undefined_link_args(self) -> list[str]:
        raise EnvironmentException(f'Linker {self.id} does not support allow undefined')

    def get_pie_link_args(self) -> list[str]:
        raise EnvironmentException(f'Linker {self.id} does not support position-independent executable')

    def get_undefined_link_args(self) -> list[str]:
        return []

    def get_coverage_link_args(self) -> list[str]:
        return []

    def no_undefined_link_args(self) -> list[str]:
        return []

    def bitcode_args(self) -> list[str]:
        raise MesonException("This linker doesn't support bitcode bundles")

    def get_soname_args(self, prefix: str, shlib_name: str,
                        suffix: str, soversion: str,
                        darwin_versions: tuple[str, str]) -> list[str]:
        raise MesonException("This linker doesn't support soname args")

    def build_rpath_args(self, build_dir: str, from_dir: str, target: BuildTarget,
                         extra_paths: list[str] | None = None,
                         ) -> tuple[list[str], set[bytes]]:
        return ([], set())

    def get_asneeded_args(self) -> list[str]:
        return []

    def get_optimization_link_args(self, optimization_level: str) -> list[str]:
        return []

    def get_linker_fatal_warnings(self) -> list[str]:
        return []

    def get_link_debugfile_name(self, targetfile: str) -> str | None:
        return None

    def thread_flags(self) -> list[str]:
        return []

    def thread_link_flags(self) -> list[str]:
        return []
