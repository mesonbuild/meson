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
functionality such as generating template RPM spec file.'''

from .. import build
from .. import compilers
import datetime
from .. import mlog
from . import GirTarget, TypelibTarget
from . import ModuleReturnValue
from . import ExtensionModule
from ..interpreterbase import noKwargs

import os

class RPMModule(ExtensionModule):

    @noKwargs
    def generate_spec_template(self, coredata, args, kwargs):
        self.coredata = coredata
        required_compilers = self.__get_required_compilers()
        proj = coredata.project_name.replace(' ', '_').replace('\t', '_')
        so_installed = False
        devel_subpkg = False
        files = set()
        files_devel = set()
        to_delete = set()
        for target in coredata.targets.values():
            if isinstance(target, build.Executable) and target.need_install:
                files.add('%%{_bindir}/%s' % target.get_filename())
            elif isinstance(target, build.SharedLibrary) and target.need_install:
                files.add('%%{_libdir}/%s' % target.get_filename())
                for alias in target.get_aliases():
                    if alias.endswith('.so'):
                        files_devel.add('%%{_libdir}/%s' % alias)
                    else:
                        files.add('%%{_libdir}/%s' % alias)
                so_installed = True
            elif isinstance(target, build.StaticLibrary) and target.need_install:
                to_delete.add('%%{buildroot}%%{_libdir}/%s' % target.get_filename())
                mlog.warning('removing', mlog.bold(target.get_filename()),
                             'from package because packaging static libs not recommended')
            elif isinstance(target, GirTarget) and target.should_install():
                files_devel.add('%%{_datadir}/gir-1.0/%s' % target.get_filename()[0])
            elif isinstance(target, TypelibTarget) and target.should_install():
                files.add('%%{_libdir}/girepository-1.0/%s' % target.get_filename()[0])
        for header in coredata.headers:
            if header.get_install_subdir():
                files_devel.add('%%{_includedir}/%s/' % header.get_install_subdir())
            else:
                for hdr_src in header.get_sources():
                    files_devel.add('%%{_includedir}/%s' % hdr_src)
        for man in coredata.man:
            for man_file in man.get_sources():
                files.add('%%{_mandir}/man%u/%s.*' % (int(man_file.split('.')[-1]), man_file))
        if files_devel:
            devel_subpkg = True

        filename = os.path.join(coredata.environment.get_build_dir(),
                                '%s.spec' % proj)
        with open(filename, 'w+') as fn:
            fn.write('Name: %s\n' % proj)
            fn.write('Version: # FIXME\n')
            fn.write('Release: 1%{?dist}\n')
            fn.write('Summary: # FIXME\n')
            fn.write('License: # FIXME\n')
            fn.write('\n')
            fn.write('Source0: %{name}-%{version}.tar.xz # FIXME\n')
            fn.write('\n')
            fn.write('BuildRequires: meson\n')
            for compiler in required_compilers:
                fn.write('BuildRequires: %s\n' % compiler)
            for dep in coredata.environment.coredata.deps.host:
                fn.write('BuildRequires: pkgconfig(%s)\n' % dep[0])
#   ext_libs and ext_progs have been removed from coredata so the following code
#   no longer works. It is kept as a reminder of the idea should anyone wish
#   to re-implement it.
#
#            for lib in state.environment.coredata.ext_libs.values():
#                name = lib.get_name()
#                fn.write('BuildRequires: {} # FIXME\n'.format(name))
#                mlog.warning('replace', mlog.bold(name), 'with the real package.',
#                             'You can use following command to find package which '
#                             'contains this lib:',
#                             mlog.bold("dnf provides '*/lib{}.so'".format(name)))
#            for prog in state.environment.coredata.ext_progs.values():
#                if not prog.found():
#                    fn.write('BuildRequires: %%{_bindir}/%s # FIXME\n' %
#                             prog.get_name())
#                else:
#                    fn.write('BuildRequires: {}\n'.format(prog.get_path()))
            fn.write('\n')
            fn.write('%description\n')
            fn.write('\n')
            if devel_subpkg:
                fn.write('%package devel\n')
                fn.write('Summary: Development files for %{name}\n')
                fn.write('Requires: %{name}%{?_isa} = %{?epoch:%{epoch}:}{version}-%{release}\n')
                fn.write('\n')
                fn.write('%description devel\n')
                fn.write('Development files for %{name}.\n')
                fn.write('\n')
            fn.write('%prep\n')
            fn.write('%autosetup\n')
            fn.write('\n')
            fn.write('%build\n')
            fn.write('%meson\n')
            fn.write('%meson_build\n')
            fn.write('\n')
            fn.write('%install\n')
            fn.write('%meson_install\n')
            if to_delete:
                fn.write('rm -vf %s\n' % ' '.join(to_delete))
            fn.write('\n')
            fn.write('%check\n')
            fn.write('%meson_test\n')
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
                fn.write('%postun -p /sbin/ldconfig\n')
            fn.write('\n')
            fn.write('%changelog\n')
            fn.write('* %s meson <meson@example.com> - \n' %
                     datetime.date.today().strftime('%a %b %d %Y'))
            fn.write('- \n')
            fn.write('\n')
        mlog.log('RPM spec template written to %s.spec.\n' % proj)
        return ModuleReturnValue(None, [])

    def __get_required_compilers(self):
        required_compilers = set()
        for compiler in self.coredata.environment.coredata.compilers.host.values():
            # Elbrus has one 'lcc' package for every compiler
            if isinstance(compiler, compilers.GnuCCompiler):
                required_compilers.add('gcc')
            elif isinstance(compiler, compilers.GnuCPPCompiler):
                required_compilers.add('gcc-c++')
            elif isinstance(compiler, compilers.ElbrusCCompiler):
                required_compilers.add('lcc')
            elif isinstance(compiler, compilers.ElbrusCPPCompiler):
                required_compilers.add('lcc')
            elif isinstance(compiler, compilers.ElbrusFortranCompiler):
                required_compilers.add('lcc')
            elif isinstance(compiler, compilers.ValaCompiler):
                required_compilers.add('vala')
            elif isinstance(compiler, compilers.GnuFortranCompiler):
                required_compilers.add('gcc-gfortran')
            elif isinstance(compiler, compilers.GnuObjCCompiler):
                required_compilers.add('gcc-objc')
            elif compiler == compilers.GnuObjCPPCompiler:
                required_compilers.add('gcc-objc++')
            else:
                mlog.log('RPM spec file not created, generation not allowed for:',
                         mlog.bold(compiler.get_id()))
        return required_compilers


def initialize(*args, **kwargs):
    return RPMModule(*args, **kwargs)
