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

import shutil

from os import path
from .. import coredata, mesonlib, build
from ..mesonlib import MesonException
from . import ModuleReturnValue
from . import ExtensionModule
from ..interpreterbase import permittedKwargs, FeatureNew, FeatureNewKwargs

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

class I18nModule(ExtensionModule):

    @staticmethod
    def _get_data_dirs(state, dirs):
        """Returns source directories of relative paths"""
        src_dir = path.join(state.environment.get_source_dir(), state.subdir)
        return [path.join(src_dir, d) for d in dirs]

    @FeatureNew('i18n.merge_file', '0.37.0')
    @permittedKwargs({'languages', 'data_dirs', 'preset', 'args', 'po_dir', 'type',
                      'input', 'output', 'install', 'install_dir'})
    def merge_file(self, state, args, kwargs):
        podir = kwargs.pop('po_dir', None)
        if not podir:
            raise MesonException('i18n: po_dir is a required kwarg')
        podir = path.join(state.build_to_src, state.subdir, podir)

        file_type = kwargs.pop('type', 'xml')
        VALID_TYPES = ('xml', 'desktop')
        if file_type not in VALID_TYPES:
            raise MesonException('i18n: "{}" is not a valid type {}'.format(file_type, VALID_TYPES))

        datadirs = self._get_data_dirs(state, mesonlib.stringlistify(kwargs.pop('data_dirs', [])))
        datadirs = '--datadirs=' + ':'.join(datadirs) if datadirs else None

        command = state.environment.get_build_command() + [
            '--internal', 'msgfmthelper',
            '@INPUT@', '@OUTPUT@', file_type, podir
        ]
        if datadirs:
            command.append(datadirs)

        kwargs['command'] = command

        inputfile = kwargs['input']
        if isinstance(inputfile, str):
            inputfile = mesonlib.File.from_source_file(state.environment.source_dir,
                                                       state.subdir, inputfile)
        output = kwargs['output']
        ifile_abs = inputfile.absolute_path(state.environment.source_dir,
                                            state.environment.build_dir)
        values = mesonlib.get_filenames_templates_dict([ifile_abs], None)
        outputs = mesonlib.substitute_values([output], values)
        output = outputs[0]

        ct = build.CustomTarget(output + '_' + state.subdir + '_merge', state.subdir, state.subproject, kwargs)
        return ModuleReturnValue(ct, [ct])

    @FeatureNewKwargs('i18n.gettext', '0.37.0', ['preset'])
    @permittedKwargs({'po_dir', 'data_dirs', 'type', 'languages', 'args', 'preset', 'install'})
    def gettext(self, state, args, kwargs):
        if len(args) != 1:
            raise coredata.MesonException('Gettext requires one positional argument (package name).')
        if not shutil.which('xgettext'):
            raise coredata.MesonException('Can not do gettext because xgettext is not installed.')
        packagename = args[0]
        languages = mesonlib.stringlistify(kwargs.get('languages', []))
        datadirs = self._get_data_dirs(state, mesonlib.stringlistify(kwargs.get('data_dirs', [])))
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

        potargs = state.environment.get_build_command() + ['--internal', 'gettext', 'pot', pkg_arg]
        if datadirs:
            potargs.append(datadirs)
        if extra_args:
            potargs.append(extra_args)
        pottarget = build.RunTarget(packagename + '-pot', potargs[0], potargs[1:], [], state.subdir, state.subproject)

        gmoargs = state.environment.get_build_command() + ['--internal', 'gettext', 'gen_gmo']
        if lang_arg:
            gmoargs.append(lang_arg)
        gmotarget = build.RunTarget(packagename + '-gmo', gmoargs[0], gmoargs[1:], [], state.subdir, state.subproject)

        updatepoargs = state.environment.get_build_command() + ['--internal', 'gettext', 'update_po', pkg_arg]
        if lang_arg:
            updatepoargs.append(lang_arg)
        if datadirs:
            updatepoargs.append(datadirs)
        if extra_args:
            updatepoargs.append(extra_args)
        updatepotarget = build.RunTarget(packagename + '-update-po', updatepoargs[0], updatepoargs[1:], [], state.subdir, state.subproject)

        targets = [pottarget, gmotarget, updatepotarget]

        install = kwargs.get('install', True)
        if install:
            script = state.environment.get_build_command()
            args = ['--internal', 'gettext', 'install',
                    '--subdir=' + state.subdir,
                    '--localedir=' + state.environment.coredata.get_builtin_option('localedir'),
                    pkg_arg]
            if lang_arg:
                args.append(lang_arg)
            iscript = build.RunScript(script, args)
            targets.append(iscript)

        return ModuleReturnValue(None, targets)

def initialize(*args, **kwargs):
    return I18nModule(*args, **kwargs)
