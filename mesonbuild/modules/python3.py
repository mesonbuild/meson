# Copyright 2016-2017 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import sysconfig
from .. import mesonlib, dependencies

from . import ExtensionModule
from mesonbuild.modules import ModuleReturnValue


class Python3Module(ExtensionModule):
    def __init__(self):
        super().__init__()
        self.snippets.add('extension_module')

    def extension_module(self, interpreter, state, args, kwargs):
        if 'name_prefix' in kwargs:
            raise mesonlib.MesonException('Name_prefix is set automatically, specifying it is forbidden.')
        if 'name_suffix' in kwargs:
            raise mesonlib.MesonException('Name_suffix is set automatically, specifying it is forbidden.')
        host_system = state.host_machine.system
        if host_system == 'darwin':
            # Default suffix is 'dylib' but Python does not use it for extensions.
            suffix = 'so'
        elif host_system == 'windows':
            # On Windows the extension is pyd for some unexplainable reason.
            suffix = 'pyd'
        else:
            suffix = []
        kwargs['name_prefix'] = ''
        kwargs['name_suffix'] = suffix
        return interpreter.func_shared_module(None, args, kwargs)

    def find_python(self, state, args, kwargs):
        py3 = dependencies.ExternalProgram('python3', sys.executable, silent=True)
        return ModuleReturnValue(py3, [py3])

    def language_version(self, state, args, kwargs):
        if args or kwargs:
            raise mesonlib.MesonException('language_version() takes no arguments.')
        return ModuleReturnValue(sysconfig.get_python_version(), [])

    def sysconfig_path(self, state, args, kwargs):
        if len(args) != 1:
            raise mesonlib.MesonException('sysconfig_path() requires passing the name of path to get.')
        if kwargs:
            raise mesonlib.MesonException('sysconfig_path() does not accept keywords.')
        path_name = args[0]
        valid_names = sysconfig.get_path_names()
        if path_name not in valid_names:
            raise mesonlib.MesonException('{} is not a valid path name {}.'.format(path_name, valid_names))

        # Get a relative path without a prefix, e.g. lib/python3.6/site-packages
        path = sysconfig.get_path(path_name, vars={'base': ''})[1:]
        return ModuleReturnValue(path, [])


def initialize():
    return Python3Module()
