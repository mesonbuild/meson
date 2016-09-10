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

from .. import coredata, build
from .. import mesonlib
import os

class PkgConfigModule:

    def generate_pkgconfig_file(self, state, libraries, subdirs, name, description, version, filebase,
                                pub_reqs, priv_reqs, priv_libs):
        coredata = state.environment.get_coredata()
        outdir = state.environment.scratch_dir
        fname = os.path.join(outdir, filebase + '.pc')
        with open(fname, 'w') as ofile:
            ofile.write('prefix=%s\n' % coredata.get_builtin_option('prefix'))
            ofile.write('libdir=${prefix}/%s\n' %
                        coredata.get_builtin_option('libdir'))
            ofile.write('includedir=${prefix}/%s\n\n' %
                        coredata.get_builtin_option('includedir'))
            ofile.write('Name: %s\n' % name)
            if len(description) > 0:
                ofile.write('Description: %s\n' % description)
            if len(version) > 0:
                ofile.write('Version: %s\n' % version)
            if len(pub_reqs) > 0:
                ofile.write('Requires: {}\n'.format(' '.join(pub_reqs)))
            if len(priv_reqs) > 0:
                ofile.write(
                    'Requires.private: {}\n'.format(' '.join(priv_reqs)))
            if len(priv_libs) > 0:
                ofile.write(
                    'Libraries.private: {}\n'.format(' '.join(priv_libs)))
            ofile.write('Libs: -L${libdir} ')
            for l in libraries:
                if l.custom_install_dir:
                    ofile.write('-L${prefix}/%s ' % l.custom_install_dir)
                ofile.write('-l%s ' % l.name)
            ofile.write('\n')
            ofile.write('CFlags: ')
            for h in subdirs:
                if h == '.':
                    h = ''
                ofile.write(os.path.join('-I${includedir}', h))
                ofile.write(' ')
            ofile.write('\n')

    def generate(self, state, args, kwargs):
        if len(args) > 0:
            raise mesonlib.MesonException('Pkgconfig_gen takes no positional arguments.')
        libs = kwargs.get('libraries', [])
        if not isinstance(libs, list):
            libs = [libs]
        processed_libs = []
        for l in libs:
            if hasattr(l, 'held_object'):
                l = l.held_object
            if not isinstance(l, (build.SharedLibrary, build.StaticLibrary)):
                raise mesonlib.MesonException('Library argument not a library object.')
            processed_libs.append(l)
        libs = processed_libs
        subdirs = mesonlib.stringlistify(kwargs.get('subdirs', ['.']))
        version = kwargs.get('version', '')
        if not isinstance(version, str):
            raise mesonlib.MesonException('Version must be a string.')
        name = kwargs.get('name', None)
        if not isinstance(name, str):
            raise mesonlib.MesonException('Name not specified.')
        filebase = kwargs.get('filebase', name)
        if not isinstance(filebase, str):
            raise mesonlib.MesonException('Filebase must be a string.')
        description = kwargs.get('description', None)
        if not isinstance(description, str):
            raise mesonlib.MesonException('Description is not a string.')
        pub_reqs = mesonlib.stringlistify(kwargs.get('requires', []))
        priv_reqs = mesonlib.stringlistify(kwargs.get('requires_private', []))
        priv_libs = mesonlib.stringlistify(kwargs.get('libraries_private', []))
        pcfile = filebase + '.pc'
        pkgroot = kwargs.get('install_dir',None)
        if pkgroot is None:
            pkgroot = os.path.join(state.environment.coredata.get_builtin_option('libdir'), 'pkgconfig')
        if not isinstance(pkgroot, str):
            raise mesonlib.MesonException('Install_dir must be a string.')
        self.generate_pkgconfig_file(state, libs, subdirs, name, description, version, filebase,
                                     pub_reqs, priv_reqs, priv_libs)
        return build.Data(False, state.environment.get_scratch_dir(), [pcfile], pkgroot)

def initialize():
    return PkgConfigModule()
