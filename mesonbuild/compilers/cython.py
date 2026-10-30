# SPDX-License-Identifier: Apache-2.0
# Copyright © 2021-2025 Intel Corporation

"""Abstraction for Cython language compilers."""

from __future__ import annotations
import os
import typing as T

from .. import options
from .. import mlog
from ..mesonlib import version_compare, EnvironmentException, late_property
from .compilers import CompileCheckMode, Compiler

if T.TYPE_CHECKING:
    from ..dependencies import Dependency
    from ..options import MutableKeyedOptionDictType
    from ..build import BuildTarget


class CythonCompiler(Compiler):

    """Cython Compiler."""

    language = 'cython'
    id = 'cython'

    dep: late_property[Dependency] = late_property()

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

    def _sanity_check_filenames(self) -> T.Tuple[str, T.Optional[str], str]:
        sourcename, _, binname = super()._sanity_check_filenames()

        lang = self.get_compileropt_value('language', None)
        assert isinstance(lang, str)

        # This is almost certainly not good enough
        ext = 'dll' if self.environment.machines[self.for_machine].is_windows() else 'so'

        return (sourcename, f'{os.path.splitext(sourcename)[0]}.{lang}',
                f'{os.path.splitext(binname)[0]}.{ext}')

    def sanity_check(self, work_dir: str) -> None:
        version = self.get_compileropt_value('version', None)
        assert isinstance(version, str)

        from ..dependencies import find_external_dependency
        with mlog.no_logging():
            # if the dependency is not found, go on with the sanity check
            # and report its failure
            self.dep = find_external_dependency(
                f'python{version}', self.environment, {'required': False, 'native': self.for_machine})
        super().sanity_check(work_dir)

    def _transpiled_sanity_check_compile_args(
            self, compiler: Compiler, sourcename: str, binname: str
            ) -> T.Tuple[T.List[str], T.List[str]]:
        args, largs = super()._transpiled_sanity_check_compile_args(compiler, sourcename, binname)
        args.extend(compiler.get_pic_args())
        largs.extend(compiler.get_std_shared_lib_link_args())
        largs.extend(compiler.get_allow_undefined_link_args())

        if self.dep.found():
            args.extend(self.dep.get_all_compile_args())
            largs.extend(self.dep.get_all_link_args())
        return args, largs

    def _sanity_check_mode(self) -> CompileCheckMode:
        # the sanity check only transpiles, the generated source is compiled
        # and linked by _transpiled_sanity_check_compile_args()
        return CompileCheckMode.COMPILE

    def _sanity_check_compile_args(self, sourcename: str, binname: str
                                   ) -> T.Tuple[T.List[str], T.List[str]]:
        args, largs = super()._sanity_check_compile_args(sourcename, binname)
        args.extend(self.get_option_compile_args(None))
        return args, largs

    def _sanity_check_source_code(self) -> str:
        return 'def func():\n    print("Hello world")'

    def _compile_sanity_check(self, cmdlist: T.List[str], linker_args: T.List[str],
                              work_dir: str) -> None:
        # A Cython project can target any Python installation, and the sanity
        # check cannot know which one.  Failing to build the transpiled source
        # against the default Python is therefore advisory only.
        try:
            super()._compile_sanity_check(cmdlist, linker_args, work_dir)
        except EnvironmentException:
            if self.dep.found():
                msg = f'The C or C++ compiler for the {self.for_machine} failed to build the\n' \
                      'transpiled code for the Cython sanity check.'
            else:
                msg = 'Cython requires the python3 dependency for link testing, but it could\n' \
                      'not be found.'
            mlog.warning(f'{msg}\n\n'
                         'Cython can be used with more than one Python installation, so Meson cannot\n'
                         'tell whether this failure affects your project.  Setup will continue;\n'
                         'if the build fails, make sure that Meson finds the desired Python\n'
                         "installation's development files (for example, with pkg-config) and that\n"
                         'they are usable. The error in meson-logs/meson-log.txt can help diagnosing\n'
                         'the issue.',
                         once=True, fatal=False)

    def _run_sanity_check(self, cmdlist: T.List[str], work_dir: str) -> None:
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

    def get_option_compile_args(self, target: 'BuildTarget', subproject: T.Optional[str] = None) -> T.List[str]:
        args: T.List[str] = []
        version = self.get_compileropt_value('version', target, subproject)
        assert isinstance(version, str)
        args.append(f'-{version}')

        lang = self.get_compileropt_value('language', target, subproject)
        assert isinstance(lang, str)
        if lang == 'cpp':
            args.append('--cplus')
        return args
