# Copyright 2017 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from . import ModuleReturnValue
from . import ExtensionModule

from .. import mesonlib

import os


class KconfigModule(ExtensionModule):
    def __init__(self):
        super().__init__()
        self.kconfig_map = {}

    def _load_file(self, path_to_config):
        try:
            with open(path_to_config) as f:
                for line in f:
                    if '#' in line:
                        comment_idx = line.index('#')
                        line = line[:comment_idx]
                    line = line.strip()
                    try:
                        name, val = line.split('=', 1)
                    except ValueError:
                        continue
                    self.kconfig_map[name.strip()] = val.strip()
        except IOError as e:
            raise mesonlib.MesonException('Failed to load config {} with err {}'.format(path_to_config, e))

    def is_set(self, state, args, kwargs):
        if not len(args) == 1:
            raise mesonlib.MesonException('Kconfig is_set takes one argument. {} passed.'.format(len(args)))

        return ModuleReturnValue(args[0] in self.kconfig_map, [])

    def value(self, state, args, kwargs):
        if not len(args) == 1:
            raise mesonlib.MesonException('Kconfig value takes one argument. {} passed.'.format(len(args)))

        if not args[0] in self.kconfig_map:
            raise mesonlib.MesonException('Kconfig value {} not in kconfig file.'.format(args[0]))
        else:
            return ModuleReturnValue(self.kconfig_map[args[0]], [])

    def load(self, state, args, kwargs):
        if not len(args) == 1:
            raise mesonlib.MesonException('Kconfig load_file takes one argument. {} passed.'.format(len(args)))
        path = os.path.join(state.environment.get_source_dir(), state.subdir)
        path = os.path.join(path, args[0])
        self._load_file(path)
        return ModuleReturnValue(None, [])


def initialize():
    return KconfigModule()
