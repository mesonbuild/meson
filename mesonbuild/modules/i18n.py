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

from os import path
from .. import coredata, mesonlib, build
from ..mesonlib import MesonException
import sys

PRESET_ARGS = {
    'glib': [
        '--from-code=UTF-8',
        '--add-comments',

        # https://developer.gnome.org/glib/stable/glib-I18N.html
        '--keyword=_',
        '--keyword=N_',
        '--keyword=C_:1c,2',
        '--keyword=NC_:1c,2',
        '--keyword=g_dcgettext:2',
        '--keyword=g_dngettext:2,3',
        '--keyword=g_dpgettext2:2c,3',

        '--flag=N_:1:pass-c-format',
        '--flag=C_:2:pass-c-format',
        '--flag=NC_:2:pass-c-format',
        '--flag=g_dngettext:2:pass-c-format',
        '--flag=g_strdup_printf:1:c-format',
        '--flag=g_string_printf:2:c-format',
        '--flag=g_string_append_printf:2:c-format',
        '--flag=g_error_new:3:c-format',
        '--flag=g_set_error:4:c-format',
    ]
}

class I18nModule:

    def merge_file(self, state, args, kwargs):
        podir = kwargs.pop('po_dir', None)
        if not podir:
            raise MesonException('i18n: po_dir is a required kwarg')
        podir = path.join(state.build_to_src, state.subdir, podir)

        file_type = kwargs.pop('type', 'xml')
        VALID_TYPES = ('xml', 'desktop')
        if not file_type in VALID_TYPES:
            raise MesonException('i18n: "{}" is not a valid type {}'.format(file_type, VALID_TYPES))

        kwargs['command'] = ['msgfmt', '--' + file_type,
                             '--template', '@INPUT@', '-d', podir, '-o', '@OUTPUT@']
        return build.CustomTarget(kwargs['output'] + '_merge', state.subdir, kwargs)

    def gettext(self, state, args, kwargs):
        if len(args) != 1:
            raise coredata.MesonException('Gettext requires one positional argument (package name).')
        packagename = args[0]
        languages = mesonlib.stringlistify(kwargs.get('languages', []))
        datadirs = mesonlib.stringlistify(kwargs.get('data_dirs', []))
        extra_args = mesonlib.stringlistify(kwargs.get('args', []))

        preset = kwargs.pop('preset', None)
        if preset:
            preset_args = PRESET_ARGS.get(preset)
            if not preset_args:
                raise coredata.MesonException('i18n: Preset "{}" is not one of the valid options: {}'.format(
                                              preset, list(PRESET_ARGS.keys())))
            extra_args = set(preset_args + extra_args)

        pkg_arg = '--pkgname=' + packagename
        lang_arg = '--langs=' + '@@'.join(languages) if languages else None
        datadirs = '--datadirs=' + ':'.join(datadirs) if datadirs else None
        extra_args = '--extra-args=' + '@@'.join(extra_args) if extra_args else None

        potargs = [state.environment.get_build_command(), '--internal', 'gettext', 'pot', pkg_arg]
        if datadirs:
            potargs.append(datadirs)
        if extra_args:
            potargs.append(extra_args)
        pottarget = build.RunTarget(packagename + '-pot', sys.executable, potargs, [], state.subdir)

        gmoargs = [state.environment.get_build_command(), '--internal', 'gettext', 'gen_gmo']
        if lang_arg:
            gmoargs.append(lang_arg)
        gmotarget = build.RunTarget(packagename + '-gmo', sys.executable, gmoargs, [], state.subdir)

        updatepoargs = [state.environment.get_build_command(), '--internal', 'gettext', 'update_po', pkg_arg]
        if lang_arg:
            updatepoargs.append(lang_arg)
        if datadirs:
            updatepoargs.append(datadirs)
        if extra_args:
            updatepoargs.append(extra_args)
        updatepotarget = build.RunTarget(packagename + '-update-po', sys.executable, updatepoargs, [], state.subdir)

        script = [sys.executable,  state.environment.get_build_command()]
        args = ['--internal', 'gettext', 'install',
                '--subdir=' + state.subdir,
                '--localedir=' + state.environment.coredata.get_builtin_option('localedir'),
                pkg_arg]
        if lang_arg:
            args.append(lang_arg)
        iscript = build.RunScript(script, args)

        return [pottarget, gmotarget, iscript, updatepotarget]

def initialize():
    return I18nModule()
