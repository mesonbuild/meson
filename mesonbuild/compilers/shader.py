from __future__ import annotations

import typing as T

from .. import coredata

from .compilers import Compiler
from .mixins.islinker import BasicLinkerIsCompilerMixin
from ..mesonlib import EnvironmentException, OptionKey

if T.TYPE_CHECKING:
    from ..envconfig import MachineInfo
    from ..environment import Environment
    from ..mesonlib import MachineChoice
    from ..coredata import KeyedOptionDictType, UserComboOption, MutableKeyedOptionDictType

glslc_optimization_args: T.Dict[str, T.List[str]] = {
    'plain': [],
    '0': ['-O0'],
    'g': ['-O'],
    '1': ['-O'],
    '2': ['-O'],
    '3': ['-O'],
    's': ['-Os'],
}

glslc_buildtype_args: T.Dict[str, T.List[str]] = {
    'plain': [],
    'debug': ['-g'],
    'debugoptimized': ['-g', '-O'],
    'release': ['-O'],
    'minsize': ['-Os'],
    'custom': [],
}


class GlslcCompiler(BasicLinkerIsCompilerMixin, Compiler):
    id = 'glslc'
    language = 'glsl'

    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice, info: 'MachineInfo'):
        super().__init__([], exelist, version, for_machine, info)

    def sanity_check(self, work_dir: str, environment: 'Environment') -> None:
        code = '#version 450\nvoid main() {}'
        with self.cached_compile(code, environment.coredata) as p:
            if p.returncode != 0:
                raise EnvironmentException(f'Cython compiler {self.id!r} cannot compile programs')

    def compute_parameters_with_absolute_paths(self, parameter_list: T.List[str],
                                               build_dir: str) -> T.List[str]:
        return parameter_list

    def needs_static_linker(self) -> bool:
        return False

    def get_output_args(self, outputname: str) -> T.List[str]:
        return ['-o', outputname]

    def get_optimization_args(self, optimization_level: str) -> T.List[str]:
        return glslc_optimization_args[optimization_level]

    def get_buildtype_args(self, buildtype: str) -> T.List[str]:
        return glslc_buildtype_args[buildtype]

    def get_debug_args(self, is_debug: bool) -> T.List[str]:
        if is_debug:
            return ['-g']
        return []

    def get_no_optimization_args(self) -> T.List[str]:
        return ['-O0']

    def get_werror_args(self) -> T.List[str]:
        return ['-Werror']

    def get_no_warn_args(self) -> T.List[str]:
        return ['-w']

    def get_preprocess_only_args(self) -> T.List[str]:
        return ['-E']

    def get_compile_only_args(self) -> T.List[str]:
        return ['-c']

    def get_include_args(self, path: str, is_system: bool) -> T.List[str]:
        return ['-I', path]

    def get_depfile_suffix(self) -> str:
        return ''

    def get_options(self) -> 'MutableKeyedOptionDictType':
        opts = super().get_options()
        target_env_key = OptionKey('target_env', lang=self.language)
        target_spv_key = OptionKey('target_spv', lang=self.language)
        std_key = OptionKey('std', lang=self.language)
        target_env_choices = ['', 'vulkan', 'vulkan1.0', 'vulkan1.1', 'vulkan1.2', 'vulkan1.3', 'opengl',
                              'opengl4.5']
        target_spv_choices = ['', 'spv1.0', 'spv1.1', 'spv1.2', 'spv1.3', 'spv1.4', 'spv1.5', 'spv1.6']
        std_choices = ['', '150core', '150es', '150compatibility', '330core', '330es', '330compatibility',
                       '400core', '400es', '400compatibility', '410core', '410es', '410compatibility',
                       '420core', '420es', '420compatibility', '430core', '430es', '430compatibility',
                       '440core', '440es', '440compatibility', '450core', '450es', '450compatibility',
                       '460core', '460es', '460compatibility']
        opts.update({
            target_env_key: coredata.UserComboOption('Target execution environment for GLSL shaders',
                                                     target_env_choices, ''),
            target_spv_key: coredata.UserComboOption('SPIR-V output version for GLSL shaders', target_spv_choices, ''),
            std_key: coredata.UserComboOption('Version and profile for GLSL shaders', std_choices, ''),
        })
        return opts

    def get_option_compile_args(self, options: 'KeyedOptionDictType') -> T.List[str]:
        target_env_key = OptionKey('target_env', lang=self.language)
        target_spv_key = OptionKey('target_spv', lang=self.language)
        std_key = OptionKey('std', lang=self.language)

        target_env = options[target_env_key].value
        target_spv = options[target_spv_key].value
        std = options[std_key].value

        args = []

        if isinstance(target_env, str) and target_env != '':
            args.append(f'--target-env={target_env}')
        if isinstance(target_spv, str) and target_spv != '':
            args.append(f'--target-spv={target_spv}')
        if isinstance(std, str) and std != '':
            args.append(f'--std={std}')

        return args
