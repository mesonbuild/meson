# Copyright 2022 Mark Bolhuis <mark@bolhuis.dev>

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from . import ExtensionModule, ModuleReturnValue
from ..build import CustomTarget
from ..interpreter.type_checking import NoneType, in_set_validator
from ..interpreterbase import FeatureNew, typed_pos_args, typed_kwargs, KwargInfo
from ..mesonlib import File, MesonException, MachineChoice


class WaylandModule(ExtensionModule):

    @FeatureNew('wayland module', '0.62.0')
    def __init__(self, interpreter):
        super().__init__(interpreter)

        self.protocols_dep = None
        self.pkgdatadir = None
        self.scanner_bin = None

        self.methods.update({
            'scan_xml': self.scan_xml,
            'find_protocol': self.find_protocol,
        })

    @typed_pos_args('wayland.scan_xml', varargs=(str, File), min_varargs=1)
    @typed_kwargs(
        'wayland.scan_xml',
        KwargInfo('public', bool, default=False),
        KwargInfo('client', bool, default=True),
        KwargInfo('server', bool, default=False),
    )
    def scan_xml(self, state, args, kwargs):
        if self.scanner_bin is None:
            # wayland-scanner from BUILD machine must have same version as wayland
            # libraries from HOST machine.
            dep = self.interpreter.func_dependency(state.current_node, ['wayland-client'], {})
            self.scanner_bin = state.find_program('wayland-scanner',
                                                  for_machine=MachineChoice.BUILD,
                                                  wanted=dep.version)

        scope = 'public' if kwargs['public'] else 'private'
        sides = [i for i in ['client', 'server'] if kwargs[i]]
        if not sides:
            raise MesonException('At least one of client or server keyword argument must be set to true.')

        xml_files = self.interpreter.source_strings_to_files(args[0])
        targets = []
        for xml_file in xml_files:
            name = os.path.splitext(os.path.basename(xml_file.fname))[0]

            code = CustomTarget(
                f'{name}-protocol',
                state.subdir,
                state.subproject,
                [self.scanner_bin, f'{scope}-code', '@INPUT@', '@OUTPUT@'],
                [xml_file],
                [f'{name}-protocol.c'],
                backend=state.backend,
            )
            targets.append(code)

            for side in sides:
                header = CustomTarget(
                    f'{name}-{side}-protocol',
                    state.subdir,
                    state.subproject,
                    [self.scanner_bin, f'{side}-header', '@INPUT@', '@OUTPUT@'],
                    [xml_file],
                    [f'{name}-{side}-protocol.h'],
                    backend=state.backend,
                )
                targets.append(header)

        return ModuleReturnValue(targets, targets)

    @typed_pos_args('wayland.find_protocol', str)
    @typed_kwargs(
        'wayland.find_protocol',
        KwargInfo('state', str, default='stable', validator=in_set_validator({'stable', 'staging', 'unstable'})),
        KwargInfo('version', (int, NoneType)),
    )
    def find_protocol(self, state, args, kwargs):
        base_name = args[0]
        xml_state = kwargs['state']
        version = kwargs['version']

        if xml_state != 'stable' and version is None:
            raise MesonException(f'{xml_state} protocols require a version number.')

        if xml_state == 'stable' and version is not None:
            raise MesonException('stable protocols do not require a version number.')

        if self.protocols_dep is None:
            self.protocols_dep = self.interpreter.func_dependency(state.current_node, ['wayland-protocols'], {})

        if self.pkgdatadir is None:
            self.pkgdatadir = self.protocols_dep.get_variable(pkgconfig='pkgdatadir', internal='pkgdatadir')

        if xml_state == 'stable':
            xml_name = f'{base_name}.xml'
        elif xml_state == 'staging':
            xml_name = f'{base_name}-v{version}.xml'
        else:
            xml_name = f'{base_name}-unstable-v{version}.xml'

        path = os.path.join(self.pkgdatadir, xml_state, base_name, xml_name)

        if not os.path.exists(path):
            raise MesonException(f'The file {path} does not exist.')

        return File.from_absolute_file(path)


def initialize(interpreter):
    return WaylandModule(interpreter)
