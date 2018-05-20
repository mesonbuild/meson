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

import os
import shutil
import glob
import subprocess

from .. import build
from .. import mlog
from ..mesonlib import MesonException, Popen_safe, File
from . import ModuleReturnValue
from . import ExtensionModule
from ..dependencies import InternalDependency
from ..interpreterbase import permittedKwargs

class DlangModule(ExtensionModule):
    girtod_path = None

    def _detect_girtod(self, env):
        if self.girtod_path:
            return

        self.girtod_path = shutil.which('girtod')
        if not self.girtod_path:
            raise MesonException('Can not use gir-to-d, girtod binary was not found.')
        mlog.log('Found girtod:', mlog.bold(self.girtod_path))

    @permittedKwargs({'gir_dir'})
    def gir_to_d(self, state, args, kwargs):
        self._detect_girtod(state.environment)

        if len(args) < 1:
            raise MesonException('Not enough arguments; The path to the wrap files directory is required')

        wrap_dir = args[0]
        if isinstance(wrap_dir, str):
            wrap_dir = os.path.join(state.subdir, wrap_dir)
        else:
            raise MesonException('Invalid wrap dir argument: {!r}'.format(wrap_dir))

        build_by_default = kwargs.get('build_by_default', False)

        wrap_dir_out = os.path.join(state.environment.get_build_dir(), wrap_dir)
        wrap_dir_out = wrap_dir_out.rstrip(os.sep)
        target_name = os.path.basename(wrap_dir_out) + '-bind'
        wrap_dir_out = wrap_dir_out + '.gen'
        os.makedirs(wrap_dir_out, exist_ok=True)

        cmd = [self.girtod_path,
               '-i', wrap_dir,
               '-o', wrap_dir_out]
        if 'gir_dir' in kwargs:
            gir_dir = kwargs.pop('gir_dir')
            if not isinstance(gir_dir, str):
                raise MesonException('Invalid gir dir argument: {!r}'.format(wrap_dir))
            cmd.extend(['-g', gir_dir])

        pc, stdout, stderr = Popen_safe(cmd, cwd=state.environment.get_source_dir())
        if pc.returncode != 0:
            m = 'girtod failed to generate D bindings {}:\n{}'
            mlog.warning(m.format(cmd[1], stderr))
            raise subprocess.CalledProcessError(pc.returncode, cmd)

        d_sources = []
        build_dir = os.path.relpath(state.environment.get_build_dir(), state.environment.get_source_dir())
        files = glob.glob(os.path.join(wrap_dir_out, '**', '*.d'), recursive=True)
        for fname in sorted(files):
            rel_fname = os.path.relpath(fname, state.environment.get_build_dir())
            d_sources.append(File.from_source_file(state.environment.get_source_dir(), build_dir, rel_fname))

        # generate static library target to compile the D wrapper code, which can be added
        # to the actual targets using the wrapped library.
        inc_dirs = build.IncludeDirs(state.subdir, [wrap_dir_out], False)
        custom_kwargs = {'build_by_default': build_by_default,
                         'install': False,
                         'include_directories': inc_dirs
                         }
        target = build.StaticLibrary(target_name,
                                     state.subdir,
                                     state.subproject,
                                     state.environment.is_cross_build(),
                                     d_sources,
                                     [],
                                     state.environment,
                                     custom_kwargs)

        rv = InternalDependency(None, inc_dirs, [], [], [target], [], [], [])

        return ModuleReturnValue(rv, [rv])


def initialize(*args, **kwargs):
    return DlangModule(*args, **kwargs)
