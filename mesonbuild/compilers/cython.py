# SPDX-License-Identifier: Apache-2.0
# Copyright © 2021-2025 Intel Corporation

"""Abstraction for Cython language compilers."""

from __future__ import annotations
import os
import typing as T

from .. import options
from ..mesonlib import version_compare
from .compilers import Compiler

if T.TYPE_CHECKING:
    from ..options import MutableKeyedOptionDictType
    from ..environment import Environment
    from ..build import BuildTarget


class CythonCompiler(Compiler):

    """Cython Compiler."""

    language = 'cython'
    id = 'cython'

    def needs_static_linker(self) -> bool:
        # We transpile into C, so we don't need any linker
        return False

    def get_always_args(self) -> T.List[str]:
        return ['--fast-fail']

    def get_werror_args(self) -> T.List[str]:
        return ['-Werror']

    def get_output_args(self, outputname: str) -> T.List[str]:
        return ['-o', outputname]

    def get_optimization_args(self, optimization_level: str) -> T.List[str]:
        # Cython doesn't have optimization levels itself, the underlying
        # compiler might though
        return []

    def get_dependency_gen_args(self, outtarget: str, outfile: str) -> T.List[str]:
        if version_compare(self.version, '>=0.29.33'):
            return ['-M']
        return []

    def get_depfile_suffix(self) -> str:
        return 'dep'

    def get_pic_args(self) -> T.List[str]:
        # We can lie here, it's fine
        return []

    def _sanity_check_source_code(self) -> str:
        return 'print("Hello world")'

    def _sanity_check_compile_args(self, env: Environment, sourcename: str, binname: str) -> T.List[str]:
        return self.exelist + self.get_always_args() + self.get_output_args(binname) + [sourcename]

    def _run_sanity_check(self, env: Environment, cmdlist: T.List[str], work_dir: str) -> None:
        # Cython will do a Cython -> C -> Exe, so the output file will actually have
        # the name of the C compiler.
        # TODO: find a way to not make this so hacky
        return super()._run_sanity_check(env, [os.path.join(work_dir, 'sanity_check_for_c.exe')], work_dir)

    def compute_parameters_with_absolute_paths(self, parameter_list: T.List[str],
                                               build_dir: str) -> T.List[str]:
        new: T.List[str] = []
        for i in parameter_list:
            new.append(i)

        return new

    def get_options(self) -> 'MutableKeyedOptionDictType':
        opts = super().get_options()

        key = self.form_compileropt_key('version')
        opts[key] = options.UserComboOption(
            self.make_option_name(key),
            'Python version to target',
            '3',
            choices=['2', '3'])

        key = self.form_compileropt_key('language')
        opts[key] = options.UserComboOption(
            self.make_option_name(key),
            'Output C or C++ files',
            'c',
            choices=['c', 'cpp'])

        return opts

    def get_option_compile_args(self, target: 'BuildTarget', env: 'Environment', subproject: T.Optional[str] = None) -> T.List[str]:
        args: T.List[str] = []
        version = self.get_compileropt_value('version', env, target, subproject)
        assert isinstance(version, str)
        args.append(f'-{version}')

        lang = self.get_compileropt_value('language', env, target, subproject)
        assert isinstance(lang, str)
        if lang == 'cpp':
            args.append('--cplus')
        return args
