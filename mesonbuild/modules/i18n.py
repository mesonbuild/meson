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

from .. import coredata, mesonlib, build
import sys

class I18nModule:

    def gettext(self, state, args, kwargs):
        if len(args) != 1:
            raise coredata.MesonException('Gettext requires one positional argument (package name).')
        packagename = args[0]
        languages = mesonlib.stringlistify(kwargs.get('languages', []))
        if len(languages) == 0:
            raise coredata.MesonException('List of languages empty.')
        datadirs = mesonlib.stringlistify(kwargs.get('data_dirs', []))
        extra_args = mesonlib.stringlistify(kwargs.get('args', []))

        pkg_arg = '--pkgname=' + packagename
        lang_arg = '--langs=' + '@@'.join(languages)
        datadirs = '--datadirs=' + ':'.join(datadirs) if datadirs else None
        extra_args = '--extra-args=' + '@@'.join(extra_args) if extra_args else None

        potargs = [state.environment.get_build_command(), '--internal', 'gettext', 'pot', pkg_arg]
        if datadirs:
            potargs.append(datadirs)
        if extra_args:
            potargs.append(extra_args)
        pottarget = build.RunTarget(packagename + '-pot', sys.executable, potargs, [], state.subdir)

        gmoargs = [state.environment.get_build_command(), '--internal', 'gettext', 'gen_gmo', lang_arg]
        gmotarget = build.RunTarget(packagename + '-gmo', sys.executable, gmoargs, [], state.subdir)

        updatepoargs = [state.environment.get_build_command(), '--internal', 'gettext', 'update_po', pkg_arg, lang_arg]
        if datadirs:
            updatepoargs.append(datadirs)
        if extra_args:
            updatepoargs.append(extra_args)
        updatepotarget = build.RunTarget(packagename + '-update-po', sys.executable, updatepoargs, [], state.subdir)

        installcmd = [sys.executable, state.environment.get_build_command(),
                      '--internal', 'gettext', 'install',
                      '--subdir=' + state.subdir,
                      '--localedir=' + state.environment.coredata.get_builtin_option('localedir'),
                      pkg_arg, lang_arg]
        iscript = build.InstallScript(installcmd)

        return [pottarget, gmotarget, iscript, updatepotarget]

def initialize():
    return I18nModule()
