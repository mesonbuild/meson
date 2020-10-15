# Copyright 2015-2016 The Meson development team

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
functionality such as gobject-introspection, gresources and gtk-doc'''

import os
import copy
import subprocess
import functools

from .. import build
from .. import mlog
from .. import mesonlib
from .. import interpreter
from . import GResourceTarget, GResourceHeaderTarget, GirTarget, TypelibTarget, VapiTarget
from . import get_include_args
from . import ExtensionModule
from . import ModuleReturnValue
from ..mesonlib import (
    MachineChoice, MesonException, OrderedSet, Popen_safe, extract_as_list,
    join_args, unholder,
)
from ..dependencies import Dependency, PkgConfigDependency, InternalDependency, ExternalProgram
from ..interpreterbase import noKwargs, permittedKwargs, FeatureNew, FeatureNewKwargs, FeatureDeprecatedKwargs

# gresource compilation is broken due to the way
# the resource compiler and Ninja clash about it
#
# https://github.com/ninja-build/ninja/issues/1184
# https://bugzilla.gnome.org/show_bug.cgi?id=774368
gresource_dep_needed_version = '>= 2.51.1'

native_glib_version = None

class GnomeModule(ExtensionModule):
    gir_dep = None

    @staticmethod
    def _get_native_glib_version(state):
        global native_glib_version
        if native_glib_version is None:
            glib_dep = PkgConfigDependency('glib-2.0', state.environment,
                                           {'native': True, 'required': False})
            if glib_dep.found():
                native_glib_version = glib_dep.get_version()
            else:
                mlog.warning('Could not detect glib version, assuming 2.54. '
                             'You may get build errors if your glib is older.')
                native_glib_version = '2.54'
        return native_glib_version

    @mesonlib.run_once
    def __print_gresources_warning(self, state):
        if not mesonlib.version_compare(self._get_native_glib_version(state),
                                        gresource_dep_needed_version):
            mlog.warning('GLib compiled dependencies do not work reliably with \n'
                         'the current version of GLib. See the following upstream issue:',
                         mlog.bold('https://bugzilla.gnome.org/show_bug.cgi?id=774368'))

    @staticmethod
    def _print_gdbus_warning():
        mlog.warning('Code generated with gdbus_codegen() requires the root directory be added to\n'
                     '  include_directories of targets with GLib < 2.51.3:',
                     mlog.bold('https://github.com/mesonbuild/meson/issues/1387'),
                     once=True)

    @FeatureNewKwargs('gnome.compile_resources', '0.37.0', ['gresource_bundle', 'export', 'install_header'])
    @permittedKwargs({'source_dir', 'c_name', 'dependencies', 'export', 'gresource_bundle', 'install_header',
                      'install', 'install_dir', 'extra_args', 'build_by_default'})
    def compile_resources(self, state, args, kwargs):
        self.__print_gresources_warning(state)
        glib_version = self._get_native_glib_version(state)

        glib_compile_resources = self.interpreter.find_program_impl('glib-compile-resources')
        cmd = [glib_compile_resources, '@INPUT@']

        source_dirs, dependencies = [mesonlib.extract_as_list(kwargs, c, pop=True) for c in  ['source_dir', 'dependencies']]

        if len(args) < 2:
            raise MesonException('Not enough arguments; the name of the resource '
                                 'and the path to the XML file are required')

        # Validate dependencies
        subdirs = []
        depends = []
        for (ii, dep) in enumerate(unholder(dependencies)):
            if isinstance(dep, mesonlib.File):
                subdirs.append(dep.subdir)
            elif isinstance(dep, (build.CustomTarget, build.CustomTargetIndex)):
                depends.append(dep)
                subdirs.append(dep.get_subdir())
                if not mesonlib.version_compare(glib_version, gresource_dep_needed_version):
                    m = 'The "dependencies" argument of gnome.compile_resources() can not\n' \
                        'be used with the current version of glib-compile-resources due to\n' \
                        '<https://bugzilla.gnome.org/show_bug.cgi?id=774368>'
                    raise MesonException(m)
            else:
                m = 'Unexpected dependency type {!r} for gnome.compile_resources() ' \
                    '"dependencies" argument.\nPlease pass the return value of ' \
                    'custom_target() or configure_file()'
                raise MesonException(m.format(dep))

        if not mesonlib.version_compare(glib_version, gresource_dep_needed_version):
            ifile = args[1]
            if isinstance(ifile, mesonlib.File):
                # glib-compile-resources will be run inside the source dir,
                # so we need either 'src_to_build' or the absolute path.
                # Absolute path is the easiest choice.
                if ifile.is_built:
                    ifile = os.path.join(state.environment.get_build_dir(), ifile.subdir, ifile.fname)
                else:
                    ifile = os.path.join(ifile.subdir, ifile.fname)
            elif isinstance(ifile, str):
                ifile = os.path.join(state.subdir, ifile)
            elif isinstance(ifile, (interpreter.CustomTargetHolder,
                                    interpreter.CustomTargetIndexHolder,
                                    interpreter.GeneratedObjectsHolder)):
                m = 'Resource xml files generated at build-time cannot be used ' \
                    'with gnome.compile_resources() because we need to scan ' \
                    'the xml for dependencies. Use configure_file() instead ' \
                    'to generate it at configure-time.'
                raise MesonException(m)
            else:
                raise MesonException('Invalid file argument: {!r}'.format(ifile))
            depend_files, depends, subdirs = self._get_gresource_dependencies(
                state, ifile, source_dirs, dependencies)

        # Make source dirs relative to build dir now
        source_dirs = [os.path.join(state.build_to_src, state.subdir, d) for d in source_dirs]
        # Ensure build directories of generated deps are included
        source_dirs += subdirs
        # Always include current directory, but after paths set by user
        source_dirs.append(os.path.join(state.build_to_src, state.subdir))

        for source_dir in OrderedSet(source_dirs):
            cmd += ['--sourcedir', source_dir]

        if 'c_name' in kwargs:
            cmd += ['--c-name', kwargs.pop('c_name')]
        export = kwargs.pop('export', False)
        if not export:
            cmd += ['--internal']

        cmd += ['--generate', '--target', '@OUTPUT@']

        cmd += mesonlib.stringlistify(kwargs.pop('extra_args', []))

        gresource = kwargs.pop('gresource_bundle', False)
        if gresource:
            output = args[0] + '.gresource'
            name = args[0] + '_gresource'
        else:
            if 'c' in state.environment.coredata.compilers.host.keys():
                output = args[0] + '.c'
                name = args[0] + '_c'
            elif 'cpp' in state.environment.coredata.compilers.host.keys():
                output = args[0] + '.cpp'
                name = args[0] + '_cpp'
            else:
                raise MesonException('Compiling GResources into code is only supported in C and C++ projects')

        if kwargs.get('install', False) and not gresource:
            raise MesonException('The install kwarg only applies to gresource bundles, see install_header')

        install_header = kwargs.pop('install_header', False)
        if install_header and gresource:
            raise MesonException('The install_header kwarg does not apply to gresource bundles')
        if install_header and not export:
            raise MesonException('GResource header is installed yet export is not enabled')

        kwargs['input'] = args[1]
        kwargs['output'] = output
        kwargs['depends'] = depends
        if not mesonlib.version_compare(glib_version, gresource_dep_needed_version):
            # This will eventually go out of sync if dependencies are added
            kwargs['depend_files'] = depend_files
            kwargs['command'] = cmd
        else:
            depfile = kwargs['output'] + '.d'
            kwargs['depfile'] = depfile
            kwargs['command'] = copy.copy(cmd) + ['--dependency-file', '@DEPFILE@']
        target_c = GResourceTarget(name, state.subdir, state.subproject, kwargs)

        if gresource: # Only one target for .gresource files
            return ModuleReturnValue(target_c, [target_c])

        h_kwargs = {
            'command': cmd,
            'input': args[1],
            'output': args[0] + '.h',
            # The header doesn't actually care about the files yet it errors if missing
            'depends': depends
        }
        if 'build_by_default' in kwargs:
            h_kwargs['build_by_default'] = kwargs['build_by_default']
        if install_header:
            h_kwargs['install'] = install_header
            h_kwargs['install_dir'] = kwargs.get('install_dir',
                                                 state.environment.coredata.get_builtin_option('includedir'))
        target_h = GResourceHeaderTarget(args[0] + '_h', state.subdir, state.subproject, h_kwargs)
        rv = [target_c, target_h]
        return ModuleReturnValue(rv, rv)

    def _get_gresource_dependencies(self, state, input_file, source_dirs, dependencies):

        cmd = ['glib-compile-resources',
               input_file,
               '--generate-dependencies']

        # Prefer generated files over source files
        cmd += ['--sourcedir', state.subdir] # Current build dir
        for source_dir in source_dirs:
            cmd += ['--sourcedir', os.path.join(state.subdir, source_dir)]

        try:
            pc, stdout, stderr = Popen_safe(cmd, cwd=state.environment.get_source_dir())
        except (FileNotFoundError, PermissionError):
            raise MesonException('Could not execute glib-compile-resources.')
        if pc.returncode != 0:
            m = 'glib-compile-resources failed to get dependencies for {}:\n{}'
            mlog.warning(m.format(cmd[1], stderr))
            raise subprocess.CalledProcessError(pc.returncode, cmd)

        dep_files = stdout.split('\n')[:-1]

        depends = []
        subdirs = []
        for resfile in dep_files[:]:
            resbasename = os.path.basename(resfile)
            for dep in unholder(dependencies):
                if isinstance(dep, mesonlib.File):
                    if dep.fname != resbasename:
                        continue
                    dep_files.remove(resfile)
                    dep_files.append(dep)
                    subdirs.append(dep.subdir)
                    break
                elif isinstance(dep, (build.CustomTarget, build.CustomTargetIndex)):
                    fname = None
                    outputs = {(o, os.path.basename(o)) for o in dep.get_outputs()}
                    for o, baseo in outputs:
                        if baseo == resbasename:
                            fname = o
                            break
                    if fname is not None:
                        dep_files.remove(resfile)
                        depends.append(dep)
                        subdirs.append(dep.get_subdir())
                        break
            else:
                # In generate-dependencies mode, glib-compile-resources doesn't raise
                # an error for missing resources but instead prints whatever filename
                # was listed in the input file.  That's good because it means we can
                # handle resource files that get generated as part of the build, as
                # follows.
                #
                # If there are multiple generated resource files with the same basename
                # then this code will get confused.
                try:
                    f = mesonlib.File.from_source_file(state.environment.get_source_dir(),
                                                       ".", resfile)
                except MesonException:
                    raise MesonException(
                        'Resource "%s" listed in "%s" was not found. If this is a '
                        'generated file, pass the target that generates it to '
                        'gnome.compile_resources() using the "dependencies" '
                        'keyword argument.' % (resfile, input_file))
                dep_files.remove(resfile)
                dep_files.append(f)
        return dep_files, depends, subdirs

    def _get_link_args(self, state, lib, depends, include_rpath=False,
                       use_gir_args=False):
        link_command = []
        # Construct link args
        if isinstance(lib, build.SharedLibrary):
            libdir = os.path.join(state.environment.get_build_dir(), state.backend.get_target_dir(lib))
            link_command.append('-L' + libdir)
            if include_rpath:
                link_command.append('-Wl,-rpath,' + libdir)
            depends.append(lib)
            # Needed for the following binutils bug:
            # https://github.com/mesonbuild/meson/issues/1911
            # However, g-ir-scanner does not understand -Wl,-rpath
            # so we need to use -L instead
            for d in state.backend.determine_rpath_dirs(lib):
                d = os.path.join(state.environment.get_build_dir(), d)
                link_command.append('-L' + d)
                if include_rpath:
                    link_command.append('-Wl,-rpath,' + d)
        if use_gir_args and self._gir_has_option('--extra-library'):
            link_command.append('--extra-library=' + lib.name)
        else:
            link_command.append('-l' + lib.name)
        return link_command

    def _get_dependencies_flags(self, deps, state, depends, include_rpath=False,
                                use_gir_args=False, separate_nodedup=False):
        cflags = OrderedSet()
        internal_ldflags = OrderedSet()
        external_ldflags = OrderedSet()
        # External linker flags that can't be de-duped reliably because they
        # require two args in order, such as -framework AVFoundation
        external_ldflags_nodedup = []
        gi_includes = OrderedSet()
        deps = mesonlib.unholder(mesonlib.listify(deps))

        for dep in deps:
            if isinstance(dep, Dependency):
                girdir = dep.get_variable(pkgconfig='girdir', internal='girdir', default_value='')
                if girdir:
                    gi_includes.update([girdir])
            if isinstance(dep, InternalDependency):
                cflags.update(dep.get_compile_args())
                cflags.update(get_include_args(dep.include_directories))
                for lib in unholder(dep.libraries):
                    if isinstance(lib, build.SharedLibrary):
                        internal_ldflags.update(self._get_link_args(state, lib, depends, include_rpath))
                        libdepflags = self._get_dependencies_flags(lib.get_external_deps(), state, depends, include_rpath,
                                                                   use_gir_args, True)
                        cflags.update(libdepflags[0])
                        internal_ldflags.update(libdepflags[1])
                        external_ldflags.update(libdepflags[2])
                        external_ldflags_nodedup += libdepflags[3]
                        gi_includes.update(libdepflags[4])
                extdepflags = self._get_dependencies_flags(dep.ext_deps, state, depends, include_rpath,
                                                           use_gir_args, True)
                cflags.update(extdepflags[0])
                internal_ldflags.update(extdepflags[1])
                external_ldflags.update(extdepflags[2])
                external_ldflags_nodedup += extdepflags[3]
                gi_includes.update(extdepflags[4])
                for source in unholder(dep.sources):
                    if isinstance(source, GirTarget):
                        gi_includes.update([os.path.join(state.environment.get_build_dir(),
                                            source.get_subdir())])
            # This should be any dependency other than an internal one.
            elif isinstance(dep, Dependency):
                cflags.update(dep.get_compile_args())
                ldflags = iter(dep.get_link_args(raw=True))
                for lib in ldflags:
                    if (os.path.isabs(lib) and
                            # For PkgConfigDependency only:
                            getattr(dep, 'is_libtool', False)):
                        lib_dir = os.path.dirname(lib)
                        external_ldflags.update(["-L%s" % lib_dir])
                        if include_rpath:
                            external_ldflags.update(['-Wl,-rpath {}'.format(lib_dir)])
                        libname = os.path.basename(lib)
                        if libname.startswith("lib"):
                            libname = libname[3:]
                        libname = libname.split(".so")[0]
                        lib = "-l%s" % libname
                    # FIXME: Hack to avoid passing some compiler options in
                    if lib.startswith("-W"):
                        continue
                    # If it's a framework arg, slurp the framework name too
                    # to preserve the order of arguments
                    if lib == '-framework':
                        external_ldflags_nodedup += [lib, next(ldflags)]
                    else:
                        external_ldflags.update([lib])
            elif isinstance(dep, (build.StaticLibrary, build.SharedLibrary)):
                cflags.update(get_include_args(dep.get_include_dirs()))
                depends.append(dep)
            else:
                mlog.log('dependency {!r} not handled to build gir files'.format(dep))
                continue

        if use_gir_args and self._gir_has_option('--extra-library'):
            def fix_ldflags(ldflags):
                fixed_ldflags = OrderedSet()
                for ldflag in ldflags:
                    if ldflag.startswith("-l"):
                        ldflag = ldflag.replace('-l', '--extra-library=', 1)
                    fixed_ldflags.add(ldflag)
                return fixed_ldflags
            internal_ldflags = fix_ldflags(internal_ldflags)
            external_ldflags = fix_ldflags(external_ldflags)
        if not separate_nodedup:
            external_ldflags.update(external_ldflags_nodedup)
            return cflags, internal_ldflags, external_ldflags, gi_includes
        else:
            return cflags, internal_ldflags, external_ldflags, external_ldflags_nodedup, gi_includes

    def _unwrap_gir_target(self, girtarget, state):
        while hasattr(girtarget, 'held_object'):
            girtarget = girtarget.held_object

        if not isinstance(girtarget, (build.Executable, build.SharedLibrary,
                                      build.StaticLibrary)):
            raise MesonException('Gir target must be an executable or library')

        STATIC_BUILD_REQUIRED_VERSION = ">=1.58.1"
        if isinstance(girtarget, (build.StaticLibrary)) and \
           not mesonlib.version_compare(
               self._get_gir_dep(state)[0].get_version(),
               STATIC_BUILD_REQUIRED_VERSION):
            raise MesonException('Static libraries can only be introspected with GObject-Introspection ' + STATIC_BUILD_REQUIRED_VERSION)

        return girtarget

    def _get_gir_dep(self, state):
        if not self.gir_dep:
            kwargs = {'native': True, 'required': True}
            holder = self.interpreter.func_dependency(state.current_node, ['gobject-introspection-1.0'], kwargs)
            self.gir_dep = holder.held_object
            giscanner = state.environment.lookup_binary_entry(MachineChoice.HOST, 'g-ir-scanner')
            if giscanner is not None:
                self.giscanner = ExternalProgram.from_entry('g-ir-scanner', giscanner)
            elif self.gir_dep.type_name == 'pkgconfig':
                self.giscanner = ExternalProgram('g_ir_scanner', self.gir_dep.get_pkgconfig_variable('g_ir_scanner', {}))
            else:
                self.giscanner = self.interpreter.find_program_impl('g-ir-scanner')
            gicompiler = state.environment.lookup_binary_entry(MachineChoice.HOST, 'g-ir-compiler')
            if gicompiler is not None:
                self.gicompiler = ExternalProgram.from_entry('g-ir-compiler', gicompiler)
            elif self.gir_dep.type_name == 'pkgconfig':
                self.gicompiler = ExternalProgram('g_ir_compiler', self.gir_dep.get_pkgconfig_variable('g_ir_compiler', {}))
            else:
                self.gicompiler = self.interpreter.find_program_impl('g-ir-compiler')
        return self.gir_dep, self.giscanner, self.gicompiler

    @functools.lru_cache(maxsize=None)
    def _gir_has_option(self, option):
        exe = self.giscanner
        if hasattr(exe, 'held_object'):
            exe = exe.held_object
        if isinstance(exe, interpreter.OverrideProgram):
            # Handle overridden g-ir-scanner
            assert option in ['--extra-library', '--sources-top-dirs']
            return True
        p, o, e = Popen_safe(exe.get_command() + ['--help'], stderr=subprocess.STDOUT)
        return p.returncode == 0 and option in o

    def _scan_header(self, kwargs):
        ret = []
        header = kwargs.pop('header', None)
        if header:
            if not isinstance(header, str):
                raise MesonException('header must be a string')
            ret = ['--c-include=' + header]
        return ret

    def _scan_extra_args(self, kwargs):
        return mesonlib.stringlistify(kwargs.pop('extra_args', []))

    def _scan_link_withs(self, state, depends, kwargs):
        ret = []
        if 'link_with' in kwargs:
            link_with = mesonlib.extract_as_list(kwargs, 'link_with', pop = True)

            for link in link_with:
                ret += self._get_link_args(state, link.held_object, depends,
                                           use_gir_args=True)
        return ret

    # May mutate depends and gir_inc_dirs
    def _scan_include(self, state, depends, gir_inc_dirs, kwargs):
        ret = []

        if 'includes' in kwargs:
            includes = mesonlib.extract_as_list(kwargs, 'includes', pop = True)
            for inc in unholder(includes):
                if isinstance(inc, str):
                    ret += ['--include=%s' % (inc, )]
                elif isinstance(inc, GirTarget):
                    gir_inc_dirs += [
                        os.path.join(state.environment.get_build_dir(),
                                     inc.get_subdir()),
                    ]
                    ret += [
                        "--include-uninstalled=%s" % (os.path.join(inc.get_subdir(), inc.get_basename()), )
                    ]
                    depends += [inc]
                else:
                    raise MesonException(
                        'Gir includes must be str, GirTarget, or list of them')

        return ret

    def _scan_symbol_prefix(self, kwargs):
        ret = []

        if 'symbol_prefix' in kwargs:
            sym_prefixes = mesonlib.stringlistify(kwargs.pop('symbol_prefix', []))
            ret += ['--symbol-prefix=%s' % sym_prefix for sym_prefix in sym_prefixes]

        return ret

    def _scan_identifier_prefix(self, kwargs):
        ret = []

        if 'identifier_prefix' in kwargs:
            identifier_prefix = kwargs.pop('identifier_prefix')
            if not isinstance(identifier_prefix, str):
                raise MesonException('Gir identifier prefix must be str')
            ret += ['--identifier-prefix=%s' % identifier_prefix]

        return ret

    def _scan_export_packages(self, kwargs):
        ret = []

        if 'export_packages' in kwargs:
            pkgs = kwargs.pop('export_packages')
            if isinstance(pkgs, str):
                ret += ['--pkg-export=%s' % pkgs]
            elif isinstance(pkgs, list):
                ret += ['--pkg-export=%s' % pkg for pkg in pkgs]
            else:
                raise MesonException('Gir export packages must be str or list')

        return ret

    def _scan_inc_dirs(self, kwargs):
        ret = mesonlib.extract_as_list(kwargs, 'include_directories', pop = True)
        for incd in ret:
            if not isinstance(incd.held_object, (str, build.IncludeDirs)):
                raise MesonException(
                    'Gir include dirs should be include_directories().')
        return ret

    def _scan_langs(self, state, langs):
        ret = []

        for lang in langs:
            link_args = state.environment.coredata.get_external_link_args(MachineChoice.HOST, lang)
            for link_arg in link_args:
                if link_arg.startswith('-L'):
                    ret.append(link_arg)

        return ret

    def _scan_gir_targets(self, state, girtargets):
        ret = []

        for girtarget in girtargets:
            if isinstance(girtarget, build.Executable):
                ret += ['--program', girtarget]
            else:
                # Because of https://gitlab.gnome.org/GNOME/gobject-introspection/merge_requests/72
                # we can't use the full path until this is merged.
                if isinstance(girtarget, build.SharedLibrary):
                    libname = girtarget.get_basename()
                else:
                    libname = os.path.join("@PRIVATE_OUTDIR_ABS_%s@" % girtarget.get_id(), girtarget.get_filename())
                ret += ['--library', libname]
                # need to put our output directory first as we need to use the
                # generated libraries instead of any possibly installed system/prefix
                # ones.
                ret += ["-L@PRIVATE_OUTDIR_ABS_%s@" % girtarget.get_id()]
                # Needed for the following binutils bug:
                # https://github.com/mesonbuild/meson/issues/1911
                # However, g-ir-scanner does not understand -Wl,-rpath
                # so we need to use -L instead
                for d in state.backend.determine_rpath_dirs(girtarget):
                    d = os.path.join(state.environment.get_build_dir(), d)
                    ret.append('-L' + d)

        return ret

    def _get_girtargets_langs_compilers(self, girtargets):
        ret = []
        for girtarget in girtargets:
            for lang, compiler in girtarget.compilers.items():
                # XXX: Can you use g-i with any other language?
                if lang in ('c', 'cpp', 'objc', 'objcpp', 'd'):
                    ret.append((lang, compiler))
                    break

        return ret

    def _get_gir_targets_deps(self, girtargets):
        ret = []
        for girtarget in girtargets:
            ret += girtarget.get_all_link_deps()
            ret += girtarget.get_external_deps()
        return ret

    def _get_gir_targets_inc_dirs(self, girtargets):
        ret = []
        for girtarget in girtargets:
            ret += girtarget.get_include_dirs()
        return ret

    def _get_langs_compilers_flags(self, state, langs_compilers):
        cflags = []
        internal_ldflags = []
        external_ldflags = []

        for lang, compiler in langs_compilers:
            if state.global_args.get(lang):
                cflags += state.global_args[lang]
            if state.project_args.get(lang):
                cflags += state.project_args[lang]
            if 'b_sanitize' in compiler.base_options:
                sanitize = state.environment.coredata.base_options['b_sanitize'].value
                cflags += compiler.sanitizer_compile_args(sanitize)
                sanitize = sanitize.split(',')
                # These must be first in ldflags
                if 'address' in sanitize:
                    internal_ldflags += ['-lasan']
                if 'thread' in sanitize:
                    internal_ldflags += ['-ltsan']
                if 'undefined' in sanitize:
                    internal_ldflags += ['-lubsan']
                # FIXME: Linking directly to lib*san is not recommended but g-ir-scanner
                # does not understand -f LDFLAGS. https://bugzilla.gnome.org/show_bug.cgi?id=783892
                # ldflags += compiler.sanitizer_link_args(sanitize)

        return cflags, internal_ldflags, external_ldflags

    def _make_gir_filelist(self, state, srcdir, ns, nsversion, girtargets, libsources):
        gir_filelist_dir = state.backend.get_target_private_dir_abs(girtargets[0])
        if not os.path.isdir(gir_filelist_dir):
            os.mkdir(gir_filelist_dir)
        gir_filelist_filename = os.path.join(gir_filelist_dir, '%s_%s_gir_filelist' % (ns, nsversion))

        with open(gir_filelist_filename, 'w', encoding='utf-8') as gir_filelist:
            for s in unholder(libsources):
                if isinstance(s, (build.CustomTarget, build.CustomTargetIndex)):
                    for custom_output in s.get_outputs():
                        gir_filelist.write(os.path.join(state.environment.get_build_dir(),
                                                        state.backend.get_target_dir(s),
                                                        custom_output) + '\n')
                elif isinstance(s, mesonlib.File):
                    gir_filelist.write(s.rel_to_builddir(state.build_to_src) + '\n')
                elif isinstance(s, build.GeneratedList):
                    for gen_src in s.get_outputs():
                        gir_filelist.write(os.path.join(srcdir, gen_src) + '\n')
                else:
                    gir_filelist.write(os.path.join(srcdir, s) + '\n')

        return gir_filelist_filename

    def _make_gir_target(self, state, girfile, scan_command, depends, kwargs):
        scankwargs = {'output': girfile,
                      'command': scan_command,
                      'depends': depends}

        if 'install' in kwargs:
            scankwargs['install'] = kwargs['install']
            scankwargs['install_dir'] = kwargs.get('install_dir_gir',
                                                   os.path.join(state.environment.get_datadir(), 'gir-1.0'))

        if 'build_by_default' in kwargs:
            scankwargs['build_by_default'] = kwargs['build_by_default']

        return GirTarget(girfile, state.subdir, state.subproject, scankwargs)

    def _make_typelib_target(self, state, typelib_output, typelib_cmd, kwargs):
        typelib_kwargs = {
            'output': typelib_output,
            'command': typelib_cmd,
        }

        if 'install' in kwargs:
            typelib_kwargs['install'] = kwargs['install']
            typelib_kwargs['install_dir'] = kwargs.get('install_dir_typelib',
                                                       os.path.join(state.environment.get_libdir(), 'girepository-1.0'))

        if 'build_by_default' in kwargs:
            typelib_kwargs['build_by_default'] = kwargs['build_by_default']

        return TypelibTarget(typelib_output, state.subdir, state.subproject, typelib_kwargs)

    # May mutate depends
    def _gather_typelib_includes_and_update_depends(self, state, deps, depends):
        # Need to recursively add deps on GirTarget sources from our
        # dependencies and also find the include directories needed for the
        # typelib generation custom target below.
        typelib_includes = []
        for dep in unholder(deps):
            # Add a dependency on each GirTarget listed in dependencies and add
            # the directory where it will be generated to the typelib includes
            if isinstance(dep, InternalDependency):
                for source in unholder(dep.sources):
                    if isinstance(source, GirTarget) and source not in depends:
                        depends.append(source)
                        subdir = os.path.join(state.environment.get_build_dir(),
                                              source.get_subdir())
                        if subdir not in typelib_includes:
                            typelib_includes.append(subdir)
            # Do the same, but for dependencies of dependencies. These are
            # stored in the list of generated sources for each link dep (from
            # girtarget.get_all_link_deps() above).
            # FIXME: Store this in the original form from declare_dependency()
            # so it can be used here directly.
            elif isinstance(dep, build.SharedLibrary):
                for source in dep.generated:
                    if isinstance(source, GirTarget):
                        subdir = os.path.join(state.environment.get_build_dir(),
                                              source.get_subdir())
                        if subdir not in typelib_includes:
                            typelib_includes.append(subdir)
            if isinstance(dep, Dependency):
                girdir = dep.get_variable(pkgconfig='girdir', internal='girdir', default_value='')
                if girdir and girdir not in typelib_includes:
                    typelib_includes.append(girdir)
        return typelib_includes

    def _get_external_args_for_langs(self, state, langs):
        ret = []
        for lang in langs:
            ret += state.environment.coredata.get_external_args(MachineChoice.HOST, lang)
        return ret

    @staticmethod
    def _get_scanner_cflags(cflags):
        'g-ir-scanner only accepts -I/-D/-U; must ignore all other flags'
        for f in cflags:
            if f.startswith(('-D', '-U', '-I')):
                yield f

    @staticmethod
    def _get_scanner_ldflags(ldflags):
        'g-ir-scanner only accepts -L/-l; must ignore -F and other linker flags'
        for f in ldflags:
            if f.startswith(('-L', '-l', '--extra-library')):
                yield f

    @FeatureNewKwargs('generate_gir', '0.55.0', ['fatal_warnings'])
    @FeatureNewKwargs('generate_gir', '0.40.0', ['build_by_default'])
    @permittedKwargs({'sources', 'nsversion', 'namespace', 'symbol_prefix', 'identifier_prefix',
                      'export_packages', 'includes', 'dependencies', 'link_with', 'include_directories',
                      'install', 'install_dir_gir', 'install_dir_typelib', 'extra_args',
                      'packages', 'header', 'build_by_default', 'fatal_warnings'})
    def generate_gir(self, state, args, kwargs):
        if not args:
            raise MesonException('generate_gir takes at least one argument')
        if kwargs.get('install_dir'):
            raise MesonException('install_dir is not supported with generate_gir(), see "install_dir_gir" and "install_dir_typelib"')

        girtargets = [self._unwrap_gir_target(arg, state) for arg in args]

        if len(girtargets) > 1 and any([isinstance(el, build.Executable) for el in girtargets]):
            raise MesonException('generate_gir only accepts a single argument when one of the arguments is an executable')

        gir_dep, giscanner, gicompiler = self._get_gir_dep(state)

        ns = kwargs.get('namespace')
        if not ns:
            raise MesonException('Missing "namespace" keyword argument')
        nsversion = kwargs.get('nsversion')
        if not nsversion:
            raise MesonException('Missing "nsversion" keyword argument')
        libsources = mesonlib.extract_as_list(kwargs, 'sources', pop=True)
        girfile = '%s-%s.gir' % (ns, nsversion)
        srcdir = os.path.join(state.environment.get_source_dir(), state.subdir)
        builddir = os.path.join(state.environment.get_build_dir(), state.subdir)
        depends = gir_dep.sources + girtargets
        gir_inc_dirs = []
        langs_compilers = self._get_girtargets_langs_compilers(girtargets)
        cflags, internal_ldflags, external_ldflags = self._get_langs_compilers_flags(state, langs_compilers)
        deps = self._get_gir_targets_deps(girtargets)
        deps += mesonlib.unholder(extract_as_list(kwargs, 'dependencies', pop=True))
        deps += [gir_dep]
        typelib_includes = self._gather_typelib_includes_and_update_depends(state, deps, depends)
        # ldflags will be misinterpreted by gir scanner (showing
        # spurious dependencies) but building GStreamer fails if they
        # are not used here.
        dep_cflags, dep_internal_ldflags, dep_external_ldflags, gi_includes = \
            self._get_dependencies_flags(deps, state, depends, use_gir_args=True)
        cflags += list(self._get_scanner_cflags(dep_cflags))
        cflags += list(self._get_scanner_cflags(self._get_external_args_for_langs(state, [lc[0] for lc in langs_compilers])))
        internal_ldflags += list(self._get_scanner_ldflags(dep_internal_ldflags))
        external_ldflags += list(self._get_scanner_ldflags(dep_external_ldflags))
        girtargets_inc_dirs = self._get_gir_targets_inc_dirs(girtargets)
        inc_dirs = self._scan_inc_dirs(kwargs)

        scan_command = [giscanner]
        scan_command += ['--no-libtool']
        scan_command += ['--namespace=' + ns, '--nsversion=' + nsversion]
        scan_command += ['--warn-all']
        scan_command += ['--output', '@OUTPUT@']
        scan_command += self._scan_header(kwargs)
        scan_command += self._scan_extra_args(kwargs)
        scan_command += ['-I' + srcdir, '-I' + builddir]
        scan_command += get_include_args(girtargets_inc_dirs)
        scan_command += ['--filelist=' + self._make_gir_filelist(state, srcdir, ns, nsversion, girtargets, libsources)]
        scan_command += self._scan_link_withs(state, depends, kwargs)
        scan_command += self._scan_include(state, depends, gir_inc_dirs, kwargs)
        scan_command += self._scan_symbol_prefix(kwargs)
        scan_command += self._scan_identifier_prefix(kwargs)
        scan_command += self._scan_export_packages(kwargs)
        scan_command += ['--cflags-begin']
        scan_command += cflags
        scan_command += ['--cflags-end']
        scan_command += get_include_args(inc_dirs)
        scan_command += get_include_args(list(gi_includes) + gir_inc_dirs + inc_dirs, prefix='--add-include-path=')
        scan_command += list(internal_ldflags)
        scan_command += self._scan_gir_targets(state, girtargets)
        scan_command += self._scan_langs(state, [lc[0] for lc in langs_compilers])
        scan_command += list(external_ldflags)

        if self._gir_has_option('--sources-top-dirs'):
            scan_command += ['--sources-top-dirs', os.path.join(state.environment.get_source_dir(), self.interpreter.subproject_dir, state.subproject)]
            scan_command += ['--sources-top-dirs', os.path.join(state.environment.get_build_dir(), self.interpreter.subproject_dir, state.subproject)]

        if '--warn-error' in scan_command:
            mlog.deprecation('Passing --warn-error is deprecated in favor of "fatal_warnings" keyword argument since v0.55')
        fatal_warnings = kwargs.get('fatal_warnings', False)
        if not isinstance(fatal_warnings, bool):
            raise MesonException('fatal_warnings keyword argument must be a boolean')
        if fatal_warnings:
            scan_command.append('--warn-error')

        scan_target = self._make_gir_target(state, girfile, scan_command, depends, kwargs)

        typelib_output = '%s-%s.typelib' % (ns, nsversion)
        typelib_cmd = [gicompiler, scan_target, '--output', '@OUTPUT@']
        typelib_cmd += get_include_args(gir_inc_dirs, prefix='--includedir=')

        for incdir in typelib_includes:
            typelib_cmd += ["--includedir=" + incdir]

        typelib_target = self._make_typelib_target(state, typelib_output, typelib_cmd, kwargs)

        rv = [scan_target, typelib_target]

        return ModuleReturnValue(rv, rv)

    @FeatureNewKwargs('build target', '0.40.0', ['build_by_default'])
    @permittedKwargs({'build_by_default', 'depend_files'})
    def compile_schemas(self, state, args, kwargs):
        if args:
            raise MesonException('Compile_schemas does not take positional arguments.')
        srcdir = os.path.join(state.build_to_src, state.subdir)
        outdir = state.subdir

        cmd = [self.interpreter.find_program_impl('glib-compile-schemas')]
        cmd += ['--targetdir', outdir, srcdir]
        kwargs['command'] = cmd
        kwargs['input'] = []
        kwargs['output'] = 'gschemas.compiled'
        if state.subdir == '':
            targetname = 'gsettings-compile'
        else:
            targetname = 'gsettings-compile-' + state.subdir.replace('/', '_')
        target_g = build.CustomTarget(targetname, state.subdir, state.subproject, kwargs)
        return ModuleReturnValue(target_g, [target_g])

    @permittedKwargs({'sources', 'media', 'symlink_media', 'languages'})
    @FeatureDeprecatedKwargs('gnome.yelp', '0.43.0', ['languages'],
                             'Use a LINGUAS file in the source directory instead')
    def yelp(self, state, args, kwargs):
        if len(args) < 1:
            raise MesonException('Yelp requires a project id')

        project_id = args[0]
        sources = mesonlib.stringlistify(kwargs.pop('sources', []))
        if not sources:
            if len(args) > 1:
                sources = mesonlib.stringlistify(args[1:])
            if not sources:
                raise MesonException('Yelp requires a list of sources')
        source_str = '@@'.join(sources)

        langs = mesonlib.stringlistify(kwargs.pop('languages', []))
        media = mesonlib.stringlistify(kwargs.pop('media', []))
        symlinks = kwargs.pop('symlink_media', True)

        if not isinstance(symlinks, bool):
            raise MesonException('symlink_media must be a boolean')

        if kwargs:
            raise MesonException('Unknown arguments passed: {}'.format(', '.join(kwargs.keys())))

        script = state.environment.get_build_command()
        args = ['--internal',
                'yelphelper',
                'install',
                '--subdir=' + state.subdir,
                '--id=' + project_id,
                '--installdir=' + os.path.join(state.environment.get_datadir(), 'help'),
                '--sources=' + source_str]
        if symlinks:
            args.append('--symlinks=true')
        if media:
            args.append('--media=' + '@@'.join(media))
        if langs:
            args.append('--langs=' + '@@'.join(langs))
        inscript = build.RunScript(script, args)

        potargs = state.environment.get_build_command() + [
            '--internal', 'yelphelper', 'pot',
            '--subdir=' + state.subdir,
            '--id=' + project_id,
            '--sources=' + source_str,
        ]
        pottarget = build.RunTarget('help-' + project_id + '-pot', potargs[0],
                                    potargs[1:], [], state.subdir, state.subproject)

        poargs = state.environment.get_build_command() + [
            '--internal', 'yelphelper', 'update-po',
            '--subdir=' + state.subdir,
            '--id=' + project_id,
            '--sources=' + source_str,
            '--langs=' + '@@'.join(langs),
        ]
        potarget = build.RunTarget('help-' + project_id + '-update-po', poargs[0],
                                   poargs[1:], [], state.subdir, state.subproject)

        rv = [inscript, pottarget, potarget]
        return ModuleReturnValue(None, rv)

    @FeatureNewKwargs('gnome.gtkdoc', '0.52.0', ['check'])
    @FeatureNewKwargs('gnome.gtkdoc', '0.48.0', ['c_args'])
    @FeatureNewKwargs('gnome.gtkdoc', '0.48.0', ['module_version'])
    @FeatureNewKwargs('gnome.gtkdoc', '0.37.0', ['namespace', 'mode'])
    @permittedKwargs({'main_xml', 'main_sgml', 'src_dir', 'dependencies', 'install',
                      'install_dir', 'scan_args', 'scanobjs_args', 'gobject_typesfile',
                      'fixxref_args', 'html_args', 'html_assets', 'content_files',
                      'mkdb_args', 'ignore_headers', 'include_directories',
                      'namespace', 'mode', 'expand_content_files', 'module_version',
                      'c_args', 'check'})
    def gtkdoc(self, state, args, kwargs):
        if len(args) != 1:
            raise MesonException('Gtkdoc must have one positional argument.')
        modulename = args[0]
        if not isinstance(modulename, str):
            raise MesonException('Gtkdoc arg must be string.')
        if 'src_dir' not in kwargs:
            raise MesonException('Keyword argument src_dir missing.')
        main_file = kwargs.get('main_sgml', '')
        if not isinstance(main_file, str):
            raise MesonException('Main sgml keyword argument must be a string.')
        main_xml = kwargs.get('main_xml', '')
        if not isinstance(main_xml, str):
            raise MesonException('Main xml keyword argument must be a string.')
        moduleversion = kwargs.get('module_version', '')
        if not isinstance(moduleversion, str):
            raise MesonException('Module version keyword argument must be a string.')
        if main_xml != '':
            if main_file != '':
                raise MesonException('You can only specify main_xml or main_sgml, not both.')
            main_file = main_xml
        targetname = modulename + ('-' + moduleversion if moduleversion else '') + '-doc'
        command = state.environment.get_build_command()

        namespace = kwargs.get('namespace', '')
        mode = kwargs.get('mode', 'auto')
        VALID_MODES = ('xml', 'sgml', 'none', 'auto')
        if mode not in VALID_MODES:
            raise MesonException('gtkdoc: Mode {} is not a valid mode: {}'.format(mode, VALID_MODES))

        src_dirs = mesonlib.extract_as_list(kwargs, 'src_dir')
        header_dirs = []
        for src_dir in src_dirs:
            if hasattr(src_dir, 'held_object'):
                src_dir = src_dir.held_object
                if not isinstance(src_dir, build.IncludeDirs):
                    raise MesonException('Invalid keyword argument for src_dir.')
                for inc_dir in src_dir.get_incdirs():
                    header_dirs.append(os.path.join(state.environment.get_source_dir(),
                                                    src_dir.get_curdir(), inc_dir))
                    header_dirs.append(os.path.join(state.environment.get_build_dir(),
                                                    src_dir.get_curdir(), inc_dir))
            else:
                header_dirs.append(src_dir)

        args = ['--internal', 'gtkdoc',
                '--sourcedir=' + state.environment.get_source_dir(),
                '--builddir=' + state.environment.get_build_dir(),
                '--subdir=' + state.subdir,
                '--headerdirs=' + '@@'.join(header_dirs),
                '--mainfile=' + main_file,
                '--modulename=' + modulename,
                '--moduleversion=' + moduleversion,
                '--mode=' + mode]
        for tool in ['scan', 'scangobj', 'mkdb', 'mkhtml', 'fixxref']:
            program_name = 'gtkdoc-' + tool
            program = self.interpreter.find_program_impl(program_name)
            path = program.held_object.get_path()
            args.append('--{}={}'.format(program_name, path))
        if namespace:
            args.append('--namespace=' + namespace)
        args += self._unpack_args('--htmlargs=', 'html_args', kwargs)
        args += self._unpack_args('--scanargs=', 'scan_args', kwargs)
        args += self._unpack_args('--scanobjsargs=', 'scanobjs_args', kwargs)
        args += self._unpack_args('--gobjects-types-file=', 'gobject_typesfile', kwargs, state)
        args += self._unpack_args('--fixxrefargs=', 'fixxref_args', kwargs)
        args += self._unpack_args('--mkdbargs=', 'mkdb_args', kwargs)
        args += self._unpack_args('--html-assets=', 'html_assets', kwargs, state)

        depends = []
        content_files = []
        for s in unholder(mesonlib.extract_as_list(kwargs, 'content_files')):
            if isinstance(s, (build.CustomTarget, build.CustomTargetIndex)):
                depends.append(s)
                for o in s.get_outputs():
                    content_files.append(os.path.join(state.environment.get_build_dir(),
                                                      state.backend.get_target_dir(s),
                                                      o))
            elif isinstance(s, mesonlib.File):
                content_files.append(s.absolute_path(state.environment.get_source_dir(),
                                                     state.environment.get_build_dir()))
            elif isinstance(s, build.GeneratedList):
                depends.append(s)
                for gen_src in s.get_outputs():
                    content_files.append(os.path.join(state.environment.get_source_dir(),
                                                      state.subdir,
                                                      gen_src))
            elif isinstance(s, str):
                content_files.append(os.path.join(state.environment.get_source_dir(),
                                                  state.subdir,
                                                  s))
            else:
                raise MesonException(
                    'Invalid object type: {!r}'.format(s.__class__.__name__))
        args += ['--content-files=' + '@@'.join(content_files)]

        args += self._unpack_args('--expand-content-files=', 'expand_content_files', kwargs, state)
        args += self._unpack_args('--ignore-headers=', 'ignore_headers', kwargs)
        args += self._unpack_args('--installdir=', 'install_dir', kwargs)
        args += self._get_build_args(kwargs, state, depends)
        custom_kwargs = {'output': modulename + '-decl.txt',
                         'command': command + args,
                         'depends': depends,
                         'build_always_stale': True,
                         }
        custom_target = build.CustomTarget(targetname, state.subdir, state.subproject, custom_kwargs)
        alias_target = build.AliasTarget(targetname, [custom_target], state.subdir, state.subproject)
        if kwargs.get('check', False):
            check_cmd = self.interpreter.find_program_impl('gtkdoc-check')
            check_env = ['DOC_MODULE=' + modulename,
                         'DOC_MAIN_SGML_FILE=' + main_file]
            check_args = [targetname + '-check', check_cmd]
            check_kwargs = {'env': check_env,
                            'workdir': os.path.join(state.environment.get_build_dir(), state.subdir),
                            'depends': custom_target}
            self.interpreter.add_test(state.current_node, check_args, check_kwargs, True)
        res = [custom_target, alias_target]
        if kwargs.get('install', True):
            res.append(build.RunScript(command, args))
        return ModuleReturnValue(custom_target, res)

    def _get_build_args(self, kwargs, state, depends):
        args = []
        deps = mesonlib.unholder(extract_as_list(kwargs, 'dependencies'))
        cflags = []
        cflags.extend(mesonlib.stringlistify(kwargs.pop('c_args', [])))
        deps_cflags, internal_ldflags, external_ldflags, gi_includes = \
            self._get_dependencies_flags(deps, state, depends, include_rpath=True)
        inc_dirs = mesonlib.extract_as_list(kwargs, 'include_directories')
        for incd in inc_dirs:
            if not isinstance(incd.held_object, (str, build.IncludeDirs)):
                raise MesonException(
                    'Gir include dirs should be include_directories().')

        cflags.extend(deps_cflags)
        cflags.extend(get_include_args(inc_dirs))
        ldflags = []
        ldflags.extend(internal_ldflags)
        ldflags.extend(external_ldflags)

        cflags.extend(state.environment.coredata.get_external_args(MachineChoice.HOST, 'c'))
        ldflags.extend(state.environment.coredata.get_external_link_args(MachineChoice.HOST, 'c'))
        compiler = state.environment.coredata.compilers[MachineChoice.HOST]['c']

        compiler_flags = self._get_langs_compilers_flags(state, [('c', compiler)])
        cflags.extend(compiler_flags[0])
        ldflags.extend(compiler_flags[1])
        ldflags.extend(compiler_flags[2])
        if compiler:
            args += ['--cc=%s' % join_args(compiler.get_exelist())]
            args += ['--ld=%s' % join_args(compiler.get_linker_exelist())]
        if cflags:
            args += ['--cflags=%s' % join_args(cflags)]
        if ldflags:
            args += ['--ldflags=%s' % join_args(ldflags)]

        return args

    @noKwargs
    def gtkdoc_html_dir(self, state, args, kwargs):
        if len(args) != 1:
            raise MesonException('Must have exactly one argument.')
        modulename = args[0]
        if not isinstance(modulename, str):
            raise MesonException('Argument must be a string')
        return ModuleReturnValue(os.path.join('share/gtk-doc/html', modulename), [])

    @staticmethod
    def _unpack_args(arg, kwarg_name, kwargs, expend_file_state=None):
        if kwarg_name not in kwargs:
            return []

        new_args = mesonlib.extract_as_list(kwargs, kwarg_name)
        args = []
        for i in new_args:
            if expend_file_state and isinstance(i, mesonlib.File):
                i = i.absolute_path(expend_file_state.environment.get_source_dir(), expend_file_state.environment.get_build_dir())
            elif expend_file_state and isinstance(i, str):
                i = os.path.join(expend_file_state.environment.get_source_dir(), expend_file_state.subdir, i)
            elif not isinstance(i, str):
                raise MesonException(kwarg_name + ' values must be strings.')
            args.append(i)

        if args:
            return [arg + '@@'.join(args)]

        return []

    def _get_autocleanup_args(self, kwargs, glib_version):
        if not mesonlib.version_compare(glib_version, '>= 2.49.1'):
            # Warn if requested, silently disable if not
            if 'autocleanup' in kwargs:
                mlog.warning('Glib version ({}) is too old to support the \'autocleanup\' '
                             'kwarg, need 2.49.1 or newer'.format(glib_version))
            return []
        autocleanup = kwargs.pop('autocleanup', 'all')
        values = ('none', 'objects', 'all')
        if autocleanup not in values:
            raise MesonException('gdbus_codegen does not support {!r} as an autocleanup value, '
                                 'must be one of: {!r}'.format(autocleanup, ', '.join(values)))
        return ['--c-generate-autocleanup', autocleanup]

    @FeatureNewKwargs('build target', '0.46.0', ['install_header', 'install_dir', 'sources'])
    @FeatureNewKwargs('build target', '0.40.0', ['build_by_default'])
    @FeatureNewKwargs('build target', '0.47.0', ['extra_args', 'autocleanup'])
    @permittedKwargs({'interface_prefix', 'namespace', 'extra_args', 'autocleanup', 'object_manager', 'build_by_default',
                      'annotations', 'docbook', 'install_header', 'install_dir', 'sources'})
    def gdbus_codegen(self, state, args, kwargs):
        if len(args) not in (1, 2):
            raise MesonException('gdbus_codegen takes at most two arguments, name and xml file.')
        namebase = args[0]
        xml_files = args[1:]
        cmd = [self.interpreter.find_program_impl('gdbus-codegen')]
        extra_args = mesonlib.stringlistify(kwargs.pop('extra_args', []))
        cmd += extra_args
        # Autocleanup supported?
        glib_version = self._get_native_glib_version(state)
        cmd += self._get_autocleanup_args(kwargs, glib_version)
        if 'interface_prefix' in kwargs:
            cmd += ['--interface-prefix', kwargs.pop('interface_prefix')]
        if 'namespace' in kwargs:
            cmd += ['--c-namespace', kwargs.pop('namespace')]
        if kwargs.get('object_manager', False):
            cmd += ['--c-generate-object-manager']
        if 'sources' in kwargs:
            xml_files += mesonlib.listify(kwargs.pop('sources'))
        build_by_default = kwargs.get('build_by_default', False)

        # Annotations are a bit ugly in that they are a list of lists of strings...
        annotations = kwargs.pop('annotations', [])
        if not isinstance(annotations, list):
            raise MesonException('annotations takes a list')
        if annotations and isinstance(annotations, list) and not isinstance(annotations[0], list):
            annotations = [annotations]

        for annotation in annotations:
            if len(annotation) != 3 or not all(isinstance(i, str) for i in annotation):
                raise MesonException('Annotations must be made up of 3 strings for ELEMENT, KEY, and VALUE')
            cmd += ['--annotate'] + annotation

        targets = []
        install_header = kwargs.get('install_header', False)
        install_dir = kwargs.get('install_dir', state.environment.coredata.get_builtin_option('includedir'))

        output = namebase + '.c'
        # Added in https://gitlab.gnome.org/GNOME/glib/commit/e4d68c7b3e8b01ab1a4231bf6da21d045cb5a816 (2.55.2)
        # Fixed in https://gitlab.gnome.org/GNOME/glib/commit/cd1f82d8fc741a2203582c12cc21b4dacf7e1872 (2.56.2)
        if mesonlib.version_compare(glib_version, '>= 2.56.2'):
            custom_kwargs = {'input': xml_files,
                             'output': output,
                             'command': cmd + ['--body', '--output', '@OUTPUT@', '@INPUT@'],
                             'build_by_default': build_by_default
                             }
        else:
            if 'docbook' in kwargs:
                docbook = kwargs['docbook']
                if not isinstance(docbook, str):
                    raise MesonException('docbook value must be a string.')

                cmd += ['--generate-docbook', docbook]

            # https://git.gnome.org/browse/glib/commit/?id=ee09bb704fe9ccb24d92dd86696a0e6bb8f0dc1a
            if mesonlib.version_compare(glib_version, '>= 2.51.3'):
                cmd += ['--output-directory', '@OUTDIR@', '--generate-c-code', namebase, '@INPUT@']
            else:
                self._print_gdbus_warning()
                cmd += ['--generate-c-code', '@OUTDIR@/' + namebase, '@INPUT@']

            custom_kwargs = {'input': xml_files,
                             'output': output,
                             'command': cmd,
                             'build_by_default': build_by_default
                             }

        cfile_custom_target = build.CustomTarget(output, state.subdir, state.subproject, custom_kwargs)
        targets.append(cfile_custom_target)

        output = namebase + '.h'
        if mesonlib.version_compare(glib_version, '>= 2.56.2'):
            custom_kwargs = {'input': xml_files,
                             'output': output,
                             'command': cmd + ['--header', '--output', '@OUTPUT@', '@INPUT@'],
                             'build_by_default': build_by_default,
                             'install': install_header,
                             'install_dir': install_dir
                             }
        else:
            custom_kwargs = {'input': xml_files,
                             'output': output,
                             'command': cmd,
                             'build_by_default': build_by_default,
                             'install': install_header,
                             'install_dir': install_dir,
                             'depends': cfile_custom_target
                             }

        hfile_custom_target = build.CustomTarget(output, state.subdir, state.subproject, custom_kwargs)
        targets.append(hfile_custom_target)

        if 'docbook' in kwargs:
            docbook = kwargs['docbook']
            if not isinstance(docbook, str):
                raise MesonException('docbook value must be a string.')

            docbook_cmd = cmd + ['--output-directory', '@OUTDIR@', '--generate-docbook', docbook, '@INPUT@']

            # The docbook output is always ${docbook}-${name_of_xml_file}
            output = namebase + '-docbook'
            outputs = []
            for f in xml_files:
                outputs.append('{}-{}'.format(docbook, os.path.basename(str(f))))

            if mesonlib.version_compare(glib_version, '>= 2.56.2'):
                custom_kwargs = {'input': xml_files,
                                 'output': outputs,
                                 'command': docbook_cmd,
                                 'build_by_default': build_by_default
                                 }
            else:
                custom_kwargs = {'input': xml_files,
                                 'output': outputs,
                                 'command': cmd,
                                 'build_by_default': build_by_default,
                                 'depends': cfile_custom_target
                                 }

            docbook_custom_target = build.CustomTarget(output, state.subdir, state.subproject, custom_kwargs)
            targets.append(docbook_custom_target)

        return ModuleReturnValue(targets, targets)

    @permittedKwargs({'sources', 'c_template', 'h_template', 'install_header', 'install_dir',
                      'comments', 'identifier_prefix', 'symbol_prefix', 'eprod', 'vprod',
                      'fhead', 'fprod', 'ftail', 'vhead', 'vtail', 'depends'})
    def mkenums(self, state, args, kwargs):
        if len(args) != 1:
            raise MesonException('Mkenums requires one positional argument.')
        basename = args[0]

        if 'sources' not in kwargs:
            raise MesonException('Missing keyword argument "sources".')
        sources = kwargs.pop('sources')
        if isinstance(sources, str):
            sources = [sources]
        elif not isinstance(sources, list):
            raise MesonException(
                'Sources keyword argument must be a string or array.')

        cmd = []
        known_kwargs = ['comments', 'eprod', 'fhead', 'fprod', 'ftail',
                        'identifier_prefix', 'symbol_prefix', 'template',
                        'vhead', 'vprod', 'vtail']
        known_custom_target_kwargs = ['install_dir', 'build_always',
                                      'depends', 'depend_files']
        c_template = h_template = None
        install_header = False
        for arg, value in kwargs.items():
            if arg == 'sources':
                raise AssertionError("sources should've already been handled")
            elif arg == 'c_template':
                c_template = value
                if isinstance(c_template, mesonlib.File):
                    c_template = c_template.absolute_path(state.environment.source_dir, state.environment.build_dir)
                if 'template' in kwargs:
                    raise MesonException('Mkenums does not accept both '
                                         'c_template and template keyword '
                                         'arguments at the same time.')
            elif arg == 'h_template':
                h_template = value
                if isinstance(h_template, mesonlib.File):
                    h_template = h_template.absolute_path(state.environment.source_dir, state.environment.build_dir)
                if 'template' in kwargs:
                    raise MesonException('Mkenums does not accept both '
                                         'h_template and template keyword '
                                         'arguments at the same time.')
            elif arg == 'install_header':
                install_header = value
            elif arg in known_kwargs:
                cmd += ['--' + arg.replace('_', '-'), value]
            elif arg not in known_custom_target_kwargs:
                raise MesonException(
                    'Mkenums does not take a %s keyword argument.' % (arg, ))
        cmd = [self.interpreter.find_program_impl(['glib-mkenums', 'mkenums'])] + cmd
        custom_kwargs = {}
        for arg in known_custom_target_kwargs:
            if arg in kwargs:
                custom_kwargs[arg] = kwargs[arg]

        targets = []

        if h_template is not None:
            h_output = os.path.basename(os.path.splitext(h_template)[0])
            # We always set template as the first element in the source array
            # so --template consumes it.
            h_cmd = cmd + ['--template', '@INPUT@']
            h_sources = [h_template] + sources
            custom_kwargs['install'] = install_header
            if 'install_dir' not in custom_kwargs:
                custom_kwargs['install_dir'] = \
                    state.environment.coredata.get_builtin_option('includedir')
            h_target = self._make_mkenum_custom_target(state, h_sources,
                                                       h_output, h_cmd,
                                                       custom_kwargs)
            targets.append(h_target)

        if c_template is not None:
            c_output = os.path.basename(os.path.splitext(c_template)[0])
            # We always set template as the first element in the source array
            # so --template consumes it.
            c_cmd = cmd + ['--template', '@INPUT@']
            c_sources = [c_template] + sources
            # Never install the C file. Complain on bug tracker if you need it.
            custom_kwargs['install'] = False
            if h_template is not None:
                if 'depends' in custom_kwargs:
                    custom_kwargs['depends'] += [h_target]
                else:
                    custom_kwargs['depends'] = h_target
            c_target = self._make_mkenum_custom_target(state, c_sources,
                                                       c_output, c_cmd,
                                                       custom_kwargs)
            targets.insert(0, c_target)

        if c_template is None and h_template is None:
            generic_cmd = cmd + ['@INPUT@']
            custom_kwargs['install'] = install_header
            if 'install_dir' not in custom_kwargs:
                custom_kwargs['install_dir'] = \
                    state.environment.coredata.get_builtin_option('includedir')
            target = self._make_mkenum_custom_target(state, sources, basename,
                                                     generic_cmd, custom_kwargs)
            return ModuleReturnValue(target, [target])
        elif len(targets) == 1:
            return ModuleReturnValue(targets[0], [targets[0]])
        else:
            return ModuleReturnValue(targets, targets)

    @FeatureNew('gnome.mkenums_simple', '0.42.0')
    def mkenums_simple(self, state, args, kwargs):
        hdr_filename = args[0] + '.h'
        body_filename = args[0] + '.c'

        # not really needed, just for sanity checking
        forbidden_kwargs = ['c_template', 'h_template', 'eprod', 'fhead',
                            'fprod', 'ftail', 'vhead', 'vtail', 'comments']
        for arg in forbidden_kwargs:
            if arg in kwargs:
                raise MesonException('mkenums_simple() does not take a %s keyword argument' % (arg, ))

        # kwargs to pass as-is from mkenums_simple() to mkenums()
        shared_kwargs = ['sources', 'install_header', 'install_dir',
                         'identifier_prefix', 'symbol_prefix']
        mkenums_kwargs = {}
        for arg in shared_kwargs:
            if arg in kwargs:
                mkenums_kwargs[arg] = kwargs[arg]

        # .c file generation
        c_file_kwargs = copy.deepcopy(mkenums_kwargs)
        if 'sources' not in kwargs:
            raise MesonException('Missing keyword argument "sources".')
        sources = kwargs['sources']
        if isinstance(sources, str):
            sources = [sources]
        elif not isinstance(sources, list):
            raise MesonException(
                'Sources keyword argument must be a string or array.')

        # The `install_header` argument will be used by mkenums() when
        # not using template files, so we need to forcibly unset it
        # when generating the C source file, otherwise we will end up
        # installing it
        c_file_kwargs['install_header'] = False

        header_prefix = kwargs.get('header_prefix', '')
        decl_decorator = kwargs.get('decorator', '')
        func_prefix = kwargs.get('function_prefix', '')
        body_prefix = kwargs.get('body_prefix', '')

        # Maybe we should write our own template files into the build dir
        # instead, but that seems like much more work, nice as it would be.
        fhead = ''
        if body_prefix != '':
            fhead += '%s\n' % body_prefix
        fhead += '#include "%s"\n' % hdr_filename
        for hdr in sources:
            fhead += '#include "%s"\n' % os.path.basename(str(hdr))
        fhead += '''
#define C_ENUM(v) ((gint) v)
#define C_FLAGS(v) ((guint) v)
'''
        c_file_kwargs['fhead'] = fhead

        c_file_kwargs['fprod'] = '''
/* enumerations from "@basename@" */
'''

        c_file_kwargs['vhead'] = '''
GType
%s@enum_name@_get_type (void)
{
  static volatile gsize gtype_id = 0;
  static const G@Type@Value values[] = {''' % func_prefix

        c_file_kwargs['vprod'] = '    { C_@TYPE@(@VALUENAME@), "@VALUENAME@", "@valuenick@" },'

        c_file_kwargs['vtail'] = '''    { 0, NULL, NULL }
  };
  if (g_once_init_enter (&gtype_id)) {
    GType new_type = g_@type@_register_static (g_intern_static_string ("@EnumName@"), values);
    g_once_init_leave (&gtype_id, new_type);
  }
  return (GType) gtype_id;
}'''

        rv = self.mkenums(state, [body_filename], c_file_kwargs)
        c_file = rv.return_value

        # .h file generation
        h_file_kwargs = copy.deepcopy(mkenums_kwargs)

        h_file_kwargs['fhead'] = '''#pragma once

#include <glib-object.h>
{}

G_BEGIN_DECLS
'''.format(header_prefix)

        h_file_kwargs['fprod'] = '''
/* enumerations from "@basename@" */
'''

        h_file_kwargs['vhead'] = '''
{}
GType {}@enum_name@_get_type (void);
#define @ENUMPREFIX@_TYPE_@ENUMSHORT@ ({}@enum_name@_get_type())'''.format(decl_decorator, func_prefix, func_prefix)

        h_file_kwargs['ftail'] = '''
G_END_DECLS'''

        rv = self.mkenums(state, [hdr_filename], h_file_kwargs)
        h_file = rv.return_value

        return ModuleReturnValue([c_file, h_file], [c_file, h_file])

    @staticmethod
    def _make_mkenum_custom_target(state, sources, output, cmd, kwargs):
        custom_kwargs = {
            'input': sources,
            'output': output,
            'capture': True,
            'command': cmd
        }
        custom_kwargs.update(kwargs)
        return build.CustomTarget(output, state.subdir, state.subproject, custom_kwargs,
                                  # https://github.com/mesonbuild/meson/issues/973
                                  absolute_paths=True)

    @permittedKwargs({'sources', 'prefix', 'install_header', 'install_dir', 'stdinc',
                      'nostdinc', 'internal', 'skip_source', 'valist_marshallers',
                      'extra_args'})
    def genmarshal(self, state, args, kwargs):
        if len(args) != 1:
            raise MesonException(
                'Genmarshal requires one positional argument.')
        output = args[0]

        if 'sources' not in kwargs:
            raise MesonException('Missing keyword argument "sources".')
        sources = kwargs.pop('sources')
        if isinstance(sources, str):
            sources = [sources]
        elif not isinstance(sources, list):
            raise MesonException(
                'Sources keyword argument must be a string or array.')

        new_genmarshal = mesonlib.version_compare(self._get_native_glib_version(state), '>= 2.53.3')

        cmd = [self.interpreter.find_program_impl('glib-genmarshal')]
        known_kwargs = ['internal', 'nostdinc', 'skip_source', 'stdinc',
                        'valist_marshallers', 'extra_args']
        known_custom_target_kwargs = ['build_always', 'depends',
                                      'depend_files', 'install_dir',
                                      'install_header']
        for arg, value in kwargs.items():
            if arg == 'prefix':
                cmd += ['--prefix', value]
            elif arg == 'extra_args':
                if new_genmarshal:
                    cmd += mesonlib.stringlistify(value)
                else:
                    mlog.warning('The current version of GLib does not support extra arguments \n'
                                 'for glib-genmarshal. You need at least GLib 2.53.3. See ',
                                 mlog.bold('https://github.com/mesonbuild/meson/pull/2049'))
            elif arg in known_kwargs and value:
                cmd += ['--' + arg.replace('_', '-')]
            elif arg not in known_custom_target_kwargs:
                raise MesonException(
                    'Genmarshal does not take a %s keyword argument.' % (
                        arg, ))

        install_header = kwargs.pop('install_header', False)
        install_dir = kwargs.pop('install_dir', None)

        custom_kwargs = {
            'input': sources,
        }

        # https://github.com/GNOME/glib/commit/0fbc98097fac4d3e647684f344e508abae109fdf
        if mesonlib.version_compare(self._get_native_glib_version(state), '>= 2.51.0'):
            cmd += ['--output', '@OUTPUT@']
        else:
            custom_kwargs['capture'] = True

        for arg in known_custom_target_kwargs:
            if arg in kwargs:
                custom_kwargs[arg] = kwargs[arg]

        header_file = output + '.h'
        custom_kwargs['command'] = cmd + ['--body', '@INPUT@']
        if mesonlib.version_compare(self._get_native_glib_version(state), '>= 2.53.4'):
            # Silence any warnings about missing prototypes
            custom_kwargs['command'] += ['--include-header', header_file]
        custom_kwargs['output'] = output + '.c'
        body = build.CustomTarget(output + '_c', state.subdir, state.subproject, custom_kwargs)

        custom_kwargs['install'] = install_header
        if install_dir is not None:
            custom_kwargs['install_dir'] = install_dir
        if new_genmarshal:
            cmd += ['--pragma-once']
        custom_kwargs['command'] = cmd + ['--header', '@INPUT@']
        custom_kwargs['output'] = header_file
        header = build.CustomTarget(output + '_h', state.subdir, state.subproject, custom_kwargs)

        rv = [body, header]
        return ModuleReturnValue(rv, rv)

    @staticmethod
    def _vapi_args_to_command(prefix, variable, kwargs, accept_vapi=False):
        arg_list = mesonlib.extract_as_list(kwargs, variable)
        ret = []
        for arg in arg_list:
            if not isinstance(arg, str):
                types = 'strings' + ' or InternalDependencys' if accept_vapi else ''
                raise MesonException('All {} must be {}'.format(variable, types))
            ret.append(prefix + arg)
        return ret

    def _extract_vapi_packages(self, state, kwargs):
        '''
        Packages are special because we need to:
        - Get a list of packages for the .deps file
        - Get a list of depends for any VapiTargets
        - Get package name from VapiTargets
        - Add include dirs for any VapiTargets
        '''
        arg_list = kwargs.get('packages')
        if not arg_list:
            return [], [], [], []
        arg_list = mesonlib.listify(arg_list)
        vapi_depends = []
        vapi_packages = []
        vapi_includes = []
        ret = []
        remaining_args = []
        for arg in unholder(arg_list):
            if isinstance(arg, InternalDependency):
                targets = [t for t in arg.sources if isinstance(t, VapiTarget)]
                for target in targets:
                    srcdir = os.path.join(state.environment.get_source_dir(),
                                          target.get_subdir())
                    outdir = os.path.join(state.environment.get_build_dir(),
                                          target.get_subdir())
                    outfile = target.get_outputs()[0][:-5] # Strip .vapi
                    ret.append('--vapidir=' + outdir)
                    ret.append('--girdir=' + outdir)
                    ret.append('--pkg=' + outfile)
                    vapi_depends.append(target)
                    vapi_packages.append(outfile)
                    vapi_includes.append(srcdir)
            else:
                vapi_packages.append(arg)
                remaining_args.append(arg)

        kwargs['packages'] = remaining_args
        vapi_args = ret + self._vapi_args_to_command('--pkg=', 'packages', kwargs, accept_vapi=True)
        return vapi_args, vapi_depends, vapi_packages, vapi_includes

    def _generate_deps(self, state, library, packages, install_dir):
        outdir = state.environment.scratch_dir
        fname = os.path.join(outdir, library + '.deps')
        with open(fname, 'w') as ofile:
            for package in packages:
                ofile.write(package + '\n')
        return build.Data(mesonlib.File(True, outdir, fname), install_dir)

    def _get_vapi_link_with(self, target):
        link_with = []
        for dep in target.get_target_dependencies():
            if isinstance(dep, build.SharedLibrary):
                link_with.append(dep)
            elif isinstance(dep, GirTarget):
                link_with += self._get_vapi_link_with(dep)
        return link_with

    @permittedKwargs({'sources', 'packages', 'metadata_dirs', 'gir_dirs',
                      'vapi_dirs', 'install', 'install_dir'})
    def generate_vapi(self, state, args, kwargs):
        if len(args) != 1:
            raise MesonException('The library name is required')

        if not isinstance(args[0], str):
            raise MesonException('The first argument must be the name of the library')
        created_values = []

        library = args[0]
        build_dir = os.path.join(state.environment.get_build_dir(), state.subdir)
        source_dir = os.path.join(state.environment.get_source_dir(), state.subdir)
        pkg_cmd, vapi_depends, vapi_packages, vapi_includes = self._extract_vapi_packages(state, kwargs)
        if 'VAPIGEN' in os.environ:
            cmd = [self.interpreter.find_program_impl(os.environ['VAPIGEN'])]
        else:
            cmd = [self.interpreter.find_program_impl('vapigen')]
        cmd += ['--quiet', '--library=' + library, '--directory=' + build_dir]
        cmd += self._vapi_args_to_command('--vapidir=', 'vapi_dirs', kwargs)
        cmd += self._vapi_args_to_command('--metadatadir=', 'metadata_dirs', kwargs)
        cmd += self._vapi_args_to_command('--girdir=', 'gir_dirs', kwargs)
        cmd += pkg_cmd
        cmd += ['--metadatadir=' + source_dir]

        if 'sources' not in kwargs:
            raise MesonException('sources are required to generate the vapi file')

        inputs = mesonlib.extract_as_list(kwargs, 'sources')

        link_with = []
        for i in inputs:
            if isinstance(i, str):
                cmd.append(os.path.join(source_dir, i))
            elif hasattr(i, 'held_object') and isinstance(i.held_object, GirTarget):
                link_with += self._get_vapi_link_with(i.held_object)
                subdir = os.path.join(state.environment.get_build_dir(),
                                      i.held_object.get_subdir())
                gir_file = os.path.join(subdir, i.held_object.get_outputs()[0])
                cmd.append(gir_file)
            else:
                raise MesonException('Input must be a str or GirTarget')

        vapi_output = library + '.vapi'
        custom_kwargs = {
            'command': cmd,
            'input': inputs,
            'output': vapi_output,
            'depends': vapi_depends,
        }
        install_dir = kwargs.get('install_dir',
                                 os.path.join(state.environment.coredata.get_builtin_option('datadir'),
                                              'vala', 'vapi'))
        if kwargs.get('install'):
            custom_kwargs['install'] = kwargs['install']
            custom_kwargs['install_dir'] = install_dir

            # We shouldn't need this locally but we install it
            deps_target = self._generate_deps(state, library, vapi_packages, install_dir)
            created_values.append(deps_target)
        vapi_target = VapiTarget(vapi_output, state.subdir, state.subproject, custom_kwargs)

        # So to try our best to get this to just work we need:
        # - link with with the correct library
        # - include the vapi and dependent vapi files in sources
        # - add relevant directories to include dirs
        incs = [build.IncludeDirs(state.subdir, ['.'] + vapi_includes, False)]
        sources = [vapi_target] + vapi_depends
        rv = InternalDependency(None, incs, [], [], link_with, [], sources, [], {})
        created_values.append(rv)
        return ModuleReturnValue(rv, created_values)

def initialize(*args, **kwargs):
    return GnomeModule(*args, **kwargs)
