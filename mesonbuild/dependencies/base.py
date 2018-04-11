# Copyright 2013-2017 The Meson development team

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

import os
import re
import stat
import shlex
import shutil
import textwrap
from enum import Enum
from pathlib import PurePath

from .. import mlog
from .. import mesonlib
from ..mesonlib import (
    MesonException, Popen_safe, version_compare_many, version_compare, listify
)


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
    # Just specify the standard link arguments, assuming the operating system provides the library.
    SYSTEM = 'system'
    # This is only supported on OSX - search the frameworks directory by name.
    EXTRAFRAMEWORK = 'extraframework'
    # Detect using the sysconfig module.
    SYSCONFIG = 'sysconfig'
    # Specify using a "program"-config style tool
    CONFIG_TOOL = 'config-tool'
    # For backewards compatibility
    SDLCONFIG = 'sdlconfig'
    CUPSCONFIG = 'cups-config'
    PCAPCONFIG = 'pcap-config'
    LIBWMFCONFIG = 'libwmf-config'


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
        self.version = 'none'
        self.language = None # None means C-like
        self.is_found = False
        self.type_name = type_name
        self.compile_args = []
        self.link_args = []
        self.sources = []
        self.methods = self._process_method_kw(kwargs)

    def __repr__(self):
        s = '<{0} {1}: {2}>'
        return s.format(self.__class__.__name__, self.name, self.is_found)

    def get_compile_args(self):
        return self.compile_args

    def get_link_args(self):
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
        return self.version

    def get_exe_args(self, compiler):
        return []

    def need_threads(self):
        return False

    def get_pkgconfig_variable(self, variable_name, kwargs):
        raise DependencyException('{!r} is not a pkgconfig dependency'.format(self.name))

    def get_configtool_variable(self, variable_name):
        raise DependencyException('{!r} is not a config-tool dependency'.format(self.name))


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


class ExternalDependency(Dependency):
    def __init__(self, type_name, environment, language, kwargs):
        super().__init__(type_name, kwargs)
        self.env = environment
        self.name = type_name # default
        self.is_found = False
        self.language = language
        self.version_reqs = kwargs.get('version', None)
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
                m = self.name.capitalize() + ' requires a {} compiler'
                raise DependencyException(m.format(self.language.capitalize()))
            self.compiler = compilers[self.language]
        else:
            # Try to find a compiler that this dependency can use for compiler
            # checks. It's ok if we don't find one.
            for lang in ('c', 'cpp', 'objc', 'objcpp', 'fortran', 'd'):
                self.compiler = compilers.get(lang, None)
                if self.compiler:
                    break

    def get_compiler(self):
        return self.compiler


class NotFoundDependency(Dependency):
    def __init__(self, environment):
        super().__init__('not-found', {})
        self.env = environment
        self.name = 'not-found'
        self.is_found = False


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

    def _sanitize_version(self, version):
        """Remove any non-numeric, non-point version suffixes."""
        m = self.__strip_version.match(version)
        if m:
            # Ensure that there isn't a trailing '.', such as an input like
            # `1.2.3.git-1234`
            return m.group(0).rstrip('.')
        return version

    @classmethod
    def factory(cls, name, environment, language, kwargs, tools, tool_name):
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
                   {'tools': tools, 'tool_name': tool_name, '__reduce__': reduce})

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

        if self.env.is_cross_build() and not self.native:
            cross_file = self.env.cross_info.config['binaries']
            try:
                tools = [cross_file[self.tool_name]]
            except KeyError:
                mlog.warning('No entry for {0} specified in your cross file. '
                             'Falling back to searching PATH. This may find a '
                             'native version of {0}!'.format(self.tool_name))
                tools = self.tools
        else:
            tools = self.tools

        best_match = (None, None)
        for tool in tools:
            try:
                p, out = Popen_safe([tool, '--version'])[:2]
            except (FileNotFoundError, PermissionError):
                continue
            if p.returncode != 0:
                continue

            out = self._sanitize_version(out.strip())
            # Some tools, like pcap-config don't supply a version, but also
            # don't fail with --version, in that case just assume that there is
            # only one version and return it.
            if not out:
                return (tool, 'none')
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
        if self.config is None:
            if version is not None:
                mlog.log('Found', mlog.bold(self.tool_name), repr(version),
                         mlog.red('NO'), '(needed', req_version, ')')
            else:
                mlog.log('Found', mlog.bold(self.tool_name), repr(req_version),
                         mlog.red('NO'))
            mlog.log('Dependency', mlog.bold(self.name), 'found:', mlog.red('NO'))
            if self.required:
                raise DependencyException('Dependency {} not found'.format(self.name))
            return False
        mlog.log('Found {}:'.format(self.tool_name), mlog.bold(shutil.which(self.config)),
                 '({})'.format(version))
        mlog.log('Dependency', mlog.bold(self.name), 'found:', mlog.green('YES'))
        return True

    def get_config_value(self, args, stage):
        p, out, err = Popen_safe([self.config] + args)
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
        p, out, _ = Popen_safe([self.config, '--{}'.format(variable_name)])
        if p.returncode != 0:
            if self.required:
                raise DependencyException(
                    'Could not get variable "{}" for dependency {}'.format(
                        variable_name, self.name))
        variable = out.strip()
        mlog.debug('Got config-tool variable {} : {}'.format(variable_name, variable))
        return variable


class PkgConfigDependency(ExternalDependency):
    # The class's copy of the pkg-config path. Avoids having to search for it
    # multiple times in the same Meson invocation.
    class_pkgbin = None

    def __init__(self, name, environment, kwargs, language=None):
        super().__init__('pkgconfig', environment, language, kwargs)
        self.name = name
        self.is_libtool = False
        # Store a copy of the pkg-config path on the object itself so it is
        # stored in the pickled coredata and recovered.
        self.pkgbin = None

        # When finding dependencies for cross-compiling, we don't care about
        # the 'native' pkg-config
        if self.want_cross:
            if 'pkgconfig' not in environment.cross_info.config['binaries']:
                if self.required:
                    raise DependencyException('Pkg-config binary missing from cross file')
            else:
                pkgname = environment.cross_info.config['binaries']['pkgconfig']
                potential_pkgbin = ExternalProgram(pkgname, silent=True)
                if potential_pkgbin.found():
                    self.pkgbin = potential_pkgbin
                    PkgConfigDependency.class_pkgbin = self.pkgbin
                else:
                    mlog.debug('Cross pkg-config %s not found.' % potential_pkgbin.name)
        # Only search for the native pkg-config the first time and
        # store the result in the class definition
        elif PkgConfigDependency.class_pkgbin is None:
            self.pkgbin = self.check_pkgconfig()
            PkgConfigDependency.class_pkgbin = self.pkgbin
        else:
            self.pkgbin = PkgConfigDependency.class_pkgbin

        if not self.pkgbin:
            if self.required:
                raise DependencyException('Pkg-config not found.')
            return
        if self.want_cross:
            self.type_string = 'Cross'
        else:
            self.type_string = 'Native'

        mlog.debug('Determining dependency {!r} with pkg-config executable '
                   '{!r}'.format(name, self.pkgbin.get_path()))
        ret, self.version = self._call_pkgbin(['--modversion', name])
        if ret != 0:
            if self.required:
                raise DependencyException('{} dependency {!r} not found'
                                          ''.format(self.type_string, name))
            return
        found_msg = [self.type_string + ' dependency', mlog.bold(name), 'found:']
        if self.version_reqs is None:
            self.is_found = True
        else:
            if not isinstance(self.version_reqs, (str, list)):
                raise DependencyException('Version argument must be string or list.')
            if isinstance(self.version_reqs, str):
                self.version_reqs = [self.version_reqs]
            (self.is_found, not_found, found) = \
                version_compare_many(self.version, self.version_reqs)
            if not self.is_found:
                found_msg += [mlog.red('NO'),
                              'found {!r} but need:'.format(self.version),
                              ', '.join(["'{}'".format(e) for e in not_found])]
                if found:
                    found_msg += ['; matched:',
                                  ', '.join(["'{}'".format(e) for e in found])]
                if not self.silent:
                    mlog.log(*found_msg)
                if self.required:
                    m = 'Invalid version of dependency, need {!r} {!r} found {!r}.'
                    raise DependencyException(m.format(name, not_found, self.version))
                return

        try:
            # Fetch cargs to be used while using this dependency
            self._set_cargs()
            # Fetch the libraries and library paths needed for using this
            self._set_libs()
            found_msg += [mlog.green('YES'), self.version]
        except DependencyException as e:
            if self.required:
                raise
            else:
                self.compile_args = []
                self.link_args = []
                self.is_found = False
                found_msg += [mlog.red('NO'), '; reason: {}'.format(str(e))]

        # Print the found message only at the very end because fetching cflags
        # and libs can also fail if other needed pkg-config files aren't found.
        if not self.silent:
            mlog.log(*found_msg)

    def __repr__(self):
        s = '<{0} {1}: {2} {3}>'
        return s.format(self.__class__.__name__, self.name, self.is_found,
                        self.version_reqs)

    def _call_pkgbin(self, args, env=None):
        if not env:
            env = os.environ
        p, out = Popen_safe(self.pkgbin.get_command() + args, env=env)[0:2]
        return p.returncode, out.strip()

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
        self.link_args = []
        libpaths = []
        static_libs_notfound = []
        for lib in self._convert_mingw_paths(shlex.split(out)):
            # If we want to use only static libraries, we have to look for the
            # file ourselves instead of depending on the compiler to find it
            # with -lfoo or foo.lib. However, we can only do this if we already
            # have some library paths gathered.
            if self.static:
                if lib.startswith('-L'):
                    libpaths.append(lib[2:])
                    continue
                # FIXME: try to handle .la files in static mode too?
                elif lib.startswith('-l'):
                    args = self.compiler.find_library(lib[2:], self.env, libpaths, libtype='static')
                    if not args or len(args) < 1:
                        if lib in static_libs_notfound:
                            continue
                        mlog.warning('Static library {!r} not found for dependency {!r}, may '
                                     'not be statically linked'.format(lib[2:], self.name))
                        static_libs_notfound.append(lib)
                    else:
                        # Replace -l arg with full path to static library
                        lib = args[0]
            elif lib.endswith(".la"):
                shared_libname = self.extract_libtool_shlib(lib)
                shared_lib = os.path.join(os.path.dirname(lib), shared_libname)
                if not os.path.exists(shared_lib):
                    shared_lib = os.path.join(os.path.dirname(lib), ".libs", shared_libname)

                if not os.path.exists(shared_lib):
                    raise DependencyException('Got a libtools specific "%s" dependencies'
                                              'but we could not compute the actual shared'
                                              'library path' % lib)
                lib = shared_lib
                self.is_libtool = True
            self.link_args.append(lib)
        # Add all -Lbar args if we have -lfoo args in link_args
        if static_libs_notfound:
            # Order of -L flags doesn't matter with ld, but it might with other
            # linkers such as MSVC, so prepend them.
            self.link_args = ['-L' + lp for lp in libpaths] + self.link_args

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
                raise DependencyException('%s dependency %s not found.' %
                                          (self.type_string, self.name))
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

    def check_pkgconfig(self):
        evar = 'PKG_CONFIG'
        if evar in os.environ:
            pkgbin = os.environ[evar].strip()
        else:
            pkgbin = 'pkg-config'
        pkgbin = ExternalProgram(pkgbin, silent=True)
        if pkgbin.found():
            try:
                p, out = Popen_safe(pkgbin.get_command() + ['--version'])[0:2]
                if p.returncode != 0:
                    mlog.warning('Found pkg-config {!r} but couldn\'t run it'
                                 ''.format(' '.join(pkgbin.get_command())))
                    # Set to False instead of None to signify that we've already
                    # searched for it and not found it
                    pkgbin = False
            except (FileNotFoundError, PermissionError):
                pkgbin = False
        else:
            pkgbin = False
        if not self.silent:
            if pkgbin:
                mlog.log('Found pkg-config:', mlog.bold(pkgbin.get_path()),
                         '(%s)' % out.strip())
            else:
                mlog.log('Found Pkg-config:', mlog.red('NO'))
        return pkgbin

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


class ExternalProgram:
    windows_exts = ('exe', 'msc', 'com', 'bat', 'cmd')

    def __init__(self, name, command=None, silent=False, search_dir=None):
        self.name = name
        if command is not None:
            self.command = listify(command)
        else:
            self.command = self._search(name, search_dir)
        if not silent:
            if self.found():
                mlog.log('Program', mlog.bold(name), 'found:', mlog.green('YES'),
                         '(%s)' % ' '.join(self.command))
            else:
                mlog.log('Program', mlog.bold(name), 'found:', mlog.red('NO'))

    def __repr__(self):
        r = '<{} {!r} -> {!r}>'
        return r.format(self.__class__.__name__, self.name, self.command)

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
        if self.found():
            # Assume that the last element is the full path to the script or
            # binary being run
            return self.command[-1]
        return None

    def get_name(self):
        return self.name

class NonExistingExternalProgram(ExternalProgram):

    def __init__(self):
        super().__init__(name = 'nonexistingprogram', silent = True)

    def __repr__(self):
        r = '<{} {!r} -> {!r}>'
        return r.format(self.__class__.__name__, self.name, self.command)

    def found(self):
        return False

class ExternalLibrary(ExternalDependency):
    def __init__(self, name, link_args, environment, language, silent=False):
        super().__init__('external', environment, language, {})
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

    def get_link_args(self, language=None):
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
        return self.link_args


class ExtraFrameworkDependency(ExternalDependency):
    def __init__(self, name, required, path, env, lang, kwargs):
        super().__init__('extraframeworks', env, lang, kwargs)
        self.name = None
        self.required = required
        self.detect(name, path)
        if self.found():
            mlog.log('Dependency', mlog.bold(name), 'found:', mlog.green('YES'),
                     os.path.join(self.path, self.name))
        else:
            mlog.log('Dependency', name, 'found:', mlog.red('NO'))

    def detect(self, name, path):
        lname = name.lower()
        if path is None:
            paths = ['/System/Library/Frameworks', '/Library/Frameworks']
        else:
            paths = [path]
        for p in paths:
            for d in os.listdir(p):
                fullpath = os.path.join(p, d)
                if lname != d.split('.')[0].lower():
                    continue
                if not stat.S_ISDIR(os.stat(fullpath).st_mode):
                    continue
                self.path = p
                self.name = d
                self.is_found = True
                return
        if not self.found() and self.required:
            raise DependencyException('Framework dependency %s not found.' % (name, ))

    def get_compile_args(self):
        if self.found():
            return ['-I' + os.path.join(self.path, self.name, 'Headers')]
        return []

    def get_link_args(self):
        if self.found():
            return ['-F' + self.path, '-framework', self.name.split('.')[0]]
        return []

    def get_version(self):
        return 'unknown'


def get_dep_identifier(name, kwargs, want_cross):
    # Need immutable objects since the identifier will be used as a dict key
    version_reqs = listify(kwargs.get('version', []))
    if isinstance(version_reqs, list):
        version_reqs = frozenset(version_reqs)
    identifier = (name, version_reqs, want_cross)
    for key, value in kwargs.items():
        # 'version' is embedded above as the second element for easy access
        # 'native' is handled above with `want_cross`
        # 'required' is irrelevant for caching; the caller handles it separately
        # 'fallback' subprojects cannot be cached -- they must be initialized
        if key in ('version', 'native', 'required', 'fallback',):
            continue
        # All keyword arguments are strings, ints, or lists (or lists of lists)
        if isinstance(value, list):
            value = frozenset(listify(value))
        identifier += (key, value)
    return identifier


def find_external_dependency(name, env, kwargs):
    required = kwargs.get('required', True)
    if not isinstance(required, bool):
        raise DependencyException('Keyword "required" must be a boolean.')
    if not isinstance(kwargs.get('method', ''), str):
        raise DependencyException('Keyword "method" must be a string.')
    lname = name.lower()
    if lname in packages:
        if lname not in _packages_accept_language and 'language' in kwargs:
            raise DependencyException('%s dependency does not accept "language" keyword argument' % (lname, ))
        # Create the dependency object using a factory class method, if one
        # exists, otherwise it is just constructed directly.
        if getattr(packages[lname], '_factory', None):
            dep = packages[lname]._factory(env, kwargs)
        else:
            dep = packages[lname](env, kwargs)
        if required and not dep.found():
            raise DependencyException('Dependency "%s" not found' % name)
        return dep
    if 'language' in kwargs:
        # Remove check when PkgConfigDependency supports language.
        raise DependencyException('%s dependency does not accept "language" keyword argument' % (lname, ))
    pkg_exc = None
    pkgdep = None
    try:
        pkgdep = PkgConfigDependency(name, env, kwargs)
        if pkgdep.found():
            return pkgdep
    except Exception as e:
        pkg_exc = e
    if mesonlib.is_osx():
        fwdep = ExtraFrameworkDependency(name, False, None, env, None, kwargs)
        if required and not fwdep.found():
            m = 'Dependency {!r} not found, tried Extra Frameworks ' \
                'and Pkg-Config:\n\n' + str(pkg_exc)
            raise DependencyException(m.format(name))
        return fwdep
    if pkg_exc is not None:
        raise pkg_exc
    mlog.log('Dependency', mlog.bold(name), 'found:', mlog.red('NO'))
    return pkgdep


def strip_system_libdirs(environment, link_args):
    """Remove -L<system path> arguments.

    leaving these in will break builds where a user has a version of a library
    in the system path, and a different version not in the system path if they
    want to link against the non-system path version.
    """
    exclude = {'-L{}'.format(p) for p in environment.get_compiler_system_dirs()}
    return [l for l in link_args if l not in exclude]
