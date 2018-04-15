# Copyright 2018 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .. import build, dependencies
from ..mesonlib import MesonException, extract_as_list
from . import ModuleReturnValue
from . import ExtensionModule
from ..interpreterbase import permittedKwargs

class XcodeModule(ExtensionModule):

    @permittedKwargs({'xib_files', 'module', 'target_device', 'install', 'install_dir', 'build_by_default', 'extra_arguments'})
    def compile_xibs(self, state, args, kwargs):
        xib_files, extra_arguments, install_dir \
            = extract_as_list(kwargs, 'xib_files', 'extra_arguments', 'install_dir', pop = True)
        sources = []
        module = kwargs.get('module')

        if not module:
            raise MesonException('The module argument is required')

        if len(xib_files) > 0:
            # Look for ibtool in PATH
            ibtool = dependencies.ExternalProgram('ibtool', silent=True)
            if not ibtool.found():
                raise MesonException('Required ibtool not found')

        for xib in xib_files:
            cmd = [ibtool] + extra_arguments + [
                '--output-format', 'human-readable-text',
                '--errors', '--warnings', '--notices',
                '--module', module,
                '--target-device', kwargs.get('target_device', 'mac'),
                '--compile', '@OUTPUT@',
                '@INPUT@'
            ]
            nib_kwargs = {'output': '@BASENAME@.nib',
                          'input': xib,
                          'install': kwargs.get('install', False),
                          'build_by_default': kwargs.get('build_by_default', False),
                          'command': cmd}
            if install_dir is not None:
                nib_kwargs['install_dir'] = install_dir

            nib_target = build.CustomTarget('xib-compile-{}'.format(xib), state.subdir, state.subproject, nib_kwargs)
            sources.append(nib_target)

        return ModuleReturnValue(sources, sources)

def initialize():
    return XcodeModule()
