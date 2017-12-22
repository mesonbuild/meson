# Copyright 2015 The Meson development team

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

from .. import mlog
from .. import mesonlib, dependencies, build
from ..mesonlib import MesonException, extract_as_list
from . import get_include_args
from . import ModuleReturnValue
from . import ExtensionModule
from ..interpreterbase import permittedKwargs

class WindowsModule(ExtensionModule):

    def detect_compiler(self, compilers):
        for l in ('c', 'cpp'):
            if l in compilers:
                return compilers[l]
        raise MesonException('Resource compilation requires a C or C++ compiler.')

    @permittedKwargs({'args', 'include_directories'})
    def compile_resources(self, state, args, kwargs):
        comp = self.detect_compiler(state.compilers)

        extra_args = mesonlib.stringlistify(kwargs.get('args', []))
        inc_dirs = extract_as_list(kwargs, 'include_directories', pop = True)
        for incd in inc_dirs:
            if not isinstance(incd.held_object, (str, build.IncludeDirs)):
                raise MesonException('Resource include dirs should be include_directories().')
        extra_args += get_include_args(inc_dirs)

        if comp.id == 'msvc':
            rescomp = dependencies.ExternalProgram('rc', silent=True)
            res_args = extra_args + ['/nologo', '/fo@OUTPUT@', '@INPUT@']
            suffix = 'res'
        else:
            m = 'Argument {!r} has a space which may not work with windres due to ' \
                'a MinGW bug: https://sourceware.org/bugzilla/show_bug.cgi?id=4933'
            for arg in extra_args:
                if ' ' in arg:
                    mlog.warning(m.format(arg))
            rescomp_name = None
            # FIXME: Does not handle `native: true` executables, see
            # https://github.com/mesonbuild/meson/issues/1531
            if state.environment.is_cross_build():
                # If cross compiling see if windres has been specified in the
                # cross file before trying to find it another way.
                rescomp_name = state.environment.cross_info.config['binaries'].get('windres')
            if rescomp_name is None:
                # Pick-up env var WINDRES if set. This is often used for
                # specifying an arch-specific windres.
                rescomp_name = os.environ.get('WINDRES', 'windres')
            rescomp = dependencies.ExternalProgram(rescomp_name, silent=True)
            res_args = extra_args + ['@INPUT@', '@OUTPUT@']
            suffix = 'o'
        if not rescomp.found():
            raise MesonException('Could not find Windows resource compiler %s.' % ' '.join(rescomp.get_command()))

        res_targets = []

        def add_target(src):
            if isinstance(src, list):
                for subsrc in src:
                    add_target(subsrc)
                return

            if hasattr(src, 'held_object'):
                src = src.held_object

            res_kwargs = {
                'output': '@BASENAME@.' + suffix,
                'input': [src],
                'command': [rescomp] + res_args,
            }

            if isinstance(src, (str, mesonlib.File)):
                name = 'file {!r}'.format(str(src))
            elif isinstance(src, build.CustomTarget):
                if len(src.get_outputs()) > 1:
                    raise MesonException('windows.compile_resources does not accept custom targets with more than 1 output.')

                name = 'target {!r}'.format(src.get_id())
            else:
                raise MesonException('Unexpected source type {!r}. windows.compile_resources accepts only strings, files, custom targets, and lists thereof.'.format(src))

            # Path separators are not allowed in target names
            name = name.replace('/', '_').replace('\\', '_')

            res_targets.append(build.CustomTarget('Windows resource for ' + name, state.subdir, state.subproject, res_kwargs))

        add_target(args)

        return ModuleReturnValue(res_targets, [res_targets])

def initialize():
    return WindowsModule()
