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

from pathlib import PurePath
import os
import typing as T

from . import ExtensionModule
from . import ModuleReturnValue
from .. import build
from .. import dependencies
from .. import mesonlib
from .. import mlog
from ..dependencies import ThreadDependency
from ..interpreterbase import permittedKwargs, FeatureNew, FeatureNewKwargs

if T.TYPE_CHECKING:
    from . import ModuleState

already_warned_objs = set()

class DependenciesHelper:
    def __init__(self, state, name):
        self.state = state
        self.name = name
        self.pub_libs = []
        self.pub_reqs = []
        self.priv_libs = []
        self.priv_reqs = []
        self.cflags = []
        self.version_reqs = {}
        self.link_whole_targets = []

    def add_pub_libs(self, libs):
        libs, reqs, cflags = self._process_libs(libs, True)
        self.pub_libs = libs + self.pub_libs # prepend to preserve dependencies
        self.pub_reqs += reqs
        self.cflags += cflags

    def add_priv_libs(self, libs):
        libs, reqs, _ = self._process_libs(libs, False)
        self.priv_libs = libs + self.priv_libs
        self.priv_reqs += reqs

    def add_pub_reqs(self, reqs):
        self.pub_reqs += self._process_reqs(reqs)

    def add_priv_reqs(self, reqs):
        self.priv_reqs += self._process_reqs(reqs)

    def _check_generated_pc_deprecation(self, obj):
        if not hasattr(obj, 'generated_pc_warn'):
            return
        name = obj.generated_pc_warn[0]
        if (name, obj.name) in already_warned_objs:
            return
        mlog.deprecation('Library', mlog.bold(obj.name), 'was passed to the '
                         '"libraries" keyword argument of a previous call '
                         'to generate() method instead of first positional '
                         'argument.', 'Adding', mlog.bold(obj.generated_pc),
                         'to "Requires" field, but this is a deprecated '
                         'behaviour that will change in a future version '
                         'of Meson. Please report the issue if this '
                         'warning cannot be avoided in your case.',
                         location=obj.generated_pc_warn[1])
        already_warned_objs.add((name, obj.name))

    def _process_reqs(self, reqs):
        '''Returns string names of requirements'''
        processed_reqs = []
        for obj in mesonlib.listify(reqs):
            if not isinstance(obj, str):
                FeatureNew.single_use('pkgconfig.generate requirement from non-string object', '0.46.0', self.state.subproject)
            if hasattr(obj, 'generated_pc'):
                self._check_generated_pc_deprecation(obj)
                processed_reqs.append(obj.generated_pc)
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
            elif isinstance(obj, ThreadDependency):
                pass
            else:
                raise mesonlib.MesonException('requires argument not a string, '
                                              'library with pkgconfig-generated file '
                                              'or pkgconfig-dependency object, got {obj!r}')
        return processed_reqs

    def add_cflags(self, cflags):
        self.cflags += mesonlib.stringlistify(cflags)

    def _process_libs(self, libs, public: bool):
        libs = mesonlib.listify(libs)
        processed_libs = []
        processed_reqs = []
        processed_cflags = []
        for obj in libs:
            if hasattr(obj, 'generated_pc'):
                self._check_generated_pc_deprecation(obj)
                processed_reqs.append(obj.generated_pc)
            elif isinstance(obj, dependencies.PkgConfigDependency):
                if obj.found():
                    processed_reqs.append(obj.name)
                    self.add_version_reqs(obj.name, obj.version_reqs)
            elif isinstance(obj, dependencies.InternalDependency):
                if obj.found():
                    processed_libs += obj.get_link_args()
                    processed_cflags += obj.get_compile_args()
                    self._add_lib_dependencies(obj.libraries, obj.whole_libraries, obj.ext_deps, public, private_external_deps=True)
            elif isinstance(obj, dependencies.Dependency):
                if obj.found():
                    processed_libs += obj.get_link_args()
                    processed_cflags += obj.get_compile_args()
            elif isinstance(obj, build.SharedLibrary) and obj.shared_library_only:
                # Do not pull dependencies for shared libraries because they are
                # only required for static linking. Adding private requires has
                # the side effect of exposing their cflags, which is the
                # intended behaviour of pkg-config but force Debian to add more
                # than needed build deps.
                # See https://bugs.freedesktop.org/show_bug.cgi?id=105572
                processed_libs.append(obj)
            elif isinstance(obj, (build.SharedLibrary, build.StaticLibrary)):
                processed_libs.append(obj)
                # If there is a static library in `Libs:` all its deps must be
                # public too, otherwise the generated pc file will never be
                # usable without --static.
                self._add_lib_dependencies(obj.link_targets,
                                           obj.link_whole_targets,
                                           obj.external_deps,
                                           isinstance(obj, build.StaticLibrary) and public)
            elif isinstance(obj, (build.CustomTarget, build.CustomTargetIndex)):
                if not obj.is_linkable_target():
                    raise mesonlib.MesonException('library argument contains a not linkable custom_target.')
                FeatureNew.single_use('custom_target in pkgconfig.generate libraries', '0.58.0', self.state.subproject)
                processed_libs.append(obj)
            elif isinstance(obj, str):
                processed_libs.append(obj)
            else:
                raise mesonlib.MesonException(f'library argument of type {type(obj).__name__} not a string, library or dependency object.')

        return processed_libs, processed_reqs, processed_cflags

    def _add_lib_dependencies(self, link_targets, link_whole_targets, external_deps, public, private_external_deps=False):
        add_libs = self.add_pub_libs if public else self.add_priv_libs
        # Recursively add all linked libraries
        for t in link_targets:
            # Internal libraries (uninstalled static library) will be promoted
            # to link_whole, treat them as such here.
            if t.is_internal():
                self._add_link_whole(t, public)
            else:
                add_libs([t])
        for t in link_whole_targets:
            self._add_link_whole(t, public)
        # And finally its external dependencies
        if private_external_deps:
            self.add_priv_libs(external_deps)
        else:
            add_libs(external_deps)

    def _add_link_whole(self, t, public):
        # Don't include static libraries that we link_whole. But we still need to
        # include their dependencies: a static library we link_whole
        # could itself link to a shared library or an installed static library.
        # Keep track of link_whole_targets so we can remove them from our
        # lists in case a library is link_with and link_whole at the same time.
        # See remove_dups() below.
        self.link_whole_targets.append(t)
        if isinstance(t, build.BuildTarget):
            self._add_lib_dependencies(t.link_targets, t.link_whole_targets, t.external_deps, public)

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
        # Set of ids that have already been handled and should not be added any more
        exclude = set()

        # We can't just check if 'x' is excluded because we could have copies of
        # the same SharedLibrary object for example.
        def _ids(x):
            if hasattr(x, 'generated_pc'):
                yield x.generated_pc
            if isinstance(x, build.Target):
                yield x.get_id()
            yield x

        # Exclude 'x' in all its forms and return if it was already excluded
        def _add_exclude(x):
            was_excluded = False
            for i in _ids(x):
                if i in exclude:
                    was_excluded = True
                else:
                    exclude.add(i)
            return was_excluded

        # link_whole targets are already part of other targets, exclude them all.
        for t in self.link_whole_targets:
            _add_exclude(t)

        def _fn(xs, libs=False):
            # Remove duplicates whilst preserving original order
            result = []
            for x in xs:
                # Don't de-dup unknown strings to avoid messing up arguments like:
                # ['-framework', 'CoreAudio', '-framework', 'CoreMedia']
                known_flags = ['-pthread']
                cannot_dedup = libs and isinstance(x, str) and \
                    not x.startswith(('-l', '-L')) and \
                    x not in known_flags
                if not cannot_dedup and _add_exclude(x):
                    continue
                result.append(x)
            return result

        # Handle lists in priority order: public items can be excluded from
        # private and Requires can excluded from Libs.
        self.pub_reqs = _fn(self.pub_reqs)
        self.pub_libs = _fn(self.pub_libs, True)
        self.priv_reqs = _fn(self.priv_reqs)
        self.priv_libs = _fn(self.priv_libs, True)
        # Reset exclude list just in case some values can be both cflags and libs.
        exclude = set()
        self.cflags = _fn(self.cflags)

class PkgConfigModule(ExtensionModule):
    def __init__(self, interpreter):
        super().__init__(interpreter)
        self.methods.update({
            'generate': self.generate,
        })

    def _get_lname(self, l, msg, pcfile, is_custom_target):
        if is_custom_target:
            basename = os.path.basename(l.get_filename())
            name = os.path.splitext(basename)[0]
            if name.startswith('lib'):
                name = name[3:]
            return name
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
        if isinstance(l, build.SharedLibrary) and l.import_filename:
            return l.name
        # In other cases, we can't guarantee that the compiler will be able to
        # find the library via '-lfoo', so tell the user that.
        mlog.warning(msg.format(l.name, 'name_prefix', l.name, pcfile))
        return l.name

    def _escape(self, value):
        '''
        We cannot use quote_arg because it quotes with ' and " which does not
        work with pkg-config and pkgconf at all.
        '''
        # We should always write out paths with / because pkg-config requires
        # spaces to be quoted with \ and that messes up on Windows:
        # https://bugs.freedesktop.org/show_bug.cgi?id=103203
        if isinstance(value, PurePath):
            value = value.as_posix()
        return value.replace(' ', r'\ ')

    def _make_relative(self, prefix, subdir):
        prefix = PurePath(prefix)
        subdir = PurePath(subdir)
        try:
            libdir = subdir.relative_to(prefix)
        except ValueError:
            libdir = subdir
        # pathlib joining makes sure absolute libdir is not appended to '${prefix}'
        return ('${prefix}' / libdir).as_posix()

    def _generate_pkgconfig_file(self, state, deps, subdirs, name, description,
                                 url, version, pcfile, conflicts, variables,
                                 unescaped_variables, uninstalled=False, dataonly=False):
        coredata = state.environment.get_coredata()
        if uninstalled:
            outdir = os.path.join(state.environment.build_dir, 'meson-uninstalled')
            if not os.path.exists(outdir):
                os.mkdir(outdir)
            prefix = PurePath(state.environment.get_build_dir())
            srcdir = PurePath(state.environment.get_source_dir())
        else:
            outdir = state.environment.scratch_dir
            prefix = PurePath(coredata.get_option(mesonlib.OptionKey('prefix')))
        # These always return paths relative to prefix
        libdir = PurePath(coredata.get_option(mesonlib.OptionKey('libdir')))
        incdir = PurePath(coredata.get_option(mesonlib.OptionKey('includedir')))
        fname = os.path.join(outdir, pcfile)
        with open(fname, 'w', encoding='utf-8') as ofile:
            if not dataonly:
                ofile.write('prefix={}\n'.format(self._escape(prefix)))
                if uninstalled:
                    ofile.write('srcdir={}\n'.format(self._escape(srcdir)))
                ofile.write('libdir={}\n'.format(self._escape('${prefix}' / libdir)))
                ofile.write('includedir={}\n'.format(self._escape('${prefix}' / incdir)))
            if variables or unescaped_variables:
                ofile.write('\n')
            for k, v in variables:
                ofile.write('{}={}\n'.format(k, self._escape(v)))
            for k, v in unescaped_variables:
                ofile.write(f'{k}={v}\n')
            ofile.write('\n')
            ofile.write(f'Name: {name}\n')
            if len(description) > 0:
                ofile.write(f'Description: {description}\n')
            if len(url) > 0:
                ofile.write(f'URL: {url}\n')
            ofile.write(f'Version: {version}\n')
            reqs_str = deps.format_reqs(deps.pub_reqs)
            if len(reqs_str) > 0:
                ofile.write(f'Requires: {reqs_str}\n')
            reqs_str = deps.format_reqs(deps.priv_reqs)
            if len(reqs_str) > 0:
                ofile.write(f'Requires.private: {reqs_str}\n')
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
                        if uninstalled:
                            install_dir = os.path.dirname(state.backend.get_target_filename_abs(l))
                        else:
                            _i = l.get_custom_install_dir()
                            install_dir = _i[0] if _i else None
                        if install_dir is False:
                            continue
                        is_custom_target = isinstance(l, (build.CustomTarget, build.CustomTargetIndex))
                        if not is_custom_target and 'cs' in l.compilers:
                            if isinstance(install_dir, str):
                                Lflag = '-r{}/{}'.format(self._escape(self._make_relative(prefix, install_dir)), l.filename)
                            else:  # install_dir is True
                                Lflag = '-r${libdir}/%s' % l.filename
                        else:
                            if isinstance(install_dir, str):
                                Lflag = '-L{}'.format(self._escape(self._make_relative(prefix, install_dir)))
                            else:  # install_dir is True
                                Lflag = '-L${libdir}'
                        if Lflag not in Lflags:
                            Lflags.append(Lflag)
                            yield Lflag
                        lname = self._get_lname(l, msg, pcfile, is_custom_target)
                        # If using a custom suffix, the compiler may not be able to
                        # find the library
                        if not is_custom_target and l.name_suffix_set:
                            mlog.warning(msg.format(l.name, 'name_suffix', lname, pcfile))
                        if is_custom_target or 'cs' not in l.compilers:
                            yield f'-l{lname}'

            def get_uninstalled_include_dirs(libs):
                result = []
                for l in libs:
                    if isinstance(l, (str, build.CustomTarget, build.CustomTargetIndex)):
                        continue
                    if l.get_subdir() not in result:
                        result.append(l.get_subdir())
                    for i in l.get_include_dirs():
                        curdir = i.get_curdir()
                        for d in i.get_incdirs():
                            path = os.path.join(curdir, d)
                            if path not in result:
                                result.append(path)
                return result

            def generate_uninstalled_cflags(libs):
                for d in get_uninstalled_include_dirs(libs):
                    for basedir in ['${prefix}', '${srcdir}']:
                        path = PurePath(basedir, d)
                        yield '-I%s' % self._escape(path.as_posix())

            if len(deps.pub_libs) > 0:
                ofile.write('Libs: {}\n'.format(' '.join(generate_libs_flags(deps.pub_libs))))
            if len(deps.priv_libs) > 0:
                ofile.write('Libs.private: {}\n'.format(' '.join(generate_libs_flags(deps.priv_libs))))

            cflags = []
            if uninstalled:
                cflags += generate_uninstalled_cflags(deps.pub_libs + deps.priv_libs)
            else:
                for d in subdirs:
                    if d == '.':
                        cflags.append('-I${includedir}')
                    else:
                        cflags.append(self._escape(PurePath('-I${includedir}') / d))
            cflags += [self._escape(f) for f in deps.cflags]
            if cflags and not dataonly:
                ofile.write('Cflags: {}\n'.format(' '.join(cflags)))

    @FeatureNewKwargs('pkgconfig.generate', '0.59.0', ['unescaped_variables', 'unescaped_uninstalled_variables'])
    @FeatureNewKwargs('pkgconfig.generate', '0.54.0', ['uninstalled_variables'])
    @FeatureNewKwargs('pkgconfig.generate', '0.42.0', ['extra_cflags'])
    @FeatureNewKwargs('pkgconfig.generate', '0.41.0', ['variables'])
    @FeatureNewKwargs('pkgconfig.generate', '0.54.0', ['dataonly'])
    @permittedKwargs({'libraries', 'version', 'name', 'description', 'filebase',
                      'subdirs', 'requires', 'requires_private', 'libraries_private',
                      'install_dir', 'extra_cflags', 'variables', 'url', 'd_module_versions',
                      'dataonly', 'conflicts', 'uninstalled_variables',
                      'unescaped_variables', 'unescaped_uninstalled_variables'})
    def generate(self, state: 'ModuleState', args, kwargs):
        default_version = state.project_version
        default_install_dir = None
        default_description = None
        default_name = None
        mainlib = None
        default_subdirs = ['.']
        if not args and 'version' not in kwargs:
            FeatureNew.single_use('pkgconfig.generate implicit version keyword', '0.46.0', state.subproject)
        elif len(args) == 1:
            FeatureNew.single_use('pkgconfig.generate optional positional argument', '0.46.0', state.subproject)
            mainlib = args[0]
            if not isinstance(mainlib, (build.StaticLibrary, build.SharedLibrary)):
                raise mesonlib.MesonException('Pkgconfig_gen first positional argument must be a library object')
            default_name = mainlib.name
            default_description = state.project_name + ': ' + mainlib.name
            install_dir = mainlib.get_custom_install_dir()
            if install_dir and isinstance(install_dir[0], str):
                default_install_dir = os.path.join(install_dir[0], 'pkgconfig')
        elif len(args) > 1:
            raise mesonlib.MesonException('Too many positional arguments passed to Pkgconfig_gen.')

        dataonly = kwargs.get('dataonly', False)
        if not isinstance(dataonly, bool):
            raise mesonlib.MesonException('dataonly must be boolean.')
        if dataonly:
            default_subdirs = []
            blocked_vars = ['libraries', 'libraries_private', 'require_private', 'extra_cflags', 'subdirs']
            if any(k in kwargs for k in blocked_vars):
                raise mesonlib.MesonException(f'Cannot combine dataonly with any of {blocked_vars}')

        subdirs = mesonlib.stringlistify(kwargs.get('subdirs', default_subdirs))
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

        # Prepend the main library to public libraries list. This is required
        # so dep.add_pub_libs() can handle dependency ordering correctly and put
        # extra libraries after the main library.
        libraries = mesonlib.extract_as_list(kwargs, 'libraries')
        if mainlib:
            libraries = [mainlib] + libraries

        deps = DependenciesHelper(state, filebase)
        deps.add_pub_libs(libraries)
        deps.add_priv_libs(kwargs.get('libraries_private', []))
        deps.add_pub_reqs(kwargs.get('requires', []))
        deps.add_priv_reqs(kwargs.get('requires_private', []))
        deps.add_cflags(kwargs.get('extra_cflags', []))

        dversions = kwargs.get('d_module_versions', None)
        if dversions:
            compiler = state.environment.coredata.compilers.host.get('d')
            if compiler:
                deps.add_cflags(compiler.get_feature_args({'versions': dversions}, None))

        deps.remove_dups()

        def parse_variable_list(vardict):
            reserved = ['prefix', 'libdir', 'includedir']
            variables = []
            for name, value in vardict.items():
                if not dataonly and name in reserved:
                    raise mesonlib.MesonException(f'Variable "{name}" is reserved')
                variables.append((name, value))
            return variables

        variables = self.interpreter.extract_variables(kwargs, dict_new=True)
        variables = parse_variable_list(variables)
        unescaped_variables = self.interpreter.extract_variables(kwargs, argname='unescaped_variables')
        unescaped_variables = parse_variable_list(unescaped_variables)

        pcfile = filebase + '.pc'
        pkgroot = pkgroot_name = kwargs.get('install_dir', default_install_dir)
        if pkgroot is None:
            if mesonlib.is_freebsd():
                pkgroot = os.path.join(state.environment.coredata.get_option(mesonlib.OptionKey('prefix')), 'libdata', 'pkgconfig')
                pkgroot_name = os.path.join('{prefix}', 'libdata', 'pkgconfig')
            else:
                pkgroot = os.path.join(state.environment.coredata.get_option(mesonlib.OptionKey('libdir')), 'pkgconfig')
                pkgroot_name = os.path.join('{libdir}', 'pkgconfig')
        if not isinstance(pkgroot, str):
            raise mesonlib.MesonException('Install_dir must be a string.')
        self._generate_pkgconfig_file(state, deps, subdirs, name, description, url,
                                      version, pcfile, conflicts, variables,
                                      unescaped_variables, False, dataonly)
        res = build.Data([mesonlib.File(True, state.environment.get_scratch_dir(), pcfile)], pkgroot, pkgroot_name, None, state.subproject, install_tag='devel')
        variables = self.interpreter.extract_variables(kwargs, argname='uninstalled_variables', dict_new=True)
        variables = parse_variable_list(variables)
        unescaped_variables = self.interpreter.extract_variables(kwargs, argname='unescaped_uninstalled_variables')
        unescaped_variables = parse_variable_list(unescaped_variables)

        pcfile = filebase + '-uninstalled.pc'
        self._generate_pkgconfig_file(state, deps, subdirs, name, description, url,
                                      version, pcfile, conflicts, variables,
                                      unescaped_variables, uninstalled=True, dataonly=dataonly)
        # Associate the main library with this generated pc file. If the library
        # is used in any subsequent call to the generated, it will generate a
        # 'Requires:' or 'Requires.private:'.
        # Backward compatibility: We used to set 'generated_pc' on all public
        # libraries instead of just the main one. Keep doing that but warn if
        # anyone is relying on that deprecated behaviour.
        if mainlib:
            if not hasattr(mainlib, 'generated_pc'):
                mainlib.generated_pc = filebase
            else:
                mlog.warning('Already generated a pkg-config file for', mlog.bold(mainlib.name))
        else:
            for lib in deps.pub_libs:
                if not isinstance(lib, str) and not hasattr(lib, 'generated_pc'):
                    lib.generated_pc = filebase
                    location = state.current_node
                    lib.generated_pc_warn = [name, location]
        return ModuleReturnValue(res, [res])

def initialize(*args, **kwargs):
    return PkgConfigModule(*args, **kwargs)
