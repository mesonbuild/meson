# Copyright © 2020 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import typing as T
from pathlib import PurePath

from . import ExtensionModule
from . import ModuleReturnValue
from .. import build
from .. import mlog
from ..interpreterbase import permittedKwargs, stringArgs
from ..mesonlib import MesonException, File, MachineChoice, version_compare

if T.TYPE_CHECKING:
    from ..interpreter import ModuleState, Interpreter


class WaylandModule(ExtensionModule):

    def __init__(self, interpreter: 'Interpreter'):
        super().__init__(interpreter)

        # wayland-scanner has a pkg-config file, we should use that to find
        # wayland-scanner, as it's more robust
        scanner_dep  = interpreter.dependency_impl(
            'wayland-scanner', 'wayland-scanner', {'required': True, 'native': True})
        scanner_name = scanner_dep.variable_method([], {'pkgconfig': 'wayland_scanner'})
        self.scanner = interpreter.find_program_impl(
            [scanner_name], silent=False, for_machine=MachineChoice.BUILD)

        # Older version of wayland-scanner take different arguments
        self.old_scanner = version_compare(scanner_dep.held_object.version, '< 1.15')

        # We need this to find the location where upstream protocols are installed
        self.protocols_dep = interpreter.dependency_impl(
            'wayland-protocols', 'wayland-protocols', {'required': True})

    @stringArgs
    @permittedKwargs(build.CustomTarget.known_kwargs | {'is_protocol'})
    def scanner_target(self, state: 'ModuleState', args: T.Sequence[str], kwargs: T.Dict[str, T.Any]) -> ModuleReturnValue:
        """Wrapper the wayland-scanner tool, and create custom targets.

        This provides a wrapper around wayland-scanner, simplifying things
        like where to find the installed protocols and setting up paths
        correctly. It can also auto generate an output name based on teh
        input name, if an output name isn't provided, which is fine for
        generating C files, though it may not be for generating headers.
        """
        if len(args) != 2:
            raise MesonException('scanner_target requires 1 arguments')

        name = args[0]
        if not isinstance(name, str):
            raise MesonException('First argument must be a string')

        valid_types = {'client-header', 'server-header', 'private-code', 'public-code'}
        type_ = args[1]
        if not isinstance(type_, str):
            raise MesonException('Second argument must be a string')
        if type_ not in valid_types:
            raise MesonException('Second argument must be one of {}'.format(' '.join(sorted(valid_types))))

        # map new argument to old arguments if necessary (so we only accept the
        # newer versions), error if the wayland-scanner is too old for the
        # requested argument
        if self.old_scanner:
            if type_ == 'private-code':
                type_ = 'code'
            elif type_ == 'public-code':
                raise MesonException('public-code type requires wayland scanner >=1.15')

        if isinstance(kwargs['input'], list):
            if len(kwargs['input']) != 1:
                raise MesonException('Only one input file allowed.')
            input_ = kwargs['input'][0]
        else:
            input_ = kwargs['input']
        if kwargs.pop('is_protocol', False):
            p = self.protocols_dep.variable_method([], {'pkgconfig': 'pkgdatadir'})
            input_ = (PurePath(p) / input_).as_posix()

        if 'output' in kwargs:
            output = kwargs['output']
        else:
            output_stem = PurePath(PurePath(input_).name).stem

            if type_.endswith('code'):
                output_suffix = 'c'
            else:
                output_suffix = 'h'
            output ='{}.{}'.format(output_stem, output_suffix)

        f_kwargs = {
            'command': [self.scanner, type_, '@INPUT@', '@OUTPUT@'],
            'input': [input_],
            'output': [output],
        }

        target = build.CustomTarget(name, state.subdir, state.subproject, f_kwargs)
        return ModuleReturnValue(target, [target])


def initialize(*args, **kwargs) -> WaylandModule:
    return WaylandModule(*args, **kwargs)
