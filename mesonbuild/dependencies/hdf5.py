# Copyright 2013-2019 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This file contains the detection logic for miscellaneous external dependencies.

import subprocess
import shutil
from pathlib import Path

from .. import mlog
from ..mesonlib import split_args, listify
from .base import (DependencyException, DependencyMethods, ExternalDependency, ExternalProgram,
                   PkgConfigDependency)

class HDF5Dependency(ExternalDependency):

    def __init__(self, environment, kwargs):
        language = kwargs.get('language', 'c')
        super().__init__('hdf5', environment, kwargs, language=language)
        kwargs['required'] = False
        kwargs['silent'] = True
        self.is_found = False
        methods = listify(self.methods)

        if language not in ('c', 'cpp', 'fortran'):
            raise DependencyException('Language {} is not supported with HDF5.'.format(language))

        if set([DependencyMethods.AUTO, DependencyMethods.PKGCONFIG]).intersection(methods):
            pkgconfig_files = ['hdf5', 'hdf5-serial']
            PCEXE = shutil.which('pkg-config')
            if PCEXE:
                # some distros put hdf5-1.2.3.pc with version number in .pc filename.
                ret = subprocess.run([PCEXE, '--list-all'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     universal_newlines=True)
                if ret.returncode == 0:
                    for pkg in ret.stdout.split('\n'):
                        if pkg.startswith(('hdf5')):
                            pkgconfig_files.append(pkg.split(' ', 1)[0])
                    pkgconfig_files = list(set(pkgconfig_files))  # dedupe

            for pkg in pkgconfig_files:
                pkgdep = PkgConfigDependency(pkg, environment, kwargs, language=self.language)
                if not pkgdep.found():
                    continue

                self.compile_args = pkgdep.get_compile_args()
                # some broken pkgconfig don't actually list the full path to the needed includes
                newinc = []
                for arg in self.compile_args:
                    if arg.startswith('-I'):
                        stem = 'static' if kwargs.get('static', False) else 'shared'
                        if (Path(arg[2:]) / stem).is_dir():
                            newinc.append('-I' + str(Path(arg[2:]) / stem))
                self.compile_args += newinc

                # derive needed libraries by language
                pd_link_args = pkgdep.get_link_args()
                link_args = []
                for larg in pd_link_args:
                    lpath = Path(larg)
                    # some pkg-config hdf5.pc (e.g. Ubuntu) don't include the commonly-used HL HDF5 libraries,
                    # so let's add them if they exist
                    # additionally, some pkgconfig HDF5 HL files are malformed so let's be sure to find HL anyway
                    if lpath.is_file():
                        hl = []
                        if language == 'cpp':
                            hl += ['_hl_cpp', '_cpp']
                        elif language == 'fortran':
                            hl += ['_hl_fortran', 'hl_fortran', '_fortran']
                        hl += ['_hl']  # C HL library, always needed

                        suffix = '.' + lpath.name.split('.', 1)[1]  # in case of .dll.a
                        for h in hl:
                            hlfn = lpath.parent / (lpath.name.split('.', 1)[0] + h + suffix)
                            if hlfn.is_file():
                                link_args.append(str(hlfn))
                        # HDF5 C libs are required by other HDF5 languages
                        link_args.append(larg)
                    else:
                        link_args.append(larg)

                self.link_args = link_args
                self.version = pkgdep.get_version()
                self.is_found = True
                self.pcdep = pkgdep
                return

        if DependencyMethods.AUTO in methods:
            wrappers = {'c': 'h5cc', 'cpp': 'h5c++', 'fortran': 'h5fc'}
            comp_args = []
            link_args = []
            # have to always do C as well as desired language
            for lang in set([language, 'c']):
                prog = ExternalProgram(wrappers[lang], silent=True)
                if not prog.found():
                    return
                cmd = prog.get_command() + ['-show']
                p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=15)
                if p.returncode != 0:
                    mlog.debug('Command', mlog.bold(cmd), 'failed to run:')
                    mlog.debug(mlog.bold('Standard output\n'), p.stdout)
                    mlog.debug(mlog.bold('Standard error\n'), p.stderr)
                    return
                args = split_args(p.stdout)
                for arg in args[1:]:
                    if arg.startswith(('-I', '-f', '-D')) or arg == '-pthread':
                        comp_args.append(arg)
                    elif arg.startswith(('-L', '-l', '-Wl')):
                        link_args.append(arg)
                    elif Path(arg).is_file():
                        link_args.append(arg)
            self.compile_args = comp_args
            self.link_args = link_args
            self.is_found = True
            return

    @staticmethod
    def get_methods():
        return [DependencyMethods.AUTO, DependencyMethods.PKGCONFIG]
