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

from .. import mlog
from .. import mesonlib
from .base import CMakeDependency, DependencyException, DependencyMethods, ExternalDependency


class OpenMPDependency(ExternalDependency):
    # Map date of specification release (which is the macro value) to a version.
    VERSIONS = {
        '201811': '5.0',
        '201611': '5.0-revision1',  # This is supported by ICC 19.x
        '201511': '4.5',
        '201307': '4.0',
        '201107': '3.1',
        '200805': '3.0',
        '200505': '2.5',
        '200203': '2.0',
        '199810': '1.0',
    }

    def __init__(self, environment, kwargs):
        language = kwargs.get('language', 'c')
        super().__init__('openmp', environment, language, kwargs)
        self.is_found = False
        methods = mesonlib.listify(self.methods)

        if language not in ('c', 'cpp', 'fortran'):
            raise DependencyException('OpenMP is only for C, C++, Fortran')

        if DependencyMethods.AUTO in methods:
            if self.clib_compiler.get_id() == 'pgi':
                # PGI has no macro defined for OpenMP, but OpenMP 3.1 is supported.
                self.version = '3.1'
                self.is_found = True
                self.compile_args = self.link_args = self.clib_compiler.openmp_flags()
                return
            try:
                openmp_date = self.clib_compiler.get_define(
                    '_OPENMP', '', self.env, self.clib_compiler.openmp_flags(), [self], disable_cache=True)[0]
            except mesonlib.EnvironmentException as e:
                mlog.debug('OpenMP support not available in the compiler')
                mlog.debug(e)
                openmp_date = None

            if openmp_date:
                self.version = self.VERSIONS[openmp_date]
                # Flang has omp_lib.h
                header_names = ('omp.h', 'omp_lib.h')
                for name in header_names:
                    if self.clib_compiler.has_header(name, '', self.env, dependencies=[self], disable_cache=True)[0]:
                        self.is_found = True
                        self.compile_args = self.link_args = self.clib_compiler.openmp_flags()
                        break
                if not self.is_found:
                    mlog.log(mlog.yellow('WARNING:'), 'OpenMP found but omp.h missing.')

        if set([DependencyMethods.AUTO, DependencyMethods.CMAKE]).intersection(methods):
            if not (kwargs.get('modules') and kwargs.get('cmake_components')):
                if language == 'c':
                    kwargs['modules'] = 'OpenMP::OpenMP_C'
                    kwargs['cmake_components'] = 'C'
                if language == 'cpp':
                    kwargs['modules'] = 'OpenMP::OpenMP_CXX'
                    kwargs['cmake_components'] = 'CXX'
                if language == 'fortran':
                    kwargs['modules'] = 'OpenMP::OpenMP_Fortran'
                    kwargs['cmake_components'] = 'Fortran'

            kwargs['cmake_full_find'] = True  # OpenMP cannot be found with faked CMake cache
            cmakedep = CMakeDependency('OpenMP', environment, kwargs, language=self.language)
            if cmakedep.found():
                self.compile_args = cmakedep.get_compile_args()
                self.link_args = cmakedep.get_link_args()
                self.version = cmakedep.get_version()
                self.is_found = True
                return

    @staticmethod
    def get_methods():
        return [DependencyMethods.AUTO, DependencyMethods.CMAKE]
