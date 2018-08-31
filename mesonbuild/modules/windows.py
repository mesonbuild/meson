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
from .. import mesonlib, build
from ..mesonlib import MesonException, extract_as_list
from . import get_include_args
from . import ModuleReturnValue
from . import ExtensionModule
from ..interpreter import CustomTargetHolder
from ..interpreterbase import permittedKwargs, FeatureNewKwargs
from ..dependencies import ExternalProgram

class WindowsModule(ExtensionModule):

    def detect_compiler(self, compilers):
        for l in ('c', 'cpp'):
            if l in compilers:
                return compilers[l]
        raise MesonException('Resource compilation requires a C or C++ compiler.')

    @FeatureNewKwargs('windows.compile_resources', '0.47.0', ['depend_files', 'depends'])
    @permittedKwargs({'args', 'include_directories', 'depend_files', 'depends'})
    def compile_resources(self, state, args, kwargs):
        comp = self.detect_compiler(state.compilers)

        extra_args = mesonlib.stringlistify(kwargs.get('args', []))
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

        rescomp = None
        # FIXME: Does not handle `native: true` executables, see
        # https://github.com/mesonbuild/meson/issues/1531
        if state.environment.is_cross_build():
            # If cross compiling see if windres has been specified in the
            # cross file before trying to find it another way.
            cross_info = state.environment.cross_info
            rescomp = ExternalProgram.from_cross_info(cross_info, 'windres')

        if not rescomp or not rescomp.found():
            if 'WINDRES' in os.environ:
                # Pick-up env var WINDRES if set. This is often used for
                # specifying an arch-specific windres.
                rescomp = ExternalProgram('windres', command=os.environ.get('WINDRES'), silent=True)

        if not rescomp or not rescomp.found():
            if comp.id == 'msvc':
                rescomp = ExternalProgram('rc', silent=True)
            else:
                rescomp = ExternalProgram('windres', silent=True)

        if not rescomp.found():
            raise MesonException('Could not find Windows resource compiler')

        if 'rc' in rescomp.get_path():
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
                    mlog.warning(m.format(arg))

        res_targets = []

        def add_target(src):
            if isinstance(src, list):
                for subsrc in src:
                    add_target(subsrc)
                return

            if hasattr(src, 'held_object'):
                src = src.held_object

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
            if 'windres' in rescomp.get_path():
                res_kwargs['depfile'] = res_kwargs['output'] + '.d'
                res_kwargs['command'] += ['--preprocessor-arg=-MD', '--preprocessor-arg=-MQ@OUTPUT@', '--preprocessor-arg=-MF@DEPFILE@']

            res_targets.append(build.CustomTarget('Windows resource for ' + name_format.format(name), state.subdir, state.subproject, res_kwargs))

        add_target(args)

        return ModuleReturnValue(res_targets, [res_targets])

def initialize(*args, **kwargs):
    return WindowsModule(*args, **kwargs)
