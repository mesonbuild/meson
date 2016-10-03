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
import subprocess
from ..mesonlib import MesonException
from .. import dependencies
from .. import mlog
from .. import mesonlib

girwarning_printed = False
gresource_warning_printed = False

class GnomeModule:

    def __print_gresources_warning(self):
        global gresource_warning_printed
        if not gresource_warning_printed:
            mlog.log('Warning, glib compiled dependencies will not work reliably until this upstream issue is fixed:',
                     mlog.bold('https://bugzilla.gnome.org/show_bug.cgi?id=745754'))
            gresource_warning_printed = True
        return []

    def compile_resources(self, state, args, kwargs):
        self.__print_gresources_warning()

        cmd = ['glib-compile-resources', '@INPUT@']

        source_dirs = kwargs.pop('source_dir', [])
        if not isinstance(source_dirs, list):
            source_dirs = [source_dirs]

        # Always include current directory, but after paths set by user
        source_dirs.append(os.path.join(state.environment.get_source_dir(), state.subdir))

        if len(args) < 2:
            raise MesonException('Not enough arguments; The name of the resource and the path to the XML file are required')

        ifile = args[1]
        if isinstance(ifile, mesonlib.File):
            ifile = os.path.join(ifile.subdir, ifile.fname)
        elif isinstance(ifile, str):
            ifile = os.path.join(state.subdir, ifile)
        else:
            raise RuntimeError('Unreachable code.')
        kwargs['depend_files'] = self.get_gresource_dependencies(state, ifile, source_dirs)

        for source_dir in source_dirs:
            sourcedir = os.path.join(state.build_to_src, state.subdir, source_dir)
            cmd += ['--sourcedir', sourcedir]

        if 'c_name' in kwargs:
            cmd += ['--c-name', kwargs.pop('c_name')]
        cmd += ['--generate', '--target', '@OUTPUT@']

        cmd += mesonlib.stringlistify(kwargs.pop('extra_args', []))

        kwargs['command'] = cmd
        kwargs['input'] = args[1]
        kwargs['output'] = args[0] + '.c'
        target_c = build.CustomTarget(args[0] + '_c', state.subdir, kwargs)
        kwargs['output'] = args[0] + '.h'
        target_h = build.CustomTarget(args[0] + '_h', state.subdir, kwargs)
        return [target_c, target_h]

    def get_gresource_dependencies(self, state, input_file, source_dirs):
        self.__print_gresources_warning()

        cmd = ['glib-compile-resources',
               input_file,
               '--generate-dependencies']

        for source_dir in source_dirs:
            cmd += ['--sourcedir', os.path.join(state.subdir, source_dir)]

        pc = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True,
                              cwd=state.environment.get_source_dir())
        (stdout, _) = pc.communicate()
        if pc.returncode != 0:
            mlog.log(mlog.bold('Warning:'), 'glib-compile-resources has failed to get the dependencies for {}'.format(cmd[1]))
            raise subprocess.CalledProcessError(pc.returncode, cmd)

        return stdout.split('\n')[:-1]

    def get_link_args(self, state, lib, depends=None):
        link_command = ['-l%s' % lib.name]
        if isinstance(lib, build.SharedLibrary):
            link_command += ['-L%s' %
                    os.path.join(state.environment.get_build_dir(),
                        lib.subdir)]
            if depends:
                depends.append(lib)
        return link_command

    def get_include_args(self, state, include_dirs, prefix='-I'):
        if not include_dirs:
            return []

        dirs_str = []
        for incdirs in include_dirs:
            if hasattr(incdirs, "held_object"):
                dirs = incdirs.held_object
            else:
                dirs = incdirs

            if isinstance(dirs, str):
                dirs_str += ['%s%s' % (prefix, dirs)]
                continue

            # Should be build.IncludeDirs object.
            basedir = dirs.get_curdir()
            for d in dirs.get_incdirs():
                expdir =  os.path.join(basedir, d)
                srctreedir = os.path.join(state.environment.get_source_dir(), expdir)
                buildtreedir = os.path.join(state.environment.get_build_dir(), expdir)
                dirs_str += ['%s%s' % (prefix, buildtreedir),
                             '%s%s' % (prefix, srctreedir)]
            for d in dirs.get_extra_build_dirs():
                dirs_str += ['%s%s' % (prefix, d)]

        return dirs_str

    def get_dependencies_flags(self, deps, state, depends=None):
        cflags = set()
        ldflags = set()
        gi_includes = set()
        if not isinstance(deps, list):
            deps = [deps]

        for dep in deps:
            if hasattr(dep, 'held_object'):
                dep = dep.held_object
            if isinstance(dep, dependencies.InternalDependency):
                cflags.update(self.get_include_args( state, dep.include_directories))
                for lib in dep.libraries:
                    ldflags.update(self.get_link_args(state, lib.held_object, depends))
                    libdepflags = self.get_dependencies_flags(lib.held_object.get_external_deps(), state, depends)
                    cflags.update(libdepflags[0])
                    ldflags.update(libdepflags[1])
                    gi_includes.update(libdepflags[2])
                extdepflags = self.get_dependencies_flags(dep.ext_deps, state, depends)
                cflags.update(extdepflags[0])
                ldflags.update(extdepflags[1])
                gi_includes.update(extdepflags[2])
                for source in dep.sources:
                    if isinstance(source.held_object, GirTarget):
                        gi_includes.update([os.path.join(state.environment.get_build_dir(),
                                        source.held_object.get_subdir())])
            # This should be any dependency other than an internal one.
            elif isinstance(dep, dependencies.Dependency):
                cflags.update(dep.get_compile_args())
                for lib in dep.get_link_args():
                    if (os.path.isabs(lib) and
                            # For PkgConfigDependency only:
                            getattr(dep, 'is_libtool', False)):
                        ldflags.update(["-L%s" % os.path.dirname(lib)])
                        libname = os.path.basename(lib)
                        if libname.startswith("lib"):
                            libname = libname[3:]
                        libname = libname.split(".so")[0]
                        lib = "-l%s" % libname
                    # Hack to avoid passing some compiler options in
                    if lib.startswith("-W"):
                        continue
                    ldflags.update([lib])

                if isinstance(dep, dependencies.PkgConfigDependency):
                    girdir = dep.get_variable("girdir")
                    if girdir:
                        gi_includes.update([girdir])
            elif isinstance(dep, (build.StaticLibrary, build.SharedLibrary)):
                for incd in dep.get_include_dirs():
                    cflags.update(incd.get_incdirs())
            else:
                mlog.log('dependency %s not handled to build gir files' % dep)
                continue

        return cflags, ldflags, gi_includes

    def generate_gir(self, state, args, kwargs):
        if len(args) != 1:
            raise MesonException('Gir takes one argument')
        if kwargs.get('install_dir'):
            raise MesonException('install_dir is not supported with generate_gir(), see "install_dir_gir" and "install_dir_typelib"')
        girtarget = args[0]
        while hasattr(girtarget, 'held_object'):
            girtarget = girtarget.held_object
        if not isinstance(girtarget, (build.Executable, build.SharedLibrary)):
            raise MesonException('Gir target must be an executable or shared library')
        try:
            pkgstr = subprocess.check_output(['pkg-config', '--cflags', 'gobject-introspection-1.0'])
        except Exception:
            global girwarning_printed
            if not girwarning_printed:
                mlog.log(mlog.bold('Warning:'), 'gobject-introspection dependency was not found, disabling gir generation.')
                girwarning_printed = True
            return []
        pkgargs = pkgstr.decode().strip().split()
        ns = kwargs.pop('namespace')
        nsversion = kwargs.pop('nsversion')
        libsources = kwargs.pop('sources')
        girfile = '%s-%s.gir' % (ns, nsversion)
        depends = [girtarget]
        gir_inc_dirs = []

        scan_command = ['g-ir-scanner', '@INPUT@']
        scan_command += pkgargs
        scan_command += ['--no-libtool', '--namespace='+ns, '--nsversion=' + nsversion, '--warn-all',
                         '--output', '@OUTPUT@']

        extra_args = mesonlib.stringlistify(kwargs.pop('extra_args', []))
        scan_command += extra_args
        scan_command += ['-I' + os.path.join(state.environment.get_source_dir(), state.subdir)]
        scan_command += self.get_include_args(state, girtarget.get_include_dirs())

        if 'link_with' in kwargs:
            link_with = kwargs.pop('link_with')
            if not isinstance(link_with, list):
                link_with = [link_with]
            for link in link_with:
                scan_command += self.get_link_args(state, link.held_object, depends)

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
        if state.global_args.get('c'):
            scan_command += ['--cflags-begin']
            scan_command += state.global_args['c']
            scan_command += ['--cflags-end']
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
        cflags, ldflags, gi_includes = self.get_dependencies_flags(deps, state, depends)
        scan_command += list(cflags) + list(ldflags)
        for i in gi_includes:
            scan_command += ['--add-include-path=%s' % i]

        inc_dirs = kwargs.pop('include_directories', [])
        if not isinstance(inc_dirs, list):
            inc_dirs = [inc_dirs]
        for incd in inc_dirs:
            if not isinstance(incd.held_object, (str, build.IncludeDirs)):
                raise MesonException(
                    'Gir include dirs should be include_directories().')
        scan_command += self.get_include_args(state, inc_dirs)
        scan_command += self.get_include_args(state, gir_inc_dirs + inc_dirs,
                                              prefix='--add-include-path=')

        if isinstance(girtarget, build.Executable):
            scan_command += ['--program', girtarget]
        elif isinstance(girtarget, build.SharedLibrary):
            scan_command += ["-L@PRIVATE_OUTDIR_ABS_%s@" % girtarget.get_id()]
            libname = girtarget.get_basename()
            scan_command += ['--library', libname]
        scankwargs = {'output' : girfile,
                      'input' : libsources,
                      'command' : scan_command,
                      'depends' : depends,
                     }
        if kwargs.get('install'):
            scankwargs['install'] = kwargs['install']
            scankwargs['install_dir'] = kwargs.get('install_dir_gir',
                os.path.join(state.environment.get_datadir(), 'gir-1.0'))
        scan_target = GirTarget(girfile, state.subdir, scankwargs)

        typelib_output = '%s-%s.typelib' % (ns, nsversion)
        typelib_cmd = ['g-ir-compiler', scan_target, '--output', '@OUTPUT@']
        typelib_cmd += self.get_include_args(state, gir_inc_dirs,
                                             prefix='--includedir=')
        for dep in deps:
            if hasattr(dep, 'held_object'):
                dep = dep.held_object
            if isinstance(dep, dependencies.InternalDependency):
                for source in dep.sources:
                    if isinstance(source.held_object, GirTarget):
                        typelib_cmd += [
                            "--includedir=%s" % (
                                os.path.join(state.environment.get_build_dir(),
                                             source.held_object.get_subdir()),
                            )
                        ]
            elif isinstance(dep, dependencies.PkgConfigDependency):
                girdir = dep.get_variable("girdir")
                if girdir:
                    typelib_cmd += ["--includedir=%s" % (girdir, )]

        typelib_kwargs = {
            'output': typelib_output,
            'command': typelib_cmd,
        }
        if kwargs.get('install'):
            typelib_kwargs['install'] = kwargs['install']
            typelib_kwargs['install_dir'] = kwargs.get('install_dir_typelib',
                os.path.join(state.environment.get_libdir(), 'girepository-1.0'))
        typelib_target = TypelibTarget(typelib_output, state.subdir, typelib_kwargs)
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

    def gtkdoc(self, state, args, kwargs):
        if len(args) != 1:
            raise MesonException('Gtkdoc must have one positional argument.')
        modulename = args[0]
        if not isinstance(modulename, str):
            raise MesonException('Gtkdoc arg must be string.')
        if not 'src_dir' in kwargs:
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
        src_dir = kwargs['src_dir']
        targetname = modulename + '-doc'
        command = [state.environment.get_build_command(), '--internal', 'gtkdoc']
        if hasattr(src_dir, 'held_object'):
            src_dir= src_dir.held_object
            if not isinstance(src_dir, build.IncludeDirs):
                raise MesonException('Invalid keyword argument for src_dir.')
            incdirs = src_dir.get_incdirs()
            if len(incdirs) != 1:
                raise MesonException('Argument src_dir has more than one directory specified.')
            header_dir = os.path.join(state.environment.get_source_dir(), src_dir.get_curdir(), incdirs[0])
        else:
            header_dir = os.path.normpath(os.path.join(state.subdir, src_dir))
        args = ['--sourcedir=' + state.environment.get_source_dir(),
                '--builddir=' + state.environment.get_build_dir(),
                '--subdir=' + state.subdir,
                '--headerdir=' + header_dir,
                '--mainfile=' + main_file,
                '--modulename=' + modulename]
        args += self.unpack_args('--htmlargs=', 'html_args', kwargs)
        args += self.unpack_args('--scanargs=', 'scan_args', kwargs)
        args += self.unpack_args('--scanobjsargs=', 'scanobjs_args', kwargs)
        args += self.unpack_args('--gobjects-types-file=', 'gobject_typesfile', kwargs, state)
        args += self.unpack_args('--fixxrefargs=', 'fixxref_args', kwargs)
        args += self.unpack_args('--html-assets=', 'html_assets', kwargs, state)
        args += self.unpack_args('--content-files=', 'content_files', kwargs, state)
        args += self.unpack_args('--installdir=', 'install_dir', kwargs, state)
        args += self.get_build_args(kwargs, state)
        res = [build.RunTarget(targetname, command[0], command[1:] + args, [], state.subdir)]
        if kwargs.get('install', True):
            res.append(build.InstallScript(command + args))
        return res

    def get_build_args(self, kwargs, state):
        args = []
        cflags, ldflags, gi_includes = self.get_dependencies_flags(kwargs.get('dependencies', []), state)
        inc_dirs = kwargs.get('include_directories', [])
        if not isinstance(inc_dirs, list):
            inc_dirs = [inc_dirs]
        for incd in inc_dirs:
            if not isinstance(incd.held_object, (str, build.IncludeDirs)):
                raise MesonException(
                    'Gir include dirs should be include_directories().')
        cflags.update(self.get_include_args(state, inc_dirs))
        if cflags:
            args += ['--cflags=%s' % ' '.join(cflags)]
        if ldflags:
            args += ['--ldflags=%s' % ' '.join(ldflags)]
        compiler = state.environment.coredata.compilers.get('c')
        if compiler:
            args += ['--cc=%s' % ' '.join(compiler.get_exelist())]
            args += ['--ld=%s' % ' '.join(compiler.get_linker_exelist())]

        return args

    def gtkdoc_html_dir(self, state, args, kwarga):
        if len(args) != 1:
            raise MesonException('Must have exactly one argument.')
        modulename = args[0]
        if not isinstance(modulename, str):
            raise MesonException('Argument must be a string')
        return os.path.join('share/gtkdoc/html', modulename)


    def unpack_args(self, arg, kwarg_name, kwargs, expend_file_state=None):
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
        cmd = ['gdbus-codegen']
        if 'interface_prefix' in kwargs:
            cmd += ['--interface-prefix', kwargs.pop('interface_prefix')]
        if 'namespace' in kwargs:
            cmd += ['--c-namespace', kwargs.pop('namespace')]
        cmd += ['--generate-c-code', '@OUTDIR@/' + namebase, '@INPUT@']
        outputs = [namebase + '.c', namebase + '.h']
        custom_kwargs = {'input' : xml_file,
                         'output' : outputs,
                         'command' : cmd
                         }
        return build.CustomTarget(namebase + '-gdbus', state.subdir, custom_kwargs)

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
        known_custom_target_kwargs = ['install', 'install_dir', 'build_always',
                                      'depends', 'depend_files']
        c_template = h_template = None
        install_header = False
        for arg, value in kwargs.items():
            if arg == 'sources':
                sources = [value] + sources
            elif arg == 'c_template':
                c_template = value
            elif arg == 'h_template':
                h_template = value
            elif arg == 'install_header':
                install_header = value
            elif arg in known_kwargs:
                cmd += ['--' + arg.replace('_', '-'), value]
            elif arg not in known_custom_target_kwargs:
                raise MesonException(
                    'Mkenums does not take a %s keyword argument.' % (arg, ))
        cmd = ['glib-mkenums'] + cmd
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
            h_target = self.make_mkenum_custom_target(state, h_sources,
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
            c_target = self.make_mkenum_custom_target(state, c_sources,
                                                      c_output, c_cmd,
                                                      custom_kwargs)
            targets.insert(0, c_target)

        if c_template is None and h_template is None:
            generic_cmd = cmd + ['@INPUT@']
            custom_kwargs['install'] = install_header
            if 'install_dir' not in custom_kwargs:
                custom_kwargs['install_dir'] = \
                    state.environment.coredata.get_builtin_option('includedir')
            target = self.make_mkenum_custom_target(state, sources, basename,
                                                    generic_cmd, custom_kwargs)
            return target
        elif len(targets) == 1:
            return targets[0]
        else:
            return targets

    def make_mkenum_custom_target(self, state, sources, output, cmd, kwargs):
        custom_kwargs = {
            'input': sources,
            'output': output,
            'capture': True,
            'command': cmd
        }
        custom_kwargs.update(kwargs)
        return build.CustomTarget(output, state.subdir, custom_kwargs)

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

        cmd = ['glib-genmarshal']
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
            'capture': True,
        }
        for arg in known_custom_target_kwargs:
            if arg in kwargs:
                custom_kwargs[arg] = kwargs[arg]

        custom_kwargs['command'] = cmd + ['--header', '--body', '@INPUT@']
        custom_kwargs['output'] = output + '.c'
        body = build.CustomTarget(output + '_c', state.subdir, custom_kwargs)

        custom_kwargs['install'] = install_header
        if install_dir is not None:
            custom_kwargs['install_dir'] = install_dir
        custom_kwargs['command'] = cmd + ['--header', '@INPUT@']
        custom_kwargs['output'] = output + '.h'
        header = build.CustomTarget(output + '_h', state.subdir, custom_kwargs)

        return [body, header]


def initialize():
    return GnomeModule()

class GirTarget(build.CustomTarget):
    def __init__(self, name, subdir, kwargs):
        super().__init__(name, subdir, kwargs)

class TypelibTarget(build.CustomTarget):
    def __init__(self, name, subdir, kwargs):
        super().__init__(name, subdir, kwargs)
