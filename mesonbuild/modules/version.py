# Copyright 2019 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os, re
from collections import namedtuple

from .. import build, mesonlib
from . import ModuleReturnValue
from . import ExtensionModule
from ..interpreterbase import permittedKwargs, FeatureNew, FeatureNewKwargs

Version = namedtuple('Version', ('major', 'minor', 'patch', 'string'))

class VersionModule(ExtensionModule):

    def _configuration_data(self, *args, **kwargs):
        return self.interpreter.funcs['configuration_data'](None, args, kwargs)

    def _configure_file(self, *args, **kwargs):
        return self.interpreter.funcs['configure_file'](None, args, kwargs)

    def _version(self, state, args, kwargs):
        string = kwargs.get('version', state.project_version['version'])
        if not isinstance(string, str):
            raise mesonlib.MesonException('Version must be a string.')
        parts = string.split('.')

        def _parse(l, i):
            try:
                return int(l[i])
            except (ValueError, IndexError):
                return None

        major = _parse(parts, 0)
        minor = _parse(parts, 1)
        patch = _parse(parts, 2)

        return Version(major, minor, patch, string)

    def _namespace(self, state, args, kwargs):
        try:
            return tuple(kwargs['namespace'].split('::'))
        except KeyError:
            return (re.sub(r'[/\?%*:|"<>."]+', '_', state.project_name),)

    def _input(self, state, args, kwargs):
        try:
            input = kwargs['input']
            if not isinstance(input, str):
                raise mesonlib.MesonException('Input must be a string.')
            return input
        except KeyError:
            filename = __loader__.get_filename()
            dirname = os.path.dirname(filename)
            return os.path.join(dirname, 'version', 'version.h.in')

    def _output(self, state, args, kwargs):
        try:
            output = kwargs['output']
            if not isinstance(output, str):
                raise mesonlib.MesonException('Output must be a string.')
            return output
        except KeyError:
            return '@BASENAME@'

    def _license(self, state, args, kwargs):
        def _read(p):
            with open(p) as file:
                return file.read()

        try:
            license = kwargs['license']
            try:
                license = _read(license)
            except OSError:
                pass
        except KeyError:
            extensions = ('', '.md')
            paths = ('LICENSE%s' % e for e in extensions)
            for path in paths:
                try:
                    license = _read(path)
                except OSError:
                    continue

        if not isinstance(license, str):
            raise mesonlib.MesonException('License must be a string or filename.')
        return tuple(license.splitlines())

    def _newline(self, state, args, kwargs):
        # TODO: determine from `license` what newline is
        return kwargs.get('newline', os.linesep)

    def _define(self, state, args, kwargs):
        namespace = self._namespace(state, args, kwargs)
        joined = '_'.join(namespace)
        upper = joined.upper()
        sanitized = re.sub(r'[^A-Z0-9_]+', '_', upper)
        return sanitized

    def _header_guard(self, state, args, kwargs):
        header_guard = kwargs.get('header_guard', 'pragma')
        newline = self._newline(state, args, kwargs)
        if not isinstance(header_guard, str):
            raise mesonlib.MesonException('Header guard must be a string.')
        if header_guard == 'pragma':
            return '{n}#pragma once{n}'.format(n=newline), ''
        if header_guard == 'macro':
            define = header_guard
        else:
            define = self._define(state, args, kwargs)
        begin = '{n}#ifndef {d}{n}#define {d}{n}'.format(d=define, n=newline)
        end = '{newline}#endif  /* {define} */'.format(d=define, n=newline)
        return begin, end

    def _configuration(self, state, args, kwargs):
        version = self._version(state, args, kwargs)

        license = self._newline(state, args, kwargs).join((
            ('/**', ' * @copyright') +
            tuple(' * %s' % l for l in self._license(state, args, kwargs)) +
            (' */',)
        ))

        header_guard = self._header_guard(state, args, kwargs)
        header_guard_begin, header_guard_end = header_guard

        has_version_major = 0 if version.major is None else 1
        has_version_minor = 0 if version.minor is None else 1
        has_version_patch = 0 if version.patch is None else 1

        namespace = self._namespace(state, args, kwargs)
        define = '_'.join((self._define(state, args, kwargs), 'VERSION'))

        dict = {
          'license': license,
          'header_guard_begin': header_guard_begin,
          'header_guard_end': header_guard_end,
          'version': version.string,
          'has_version_major': has_version_major,
          'has_version_minor': has_version_minor,
          'has_version_patch': has_version_patch,
          'version_define': define,
          'version_major_define': '_'.join((define, 'MAJOR')),
          'version_minor_define': '_'.join((define, 'MINOR')),
          'version_patch_define': '_'.join((define, 'PATCH')),
        }

        if has_version_major:
            dict['version_major'] = version.major
        if has_version_minor:
            dict['version_minor'] = version.minor
        if has_version_patch:
            dict['version_patch'] = version.patch

        return self._configuration_data(dict)

    def _install(self, state, args, kwargs):
        install = kwargs.get('install', True)
        if not isinstance(install, bool):
            raise mesonlib.MesonException('Install must be a boolean.')
        return install

    def _install_dir(self, state, args, kwargs):
        try:
            install_dir = kwargs['install_dir']
            if not isinstance(install_dir, str):
                raise mesonlib.MesonException('Install directory must be a string.')
            return install_dir
        except KeyError:
            namespace = self._namespace(state, args, kwargs)
            return os.path.join('include', *namespace)

    @permittedKwargs({'input', 'output', 'configuration', 'install',
                      'install_dir', 'version', 'namespace', 'license',
                      'header_guard', 'header_guard', 'newline'})
    def configure_file(self, state, args, kwargs):
        install_dir = self._install_dir(state, args, kwargs)
        generated = self._configure_file(
            input = self._input(state, args, kwargs),
            output = self._output(state, args, kwargs),
            configuration = self._configuration(state, args, kwargs),
            install = self._install(state, args, kwargs),
            install_dir = install_dir,
        )

        res = build.Data(generated, install_dir)

        return ModuleReturnValue(res, [res])

def initialize(*args, **kwargs):
    return VersionModule(*args, **kwargs)
