# Copyright 2013-2018 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This file contains the detection logic for external dependencies.
# Custom logic for several other packages are in separate files.

import copy
import functools
import os
import re
import stat
import json
import shlex
import shutil
import textwrap
import platform
import itertools
import ctypes
from enum import Enum
from pathlib import PurePath

from .. import mlog
from .. import mesonlib
from ..compilers import clib_langs
from ..environment import BinaryTable
from ..mesonlib import MachineChoice, MesonException, OrderedSet, PerMachine
from ..mesonlib import Popen_safe, version_compare_many, version_compare, listify

# These must be defined in this file to avoid cyclical references.
packages = {}
_packages_accept_language = set()


class DependencyException(MesonException):
    '''Exceptions raised while trying to find dependencies'''


class DependencyMethods(Enum):
    # Auto means to use whatever dependency checking mechanisms in whatever order meson thinks is best.
    AUTO = 'auto'
    PKGCONFIG = 'pkg-config'
    QMAKE = 'qmake'
    CMAKE = 'cmake'
    # Just specify the standard link arguments, assuming the operating system provides the library.
    SYSTEM = 'system'
    # This is only supported on OSX - search the frameworks directory by name.
    EXTRAFRAMEWORK = 'extraframework'
    # Detect using the sysconfig module.
    SYSCONFIG = 'sysconfig'
    # Specify using a "program"-config style tool
    CONFIG_TOOL = 'config-tool'
    # For backwards compatibility
    SDLCONFIG = 'sdlconfig'
    CUPSCONFIG = 'cups-config'
    PCAPCONFIG = 'pcap-config'
    LIBWMFCONFIG = 'libwmf-config'
    # Misc
    DUB = 'dub'


class Dependency:
    @classmethod
    def _process_method_kw(cls, kwargs):
        method = kwargs.get('method', 'auto')
        if method not in [e.value for e in DependencyMethods]:
            raise DependencyException('method {!r} is invalid'.format(method))
        method = DependencyMethods(method)

        # This sets per-tool config methods which are deprecated to to the new
        # generic CONFIG_TOOL value.
        if method in [DependencyMethods.SDLCONFIG, DependencyMethods.CUPSCONFIG,
                      DependencyMethods.PCAPCONFIG, DependencyMethods.LIBWMFCONFIG]:
            mlog.warning(textwrap.dedent("""\
                Configuration method {} has been deprecated in favor of
                'config-tool'. This will be removed in a future version of
                meson.""".format(method)))
            method = DependencyMethods.CONFIG_TOOL

        # Set the detection method. If the method is set to auto, use any available method.
        # If method is set to a specific string, allow only that detection method.
        if method == DependencyMethods.AUTO:
            methods = cls.get_methods()
        elif method in cls.get_methods():
            methods = [method]
        else:
            raise DependencyException(
                'Unsupported detection method: {}, allowed methods are {}'.format(
                    method.value,
                    mlog.format_list([x.value for x in [DependencyMethods.AUTO] + cls.get_methods()])))

        return methods

    def __init__(self, type_name, kwargs):
        self.name = "null"
        self.version = None
        self.language = None # None means C-like
        self.is_found = False
        self.type_name = type_name
        self.compile_args = []
        self.link_args = []
        # Raw -L and -l arguments without manual library searching
        # If None, self.link_args will be used
        self.raw_link_args = None
        self.sources = []
        self.methods = self._process_method_kw(kwargs)

    def __repr__(self):
        s = '<{0} {1}: {2}>'
        return s.format(self.__class__.__name__, self.name, self.is_found)

    def get_compile_args(self):
        return self.compile_args

    def get_link_args(self, raw=False):
        if raw and self.raw_link_args is not None:
            return self.raw_link_args
        return self.link_args

    def found(self):
        return self.is_found

    def get_sources(self):
        """Source files that need to be added to the target.
        As an example, gtest-all.cc when using GTest."""
        return self.sources

    @staticmethod
    def get_methods():
        return [DependencyMethods.AUTO]

    def get_name(self):
        return self.name

    def get_version(self):
        if self.version:
            return self.version
        else:
            return 'unknown'

    def get_exe_args(self, compiler):
        return []

    def need_openmp(self):
        return False

    def need_threads(self):
        return False

    def get_pkgconfig_variable(self, variable_name, kwargs):
        raise DependencyException('{!r} is not a pkgconfig dependency'.format(self.name))

    def get_configtool_variable(self, variable_name):
        raise DependencyException('{!r} is not a config-tool dependency'.format(self.name))

    def get_partial_dependency(self, *, compile_args=False, link_args=False,
                               links=False, includes=False, sources=False):
        """Create a new dependency that contains part of the parent dependency.

        The following options can be inherited:
            links -- all link_with arguemnts
            includes -- all include_directory and -I/-isystem calls
            sources -- any source, header, or generated sources
            compile_args -- any compile args
            link_args -- any link args

        Additionally the new dependency will have the version parameter of it's
        parent (if any) and the requested values of any dependencies will be
        added as well.
        """
        raise RuntimeError('Unreachable code in partial_dependency called')


class InternalDependency(Dependency):
    def __init__(self, version, incdirs, compile_args, link_args, libraries, whole_libraries, sources, ext_deps):
        super().__init__('internal', {})
        self.version = version
        self.is_found = True
        self.include_directories = incdirs
        self.compile_args = compile_args
        self.link_args = link_args
        self.libraries = libraries
        self.whole_libraries = whole_libraries
        self.sources = sources
        self.ext_deps = ext_deps

    def get_pkgconfig_variable(self, variable_name, kwargs):
        raise DependencyException('Method "get_pkgconfig_variable()" is '
                                  'invalid for an internal dependency')

    def get_configtool_variable(self, variable_name):
        raise DependencyException('Method "get_configtool_variable()" is '
                                  'invalid for an internal dependency')

    def get_partial_dependency(self, *, compile_args=False, link_args=False,
                               links=False, includes=False, sources=False):
        compile_args = self.compile_args.copy() if compile_args else []
        link_args = self.link_args.copy() if link_args else []
        libraries = self.libraries.copy() if links else []
        whole_libraries = self.whole_libraries.copy() if links else []
        sources = self.sources.copy() if sources else []
        includes = self.include_directories.copy() if includes else []
        deps = [d.get_partial_dependency(
            compile_args=compile_args, link_args=link_args, links=links,
            includes=includes, sources=sources) for d in self.ext_deps]
        return InternalDependency(
            self.version, includes, compile_args, link_args, libraries,
            whole_libraries, sources, deps)


class ExternalDependency(Dependency):
    def __init__(self, type_name, environment, language, kwargs):
        super().__init__(type_name, kwargs)
        self.env = environment
        self.name = type_name # default
        self.is_found = False
        self.language = language
        self.version_reqs = kwargs.get('version', None)
        if isinstance(self.version_reqs, str):
            self.version_reqs = [self.version_reqs]
        self.required = kwargs.get('required', True)
        self.silent = kwargs.get('silent', False)
        self.static = kwargs.get('static', False)
        if not isinstance(self.static, bool):
            raise DependencyException('Static keyword must be boolean')
        # Is this dependency for cross-compilation?
        if 'native' in kwargs and self.env.is_cross_build():
            self.want_cross = not kwargs['native']
        else:
            self.want_cross = self.env.is_cross_build()
        self.clib_compiler = None
        # Set the compiler that will be used by this dependency
        # This is only used for configuration checks
        if self.want_cross:
            compilers = self.env.coredata.cross_compilers
        else:
            compilers = self.env.coredata.compilers
        # Set the compiler for this dependency if a language is specified,
        # else try to pick something that looks usable.
        if self.language:
            if self.language not in compilers:
                m = self.name.capitalize() + ' requires a {0} compiler, but ' \
                    '{0} is not in the list of project languages'
                raise DependencyException(m.format(self.language.capitalize()))
            self.clib_compiler = compilers[self.language]
        else:
            # Try to find a compiler that can find C libraries for
            # running compiler.find_library()
            for lang in clib_langs:
                self.clib_compiler = compilers.get(lang, None)
                if self.clib_compiler:
                    break

    def get_compiler(self):
        return self.clib_compiler

    def get_partial_dependency(self, *, compile_args=False, link_args=False,
                               links=False, includes=False, sources=False):
        new = copy.copy(self)
        if not compile_args:
            new.compile_args = []
        if not link_args:
            new.link_args = []
        if not sources:
            new.sources = []

        return new

    def log_details(self):
        return ''

    def log_info(self):
        return ''

    def log_tried(self):
        return ''

    # Check if dependency version meets the requirements
    def _check_version(self):
        if not self.is_found:
            return

        if self.version_reqs:
            # an unknown version can never satisfy any requirement
            if not self.version:
                found_msg = ['Dependency', mlog.bold(self.name), 'found:']
                found_msg += [mlog.red('NO'), 'unknown version, but need:',
                              self.version_reqs]
                mlog.log(*found_msg)

                if self.required:
                    m = 'Unknown version of dependency {!r}, but need {!r}.'
                    raise DependencyException(m.format(self.name, self.version_reqs))

            else:
                (self.is_found, not_found, found) = \
                    version_compare_many(self.version, self.version_reqs)
                if not self.is_found:
                    found_msg = ['Dependency', mlog.bold(self.name), 'found:']
                    found_msg += [mlog.red('NO'),
                                  'found {!r} but need:'.format(self.version),
                                  ', '.join(["'{}'".format(e) for e in not_found])]
                    if found:
                        found_msg += ['; matched:',
                                      ', '.join(["'{}'".format(e) for e in found])]
                    mlog.log(*found_msg)

                    if self.required:
                        m = 'Invalid version of dependency, need {!r} {!r} found {!r}.'
                        raise DependencyException(m.format(self.name, not_found, self.version))
                    return


class NotFoundDependency(Dependency):
    def __init__(self, environment):
        super().__init__('not-found', {})
        self.env = environment
        self.name = 'not-found'
        self.is_found = False

    def get_partial_dependency(self, *, compile_args=False, link_args=False,
                               links=False, includes=False, sources=False):
        return copy.copy(self)


class ConfigToolDependency(ExternalDependency):

    """Class representing dependencies found using a config tool."""

    tools = None
    tool_name = None
    __strip_version = re.compile(r'^[0-9.]*')

    def __init__(self, name, environment, language, kwargs):
        super().__init__('config-tool', environment, language, kwargs)
        self.name = name
        self.native = kwargs.get('native', False)
        self.tools = listify(kwargs.get('tools', self.tools))

        req_version = kwargs.get('version', None)
        tool, version = self.find_config(req_version)
        self.config = tool
        self.is_found = self.report_config(version, req_version)
        if not self.is_found:
            self.config = None
            return
        self.version = version
        if getattr(self, 'finish_init', None):
            self.finish_init(self)

    def _sanitize_version(self, version):
        """Remove any non-numeric, non-point version suffixes."""
        m = self.__strip_version.match(version)
        if m:
            # Ensure that there isn't a trailing '.', such as an input like
            # `1.2.3.git-1234`
            return m.group(0).rstrip('.')
        return version

    @classmethod
    def factory(cls, name, environment, language, kwargs, tools, tool_name, finish_init=None):
        """Constructor for use in dependencies that can be found multiple ways.

        In addition to the standard constructor values, this constructor sets
        the tool_name and tools values of the instance.
        """
        # This deserves some explanation, because metaprogramming is hard.
        # This uses type() to create a dynamic subclass of ConfigToolDependency
        # with the tools and tool_name class attributes set, this class is then
        # instantiated and returned. The reduce function (method) is also
        # attached, since python's pickle module won't be able to do anything
        # with this dynamically generated class otherwise.
        def reduce(self):
            return (cls._unpickle, (), self.__dict__)
        sub = type('{}Dependency'.format(name.capitalize()), (cls, ),
                   {'tools': tools, 'tool_name': tool_name, '__reduce__': reduce, 'finish_init': staticmethod(finish_init)})

        return sub(name, environment, language, kwargs)

    @classmethod
    def _unpickle(cls):
        return cls.__new__(cls)

    def find_config(self, versions=None):
        """Helper method that searchs for config tool binaries in PATH and
        returns the one that best matches the given version requirements.
        """
        if not isinstance(versions, list) and versions is not None:
            versions = listify(versions)

        for_machine = MachineChoice.BUILD if self.native else MachineChoice.HOST
        tool = self.env.binaries[for_machine].lookup_entry(self.tool_name)
        if tool is not None:
            tools = [tool]
        else:
            if self.env.is_cross_build() and not self.native:
                mlog.warning('No entry for {0} specified in your cross file. '
                             'Falling back to searching PATH. This may find a '
                             'native version of {0}!'.format(self.tool_name))
            tools = [[t] for t in self.tools]

        best_match = (None, None)
        for tool in tools:
            try:
                p, out = Popen_safe(tool + ['--version'])[:2]
            except (FileNotFoundError, PermissionError):
                continue
            if p.returncode != 0:
                continue

            out = self._sanitize_version(out.strip())
            # Some tools, like pcap-config don't supply a version, but also
            # don't fail with --version, in that case just assume that there is
            # only one version and return it.
            if not out:
                return (tool, None)
            if versions:
                is_found = version_compare_many(out, versions)[0]
                # This allows returning a found version without a config tool,
                # which is useful to inform the user that you found version x,
                # but y was required.
                if not is_found:
                    tool = None
            if best_match[1]:
                if version_compare(out, '> {}'.format(best_match[1])):
                    best_match = (tool, out)
            else:
                best_match = (tool, out)

        return best_match

    def report_config(self, version, req_version):
        """Helper method to print messages about the tool."""

        found_msg = [mlog.bold(self.tool_name), 'found:']

        if self.config is None:
            found_msg.append(mlog.red('NO'))
            if version is not None and req_version is not None:
                found_msg.append('found {!r} but need {!r}'.format(version, req_version))
            elif req_version:
                found_msg.append('need {!r}'.format(req_version))
        else:
            found_msg += [mlog.green('YES'), '({})'.format(shutil.which(self.config[0])), version]

        mlog.log(*found_msg)

        return self.config is not None

    def get_config_value(self, args, stage):
        p, out, err = Popen_safe(self.config + args)
        # This is required to keep shlex from stripping path separators on
        # Windows. Also, don't put escape sequences in config values, okay?
        out = out.replace('\\', '\\\\')
        if p.returncode != 0:
            if self.required:
                raise DependencyException(
                    'Could not generate {} for {}.\n{}'.format(
                        stage, self.name, err))
            return []
        return shlex.split(out)

    @staticmethod
    def get_methods():
        return [DependencyMethods.AUTO, DependencyMethods.CONFIG_TOOL]

    def get_configtool_variable(self, variable_name):
        p, out, _ = Popen_safe(self.config + ['--{}'.format(variable_name)])
        if p.returncode != 0:
            if self.required:
                raise DependencyException(
                    'Could not get variable "{}" for dependency {}'.format(
                        variable_name, self.name))
        variable = out.strip()
        mlog.debug('Got config-tool variable {} : {}'.format(variable_name, variable))
        return variable

    def log_tried(self):
        return self.type_name


class PkgConfigDependency(ExternalDependency):
    # The class's copy of the pkg-config path. Avoids having to search for it
    # multiple times in the same Meson invocation.
    class_pkgbin = PerMachine(None, None, None)
    # We cache all pkg-config subprocess invocations to avoid redundant calls
    pkgbin_cache = {}

    def __init__(self, name, environment, kwargs, language=None):
        super().__init__('pkgconfig', environment, language, kwargs)
        self.name = name
        self.is_libtool = False
        # Store a copy of the pkg-config path on the object itself so it is
        # stored in the pickled coredata and recovered.
        self.pkgbin = None

        if not self.want_cross and environment.is_cross_build():
            for_machine = MachineChoice.BUILD
        else:
            for_machine = MachineChoice.HOST

        # Create an iterator of options
        def search():
            # Lookup in cross or machine file.
            potential_pkgpath = environment.binaries[for_machine].lookup_entry('pkgconfig')
            if potential_pkgpath is not None:
                mlog.debug('Pkg-config binary for {} specified from cross file, native file, '
                           'or env var as {}'.format(for_machine, potential_pkgpath))
                yield ExternalProgram.from_entry('pkgconfig', potential_pkgpath)
                # We never fallback if the user-specified option is no good, so
                # stop returning options.
                return
            mlog.debug('Pkg-config binary missing from cross or native file, or env var undefined.')
            # Fallback on hard-coded defaults.
            # TODO prefix this for the cross case instead of ignoring thing.
            if environment.machines.matches_build_machine(for_machine):
                for potential_pkgpath in environment.default_pkgconfig:
                    mlog.debug('Trying a default pkg-config fallback at', potential_pkgpath)
                    yield ExternalProgram(potential_pkgpath, silent=True)

        # Only search for pkg-config for each machine the first time and store
        # the result in the class definition
        if PkgConfigDependency.class_pkgbin[for_machine] is False:
            mlog.debug('Pkg-config binary for %s is cached missing.' % for_machine)
        elif PkgConfigDependency.class_pkgbin[for_machine] is not None:
            mlog.debug('Pkg-config binary for %s is cached.' % for_machine)
        else:
            assert PkgConfigDependency.class_pkgbin[for_machine] is None
            mlog.debug('Pkg-config binary for %s is not cached.' % for_machine)
            for potential_pkgbin in search():
                mlog.debug('Trying pkg-config binary {} for machine {} at {}'
                           .format(potential_pkgbin.name, for_machine, potential_pkgbin.command))
                version_if_ok = self.check_pkgconfig(potential_pkgbin)
                if not version_if_ok:
                    continue
                if not self.silent:
                    mlog.log('Found pkg-config:', mlog.bold(potential_pkgbin.get_path()),
                             '(%s)' % version_if_ok)
                PkgConfigDependency.class_pkgbin[for_machine] = potential_pkgbin
                break
            else:
                if not self.silent:
                    mlog.log('Found Pkg-config:', mlog.red('NO'))
                # Set to False instead of None to signify that we've already
                # searched for it and not found it
                PkgConfigDependency.class_pkgbin[for_machine] = False

        self.pkgbin = PkgConfigDependency.class_pkgbin[for_machine]
        if self.pkgbin is False:
            self.pkgbin = None
            msg = 'No pkg-config binary for machine %s not found. Giving up.' % for_machine
            if self.required:
                raise DependencyException(msg)
            else:
                mlog.debug(msg)

        mlog.debug('Determining dependency {!r} with pkg-config executable '
                   '{!r}'.format(name, self.pkgbin.get_path()))
        ret, self.version = self._call_pkgbin(['--modversion', name])
        if ret != 0:
            return

        try:
            # Fetch cargs to be used while using this dependency
            self._set_cargs()
            # Fetch the libraries and library paths needed for using this
            self._set_libs()
        except DependencyException as e:
            if self.required:
                raise
            else:
                self.compile_args = []
                self.link_args = []
                self.is_found = False
                self.reason = e

        self.is_found = True

    def __repr__(self):
        s = '<{0} {1}: {2} {3}>'
        return s.format(self.__class__.__name__, self.name, self.is_found,
                        self.version_reqs)

    def _call_pkgbin_real(self, args, env):
        cmd = self.pkgbin.get_command() + args
        p, out = Popen_safe(cmd, env=env)[0:2]
        rc, out = p.returncode, out.strip()
        call = ' '.join(cmd)
        mlog.debug("Called `{}` -> {}\n{}".format(call, rc, out))
        return rc, out

    def _call_pkgbin(self, args, env=None):
        if env is None:
            fenv = env
            env = os.environ
        else:
            fenv = frozenset(env.items())
        targs = tuple(args)
        cache = PkgConfigDependency.pkgbin_cache
        if (self.pkgbin, targs, fenv) not in cache:
            cache[(self.pkgbin, targs, fenv)] = self._call_pkgbin_real(args, env)
        return cache[(self.pkgbin, targs, fenv)]

    def _convert_mingw_paths(self, args):
        '''
        Both MSVC and native Python on Windows cannot handle MinGW-esque /c/foo
        paths so convert them to C:/foo. We cannot resolve other paths starting
        with / like /home/foo so leave them as-is so that the user gets an
        error/warning from the compiler/linker.
        '''
        if not mesonlib.is_windows():
            return args
        converted = []
        for arg in args:
            pargs = []
            # Library search path
            if arg.startswith('-L/'):
                pargs = PurePath(arg[2:]).parts
                tmpl = '-L{}:/{}'
            elif arg.startswith('-I/'):
                pargs = PurePath(arg[2:]).parts
                tmpl = '-I{}:/{}'
            # Full path to library or .la file
            elif arg.startswith('/'):
                pargs = PurePath(arg).parts
                tmpl = '{}:/{}'
            if len(pargs) > 1 and len(pargs[1]) == 1:
                arg = tmpl.format(pargs[1], '/'.join(pargs[2:]))
            converted.append(arg)
        return converted

    def _set_cargs(self):
        env = None
        if self.language == 'fortran':
            # gfortran doesn't appear to look in system paths for INCLUDE files,
            # so don't allow pkg-config to suppress -I flags for system paths
            env = os.environ.copy()
            env['PKG_CONFIG_ALLOW_SYSTEM_CFLAGS'] = '1'
        ret, out = self._call_pkgbin(['--cflags', self.name], env=env)
        if ret != 0:
            raise DependencyException('Could not generate cargs for %s:\n\n%s' %
                                      (self.name, out))
        self.compile_args = self._convert_mingw_paths(shlex.split(out))

    def _search_libs(self, out, out_raw):
        '''
        @out: PKG_CONFIG_ALLOW_SYSTEM_LIBS=1 pkg-config --libs
        @out_raw: pkg-config --libs

        We always look for the file ourselves instead of depending on the
        compiler to find it with -lfoo or foo.lib (if possible) because:
        1. We want to be able to select static or shared
        2. We need the full path of the library to calculate RPATH values
        3. De-dup of libraries is easier when we have absolute paths

        Libraries that are provided by the toolchain or are not found by
        find_library() will be added with -L -l pairs.
        '''
        # Library paths should be safe to de-dup
        #
        # First, figure out what library paths to use. Originally, we were
        # doing this as part of the loop, but due to differences in the order
        # of -L values between pkg-config and pkgconf, we need to do that as
        # a separate step. See:
        # https://github.com/mesonbuild/meson/issues/3951
        # https://github.com/mesonbuild/meson/issues/4023
        #
        # Separate system and prefix paths, and ensure that prefix paths are
        # always searched first.
        prefix_libpaths = OrderedSet()
        # We also store this raw_link_args on the object later
        raw_link_args = self._convert_mingw_paths(shlex.split(out_raw))
        for arg in raw_link_args:
            if arg.startswith('-L') and not arg.startswith(('-L-l', '-L-L')):
                prefix_libpaths.add(arg[2:])
        system_libpaths = OrderedSet()
        full_args = self._convert_mingw_paths(shlex.split(out))
        for arg in full_args:
            if arg.startswith(('-L-l', '-L-L')):
                # These are D language arguments, not library paths
                continue
            if arg.startswith('-L') and arg[2:] not in prefix_libpaths:
                system_libpaths.add(arg[2:])
        # Use this re-ordered path list for library resolution
        libpaths = list(prefix_libpaths) + list(system_libpaths)
        # Track -lfoo libraries to avoid duplicate work
        libs_found = OrderedSet()
        # Track not-found libraries to know whether to add library paths
        libs_notfound = []
        libtype = 'static' if self.static else 'default'
        # Generate link arguments for this library
        link_args = []
        for lib in full_args:
            if lib.startswith(('-L-l', '-L-L')):
                # These are D language arguments, add them as-is
                pass
            elif lib.startswith('-L'):
                # We already handled library paths above
                continue
            elif lib.startswith('-l'):
                # Don't resolve the same -lfoo argument again
                if lib in libs_found:
                    continue
                if self.clib_compiler:
                    args = self.clib_compiler.find_library(lib[2:], self.env,
                                                           libpaths, libtype)
                # If the project only uses a non-clib language such as D, Rust,
                # C#, Python, etc, all we can do is limp along by adding the
                # arguments as-is and then adding the libpaths at the end.
                else:
                    args = None
                if args is not None:
                    libs_found.add(lib)
                    # Replace -l arg with full path to library if available
                    # else, library is either to be ignored, or is provided by
                    # the compiler, can't be resolved, and should be used as-is
                    if args:
                        if not args[0].startswith('-l'):
                            lib = args[0]
                    else:
                        continue
                else:
                    # Library wasn't found, maybe we're looking in the wrong
                    # places or the library will be provided with LDFLAGS or
                    # LIBRARY_PATH from the environment (on macOS), and many
                    # other edge cases that we can't account for.
                    #
                    # Add all -L paths and use it as -lfoo
                    if lib in libs_notfound:
                        continue
                    if self.static:
                        mlog.warning('Static library {!r} not found for dependency {!r}, may '
                                     'not be statically linked'.format(lib[2:], self.name))
                    libs_notfound.append(lib)
            elif lib.endswith(".la"):
                shared_libname = self.extract_libtool_shlib(lib)
                shared_lib = os.path.join(os.path.dirname(lib), shared_libname)
                if not os.path.exists(shared_lib):
                    shared_lib = os.path.join(os.path.dirname(lib), ".libs", shared_libname)

                if not os.path.exists(shared_lib):
                    raise DependencyException('Got a libtools specific "%s" dependencies'
                                              'but we could not compute the actual shared'
                                              'library path' % lib)
                self.is_libtool = True
                lib = shared_lib
                if lib in link_args:
                    continue
            link_args.append(lib)
        # Add all -Lbar args if we have -lfoo args in link_args
        if libs_notfound:
            # Order of -L flags doesn't matter with ld, but it might with other
            # linkers such as MSVC, so prepend them.
            link_args = ['-L' + lp for lp in prefix_libpaths] + link_args
        return link_args, raw_link_args

    def _set_libs(self):
        env = None
        libcmd = [self.name, '--libs']
        if self.static:
            libcmd.append('--static')
        # Force pkg-config to output -L fields even if they are system
        # paths so we can do manual searching with cc.find_library() later.
        env = os.environ.copy()
        env['PKG_CONFIG_ALLOW_SYSTEM_LIBS'] = '1'
        ret, out = self._call_pkgbin(libcmd, env=env)
        if ret != 0:
            raise DependencyException('Could not generate libs for %s:\n\n%s' %
                                      (self.name, out))
        # Also get the 'raw' output without -Lfoo system paths for adding -L
        # args with -lfoo when a library can't be found, and also in
        # gnome.generate_gir + gnome.gtkdoc which need -L -l arguments.
        ret, out_raw = self._call_pkgbin(libcmd)
        if ret != 0:
            raise DependencyException('Could not generate libs for %s:\n\n%s' %
                                      (self.name, out_raw))
        self.link_args, self.raw_link_args = self._search_libs(out, out_raw)

    def get_pkgconfig_variable(self, variable_name, kwargs):
        options = ['--variable=' + variable_name, self.name]

        if 'define_variable' in kwargs:
            definition = kwargs.get('define_variable', [])
            if not isinstance(definition, list):
                raise MesonException('define_variable takes a list')

            if len(definition) != 2 or not all(isinstance(i, str) for i in definition):
                raise MesonException('define_variable must be made up of 2 strings for VARIABLENAME and VARIABLEVALUE')

            options = ['--define-variable=' + '='.join(definition)] + options

        ret, out = self._call_pkgbin(options)
        variable = ''
        if ret != 0:
            if self.required:
                raise DependencyException('dependency %s not found.' %
                                          (self.name))
        else:
            variable = out.strip()

            # pkg-config doesn't distinguish between empty and non-existent variables
            # use the variable list to check for variable existence
            if not variable:
                ret, out = self._call_pkgbin(['--print-variables', self.name])
                if not re.search(r'^' + variable_name + r'$', out, re.MULTILINE):
                    if 'default' in kwargs:
                        variable = kwargs['default']
                    else:
                        mlog.warning("pkgconfig variable '%s' not defined for dependency %s." % (variable_name, self.name))

        mlog.debug('Got pkgconfig variable %s : %s' % (variable_name, variable))
        return variable

    @staticmethod
    def get_methods():
        return [DependencyMethods.PKGCONFIG]

    def check_pkgconfig(self, pkgbin):
        if not pkgbin.found():
            mlog.log('Did not find pkg-config by name {!r}'.format(pkgbin.name))
            return None
        try:
            p, out = Popen_safe(pkgbin.get_command() + ['--version'])[0:2]
            if p.returncode != 0:
                mlog.warning('Found pkg-config {!r} but it failed when run'
                             ''.format(' '.join(pkgbin.get_command())))
                return None
        except FileNotFoundError:
            mlog.warning('We thought we found pkg-config {!r} but now it\'s not there. How odd!'
                         ''.format(' '.join(pkgbin.get_command())))
            return None
        except PermissionError:
            msg = 'Found pkg-config {!r} but didn\'t have permissions to run it.'.format(' '.join(pkgbin.get_command()))
            if not mesonlib.is_windows():
                msg += '\n\nOn Unix-like systems this is often caused by scripts that are not executable.'
            mlog.warning(msg)
            return None
        return out.strip()

    def extract_field(self, la_file, fieldname):
        with open(la_file) as f:
            for line in f:
                arr = line.strip().split('=')
                if arr[0] == fieldname:
                    return arr[1][1:-1]
        return None

    def extract_dlname_field(self, la_file):
        return self.extract_field(la_file, 'dlname')

    def extract_libdir_field(self, la_file):
        return self.extract_field(la_file, 'libdir')

    def extract_libtool_shlib(self, la_file):
        '''
        Returns the path to the shared library
        corresponding to this .la file
        '''
        dlname = self.extract_dlname_field(la_file)
        if dlname is None:
            return None

        # Darwin uses absolute paths where possible; since the libtool files never
        # contain absolute paths, use the libdir field
        if mesonlib.is_osx():
            dlbasename = os.path.basename(dlname)
            libdir = self.extract_libdir_field(la_file)
            if libdir is None:
                return dlbasename
            return os.path.join(libdir, dlbasename)
        # From the comments in extract_libtool(), older libtools had
        # a path rather than the raw dlname
        return os.path.basename(dlname)

    def log_tried(self):
        return self.type_name

class CMakeTraceLine:
    def __init__(self, file, line, func, args):
        self.file = file
        self.line = line
        self.func = func.lower()
        self.args = args

    def __repr__(self):
        s = 'CMake TRACE: {0}:{1} {2}({3})'
        return s.format(self.file, self.line, self.func, self.args)

class CMakeTarget:
    def __init__(self, name, type, properies = {}):
        self.name = name
        self.type = type
        self.properies = properies

    def __repr__(self):
        s = 'CMake TARGET:\n  -- name:      {}\n  -- type:      {}\n  -- properies: {{\n{}     }}'
        propSTR = ''
        for i in self.properies:
            propSTR += "      '{}': {}\n".format(i, self.properies[i])
        return s.format(self.name, self.type, propSTR)

class CMakeDependency(ExternalDependency):
    # The class's copy of the CMake path. Avoids having to search for it
    # multiple times in the same Meson invocation.
    class_cmakebin = PerMachine(None, None, None)
    class_cmakevers = PerMachine(None, None, None)
    # We cache all pkg-config subprocess invocations to avoid redundant calls
    cmake_cache = {}
    # Version string for the minimum CMake version
    class_cmake_version = '>=3.4'
    # CMake generators to try (empty for no generator)
    class_cmake_generators = ['', 'Ninja', 'Unix Makefiles', 'Visual Studio 10 2010']

    def _gen_exception(self, msg):
        return DependencyException('Dependency {} not found: {}'.format(self.name, msg))

    def __init__(self, name, environment, kwargs, language=None):
        super().__init__('cmake', environment, language, kwargs)
        self.name = name
        self.is_libtool = False
        # Store a copy of the CMake path on the object itself so it is
        # stored in the pickled coredata and recovered.
        self.cmakebin = None
        self.cmakevers = None

        # Dict of CMake variables: '<var_name>': ['list', 'of', 'values']
        self.vars = {}

        # Dict of CMakeTarget
        self.targets = {}

        # Where all CMake "build dirs" are located
        self.cmake_root_dir = environment.scratch_dir

        # When finding dependencies for cross-compiling, we don't care about
        # the 'native' CMake binary
        # TODO: Test if this works as expected
        if environment.is_cross_build() and not self.want_cross:
            for_machine = MachineChoice.BUILD
        else:
            for_machine = MachineChoice.HOST

        # Create an iterator of options
        def search():
            # Lookup in cross or machine file.
            potential_cmakepath = environment.binaries[for_machine].lookup_entry('cmake')
            if potential_cmakepath is not None:
                mlog.debug('CMake binary for %s specified from cross file, native file, or env var as %s.', for_machine, potential_cmakepath)
                yield ExternalProgram.from_entry('cmake', potential_cmakepath)
                # We never fallback if the user-specified option is no good, so
                # stop returning options.
                return
            mlog.debug('CMake binary missing from cross or native file, or env var undefined.')
            # Fallback on hard-coded defaults.
            # TODO prefix this for the cross case instead of ignoring thing.
            if environment.machines.matches_build_machine(for_machine):
                for potential_cmakepath in environment.default_cmake:
                    mlog.debug('Trying a default CMake fallback at', potential_cmakepath)
                    yield ExternalProgram(potential_cmakepath, silent=True)

        # Only search for CMake the first time and store the result in the class
        # definition
        if CMakeDependency.class_cmakebin[for_machine] is False:
            mlog.debug('CMake binary for %s is cached missing.' % for_machine)
        elif CMakeDependency.class_cmakebin[for_machine] is not None:
            mlog.debug('CMake binary for %s is cached.' % for_machine)
        else:
            assert CMakeDependency.class_cmakebin[for_machine] is None
            mlog.debug('CMake binary for %s is not cached.', for_machine)
            for potential_cmakebin in search():
                mlog.debug(
                    'Trying CMake binary %s for machine %s at %s.',
                    potential_cmakebin.name, for_machine, potential_cmakebin.command)
                version_if_ok = self.check_cmake(potential_cmakebin)
                if not version_if_ok:
                    continue
                if not self.silent:
                    mlog.log('Found CMake:', mlog.bold(potential_cmakebin.get_path()),
                             '(%s)' % version_if_ok)
                CMakeDependency.class_cmakebin[for_machine] = potential_cmakebin
                CMakeDependency.class_cmakevers[for_machine] = version_if_ok
                break
            else:
                if not self.silent:
                    mlog.log('Found CMake:', mlog.red('NO'))
                # Set to False instead of None to signify that we've already
                # searched for it and not found it
                CMakeDependency.class_cmakebin[for_machine] = False
                CMakeDependency.class_cmakevers[for_machine] = None

        self.cmakebin = CMakeDependency.class_cmakebin[for_machine]
        self.cmakevers = CMakeDependency.class_cmakevers[for_machine]
        if self.cmakebin is False:
            self.cmakebin = None
            msg = 'No CMake binary for machine %s not found. Giving up.' % for_machine
            if self.required:
                raise DependencyException(msg)
            mlog.debug(msg)

        modules = kwargs.get('modules', [])
        if not isinstance(modules, list):
            modules = [modules]
        self._detect_dep(name, modules)

    def __repr__(self):
        s = '<{0} {1}: {2} {3}>'
        return s.format(self.__class__.__name__, self.name, self.is_found,
                        self.version_reqs)

    def _detect_dep(self, name, modules):
        # Detect a dependency with CMake using the '--find-package' mode
        # and the trace output (stderr)
        #
        # When the trace output is enabled CMake prints all functions with
        # parameters to stderr as they are executed. Since CMake 3.4.0
        # variables ("${VAR}") are also replaced in the trace output.
        mlog.debug('\nDetermining dependency {!r} with CMake executable '
                   '{!r}'.format(name, self.cmakebin.get_path()))

        # Try different CMake generators since specifying no generator may fail
        # in cygwin for some reason
        for i in CMakeDependency.class_cmake_generators:
            mlog.debug('Try CMake generator: {}'.format(i if len(i) > 0 else 'auto'))

            # Prepare options
            cmake_opts = ['--trace-expand', '-DNAME={}'.format(name), '.']
            if len(i) > 0:
                cmake_opts = ['-G', i] + cmake_opts

            # Run CMake
            ret1, out1, err1 = self._call_cmake(cmake_opts)

            # Current generator was successful
            if ret1 == 0:
                break

            mlog.debug('CMake failed for generator {} and package {} with error code {}'.format(i, name, ret1))
            mlog.debug('OUT:\n{}\n\n\nERR:\n{}\n\n'.format(out1, err1))

        # Check if any generator succeeded
        if ret1 != 0:
            return

        try:
            # First parse the trace
            lexer1 = self._lex_trace(err1)

            # All supported functions
            functions = {
                'set': self._cmake_set,
                'unset': self._cmake_unset,
                'add_executable': self._cmake_add_executable,
                'add_library': self._cmake_add_library,
                'add_custom_target': self._cmake_add_custom_target,
                'set_property': self._cmake_set_property,
                'set_target_properties': self._cmake_set_target_properties
            }

            # Primary pass -- parse everything
            for l in lexer1:
                # "Execute" the CMake function if supported
                fn = functions.get(l.func, None)
                if(fn):
                    fn(l)

        except DependencyException as e:
            if self.required:
                raise
            else:
                self.compile_args = []
                self.link_args = []
                self.is_found = False
                self.reason = e
                return

        # Whether the package is found or not is always stored in PACKAGE_FOUND
        self.is_found = self._var_to_bool('PACKAGE_FOUND')
        if not self.is_found:
            return

        # Try to detect the version
        vers_raw = self.get_first_cmake_var_of(['PACKAGE_VERSION'])

        if len(vers_raw) > 0:
            self.version = vers_raw[0]
            self.version.strip('"\' ')

        # Try guessing a CMake target if none is provided
        if len(modules) == 0:
            for i in self.targets:
                tg = i.lower()
                lname = name.lower()
                if '{}::{}'.format(lname, lname) == tg or lname == tg.replace('::', ''):
                    mlog.debug('Guessed CMake target \'{}\''.format(i))
                    modules = [i]
                    break

        # Failed to guess a target --> try the old-style method
        if len(modules) == 0:
            incDirs = self.get_first_cmake_var_of(['PACKAGE_INCLUDE_DIRS'])
            libs = self.get_first_cmake_var_of(['PACKAGE_LIBRARIES'])

            # Try to use old style variables if no module is specified
            if len(libs) > 0:
                self.compile_args = list(map(lambda x: '-I{}'.format(x), incDirs))
                self.link_args = libs
                mlog.debug('using old-style CMake variables for dependency {}'.format(name))
                return

            # Even the old-style approach failed. Nothing else we can do here
            self.is_found = False
            raise self._gen_exception('CMake: failed to guess a CMake target for {}.\n'
                                      'Try to explicitly specify one or more targets with the "modules" property.\n'
                                      'Valid targets are:\n{}'.format(name, list(self.targets.keys())))

        # Set dependencies with CMake targets
        processed_targets = []
        incDirs = []
        compileDefinitions = []
        compileOptions = []
        libraries = []
        for i in modules:
            if i not in self.targets:
                raise self._gen_exception('CMake: invalid CMake target {} for {}.\n'
                                          'Try to explicitly specify one or more targets with the "modules" property.\n'
                                          'Valid targets are:\n{}'.format(i, name, list(self.targets.keys())))

            targets = [i]
            while len(targets) > 0:
                curr = targets.pop(0)

                # Skip already processed targets
                if curr in processed_targets:
                    continue

                tgt = self.targets[curr]
                cfgs = []
                cfg = ''
                otherDeps = []
                mlog.debug(tgt)

                if 'INTERFACE_INCLUDE_DIRECTORIES' in tgt.properies:
                    incDirs += tgt.properies['INTERFACE_INCLUDE_DIRECTORIES']

                if 'INTERFACE_COMPILE_DEFINITIONS' in tgt.properies:
                    tempDefs = list(tgt.properies['INTERFACE_COMPILE_DEFINITIONS'])
                    tempDefs = list(map(lambda x: '-D{}'.format(re.sub('^-D', '', x)), tempDefs))
                    compileDefinitions += tempDefs

                if 'INTERFACE_COMPILE_OPTIONS' in tgt.properies:
                    compileOptions += tgt.properies['INTERFACE_COMPILE_OPTIONS']

                if 'IMPORTED_CONFIGURATIONS' in tgt.properies:
                    cfgs = tgt.properies['IMPORTED_CONFIGURATIONS']
                    cfg = cfgs[0]

                if 'RELEASE' in cfgs:
                    cfg = 'RELEASE'

                if 'IMPORTED_LOCATION_{}'.format(cfg) in tgt.properies:
                    libraries += tgt.properies['IMPORTED_LOCATION_{}'.format(cfg)]
                elif 'IMPORTED_LOCATION' in tgt.properies:
                    libraries += tgt.properies['IMPORTED_LOCATION']

                if 'INTERFACE_LINK_LIBRARIES' in tgt.properies:
                    otherDeps += tgt.properies['INTERFACE_LINK_LIBRARIES']

                if 'IMPORTED_LINK_DEPENDENT_LIBRARIES_{}'.format(cfg) in tgt.properies:
                    otherDeps += tgt.properies['IMPORTED_LINK_DEPENDENT_LIBRARIES_{}'.format(cfg)]
                elif 'IMPORTED_LINK_DEPENDENT_LIBRARIES' in tgt.properies:
                    otherDeps += tgt.properies['IMPORTED_LINK_DEPENDENT_LIBRARIES']

                for j in otherDeps:
                    if j in self.targets:
                        targets += [j]

                processed_targets += [curr]

        # Make sure all elements in the lists are unique and sorted
        incDirs = list(sorted(list(set(incDirs))))
        compileDefinitions = list(sorted(list(set(compileDefinitions))))
        compileOptions = list(sorted(list(set(compileOptions))))
        libraries = list(sorted(list(set(libraries))))

        mlog.debug('Include Dirs:         {}'.format(incDirs))
        mlog.debug('Compiler Definitions: {}'.format(compileDefinitions))
        mlog.debug('Compiler Options:     {}'.format(compileOptions))
        mlog.debug('Libraries:            {}'.format(libraries))

        self.compile_args = compileOptions + compileDefinitions + list(map(lambda x: '-I{}'.format(x), incDirs))
        self.link_args = libraries

    def get_first_cmake_var_of(self, var_list):
        # Return the first found CMake variable in list var_list
        for i in var_list:
            if i in self.vars:
                return self.vars[i]

        return []

    def get_cmake_var(self, var):
        # Return the value of the CMake variable var or an empty list if var does not exist
        for var in self.vars:
            return self.vars[var]

        return []

    def _var_to_bool(self, var):
        if var not in self.vars:
            return False

        if len(self.vars[var]) < 1:
            return False

        if self.vars[var][0].upper() in ['1', 'ON', 'TRUE']:
            return True
        return False

    def _cmake_set(self, tline: CMakeTraceLine):
        # DOC: https://cmake.org/cmake/help/latest/command/set.html

        # 1st remove PARENT_SCOPE and CACHE from args
        args = []
        for i in tline.args:
            if i == 'PARENT_SCOPE' or len(i) == 0:
                continue

            # Discard everything after the CACHE keyword
            if i == 'CACHE':
                break

            args.append(i)

        if len(args) < 1:
            raise self._gen_exception('CMake: set() requires at least one argument\n{}'.format(tline))

        if len(args) == 1:
            # Same as unset
            if args[0] in self.vars:
                del self.vars[args[0]]
        else:
            values = list(itertools.chain(*map(lambda x: x.split(';'), args[1:])))
            self.vars[args[0]] = values

    def _cmake_unset(self, tline: CMakeTraceLine):
        # DOC: https://cmake.org/cmake/help/latest/command/unset.html
        if len(tline.args) < 1:
            raise self._gen_exception('CMake: unset() requires at least one argument\n{}'.format(tline))

        if tline.args[0] in self.vars:
            del self.vars[tline.args[0]]

    def _cmake_add_executable(self, tline: CMakeTraceLine):
        # DOC: https://cmake.org/cmake/help/latest/command/add_executable.html
        args = list(tline.args) # Make a working copy

        # Make sure the exe is imported
        if 'IMPORTED' not in args:
            raise self._gen_exception('CMake: add_executable() non imported executables are not supported\n{}'.format(tline))

        args.remove('IMPORTED')

        if len(args) < 1:
            raise self._gen_exception('CMake: add_executable() requires at least 1 argument\n{}'.format(tline))

        self.targets[args[0]] = CMakeTarget(args[0], 'EXECUTABLE', {})

    def _cmake_add_library(self, tline: CMakeTraceLine):
        # DOC: https://cmake.org/cmake/help/latest/command/add_library.html
        args = list(tline.args) # Make a working copy

        # Make sure the lib is imported
        if 'IMPORTED' not in args:
            raise self._gen_exception('CMake: add_library() non imported libraries are not supported\n{}'.format(tline))

        args.remove('IMPORTED')

        # No only look at the first two arguments (target_name and target_type) and ignore the rest
        if len(args) < 2:
            raise self._gen_exception('CMake: add_library() requires at least 2 arguments\n{}'.format(tline))

        self.targets[args[0]] = CMakeTarget(args[0], args[1], {})

    def _cmake_add_custom_target(self, tline: CMakeTraceLine):
        # DOC: https://cmake.org/cmake/help/latest/command/add_custom_target.html
        # We only the first parameter (the target name) is interesting
        if len(tline.args) < 1:
            raise self._gen_exception('CMake: add_custom_target() requires at least one argument\n{}'.format(tline))

        self.targets[tline.args[0]] = CMakeTarget(tline.args[0], 'CUSTOM', {})

    def _cmake_set_property(self, tline: CMakeTraceLine):
        # DOC: https://cmake.org/cmake/help/latest/command/set_property.html
        args = list(tline.args)

        # We only care for TARGET properties
        if args.pop(0) != 'TARGET':
            return

        append = False
        targets = []
        while len(args) > 0:
            curr = args.pop(0)
            if curr == 'APPEND' or curr == 'APPEND_STRING':
                append = True
                continue

            if curr == 'PROPERTY':
                break

            targets.append(curr)

        if len(args) == 1:
            # Tries to set property to nothing so nothing has to be done
            return

        if len(args) < 2:
            raise self._gen_exception('CMake: set_property() faild to parse argument list\n{}'.format(tline))

        propName = args[0]
        propVal = list(itertools.chain(*map(lambda x: x.split(';'), args[1:])))
        propVal = list(filter(lambda x: len(x) > 0, propVal))

        if len(propVal) == 0:
            return

        for i in targets:
            if i not in self.targets:
                raise self._gen_exception('CMake: set_property() TARGET {} not found\n{}'.format(i, tline))

            if propName not in self.targets[i].properies:
                self.targets[i].properies[propName] = []

            if append:
                self.targets[i].properies[propName] += propVal
            else:
                self.targets[i].properies[propName] = propVal

    def _cmake_set_target_properties(self, tline: CMakeTraceLine):
        # DOC: https://cmake.org/cmake/help/latest/command/set_target_properties.html
        args = list(tline.args)

        targets = []
        while len(args) > 0:
            curr = args.pop(0)
            if curr == 'PROPERTIES':
                break

            targets.append(curr)

        if (len(args) % 2) != 0:
            raise self._gen_exception('CMake: set_target_properties() uneven number of property arguments\n{}'.format(tline))

        while len(args) > 0:
            propName = args.pop(0)
            propVal = args.pop(0).split(';')
            propVal = list(filter(lambda x: len(x) > 0, propVal))

            if len(propVal) == 0:
                continue

            for i in targets:
                if i not in self.targets:
                    raise self._gen_exception('CMake: set_target_properties() TARGET {} not found\n{}'.format(i, tline))

                self.targets[i].properies[propName] = propVal

    def _lex_trace(self, trace):
        # The trace format is: '<file>(<line>):  <func>(<args -- can contain \n> )\n'
        reg_tline = re.compile(r'\s*(.*\.(cmake|txt))\(([0-9]+)\):\s*(\w+)\(([\s\S]*?) ?\)\s*\n', re.MULTILINE)
        reg_other = re.compile(r'[^\n]*\n')
        reg_genexp = re.compile(r'\$<.*>')
        loc = 0
        while loc < len(trace):
            mo_file_line = reg_tline.match(trace, loc)
            if not mo_file_line:
                skip_match = reg_other.match(trace, loc)
                if not skip_match:
                    print(trace[loc:])
                    raise self._gen_exception('Failed to parse CMake trace')

                loc = skip_match.end()
                continue

            loc = mo_file_line.end()

            file = mo_file_line.group(1)
            line = mo_file_line.group(3)
            func = mo_file_line.group(4)
            args = mo_file_line.group(5).split(' ')
            args = list(map(lambda x: x.strip(), args))
            args = list(map(lambda x: reg_genexp.sub('', x), args)) # Remove generator expressions

            yield CMakeTraceLine(file, line, func, args)

    def _reset_cmake_cache(self, build_dir):
        with open('{}/CMakeCache.txt'.format(build_dir), 'w') as fp:
            fp.write('CMAKE_PLATFORM_INFO_INITIALIZED:INTERNAL=1\n')

    def _setup_compiler(self, build_dir):
        comp_dir = '{}/CMakeFiles/{}'.format(build_dir, self.cmakevers)
        os.makedirs(comp_dir, exist_ok=True)

        c_comp = '{}/CMakeCCompiler.cmake'.format(comp_dir)
        cxx_comp = '{}/CMakeCXXCompiler.cmake'.format(comp_dir)

        if not os.path.exists(c_comp):
            with open(c_comp, 'w') as fp:
                fp.write('''# Fake CMake file to skip the boring and slow stuff
set(CMAKE_C_COMPILER "{}") # Just give CMake a valid full path to any file
set(CMAKE_C_COMPILER_ID "GNU") # Pretend we have found GCC
set(CMAKE_COMPILER_IS_GNUCC 1)
set(CMAKE_C_COMPILER_LOADED 1)
set(CMAKE_C_COMPILER_WORKS TRUE)
set(CMAKE_C_ABI_COMPILED TRUE)
set(CMAKE_SIZEOF_VOID_P "{}")
'''.format(os.path.realpath(__file__), ctypes.sizeof(ctypes.c_voidp)))

        if not os.path.exists(cxx_comp):
            with open(cxx_comp, 'w') as fp:
                fp.write('''# Fake CMake file to skip the boring and slow stuff
set(CMAKE_CXX_COMPILER "{}") # Just give CMake a valid full path to any file
set(CMAKE_CXX_COMPILER_ID "GNU") # Pretend we have found GCC
set(CMAKE_COMPILER_IS_GNUCXX 1)
set(CMAKE_CXX_COMPILER_LOADED 1)
set(CMAKE_CXX_COMPILER_WORKS TRUE)
set(CMAKE_CXX_ABI_COMPILED TRUE)
set(CMAKE_SIZEOF_VOID_P "{}")
'''.format(os.path.realpath(__file__), ctypes.sizeof(ctypes.c_voidp)))

    def _setup_cmake_dir(self):
        # Setup the CMake build environment and return the "build" directory
        build_dir = '{}/cmake_{}'.format(self.cmake_root_dir, self.name)
        os.makedirs(build_dir, exist_ok=True)

        # Copy the CMakeLists.txt
        cmake_lists = '{}/CMakeLists.txt'.format(build_dir)
        if not os.path.exists(cmake_lists):
            dir_path = os.path.dirname(os.path.realpath(__file__))
            src_cmake = '{}/data/CMakeLists.txt'.format(dir_path)
            shutil.copyfile(src_cmake, cmake_lists)

        self._setup_compiler(build_dir)
        self._reset_cmake_cache(build_dir)
        return build_dir

    def _call_cmake_real(self, args, env):
        build_dir = self._setup_cmake_dir()
        cmd = self.cmakebin.get_command() + args
        p, out, err = Popen_safe(cmd, env=env, cwd=build_dir)
        rc = p.returncode
        call = ' '.join(cmd)
        mlog.debug("Called `{}` in {} -> {}".format(call, build_dir, rc))

        return rc, out, err

    def _call_cmake(self, args, env=None):
        if env is None:
            fenv = env
            env = os.environ
        else:
            fenv = frozenset(env.items())
        targs = tuple(args)

        # First check if cached, if not call the real cmake function
        cache = CMakeDependency.cmake_cache
        if (self.cmakebin, targs, fenv) not in cache:
            cache[(self.cmakebin, targs, fenv)] = self._call_cmake_real(args, env)
        return cache[(self.cmakebin, targs, fenv)]

    @staticmethod
    def get_methods():
        return [DependencyMethods.CMAKE]

    def check_cmake(self, cmakebin):
        if not cmakebin.found():
            mlog.log('Did not find CMake {!r}'
                     ''.format(' '.join(cmakebin.get_command())))
            return None
        try:
            p, out = Popen_safe(cmakebin.get_command() + ['--version'])[0:2]
            if p.returncode != 0:
                mlog.warning('Found CMake {!r} but couldn\'t run it'
                             ''.format(' '.join(cmakebin.get_command())))
                return None
        except FileNotFoundError:
            mlog.warning('We thought we found CMake {!r} but now it\'s not there. How odd!'
                         ''.format(' '.join(cmakebin.get_command())))
            return None
        except PermissionError:
            msg = 'Found CMake {!r} but didn\'t have permissions to run it.'.format(' '.join(cmakebin.get_command()))
            if not mesonlib.is_windows():
                msg += '\n\nOn Unix-like systems this is often caused by scripts that are not executable.'
            mlog.warning(msg)
            return None
        cmvers = re.sub(r'\s*cmake version\s*', '', out.split('\n')[0]).strip()
        if not version_compare(cmvers, CMakeDependency.class_cmake_version):
            mlog.warning(
                'The version of CMake', mlog.bold(cmakebin.get_path()),
                'is', mlog.bold(cmvers), 'but version', mlog.bold(CMakeDependency.class_cmake_version),
                'is required')
            return None
        return cmvers

    def log_tried(self):
        return self.type_name

class DubDependency(ExternalDependency):
    class_dubbin = None

    def __init__(self, name, environment, kwargs):
        super().__init__('dub', environment, 'd', kwargs)
        self.name = name
        self.compiler = super().get_compiler()
        self.module_path = None

        if 'required' in kwargs:
            self.required = kwargs.get('required')

        if DubDependency.class_dubbin is None:
            self.dubbin = self._check_dub()
            DubDependency.class_dubbin = self.dubbin
        else:
            self.dubbin = DubDependency.class_dubbin

        if not self.dubbin:
            if self.required:
                raise DependencyException('DUB not found.')
            self.is_found = False
            return

        mlog.debug('Determining dependency {!r} with DUB executable '
                   '{!r}'.format(name, self.dubbin.get_path()))

        # we need to know the target architecture
        arch = self.compiler.arch

        # Ask dub for the package
        ret, res = self._call_dubbin(['describe', name, '--arch=' + arch])

        if ret != 0:
            self.is_found = False
            return

        comp = self.compiler.get_id().replace('llvm', 'ldc').replace('gcc', 'gdc')
        packages = []
        description = json.loads(res)
        for package in description['packages']:
            packages.append(package['name'])
            if package['name'] == name:
                self.is_found = True

                not_lib = True
                if 'targetType' in package:
                    if package['targetType'] == 'library':
                        not_lib = False

                if not_lib:
                    mlog.error(mlog.bold(name), "found but it isn't a library")
                    self.is_found = False
                    return

                self.module_path = self._find_right_lib_path(package['path'], comp, description, True, package['targetFileName'])
                if not os.path.exists(self.module_path):
                    # check if the dependency was built for other archs
                    archs = [['x86_64'], ['x86'], ['x86', 'x86_mscoff']]
                    for a in archs:
                        description_a = copy.deepcopy(description)
                        description_a['architecture'] = a
                        arch_module_path = self._find_right_lib_path(package['path'], comp, description_a, True, package['targetFileName'])
                        if arch_module_path:
                            mlog.error(mlog.bold(name), "found but it wasn't compiled for", mlog.bold(arch))
                            self.is_found = False
                            return

                    mlog.error(mlog.bold(name), "found but it wasn't compiled with", mlog.bold(comp))
                    self.is_found = False
                    return

                self.version = package['version']
                self.pkg = package

        if self.pkg['targetFileName'].endswith('.a'):
            self.static = True

        self.compile_args = []
        for flag in self.pkg['dflags']:
            self.link_args.append(flag)
        for path in self.pkg['importPaths']:
            self.compile_args.append('-I' + os.path.join(self.pkg['path'], path))

        self.link_args = self.raw_link_args = []
        for flag in self.pkg['lflags']:
            self.link_args.append(flag)

        self.link_args.append(os.path.join(self.module_path, self.pkg['targetFileName']))

        # Handle dependencies
        libs = []

        def add_lib_args(field_name, target):
            if field_name in target['buildSettings']:
                for lib in target['buildSettings'][field_name]:
                    if lib not in libs:
                        libs.append(lib)
                        if os.name is not 'nt':
                            pkgdep = PkgConfigDependency(lib, environment, {'required': 'true', 'silent': 'true'})
                            for arg in pkgdep.get_compile_args():
                                self.compile_args.append(arg)
                            for arg in pkgdep.get_link_args():
                                self.link_args.append(arg)
                            for arg in pkgdep.get_link_args(raw=True):
                                self.raw_link_args.append(arg)

        for target in description['targets']:
            if target['rootPackage'] in packages:
                add_lib_args('libs', target)
                add_lib_args('libs-{}'.format(platform.machine()), target)
                for file in target['buildSettings']['linkerFiles']:
                    lib_path = self._find_right_lib_path(file, comp, description)
                    if lib_path:
                        self.link_args.append(lib_path)
                    else:
                        self.is_found = False

    def get_compiler(self):
        return self.compiler

    def _find_right_lib_path(self, default_path, comp, description, folder_only=False, file_name=''):
        module_path = lib_file_name = ''
        if folder_only:
            module_path = default_path
            lib_file_name = file_name
        else:
            module_path = os.path.dirname(default_path)
            lib_file_name = os.path.basename(default_path)
        module_build_path = os.path.join(module_path, '.dub', 'build')

        # Get D version implemented in the compiler
        # gdc doesn't support this
        ret, res = self._call_dubbin(['--version'])

        if ret != 0:
            mlog.error('Failed to run {!r}', mlog.bold(comp))
            return

        d_ver = re.search('v[0-9].[0-9][0-9][0-9].[0-9]', res) # Ex.: v2.081.2
        if d_ver is not None:
            d_ver = d_ver.group().rsplit('.', 1)[0].replace('v', '').replace('.', '') # Fix structure. Ex.: 2081
        else:
            d_ver = '' # gdc

        if not os.path.isdir(module_build_path):
            return ''

        # Ex.: library-debug-linux.posix-x86_64-ldc_2081-EF934983A3319F8F8FF2F0E107A363BA
        build_name = 'library-{}-{}-{}-{}_{}'.format(description['buildType'], '.'.join(description['platform']), '.'.join(description['architecture']), comp, d_ver)
        for entry in os.listdir(module_build_path):
            if entry.startswith(build_name):
                for file in os.listdir(os.path.join(module_build_path, entry)):
                    if file == lib_file_name:
                        if folder_only:
                            return os.path.join(module_build_path, entry)
                        else:
                            return os.path.join(module_build_path, entry, lib_file_name)

        return ''

    def _call_dubbin(self, args, env=None):
        p, out = Popen_safe(self.dubbin.get_command() + args, env=env)[0:2]
        return p.returncode, out.strip()

    def _call_copmbin(self, args, env=None):
        p, out = Popen_safe(self.compiler.get_exelist() + args, env=env)[0:2]
        return p.returncode, out.strip()

    def _check_dub(self):
        dubbin = ExternalProgram('dub', silent=True)
        if dubbin.found():
            try:
                p, out = Popen_safe(dubbin.get_command() + ['--version'])[0:2]
                if p.returncode != 0:
                    mlog.warning('Found dub {!r} but couldn\'t run it'
                                 ''.format(' '.join(dubbin.get_command())))
                    # Set to False instead of None to signify that we've already
                    # searched for it and not found it
                    dubbin = False
            except (FileNotFoundError, PermissionError):
                dubbin = False
        else:
            dubbin = False
        if dubbin:
            mlog.log('Found DUB:', mlog.bold(dubbin.get_path()),
                     '(%s)' % out.strip())
        else:
            mlog.log('Found DUB:', mlog.red('NO'))
        return dubbin

    @staticmethod
    def get_methods():
        return [DependencyMethods.DUB]

class ExternalProgram:
    windows_exts = ('exe', 'msc', 'com', 'bat', 'cmd')

    def __init__(self, name, command=None, silent=False, search_dir=None):
        self.name = name
        if command is not None:
            self.command = listify(command)
        else:
            self.command = self._search(name, search_dir)

        # Set path to be the last item that is actually a file (in order to
        # skip options in something like ['python', '-u', 'file.py']. If we
        # can't find any components, default to the last component of the path.
        self.path = self.command[-1]
        for i in range(len(self.command) - 1, -1, -1):
            arg = self.command[i]
            if arg is not None and os.path.isfile(arg):
                self.path = arg
                break

        if not silent:
            if self.found():
                mlog.log('Program', mlog.bold(name), 'found:', mlog.green('YES'),
                         '(%s)' % ' '.join(self.command))
            else:
                mlog.log('Program', mlog.bold(name), 'found:', mlog.red('NO'))

    def __repr__(self):
        r = '<{} {!r} -> {!r}>'
        return r.format(self.__class__.__name__, self.name, self.command)

    def description(self):
        '''Human friendly description of the command'''
        return ' '.join(self.command)

    @classmethod
    def from_bin_list(cls, bt: BinaryTable, name):
        command = bt.lookup_entry(name)
        if command is None:
            return NonExistingExternalProgram()
        return cls.from_entry(name, command)

    @staticmethod
    def from_entry(name, command):
        if isinstance(command, list):
            if len(command) == 1:
                command = command[0]
        # We cannot do any searching if the command is a list, and we don't
        # need to search if the path is an absolute path.
        if isinstance(command, list) or os.path.isabs(command):
            return ExternalProgram(name, command=command, silent=True)
        assert isinstance(command, str)
        # Search for the command using the specified string!
        return ExternalProgram(command, silent=True)

    @staticmethod
    def _shebang_to_cmd(script):
        """
        Check if the file has a shebang and manually parse it to figure out
        the interpreter to use. This is useful if the script is not executable
        or if we're on Windows (which does not understand shebangs).
        """
        try:
            with open(script) as f:
                first_line = f.readline().strip()
            if first_line.startswith('#!'):
                # In a shebang, everything before the first space is assumed to
                # be the command to run and everything after the first space is
                # the single argument to pass to that command. So we must split
                # exactly once.
                commands = first_line[2:].split('#')[0].strip().split(maxsplit=1)
                if mesonlib.is_windows():
                    # Windows does not have UNIX paths so remove them,
                    # but don't remove Windows paths
                    if commands[0].startswith('/'):
                        commands[0] = commands[0].split('/')[-1]
                    if len(commands) > 0 and commands[0] == 'env':
                        commands = commands[1:]
                    # Windows does not ship python3.exe, but we know the path to it
                    if len(commands) > 0 and commands[0] == 'python3':
                        commands = mesonlib.python_command + commands[1:]
                elif mesonlib.is_haiku():
                    # Haiku does not have /usr, but a lot of scripts assume that
                    # /usr/bin/env always exists. Detect that case and run the
                    # script with the interpreter after it.
                    if commands[0] == '/usr/bin/env':
                        commands = commands[1:]
                    # We know what python3 is, we're running on it
                    if len(commands) > 0 and commands[0] == 'python3':
                        commands = mesonlib.python_command + commands[1:]
                return commands + [script]
        except Exception as e:
            mlog.debug(e)
            pass
        mlog.debug('Unusable script {!r}'.format(script))
        return False

    def _is_executable(self, path):
        suffix = os.path.splitext(path)[-1].lower()[1:]
        if mesonlib.is_windows():
            if suffix in self.windows_exts:
                return True
        elif os.access(path, os.X_OK):
            return not os.path.isdir(path)
        return False

    def _search_dir(self, name, search_dir):
        if search_dir is None:
            return False
        trial = os.path.join(search_dir, name)
        if os.path.exists(trial):
            if self._is_executable(trial):
                return [trial]
            # Now getting desperate. Maybe it is a script file that is
            # a) not chmodded executable, or
            # b) we are on windows so they can't be directly executed.
            return self._shebang_to_cmd(trial)
        else:
            if mesonlib.is_windows():
                for ext in self.windows_exts:
                    trial_ext = '{}.{}'.format(trial, ext)
                    if os.path.exists(trial_ext):
                        return [trial_ext]
        return False

    def _search_windows_special_cases(self, name, command):
        '''
        Lots of weird Windows quirks:
        1. PATH search for @name returns files with extensions from PATHEXT,
           but only self.windows_exts are executable without an interpreter.
        2. @name might be an absolute path to an executable, but without the
           extension. This works inside MinGW so people use it a lot.
        3. The script is specified without an extension, in which case we have
           to manually search in PATH.
        4. More special-casing for the shebang inside the script.
        '''
        if command:
            # On Windows, even if the PATH search returned a full path, we can't be
            # sure that it can be run directly if it's not a native executable.
            # For instance, interpreted scripts sometimes need to be run explicitly
            # with an interpreter if the file association is not done properly.
            name_ext = os.path.splitext(command)[1]
            if name_ext[1:].lower() in self.windows_exts:
                # Good, it can be directly executed
                return [command]
            # Try to extract the interpreter from the shebang
            commands = self._shebang_to_cmd(command)
            if commands:
                return commands
            return [None]
        # Maybe the name is an absolute path to a native Windows
        # executable, but without the extension. This is technically wrong,
        # but many people do it because it works in the MinGW shell.
        if os.path.isabs(name):
            for ext in self.windows_exts:
                command = '{}.{}'.format(name, ext)
                if os.path.exists(command):
                    return [command]
        # On Windows, interpreted scripts must have an extension otherwise they
        # cannot be found by a standard PATH search. So we do a custom search
        # where we manually search for a script with a shebang in PATH.
        search_dirs = os.environ.get('PATH', '').split(';')
        for search_dir in search_dirs:
            commands = self._search_dir(name, search_dir)
            if commands:
                return commands
        return [None]

    def _search(self, name, search_dir):
        '''
        Search in the specified dir for the specified executable by name
        and if not found search in PATH
        '''
        commands = self._search_dir(name, search_dir)
        if commands:
            return commands
        # Do a standard search in PATH
        command = shutil.which(name)
        if mesonlib.is_windows():
            return self._search_windows_special_cases(name, command)
        # On UNIX-like platforms, shutil.which() is enough to find
        # all executables whether in PATH or with an absolute path
        return [command]

    def found(self):
        return self.command[0] is not None

    def get_command(self):
        return self.command[:]

    def get_path(self):
        return self.path

    def get_name(self):
        return self.name


class NonExistingExternalProgram(ExternalProgram):
    "A program that will never exist"

    def __init__(self, name='nonexistingprogram'):
        self.name = name
        self.command = [None]
        self.path = None

    def __repr__(self):
        r = '<{} {!r} -> {!r}>'
        return r.format(self.__class__.__name__, self.name, self.command)

    def found(self):
        return False


class EmptyExternalProgram(ExternalProgram):
    '''
    A program object that returns an empty list of commands. Used for cases
    such as a cross file exe_wrapper to represent that it's not required.
    '''

    def __init__(self):
        self.name = None
        self.command = []
        self.path = None

    def __repr__(self):
        r = '<{} {!r} -> {!r}>'
        return r.format(self.__class__.__name__, self.name, self.command)

    def found(self):
        return True


class ExternalLibrary(ExternalDependency):
    def __init__(self, name, link_args, environment, language, silent=False):
        super().__init__('library', environment, language, {})
        self.name = name
        self.language = language
        self.is_found = False
        if link_args:
            self.is_found = True
            self.link_args = link_args
        if not silent:
            if self.is_found:
                mlog.log('Library', mlog.bold(name), 'found:', mlog.green('YES'))
            else:
                mlog.log('Library', mlog.bold(name), 'found:', mlog.red('NO'))

    def get_link_args(self, language=None, **kwargs):
        '''
        External libraries detected using a compiler must only be used with
        compatible code. For instance, Vala libraries (.vapi files) cannot be
        used with C code, and not all Rust library types can be linked with
        C-like code. Note that C++ libraries *can* be linked with C code with
        a C++ linker (and vice-versa).
        '''
        # Using a vala library in a non-vala target, or a non-vala library in a vala target
        # XXX: This should be extended to other non-C linkers such as Rust
        if (self.language == 'vala' and language != 'vala') or \
           (language == 'vala' and self.language != 'vala'):
            return []
        return super().get_link_args(**kwargs)

    def get_partial_dependency(self, *, compile_args=False, link_args=False,
                               links=False, includes=False, sources=False):
        # External library only has link_args, so ignore the rest of the
        # interface.
        new = copy.copy(self)
        if not link_args:
            new.link_args = []
        return new


class ExtraFrameworkDependency(ExternalDependency):
    def __init__(self, name, required, path, env, lang, kwargs):
        super().__init__('extraframeworks', env, lang, kwargs)
        self.name = name
        self.required = required
        self.detect(name, path)
        if self.found():
            self.compile_args = ['-I' + os.path.join(self.path, self.name, 'Headers')]
            self.link_args = ['-F' + self.path, '-framework', self.name.split('.')[0]]

    def detect(self, name, path):
        # should use the compiler to look for frameworks, rather than peering at
        # the filesystem, so we can also find them when cross-compiling
        if self.want_cross:
            return

        lname = name.lower()
        if path is None:
            paths = ['/System/Library/Frameworks', '/Library/Frameworks']
        else:
            paths = [path]
        for p in paths:
            for d in os.listdir(p):
                fullpath = os.path.join(p, d)
                if lname != d.rsplit('.', 1)[0].lower():
                    continue
                if not stat.S_ISDIR(os.stat(fullpath).st_mode):
                    continue
                self.path = p
                self.name = d
                self.is_found = True
                return

    def log_info(self):
        return os.path.join(self.path, self.name)

    def log_tried(self):
        return 'framework'


def get_dep_identifier(name, kwargs, want_cross):
    identifier = (name, want_cross)
    for key, value in kwargs.items():
        # 'version' is irrelevant for caching; the caller must check version matches
        # 'native' is handled above with `want_cross`
        # 'required' is irrelevant for caching; the caller handles it separately
        # 'fallback' subprojects cannot be cached -- they must be initialized
        # 'default_options' is only used in fallback case
        if key in ('version', 'native', 'required', 'fallback', 'default_options'):
            continue
        # All keyword arguments are strings, ints, or lists (or lists of lists)
        if isinstance(value, list):
            value = frozenset(listify(value))
        identifier += (key, value)
    return identifier

display_name_map = {
    'boost': 'Boost',
    'dub': 'DUB',
    'gmock': 'GMock',
    'gtest': 'GTest',
    'llvm': 'LLVM',
    'mpi': 'MPI',
    'openmp': 'OpenMP',
    'wxwidgets': 'WxWidgets',
}

def find_external_dependency(name, env, kwargs):
    assert(name)
    required = kwargs.get('required', True)
    if not isinstance(required, bool):
        raise DependencyException('Keyword "required" must be a boolean.')
    if not isinstance(kwargs.get('method', ''), str):
        raise DependencyException('Keyword "method" must be a string.')
    lname = name.lower()
    if lname not in _packages_accept_language and 'language' in kwargs:
        raise DependencyException('%s dependency does not accept "language" keyword argument' % (name, ))
    if not isinstance(kwargs.get('version', ''), (str, list)):
        raise DependencyException('Keyword "Version" must be string or list.')

    # display the dependency name with correct casing
    display_name = display_name_map.get(lname, lname)

    # if this isn't a cross-build, it's uninteresting if native: is used or not
    if not env.is_cross_build():
        type_text = 'Dependency'
    else:
        type_text = 'Native' if kwargs.get('native', False) else 'Cross'
        type_text += ' dependency'

    # build a list of dependency methods to try
    candidates = _build_external_dependency_list(name, env, kwargs)

    pkg_exc = []
    pkgdep = []
    details = ''

    for c in candidates:
        # try this dependency method
        try:
            d = c()
            d._check_version()
            pkgdep.append(d)
        except Exception as e:
            pkg_exc.append(e)
            mlog.debug(str(e))
        else:
            pkg_exc.append(None)
            details = d.log_details()
            if details:
                details = '(' + details + ') '
            if 'language' in kwargs:
                details += 'for ' + d.language + ' '

            # if the dependency was found
            if d.found():

                info = []
                if d.version:
                    info.append(d.version)

                log_info = d.log_info()
                if log_info:
                    info.append('(' + log_info + ')')

                info = ' '.join(info)

                mlog.log(type_text, mlog.bold(display_name), details + 'found:', mlog.green('YES'), info)

                return d

    # otherwise, the dependency could not be found
    tried_methods = [d.log_tried() for d in pkgdep if d.log_tried()]
    if tried_methods:
        tried = '{}'.format(mlog.format_list(tried_methods))
    else:
        tried = ''

    mlog.log(type_text, mlog.bold(display_name), details + 'found:', mlog.red('NO'),
             '(tried {})'.format(tried) if tried else '')

    if required:
        # if an exception occurred with the first detection method, re-raise it
        # (on the grounds that it came from the preferred dependency detection
        # method)
        if pkg_exc[0]:
            raise pkg_exc[0]

        # we have a list of failed ExternalDependency objects, so we can report
        # the methods we tried to find the dependency
        raise DependencyException('Dependency "%s" not found' % (name) +
                                  (', tried %s' % (tried) if tried else ''))

    return NotFoundDependency(env)


def _build_external_dependency_list(name, env, kwargs):
    # First check if the method is valid
    if 'method' in kwargs and kwargs['method'] not in [e.value for e in DependencyMethods]:
        raise DependencyException('method {!r} is invalid'.format(kwargs['method']))

    # Is there a specific dependency detector for this dependency?
    lname = name.lower()
    if lname in packages:
        # Create the list of dependency object constructors using a factory
        # class method, if one exists, otherwise the list just consists of the
        # constructor
        if getattr(packages[lname], '_factory', None):
            dep = packages[lname]._factory(env, kwargs)
        else:
            dep = [functools.partial(packages[lname], env, kwargs)]
        return dep

    candidates = []

    # If it's explicitly requested, use the dub detection method (only)
    if 'dub' == kwargs.get('method', ''):
        candidates.append(functools.partial(DubDependency, name, env, kwargs))
        return candidates

    # If it's explicitly requested, use the pkgconfig detection method (only)
    if 'pkg-config' == kwargs.get('method', ''):
        candidates.append(functools.partial(PkgConfigDependency, name, env, kwargs))
        return candidates

    # If it's explicitly requested, use the CMake detection method (only)
    if 'cmake' == kwargs.get('method', ''):
        candidates.append(functools.partial(CMakeDependency, name, env, kwargs))
        return candidates

    # Otherwise, just use the pkgconfig and cmake dependency detector
    if 'auto' == kwargs.get('method', 'auto'):
        candidates.append(functools.partial(PkgConfigDependency, name, env, kwargs))
        candidates.append(functools.partial(CMakeDependency,     name, env, kwargs))

        # On OSX, also try framework dependency detector
        if mesonlib.is_osx():
            candidates.append(functools.partial(ExtraFrameworkDependency, name,
                                                False, None, env, None, kwargs))

    return candidates


def strip_system_libdirs(environment, link_args):
    """Remove -L<system path> arguments.

    leaving these in will break builds where a user has a version of a library
    in the system path, and a different version not in the system path if they
    want to link against the non-system path version.
    """
    exclude = {'-L{}'.format(p) for p in environment.get_compiler_system_dirs()}
    return [l for l in link_args if l not in exclude]
