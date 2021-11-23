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

# This file contains the detection logic for external dependencies that
# are UI-related.

import json
import os

from . import ExtensionModule
from .. import dependencies
from .. import mlog
from ..mesonlib import Popen_safe, MesonException


class DlangModule(ExtensionModule):

    # This will always be ready since the DubDependency constructor will have
    # been called by importing the module
    dubbin = dependencies.DubDependency.dubbin

    def __init__(self, interpreter):
        super().__init__(interpreter)
        self.methods.update({
            'generate_dub_file': self.generate_dub_file,
        })

    def generate_dub_file(self, state, args, kwargs):
        if not self.dubbin.found():
            raise MesonException('dub.generate_dub_file: cannot generate dub file without dub binary.')

        if len(args) < 2:
            raise MesonException('Missing arguments')

        config = {
            'name': args[0]
        }

        config_path = os.path.join(args[1], 'dub.json')
        if os.path.exists(config_path):
            with open(config_path, encoding='utf-8') as ofile:
                try:
                    config = json.load(ofile)
                except ValueError:
                    mlog.warning('Failed to load the data in dub.json')

        warn_publishing = ['description', 'license']
        for arg in warn_publishing:
            if arg not in kwargs and \
               arg not in config:
                mlog.warning('Without', mlog.bold(arg), 'the DUB package can\'t be published')

        for key, value in kwargs.items():
            if key == 'dependencies':
                config[key] = {}
                if isinstance(value, list):
                    for dep in value:
                        if isinstance(dep, dependencies.Dependency):
                            name = dep.get_name()
                            ret, res = self._call_dubbin(['describe', name])
                            if ret == 0:
                                version = dep.get_version()
                                if version is None:
                                    config[key][name] = ''
                                else:
                                    config[key][name] = version
                elif isinstance(value, dependencies.Dependency):
                    name = value.get_name()
                    ret, res = self._call_dubbin(['describe', name])
                    if ret == 0:
                        version = value.get_version()
                        if version is None:
                            config[key][name] = ''
                        else:
                            config[key][name] = version
            else:
                config[key] = value

        with open(config_path, 'w', encoding='utf-8') as ofile:
            ofile.write(json.dumps(config, indent=4, ensure_ascii=False))

    def _call_dubbin(self, args, env=None):
        p, out = Popen_safe(self.dubbin.get_command() + args, env=env)[0:2]
        return p.returncode, out.strip()

def initialize(*args, **kwargs):
    return DlangModule(*args, **kwargs)
