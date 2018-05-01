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
from pathlib import PurePath

from .. import build
from .. import dependencies
from .. import mesonlib
from .. import mlog
from . import ModuleReturnValue
from . import ExtensionModule
from ..interpreterbase import permittedKwargs

class DependenciesHelper:
    def __init__(self, name):
        self.name = name
        self.pub_libs = []
        self.pub_reqs = []
        self.priv_libs = []
        self.priv_reqs = []
        self.cflags = []
        self.version_reqs = {}

    def add_pub_libs(self, libs):
        libs, reqs, cflags = self._process_libs(libs, True)
        self.pub_libs += libs
        self.pub_reqs += reqs
        self.cflags += cflags

    def add_priv_libs(self, libs):
        libs, reqs, _ = self._process_libs(libs, False)
        self.priv_libs += libs
        self.priv_reqs += reqs

    def add_pub_reqs(self, reqs):
        self.pub_reqs += self._process_reqs(reqs)

    def add_priv_reqs(self, reqs):
        self.priv_reqs += self._process_reqs(reqs)

    def _process_reqs(self, reqs):
        '''Returns string names of requirements'''
        processed_reqs = []
        for obj in mesonlib.listify(reqs, unholder=True):
            if hasattr(obj, 'generated_pc'):
                processed_reqs.append(obj.generated_pc)
            elif hasattr(obj, 'pcdep'):
                pcdeps = mesonlib.listify(obj.pcdep)
                for d in pcdeps:
                    processed_reqs.append(d.name)
                    self.add_version_reqs(d.name, obj.version_reqs)
            elif isinstance(obj, dependencies.PkgConfigDependency):
                if obj.found():
                    processed_reqs.append(obj.name)
                    self.add_version_reqs(obj.name, obj.version_reqs)
            elif isinstance(obj, str):
                name, version_req = self.split_version_req(obj)
                processed_reqs.append(name)
                self.add_version_reqs(name, version_req)
            elif isinstance(obj, dependencies.Dependency) and not obj.found():
                pass
            else:
                raise mesonlib.MesonException('requires argument not a string, '
                                              'library with pkgconfig-generated file '
                                              'or pkgconfig-dependency object, '
                                              'got {!r}'.format(obj))
        return processed_reqs

    def add_cflags(self, cflags):
        self.cflags += mesonlib.stringlistify(cflags)

    def _process_libs(self, libs, public):
        libs = mesonlib.listify(libs, unholder=True)
        processed_libs = []
        processed_reqs = []
        processed_cflags = []
        for obj in libs:
            shared_library_only = getattr(obj, 'shared_library_only', False)
            if hasattr(obj, 'pcdep'):
                pcdeps = mesonlib.listify(obj.pcdep)
                for d in pcdeps:
                    processed_reqs.append(d.name)
                    self.add_version_reqs(d.name, obj.version_reqs)
            elif hasattr(obj, 'generated_pc'):
                processed_reqs.append(obj.generated_pc)
            elif isinstance(obj, dependencies.PkgConfigDependency):
                if obj.found():
                    processed_reqs.append(obj.name)
                    self.add_version_reqs(obj.name, obj.version_reqs)
            elif isinstance(obj, dependencies.ThreadDependency):
                processed_libs += obj.get_compiler().thread_link_flags(obj.env)
                processed_cflags += obj.get_compiler().thread_flags(obj.env)
            elif isinstance(obj, dependencies.Dependency):
                if obj.found():
                    processed_libs += obj.get_link_args()
                    processed_cflags += obj.get_compile_args()
            elif isinstance(obj, build.SharedLibrary) and shared_library_only:
                # Do not pull dependencies for shared libraries because they are
                # only required for static linking. Adding private requires has
                # the side effect of exposing their cflags, which is the
                # intended behaviour of pkg-config but force Debian to add more
                # than needed build deps.
                # See https://bugs.freedesktop.org/show_bug.cgi?id=105572
                processed_libs.append(obj)
                if public:
                    if not hasattr(obj, 'generated_pc'):
                        obj.generated_pc = self.name
            elif isinstance(obj, (build.SharedLibrary, build.StaticLibrary)):
                processed_libs.append(obj)
                if public:
                    if not hasattr(obj, 'generated_pc'):
                        obj.generated_pc = self.name
                if isinstance(obj, build.StaticLibrary) and public:
                    self.add_pub_libs(obj.get_dependencies(internal=False))
                    self.add_pub_libs(obj.get_external_deps())
                else:
                    self.add_priv_libs(obj.get_dependencies(internal=False))
                    self.add_priv_libs(obj.get_external_deps())
            elif isinstance(obj, str):
                processed_libs.append(obj)
            else:
                raise mesonlib.MesonException('library argument not a string, library or dependency object.')

        return processed_libs, processed_reqs, processed_cflags

    def add_version_reqs(self, name, version_reqs):
        if version_reqs:
            if name not in self.version_reqs:
                self.version_reqs[name] = set()
            # Note that pkg-config is picky about whitespace.
            # 'foo > 1.2' is ok but 'foo>1.2' is not.
            # foo, bar' is ok, but 'foo,bar' is not.
            new_vreqs = [s for s in mesonlib.stringlistify(version_reqs)]
            self.version_reqs[name].update(new_vreqs)

    def split_version_req(self, s):
        for op in ['>=', '<=', '!=', '==', '=', '>', '<']:
            pos = s.find(op)
            if pos > 0:
                return s[0:pos].strip(), s[pos:].strip()
        return s, None

    def format_vreq(self, vreq):
        # vreq are '>=1.0' and pkgconfig wants '>= 1.0'
        for op in ['>=', '<=', '!=', '==', '=', '>', '<']:
            if vreq.startswith(op):
                return op + ' ' + vreq[len(op):]
        return vreq

    def format_reqs(self, reqs):
        result = []
        for name in reqs:
            vreqs = self.version_reqs.get(name, None)
            if vreqs:
                result += [name + ' ' + self.format_vreq(vreq) for vreq in vreqs]
            else:
                result += [name]
        return ', '.join(result)

    def remove_dups(self):
        def _fn(xs):
            # Remove duplicates whilst preserving original order
            result = []
            for x in xs:
                if x not in result:
                    result.append(x)
            return result
        self.pub_libs = _fn(self.pub_libs)
        self.pub_reqs = _fn(self.pub_reqs)
        self.priv_libs = _fn(self.priv_libs)
        self.priv_reqs = _fn(self.priv_reqs)
        self.cflags = _fn(self.cflags)

        # Remove from private libs/reqs if they are in public already
        self.priv_libs = [i for i in self.priv_libs if i not in self.pub_libs]
        self.priv_reqs = [i for i in self.priv_reqs if i not in self.pub_reqs]

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

    def _escape(self, value):
        '''
        We cannot use shlex.quote because it quotes with ' and " which does not
        work with pkg-config and pkgconf at all.
        '''
        # We should always write out paths with / because pkg-config requires
        # spaces to be quoted with \ and that messes up on Windows:
        # https://bugs.freedesktop.org/show_bug.cgi?id=103203
        if isinstance(value, PurePath):
            value = value.as_posix()
        return value.replace(' ', '\ ')

    def _make_relative(self, prefix, subdir):
        if isinstance(prefix, PurePath):
            prefix = prefix.as_posix()
        if isinstance(subdir, PurePath):
            subdir = subdir.as_posix()
        if subdir.startswith(prefix):
            subdir = subdir.replace(prefix, '')
        return subdir

    def generate_pkgconfig_file(self, state, deps, subdirs, name, description,
                                url, version, pcfile, conflicts, variables):
        deps.remove_dups()
        coredata = state.environment.get_coredata()
        outdir = state.environment.scratch_dir
        fname = os.path.join(outdir, pcfile)
        prefix = PurePath(coredata.get_builtin_option('prefix'))
        # These always return paths relative to prefix
        libdir = PurePath(coredata.get_builtin_option('libdir'))
        incdir = PurePath(coredata.get_builtin_option('includedir'))
        with open(fname, 'w') as ofile:
            ofile.write('prefix={}\n'.format(self._escape(prefix)))
            ofile.write('libdir={}\n'.format(self._escape('${prefix}' / libdir)))
            ofile.write('includedir={}\n'.format(self._escape('${prefix}' / incdir)))
            if variables:
                ofile.write('\n')
            for k, v in variables:
                ofile.write('{}={}\n'.format(k, self._escape(v)))
            ofile.write('\n')
            ofile.write('Name: %s\n' % name)
            if len(description) > 0:
                ofile.write('Description: %s\n' % description)
            if len(url) > 0:
                ofile.write('URL: %s\n' % url)
            ofile.write('Version: %s\n' % version)
            reqs_str = deps.format_reqs(deps.pub_reqs)
            if len(reqs_str) > 0:
                ofile.write('Requires: {}\n'.format(reqs_str))
            reqs_str = deps.format_reqs(deps.priv_reqs)
            if len(reqs_str) > 0:
                ofile.write('Requires.private: {}\n'.format(reqs_str))
            if len(conflicts) > 0:
                ofile.write('Conflicts: {}\n'.format(' '.join(conflicts)))

            def generate_libs_flags(libs):
                msg = 'Library target {0!r} has {1!r} set. Compilers ' \
                      'may not find it from its \'-l{2}\' linker flag in the ' \
                      '{3!r} pkg-config file.'
                Lflags = []
                for l in libs:
                    if isinstance(l, str):
                        yield l
                    else:
                        install_dir = l.get_custom_install_dir()[0]
                        if install_dir is False:
                            continue
                        if isinstance(install_dir, str):
                            Lflag = '-L${prefix}/%s ' % self._escape(self._make_relative(prefix, install_dir))
                        else:  # install_dir is True
                            Lflag = '-L${libdir}'
                        if Lflag not in Lflags:
                            Lflags.append(Lflag)
                            yield Lflag
                        lname = self._get_lname(l, msg, pcfile)
                        # If using a custom suffix, the compiler may not be able to
                        # find the library
                        if l.name_suffix_set:
                            mlog.warning(msg.format(l.name, 'name_suffix', lname, pcfile))
                        yield '-l%s' % lname

            if len(deps.pub_libs) > 0:
                ofile.write('Libs: {}\n'.format(' '.join(generate_libs_flags(deps.pub_libs))))
            if len(deps.priv_libs) > 0:
                ofile.write('Libs.private: {}\n'.format(' '.join(generate_libs_flags(deps.priv_libs))))
            ofile.write('Cflags:')
            for h in subdirs:
                ofile.write(' ')
                if h == '.':
                    ofile.write('-I${includedir}')
                else:
                    ofile.write(self._escape(PurePath('-I${includedir}') / h))
            for f in deps.cflags:
                ofile.write(' ')
                ofile.write(self._escape(f))
            ofile.write('\n')

    @permittedKwargs({'libraries', 'version', 'name', 'description', 'filebase',
                      'subdirs', 'requires', 'requires_private', 'libraries_private',
                      'install_dir', 'extra_cflags', 'variables', 'url', 'd_module_versions'})
    def generate(self, state, args, kwargs):
        default_version = state.project_version['version']
        default_install_dir = None
        default_description = None
        default_name = None
        mainlib = None
        if len(args) == 1:
            mainlib = getattr(args[0], 'held_object', args[0])
            if not isinstance(mainlib, (build.StaticLibrary, build.SharedLibrary)):
                raise mesonlib.MesonException('Pkgconfig_gen first positional argument must be a library object')
            default_name = mainlib.name
            default_description = state.project_name + ': ' + mainlib.name
            install_dir = mainlib.get_custom_install_dir()[0]
            if isinstance(install_dir, str):
                default_install_dir = os.path.join(install_dir, 'pkgconfig')
        elif len(args) > 1:
            raise mesonlib.MesonException('Too many positional arguments passed to Pkgconfig_gen.')

        subdirs = mesonlib.stringlistify(kwargs.get('subdirs', ['.']))
        version = kwargs.get('version', default_version)
        if not isinstance(version, str):
            raise mesonlib.MesonException('Version must be specified.')
        name = kwargs.get('name', default_name)
        if not isinstance(name, str):
            raise mesonlib.MesonException('Name not specified.')
        filebase = kwargs.get('filebase', name)
        if not isinstance(filebase, str):
            raise mesonlib.MesonException('Filebase must be a string.')
        description = kwargs.get('description', default_description)
        if not isinstance(description, str):
            raise mesonlib.MesonException('Description is not a string.')
        url = kwargs.get('url', '')
        if not isinstance(url, str):
            raise mesonlib.MesonException('URL is not a string.')
        conflicts = mesonlib.stringlistify(kwargs.get('conflicts', []))

        deps = DependenciesHelper(filebase)
        if mainlib:
            deps.add_pub_libs(mainlib)
        deps.add_pub_libs(kwargs.get('libraries', []))
        deps.add_priv_libs(kwargs.get('libraries_private', []))
        deps.add_pub_reqs(kwargs.get('requires', []))
        deps.add_priv_reqs(kwargs.get('requires_private', []))
        deps.add_cflags(kwargs.get('extra_cflags', []))

        dversions = kwargs.get('d_module_versions', None)
        if dversions:
            compiler = state.environment.coredata.compilers.get('d')
            if compiler:
                deps.add_cflags(compiler.get_feature_args({'versions': dversions}, None))

        def parse_variable_list(stringlist):
            reserved = ['prefix', 'libdir', 'includedir']
            variables = []
            for var in stringlist:
                # foo=bar=baz is ('foo', 'bar=baz')
                l = var.split('=', 1)
                if len(l) < 2:
                    raise mesonlib.MesonException('Invalid variable "{}". Variables must be in \'name=value\' format'.format(var))

                name, value = l[0].strip(), l[1].strip()
                if not name or not value:
                    raise mesonlib.MesonException('Invalid variable "{}". Variables must be in \'name=value\' format'.format(var))

                # Variable names must not contain whitespaces
                if any(c.isspace() for c in name):
                    raise mesonlib.MesonException('Invalid whitespace in assignment "{}"'.format(var))

                if name in reserved:
                    raise mesonlib.MesonException('Variable "{}" is reserved'.format(name))

                variables.append((name, value))

            return variables

        variables = parse_variable_list(mesonlib.stringlistify(kwargs.get('variables', [])))

        pcfile = filebase + '.pc'
        pkgroot = kwargs.get('install_dir', default_install_dir)
        if pkgroot is None:
            pkgroot = os.path.join(state.environment.coredata.get_builtin_option('libdir'), 'pkgconfig')
        if not isinstance(pkgroot, str):
            raise mesonlib.MesonException('Install_dir must be a string.')
        self.generate_pkgconfig_file(state, deps, subdirs, name, description, url,
                                     version, pcfile, conflicts, variables)
        res = build.Data(mesonlib.File(True, state.environment.get_scratch_dir(), pcfile), pkgroot)
        return ModuleReturnValue(res, [res])

def initialize(*args, **kwargs):
    return PkgConfigModule(*args, **kwargs)
