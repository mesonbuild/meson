# Copyright 2013-2017 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This file contains the detection logic for external dependencies that are
# platform-specific (generally speaking).

from .. import mesonlib

from .base import ExtraFrameworkDependency, ExternalDependency, DependencyException


class AppleFrameworks(ExternalDependency):
    def __init__(self, env, kwargs):
        super().__init__('appleframeworks', env, None, kwargs)
        modules = kwargs.get('modules', [])
        includes = kwargs.get('include', [])

        if isinstance(modules, str):
            modules = [modules]
        if not modules:
            raise DependencyException("AppleFrameworks dependency requires at least one module.")

        if isinstance(includes, str):
            includes = [includes]
        if includes:
            includes = ['/System/Library/Frameworks', '/Library/Frameworks'] + includes

        self.frameworks = []

        for f in modules:
            self.frameworks += [
                ExtraFrameworkDependency(
                    f,
                    True,
                    includes,
                    env,
                    None,
                    kwargs,
                )
            ]

        for f in self.frameworks:
            self.link_args += f.get_link_args()
            self.compile_args += f.get_compile_args()

    def found(self):
        return all([f.found() for f in self.frameworks])

    def get_version(self):
        return 'unknown'
