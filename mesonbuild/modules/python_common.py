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

from . import ExtensionModule
from .. import mesonlib
from mesonbuild.modules import ModuleReturnValue
from . import permittedSnippetKwargs
from ..interpreterbase import noKwargs
from ..interpreter import shlib_kwargs


mod_kwargs = set()
mod_kwargs.update(shlib_kwargs)


class PythonModule(ExtensionModule):
    def __init__(self):
        super().__init__()
        self.snippets.add('extension_module')
        self._python = None

    def _find_python(self):
        raise NotImplementedError

    @property
    def python(self):
        if self._python:
            return self._python
        self._python = self._find_python()
        return self._python

    @permittedSnippetKwargs(mod_kwargs)
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

    @noKwargs
    def find_python(self, state, args, kwargs):
        return ModuleReturnValue(self.python, [self.python])

    @noKwargs
    def sysconfig_path(self, state, args, kwargs):
        if len(args) != 1:
            raise mesonlib.MesonException('sysconfig_path() requires passing the name of path to get.')

        _, stdout, _ = mesonlib.Popen_safe(self.python.get_command() + [
            '-c',
            "import sysconfig; print (','.join(k for k in sysconfig.get_path_names()))"])

        valid_names = stdout.strip().split(',')

        path_name = args[0]
        if path_name not in valid_names:
            raise mesonlib.MesonException('{} is not a valid path name {}.'.format(path_name, valid_names))

        # Get a relative path without a prefix, e.g. lib/python3.6/site-packages
        _, stdout, _ = mesonlib.Popen_safe(self.python.get_command() + [
            '-c',
            "import sysconfig; print (sysconfig.get_path('%s', vars={'base': '', 'platbase': '', 'installed_base': ''})[1:])" % path_name])

        path = stdout.strip()

        return ModuleReturnValue(path, [])

    @noKwargs
    def language_version(self, state, args, kwargs):
        _, stdout, _ = mesonlib.Popen_safe(self.python.get_command() + [
            '-c',
            "import sysconfig; print (sysconfig.get_python_version())"])

        return ModuleReturnValue(stdout.strip(), [])
