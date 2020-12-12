# Copyright © 2020 Intel Corporation

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Dependency finders for programing and scripting languages."""

import typing as T

from ..environment import search_version
from .base import ConfigToolDependency

if T.TYPE_CHECKING:
    from ..environment import Environment


class PerlDependency(ConfigToolDependency):

    """Create a dependency for embedding perl.

    This uses the perl ExtUtils::Embed module to get the necessary arguments.
    """

    tools = ['perl']

    def __init__(self, env: 'Environment', kwargs: T.Dict[str, T.Any]):
        super().__init__('perl', env, kwargs)

        self.__rpath = ''

        include_flags = self.get_config_value(['-MExtUtils::Embed', '-e', 'perl_inc'], 'cflags')
        cflags = self.get_config_value(['-MExtUtils::Embed', '-e', 'ccflags'], 'cflags')
        self.compile_args = include_flags + self.__filter_cflags(cflags)

        ldflags = self.get_config_value(['-MExtUtils::Embed', '-e', 'ccdlflags'], 'ldflags')
        self.link_args = self.__filter_ldflags(ldflags)

    def __filter_cflags(self, cflags: T.List[str]) -> T.List[str]:
        """Remove any compile flags we don't want to propogate."""
        new: T.List[str] = []
        for flag in cflags:
            if flag == '-pipe':
                continue
            new.append(flag)

        return new

    def __filter_ldflags(self, cflags: T.List[str]) -> T.List[str]:
        """Remove any link flags we don't want to propogate."""
        new: T.List[str] = []
        for flag in cflags:
            if '-rpath' in flag:
                self.__rpath = flag.split(',')[-1]
                continue
            new.append(flag)

        return new

    def _sanitize_version(self, version: str) -> str:
        """Get the version string.

        Perl prints enough stuff here we just fall back to our swiss army
        knife version extractor.
        """
        return search_version(version)

    def get_configtool_variable(self, variable_name: str) -> str:
        if variable_name == 'rpath':
            return self.__rpath
        return super().get_configtool_variable(variable_name)
