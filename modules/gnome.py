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

'''This module provides helper functions for Gnome/GLib related
functionality such as gobject-introspection and gresources.'''

import build
import os
import subprocess
from coredata import MesonException
import mlog

class GnomeModule:

    def compile_resources(self, state, args, kwargs):
        cmd = ['glib-compile-resources', '@INPUT@', '--generate']
        if 'source_dir' in kwargs:
            d = os.path.join(state.build_to_src, state.subdir, kwargs.pop('source_dir'))
            cmd += ['--sourcedir', d]
        if 'c_name' in kwargs:
            cmd += ['--c-name', kwargs.pop('c_name')]
        cmd += ['--target', '@OUTPUT@']
        kwargs['command'] = cmd
        output_c = args[0] + '.c'
        output_h = args[0] + '.h'
        kwargs['input'] = args[1]
        kwargs['output'] = output_c
        target_c = build.CustomTarget(args[0]+'_c', state.subdir, kwargs)
        kwargs['output'] = output_h
        target_h = build.CustomTarget(args[0] + '_h', state.subdir, kwargs)
        return [target_c, target_h]
    
    def generate_gir(self, state, args, kwargs):
        if len(args) != 1:
            raise MesonException('Gir takes one argument')
        girtarget = args[0]
        while hasattr(girtarget, 'held_object'):
            girtarget = girtarget.held_object
        if not isinstance(girtarget, build.Executable):
            raise MesonException('Gir target must be an executable')
        pkgstr = subprocess.check_output(['pkg-config', '--cflags', 'gobject-introspection-1.0'])
        pkgargs = pkgstr.decode().strip().split()
        ns = kwargs.pop('namespace')
        nsversion = kwargs.pop('nsversion')
        libsources = kwargs.pop('sources')
        girfile = '%s-%s.gir' % (ns, nsversion)
        scan_name = girtarget.name + '-gir'
        scan_command = ['g-ir-scanner', '@INPUT@', '--program', girtarget]
        scan_command += pkgargs
        scan_command += ['--include=GObject-2.0', '--namespace='+ns,
                         '--nsversion=' + nsversion, '--output', '@OUTPUT@']
        scankwargs = {'output' : girfile,
                      'input' : libsources,
                      'command' : scan_command}
        scan_target = build.CustomTarget(scan_name, state.subdir, scankwargs)
        
        typelib_name = girtarget.name + '-typelib'
        typelib_output = '%s-%s.typelib' % (ns, nsversion)
        typelib_cmd = ['g-ir-compiler', scan_target, '--output', '@OUTPUT@']
        kwargs['output'] = typelib_output
        kwargs['command'] = typelib_cmd
        typelib_target = build.CustomTarget(typelib_name, state.subdir, kwargs)
        return [scan_target, typelib_target]

    def compile_schemas(self, state, args, kwargs):
        if len(args) != 0:
            raise MesonException('Compile_schemas does not take positional arguments.')
        srcdir = os.path.join(state.build_to_src, state.subdir)
        outdir = state.subdir
        cmd = ['glib-compile-schemas', '--targetdir', outdir, srcdir]
        kwargs['command'] = cmd
        kwargs['input'] = []
        kwargs['output'] = 'gschemas.compiled'
        if state.subdir == '':
            targetname = 'gsettings-compile'
        else:
            targetname = 'gsettings-compile-' + state.subdir
        target_g = build.CustomTarget(targetname, state.subdir, kwargs)
        return target_g

    def gdbus_codegen(self, state, args, kwargs):
        if len(args) != 2:
            raise MesonException('Gdbus_codegen takes two arguments, name and xml file.')
        namebase = args[0]
        xml_file = args[1]
        cmd = ['gdbus-codegen']
        if 'interface_prefix' in kwargs:
            cmd += ['--interface-prefix', kwargs.pop('interface_prefix')]
        if 'namespace' in kwargs:
            cmd += ['--c-namespace', kwargs.pop('namespace')]
        cmd += ['--generate-c-code', os.path.join(state.subdir, namebase), '@INPUT@']
        outputs = [namebase + '.c', namebase + '.h']
        custom_kwargs = {'input' : xml_file,
                         'output' : outputs,
                         'command' : cmd
                         }
        return build.CustomTarget(namebase + '-gdbus', state.subdir, custom_kwargs)

def initialize():
    mlog.log('Warning, glib compiled dependencies will not work until this upstream issue is fixed:',
             mlog.bold('https://bugzilla.gnome.org/show_bug.cgi?id=745754'))
    return GnomeModule()
