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
from ..mesonlib import MesonException
from . import get_include_args
from . import ModuleReturnValue
from . import ExtensionModule

class WindowsModule(ExtensionModule):

    def detect_compiler(self, compilers):
        for l in ('c', 'cpp'):
            if l in compilers:
                return compilers[l]
        raise MesonException('Resource compilation requires a C or C++ compiler.')

    def compile_resources(self, state, args, kwargs):
        comp = self.detect_compiler(state.compilers)

        extra_args = mesonlib.stringlistify(kwargs.get('args', []))
        inc_dirs = kwargs.pop('include_directories', [])
        if not isinstance(inc_dirs, list):
            inc_dirs = [inc_dirs]
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
        res_kwargs = {'output': '@BASENAME@.' + suffix,
                      'arguments': res_args}
        res_gen = build.Generator([rescomp], res_kwargs)
        res_output = res_gen.process_files('Windows resource', args, state)
        return ModuleReturnValue(res_output, [res_output])

def initialize():
    return WindowsModule()
