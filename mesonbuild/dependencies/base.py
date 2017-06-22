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
import shutil
import stat
import sys
from enum import Enum

from .. import mlog
from .. import mesonlib
from ..mesonlib import MesonException, Popen_safe, flatten, version_compare_many


# This must be defined in this file to avoid cyclical references.
packages = {}


class DependencyException(MesonException):
    '''Exceptions raised while trying to find dependencies'''


class DependencyMethods(Enum):
    # Auto means to use whatever dependency checking mechanisms in whatever order meson thinks is best.
    AUTO = 'auto'
    PKGCONFIG = 'pkg-config'
    QMAKE = 'qmake'
    # Just specify the standard link arguments, assuming the operating system provides the library.
    SYSTEM = 'system'
    # Detect using sdl2-config
    SDLCONFIG = 'sdlconfig'
    # This is only supported on OSX - search the frameworks directory by name.
    EXTRAFRAMEWORK = 'extraframework'
    # Detect using the sysconfig module.
    SYSCONFIG = 'sysconfig'


class Dependency:
    def __init__(self, type_name, kwargs):
        self.name = "null"
        self.version = 'none'
        self.language = None # None means C-like
        self.is_found = False
        self.type_name = type_name
        self.compile_args = []
        self.link_args = []
        self.sources = []
        method = kwargs.get('method', 'auto')
        if method not in [e.value for e in DependencyMethods]:
            raise DependencyException('method {!r} is invalid'.format(method))
        method = DependencyMethods(method)

        # Set the detection method. If the method is set to auto, use any available method.
        # If method is set to a specific string, allow only that detection method.
        if method == DependencyMethods.AUTO:
            self.methods = self.get_methods()
        elif method in self.get_methods():
            self.methods = [method]
        else:
            raise DependencyException(
                'Unsupported detection method: {}, allowed methods are {}'.format(
                    method.value,
                    mlog.format_list(map(lambda x: x.value, [DependencyMethods.AUTO] + self.get_methods()))))

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

    def get_methods(self):
        return [DependencyMethods.AUTO]

    def get_name(self):
        return self.name

    def get_version(self):
        return self.version

    def get_exe_args(self, compiler):
        return []

    def need_threads(self):
        return False

    def get_pkgconfig_variable(self, variable_name):
        raise NotImplementedError('{!r} is not a pkgconfig dependency'.format(self.name))


class InternalDependency(Dependency):
    def __init__(self, version, incdirs, compile_args, link_args, libraries, sources, ext_deps):
        super().__init__('internal', {})
        self.version = version
        self.is_found = True
        self.include_directories = incdirs
        self.compile_args = compile_args
        self.link_args = link_args
        self.libraries = libraries
        self.sources = sources
        self.ext_deps = ext_deps


class ExternalDependency(Dependency):
    def __init__(self, type_name, environment, language, kwargs):
        super().__init__(type_name, kwargs)
        self.env = environment
        self.name = type_name # default
        self.is_found = False
        self.language = language
        if language and language not in self.env.coredata.compilers:
            m = self.name.capitalize() + ' requires a {} compiler'
            raise DependencyException(m.format(language.capitalize()))
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
        self.compiler = compilers.get(self.language or 'c', None)

    def get_compiler(self):
        return self.compiler


class PkgConfigDependency(ExternalDependency):
    # The class's copy of the pkg-config path. Avoids having to search for it
    # multiple times in the same Meson invocation.
    class_pkgbin = None

    def __init__(self, name, environment, kwargs):
        super().__init__('pkgconfig', environment, None, kwargs)
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
                    # FIXME, we should store all pkg-configs in ExternalPrograms.
                    # However that is too destabilizing a change to do just before release.
                    self.pkgbin = potential_pkgbin.get_command()[0]
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
                   '{!r}'.format(name, self.pkgbin))
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
        found_msg += [mlog.green('YES'), self.version]
        # Fetch cargs to be used while using this dependency
        self._set_cargs()
        # Fetch the libraries and library paths needed for using this
        self._set_libs()
        # Print the found message only at the very end because fetching cflags
        # and libs can also fail if other needed pkg-config files aren't found.
        if not self.silent:
            mlog.log(*found_msg)

    def __repr__(self):
        s = '<{0} {1}: {2} {3}>'
        return s.format(self.__class__.__name__, self.name, self.is_found,
                        self.version_reqs)

    def _call_pkgbin(self, args):
        p, out = Popen_safe([self.pkgbin] + args, env=os.environ)[0:2]
        return p.returncode, out.strip()

    def _set_cargs(self):
        ret, out = self._call_pkgbin(['--cflags', self.name])
        if ret != 0:
            raise DependencyException('Could not generate cargs for %s:\n\n%s' %
                                      (self.name, out))
        self.compile_args = out.split()

    def _set_libs(self):
        libcmd = [self.name, '--libs']
        if self.static:
            libcmd.append('--static')
        ret, out = self._call_pkgbin(libcmd)
        if ret != 0:
            raise DependencyException('Could not generate libs for %s:\n\n%s' %
                                      (self.name, out))
        self.link_args = []
        for lib in out.split():
            if lib.endswith(".la"):
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

    def get_pkgconfig_variable(self, variable_name):
        ret, out = self._call_pkgbin(['--variable=' + variable_name, self.name])
        variable = ''
        if ret != 0:
            if self.required:
                raise DependencyException('%s dependency %s not found.' %
                                          (self.type_string, self.name))
        else:
            variable = out.strip()
        mlog.debug('Got pkgconfig variable %s : %s' % (variable_name, variable))
        return variable

    def get_methods(self):
        return [DependencyMethods.PKGCONFIG]

    def check_pkgconfig(self):
        evar = 'PKG_CONFIG'
        if evar in os.environ:
            pkgbin = os.environ[evar].strip()
        else:
            pkgbin = 'pkg-config'
        try:
            p, out = Popen_safe([pkgbin, '--version'])[0:2]
            if p.returncode != 0:
                # Set to False instead of None to signify that we've already
                # searched for it and not found it
                pkgbin = False
        except (FileNotFoundError, PermissionError):
            pkgbin = False
        if pkgbin and not os.path.isabs(pkgbin) and shutil.which(pkgbin):
            # Sometimes shutil.which fails where Popen succeeds, so
            # only find the abs path if it can be found by shutil.which
            pkgbin = shutil.which(pkgbin)
        if not self.silent:
            if pkgbin:
                mlog.log('Found pkg-config:', mlog.bold(pkgbin),
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
    windows_exts = ('exe', 'msc', 'com', 'bat')

    def __init__(self, name, command=None, silent=False, search_dir=None):
        self.name = name
        if command is not None:
            if not isinstance(command, list):
                self.command = [command]
            else:
                self.command = command
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
                commands = first_line[2:].split('#')[0].strip().split()
                if mesonlib.is_windows():
                    # Windows does not have UNIX paths so remove them,
                    # but don't remove Windows paths
                    if commands[0].startswith('/'):
                        commands[0] = commands[0].split('/')[-1]
                    if len(commands) > 0 and commands[0] == 'env':
                        commands = commands[1:]
                    # Windows does not ship python3.exe, but we know the path to it
                    if len(commands) > 0 and commands[0] == 'python3':
                        commands[0] = sys.executable
                return commands + [script]
        except Exception:
            pass
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
        if not mesonlib.is_windows():
            # On UNIX-like platforms, shutil.which() is enough to find
            # all executables whether in PATH or with an absolute path
            return [command]
        # HERE BEGINS THE TERROR OF WINDOWS
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
        else:
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
            paths = ['/Library/Frameworks']
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
    version_reqs = flatten(kwargs.get('version', []))
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
            value = frozenset(flatten(value))
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
        dep = packages[lname](env, kwargs)
        if required and not dep.found():
            raise DependencyException('Dependency "%s" not found' % name)
        return dep
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
