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
import json
import shlex
import shutil
import stat
import sys
import textwrap
import platform
import typing as T
from enum import Enum
from pathlib import Path, PurePath

import pkg_resources

from .. import mlog
from .. import mesonlib
from ..compilers import clib_langs
from ..envconfig import get_env_var
from ..environment import BinaryTable, Environment, MachineInfo
from ..cmake import CMakeExecutor, CMakeTraceParser, CMakeException
from ..mesonlib import MachineChoice, MesonException, OrderedSet, PerMachine
from ..mesonlib import Popen_safe, version_compare_many, version_compare, listify, stringlistify, extract_as_list, split_args
from ..mesonlib import Version, LibType

if T.TYPE_CHECKING:
    from ..compilers.compilers import CompilerType  # noqa: F401
    DependencyType = T.TypeVar('DependencyType', bound='Dependency')

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


def find_external_program(env: Environment, for_machine: MachineChoice, name: str,
                          display_name: str, default_names: T.List[str],
                          allow_default_for_cross: bool = True) -> T.Generator['ExternalProgram', None, None]:
    """Find an external program, chcking the cross file plus any default options."""
    # Lookup in cross or machine file.
    potential_path = env.lookup_binary_entry(for_machine, name)
    if potential_path is not None:
        mlog.debug('{} binary for {} specified from cross file, native file, '
                    'or env var as {}'.format(display_name, for_machine, potential_path))
        yield ExternalProgram.from_entry(name, potential_path)
        # We never fallback if the user-specified option is no good, so
        # stop returning options.
        return
    mlog.debug('{} binary missing from cross or native file, or env var undefined.'.format(display_name))
    # Fallback on hard-coded defaults, if a default binary is allowed for use
    # with cross targets, or if this is not a cross target
    if allow_default_for_cross or not (for_machine is MachineChoice.HOST and env.is_cross_build(for_machine)):
        for potential_path in default_names:
            mlog.debug('Trying a default {} fallback at'.format(display_name), potential_path)
            yield ExternalProgram(potential_path, silent=True)
    else:
        mlog.debug('Default target is not allowed for cross use')


class Dependency:

    @classmethod
    def _process_include_type_kw(cls, kwargs) -> str:
        if 'include_type' not in kwargs:
            return 'preserve'
        if not isinstance(kwargs['include_type'], str):
            raise DependencyException('The include_type kwarg must be a string type')
        if kwargs['include_type'] not in ['preserve', 'system', 'non-system']:
            raise DependencyException("include_type may only be one of ['preserve', 'system', 'non-system']")
        return kwargs['include_type']

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
        self.methods = process_method_kw(self.get_methods(), kwargs)
        self.include_type = self._process_include_type_kw(kwargs)
        self.ext_deps = []  # type: T.List[Dependency]

    def __repr__(self):
        s = '<{0} {1}: {2}>'
        return s.format(self.__class__.__name__, self.name, self.is_found)

    def get_compile_args(self):
        if self.include_type == 'system':
            converted = []
            for i in self.compile_args:
                if i.startswith('-I') or i.startswith('/I'):
                    converted += ['-isystem' + i[2:]]
                else:
                    converted += [i]
            return converted
        if self.include_type == 'non-system':
            converted = []
            for i in self.compile_args:
                if i.startswith('-isystem'):
                    converted += ['-I' + i[8:]]
                else:
                    converted += [i]
            return converted
        return self.compile_args

    def get_link_args(self, raw: bool = False) -> T.List[str]:
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

    def get_include_type(self) -> str:
        return self.include_type

    def get_exe_args(self, compiler):
        return []

    def get_pkgconfig_variable(self, variable_name, kwargs):
        raise DependencyException('{!r} is not a pkgconfig dependency'.format(self.name))

    def get_configtool_variable(self, variable_name):
        raise DependencyException('{!r} is not a config-tool dependency'.format(self.name))

    def get_partial_dependency(self, *, compile_args: bool = False,
                               link_args: bool = False, links: bool = False,
                               includes: bool = False, sources: bool = False):
        """Create a new dependency that contains part of the parent dependency.

        The following options can be inherited:
            links -- all link_with arguments
            includes -- all include_directory and -I/-isystem calls
            sources -- any source, header, or generated sources
            compile_args -- any compile args
            link_args -- any link args

        Additionally the new dependency will have the version parameter of it's
        parent (if any) and the requested values of any dependencies will be
        added as well.
        """
        raise RuntimeError('Unreachable code in partial_dependency called')

    def _add_sub_dependency(self, deplist: T.List['DependencyType']) -> bool:
        """Add an internal depdency from a list of possible dependencies.

        This method is intended to make it easier to add additional
        dependencies to another dependency internally.

        Returns true if the dependency was successfully added, false
        otherwise.
        """
        for d in deplist:
            dep = d()
            if dep.is_found:
                self.ext_deps.append(dep)
                return True
        return False

    def get_variable(self, *, cmake: T.Optional[str] = None, pkgconfig: T.Optional[str] = None,
                     configtool: T.Optional[str] = None, internal: T.Optional[str] = None,
                     default_value: T.Optional[str] = None,
                     pkgconfig_define: T.Optional[T.List[str]] = None) -> T.Union[str, T.List[str]]:
        if default_value is not None:
            return default_value
        raise DependencyException('No default provided for dependency {!r}, which is not pkg-config, cmake, or config-tool based.'.format(self))

    def generate_system_dependency(self, include_type: str) -> T.Type['Dependency']:
        new_dep = copy.deepcopy(self)
        new_dep.include_type = self._process_include_type_kw({'include_type': include_type})
        return new_dep

class InternalDependency(Dependency):
    def __init__(self, version, incdirs, compile_args, link_args, libraries,
                 whole_libraries, sources, ext_deps, variables: T.Dict[str, T.Any]):
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
        self.variables = variables

    def get_pkgconfig_variable(self, variable_name, kwargs):
        raise DependencyException('Method "get_pkgconfig_variable()" is '
                                  'invalid for an internal dependency')

    def get_configtool_variable(self, variable_name):
        raise DependencyException('Method "get_configtool_variable()" is '
                                  'invalid for an internal dependency')

    def get_partial_dependency(self, *, compile_args: bool = False,
                               link_args: bool = False, links: bool = False,
                               includes: bool = False, sources: bool = False):
        final_compile_args = self.compile_args.copy() if compile_args else []
        final_link_args = self.link_args.copy() if link_args else []
        final_libraries = self.libraries.copy() if links else []
        final_whole_libraries = self.whole_libraries.copy() if links else []
        final_sources = self.sources.copy() if sources else []
        final_includes = self.include_directories.copy() if includes else []
        final_deps = [d.get_partial_dependency(
            compile_args=compile_args, link_args=link_args, links=links,
            includes=includes, sources=sources) for d in self.ext_deps]
        return InternalDependency(
            self.version, final_includes, final_compile_args,
            final_link_args, final_libraries, final_whole_libraries,
            final_sources, final_deps, self.variables)

    def get_variable(self, *, cmake: T.Optional[str] = None, pkgconfig: T.Optional[str] = None,
                     configtool: T.Optional[str] = None, internal: T.Optional[str] = None,
                     default_value: T.Optional[str] = None,
                     pkgconfig_define: T.Optional[T.List[str]] = None) -> T.Union[str, T.List[str]]:
        val = self.variables.get(internal, default_value)
        if val is not None:
            return val
        raise DependencyException('Could not get an internal variable and no default provided for {!r}'.format(self))


class HasNativeKwarg:
    def __init__(self, kwargs):
        self.for_machine = self.get_for_machine_from_kwargs(kwargs)

    def get_for_machine_from_kwargs(self, kwargs):
        return MachineChoice.BUILD if kwargs.get('native', False) else MachineChoice.HOST

class ExternalDependency(Dependency, HasNativeKwarg):
    def __init__(self, type_name, environment, kwargs, language: T.Optional[str] = None):
        Dependency.__init__(self, type_name, kwargs)
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
        # Is this dependency to be run on the build platform?
        HasNativeKwarg.__init__(self, kwargs)
        self.clib_compiler = detect_compiler(self.name, environment, self.for_machine, self.language)

    def get_compiler(self):
        return self.clib_compiler

    def get_partial_dependency(self, *, compile_args: bool = False,
                               link_args: bool = False, links: bool = False,
                               includes: bool = False, sources: bool = False):
        new = copy.copy(self)
        if not compile_args:
            new.compile_args = []
        if not link_args:
            new.link_args = []
        if not sources:
            new.sources = []
        if not includes:
            new.include_directories = []
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
                                  'found', mlog.normal_cyan(self.version), 'but need:',
                                  mlog.bold(', '.join(["'{}'".format(e) for e in not_found]))]
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

    def get_partial_dependency(self, *, compile_args: bool = False,
                               link_args: bool = False, links: bool = False,
                               includes: bool = False, sources: bool = False):
        return copy.copy(self)


class ConfigToolDependency(ExternalDependency):

    """Class representing dependencies found using a config tool.

    Takes the following extra keys in kwargs that it uses internally:
    :tools List[str]: A list of tool names to use
    :version_arg str: The argument to pass to the tool to get it's version
    :returncode_value int: The value of the correct returncode
        Because some tools are stupid and don't return 0
    """

    tools = None
    tool_name = None
    version_arg = '--version'
    __strip_version = re.compile(r'^[0-9][0-9.]+')

    def __init__(self, name, environment, kwargs, language: T.Optional[str] = None):
        super().__init__('config-tool', environment, kwargs, language=language)
        self.name = name
        # You may want to overwrite the class version in some cases
        self.tools = listify(kwargs.get('tools', self.tools))
        if not self.tool_name:
            self.tool_name = self.tools[0]
        if 'version_arg' in kwargs:
            self.version_arg = kwargs['version_arg']

        req_version = kwargs.get('version', None)
        tool, version = self.find_config(req_version, kwargs.get('returncode_value', 0))
        self.config = tool
        self.is_found = self.report_config(version, req_version)
        if not self.is_found:
            self.config = None
            return
        self.version = version

    def _sanitize_version(self, version):
        """Remove any non-numeric, non-point version suffixes."""
        m = self.__strip_version.match(version)
        if m:
            # Ensure that there isn't a trailing '.', such as an input like
            # `1.2.3.git-1234`
            return m.group(0).rstrip('.')
        return version

    def find_config(self, versions: T.Optional[T.List[str]] = None, returncode: int = 0) \
            -> T.Tuple[T.Optional[str], T.Optional[str]]:
        """Helper method that searches for config tool binaries in PATH and
        returns the one that best matches the given version requirements.
        """
        if not isinstance(versions, list) and versions is not None:
            versions = listify(versions)
        best_match = (None, None)  # type: T.Tuple[T.Optional[str], T.Optional[str]]
        for potential_bin in find_external_program(
                self.env, self.for_machine, self.tool_name,
                self.tool_name, self.tools, allow_default_for_cross=False):
            if not potential_bin.found():
                continue
            tool = potential_bin.get_command()
            try:
                p, out = Popen_safe(tool + [self.version_arg])[:2]
            except (FileNotFoundError, PermissionError):
                continue
            if p.returncode != returncode:
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
            found_msg += [mlog.green('YES'), '({})'.format(' '.join(self.config)), version]

        mlog.log(*found_msg)

        return self.config is not None

    def get_config_value(self, args, stage):
        p, out, err = Popen_safe(self.config + args)
        if p.returncode != 0:
            if self.required:
                raise DependencyException(
                    'Could not generate {} for {}.\n{}'.format(
                        stage, self.name, err))
            return []
        return split_args(out)

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

    def get_variable(self, *, cmake: T.Optional[str] = None, pkgconfig: T.Optional[str] = None,
                     configtool: T.Optional[str] = None, internal: T.Optional[str] = None,
                     default_value: T.Optional[str] = None,
                     pkgconfig_define: T.Optional[T.List[str]] = None) -> T.Union[str, T.List[str]]:
        if configtool:
            # In the not required case '' (empty string) will be returned if the
            # variable is not found. Since '' is a valid value to return we
            # set required to True here to force and error, and use the
            # finally clause to ensure it's restored.
            restore = self.required
            self.required = True
            try:
                return self.get_configtool_variable(configtool)
            except DependencyException:
                pass
            finally:
                self.required = restore
        if default_value is not None:
            return default_value
        raise DependencyException('Could not get config-tool variable and no default provided for {!r}'.format(self))


class PkgConfigDependency(ExternalDependency):
    # The class's copy of the pkg-config path. Avoids having to search for it
    # multiple times in the same Meson invocation.
    class_pkgbin = PerMachine(None, None)
    # We cache all pkg-config subprocess invocations to avoid redundant calls
    pkgbin_cache = {}

    def __init__(self, name, environment, kwargs, language: T.Optional[str] = None):
        super().__init__('pkgconfig', environment, kwargs, language=language)
        self.name = name
        self.is_libtool = False
        # Store a copy of the pkg-config path on the object itself so it is
        # stored in the pickled coredata and recovered.
        self.pkgbin = None

        # Only search for pkg-config for each machine the first time and store
        # the result in the class definition
        if PkgConfigDependency.class_pkgbin[self.for_machine] is False:
            mlog.debug('Pkg-config binary for %s is cached as not found.' % self.for_machine)
        elif PkgConfigDependency.class_pkgbin[self.for_machine] is not None:
            mlog.debug('Pkg-config binary for %s is cached.' % self.for_machine)
        else:
            assert PkgConfigDependency.class_pkgbin[self.for_machine] is None
            mlog.debug('Pkg-config binary for %s is not cached.' % self.for_machine)
            for potential_pkgbin in find_external_program(
                    self.env, self.for_machine, 'pkgconfig', 'Pkg-config',
                    environment.default_pkgconfig, allow_default_for_cross=False):
                version_if_ok = self.check_pkgconfig(potential_pkgbin)
                if not version_if_ok:
                    continue
                if not self.silent:
                    mlog.log('Found pkg-config:', mlog.bold(potential_pkgbin.get_path()),
                             '(%s)' % version_if_ok)
                PkgConfigDependency.class_pkgbin[self.for_machine] = potential_pkgbin
                break
            else:
                if not self.silent:
                    mlog.log('Found Pkg-config:', mlog.red('NO'))
                # Set to False instead of None to signify that we've already
                # searched for it and not found it
                PkgConfigDependency.class_pkgbin[self.for_machine] = False

        self.pkgbin = PkgConfigDependency.class_pkgbin[self.for_machine]
        if self.pkgbin is False:
            self.pkgbin = None
            msg = 'Pkg-config binary for machine %s not found. Giving up.' % self.for_machine
            if self.required:
                raise DependencyException(msg)
            else:
                mlog.debug(msg)
                return

        mlog.debug('Determining dependency {!r} with pkg-config executable '
                   '{!r}'.format(name, self.pkgbin.get_path()))
        ret, self.version, _ = self._call_pkgbin(['--modversion', name])
        if ret != 0:
            return

        self.is_found = True

        try:
            # Fetch cargs to be used while using this dependency
            self._set_cargs()
            # Fetch the libraries and library paths needed for using this
            self._set_libs()
        except DependencyException as e:
            mlog.debug("pkg-config error with '%s': %s" % (name, e))
            if self.required:
                raise
            else:
                self.compile_args = []
                self.link_args = []
                self.is_found = False
                self.reason = e

    def __repr__(self):
        s = '<{0} {1}: {2} {3}>'
        return s.format(self.__class__.__name__, self.name, self.is_found,
                        self.version_reqs)

    def _call_pkgbin_real(self, args, env):
        cmd = self.pkgbin.get_command() + args
        p, out, err = Popen_safe(cmd, env=env)
        rc, out, err = p.returncode, out.strip(), err.strip()
        call = ' '.join(cmd)
        mlog.debug("Called `{}` -> {}\n{}".format(call, rc, out))
        return rc, out, err

    def _call_pkgbin(self, args, env=None):
        # Always copy the environment since we're going to modify it
        # with pkg-config variables
        if env is None:
            env = os.environ.copy()
        else:
            env = env.copy()

        extra_paths = self.env.coredata.builtins_per_machine[self.for_machine]['pkg_config_path'].value
        sysroot = self.env.properties[self.for_machine].get_sys_root()
        if sysroot:
            env['PKG_CONFIG_SYSROOT_DIR'] = sysroot
        new_pkg_config_path = ':'.join([p for p in extra_paths])
        mlog.debug('PKG_CONFIG_PATH: ' + new_pkg_config_path)
        env['PKG_CONFIG_PATH'] = new_pkg_config_path

        pkg_config_libdir_prop = self.env.properties[self.for_machine].get_pkg_config_libdir()
        if pkg_config_libdir_prop:
            new_pkg_config_libdir = ':'.join([p for p in pkg_config_libdir_prop])
            env['PKG_CONFIG_LIBDIR'] = new_pkg_config_libdir
            mlog.debug('PKG_CONFIG_LIBDIR: ' + new_pkg_config_libdir)

        fenv = frozenset(env.items())
        targs = tuple(args)
        cache = PkgConfigDependency.pkgbin_cache
        if (self.pkgbin, targs, fenv) not in cache:
            cache[(self.pkgbin, targs, fenv)] = self._call_pkgbin_real(args, env)
        return cache[(self.pkgbin, targs, fenv)]

    def _convert_mingw_paths(self, args: T.List[str]) -> T.List[str]:
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
            elif arg.startswith(('-L', '-I')) or (len(arg) > 2 and arg[1] == ':'):
                # clean out improper '\\ ' as comes from some Windows pkg-config files
                arg = arg.replace('\\ ', ' ')
            if len(pargs) > 1 and len(pargs[1]) == 1:
                arg = tmpl.format(pargs[1], '/'.join(pargs[2:]))
            converted.append(arg)
        return converted

    def _split_args(self, cmd):
        # pkg-config paths follow Unix conventions, even on Windows; split the
        # output using shlex.split rather than mesonlib.split_args
        return shlex.split(cmd)

    def _set_cargs(self):
        env = None
        if self.language == 'fortran':
            # gfortran doesn't appear to look in system paths for INCLUDE files,
            # so don't allow pkg-config to suppress -I flags for system paths
            env = os.environ.copy()
            env['PKG_CONFIG_ALLOW_SYSTEM_CFLAGS'] = '1'
        ret, out, err = self._call_pkgbin(['--cflags', self.name], env=env)
        if ret != 0:
            raise DependencyException('Could not generate cargs for %s:\n%s\n' %
                                      (self.name, err))
        self.compile_args = self._convert_mingw_paths(self._split_args(out))

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
        raw_link_args = self._convert_mingw_paths(self._split_args(out_raw))
        for arg in raw_link_args:
            if arg.startswith('-L') and not arg.startswith(('-L-l', '-L-L')):
                path = arg[2:]
                if not os.path.isabs(path):
                    # Resolve the path as a compiler in the build directory would
                    path = os.path.join(self.env.get_build_dir(), path)
                prefix_libpaths.add(path)
        # Library paths are not always ordered in a meaningful way
        #
        # Instead of relying on pkg-config or pkgconf to provide -L flags in a
        # specific order, we reorder library paths ourselves, according to th
        # order specified in PKG_CONFIG_PATH. See:
        # https://github.com/mesonbuild/meson/issues/4271
        #
        # Only prefix_libpaths are reordered here because there should not be
        # too many system_libpaths to cause library version issues.
        pkg_config_path = get_env_var(
            self.for_machine,
            self.env.is_cross_build(),
            'PKG_CONFIG_PATH')
        if pkg_config_path:
            pkg_config_path = pkg_config_path.split(os.pathsep)
        else:
            pkg_config_path = []
        pkg_config_path = self._convert_mingw_paths(pkg_config_path)
        prefix_libpaths = sort_libpaths(prefix_libpaths, pkg_config_path)
        system_libpaths = OrderedSet()
        full_args = self._convert_mingw_paths(self._split_args(out))
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
        libtype = LibType.STATIC if self.static else LibType.PREFER_SHARED
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
        ret, out, err = self._call_pkgbin(libcmd, env=env)
        if ret != 0:
            raise DependencyException('Could not generate libs for %s:\n%s\n' %
                                      (self.name, err))
        # Also get the 'raw' output without -Lfoo system paths for adding -L
        # args with -lfoo when a library can't be found, and also in
        # gnome.generate_gir + gnome.gtkdoc which need -L -l arguments.
        ret, out_raw, err_raw = self._call_pkgbin(libcmd)
        if ret != 0:
            raise DependencyException('Could not generate libs for %s:\n\n%s' %
                                      (self.name, out_raw))
        self.link_args, self.raw_link_args = self._search_libs(out, out_raw)

    def get_pkgconfig_variable(self, variable_name, kwargs):
        options = ['--variable=' + variable_name, self.name]

        if 'define_variable' in kwargs:
            definition = kwargs.get('define_variable', [])
            if not isinstance(definition, list):
                raise DependencyException('define_variable takes a list')

            if len(definition) != 2 or not all(isinstance(i, str) for i in definition):
                raise DependencyException('define_variable must be made up of 2 strings for VARIABLENAME and VARIABLEVALUE')

            options = ['--define-variable=' + '='.join(definition)] + options

        ret, out, err = self._call_pkgbin(options)
        variable = ''
        if ret != 0:
            if self.required:
                raise DependencyException('dependency %s not found:\n%s\n' %
                                          (self.name, err))
        else:
            variable = out.strip()

            # pkg-config doesn't distinguish between empty and non-existent variables
            # use the variable list to check for variable existence
            if not variable:
                ret, out, _ = self._call_pkgbin(['--print-variables', self.name])
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

    def get_variable(self, *, cmake: T.Optional[str] = None, pkgconfig: T.Optional[str] = None,
                     configtool: T.Optional[str] = None, internal: T.Optional[str] = None,
                     default_value: T.Optional[str] = None,
                     pkgconfig_define: T.Optional[T.List[str]] = None) -> T.Union[str, T.List[str]]:
        if pkgconfig:
            kwargs = {}
            if default_value is not None:
                kwargs['default'] = default_value
            if pkgconfig_define is not None:
                kwargs['define_variable'] = pkgconfig_define
            try:
                return self.get_pkgconfig_variable(pkgconfig, kwargs)
            except DependencyException:
                pass
        if default_value is not None:
            return default_value
        raise DependencyException('Could not get pkg-config variable and no default provided for {!r}'.format(self))

class CMakeDependency(ExternalDependency):
    # The class's copy of the CMake path. Avoids having to search for it
    # multiple times in the same Meson invocation.
    class_cmakeinfo = PerMachine(None, None)
    # Version string for the minimum CMake version
    class_cmake_version = '>=3.4'
    # CMake generators to try (empty for no generator)
    class_cmake_generators = ['', 'Ninja', 'Unix Makefiles', 'Visual Studio 10 2010']
    class_working_generator = None

    def _gen_exception(self, msg):
        return DependencyException('Dependency {} not found: {}'.format(self.name, msg))

    def _main_cmake_file(self) -> str:
        return 'CMakeLists.txt'

    def _extra_cmake_opts(self) -> T.List[str]:
        return []

    def _map_module_list(self, modules: T.List[T.Tuple[str, bool]], components: T.List[T.Tuple[str, bool]]) -> T.List[T.Tuple[str, bool]]:
        # Map the input module list to something else
        # This function will only be executed AFTER the initial CMake
        # interpreter pass has completed. Thus variables defined in the
        # CMakeLists.txt can be accessed here.
        #
        # Both the modules and components inputs contain the original lists.
        return modules

    def _map_component_list(self, modules: T.List[T.Tuple[str, bool]], components: T.List[T.Tuple[str, bool]]) -> T.List[T.Tuple[str, bool]]:
        # Map the input components list to something else. This
        # function will be executed BEFORE the initial CMake interpreter
        # pass. Thus variables from the CMakeLists.txt can NOT be accessed.
        #
        # Both the modules and components inputs contain the original lists.
        return components

    def _original_module_name(self, module: str) -> str:
        # Reverse the module mapping done by _map_module_list for
        # one module
        return module

    def __init__(self, name: str, environment: Environment, kwargs, language: T.Optional[str] = None):
        # Gather a list of all languages to support
        self.language_list = []  # type: T.List[str]
        if language is None:
            compilers = None
            if kwargs.get('native', False):
                compilers = environment.coredata.compilers.build
            else:
                compilers = environment.coredata.compilers.host

            candidates = ['c', 'cpp', 'fortran', 'objc', 'objcxx']
            self.language_list += [x for x in candidates if x in compilers]
        else:
            self.language_list += [language]

        # Add additional languages if required
        if 'fortran' in self.language_list:
            self.language_list += ['c']

        # Ensure that the list is unique
        self.language_list = list(set(self.language_list))

        super().__init__('cmake', environment, kwargs, language=language)
        self.name = name
        self.is_libtool = False
        # Store a copy of the CMake path on the object itself so it is
        # stored in the pickled coredata and recovered.
        self.cmakebin = None
        self.cmakeinfo = None

        # Where all CMake "build dirs" are located
        self.cmake_root_dir = environment.scratch_dir

        # T.List of successfully found modules
        self.found_modules = []

        # Initialize with None before the first return to avoid
        # AttributeError exceptions in derived classes
        self.traceparser = None  # type: CMakeTraceParser

        self.cmakebin = CMakeExecutor(environment, CMakeDependency.class_cmake_version, self.for_machine, silent=self.silent)
        if not self.cmakebin.found():
            self.cmakebin = None
            msg = 'No CMake binary for machine %s not found. Giving up.' % self.for_machine
            if self.required:
                raise DependencyException(msg)
            mlog.debug(msg)
            return

        # Setup the trace parser
        self.traceparser = CMakeTraceParser(self.cmakebin.version(), self._get_build_dir())

        cm_args = stringlistify(extract_as_list(kwargs, 'cmake_args'))
        if CMakeDependency.class_cmakeinfo[self.for_machine] is None:
            CMakeDependency.class_cmakeinfo[self.for_machine] = self._get_cmake_info(cm_args)
        self.cmakeinfo = CMakeDependency.class_cmakeinfo[self.for_machine]
        if self.cmakeinfo is None:
            raise self._gen_exception('Unable to obtain CMake system information')

        components = [(x, True) for x in stringlistify(extract_as_list(kwargs, 'components'))]
        modules = [(x, True) for x in stringlistify(extract_as_list(kwargs, 'modules'))]
        modules += [(x, False) for x in stringlistify(extract_as_list(kwargs, 'optional_modules'))]
        cm_path = stringlistify(extract_as_list(kwargs, 'cmake_module_path'))
        cm_path = [x if os.path.isabs(x) else os.path.join(environment.get_source_dir(), x) for x in cm_path]
        if cm_path:
            cm_args.append('-DCMAKE_MODULE_PATH=' + ';'.join(cm_path))
        if not self._preliminary_find_check(name, cm_path, self.cmakebin.get_cmake_prefix_paths(), environment.machines[self.for_machine]):
            mlog.debug('Preliminary CMake check failed. Aborting.')
            return
        self._detect_dep(name, modules, components, cm_args)

    def __repr__(self):
        s = '<{0} {1}: {2} {3}>'
        return s.format(self.__class__.__name__, self.name, self.is_found,
                        self.version_reqs)

    def _get_cmake_info(self, cm_args):
        mlog.debug("Extracting basic cmake information")
        res = {}

        # Try different CMake generators since specifying no generator may fail
        # in cygwin for some reason
        gen_list = []
        # First try the last working generator
        if CMakeDependency.class_working_generator is not None:
            gen_list += [CMakeDependency.class_working_generator]
        gen_list += CMakeDependency.class_cmake_generators

        temp_parser = CMakeTraceParser(self.cmakebin.version(), self._get_build_dir())

        for i in gen_list:
            mlog.debug('Try CMake generator: {}'.format(i if len(i) > 0 else 'auto'))

            # Prepare options
            cmake_opts = temp_parser.trace_args() + ['.']
            cmake_opts += cm_args
            if len(i) > 0:
                cmake_opts = ['-G', i] + cmake_opts

            # Run CMake
            ret1, out1, err1 = self._call_cmake(cmake_opts, 'CMakePathInfo.txt')

            # Current generator was successful
            if ret1 == 0:
                CMakeDependency.class_working_generator = i
                break

            mlog.debug('CMake failed to gather system information for generator {} with error code {}'.format(i, ret1))
            mlog.debug('OUT:\n{}\n\n\nERR:\n{}\n\n'.format(out1, err1))

        # Check if any generator succeeded
        if ret1 != 0:
            return None

        try:
            temp_parser.parse(err1)
        except MesonException:
            return None

        def process_paths(l: T.List[str]) -> T.Set[str]:
            l = [x.split(':') for x in l]
            l = [x for sublist in l for x in sublist]
            return set(l)

        # Extract the variables and sanity check them
        root_paths = process_paths(temp_parser.get_cmake_var('MESON_FIND_ROOT_PATH'))
        root_paths.update(process_paths(temp_parser.get_cmake_var('MESON_CMAKE_SYSROOT')))
        root_paths = sorted(root_paths)
        root_paths = list(filter(lambda x: os.path.isdir(x), root_paths))
        module_paths = process_paths(temp_parser.get_cmake_var('MESON_PATHS_LIST'))
        rooted_paths = []
        for j in [Path(x) for x in root_paths]:
            for i in [Path(x) for x in module_paths]:
                rooted_paths.append(str(j / i.relative_to(i.anchor)))
        module_paths = sorted(module_paths.union(rooted_paths))
        module_paths = list(filter(lambda x: os.path.isdir(x), module_paths))
        archs = temp_parser.get_cmake_var('MESON_ARCH_LIST')

        common_paths = ['lib', 'lib32', 'lib64', 'libx32', 'share']
        for i in archs:
            common_paths += [os.path.join('lib', i)]

        res = {
            'module_paths': module_paths,
            'cmake_root': temp_parser.get_cmake_var('MESON_CMAKE_ROOT')[0],
            'archs': archs,
            'common_paths': common_paths
        }

        mlog.debug('  -- Module search paths:    {}'.format(res['module_paths']))
        mlog.debug('  -- CMake root:             {}'.format(res['cmake_root']))
        mlog.debug('  -- CMake architectures:    {}'.format(res['archs']))
        mlog.debug('  -- CMake lib search paths: {}'.format(res['common_paths']))

        return res

    @staticmethod
    @functools.lru_cache(maxsize=None)
    def _cached_listdir(path: str) -> T.Tuple[T.Tuple[str, str]]:
        try:
            return tuple((x, str(x).lower()) for x in os.listdir(path))
        except OSError:
            return ()

    @staticmethod
    @functools.lru_cache(maxsize=None)
    def _cached_isdir(path: str) -> bool:
        try:
            return os.path.isdir(path)
        except OSError:
            return False

    def _preliminary_find_check(self, name: str, module_path: T.List[str], prefix_path: T.List[str], machine: MachineInfo) -> bool:
        lname = str(name).lower()

        # Checks <path>, <path>/cmake, <path>/CMake
        def find_module(path: str) -> bool:
            for i in [path, os.path.join(path, 'cmake'), os.path.join(path, 'CMake')]:
                if not self._cached_isdir(i):
                    continue

                # Check the directory case insensitve
                content = self._cached_listdir(i)
                candidates = ['Find{}.cmake', '{}Config.cmake', '{}-config.cmake']
                candidates = [x.format(name).lower() for x in candidates]
                if any([x[1] in candidates for x in content]):
                    return True
            return False

        # Search in <path>/(lib/<arch>|lib*|share) for cmake files
        def search_lib_dirs(path: str) -> bool:
            for i in [os.path.join(path, x) for x in self.cmakeinfo['common_paths']]:
                if not self._cached_isdir(i):
                    continue

                # Check <path>/(lib/<arch>|lib*|share)/cmake/<name>*/
                cm_dir = os.path.join(i, 'cmake')
                if self._cached_isdir(cm_dir):
                    content = self._cached_listdir(cm_dir)
                    content = list(filter(lambda x: x[1].startswith(lname), content))
                    for k in content:
                        if find_module(os.path.join(cm_dir, k[0])):
                            return True

                # <path>/(lib/<arch>|lib*|share)/<name>*/
                # <path>/(lib/<arch>|lib*|share)/<name>*/(cmake|CMake)/
                content = self._cached_listdir(i)
                content = list(filter(lambda x: x[1].startswith(lname), content))
                for k in content:
                    if find_module(os.path.join(i, k[0])):
                        return True

            return False

        # Check the user provided and system module paths
        for i in module_path + [os.path.join(self.cmakeinfo['cmake_root'], 'Modules')]:
            if find_module(i):
                return True

        # Check the user provided prefix paths
        for i in prefix_path:
            if search_lib_dirs(i):
                return True

        # Check the system paths
        for i in self.cmakeinfo['module_paths']:
            if find_module(i):
                return True

            if search_lib_dirs(i):
                return True

            content = self._cached_listdir(i)
            content = list(filter(lambda x: x[1].startswith(lname), content))
            for k in content:
                if search_lib_dirs(os.path.join(i, k[0])):
                    return True

            # Mac framework support
            if machine.is_darwin():
                for j in ['{}.framework', '{}.app']:
                    j = j.format(lname)
                    if j in content:
                        if find_module(os.path.join(i, j[0], 'Resources')) or find_module(os.path.join(i, j[0], 'Version')):
                            return True

        # Check the environment path
        env_path = os.environ.get('{}_DIR'.format(name))
        if env_path and find_module(env_path):
            return True

        return False

    def _detect_dep(self, name: str, modules: T.List[T.Tuple[str, bool]], components: T.List[T.Tuple[str, bool]], args: T.List[str]):
        # Detect a dependency with CMake using the '--find-package' mode
        # and the trace output (stderr)
        #
        # When the trace output is enabled CMake prints all functions with
        # parameters to stderr as they are executed. Since CMake 3.4.0
        # variables ("${VAR}") are also replaced in the trace output.
        mlog.debug('\nDetermining dependency {!r} with CMake executable '
                   '{!r}'.format(name, self.cmakebin.executable_path()))

        # Try different CMake generators since specifying no generator may fail
        # in cygwin for some reason
        gen_list = []
        # First try the last working generator
        if CMakeDependency.class_working_generator is not None:
            gen_list += [CMakeDependency.class_working_generator]
        gen_list += CMakeDependency.class_cmake_generators

        # Map the components
        comp_mapped = self._map_component_list(modules, components)

        for i in gen_list:
            mlog.debug('Try CMake generator: {}'.format(i if len(i) > 0 else 'auto'))

            # Prepare options
            cmake_opts = []
            cmake_opts += ['-DNAME={}'.format(name)]
            cmake_opts += ['-DARCHS={}'.format(';'.join(self.cmakeinfo['archs']))]
            cmake_opts += ['-DCOMPS={}'.format(';'.join([x[0] for x in comp_mapped]))]
            cmake_opts += args
            cmake_opts += self.traceparser.trace_args()
            cmake_opts += self._extra_cmake_opts()
            cmake_opts += ['.']
            if len(i) > 0:
                cmake_opts = ['-G', i] + cmake_opts

            # Run CMake
            ret1, out1, err1 = self._call_cmake(cmake_opts, self._main_cmake_file())

            # Current generator was successful
            if ret1 == 0:
                CMakeDependency.class_working_generator = i
                break

            mlog.debug('CMake failed for generator {} and package {} with error code {}'.format(i, name, ret1))
            mlog.debug('OUT:\n{}\n\n\nERR:\n{}\n\n'.format(out1, err1))

        # Check if any generator succeeded
        if ret1 != 0:
            return

        try:
            self.traceparser.parse(err1)
        except CMakeException as e:
            e = self._gen_exception(str(e))
            if self.required:
                raise
            else:
                self.compile_args = []
                self.link_args = []
                self.is_found = False
                self.reason = e
                return

        # Whether the package is found or not is always stored in PACKAGE_FOUND
        self.is_found = self.traceparser.var_to_bool('PACKAGE_FOUND')
        if not self.is_found:
            return

        # Try to detect the version
        vers_raw = self.traceparser.get_cmake_var('PACKAGE_VERSION')

        if len(vers_raw) > 0:
            self.version = vers_raw[0]
            self.version.strip('"\' ')

        # Post-process module list. Used in derived classes to modify the
        # module list (append prepend a string, etc.).
        modules = self._map_module_list(modules, components)
        autodetected_module_list = False

        # Try guessing a CMake target if none is provided
        if len(modules) == 0:
            for i in self.traceparser.targets:
                tg = i.lower()
                lname = name.lower()
                if '{}::{}'.format(lname, lname) == tg or lname == tg.replace('::', ''):
                    mlog.debug('Guessed CMake target \'{}\''.format(i))
                    modules = [(i, True)]
                    autodetected_module_list = True
                    break

        # Failed to guess a target --> try the old-style method
        if len(modules) == 0:
            incDirs = [x for x in self.traceparser.get_cmake_var('PACKAGE_INCLUDE_DIRS') if x]
            defs = [x for x in self.traceparser.get_cmake_var('PACKAGE_DEFINITIONS') if x]
            libs = [x for x in self.traceparser.get_cmake_var('PACKAGE_LIBRARIES') if x]

            # Try to use old style variables if no module is specified
            if len(libs) > 0:
                self.compile_args = list(map(lambda x: '-I{}'.format(x), incDirs)) + defs
                self.link_args = libs
                mlog.debug('using old-style CMake variables for dependency {}'.format(name))
                mlog.debug('Include Dirs:         {}'.format(incDirs))
                mlog.debug('Compiler Definitions: {}'.format(defs))
                mlog.debug('Libraries:            {}'.format(libs))
                return

            # Even the old-style approach failed. Nothing else we can do here
            self.is_found = False
            raise self._gen_exception('CMake: failed to guess a CMake target for {}.\n'
                                      'Try to explicitly specify one or more targets with the "modules" property.\n'
                                      'Valid targets are:\n{}'.format(name, list(self.traceparser.targets.keys())))

        # Set dependencies with CMake targets
        # recognise arguments we should pass directly to the linker
        reg_is_lib = re.compile(r'^(-l[a-zA-Z0-9_]+|-pthread|-delayload:[a-zA-Z0-9_\.]+|[a-zA-Z0-9_]+\.lib)$')
        reg_is_maybe_bare_lib = re.compile(r'^[a-zA-Z0-9_]+$')
        processed_targets = []
        incDirs = []
        compileDefinitions = []
        compileOptions = []
        libraries = []
        for i, required in modules:
            if i not in self.traceparser.targets:
                if not required:
                    mlog.warning('CMake: T.Optional module', mlog.bold(self._original_module_name(i)), 'for', mlog.bold(name), 'was not found')
                    continue
                raise self._gen_exception('CMake: invalid module {} for {}.\n'
                                          'Try to explicitly specify one or more targets with the "modules" property.\n'
                                          'Valid targets are:\n{}'.format(self._original_module_name(i), name, list(self.traceparser.targets.keys())))

            targets = [i]
            if not autodetected_module_list:
                self.found_modules += [i]

            while len(targets) > 0:
                curr = targets.pop(0)

                # Skip already processed targets
                if curr in processed_targets:
                    continue

                tgt = self.traceparser.targets[curr]
                cfgs = []
                cfg = ''
                otherDeps = []
                mlog.debug(tgt)

                if 'INTERFACE_INCLUDE_DIRECTORIES' in tgt.properties:
                    incDirs += [x for x in tgt.properties['INTERFACE_INCLUDE_DIRECTORIES'] if x]

                if 'INTERFACE_COMPILE_DEFINITIONS' in tgt.properties:
                    compileDefinitions += ['-D' + re.sub('^-D', '', x) for x in tgt.properties['INTERFACE_COMPILE_DEFINITIONS'] if x]

                if 'INTERFACE_COMPILE_OPTIONS' in tgt.properties:
                    compileOptions += [x for x in tgt.properties['INTERFACE_COMPILE_OPTIONS'] if x]

                if 'IMPORTED_CONFIGURATIONS' in tgt.properties:
                    cfgs = [x for x in tgt.properties['IMPORTED_CONFIGURATIONS'] if x]
                    cfg = cfgs[0]

                is_debug = self.env.coredata.get_builtin_option('debug');
                if is_debug:
                    if 'DEBUG' in cfgs:
                        cfg = 'DEBUG'
                    elif 'RELEASE' in cfgs:
                        cfg = 'RELEASE'
                else:
                    if 'RELEASE' in cfgs:
                        cfg = 'RELEASE'

                if 'IMPORTED_IMPLIB_{}'.format(cfg) in tgt.properties:
                    libraries += [x for x in tgt.properties['IMPORTED_IMPLIB_{}'.format(cfg)] if x]
                elif 'IMPORTED_IMPLIB' in tgt.properties:
                    libraries += [x for x in tgt.properties['IMPORTED_IMPLIB'] if x]
                elif 'IMPORTED_LOCATION_{}'.format(cfg) in tgt.properties:
                    libraries += [x for x in tgt.properties['IMPORTED_LOCATION_{}'.format(cfg)] if x]
                elif 'IMPORTED_LOCATION' in tgt.properties:
                    libraries += [x for x in tgt.properties['IMPORTED_LOCATION'] if x]

                if 'INTERFACE_LINK_LIBRARIES' in tgt.properties:
                    otherDeps += [x for x in tgt.properties['INTERFACE_LINK_LIBRARIES'] if x]

                if 'IMPORTED_LINK_DEPENDENT_LIBRARIES_{}'.format(cfg) in tgt.properties:
                    otherDeps += [x for x in tgt.properties['IMPORTED_LINK_DEPENDENT_LIBRARIES_{}'.format(cfg)] if x]
                elif 'IMPORTED_LINK_DEPENDENT_LIBRARIES' in tgt.properties:
                    otherDeps += [x for x in tgt.properties['IMPORTED_LINK_DEPENDENT_LIBRARIES'] if x]

                for j in otherDeps:
                    if j in self.traceparser.targets:
                        targets += [j]
                    elif reg_is_lib.match(j):
                        libraries += [j]
                    elif os.path.isabs(j) and os.path.exists(j):
                        libraries += [j]
                    elif mesonlib.is_windows() and reg_is_maybe_bare_lib.match(j):
                        # On Windows, CMake library dependencies can be passed as bare library names,
                        # e.g. 'version' should translate into 'version.lib'. CMake brute-forces a
                        # combination of prefix/suffix combinations to find the right library, however
                        # as we do not have a compiler environment available to us, we cannot do the
                        # same, but must assume any bare argument passed which is not also a CMake
                        # target must be a system library we should try to link against
                        libraries += ["{}.lib".format(j)]
                    else:
                        mlog.warning('CMake: Dependency', mlog.bold(j), 'for', mlog.bold(name), 'target', mlog.bold(self._original_module_name(curr)), 'was not found')

                processed_targets += [curr]

        # Make sure all elements in the lists are unique and sorted
        incDirs = sorted(set(incDirs))
        compileDefinitions = sorted(set(compileDefinitions))
        compileOptions = sorted(set(compileOptions))
        libraries = sorted(set(libraries))

        mlog.debug('Include Dirs:         {}'.format(incDirs))
        mlog.debug('Compiler Definitions: {}'.format(compileDefinitions))
        mlog.debug('Compiler Options:     {}'.format(compileOptions))
        mlog.debug('Libraries:            {}'.format(libraries))

        self.compile_args = compileOptions + compileDefinitions + ['-I{}'.format(x) for x in incDirs]
        self.link_args = libraries

    def _get_build_dir(self) -> str:
        build_dir = Path(self.cmake_root_dir) / 'cmake_{}'.format(self.name)
        build_dir.mkdir(parents=True, exist_ok=True)
        return str(build_dir)

    def _setup_cmake_dir(self, cmake_file: str) -> str:
        # Setup the CMake build environment and return the "build" directory
        build_dir = self._get_build_dir()

        # Insert language parameters into the CMakeLists.txt and write new CMakeLists.txt
        # Per the warning in pkg_resources, this is *not* a path and os.path and Pathlib are *not* safe to use here.
        cmake_txt = pkg_resources.resource_string('mesonbuild', 'dependencies/data/' + cmake_file).decode()

        # In general, some Fortran CMake find_package() also require C language enabled,
        # even if nothing from C is directly used. An easy Fortran example that fails
        # without C language is
        #   find_package(Threads)
        # To make this general to
        # any other language that might need this, we use a list for all
        # languages and expand in the cmake Project(... LANGUAGES ...) statement.
        from ..cmake import language_map
        cmake_language = [language_map[x] for x in self.language_list if x in language_map]
        if not cmake_language:
            cmake_language += ['NONE']

        cmake_txt = """
cmake_minimum_required(VERSION ${{CMAKE_VERSION}})
project(MesonTemp LANGUAGES {})
""".format(' '.join(cmake_language)) + cmake_txt

        cm_file = Path(build_dir) / 'CMakeLists.txt'
        cm_file.write_text(cmake_txt)
        mlog.cmd_ci_include(cm_file.absolute().as_posix())

        return build_dir

    def _call_cmake(self, args, cmake_file: str, env=None):
        build_dir = self._setup_cmake_dir(cmake_file)
        return self.cmakebin.call_with_fake_build(args, build_dir, env=env)

    @staticmethod
    def get_methods():
        return [DependencyMethods.CMAKE]

    def log_tried(self):
        return self.type_name

    def log_details(self) -> str:
        modules = [self._original_module_name(x) for x in self.found_modules]
        modules = sorted(set(modules))
        if modules:
            return 'modules: ' + ', '.join(modules)
        return ''

    def get_variable(self, *, cmake: T.Optional[str] = None, pkgconfig: T.Optional[str] = None,
                     configtool: T.Optional[str] = None, internal: T.Optional[str] = None,
                     default_value: T.Optional[str] = None,
                     pkgconfig_define: T.Optional[T.List[str]] = None) -> T.Union[str, T.List[str]]:
        if cmake and self.traceparser is not None:
            try:
                v = self.traceparser.vars[cmake]
            except KeyError:
                pass
            else:
                if len(v) == 1:
                    return v[0]
                elif v:
                    return v
        if default_value is not None:
            return default_value
        raise DependencyException('Could not get cmake variable and no default provided for {!r}'.format(self))

class DubDependency(ExternalDependency):
    class_dubbin = None

    def __init__(self, name, environment, kwargs):
        super().__init__('dub', environment, kwargs, language='d')
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
                    if package['targetType'] in ['library', 'sourceLibrary', 'staticLibrary', 'dynamicLibrary']:
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
                        if os.name != 'nt':
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

        # If default_path is a path to lib file and
        # directory of lib don't have subdir '.dub/build'
        if not os.path.isdir(module_build_path) and os.path.isfile(default_path):
            if folder_only:
                return module_path
            else:
                return default_path

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
        build_name = '-{}-{}-{}-{}_{}'.format(description['buildType'], '.'.join(description['platform']), '.'.join(description['architecture']), comp, d_ver)
        for entry in os.listdir(module_build_path):
            if build_name in entry:
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
    # An 'ExternalProgram' always runs on the build machine
    for_machine = MachineChoice.BUILD

    def __init__(self, name: str, command: T.Optional[T.List[str]] = None,
                 silent: bool = False, search_dir: T.Optional[str] = None,
                 extra_search_dirs: T.Optional[T.List[str]] = None):
        self.name = name
        if command is not None:
            self.command = listify(command)
            if mesonlib.is_windows():
                cmd = self.command[0]
                args = self.command[1:]
                self.command = self._search_windows_special_cases(name, cmd) + args
        else:
            all_search_dirs = [search_dir]
            if extra_search_dirs:
                all_search_dirs += extra_search_dirs
            for d in all_search_dirs:
                self.command = self._search(name, d)
                if self.found():
                    break

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
            # ignore the warning because derived classes never call this __init__
            # method, and thus only the found() method of this class is ever executed
            if self.found():  # lgtm [py/init-calls-subclass]
                mlog.log('Program', mlog.bold(name), 'found:', mlog.green('YES'),
                         '(%s)' % ' '.join(self.command))
            else:
                mlog.log('Program', mlog.bold(name), 'found:', mlog.red('NO'))

    def __repr__(self) -> str:
        r = '<{} {!r} -> {!r}>'
        return r.format(self.__class__.__name__, self.name, self.command)

    def description(self) -> str:
        '''Human friendly description of the command'''
        return ' '.join(self.command)

    @classmethod
    def from_bin_list(cls, env: Environment, for_machine: MachineChoice, name):
        # There is a static `for_machine` for this class because the binary
        # aways runs on the build platform. (It's host platform is our build
        # platform.) But some external programs have a target platform, so this
        # is what we are specifying here.
        command = env.lookup_binary_entry(for_machine, name)
        if command is None:
            return NonExistingExternalProgram()
        return cls.from_entry(name, command)

    @staticmethod
    @functools.lru_cache(maxsize=None)
    def _windows_sanitize_path(path: str) -> str:
        # Ensure that we use USERPROFILE even when inside MSYS, MSYS2, Cygwin, etc.
        if 'USERPROFILE' not in os.environ:
            return path
        # The WindowsApps directory is a bit of a problem. It contains
        # some zero-sized .exe files which have "reparse points", that
        # might either launch an installed application, or might open
        # a page in the Windows Store to download the application.
        #
        # To handle the case where the python interpreter we're
        # running on came from the Windows Store, if we see the
        # WindowsApps path in the search path, replace it with
        # dirname(sys.executable).
        appstore_dir = Path(os.environ['USERPROFILE']) / 'AppData' / 'Local' / 'Microsoft' / 'WindowsApps'
        paths = []
        for each in path.split(os.pathsep):
            if Path(each) != appstore_dir:
                paths.append(each)
            elif 'WindowsApps' in sys.executable:
                paths.append(os.path.dirname(sys.executable))
        return os.pathsep.join(paths)

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
                else:
                    # Replace python3 with the actual python3 that we are using
                    if commands[0] == '/usr/bin/env' and commands[1] == 'python3':
                        commands = mesonlib.python_command + commands[2:]
                    elif commands[0].split('/')[-1] == 'python3':
                        commands = mesonlib.python_command + commands[1:]
                return commands + [script]
        except Exception as e:
            mlog.debug(e)
        mlog.debug('Unusable script {!r}'.format(script))
        return False

    def _is_executable(self, path):
        suffix = os.path.splitext(path)[-1].lower()[1:]
        execmask = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        if mesonlib.is_windows():
            if suffix in self.windows_exts:
                return True
        elif os.stat(path).st_mode & execmask:
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
        search_dirs = self._windows_sanitize_path(os.environ.get('PATH', '')).split(';')
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
        path = os.environ.get('PATH', None)
        if mesonlib.is_windows() and path:
            path = self._windows_sanitize_path(path)
        command = shutil.which(name, path=path)
        if mesonlib.is_windows():
            return self._search_windows_special_cases(name, command)
        # On UNIX-like platforms, shutil.which() is enough to find
        # all executables whether in PATH or with an absolute path
        return [command]

    def found(self) -> bool:
        return self.command[0] is not None

    def get_command(self):
        return self.command[:]

    def get_path(self):
        return self.path

    def get_name(self):
        return self.name


class NonExistingExternalProgram(ExternalProgram):  # lgtm [py/missing-call-to-init]
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


class EmptyExternalProgram(ExternalProgram):  # lgtm [py/missing-call-to-init]
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
        super().__init__('library', environment, {}, language=language)
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

    def get_partial_dependency(self, *, compile_args: bool = False,
                               link_args: bool = False, links: bool = False,
                               includes: bool = False, sources: bool = False):
        # External library only has link_args, so ignore the rest of the
        # interface.
        new = copy.copy(self)
        if not link_args:
            new.link_args = []
        return new


class ExtraFrameworkDependency(ExternalDependency):
    system_framework_paths = None

    def __init__(self, name, env, kwargs, language: T.Optional[str] = None):
        paths = kwargs.get('paths', [])
        super().__init__('extraframeworks', env, kwargs, language=language)
        self.name = name
        # Full path to framework directory
        self.framework_path = None
        if not self.clib_compiler:
            raise DependencyException('No C-like compilers are available')
        if self.system_framework_paths is None:
            try:
                self.system_framework_paths = self.clib_compiler.find_framework_paths(self.env)
            except MesonException as e:
                if 'non-clang' in str(e):
                    # Apple frameworks can only be found (and used) with the
                    # system compiler. It is not available so bail immediately.
                    self.is_found = False
                    return
                raise
        self.detect(name, paths)

    def detect(self, name, paths):
        if not paths:
            paths = self.system_framework_paths
        for p in paths:
            mlog.debug('Looking for framework {} in {}'.format(name, p))
            # We need to know the exact framework path because it's used by the
            # Qt5 dependency class, and for setting the include path. We also
            # want to avoid searching in an invalid framework path which wastes
            # time and can cause a false positive.
            framework_path = self._get_framework_path(p, name)
            if framework_path is None:
                continue
            # We want to prefer the specified paths (in order) over the system
            # paths since these are "extra" frameworks.
            # For example, Python2's framework is in /System/Library/Frameworks and
            # Python3's framework is in /Library/Frameworks, but both are called
            # Python.framework. We need to know for sure that the framework was
            # found in the path we expect.
            allow_system = p in self.system_framework_paths
            args = self.clib_compiler.find_framework(name, self.env, [p], allow_system)
            if args is None:
                continue
            self.link_args = args
            self.framework_path = framework_path.as_posix()
            self.compile_args = ['-F' + self.framework_path]
            # We need to also add -I includes to the framework because all
            # cross-platform projects such as OpenGL, Python, Qt, GStreamer,
            # etc do not use "framework includes":
            # https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPFrameworks/Tasks/IncludingFrameworks.html
            incdir = self._get_framework_include_path(framework_path)
            if incdir:
                self.compile_args += ['-I' + incdir]
            self.is_found = True
            return

    def _get_framework_path(self, path, name):
        p = Path(path)
        lname = name.lower()
        for d in p.glob('*.framework/'):
            if lname == d.name.rsplit('.', 1)[0].lower():
                return d
        return None

    def _get_framework_latest_version(self, path):
        versions = []
        for each in path.glob('Versions/*'):
            # macOS filesystems are usually case-insensitive
            if each.name.lower() == 'current':
                continue
            versions.append(Version(each.name))
        if len(versions) == 0:
            # most system frameworks do not have a 'Versions' directory
            return 'Headers'
        return 'Versions/{}/Headers'.format(sorted(versions)[-1]._s)

    def _get_framework_include_path(self, path):
        # According to the spec, 'Headers' must always be a symlink to the
        # Headers directory inside the currently-selected version of the
        # framework, but sometimes frameworks are broken. Look in 'Versions'
        # for the currently-selected version or pick the latest one.
        trials = ('Headers', 'Versions/Current/Headers',
                  self._get_framework_latest_version(path))
        for each in trials:
            trial = path / each
            if trial.is_dir():
                return trial.as_posix()
        return None

    @staticmethod
    def get_methods():
        return [DependencyMethods.EXTRAFRAMEWORK]

    def log_info(self):
        return self.framework_path

    def log_tried(self):
        return 'framework'


class DependencyFactory:

    """Factory to get dependencies from multiple sources.

    This class provides an initializer that takes a set of names and classes
    for various kinds of dependencies. When the initialized object is called
    it returns a list of callables return Dependency objects to try in order.

    :name: The name of the dependency. This will be passed as the name
        parameter of the each dependency unless it is overridden on a per
        type basis.
    :methods: An ordered list of DependencyMethods. This is the order
        dependencies will be returned in unless they are removed by the
        _process_method function
    :*_name: This will overwrite the name passed to the coresponding class.
        For example, if the name is 'zlib', but cmake calls the dependency
        'Z', then using `cmake_name='Z'` will pass the name as 'Z' to cmake.
    :*_class: A *type* or callable that creates a class, and has the
        signature of an ExternalDependency
    :system_class: If you pass DependencyMethods.SYSTEM in methods, you must
        set this argument.
    """

    def __init__(self, name: str, methods: T.List[DependencyMethods], *,
                 extra_kwargs: T.Optional[T.Dict[str, T.Any]] = None,
                 pkgconfig_name: T.Optional[str] = None,
                 pkgconfig_class: 'T.Type[PkgConfigDependency]' = PkgConfigDependency,
                 cmake_name: T.Optional[str] = None,
                 cmake_class: 'T.Type[CMakeDependency]' = CMakeDependency,
                 configtool_class: 'T.Optional[T.Type[ConfigToolDependency]]' = None,
                 framework_name: T.Optional[str] = None,
                 framework_class: 'T.Type[ExtraFrameworkDependency]' = ExtraFrameworkDependency,
                 system_class: 'T.Type[ExternalDependency]' = ExternalDependency):

        if DependencyMethods.CONFIG_TOOL in methods and not configtool_class:
            raise DependencyException('A configtool must have a custom class')

        self.extra_kwargs = extra_kwargs or {}
        self.methods = methods
        self.classes = {
            # Just attach the correct name right now, either the generic name
            # or the method specific name.
            DependencyMethods.EXTRAFRAMEWORK: functools.partial(framework_class, framework_name or name),
            DependencyMethods.PKGCONFIG: functools.partial(pkgconfig_class, pkgconfig_name or name),
            DependencyMethods.CMAKE: functools.partial(cmake_class, cmake_name or name),
            DependencyMethods.SYSTEM: functools.partial(system_class, name),
            DependencyMethods.CONFIG_TOOL: None,
        }
        if configtool_class is not None:
            self.classes[DependencyMethods.CONFIG_TOOL] = functools.partial(configtool_class, name)

    @staticmethod
    def _process_method(method: DependencyMethods, env: Environment, for_machine: MachineChoice) -> bool:
        """Report whether a method is valid or not.

        If the method is valid, return true, otherwise return false. This is
        used in a list comprehension to filter methods that are not possible.

        By default this only remove EXTRAFRAMEWORK dependencies for non-mac platforms.
        """
        # Extra frameworks are only valid for macOS and other apple products
        if (method is DependencyMethods.EXTRAFRAMEWORK and
                not env.machines[for_machine].is_darwin()):
            return False
        return True

    def __call__(self, env: Environment, for_machine: MachineChoice,
                 kwargs: T.Dict[str, T.Any]) -> T.List['DependencyType']:
        """Return a list of Dependencies with the arguments already attached."""
        methods = process_method_kw(self.methods, kwargs)
        nwargs = self.extra_kwargs.copy()
        nwargs.update(kwargs)

        return [functools.partial(self.classes[m], env, nwargs) for m in methods
                if self._process_method(m, env, for_machine)]


def get_dep_identifier(name, kwargs) -> T.Tuple:
    identifier = (name, )
    for key, value in kwargs.items():
        # 'version' is irrelevant for caching; the caller must check version matches
        # 'native' is handled above with `for_machine`
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
    'cuda': 'CUDA',
    'dub': 'DUB',
    'gmock': 'GMock',
    'gtest': 'GTest',
    'hdf5': 'HDF5',
    'llvm': 'LLVM',
    'mpi': 'MPI',
    'netcdf': 'NetCDF',
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

    for_machine = MachineChoice.BUILD if kwargs.get('native', False) else MachineChoice.HOST

    type_text = PerMachine('Build-time', 'Run-time')[for_machine] + ' dependency'

    # build a list of dependency methods to try
    candidates = _build_external_dependency_list(name, env, for_machine, kwargs)

    pkg_exc = []
    pkgdep = []
    details = ''

    for c in candidates:
        # try this dependency method
        try:
            d = c()
            d._check_version()
            pkgdep.append(d)
        except DependencyException as e:
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
                    info.append(mlog.normal_cyan(d.version))

                log_info = d.log_info()
                if log_info:
                    info.append('(' + log_info + ')')

                mlog.log(type_text, mlog.bold(display_name), details + 'found:', mlog.green('YES'), *info)

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
        if pkg_exc and pkg_exc[0]:
            raise pkg_exc[0]

        # we have a list of failed ExternalDependency objects, so we can report
        # the methods we tried to find the dependency
        raise DependencyException('Dependency "%s" not found' % (name) +
                                  (', tried %s' % (tried) if tried else ''))

    return NotFoundDependency(env)


def _build_external_dependency_list(name: str, env: Environment, for_machine: MachineChoice,
                                    kwargs: T.Dict[str, T.Any]) -> T.List['DependencyType']:
    # First check if the method is valid
    if 'method' in kwargs and kwargs['method'] not in [e.value for e in DependencyMethods]:
        raise DependencyException('method {!r} is invalid'.format(kwargs['method']))

    # Is there a specific dependency detector for this dependency?
    lname = name.lower()
    if lname in packages:
        # Create the list of dependency object constructors using a factory
        # class method, if one exists, otherwise the list just consists of the
        # constructor
        if isinstance(packages[lname], type) and issubclass(packages[lname], Dependency):
            dep = [functools.partial(packages[lname], env, kwargs)]
        else:
            dep = packages[lname](env, for_machine, kwargs)
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

    # If it's explicitly requested, use the Extraframework detection method (only)
    if 'extraframework' == kwargs.get('method', ''):
        # On OSX, also try framework dependency detector
        if mesonlib.is_osx():
            candidates.append(functools.partial(ExtraFrameworkDependency, name, env, kwargs))
        return candidates

    # Otherwise, just use the pkgconfig and cmake dependency detector
    if 'auto' == kwargs.get('method', 'auto'):
        candidates.append(functools.partial(PkgConfigDependency, name, env, kwargs))

        # On OSX, also try framework dependency detector
        if mesonlib.is_osx():
            candidates.append(functools.partial(ExtraFrameworkDependency, name, env, kwargs))

        # Only use CMake as a last resort, since it might not work 100% (see #6113)
        candidates.append(functools.partial(CMakeDependency, name, env, kwargs))

    return candidates


def sort_libpaths(libpaths: T.List[str], refpaths: T.List[str]) -> T.List[str]:
    """Sort <libpaths> according to <refpaths>

    It is intended to be used to sort -L flags returned by pkg-config.
    Pkg-config returns flags in random order which cannot be relied on.
    """
    if len(refpaths) == 0:
        return list(libpaths)

    def key_func(libpath):
        common_lengths = []
        for refpath in refpaths:
            try:
                common_path = os.path.commonpath([libpath, refpath])
            except ValueError:
                common_path = ''
            common_lengths.append(len(common_path))
        max_length = max(common_lengths)
        max_index = common_lengths.index(max_length)
        reversed_max_length = len(refpaths[max_index]) - max_length
        return (max_index, reversed_max_length)
    return sorted(libpaths, key=key_func)


def strip_system_libdirs(environment, for_machine: MachineChoice, link_args):
    """Remove -L<system path> arguments.

    leaving these in will break builds where a user has a version of a library
    in the system path, and a different version not in the system path if they
    want to link against the non-system path version.
    """
    exclude = {'-L{}'.format(p) for p in environment.get_compiler_system_dirs(for_machine)}
    return [l for l in link_args if l not in exclude]


def process_method_kw(possible: T.List[DependencyMethods], kwargs) -> T.List[DependencyMethods]:
    method = kwargs.get('method', 'auto')
    if isinstance(method, DependencyMethods):
        return method
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
        methods = possible
    elif method in possible:
        methods = [method]
    else:
        raise DependencyException(
            'Unsupported detection method: {}, allowed methods are {}'.format(
                method.value,
                mlog.format_list([x.value for x in [DependencyMethods.AUTO] + possible])))

    return methods


if T.TYPE_CHECKING:
    FactoryType = T.Callable[[Environment, MachineChoice, T.Dict[str, T.Any]],
                             T.List['DependencyType']]
    FullFactoryType = T.Callable[[Environment, MachineChoice, T.Dict[str, T.Any], T.Set[DependencyMethods]],
                                 T.List['DependencyType']]


def factory_methods(methods: T.Set[DependencyMethods]) -> 'FactoryType':
    """Decorator for handling methods for dependency factory functions.

    This helps to make factory functions self documenting
    >>> @factory_methods([DependencyMethods.PKGCONFIG, DependencyMethods.CMAKE])
    >>> def factory(env: Environment, for_machine: MachineChoice, kwargs: T.Dict[str, T.Any], methods: T.Set[DependencyMethods]) -> T.List[DependencyType]:
    >>>     pass
    """

    def inner(func: 'FullFactoryType') -> 'FactoryType':

        @functools.wraps(func)
        def wrapped(env: Environment, for_machine: MachineChoice, kwargs: T.Dict[str, T.Any]) -> T.List['DependencyType']:
            return func(env, for_machine, kwargs, process_method_kw(methods, kwargs))

        return wrapped

    return inner


def detect_compiler(name: str, env: Environment, for_machine: MachineChoice,
                    language: T.Optional[str]) -> T.Optional['CompilerType']:
    """Given a language and environment find the compiler used."""
    compilers = env.coredata.compilers[for_machine]

    # Set the compiler for this dependency if a language is specified,
    # else try to pick something that looks usable.
    if language:
        if language not in compilers:
            m = name.capitalize() + ' requires a {0} compiler, but ' \
                '{0} is not in the list of project languages'
            raise DependencyException(m.format(language.capitalize()))
        return compilers[language]
    else:
        for lang in clib_langs:
            try:
                return compilers[lang]
            except KeyError:
                continue
    return None
