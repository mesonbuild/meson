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

import enum
import os
import re

from .. import mlog
from .. import mesonlib, build
from ..mesonlib import MachineChoice, MesonException, extract_as_list, unholder
from . import get_include_args
from . import ModuleReturnValue
from . import ExtensionModule
from ..interpreter import CustomTargetHolder
from ..interpreterbase import permittedKwargs, FeatureNewKwargs, flatten
from ..dependencies import ExternalProgram

class ResourceCompilerType(enum.Enum):
    windres = 1
    rc = 2

class WindowsModule(ExtensionModule):

    def detect_compiler(self, compilers):
        for l in ('c', 'cpp'):
            if l in compilers:
                return compilers[l]
        raise MesonException('Resource compilation requires a C or C++ compiler.')

    def _find_resource_compiler(self, state):
        # FIXME: Does not handle `native: true` executables, see
        # See https://github.com/mesonbuild/meson/issues/1531
        # Take a parameter instead of the hardcoded definition below
        for_machine = MachineChoice.HOST

        if hasattr(self, '_rescomp'):
            return self._rescomp

        # Will try cross / native file and then env var
        rescomp = ExternalProgram.from_bin_list(state.environment, for_machine, 'windres')

        if not rescomp or not rescomp.found():
            comp = self.detect_compiler(state.environment.coredata.compilers[for_machine])
            if comp.id in {'msvc', 'clang-cl', 'intel-cl'}:
                rescomp = ExternalProgram('rc', silent=True)
            else:
                rescomp = ExternalProgram('windres', silent=True)

        if not rescomp.found():
            raise MesonException('Could not find Windows resource compiler')

        for (arg, match, rc_type) in [
                ('/?', '^.*Microsoft.*Resource Compiler.*$', ResourceCompilerType.rc),
                ('--version', '^.*GNU windres.*$', ResourceCompilerType.windres),
        ]:
            p, o, e = mesonlib.Popen_safe(rescomp.get_command() + [arg])
            m = re.search(match, o, re.MULTILINE)
            if m:
                mlog.log('Windows resource compiler: %s' % m.group())
                self._rescomp = (rescomp, rc_type)
                break
        else:
            raise MesonException('Could not determine type of Windows resource compiler')

        return self._rescomp

    @FeatureNewKwargs('windows.compile_resources', '0.47.0', ['depend_files', 'depends'])
    @permittedKwargs({'args', 'include_directories', 'depend_files', 'depends'})
    def compile_resources(self, state, args, kwargs):
        extra_args = mesonlib.stringlistify(flatten(kwargs.get('args', [])))
        wrc_depend_files = extract_as_list(kwargs, 'depend_files', pop = True)
        wrc_depends = extract_as_list(kwargs, 'depends', pop = True)
        for d in wrc_depends:
            if isinstance(d, CustomTargetHolder):
                extra_args += get_include_args([d.outdir_include()])
        inc_dirs = extract_as_list(kwargs, 'include_directories', pop = True)
        for incd in inc_dirs:
            if not isinstance(incd.held_object, (str, build.IncludeDirs)):
                raise MesonException('Resource include dirs should be include_directories().')
        extra_args += get_include_args(inc_dirs)

        rescomp, rescomp_type = self._find_resource_compiler(state)
        if rescomp_type == ResourceCompilerType.rc:
            # RC is used to generate .res files, a special binary resource
            # format, which can be passed directly to LINK (apparently LINK uses
            # CVTRES internally to convert this to a COFF object)
            suffix = 'res'
            res_args = extra_args + ['/nologo', '/fo@OUTPUT@', '@INPUT@']
        else:
            # ld only supports object files, so windres is used to generate a
            # COFF object
            suffix = 'o'
            res_args = extra_args + ['@INPUT@', '@OUTPUT@']

            m = 'Argument {!r} has a space which may not work with windres due to ' \
                'a MinGW bug: https://sourceware.org/bugzilla/show_bug.cgi?id=4933'
            for arg in extra_args:
                if ' ' in arg:
                    mlog.warning(m.format(arg), fatal=False)

        res_targets = []

        def add_target(src):
            if isinstance(src, list):
                for subsrc in src:
                    add_target(subsrc)
                return
            src = unholder(src)

            if isinstance(src, str):
                name_format = 'file {!r}'
                name = os.path.join(state.subdir, src)
            elif isinstance(src, mesonlib.File):
                name_format = 'file {!r}'
                name = src.relative_name()
            elif isinstance(src, build.CustomTarget):
                if len(src.get_outputs()) > 1:
                    raise MesonException('windows.compile_resources does not accept custom targets with more than 1 output.')

                name_format = 'target {!r}'
                name = src.get_id()
            else:
                raise MesonException('Unexpected source type {!r}. windows.compile_resources accepts only strings, files, custom targets, and lists thereof.'.format(src))

            # Path separators are not allowed in target names
            name = name.replace('/', '_').replace('\\', '_')

            res_kwargs = {
                'output': name + '_@BASENAME@.' + suffix,
                'input': [src],
                'command': [rescomp] + res_args,
                'depend_files': wrc_depend_files,
                'depends': wrc_depends,
            }

            # instruct binutils windres to generate a preprocessor depfile
            if rescomp_type == ResourceCompilerType.windres:
                res_kwargs['depfile'] = res_kwargs['output'] + '.d'
                res_kwargs['command'] += ['--preprocessor-arg=-MD', '--preprocessor-arg=-MQ@OUTPUT@', '--preprocessor-arg=-MF@DEPFILE@']

            res_targets.append(build.CustomTarget('Windows resource for ' + name_format.format(name), state.subdir, state.subproject, res_kwargs))

        add_target(args)

        return ModuleReturnValue(res_targets, [res_targets])

def initialize(*args, **kwargs):
    return WindowsModule(*args, **kwargs)
