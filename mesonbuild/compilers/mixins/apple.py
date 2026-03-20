# SPDX-License-Identifier: Apache-2.0
# Copyright 2012-2022 The Meson development team

"""Provides mixins for Apple compilers."""

from __future__ import annotations

import os
import typing as T

from ...mesonlib import MesonException

if T.TYPE_CHECKING:
    from ...environment import Environment
    from ...programs import ExternalProgram
    from ...dependencies import Dependency
    from ...mesonlib import MachineInfo
    Compiler = T.TypeVar('Compiler', bound='Compiler')
else:
    Compiler = object


class AppleCompilerMixin(Compiler):

    """Handle differences between Vanilla Clang and the Clang shipped with XCode."""

    if T.TYPE_CHECKING:
        # Older versions of mypy can't figure this out
        info: MachineInfo

    def _get_brew_prefix(self) -> str:
        """Get the Homebrew prefix based on environment and architecture."""
        # Meson preferred way: check environment first
        brew_prefix = os.environ.get('HOMEBREW_PREFIX')
        if brew_prefix:
            return brew_prefix
        # Fallback to standard locations based on architecture
        if self.info.cpu_family.startswith('x86'):
            return '/usr/local'
        return '/opt/homebrew'

    def openmp_flags(self) -> T.List[str]:
        """Flags required to compile with OpenMP on Apple.

        Apple Clang does not support OpenMP directly.
        Instead, we use the OpenMP implementation from Homebrew.

        :return: A list of arguments
        """
        root = self._get_brew_prefix()
        return self.__BASE_OMP_FLAGS + [f'-I{root}/opt/libomp/include']

    def openmp_link_flags(self) -> T.List[str]:
        root = self._get_brew_prefix()
        link = self.find_library('omp', [f'{root}/opt/libomp/lib'])
        if not link:
            raise MesonException("Couldn't find libomp")
        return link + [f'-L{root}/opt/libomp/lib', '-lomp']

    __BASE_OMP_FLAGS = ['-Xpreprocessor', '-fopenmp']


class AppleCPPStdsMixin(Compiler):

    """Provide version overrides for the Apple C++ Compilers."""

    _CPP23_VERSION = '>=13.0.0'
    _CPP26_VERSION = '>=16.0.0'
