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

from pathlib import Path
import os

from .. import mesonlib
from .base import CMakeDependency, DependencyMethods, ExternalDependency, PkgConfigDependency


class ScalapackDependency(ExternalDependency):
    def __init__(self, environment, kwargs: dict):
        super().__init__('scalapack', environment, None, kwargs)
        kwargs['required'] = False
        kwargs['silent'] = True
        self.is_found = False
        self.static = kwargs.get('static', False)
        methods = mesonlib.listify(self.methods)

        if set([DependencyMethods.AUTO, DependencyMethods.PKGCONFIG]).intersection(methods):
            pkgconfig_files = []
            mklroot = None
            is_gcc = self.clib_compiler.get_id() == 'gcc'
            # Intel MKL works with non-Intel compilers too -- but not gcc on windows
            if 'MKLROOT' in os.environ and not (mesonlib.is_windows() and is_gcc):
                try:
                    mklroot = Path(os.environ['MKLROOT']).resolve()
                except Exception:
                    pass
            if mklroot is not None:
                # MKL pkg-config is a start, but you have to add / change stuff
                # https://software.intel.com/en-us/articles/intel-math-kernel-library-intel-mkl-and-pkg-config-tool
                pkgconfig_files = (
                    ['mkl-static-lp64-iomp'] if self.static else ['mkl-dynamic-lp64-iomp']
                )
                if mesonlib.is_windows():
                    suffix = '.lib'
                elif self.static:
                    suffix = '.a'
                else:
                    suffix = ''
                libdir = mklroot / 'lib/intel64'
            # Intel compiler might not have Parallel Suite
            pkgconfig_files += ['scalapack-openmpi', 'scalapack']

            for pkg in pkgconfig_files:
                pkgdep = PkgConfigDependency(
                    pkg, environment, kwargs, language=self.language
                )
                if pkgdep.found():
                    self.compile_args = pkgdep.get_compile_args()
                    if mklroot:
                        link_args = pkgdep.get_link_args()
                        if is_gcc:
                            for i, a in enumerate(link_args):
                                if 'mkl_intel_lp64' in a:
                                    link_args[i] = a.replace('intel', 'gf')
                                    break
                        # MKL pkg-config omits scalapack
                        # be sure "-L" and "-Wl" are first if present
                        i = 0
                        for j, a in enumerate(link_args):
                            if a.startswith(('-L', '-Wl')):
                                i = j + 1
                            elif j > 3:
                                break
                        if mesonlib.is_windows() or self.static:
                            link_args.insert(
                                i, str(libdir / ('mkl_scalapack_lp64' + suffix))
                            )
                            link_args.insert(
                                i + 1, str(libdir / ('mkl_blacs_intelmpi_lp64' + suffix))
                            )
                        else:
                            link_args.insert(i, '-lmkl_scalapack_lp64')
                            link_args.insert(i + 1, '-lmkl_blacs_intelmpi_lp64')
                    else:
                        link_args = pkgdep.get_link_args()
                    self.link_args = link_args

                    self.version = pkgdep.get_version()
                    if self.version == 'unknown' and mklroot:
                        try:
                            v = (
                                mklroot.as_posix()
                                .split('compilers_and_libraries_')[1]
                                .split('/', 1)[0]
                            )
                            if v:
                                self.version = v
                        except IndexError:
                            pass

                    self.is_found = True
                    self.pcdep = pkgdep
                    return

        if set([DependencyMethods.AUTO, DependencyMethods.CMAKE]).intersection(methods):
            cmakedep = CMakeDependency('Scalapack', environment, kwargs, language=self.language)
            if cmakedep.found():
                self.compile_args = cmakedep.get_compile_args()
                self.link_args = cmakedep.get_link_args()
                self.version = cmakedep.get_version()
                self.is_found = True
                return

    @staticmethod
    def get_methods():
        return [DependencyMethods.AUTO, DependencyMethods.PKGCONFIG, DependencyMethods.CMAKE]
