# Copyright 2016 The Meson development team

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
from os import path
from ..mesonlib import MesonException, File
from ..build import Data, RunScript
from . import ExtensionModule, ModuleReturnValue


class XdgModule(ExtensionModule):

    @staticmethod
    def _create_post_install_script(state, command):
        return RunScript([sys.executable, state.environment.get_build_command()],
                         ['--internal', 'xdg'] + command)

    @staticmethod
    def _validate_args(func_name, args, kwargs, extensions=None):
        if len(kwargs):
            raise MesonException('{} does not take any keywords'.format(func_name))
        if len(args) != 1:
            raise MesonException('Must pass a single file to install')
        if not isinstance(args[0], str):  # TODO: Handle other types
            raise MesonException('Argument must be a string')
        if extensions is not None:
            _, ext = path.splitext(args[0])
            if ext not in extensions:
                raise MesonException('File extension ({}) is not valid: {}'.format(ext, extensions))

    def install_desktop(self, state, args, kwargs):
        self._validate_args('install_desktop', args, kwargs, extensions=('.desktop',))

        desktop_file = File(False, state.subdir, args[0])
        appdir = path.join(state.environment.get_datadir(), 'applications')
        data = Data(desktop_file, appdir)

        post_target = self._create_post_install_script(state, [
            'update-desktop-database', '--quiet', appdir,
        ])

        return ModuleReturnValue([], [data, post_target])

    def install_mime(self, state, args, kwargs):
        self._validate_args('install_mime', args, kwargs, extensions=('.xml',))

        mime_file = File(False, state.subdir, args[0])
        mimedir = path.join(state.environment.get_datadir(), 'mime', 'packages')
        data = Data(mime_file, mimedir)

        post_target = self._create_post_install_script(state, [
            'update-mime-database', mimedir,
        ])

        return ModuleReturnValue([], [data, post_target])

    def install_appstream(self, state, args, kwargs):
        self._validate_args('install_appstream', args, kwargs,
                            extensions=('.metainfo.xml', '.appdata.xml'))

        appdata_file = File(False, state.subdir, args[0])
        appdata_dir = path.join(state.environment.get_datadir(), 'appdata')
        data = Data(appdata_file, appdata_dir)

        return ModuleReturnValue([], [data])

#    def install_icons(self, state, args, kwargs):
#        self._validate_args('install_icons', args, kwargs)
#
#        # TODO: Need to handle subdirectories of multiple icons and ensure they are valid
#        icondir = path.join(state.environment.get_datadir(), 'icons', 'hicolor')
#
#        post_target = self._create_post_install_script(state, [
#            'gtk-update-icon-cache', '--quiet', '--ignore-theme-index', icondir,
#        ])
#
#        return ModuleReturnValue([], [, post_target])


def initialize():
    return XdgModule()
