# Copyright 2015 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from .. import build
from .. import mesonlib
from .. import mlog
from . import ModuleReturnValue
from . import ExtensionModule


class PkgConfigModule(ExtensionModule):

    def _get_lname(self, l, msg, pcfile):
        # Nothing special
        if not l.name_prefix_set:
            return l.name
        # Sometimes people want the library to start with 'lib' everywhere,
        # which is achieved by setting name_prefix to '' and the target name to
        # 'libfoo'. In that case, try to get the pkg-config '-lfoo' arg correct.
        if l.prefix == '' and l.name.startswith('lib'):
            return l.name[3:]
        # If the library is imported via an import library which is always
        # named after the target name, '-lfoo' is correct.
        if l.import_filename:
            return l.name
        # In other cases, we can't guarantee that the compiler will be able to
        # find the library via '-lfoo', so tell the user that.
        mlog.warning(msg.format(l.name, 'name_prefix', l.name, pcfile))
        return l.name

    def generate_pkgconfig_file(self, state, libraries, subdirs, name, description,
                                url, version, pcfile, pub_reqs, priv_reqs,
                                conflicts, priv_libs, variables):
        coredata = state.environment.get_coredata()
        outdir = state.environment.scratch_dir
        fname = os.path.join(outdir, pcfile)
        with open(fname, 'w') as ofile:
            ofile.write('prefix=%s\n' % coredata.get_builtin_option('prefix'))
            # '${prefix}' is ignored if the second path is absolute (see
            # 'os.path.join' for details)
            ofile.write('libdir=%s\n' % os.path.join('${prefix}', coredata.get_builtin_option('libdir')))
            ofile.write('includedir=%s\n' % os.path.join('${prefix}', coredata.get_builtin_option('includedir')))
            for k, v in variables:
                ofile.write('%s=%s\n' % (k, v))
            ofile.write('\n')
            ofile.write('Name: %s\n' % name)
            if len(description) > 0:
                ofile.write('Description: %s\n' % description)
            if len(url) > 0:
                ofile.write('URL: %s\n' % url)
            ofile.write('Version: %s\n' % version)
            if len(pub_reqs) > 0:
                ofile.write('Requires: {}\n'.format(' '.join(pub_reqs)))
            if len(priv_reqs) > 0:
                ofile.write(
                    'Requires.private: {}\n'.format(' '.join(priv_reqs)))
            if len(conflicts) > 0:
                ofile.write('Conflicts: {}\n'.format(' '.join(conflicts)))

            def generate_libs_flags(libs):
                msg = 'Library target {0!r} has {1!r} set. Compilers ' \
                      'may not find it from its \'-l{2}\' linker flag in the ' \
                      '{3!r} pkg-config file.'
                for l in libs:
                    if isinstance(l, str):
                        yield l
                    else:
                        install_dir = l.get_custom_install_dir()[0]
                        if install_dir:
                            yield '-L${prefix}/%s ' % install_dir
                        else:
                            yield '-L${libdir}'
                        lname = self._get_lname(l, msg, pcfile)
                        # If using a custom suffix, the compiler may not be able to
                        # find the library
                        if l.name_suffix_set:
                            mlog.warning(msg.format(l.name, 'name_suffix', lname, pcfile))
                        yield '-l%s' % lname

            if len(libraries) > 0:
                ofile.write('Libs: {}\n'.format(' '.join(generate_libs_flags(libraries))))
            if len(priv_libs) > 0:
                ofile.write('Libs.private: {}\n'.format(' '.join(generate_libs_flags(priv_libs))))
            ofile.write('Cflags:')
            for h in subdirs:
                if h == '.':
                    h = ''
                ofile.write(' ')
                ofile.write(os.path.join('-I${includedir}', h))
            ofile.write('\n')

    def process_libs(self, libs):
        if not isinstance(libs, list):
            libs = [libs]
        processed_libs = []
        for l in libs:
            if hasattr(l, 'held_object'):
                l = l.held_object
            if not isinstance(l, (build.SharedLibrary, build.StaticLibrary, str)):
                raise mesonlib.MesonException('Library argument not a library object nor a string.')
            processed_libs.append(l)
        return processed_libs

    def generate(self, state, args, kwargs):
        if len(args) > 0:
            raise mesonlib.MesonException('Pkgconfig_gen takes no positional arguments.')
        libs = self.process_libs(kwargs.get('libraries', []))
        priv_libs = self.process_libs(kwargs.get('libraries_private', []))
        subdirs = mesonlib.stringlistify(kwargs.get('subdirs', ['.']))
        version = kwargs.get('version', None)
        if not isinstance(version, str):
            raise mesonlib.MesonException('Version must be specified.')
        name = kwargs.get('name', None)
        if not isinstance(name, str):
            raise mesonlib.MesonException('Name not specified.')
        filebase = kwargs.get('filebase', name)
        if not isinstance(filebase, str):
            raise mesonlib.MesonException('Filebase must be a string.')
        description = kwargs.get('description', None)
        if not isinstance(description, str):
            raise mesonlib.MesonException('Description is not a string.')
        url = kwargs.get('url', '')
        if not isinstance(url, str):
            raise mesonlib.MesonException('URL is not a string.')
        pub_reqs = mesonlib.stringlistify(kwargs.get('requires', []))
        priv_reqs = mesonlib.stringlistify(kwargs.get('requires_private', []))
        conflicts = mesonlib.stringlistify(kwargs.get('conflicts', []))

        def parse_variable_list(stringlist):
            reserved = ['prefix', 'libdir', 'includedir']
            variables = []
            for var in stringlist:
                # foo=bar=baz is ('foo', 'bar=baz')
                l = var.split('=', 1)
                if len(l) < 2:
                    raise mesonlib.MesonException('Variables must be in \'name=value\' format')

                name, value = l[0].strip(), l[1].strip()
                if not name or not value:
                    raise mesonlib.MesonException('Variables must be in \'name=value\' format')

                # Variable names must not contain whitespaces
                if any(c.isspace() for c in name):
                    raise mesonlib.MesonException('Invalid whitespace in assignment "{}"'.format(var))

                if name in reserved:
                    raise mesonlib.MesonException('Variable "{}" is reserved'.format(name))

                variables.append((name, value))

            return variables

        variables = parse_variable_list(mesonlib.stringlistify(kwargs.get('variables', [])))

        pcfile = filebase + '.pc'
        pkgroot = kwargs.get('install_dir', None)
        if pkgroot is None:
            pkgroot = os.path.join(state.environment.coredata.get_builtin_option('libdir'), 'pkgconfig')
        if not isinstance(pkgroot, str):
            raise mesonlib.MesonException('Install_dir must be a string.')
        self.generate_pkgconfig_file(state, libs, subdirs, name, description, url,
                                     version, pcfile, pub_reqs, priv_reqs,
                                     conflicts, priv_libs, variables)
        res = build.Data(mesonlib.File(True, state.environment.get_scratch_dir(), pcfile), pkgroot)
        return ModuleReturnValue(res, [res])

def initialize():
    return PkgConfigModule()
