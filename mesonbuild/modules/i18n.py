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
import shutil
import pickle

from os import path
from .. import coredata, mesonlib, build
from ..mesonlib import MesonException
from . import ModuleReturnValue
from . import ExtensionModule
from . import permittedKwargs
from ..interpreterbase import InterpreterObject

PRESET_ARGS = {
    'none': {
        'args': [],
        'keywords': [],
        'flags': [],
    },

    'glib': {
        'args': [
            '--from-code=UTF-8',
            '--add-comments',
        ],

        # https://developer.gnome.org/glib/stable/glib-I18N.html
        'keywords': [
            '_',
            'N_',
            'C_:1c,2',
            'NC_:1c,2',
            'g_dcgettext:2',
            'g_dngettext:2,3',
            'g_dpgettext2:2c,3',
        ],

        'flags': [
            'N_:1:pass-c-format',
            'C_:2:pass-c-format',
            'NC_:2:pass-c-format',
            'g_dngettext:2:pass-c-format',
            'g_strdup_printf:1:c-format',
            'g_string_printf:2:c-format',
            'g_string_append_printf:2:c-format',
            'g_error_new:3:c-format',
            'g_set_error:4:c-format',
        ],
    },
}

class I18nFilesHolder(InterpreterObject):

    def __init__(self, files):
        super().__init__()
        self.held_object = files


class I18nFiles:

    @staticmethod
    def _flatten_files(args, source_dir, subdir):
        files = []
        for f in args:
            if isinstance(f, str):
                files.append(mesonlib.File.from_source_file(source_dir, subdir, f))
            elif isinstance(f, mesonlib.File):
                files.append(f)
            elif isinstance(f, list):
                files += I18nFiles._flatten_files(f, source_dir, subdir)
            else:
                raise coredata.MesonException('i18n: Files argument must be a files() object')

        return files

    def __init__(self, interpreter, args, kwargs):
        super().__init__()
        if len(args) < 1:
            raise coredata.MesonException('add_files requires at least one positional argument (file).')

        I18nModule._check_preset(kwargs)

        self.subdir = interpreter.subdir
        self.files = self._flatten_files(args, interpreter.environment.source_dir, self.subdir)
        self.preset = kwargs.pop('preset', 'none')
        self.language = kwargs.pop('language', None)
        self.keywords = mesonlib.stringlistify(kwargs.pop('keywords', []))
        self.flags = mesonlib.stringlistify(kwargs.pop('flags', []))
        self.extra_args = mesonlib.stringlistify(kwargs.pop('extra_args', []))

        self.merge_files = []
        if len(kwargs) == 0:
            return

        MERGE_LANGUAGES = ('xml', 'desktop')
        if self.language not in MERGE_LANGUAGES:
            raise MesonException('i18n: "{}" is not a valid merge language {}'.format(self.language, MERGE_LANGUAGES))

        if not kwargs.pop('merge', True):
            return

        suffix = kwargs.pop('suffix', None)

        for f in self.files:
            kwargs['input'] = f
            f = path.basename(f.relative_name())
            if suffix and f.endswith(suffix):
                f = f[0:f.index(suffix)]
            kwargs['output'] = f
            self.merge_files.append(kwargs)

class I18nModule(ExtensionModule):

    @staticmethod
    def _check_preset(kwargs):
        preset = kwargs.get('preset', 'none')
        if preset not in PRESET_ARGS:
            raise coredata.MesonException('i18n: Preset "{}" is not one of the valid options: {}'.format(
                                          preset, list(PRESET_ARGS.keys())))

    @staticmethod
    def _get_data_dirs(environment, subdir, dirs):
        """Returns source directories of relative paths"""
        src_dir = path.join(environment.get_source_dir(), subdir)
        return [path.join(src_dir, d) for d in dirs]

    def __init__(self):
        super().__init__()
        self.snippets.add('files')

    @permittedKwargs({'data_dirs', 'po_dir', 'type', 'input', 'output', 'install', 'install_dir'})
    def merge_file(self, state, args, kwargs):
        podir = kwargs.pop('po_dir', None)
        if not podir:
            raise MesonException('i18n: po_dir is a required kwarg')
        podir = path.join(state.build_to_src, state.subdir, podir)

        file_type = kwargs.pop('type', 'xml')
        VALID_TYPES = ('xml', 'desktop')
        if file_type not in VALID_TYPES:
            raise MesonException('i18n: "{}" is not a valid type {}'.format(file_type, VALID_TYPES))

        datadirs = self._get_data_dirs(state.environment, state.subdir, mesonlib.stringlistify(kwargs.pop('data_dirs', [])))
        datadirs = '--datadirs=' + ':'.join(datadirs) if datadirs else None

        command = [state.environment.get_build_command(), '--internal', 'msgfmthelper',
                   '@INPUT@', '@OUTPUT@', file_type, podir]
        if datadirs:
            command.append(datadirs)

        kwargs['command'] = command
        ct = build.CustomTarget(kwargs['output'] + '_merge', state.subdir, kwargs)
        return ModuleReturnValue(ct, [ct])

    @permittedKwargs({'preset', 'data_dirs', 'languages', 'args'})
    def gettext(self, state, args, kwargs):
        if len(args) != 1:
            raise coredata.MesonException('Gettext requires one positional argument (package name).')
        if not shutil.which('xgettext'):
            raise coredata.MesonException('Can not do gettext because xgettext is not installed.')
        packagename = args[0]
        languages = mesonlib.stringlistify(kwargs.get('languages', []))
        datadirs = self._get_data_dirs(state.environment, state.subdir, mesonlib.stringlistify(kwargs.get('data_dirs', [])))
        extra_args = mesonlib.stringlistify(kwargs.get('args', []))

        preset = kwargs.pop('preset', 'none')
        if preset:
            if preset not in PRESET_ARGS:
                raise coredata.MesonException('i18n: Preset "{}" is not one of the valid options: {}'.format(
                                              preset, list(PRESET_ARGS.keys())))
            preset = PRESET_ARGS.get(preset)
            extra_args = set(preset['args'] +
                             ['--keyword=' + k for k in preset['keywords']] +
                             ['--flag=' + f for f in preset['flags']] +
                             extra_args)

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

        script = [sys.executable, state.environment.get_build_command()]
        args = ['--internal', 'gettext', 'install',
                '--subdir=' + state.subdir,
                '--localedir=' + state.environment.coredata.get_builtin_option('localedir'),
                pkg_arg]
        if lang_arg:
            args.append(lang_arg)
        iscript = build.RunScript(script, args)

        return ModuleReturnValue(None, [pottarget, gmotarget, iscript, updatepotarget])

#    @permittedKwargs({'language', 'keywords', 'preset'} + (permitted_kwargs['custom_target'] - {'input', 'output', 'capture', 'command', 'depfile'}))
    def files(self, interpreter, state, args, kwargs):
        return I18nFilesHolder(I18nFiles(interpreter, args, kwargs))

    @staticmethod
    def _flatten_files(args):
        i18n_files = []
        files = []
        for f in args:
            if isinstance(f, I18nFilesHolder):
                i18n_files.append(f)
            elif isinstance(f, mesonlib.File):
                files.append(f)
            elif isinstance(f, list):
                r = I18nModule._flatten_files(f)
                i18n_files += r[0]
                files += r[1]
            else:
                raise coredata.MesonException('i18n: Files argument must be an object from i18n.files() or files()')

        return [i18n_files, files]

    @permittedKwargs({'languages', 'data_dirs', 'preset'})
    def create_pot(self, state, args, kwargs):
        if len(args) < 2:
            raise coredata.MesonException('Gettext requires at least two positional argument (package name and files).')
        if not shutil.which('xgettext'):
            raise coredata.MesonException('Can not do gettext because xgettext is not installed.')
        packagename = args.pop(0)
        [i18n_files, files] = self._flatten_files(args)
        languages = mesonlib.stringlistify(kwargs.get('languages', []))
        datadirs = self._get_data_dirs(state.environment, state.subdir, mesonlib.stringlistify(kwargs.get('data_dirs', [])))

        preset = kwargs.pop('preset', 'none')
        if preset:
            if preset not in PRESET_ARGS:
                raise coredata.MesonException('i18n: Preset "{}" is not one of the valid options: {}'.format(
                                              preset, list(PRESET_ARGS.keys())))
            preset = PRESET_ARGS.get(preset)

        pkg_arg = '--pkgname=' + packagename
        lang_arg = '--langs=' + '@@'.join(languages) if languages else None
        datadirs = '--datadirs=' + ':'.join(datadirs) if datadirs else None

        source_dir = state.environment.get_source_dir()
        build_dir = state.environment.get_build_dir()
        # Generate a data file to run xgettext
        data_files = []
        for file_set in i18n_files:
            file_set = file_set.held_object
            p = PRESET_ARGS.get(file_set.preset)
            data_files.append({
                'files': [f.relative_name() for f in file_set.files],
                'language': file_set.language,
                'keywords': preset['keywords'] + p['keywords'] + file_set.keywords,
                'flags': preset['flags'] + p['flags'] + file_set.flags,
                'extra_args': preset['args'] + p['args'] + file_set.extra_args,
            })
        if len(files) > 0:
            data_files.append({
                'files': [f.relative_name() for f in files],
                'language': None,
                'keywords': preset['keywords'],
                'flags': preset['flags'],
                'extra_args': preset['args'],
            })

        pot_data_file = path.join(state.environment.get_scratch_dir(), 'i18n-' + packagename + '-pot.dat')
        pot_data_file_arg = '--datafilename=' + pot_data_file
        with open(pot_data_file, 'wb') as data_file:
            pickle.dump(data_files, data_file)

        potargs = [state.environment.get_build_command(), '--internal', 'gettext', 'pot', pkg_arg, pot_data_file_arg]
        if datadirs:
            potargs.append(datadirs)
        pottarget = build.RunTarget(packagename + '-pot', sys.executable, potargs, [], state.subdir)

        gmoargs = [state.environment.get_build_command(), '--internal', 'gettext', 'gen_gmo']
        if lang_arg:
            gmoargs.append(lang_arg)
        gmotarget = build.RunTarget(packagename + '-gmo', sys.executable, gmoargs, [], state.subdir)

        updatepoargs = [state.environment.get_build_command(), '--internal', 'gettext', 'update_po', pkg_arg, pot_data_file_arg]
        if lang_arg:
            updatepoargs.append(lang_arg)
        if datadirs:
            updatepoargs.append(datadirs)
        updatepotarget = build.RunTarget(packagename + '-update-po', sys.executable, updatepoargs, [], state.subdir)

        script = [sys.executable, state.environment.get_build_command()]
        args = ['--internal', 'gettext', 'install',
                '--subdir=' + state.subdir,
                '--localedir=' + state.environment.coredata.get_builtin_option('localedir'),
                pkg_arg]
        if lang_arg:
            args.append(lang_arg)
        iscript = build.RunScript(script, args)

        podir = path.join(path.relpath(source_dir, build_dir), state.subdir)

        merge_targets = []
        for f in i18n_files:
            f = f.held_object
            p = PRESET_ARGS.get(f.preset)
            command = [state.environment.get_build_command(), '--internal', 'msgfmthelper',
                       '@INPUT@', '@OUTPUT@', f.language, podir]
            if datadirs:
                command.append(datadirs)
            command.append('--')
            for k in preset['keywords'] + p['keywords'] + f.keywords:
                command.append('--keyword=' + k)
            for mk in f.merge_files:
                mk['command'] = command
                merge_targets.append(build.CustomTarget(mk['output'], f.subdir, mk))

        return ModuleReturnValue(merge_targets, [pottarget, gmotarget, iscript, updatepotarget] + merge_targets)

def initialize():
    return I18nModule()
