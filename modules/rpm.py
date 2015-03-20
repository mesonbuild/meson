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

'''This module provides helper functions for RPM related
functionality such as generating RPM spec file.'''

import build
import datetime
import mlog
import os

class RPMModule:

    def generate_spec_template(self, state, args, kwargs):
        proj = state.project_name.replace(' ', '_').replace('\t', '_')
        so_installed = False
        devel_subpkg = False
        files = []
        files_devel = []
        to_delete = []
        for target in state.targets.values():
            if isinstance(target, build.Executable) and target.need_install:
                files.append('%%{_bindir}/%s' % target.get_filename())
            elif isinstance(target, build.SharedLibrary) and target.need_install:
                files.append('%%{_libdir}/%s' % target.get_filename())
                for alias in target.get_aliaslist():
                    if alias.endswith('.so'):
                        files_devel.append('%%{_libdir}/%s' % alias)
                    else:
                        files.append('%%{_libdir}/%s' % alias)
                so_installed = True
            elif isinstance(target, build.StaticLibrary) and target.need_install:
                to_delete.append('%%{buildroot}%%{_libdir}/%s' % target.get_filename())
                mlog.log('Ignoring', mlog.bold(target.get_filename()),
                         'because packaging static libs not recommended')
        if len(files_devel) > 0:
            devel_subpkg = True
        fn = open('%s.spec' % os.path.join(state.environment.get_build_dir(), proj),
                  'w+')
        fn.write('Name: %s\n' % proj)
        fn.write('\n')
        for dep in state.environment.coredata.deps:
            fn.write('BuildRequires: pkgconfig(%s)\n' % dep)
        for lib in state.environment.coredata.ext_libs.values():
            fn.write('BuildRequires: %s # FIXME\n' % lib.fullpath)
            mlog.log('Warning, replace', mlog.bold(lib.fullpath), 'with real package.',
                     'You can use following command to find package which contains this lib:',
                     mlog.bold('dnf provides %s' % lib.fullpath))
        for prog in state.environment.coredata.ext_progs.values():
            fn.write('BuildRequires: %s\n' % ' '.join(prog.fullpath))
        fn.write('BuildRequires: meson\n')
        fn.write('\n')
        fn.write('%description\n')
        fn.write('\n')
        if devel_subpkg:
            fn.write('%package devel\n')
            fn.write('Requires: %{name}%{?_isa} = %{version}-%{release}\n')
            fn.write('\n')
            fn.write('%description devel\n')
            fn.write('\n')
        fn.write('%prep\n')
        fn.write('%autosetup\n')
        fn.write('rm -rf rpmbuilddir && mkdir rpmbuilddir\n')
        fn.write('echo "#!/bin/bash" > rpmbuilddir/configure && chmod +x rpmbuilddir/configure\n')
        fn.write('\n')
        fn.write('%build\n')
        fn.write('pushd rpmbuilddir\n')
        fn.write('  %configure\n')
        fn.write('  meson .. --buildtype=plain\n')
        fn.write('  ninja-build -v\n')
        fn.write('popd\n')
        fn.write('\n')
        fn.write('%install\n')
        fn.write('pushd rpmbuilddir\n')
        fn.write('  DESTDIR=%{buildroot} ninja-build -v install\n')
        fn.write('popd\n')
        if len(to_delete) > 0:
            fn.write('rm -rf %s\n' % ' '.join(to_delete))
        fn.write('\n')
        fn.write('%check\n')
        fn.write('pushd rpmbuilddir\n')
        fn.write('  ninja-build -v test\n')
        fn.write('popd\n')
        fn.write('\n')
        fn.write('%files\n')
        for f in files:
            fn.write('%s\n' % f)
        fn.write('\n')
        if devel_subpkg:
            fn.write('%files devel\n')
            for f in files_devel:
                fn.write('%s\n' % f)
        fn.write('\n')
        if so_installed:
                fn.write('%post -p /sbin/ldconfig\n')
                fn.write('\n')
                fn.write('%postun -p /sbin/ldconfig\n')
        fn.write('\n')
        fn.write('%changelog\n')
        fn.write('* %s meson <meson@example.com> - \n' % datetime.date.today().strftime('%a %b %d %Y'))
        fn.write('- \n')
        fn.write('\n')
        fn.close()

def initialize():
    return RPMModule()
