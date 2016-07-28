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

from .. import mesonlib, dependencies, build
from ..mesonlib import MesonException
import os

class WindowsModule:

    def detect_compiler(self, compilers):
        for c in compilers:
            if c.language == 'c' or c.language == 'cpp':
                return c
        raise MesonException('Resource compilation requires a C or C++ compiler.')

    def compile_resources(self, state, args, kwargs):
        comp = self.detect_compiler(state.compilers)
        extra_args = mesonlib.stringlistify(kwargs.get('args', []))
        if comp.id == 'msvc':
            rescomp = dependencies.ExternalProgram('rc', silent=True)
            res_args = extra_args + ['/nologo', '/fo@OUTPUT@', '@INPUT@']
            suffix = 'res'
        else:
            # Pick-up env var WINDRES if set. This is often used for specifying
            # an arch-specific windres.
            rescomp_name = os.environ.get('WINDRES', 'windres')
            rescomp = dependencies.ExternalProgram(rescomp_name, silent=True)
            res_args = extra_args + ['@INPUT@', '@OUTPUT@']
            suffix = 'o'
        if not rescomp.found():
            raise MesonException('Could not find Windows resource compiler %s.' % ' '.join(rescomp.get_command()))
        res_files = mesonlib.stringlistify(args)
        res_kwargs = {'output' : '@BASENAME@.' + suffix,
                      'arguments': res_args}
        res_gen = build.Generator([rescomp], res_kwargs)
        res_output = build.GeneratedList(res_gen)
        [res_output.add_file(os.path.join(state.subdir, a)) for a in res_files]
        return res_output

def initialize():
    return WindowsModule()
