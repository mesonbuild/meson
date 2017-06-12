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

from .base import ExternalDependency, DependencyException


class AppleFrameworks(ExternalDependency):
    def __init__(self, env, kwargs):
        super().__init__('appleframeworks', env, None, kwargs)
        modules = kwargs.get('modules', [])
        if isinstance(modules, str):
            modules = [modules]
        if not modules:
            raise DependencyException("AppleFrameworks dependency requires at least one module.")
        self.frameworks = modules
        # FIXME: Use self.compiler to check if the frameworks are available
        for f in self.frameworks:
            self.link_args += ['-framework', f]

    def found(self):
        return mesonlib.is_osx()

    def get_version(self):
        return 'unknown'
