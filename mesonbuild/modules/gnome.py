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
functionality such as gobject-introspection and gresources.'''

from .. import build
import os
import sys
import copy
import subprocess
from . import ModuleReturnValue
from ..mesonlib import MesonException, OrderedSet, Popen_safe
from ..dependencies import Dependency, PkgConfigDependency, InternalDependency
from .. import mlog
from .. import mesonlib
from .. import compilers
from .. import interpreter
from . import GResourceTarget, GResourceHeaderTarget, GirTarget, TypelibTarget, VapiTarget
from . import find_program, get_include_args
from . import ExtensionModule


# gresource compilation is broken due to the way
# the resource compiler and Ninja clash about it
#
# https://github.com/ninja-build/ninja/issues/1184
# https://bugzilla.gnome.org/show_bug.cgi?id=774368
gresource_dep_needed_version = '>= 2.51.1'

native_glib_version = None
girwarning_printed = False
gdbuswarning_printed = False
gresource_warning_printed = False
_gir_has_extra_lib_arg = None

def gir_has_extra_lib_arg():
    global _gir_has_extra_lib_arg
    if _gir_has_extra_lib_arg is not None:
        return _gir_has_extra_lib_arg

    _gir_has_extra_lib_arg = False
    try:
        g_ir_scanner = find_program('g-ir-scanner', '').get_command()
        opts = Popen_safe(g_ir_scanner + ['--help'], stderr=subprocess.STDOUT)[1]
        _gir_has_extra_lib_arg = '--extra-library' in opts
    except (MesonException, FileNotFoundError, subprocess.CalledProcessError):
        pass
    return _gir_has_extra_lib_arg

class GnomeModule(ExtensionModule):
    gir_dep = None

    @staticmethod
    def _get_native_glib_version(state):
        global native_glib_version
        if native_glib_version is None:
            glib_dep = PkgConfigDependency('glib-2.0', state.environment,
                                           {'native': True})
            native_glib_version = glib_dep.get_version()
        return native_glib_version

    def __print_gresources_warning(self, state):
        global gresource_warning_printed
        if not gresource_warning_printed:
            if not mesonlib.version_compare(self._get_native_glib_version(state), gresource_dep_needed_version):
                mlog.warning('GLib compiled dependencies do not work reliably with \n'
                             'the current version of GLib. See the following upstream issue:',
                             mlog.bold('https://bugzilla.gnome.org/show_bug.cgi?id=774368'))
            gresource_warning_printed = True
        return []

    @staticmethod
    def _print_gdbus_warning():
        global gdbuswarning_printed
        if not gdbuswarning_printed:
            mlog.warning('Code generated with gdbus_codegen() requires the root directory be added to\n'
                         '  include_directories of targets with GLib < 2.51.3:',
                         mlog.bold('https://github.com/mesonbuild/meson/issues/1387'))
            gdbuswarning_printed = True

    def compile_resources(self, state, args, kwargs):
        self.__print_gresources_warning(state)
        glib_version = self._get_native_glib_version(state)

        cmd = ['glib-compile-resources', '@INPUT@']

        source_dirs = kwargs.pop('source_dir', [])
        if not isinstance(source_dirs, list):
            source_dirs = [source_dirs]

        if len(args) < 2:
            raise MesonException('Not enough arguments; the name of the resource '
                                 'and the path to the XML file are required')

        dependencies = kwargs.pop('dependencies', [])
        if not isinstance(dependencies, list):
            dependencies = [dependencies]
        # Validate dependencies
        for (ii, dep) in enumerate(dependencies):
            if hasattr(dep, 'held_object'):
                dependencies[ii] = dep = dep.held_object
            if not isinstance(dep, (mesonlib.File, build.CustomTarget)):
                m = 'Unexpected dependency type {!r} for gnome.compile_resources() ' \
                    '"dependencies" argument.\nPlease pass the return value of ' \
                    'custom_target() or configure_file()'
                raise MesonException(m.format(dep))
            if isinstance(dep, build.CustomTarget):
                if not mesonlib.version_compare(glib_version, gresource_dep_needed_version):
                    m = 'The "dependencies" argument of gnome.compile_resources() can not\n' \
                        'be used with the current version of glib-compile-resources due to\n' \
                        '<https://bugzilla.gnome.org/show_bug.cgi?id=774368>'
                    raise MesonException(m)

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
        # Always include current directory, but after paths set by user
        source_dirs.append(os.path.join(state.build_to_src, state.subdir))
        # Ensure build directories of generated deps are included
        source_dirs += subdirs

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
            output = args[0] + '.c'
            name = args[0] + '_c'

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
        target_c = GResourceTarget(name, state.subdir, kwargs)

        if gresource: # Only one target for .gresource files
            return ModuleReturnValue(target_c, [target_c])

        h_kwargs = {
            'command': cmd,
            'input': args[1],
            'output': args[0] + '.h',
            # The header doesn't actually care about the files yet it errors if missing
            'depends': depends
        }
        if install_header:
            h_kwargs['install'] = install_header
            h_kwargs['install_dir'] = kwargs.get('install_dir',
                                                 state.environment.coredata.get_builtin_option('includedir'))
        target_h = GResourceHeaderTarget(args[0] + '_h', state.subdir, h_kwargs)
        rv = [target_c, target_h]
        return ModuleReturnValue(rv, rv)

    def _get_gresource_dependencies(self, state, input_file, source_dirs, dependencies):

        cmd = ['glib-compile-resources',
               input_file,
               '--generate-dependencies']

        for source_dir in source_dirs:
            cmd += ['--sourcedir', os.path.join(state.subdir, source_dir)]
        cmd += ['--sourcedir', state.subdir] # Current dir

        pc, stdout, stderr = Popen_safe(cmd, cwd=state.environment.get_source_dir())
        if pc.returncode != 0:
            m = 'glib-compile-resources failed to get dependencies for {}:\n{}'
            mlog.warning(m.format(cmd[1], stderr))
            raise subprocess.CalledProcessError(pc.returncode, cmd)

        dep_files = stdout.split('\n')[:-1]

        # In generate-dependencies mode, glib-compile-resources doesn't raise
        # an error for missing resources but instead prints whatever filename
        # was listed in the input file.  That's good because it means we can
        # handle resource files that get generated as part of the build, as
        # follows.
        #
        # If there are multiple generated resource files with the same basename
        # then this code will get confused.

        def exists_in_srcdir(f):
            return os.path.exists(os.path.join(state.environment.get_source_dir(), f))
        missing_dep_files = [f for f in dep_files if not exists_in_srcdir(f)]

        depends = []
        subdirs = []
        for missing in missing_dep_files:
            found = False
            missing_basename = os.path.basename(missing)

            for dep in dependencies:
                if hasattr(dep, 'held_object'):
                    dep = dep.held_object
                if isinstance(dep, mesonlib.File):
                    if dep.fname == missing_basename:
                        found = True
                        dep_files.remove(missing)
                        dep_files.append(dep)
                        subdirs.append(dep.subdir)
                        break
                elif isinstance(dep, build.CustomTarget):
                    if dep.get_basename() == missing_basename:
                        found = True
                        dep_files.remove(missing)
                        dep_files.append(
                            mesonlib.File(
                                is_built=True,
                                subdir=dep.get_subdir(),
                                fname=dep.get_basename()))
                        depends.append(dep)
                        subdirs.append(dep.get_subdir())
                        break
                else:
                    raise RuntimeError('Unreachable code.')

            if not found:
                raise MesonException(
                    'Resource "%s" listed in "%s" was not found. If this is a '
                    'generated file, pass the target that generates it to '
                    'gnome.compile_resources() using the "dependencies" '
                    'keyword argument.' % (missing, input_file))

        return dep_files, depends, subdirs

    def _get_link_args(self, state, lib, depends=None, include_rpath=False,
                       use_gir_args=False):
        # Construct link args
        if gir_has_extra_lib_arg() and use_gir_args:
            link_command = ['--extra-library=' + lib.name]
        else:
            link_command = ['-l' + lib.name]
        if isinstance(lib, build.SharedLibrary):
            libdir = state.backend.get_target_dir(lib)
            link_command.append('-L' + libdir)
            # Needed for the following binutils bug:
            # https://github.com/mesonbuild/meson/issues/1911
            # However, g-ir-scanner does not understand -Wl,-rpath
            # so we need to use -L instead
            for d in state.backend.determine_rpath_dirs(lib):
                d = os.path.join(state.environment.get_build_dir(), d)
                link_command.append('-L' + d)
            if include_rpath:
                link_command.append('-Wl,-rpath,' + libdir)
            if depends:
                depends.append(lib)
        return link_command

    def _get_dependencies_flags(self, deps, state, depends=None, include_rpath=False,
                                use_gir_args=False):
        cflags = OrderedSet()
        ldflags = OrderedSet()
        gi_includes = OrderedSet()
        if not isinstance(deps, list):
            deps = [deps]

        for dep in deps:
            if hasattr(dep, 'held_object'):
                dep = dep.held_object
            if isinstance(dep, InternalDependency):
                cflags.update(get_include_args(dep.include_directories))
                for lib in dep.libraries:
                    ldflags.update(self._get_link_args(state, lib.held_object, depends, include_rpath))
                    libdepflags = self._get_dependencies_flags(lib.held_object.get_external_deps(), state, depends, include_rpath,
                                                               use_gir_args)
                    cflags.update(libdepflags[0])
                    ldflags.update(libdepflags[1])
                    gi_includes.update(libdepflags[2])
                extdepflags = self._get_dependencies_flags(dep.ext_deps, state, depends, include_rpath,
                                                           use_gir_args)
                cflags.update(extdepflags[0])
                ldflags.update(extdepflags[1])
                gi_includes.update(extdepflags[2])
                for source in dep.sources:
                    if hasattr(source, 'held_object') and isinstance(source.held_object, GirTarget):
                        gi_includes.update([os.path.join(state.environment.get_build_dir(),
                                            source.held_object.get_subdir())])
            # This should be any dependency other than an internal one.
            elif isinstance(dep, Dependency):
                cflags.update(dep.get_compile_args())
                for lib in dep.get_link_args():
                    if (os.path.isabs(lib) and
                            # For PkgConfigDependency only:
                            getattr(dep, 'is_libtool', False)):
                        lib_dir = os.path.dirname(lib)
                        ldflags.update(["-L%s" % lib_dir])
                        if include_rpath:
                            ldflags.update(['-Wl,-rpath {}'.format(lib_dir)])
                        libname = os.path.basename(lib)
                        if libname.startswith("lib"):
                            libname = libname[3:]
                        libname = libname.split(".so")[0]
                        lib = "-l%s" % libname
                    # Hack to avoid passing some compiler options in
                    if lib.startswith("-W"):
                        continue
                    if gir_has_extra_lib_arg() and use_gir_args:
                        lib = lib.replace('-l', '--extra-library=')
                    ldflags.update([lib])

                if isinstance(dep, PkgConfigDependency):
                    girdir = dep.get_pkgconfig_variable("girdir")
                    if girdir:
                        gi_includes.update([girdir])
            elif isinstance(dep, (build.StaticLibrary, build.SharedLibrary)):
                for incd in dep.get_include_dirs():
                    for idir in incd.get_incdirs():
                        cflags.update(["-I%s" % idir])
            else:
                mlog.log('dependency %s not handled to build gir files' % dep)
                continue

        return cflags, ldflags, gi_includes

    def generate_gir(self, state, args, kwargs):
        if len(args) != 1:
            raise MesonException('Gir takes one argument')
        if kwargs.get('install_dir'):
            raise MesonException('install_dir is not supported with generate_gir(), see "install_dir_gir" and "install_dir_typelib"')
        giscanner = find_program('g-ir-scanner', 'Gir')
        gicompiler = find_program('g-ir-compiler', 'Gir')
        girtarget = args[0]
        while hasattr(girtarget, 'held_object'):
            girtarget = girtarget.held_object
        if not isinstance(girtarget, (build.Executable, build.SharedLibrary)):
            raise MesonException('Gir target must be an executable or shared library')
        try:
            if not self.gir_dep:
                self.gir_dep = PkgConfigDependency('gobject-introspection-1.0',
                                                   state.environment,
                                                   {'native': True})
            pkgargs = self.gir_dep.get_compile_args()
        except Exception:
            raise MesonException('gobject-introspection dependency was not found, gir cannot be generated.')
        ns = kwargs.pop('namespace')
        nsversion = kwargs.pop('nsversion')
        libsources = kwargs.pop('sources')
        girfile = '%s-%s.gir' % (ns, nsversion)
        depends = [girtarget]
        gir_inc_dirs = []

        scan_command = [giscanner, '@INPUT@']
        scan_command += pkgargs
        scan_command += ['--no-libtool', '--namespace=' + ns, '--nsversion=' + nsversion, '--warn-all',
                         '--output', '@OUTPUT@']

        extra_args = mesonlib.stringlistify(kwargs.pop('extra_args', []))
        scan_command += extra_args
        scan_command += ['-I' + os.path.join(state.environment.get_source_dir(), state.subdir),
                         '-I' + os.path.join(state.environment.get_build_dir(), state.subdir)]
        scan_command += get_include_args(girtarget.get_include_dirs())

        if 'link_with' in kwargs:
            link_with = kwargs.pop('link_with')
            if not isinstance(link_with, list):
                link_with = [link_with]
            for link in link_with:
                scan_command += self._get_link_args(state, link.held_object, depends,
                                                    use_gir_args=True)

        if 'includes' in kwargs:
            includes = kwargs.pop('includes')
            if not isinstance(includes, list):
                includes = [includes]
            for inc in includes:
                if hasattr(inc, 'held_object'):
                    inc = inc.held_object
                if isinstance(inc, str):
                    scan_command += ['--include=%s' % (inc, )]
                elif isinstance(inc, GirTarget):
                    gir_inc_dirs += [
                        os.path.join(state.environment.get_build_dir(),
                                     inc.get_subdir()),
                    ]
                    scan_command += [
                        "--include=%s" % (inc.get_basename()[:-4], ),
                    ]
                    depends += [inc]
                else:
                    raise MesonException(
                        'Gir includes must be str, GirTarget, or list of them')

        cflags = []
        for lang, compiler in girtarget.compilers.items():
            # XXX: Can you use g-i with any other language?
            if lang in ('c', 'cpp', 'objc', 'objcpp', 'd'):
                break
        else:
            lang = None
            compiler = None
        if lang and compiler:
            if state.global_args.get(lang):
                cflags += state.global_args[lang]
            if state.project_args.get(lang):
                cflags += state.project_args[lang]
            sanitize = compiler.get_options().get('b_sanitize')
            if sanitize:
                cflags += compilers.sanitizer_compile_args(sanitize)
        if kwargs.get('symbol_prefix'):
            sym_prefix = kwargs.pop('symbol_prefix')
            if not isinstance(sym_prefix, str):
                raise MesonException('Gir symbol prefix must be str')
            scan_command += ['--symbol-prefix=%s' % sym_prefix]
        if kwargs.get('identifier_prefix'):
            identifier_prefix = kwargs.pop('identifier_prefix')
            if not isinstance(identifier_prefix, str):
                raise MesonException('Gir identifier prefix must be str')
            scan_command += ['--identifier-prefix=%s' % identifier_prefix]
        if kwargs.get('export_packages'):
            pkgs = kwargs.pop('export_packages')
            if isinstance(pkgs, str):
                scan_command += ['--pkg-export=%s' % pkgs]
            elif isinstance(pkgs, list):
                scan_command += ['--pkg-export=%s' % pkg for pkg in pkgs]
            else:
                raise MesonException('Gir export packages must be str or list')

        deps = kwargs.pop('dependencies', [])
        if not isinstance(deps, list):
            deps = [deps]
        deps = (girtarget.get_all_link_deps() + girtarget.get_external_deps() +
                deps)
        # Need to recursively add deps on GirTarget sources from our
        # dependencies and also find the include directories needed for the
        # typelib generation custom target below.
        typelib_includes = []
        for dep in deps:
            if hasattr(dep, 'held_object'):
                dep = dep.held_object
            # Add a dependency on each GirTarget listed in dependencies and add
            # the directory where it will be generated to the typelib includes
            if isinstance(dep, InternalDependency):
                for source in dep.sources:
                    if hasattr(source, 'held_object'):
                        source = source.held_object
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
            elif isinstance(dep, PkgConfigDependency):
                girdir = dep.get_pkgconfig_variable("girdir")
                if girdir and girdir not in typelib_includes:
                    typelib_includes.append(girdir)
        # ldflags will be misinterpreted by gir scanner (showing
        # spurious dependencies) but building GStreamer fails if they
        # are not used here.
        dep_cflags, ldflags, gi_includes = self._get_dependencies_flags(deps, state, depends,
                                                                        use_gir_args=True)
        cflags += list(dep_cflags)
        scan_command += ['--cflags-begin']
        scan_command += cflags
        scan_command += ['--cflags-end']
        # need to put our output directory first as we need to use the
        # generated libraries instead of any possibly installed system/prefix
        # ones.
        if isinstance(girtarget, build.SharedLibrary):
            scan_command += ["-L@PRIVATE_OUTDIR_ABS_%s@" % girtarget.get_id()]
        scan_command += list(ldflags)
        for i in gi_includes:
            scan_command += ['--add-include-path=%s' % i]

        inc_dirs = kwargs.pop('include_directories', [])
        if not isinstance(inc_dirs, list):
            inc_dirs = [inc_dirs]
        for incd in inc_dirs:
            if not isinstance(incd.held_object, (str, build.IncludeDirs)):
                raise MesonException(
                    'Gir include dirs should be include_directories().')
        scan_command += get_include_args(inc_dirs)
        scan_command += get_include_args(gir_inc_dirs + inc_dirs, prefix='--add-include-path=')

        if isinstance(girtarget, build.Executable):
            scan_command += ['--program', girtarget]
        elif isinstance(girtarget, build.SharedLibrary):
            libname = girtarget.get_basename()
            # Needed for the following binutils bug:
            # https://github.com/mesonbuild/meson/issues/1911
            # However, g-ir-scanner does not understand -Wl,-rpath
            # so we need to use -L instead
            for d in state.backend.determine_rpath_dirs(girtarget):
                d = os.path.join(state.environment.get_build_dir(), d)
                scan_command.append('-L' + d)
            scan_command += ['--library', libname]
        scankwargs = {'output': girfile,
                      'input': libsources,
                      'command': scan_command,
                      'depends': depends}
        if kwargs.get('install'):
            scankwargs['install'] = kwargs['install']
            scankwargs['install_dir'] = kwargs.get('install_dir_gir',
                                                   os.path.join(state.environment.get_datadir(), 'gir-1.0'))
        scan_target = GirTarget(girfile, state.subdir, scankwargs)

        typelib_output = '%s-%s.typelib' % (ns, nsversion)
        typelib_cmd = [gicompiler, scan_target, '--output', '@OUTPUT@']
        typelib_cmd += get_include_args(gir_inc_dirs, prefix='--includedir=')
        for incdir in typelib_includes:
            typelib_cmd += ["--includedir=" + incdir]

        typelib_kwargs = {
            'output': typelib_output,
            'command': typelib_cmd,
        }
        if kwargs.get('install'):
            typelib_kwargs['install'] = kwargs['install']
            typelib_kwargs['install_dir'] = kwargs.get('install_dir_typelib',
                                                       os.path.join(state.environment.get_libdir(), 'girepository-1.0'))
        typelib_target = TypelibTarget(typelib_output, state.subdir, typelib_kwargs)
        rv = [scan_target, typelib_target]
        return ModuleReturnValue(rv, rv)

    def compile_schemas(self, state, args, kwargs):
        if args:
            raise MesonException('Compile_schemas does not take positional arguments.')
        srcdir = os.path.join(state.build_to_src, state.subdir)
        outdir = state.subdir

        cmd = [find_program('glib-compile-schemas', 'gsettings-compile')]
        cmd += ['--targetdir', outdir, srcdir]
        kwargs['command'] = cmd
        kwargs['input'] = []
        kwargs['output'] = 'gschemas.compiled'
        if state.subdir == '':
            targetname = 'gsettings-compile'
        else:
            targetname = 'gsettings-compile-' + state.subdir
        target_g = build.CustomTarget(targetname, state.subdir, kwargs)
        return ModuleReturnValue(target_g, [target_g])

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
        symlinks = kwargs.pop('symlink_media', False)

        if not isinstance(symlinks, bool):
            raise MesonException('symlink_media must be a boolean')

        if kwargs:
            raise MesonException('Unknown arguments passed: {}'.format(', '.join(kwargs.keys())))

        script = [sys.executable, state.environment.get_build_command()]
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

        potargs = [state.environment.get_build_command(), '--internal', 'yelphelper', 'pot',
                   '--subdir=' + state.subdir,
                   '--id=' + project_id,
                   '--sources=' + source_str]
        pottarget = build.RunTarget('help-' + project_id + '-pot', sys.executable,
                                    potargs, [], state.subdir)

        poargs = [state.environment.get_build_command(), '--internal', 'yelphelper', 'update-po',
                  '--subdir=' + state.subdir,
                  '--id=' + project_id,
                  '--sources=' + source_str,
                  '--langs=' + '@@'.join(langs)]
        potarget = build.RunTarget('help-' + project_id + '-update-po', sys.executable,
                                   poargs, [], state.subdir)

        rv = [inscript, pottarget, potarget]
        return ModuleReturnValue(None, rv)

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
        if main_xml != '':
            if main_file != '':
                raise MesonException('You can only specify main_xml or main_sgml, not both.')
            main_file = main_xml
        targetname = modulename + '-doc'
        command = [sys.executable, state.environment.get_build_command()]

        namespace = kwargs.get('namespace', '')
        mode = kwargs.get('mode', 'auto')
        VALID_MODES = ('xml', 'sgml', 'none', 'auto')
        if mode not in VALID_MODES:
            raise MesonException('gtkdoc: Mode {} is not a valid mode: {}'.format(mode, VALID_MODES))

        src_dirs = kwargs['src_dir']
        if not isinstance(src_dirs, list):
            src_dirs = [src_dirs]
        header_dirs = []
        for src_dir in src_dirs:
            if hasattr(src_dir, 'held_object'):
                src_dir = src_dir.held_object
                if not isinstance(src_dir, build.IncludeDirs):
                    raise MesonException('Invalid keyword argument for src_dir.')
                for inc_dir in src_dir.get_incdirs():
                    header_dirs.append(os.path.join(state.environment.get_source_dir(),
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
                '--mode=' + mode]
        if namespace:
            args.append('--namespace=' + namespace)
        args += self._unpack_args('--htmlargs=', 'html_args', kwargs)
        args += self._unpack_args('--scanargs=', 'scan_args', kwargs)
        args += self._unpack_args('--scanobjsargs=', 'scanobjs_args', kwargs)
        args += self._unpack_args('--gobjects-types-file=', 'gobject_typesfile', kwargs, state)
        args += self._unpack_args('--fixxrefargs=', 'fixxref_args', kwargs)
        args += self._unpack_args('--mkdbargs=', 'mkdb_args', kwargs)
        args += self._unpack_args('--html-assets=', 'html_assets', kwargs, state)
        args += self._unpack_args('--content-files=', 'content_files', kwargs, state)
        args += self._unpack_args('--expand-content-files=', 'expand_content_files', kwargs, state)
        args += self._unpack_args('--ignore-headers=', 'ignore_headers', kwargs)
        args += self._unpack_args('--installdir=', 'install_dir', kwargs, state)
        args += self._get_build_args(kwargs, state)
        res = [build.RunTarget(targetname, command[0], command[1:] + args, [], state.subdir)]
        if kwargs.get('install', True):
            res.append(build.RunScript(command, args))
        return ModuleReturnValue(None, res)

    def _get_build_args(self, kwargs, state):
        args = []
        cflags, ldflags, gi_includes = self._get_dependencies_flags(kwargs.get('dependencies', []), state, include_rpath=True)
        inc_dirs = kwargs.get('include_directories', [])
        if not isinstance(inc_dirs, list):
            inc_dirs = [inc_dirs]
        for incd in inc_dirs:
            if not isinstance(incd.held_object, (str, build.IncludeDirs)):
                raise MesonException(
                    'Gir include dirs should be include_directories().')
        cflags.update(get_include_args(inc_dirs))
        if cflags:
            args += ['--cflags=%s' % ' '.join(cflags)]
        if ldflags:
            args += ['--ldflags=%s' % ' '.join(ldflags)]
        compiler = state.environment.coredata.compilers.get('c')
        if compiler:
            args += ['--cc=%s' % ' '.join(compiler.get_exelist())]
            args += ['--ld=%s' % ' '.join(compiler.get_linker_exelist())]

        return args

    def gtkdoc_html_dir(self, state, args, kwargs):
        if len(args) != 1:
            raise MesonException('Must have exactly one argument.')
        modulename = args[0]
        if not isinstance(modulename, str):
            raise MesonException('Argument must be a string')
        return ModuleReturnValue(os.path.join('share/gtkdoc/html', modulename), [])

    @staticmethod
    def _unpack_args(arg, kwarg_name, kwargs, expend_file_state=None):
        if kwarg_name not in kwargs:
            return []

        new_args = kwargs[kwarg_name]
        if not isinstance(new_args, list):
            new_args = [new_args]
        args = []
        for i in new_args:
            if expend_file_state and isinstance(i, mesonlib.File):
                i = os.path.join(expend_file_state.environment.get_build_dir(), i.subdir, i.fname)
            elif not isinstance(i, str):
                raise MesonException(kwarg_name + ' values must be strings.')
            args.append(i)

        if args:
            return [arg + '@@'.join(args)]

        return []

    def gdbus_codegen(self, state, args, kwargs):
        if len(args) != 2:
            raise MesonException('Gdbus_codegen takes two arguments, name and xml file.')
        namebase = args[0]
        xml_file = args[1]
        target_name = namebase + '-gdbus'
        cmd = [find_program('gdbus-codegen', target_name)]
        if 'interface_prefix' in kwargs:
            cmd += ['--interface-prefix', kwargs.pop('interface_prefix')]
        if 'namespace' in kwargs:
            cmd += ['--c-namespace', kwargs.pop('namespace')]
        if kwargs.get('object_manager', False):
            cmd += ['--c-generate-object-manager']

        # https://git.gnome.org/browse/glib/commit/?id=ee09bb704fe9ccb24d92dd86696a0e6bb8f0dc1a
        if mesonlib.version_compare(self._get_native_glib_version(state), '>= 2.51.3'):
            cmd += ['--output-directory', '@OUTDIR@', '--generate-c-code', namebase, '@INPUT@']
        else:
            self._print_gdbus_warning()
            cmd += ['--generate-c-code', '@OUTDIR@/' + namebase, '@INPUT@']
        outputs = [namebase + '.c', namebase + '.h']
        custom_kwargs = {'input': xml_file,
                         'output': outputs,
                         'command': cmd
                         }
        ct = build.CustomTarget(target_name, state.subdir, custom_kwargs)
        return ModuleReturnValue(ct, [ct])

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
                if 'template' in kwargs:
                    raise MesonException('Mkenums does not accept both '
                                         'c_template and template keyword '
                                         'arguments at the same time.')
            elif arg == 'h_template':
                h_template = value
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
        cmd = [find_program('glib-mkenums', 'mkenums')] + cmd
        custom_kwargs = {}
        for arg in known_custom_target_kwargs:
            if arg in kwargs:
                custom_kwargs[arg] = kwargs[arg]

        targets = []

        if h_template is not None:
            h_output = os.path.splitext(h_template)[0]
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
            c_output = os.path.splitext(c_template)[0]
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

    @staticmethod
    def _make_mkenum_custom_target(state, sources, output, cmd, kwargs):
        custom_kwargs = {
            'input': sources,
            'output': output,
            'capture': True,
            'command': cmd
        }
        custom_kwargs.update(kwargs)
        return build.CustomTarget(output, state.subdir, custom_kwargs,
                                  # https://github.com/mesonbuild/meson/issues/973
                                  absolute_paths=True)

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

        cmd = [find_program('glib-genmarshal', output + '_genmarshal')]
        known_kwargs = ['internal', 'nostdinc', 'skip_source', 'stdinc',
                        'valist_marshallers']
        known_custom_target_kwargs = ['build_always', 'depends',
                                      'depend_files', 'install_dir',
                                      'install_header']
        for arg, value in kwargs.items():
            if arg == 'prefix':
                cmd += ['--prefix', value]
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

        custom_kwargs['command'] = cmd + ['--body', '@INPUT@']
        custom_kwargs['output'] = output + '.c'
        body = build.CustomTarget(output + '_c', state.subdir, custom_kwargs)

        custom_kwargs['install'] = install_header
        if install_dir is not None:
            custom_kwargs['install_dir'] = install_dir
        custom_kwargs['command'] = cmd + ['--header', '@INPUT@']
        custom_kwargs['output'] = output + '.h'
        header = build.CustomTarget(output + '_h', state.subdir, custom_kwargs)

        rv = [body, header]
        return ModuleReturnValue(rv, rv)

    @staticmethod
    def _vapi_args_to_command(prefix, variable, kwargs, accept_vapi=False):
        arg_list = kwargs.get(variable)
        if not arg_list:
            return []
        ret = []
        if not isinstance(arg_list, list):
            arg_list = [arg_list]
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
        if not isinstance(arg_list, list):
            arg_list = [arg_list]

        vapi_depends = []
        vapi_packages = []
        vapi_includes = []
        ret = []
        remaining_args = []
        for arg in arg_list:
            if hasattr(arg, 'held_object'):
                arg = arg.held_object
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
        cmd = [find_program('vapigen', 'Vaapi')]
        cmd += ['--quiet', '--library=' + library, '--directory=' + build_dir]
        cmd += self._vapi_args_to_command('--vapidir=', 'vapi_dirs', kwargs)
        cmd += self._vapi_args_to_command('--metadatadir=', 'metadata_dirs', kwargs)
        cmd += self._vapi_args_to_command('--girdir=', 'gir_dirs', kwargs)
        cmd += pkg_cmd
        cmd += ['--metadatadir=' + source_dir]

        inputs = kwargs.get('sources')
        if not inputs:
            raise MesonException('sources are required to generate the vapi file')

        if not isinstance(inputs, list):
            inputs = [inputs]

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
        vapi_target = VapiTarget(vapi_output, state.subdir, custom_kwargs)

        # So to try our best to get this to just work we need:
        # - link with with the correct library
        # - include the vapi and dependent vapi files in sources
        # - add relevant directories to include dirs
        incs = [build.IncludeDirs(state.subdir, ['.'] + vapi_includes, False)]
        sources = [vapi_target] + vapi_depends
        rv = InternalDependency(None, incs, [], [], link_with, sources, [])
        created_values.append(rv)
        return ModuleReturnValue(rv, created_values)

def initialize():
    return GnomeModule()
