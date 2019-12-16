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

from ..mesonlib import listify
from .base import CMakeDependency, DependencyMethods, ExternalDependency, PkgConfigDependency


class CoarrayDependency(ExternalDependency):
    """
    Coarrays are a Fortran 2008 feature.

    Coarrays are sometimes implemented via external library (GCC+OpenCoarrays),
    while other compilers just build in support (Cray, IBM, Intel, NAG).
    Coarrays may be thought of as a high-level language abstraction of
    low-level MPI calls.
    """
    def __init__(self, environment, kwargs: dict):
        super().__init__('coarray', environment, 'fortran', kwargs)
        kwargs['required'] = False
        kwargs['silent'] = True
        self.is_found = False
        methods = listify(self.methods)

        cid = self.get_compiler().get_id()
        if cid == 'gcc':
            """ OpenCoarrays is the most commonly used method for Fortran Coarray with GCC """

            if set([DependencyMethods.AUTO, DependencyMethods.PKGCONFIG]).intersection(methods):
                for pkg in ['caf-openmpi', 'caf']:
                    pkgdep = PkgConfigDependency(pkg, environment, kwargs, language=self.language)
                    if pkgdep.found():
                        self.compile_args = pkgdep.get_compile_args()
                        self.link_args = pkgdep.get_link_args()
                        self.version = pkgdep.get_version()
                        self.is_found = True
                        self.pcdep = pkgdep
                        return

            if set([DependencyMethods.AUTO, DependencyMethods.CMAKE]).intersection(methods):
                if not kwargs.get('modules'):
                    kwargs['modules'] = 'OpenCoarrays::caf_mpi'
                cmakedep = CMakeDependency('OpenCoarrays', environment, kwargs, language=self.language)
                if cmakedep.found():
                    self.compile_args = cmakedep.get_compile_args()
                    self.link_args = cmakedep.get_link_args()
                    self.version = cmakedep.get_version()
                    self.is_found = True
                    return

            if DependencyMethods.AUTO in methods:
                # fallback to single image
                self.compile_args = ['-fcoarray=single']
                self.version = 'single image (fallback)'
                self.is_found = True
                return

        elif cid == 'intel':
            """ Coarrays are built into Intel compilers, no external library needed """
            self.is_found = True
            self.link_args = ['-coarray=shared']
            self.compile_args = self.link_args
        elif cid == 'intel-cl':
            """ Coarrays are built into Intel compilers, no external library needed """
            self.is_found = True
            self.compile_args = ['/Qcoarray:shared']
        elif cid == 'nagfor':
            """ NAG doesn't require any special arguments for Coarray """
            self.is_found = True

    @staticmethod
    def get_methods():
        return [DependencyMethods.AUTO, DependencyMethods.CMAKE, DependencyMethods.PKGCONFIG]
