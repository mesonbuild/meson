# SPDX-License-Identifier: Apache-2.0
# Copyright 2016-2017 The Meson development team

from __future__ import annotations

import sysconfig
import typing as T

from .. import mesonlib
from . import ExtensionModule, ModuleInfo
from ..build import SharedModule
from ..interpreter.type_checking import SHARED_MOD_KWS, STR_PARG, SRC_VARG
from ..interpreterbase import TypedArgs
from ..programs import ExternalProgram

if T.TYPE_CHECKING:
    from . import ModuleState
    from ..interpreter.interpreter import BuildTargetSource, Interpreter
    from ..interpreter.kwargs import SharedModule as SharedModuleKW
    from ..interpreterbase import TYPE_var, TYPE_kwargs
    from ..interpreter.type_checking import SourcesVarargsType


_MOD_KWARGS = [k for k in SHARED_MOD_KWS if k.name not in {'name_prefix', 'name_suffix'}]


class Python3Module(ExtensionModule):

    INFO = ModuleInfo('python3', '0.38.0', deprecated='0.48.0')

    def __init__(self, interp: Interpreter):
        super().__init__(interp)
        self.methods.update({
            'extension_module': self.extension_module,
            'find_python': self.find_python,
            'language_version': self.language_version,
            'sysconfig_path': self.sysconfig_path,
        })

    @TypedArgs(
        'python3.extension_module',
        pos_types=[STR_PARG],
        var_types=SRC_VARG,
        kw_types=_MOD_KWARGS,
    )
    def extension_module(self, state: ModuleState, args: T.Tuple[str, T.List[BuildTargetSource]], kwargs: SharedModuleKW) -> SharedModule:
        host_system = state.environment.machines.host.system
        if host_system == 'darwin':
            # Default suffix is 'dylib' but Python does not use it for extensions.
            suffix = 'so'
        elif host_system == 'windows':
            # On Windows the extension is pyd for some unexplainable reason.
            suffix = 'pyd'
        else:
            suffix = None
        kwargs['name_prefix'] = ''
        kwargs['name_suffix'] = suffix
        m = self.interpreter.build_target(
            state.current_node, T.cast('T.Tuple[str, SourcesVarargsType]', args), kwargs, SharedModule)
        assert isinstance(m, SharedModule), 'for mypy'
        return m

    @TypedArgs('python3.find_python')
    def find_python(self, state: ModuleState, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> ExternalProgram:
        command = state.environment.lookup_binary_entry(mesonlib.MachineChoice.HOST, 'python3')
        if command is not None:
            py3 = ExternalProgram.from_entry('python3', command)
        else:
            py3 = ExternalProgram('python3', mesonlib.python_command, silent=True)
        return py3

    @TypedArgs('python3.sysconfig_path')
    def language_version(self, state: ModuleState, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> str:
        return sysconfig.get_python_version()

    @TypedArgs(
        'python3.sysconfig_path',
        pos_types=[STR_PARG],
    )
    def sysconfig_path(self, state: ModuleState, args: T.Tuple[str], kwargs: TYPE_kwargs) -> str:
        path_name = args[0]
        valid_names = sysconfig.get_path_names()
        if path_name not in valid_names:
            raise mesonlib.MesonException(f'{path_name} is not a valid path name {valid_names}.')

        # Get a relative path without a prefix, e.g. lib/python3.6/site-packages
        return sysconfig.get_path(path_name, vars={'base': '', 'platbase': '', 'installed_base': ''})[1:]


def initialize(interp: Interpreter) -> Python3Module:
    return Python3Module(interp)
