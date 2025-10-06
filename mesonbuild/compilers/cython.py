# SPDX-License-Identifier: Apache-2.0
# Copyright © 2021-2025 Intel Corporation

"""Abstraction for Cython language compilers."""

from __future__ import annotations
import os
import typing as T

from .. import options
from .. import mlog
from ..mesonlib import version_compare, EnvironmentException
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

    def _sanity_check_filenames(self, env: Environment) -> T.Tuple[str, T.Optional[str], str]:
        sourcename, _, binname = super()._sanity_check_filenames(env)

        lang = self.get_compileropt_value('language', env, None)
        assert isinstance(lang, str)

        # This is almost certainly not good enough
        ext = 'dll' if env.machines[self.for_machine].is_windows() else 'so'

        return (sourcename, f'{os.path.splitext(sourcename)}.{lang}',
                f'{os.path.splitext(binname)}.{ext}')

    def _transpiled_sanity_check_compile_args(self, compiler: Compiler, env: Environment, sourcename: str, binname: str) -> T.List[str]:
        args = super()._transpiled_sanity_check_compile_args(compiler, env, sourcename, binname)
        args.extend(compiler.get_std_shared_lib_link_args())
        args.extend(compiler.get_allow_undefined_link_args())
        args.extend(compiler.get_pic_args())

        version = self.get_compileropt_value('version', env, None)
        assert isinstance(version, str)

        from ..dependencies import find_external_dependency
        with mlog.no_logging():
            dep = find_external_dependency(f'python{version}', env, {'required': False})
        if not dep.found():
            raise EnvironmentException(
                'Cython requires python3 dependency for link testing, but it could not be found')

        args.extend(dep.get_all_compile_args())
        return args

    def _sanity_check_compile_args(self, env: Environment, sourcename: str, binname: str) -> T.List[str]:
        return super()._sanity_check_compile_args(env, sourcename, binname) + \
            self.get_option_compile_args(None, env)

    def _sanity_check_source_code(self) -> str:
        return 'def func():\n    print("Hello world")'

    def _run_sanity_check(self, env: Environment, cmdlist: T.List[str], work_dir: str) -> None:
        # XXX: this is a punt
        # This means we transpile the Cython .pyx file into C or C++, and we
        # link it, but we don't actually attempt to run it.
        return

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
