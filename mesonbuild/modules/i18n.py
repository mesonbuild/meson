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
import os

class I18nModule:

    def __get_languages(self, state, source_po_dir, kwargs):
        languages = mesonlib.stringlistify(kwargs.get('languages', []))
        if len(languages) == 0:
            try:
                with open(os.path.join(source_po_dir, 'LINGUAS')) as f:
                    lines = f.readlines()
                    for line in lines:
                        line = line.strip()
                        if len(line) > 0 and not line.startswith('#'):
                            languages.append(line)
            except OSError:
                pass
        return languages

    def gettext(self, state, args, kwargs):
        if len(args) != 1:
            packagename = state.project_name
        else:
            packagename = args[0]

        languages = self.__get_languages(state,
                                         os.path.join(state.environment.get_source_dir(), state.subdir),
                                         kwargs)
        if len(languages) == 0:
            raise coredata.MesonException('No languages were provided and the LINGUAS file was not found or has not any languages.')

        targets = []
        for language in languages:
            gmo_filename = language + '.gmo'

            options = {'command': ['msgfmt', '@INPUT@', '-o', '@OUTPUT@'],
                       'input': language + '.po',
                       'output': gmo_filename}
            build_target = build.CustomTarget(packagename + '_' + language + '_gmo',
                                              state.subdir, options)

            install_target = build.Data(False, state.subdir, [gmo_filename],
                                        os.path.join(state.environment.coredata.get_builtin_option('localedir'),
                                                     language, 'LC_MESSAGES'),
                                        {gmo_filename: packagename + '.mo'})

            targets.append(build_target)
            targets.append(install_target)

        pot_target = build.RunTarget(packagename + '-pot', 'intltool-update',
                                     ['-p', '-g', packagename], state.subdir)
        targets.append(pot_target)

        return targets

    def intltool_merge(self, state, args, kwargs):
        _input = kwargs.get('input')
        if not _input:
            raise coredata.MesonException('input parameter is required.')

        style = kwargs.get('style')
        if not style:
            raise coredata.MesonException('style parameter is required.')

        # If output is not provided, use the input filename without the extension.
        # Useful when using files like org.example.MyApp.desktop.in
        output = kwargs.get('output', os.path.splitext(os.path.split(_input)[1])[0])
        po_dir = kwargs.get('po_dir', '.')
        source_po_dir = os.path.join(state.environment.get_source_dir(), state.subdir, po_dir)
        build_po_dir = os.path.join(state.environment.get_build_dir(), state.subdir, po_dir)
        languages = self.__get_languages(state, source_po_dir, kwargs)

        install = kwargs.get('install', False)
        install_dir = kwargs.get('install_dir')
        if install and not install_dir:
            raise coredata.MesonException('install_dir parameter is required when install is true')

        options = {'command': ['intltool-merge',
                               '--{}-style'.format(style), '-q',
                               '-c', os.path.join(build_po_dir, '.intltool-merge-cache'),
                               source_po_dir, '@INPUT@', '@OUTPUT@'],
                   'input': _input,
                   'output': output,
                   'install': install,
                   'install_dir': install_dir,
                   'depend_files': [os.path.join(source_po_dir, l) + '.po' for l in languages]}
        return build.CustomTarget('intltool-merge-' + _input, state.subdir, options)

def initialize():
    return I18nModule()
