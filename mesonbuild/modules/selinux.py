# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Red Hat, Inc

from __future__ import annotations

import os
import typing as T

from . import ExtensionModule, ModuleReturnValue, ModuleInfo
from .. import mesonlib
from .. import build
from ..interpreter import Interpreter
from ..interpreterbase.decorators import typed_kwargs, typed_pos_args
from ..interpreter.type_checking import NoneType
from ..mesonlib import File, MesonException, EnvironmentVariables
from ..programs import ExternalProgram
from ..interpreterbase.decorators import KwargInfo
from mesonbuild.programs import OverrideProgram

if T.TYPE_CHECKING:
    from ..interpreterbase import TYPE_kwargs, TYPE_var
    from . import ModuleState

    PROG = T.Union[ExternalProgram, build.OverrideExecutable, OverrideProgram]

class SELinuxModule(ExtensionModule):
    INFO = ModuleInfo('selinux', '1.9.0')

    def __init__(self, interpreter: Interpreter) -> None:
        super().__init__(interpreter)
        self.methods.update({
            'found': self.found_method,
            'package': self.package,
        })
        self._tools: T.Optional[T.Dict[str, PROG]] = None

    def _find_tools(self, state: ModuleState) -> T.Dict[str, PROG]:
        if self._tools is None:
            self._tools = {
                'm4': state.find_program('m4', required=False),
                'checkmodule': state.find_program('checkmodule', required=False),
                'semodule_package': state.find_program('semodule_package', required=False),
            }
        return self._tools

    def found_method(self, state: ModuleState, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> bool:
        return all(t.found() for t in self._find_tools(state).values() if t)

    @typed_pos_args('selinux.package', str)
    @typed_kwargs(
        'selinux.package',
        KwargInfo('te_file', (str, File, NoneType), required=True),
        KwargInfo('if_file', (str, File, NoneType)),
        KwargInfo('fc_file', (str, File, NoneType)),
        KwargInfo('install', bool, default=True),
        KwargInfo('install_dir', (str, NoneType)),
        KwargInfo('name', (str, NoneType)),
        KwargInfo('mls', bool, default=False),
        KwargInfo('type', (str, NoneType)),
        KwargInfo('distro', (str, NoneType)),
        KwargInfo('direct_initrc', (bool, NoneType)),
    )
    def package(self, state: ModuleState, args: T.Tuple[str], kwargs: TYPE_kwargs) -> ModuleReturnValue:
        sharedir = os.path.join(state.environment.get_prefix(), state.environment.get_datadir(), 'selinux')
        tools = self._find_tools(state)
        for tool_name, tool in tools.items():
            if not tool or not tool.found():
                raise MesonException(f'SELinux tool {tool_name} not found')

        package_name = args[0]
        ppfile = args[0] + '.pp'
        depfile = args[0] + '.d'

        te_file = T.cast(T.Optional[T.Union[str, mesonlib.File]], kwargs.get('te_file'))
        te_file = self._resolve_file_path(state, te_file)
        if_file = T.cast(T.Optional[T.Union[str, mesonlib.File]], kwargs.get('if_file'))
        if_file = self._resolve_file_path(state, if_file)
        fc_file = T.cast(T.Optional[T.Union[str, mesonlib.File]], kwargs.get('fc_file'))
        fc_file = self._resolve_file_path(state, fc_file)

        install = T.cast(bool, kwargs['install'])
        install_dir = T.cast(T.Optional[str], kwargs.get('install_dir'))
        if install and install_dir is None:
            install_dir = os.path.join(sharedir, 'packages')

        name = T.cast(T.Optional[str], kwargs['name'])
        mls = T.cast(bool, kwargs.get('mls'))
        type = T.cast(T.Optional[str], kwargs['type'])
        distro = T.cast(T.Optional[str], kwargs['distro'])
        direct_initrc = T.cast(T.Optional[bool], kwargs['direct_initrc'])

        pp_cmd: T.List[T.Union[str, build.BuildTarget, build.CustomTarget,
                               build.CustomTargetIndex, ExternalProgram, mesonlib.File]] = []
        pp_cmd.extend(state.environment.get_build_command())
        pp_cmd.extend([
            '--internal', 'selinux',
            '--quiet',
            '--output', '@OUTPUT@',
            '--depfile', '@DEPFILE@',
            '--private-dir', '@PRIVATE_DIR@',
            '--te', te_file,
        ])
        if if_file:
            pp_cmd.extend(['--if', if_file])
        if fc_file:
            pp_cmd.extend(['--fc', fc_file])
        if name:
            pp_cmd.extend(['--name', name])
        if mls:
            pp_cmd.extend(['--mls'])
        if type:
            pp_cmd.extend(['--type', type])
        if distro:
            pp_cmd.extend(['--distro', distro])
        if direct_initrc:
            pp_cmd.extend(['--direct-initrc'])

        env = EnvironmentVariables()
        env.set('M4', [tools['m4'].get_path()])
        env.set('CHECKMODULE', [tools['checkmodule'].get_path()])
        env.set('SEMOD_PKG', [tools['semodule_package'].get_path()])

        pp_target = build.CustomTarget(
            package_name,
            state.subdir,
            state.subproject,
            state.environment,
            pp_cmd,
            [],
            [ppfile],
            env=env,
            install=install,
            install_dir=[install_dir] if install_dir else [],
            depfile=depfile,
            description='Building SELinux policy {}'
        )
        return ModuleReturnValue(pp_target, [pp_target])

    def _resolve_file_path(self, state: ModuleState, file_arg: T.Optional[T.Union[str, mesonlib.File]]) -> T.Optional[str]:
        if file_arg is None:
            return None
        if isinstance(file_arg, mesonlib.File):
            return file_arg.absolute_path(state.environment.get_source_dir(), state.environment.get_build_dir())
        else:
            return os.path.join(state.environment.get_source_dir(), state.subdir, file_arg)


def initialize(interpreter: Interpreter) -> SELinuxModule:
    return SELinuxModule(interpreter)
