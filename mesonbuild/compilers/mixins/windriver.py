# SPDX-License-Identifier: Apache-2.0
# Copyright 2012-2023 The Meson development team
from __future__ import annotations
from abc import abstractmethod, ABC

from mesonbuild.utils.core import MesonException

import os
import typing as T

if T.TYPE_CHECKING:
    from ...compilers.compilers import Compiler
    from ...options import MutableKeyedOptionDictType
    from ...build import BuildTarget
else:
    # This is a bit clever, for mypy we pretend that these mixins descend from
    # Compiler, so we get all of the methods and attributes defined for us, but
    # for runtime we make them descend from object (which all classes normally
    # do). This gives us DRYer type checking, with no runtime impact
    Compiler = ABC

class DiabCompilerMixin(Compiler):
    """The Wind River Diab compiler suite for bare-metal PowerPC

    This is a mixin for the C++ and C compilers.
    It should have a DiabLinker instance in its `linker` member.

    Archiving can be done with DiabArchiver.
    """
    id = 'diab'

    optimization_args: T.Dict[str, T.List[str]] = {
        'plain': [],
        '0': [],
        'g': ['-O', '-Xno-optimized-debug'],
        '1': ['-O'],
        '2': ['-O', '-Xinline=40'],
        '3': ['-XO'],
        's': ['-Xsize-opt'],
    }
    
    @property
    @abstractmethod
    def std_args(self) -> T.Dict[str, T.List[str]]: ...

    def get_options(self) -> 'MutableKeyedOptionDictType':
        opts = super().get_options()
        self._update_language_stds(opts, list(self.std_args))
        return opts

    def get_warn_args(self, level: str) -> T.List[str]:
        """No such levels"""
        return []

    def get_werror_args(self) -> T.List[str]:
        return ['-Xstop-on-warning']

    def get_optimization_args(self, optimization_level: str) -> T.List[str]:
        return self.optimization_args[optimization_level]

    def get_option_std_args(self, target: BuildTarget, subproject: T.Optional[str] = None) -> T.List[str]:
        std = self.get_compileropt_value('std', target, subproject)
        assert isinstance(std, str)
        return self.std_args.get(std, [])

    def get_debug_args(self, is_debug: bool) -> T.List[str]:
        return ['-g'] if is_debug else []

    def compute_parameters_with_absolute_paths(self, parameter_list: T.List[str], build_dir: str) -> T.List[str]:
        for idx, i in enumerate(parameter_list):
            if i.startswith(('-I', '-L')):
                parameter_list[idx] = i[:2] + os.path.normpath(os.path.join(build_dir, i[2:]))

        return parameter_list

    def get_always_args(self) -> T.List[str]:
        """Disable super's large-file-support"""
        return []

    def get_pic_args(self) -> T.List[str]:
        raise MesonException('Compiler support for PIC not implemented')

    def get_dependency_gen_args(self, outtarget: str, outfile: str) -> T.List[str]:
        return ['-Xmake-dependency=4', f'-Xmake-dependency-savefile={outfile}']
