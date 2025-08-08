# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Red Hat, Inc

from __future__ import annotations

import os
import glob
import re
import typing as T

from . import ExtensionModule, ModuleReturnValue, ModuleInfo
from .. import mesonlib
from .. import build
from .. import programs
from ..build import CustomTarget
from ..interpreter import Interpreter
from ..interpreterbase.decorators import typed_kwargs, typed_pos_args
from ..interpreter.type_checking import NoneType
from ..mesonlib import File, MesonException
from ..programs import ExternalProgram
from ..interpreterbase.decorators import KwargInfo

if T.TYPE_CHECKING:
    from ..interpreterbase import TYPE_kwargs, TYPE_var
    from . import ModuleState

class SELinuxModule(ExtensionModule):
    INFO = ModuleInfo('selinux', '1.9.0')

    def __init__(self, interpreter: Interpreter) -> None:
        super().__init__(interpreter)
        self.methods.update({
            'found': self.found_method,
            'package': self.package,
        })
        self._tools: T.Optional[T.Dict[str, ExternalProgram]] = None

    def _find_tools(self, state: ModuleState) -> T.Dict[str, ExternalProgram]:
        if self._tools is None:
            self._tools = {
                'm4': T.cast(ExternalProgram, state.find_program('m4', required=False)),
                'checkmodule': T.cast(ExternalProgram, state.find_program('checkmodule', required=False)),
                'semodule_package': T.cast(ExternalProgram, state.find_program('semodule_package', required=False)),
            }
        return self._tools

    def found_method(self, state: ModuleState, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> bool:
        return all(t.found() for t in self._find_tools(state).values() if t)

    def _ensure_file(self, state: ModuleState, file: T.Union[str, File], default_content: T.Optional[str] = None) -> T.Union[File, build.CustomTarget]:
        sourcedir = state.environment.get_source_dir()
        subdir = state.subdir

        if isinstance(file, str):
            if os.path.exists(os.path.join(state.environment.source_dir, subdir, file)) or default_content is None:
                return File.from_source_file(sourcedir, subdir, file)

            if default_content:
                py_cmd = f"with open('@OUTPUT@', 'w') as f: f.write('{default_content}')"
                desc = f"Creating file {file} with content"
            else:
                py_cmd = "open('@OUTPUT@', 'a').close()"
                desc = f"Creating empty file {file}"

            python = T.cast(ExternalProgram, state.find_program('python3', required=True))
            cmd: T.List[T.Union[str, File, ExternalProgram]] = [python, '-c', py_cmd]
            target = build.CustomTarget(
                file,
                state.subdir,
                state.subproject,
                state.environment,
                cmd,
                [],
                [file],
                description=desc,
            )
            return target
        else:
            return file

    @typed_pos_args('selinux.package', str)
    @typed_kwargs(
        'selinux.package',
        KwargInfo('te_file', (str, File, NoneType)),
        KwargInfo('if_file', (str, File, NoneType)),
        KwargInfo('fc_file', (str, File, NoneType)),
        KwargInfo('install', bool, default=True),
        KwargInfo('install_dir', (str, NoneType)),
        KwargInfo('name', (str, NoneType)),
        KwargInfo('mls', bool, default=True),
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
        te_file = self._ensure_file(state, T.cast(T.Union[str, File], kwargs.get('te_file') or f'{package_name}.te'))
        if_file = self._ensure_file(
            state, T.cast(T.Union[str, File], kwargs.get('if_file') or f'{package_name}.if'),
            default_content=f"## <summary>{package_name}</summary>\n")
        fc_file = self._ensure_file(
            state, T.cast(T.Union[str, File], kwargs.get('fc_file') or f'{package_name}.fc'),
            default_content='')
        install = T.cast(bool, kwargs['install'])
        install_dir = T.cast(T.Optional[str], kwargs.get('install_dir'))
        if install and install_dir is None:
            install_dir = os.path.join(sharedir, 'packages')

        # mimic '/usr/share/selinux/devel/Makefile' behaviour
        name = T.cast(T.Optional[str], kwargs.get('name'))
        if name is None:
            config = '/etc/selinux/config'
            try:
                with open(config, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('SELINUXTYPE='):
                            name = line.split('=', 1)[1].strip().strip('"\'')
                            break
            except (IOError, OSError) as e:
                raise MesonException(f'Failed to read "{config}": {e}')

        mls = T.cast(bool, kwargs.get('mls'))
        type = T.cast(T.Optional[str], kwargs['type'])
        if type is None:
            if name == 'mls':
                type = 'mls'
            elif mls:
                type = 'mcs'

        distro = T.cast(T.Optional[str], kwargs['distro'])
        direct_initrc = T.cast(T.Optional[bool], kwargs['direct_initrc'])

        headerdir = os.path.join(sharedir, 'devel', 'include')
        # fallback to system default
        if not os.path.exists(headerdir):
            headerdir = '/usr/share/selinux/devel/include'
        build_conf = os.path.join(headerdir, 'build.conf')

        try:
            with open(build_conf, 'r', encoding='utf-8') as f:
                build_vars: T.Dict[str, str] = {}
                build_vars = {k: v for k, v in {
                    'TYPE': type,
                    'NAME': name,
                    'DISTRO': distro,
                    'DIRECT_INITRC': 'y' if direct_initrc else 'n'
                }.items() if v is not None}
                build_vars = parse_makefile_variables(f.read(), build_vars)

                type = build_vars.get('TYPE', 'standard')
                name = build_vars['NAME']
                distro = build_vars['DISTRO']
                direct_initrc = build_vars.get('DIRECT_INITRC', 'n') == 'y'
                ubac = build_vars.get('UBAC', 'n') == 'y'
                mls_sens = build_vars.get('MLS_SENS', '16')
                mls_cats = build_vars.get('MLS_CATS', '1024')
                mcs_cats = build_vars.get('MCS_CATS', '1024')
        except (IOError, OSError) as e:
            raise MesonException(f'Failed to read "{build_conf}": {e}')

        m4 = tools['m4']
        checkmodule = tools['checkmodule']
        semodule_package = tools['semodule_package']

        m4_args: T.List[str] = []
        if type == 'mls':
            m4_args.extend(['-D', 'enable_mls'])
        elif type == 'mcs':
            m4_args.extend(['-D', 'enable_mcs'])
        if distro:
            m4_args.extend(['-D', f'distro_{distro}'])
        if direct_initrc:
            m4_args.extend(['-D', 'direct_sysadm_daemon'])
        if ubac:
            m4_args.extend(['-D', 'enable_ubac'])

        m4_args.extend(['-D', 'hide_broken_symptoms'])
        m4_args.extend(['-D', f'mls_num_sens={mls_sens}'])
        m4_args.extend(['-D', f'mls_num_cats={mls_cats}'])
        m4_args.extend(['-D', f'mcs_num_cats={mcs_cats}'])

        # gather the support files
        m4supportdir = os.path.join(headerdir, 'support')
        m4support = glob.glob(os.path.join(m4supportdir, '*.spt'))

        # gather all the {headerdir}/*/*.if files, except if the subdir is 'support'
        header_ifaces = []
        for item in os.listdir(headerdir):
            subdir_path = os.path.join(headerdir, item)
            if os.path.isdir(subdir_path) and item != 'support':
                for file in os.listdir(subdir_path):
                    if file.endswith('.if'):
                        header_ifaces.append(os.path.join(subdir_path, file))

        all_ifaces_conf = f'{package_name}_all_interfaces.conf' # we may want a temporary file instead?
        all_ifaces_cmd: T.List[T.Union[str, build.BuildTarget, build.CustomTarget,
                                       build.CustomTargetIndex, ExternalProgram, mesonlib.File]] = []
        all_ifaces_cmd.extend(state.environment.get_build_command())
        all_ifaces_cmd.extend([
            '--internal', 'selinux', 'all-ifaces',
            '-i', '@INPUT@',
            '-o', '@OUTPUT@'
        ])
        all_ifaces_inputs = m4support + header_ifaces + [if_file]
        all_ifaces = build.CustomTarget(
            all_ifaces_conf,
            state.subdir,
            state.subproject,
            state.environment,
            all_ifaces_cmd,
            all_ifaces_inputs,
            [all_ifaces_conf],
            description='Generating all interfaces for SELinux policy'
        )

        te_processed_name = f'{package_name}.te.pre'
        te_inputs: T.List[T.Union[str, File, CustomTarget]] = []
        te_inputs.extend(m4support)
        te_inputs.extend([all_ifaces, te_file])
        te_cmd: T.List[T.Union[ExternalProgram, str]] = [m4]
        te_cmd.extend(m4_args)
        te_cmd.extend(['-s', '@INPUT@'])
        te_target = build.CustomTarget(
            te_processed_name,
            state.subdir,
            state.subproject,
            state.environment,
            te_cmd,
            te_inputs,
            [te_processed_name],
            capture=True,
            description=f'Preprocessing {te_file.fname if isinstance(te_file, File) else te_file.name}',
        )

        mod_fc_name = f'{package_name}.mod.fc'
        mod_fc_inputs = m4support + [fc_file]
        mod_fc_cmd: T.List[T.Union[ExternalProgram, str]] = [m4]
        mod_fc_cmd.extend(m4_args)
        mod_fc_cmd.extend(['@INPUT@'])
        mod_fc_target = build.CustomTarget(
            mod_fc_name,
            state.subdir,
            state.subproject,
            state.environment,
            mod_fc_cmd,
            mod_fc_inputs,
            [mod_fc_name],
            capture=True,
            description=f'Preprocessing {mod_fc_name}',
        )

        mod_name = f'{package_name}.mod'
        mod_cmd: T.List[T.Union[programs.ExternalProgram, str]] = [checkmodule]
        if type in {'mls', 'mcs'}:
            mod_cmd.append('-M')
        mod_cmd.extend(['-m', '@INPUT@', '-o', '@OUTPUT@'])
        mod_target = build.CustomTarget(
            mod_name,
            state.subdir,
            state.subproject,
            state.environment,
            mod_cmd,
            [te_target],
            [mod_name],
            description=f'Compiling {mod_name} module',
        )

        pp_name = f'{package_name}.pp'
        pp_cmd: T.List[T.Union[programs.ExternalProgram, str, build.CustomTarget, File]] = [semodule_package]
        pp_cmd.extend(['-o', '@OUTPUT@', '-m', mod_target, '-f', mod_fc_target])
        pp_target = build.CustomTarget(
            pp_name,
            state.subdir,
            state.subproject,
            state.environment,
            pp_cmd,
            [mod_target, fc_file],
            [pp_name],
            install=install,
            install_dir=[install_dir] if install_dir else [],
            description=f'Creating {pp_name}',
        )

        targets = [all_ifaces, pp_target, mod_target, te_target, mod_fc_target]
        if isinstance(if_file, build.CustomTarget):
            targets.append(if_file)
        if isinstance(fc_file, build.CustomTarget):
            targets.append(fc_file)
        return ModuleReturnValue(pp_target, targets)


def parse_makefile_variables(content: str, variables: T.Optional[T.Dict[str, str]] = None) -> T.Dict[str, str]:
    """
    Parses a Makefile to extract variable assignments.

    This function reads a file line by line and uses a regular expression
    to find variable declarations. It correctly interprets the logic for
    standard (`=`, `:=`), conditional (`?=`), and override assignments.

    Args:
        file_path (str): The path to the Makefile or file with variables.

    Returns:
        dict: A dictionary containing the parsed variable names and their values.
    """
    if variables is None:
        variables = {}

    # Regex to capture the variable name, assignment operator, and value.
    # It correctly handles optional 'override', different operators,
    # and strips trailing whitespace and comments.
    var_regex = re.compile(
        r"^\s*(?:override\s+)?(?P<name>[a-zA-Z0-9_-]+)\s*(?P<operator>[:?]?=)\s*(?P<value>.*?)\s*(?:#.*)?$"
    )

    for line in content.splitlines():
        match = var_regex.match(line)
        if match:
            data = match.groupdict()
            name = data['name']
            operator = data['operator']
            value = data['value'].strip()

            # For conditional assignment ('?='), only set the variable
            # if it has not been defined yet.
            if operator == '?=':
                if name not in variables:
                    variables[name] = value
            # For regular ('=') and simple (':=') assignments,
            # set or overwrite the variable.
            else:
                variables[name] = value
    return variables


def initialize(interpreter: Interpreter) -> SELinuxModule:
    return SELinuxModule(interpreter)
