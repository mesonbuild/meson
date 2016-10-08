# Copyright 2013-2015 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This file contains the detection logic for external
# dependencies. Mostly just uses pkg-config but also contains
# custom logic for packages that don't provide them.

# Currently one file, should probably be split into a
# package before this gets too big.

import re
import os, stat, glob, subprocess, shutil
import sysconfig
from . mesonlib import MesonException
from . import mlog
from . import mesonlib
from .environment import detect_cpu_family

class DependencyException(MesonException):
    def __init__(self, *args, **kwargs):
        MesonException.__init__(self, *args, **kwargs)

class Dependency():
    def __init__(self):
        self.name = "null"
        self.is_found = False

    def get_compile_args(self):
        return []

    def get_link_args(self):
        return []

    def found(self):
        return self.is_found

    def get_sources(self):
        """Source files that need to be added to the target.
        As an example, gtest-all.cc when using GTest."""
        return []

    def get_name(self):
        return self.name

    def get_exe_args(self):
        return []

    def need_threads(self):
        return False

class InternalDependency(Dependency):
    def __init__(self, version, incdirs, compile_args, link_args, libraries, sources, ext_deps):
        super().__init__()
        self.version = version
        self.include_directories = incdirs
        self.compile_args = compile_args
        self.link_args = link_args
        self.libraries = libraries
        self.sources = sources
        self.ext_deps = ext_deps

    def get_compile_args(self):
        return self.compile_args

    def get_link_args(self):
        return self.link_args

    def get_version(self):
        return self.version

class PkgConfigDependency(Dependency):
    pkgconfig_found = None

    def __init__(self, name, environment, kwargs):
        Dependency.__init__(self)
        self.is_libtool = False
        self.required = kwargs.get('required', True)
        self.static = kwargs.get('static', False)
        if not isinstance(self.static, bool):
            raise DependencyException('Static keyword must be boolean')
        self.cargs = []
        self.libs = []
        if 'native' in kwargs and environment.is_cross_build():
            want_cross = not kwargs['native']
        else:
            want_cross = environment.is_cross_build()
        self.name = name
        if PkgConfigDependency.pkgconfig_found is None:
            self.check_pkgconfig()

        self.is_found = False
        if not PkgConfigDependency.pkgconfig_found:
            if self.required:
                raise DependencyException('Pkg-config not found.')
            return
        if environment.is_cross_build() and want_cross:
            if "pkgconfig" not in environment.cross_info.config["binaries"]:
                raise DependencyException('Pkg-config binary missing from cross file.')
            pkgbin = environment.cross_info.config["binaries"]['pkgconfig']
            self.type_string = 'Cross'
        else:
            pkgbin = 'pkg-config'
            self.type_string = 'Native'

        mlog.debug('Determining dependency %s with pkg-config executable %s.' % (name, pkgbin))
        self.pkgbin = pkgbin
        p = subprocess.Popen([pkgbin, '--modversion', name],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        out = p.communicate()[0]
        if p.returncode != 0:
            if self.required:
                raise DependencyException('%s dependency %s not found.' % (self.type_string, name))
            self.modversion = 'none'
            return
        self.modversion = out.decode().strip()
        found_msg = ['%s dependency' % self.type_string, mlog.bold(name), 'found:']
        self.version_requirement = kwargs.get('version', None)
        if self.version_requirement is None:
            self.is_found = True
        else:
            if not isinstance(self.version_requirement, str):
                raise DependencyException('Version argument must be string.')
            self.is_found = mesonlib.version_compare(self.modversion, self.version_requirement)
            if not self.is_found:
                found_msg += [mlog.red('NO'), 'found {!r}'.format(self.modversion),
                              'but need {!r}'.format(self.version_requirement)]
                mlog.log(*found_msg)
                if self.required:
                    raise DependencyException(
                        'Invalid version of a dependency, needed %s %s found %s.' %
                        (name, self.version_requirement, self.modversion))
                return
        found_msg += [mlog.green('YES'), self.modversion]
        mlog.log(*found_msg)
        # Fetch cargs to be used while using this dependency
        self._set_cargs()
        # Fetch the libraries and library paths needed for using this
        self._set_libs()

    def _set_cargs(self):
        p = subprocess.Popen([self.pkgbin, '--cflags', self.name],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = p.communicate()[0]
        if p.returncode != 0:
            raise DependencyException('Could not generate cargs for %s:\n\n%s' % \
                                      (self.name, out.decode(errors='ignore')))
        self.cargs = out.decode().split()

    def _set_libs(self):
        libcmd = [self.pkgbin, '--libs']
        if self.static:
            libcmd.append('--static')
        p = subprocess.Popen(libcmd + [self.name],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = p.communicate()[0]
        if p.returncode != 0:
            raise DependencyException('Could not generate libs for %s:\n\n%s' % \
                                      (self.name, out.decode(errors='ignore')))
        self.libs = []
        for lib in out.decode().split():
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
            self.libs.append(lib)

    def get_variable(self, variable_name):
        p = subprocess.Popen([self.pkgbin, '--variable=%s' % variable_name, self.name],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = p.communicate()[0]
        variable = ''
        if p.returncode != 0:
            if self.required:
                raise DependencyException('%s dependency %s not found.' %
                                          (self.type_string, self.name))
        else:
            variable = out.decode().strip()
        mlog.debug('return of subprocess : %s' % variable)

        return variable

    def get_modversion(self):
        return self.modversion

    def get_version(self):
        return self.get_modversion()

    def get_compile_args(self):
        return self.cargs

    def get_link_args(self):
        return self.libs

    def check_pkgconfig(self):
        try:
            p = subprocess.Popen(['pkg-config', '--version'], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            out = p.communicate()[0]
            if p.returncode == 0:
                mlog.log('Found pkg-config:', mlog.bold(shutil.which('pkg-config')),
                         '(%s)' % out.decode().strip())
                PkgConfigDependency.pkgconfig_found = True
                return
        except Exception:
            pass
        PkgConfigDependency.pkgconfig_found = False
        mlog.log('Found Pkg-config:', mlog.red('NO'))

    def found(self):
        return self.is_found

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

class WxDependency(Dependency):
    wx_found = None

    def __init__(self, environment, kwargs):
        Dependency.__init__(self)
        self.is_found = False
        if WxDependency.wx_found is None:
            self.check_wxconfig()
        if not WxDependency.wx_found:
            mlog.log("Neither wx-config-3.0 nor wx-config found; can't detect dependency")
            return

        p = subprocess.Popen([self.wxc, '--version'],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        out = p.communicate()[0]
        if p.returncode != 0:
            mlog.log('Dependency wxwidgets found:', mlog.red('NO'))
            self.cargs = []
            self.libs = []
        else:
            self.modversion = out.decode().strip()
            version_req = kwargs.get('version', None)
            if version_req is not None:
                if not mesonlib.version_compare(self.modversion, version_req):
                    mlog.log('Wxwidgets version %s does not fullfill requirement %s' %\
                             (self.modversion, version_req))
                    return
            mlog.log('Dependency wxwidgets found:', mlog.green('YES'))
            self.is_found = True
            self.requested_modules = self.get_requested(kwargs)
            # wx-config seems to have a cflags as well but since it requires C++,
            # this should be good, at least for now.
            p = subprocess.Popen([self.wxc, '--cxxflags'],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            out = p.communicate()[0]
            if p.returncode != 0:
                raise DependencyException('Could not generate cargs for wxwidgets.')
            self.cargs = out.decode().split()

            p = subprocess.Popen([self.wxc, '--libs'] + self.requested_modules,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out = p.communicate()[0]
            if p.returncode != 0:
                raise DependencyException('Could not generate libs for wxwidgets.')
            self.libs = out.decode().split()

    def get_requested(self, kwargs):
        modules = 'modules'
        if not modules in kwargs:
            return []
        candidates = kwargs[modules]
        if isinstance(candidates, str):
            return [candidates]
        for c in candidates:
            if not isinstance(c, str):
                raise DependencyException('wxwidgets module argument is not a string.')
        return candidates

    def get_modversion(self):
        return self.modversion

    def get_compile_args(self):
        return self.cargs

    def get_link_args(self):
        return self.libs

    def check_wxconfig(self):
        for wxc in ['wx-config-3.0', 'wx-config']:
            try:
                p = subprocess.Popen([wxc, '--version'], stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
                out = p.communicate()[0]
                if p.returncode == 0:
                    mlog.log('Found wx-config:', mlog.bold(shutil.which(wxc)),
                             '(%s)' % out.decode().strip())
                    self.wxc = wxc
                    WxDependency.wx_found = True
                    return
            except Exception:
                pass
        WxDependency.wxconfig_found = False
        mlog.log('Found wx-config:', mlog.red('NO'))

    def found(self):
        return self.is_found

class ExternalProgram():
    def __init__(self, name, fullpath=None, silent=False, search_dir=None):
        self.name = name
        if fullpath is not None:
            if not isinstance(fullpath, list):
                self.fullpath = [fullpath]
            else:
                self.fullpath = fullpath
        else:
            self.fullpath = self._search(name, search_dir)
        if not silent:
            if self.found():
                mlog.log('Program', mlog.bold(name), 'found:', mlog.green('YES'),
                         '(%s)' % ' '.join(self.fullpath))
            else:
                mlog.log('Program', mlog.bold(name), 'found:', mlog.red('NO'))

    @staticmethod
    def _shebang_to_cmd(script):
        """
        Windows does not understand shebangs, so we check if the file has a
        shebang and manually parse it to figure out the interpreter to use
        """
        try:
            with open(script) as f:
                first_line = f.readline().strip()
            if first_line.startswith('#!'):
                commands = first_line[2:].split('#')[0].strip().split()
                if mesonlib.is_windows():
                    # Windows does not have /usr/bin.
                    commands[0] = commands[0].split('/')[-1]
                    if commands[0] == 'env':
                        commands = commands[1:]
                return commands + [script]
        except Exception:
            pass
        return False

    @staticmethod
    def _is_executable(path):
        suffix = os.path.splitext(path)[-1].lower()[1:]
        if mesonlib.is_windows():
            if suffix == 'exe' or suffix == 'com' or suffix == 'bat':
                return True
        elif os.access(path, os.X_OK):
            return True
        return False

    def _search_dir(self, name, search_dir):
        if search_dir is None:
            return False
        trial = os.path.join(search_dir, name)
        if not os.path.exists(trial):
            return False
        if self._is_executable(trial):
            return [trial]
        # Now getting desperate. Maybe it is a script file that is a) not chmodded
        # executable or b) we are on windows so they can't be directly executed.
        return self._shebang_to_cmd(trial)

    def _search(self, name, search_dir):
        commands = self._search_dir(name, search_dir)
        if commands:
            return commands
        # Do a standard search in PATH
        fullpath = shutil.which(name)
        if fullpath or not mesonlib.is_windows():
            # On UNIX-like platforms, the standard PATH search is enough
            return [fullpath]
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
        return self.fullpath[0] is not None

    def get_command(self):
        return self.fullpath

    def get_name(self):
        return self.name

class ExternalLibrary(Dependency):
    def __init__(self, name, link_args=None, silent=False):
        super().__init__()
        self.name = name
        # Rename fullpath to link_args once standalone find_library() gets removed.
        if link_args is not None:
            if isinstance(link_args, list):
                self.link_args = link_args
            else:
                self.link_args = [link_args]
        else:
            self.link_args = link_args
        if not silent:
            if self.found():
                mlog.log('Library', mlog.bold(name), 'found:', mlog.green('YES'))
            else:
                mlog.log('Library', mlog.bold(name), 'found:', mlog.red('NO'))

    def found(self):
        return self.link_args is not None

    def get_link_args(self):
        if self.found():
            return self.link_args
        return []

class BoostDependency(Dependency):
    # Some boost libraries have different names for
    # their sources and libraries. This dict maps
    # between the two.
    name2lib = {'test' : 'unit_test_framework'}

    def __init__(self, environment, kwargs):
        Dependency.__init__(self)
        self.name = 'boost'
        self.environment = environment
        self.libdir = ''
        if 'native' in kwargs and environment.is_cross_build():
            want_cross = not kwargs['native']
        else:
            want_cross = environment.is_cross_build()
        try:
            self.boost_root = os.environ['BOOST_ROOT']
            if not os.path.isabs(self.boost_root):
                raise DependencyException('BOOST_ROOT must be an absolute path.')
        except KeyError:
            self.boost_root = None
        if self.boost_root is None:
            if want_cross:
                raise DependencyException('BOOST_ROOT is needed while cross-compiling')
            if mesonlib.is_windows():
                self.boost_root = self.detect_win_root()
                self.incdir = self.boost_root
            else:
                self.incdir = '/usr/include'
        else:
            self.incdir = os.path.join(self.boost_root, 'include')
        self.boost_inc_subdir = os.path.join(self.incdir, 'boost')
        mlog.debug('Boost library root dir is', self.boost_root)
        self.src_modules = {}
        self.lib_modules = {}
        self.lib_modules_mt = {}
        self.detect_version()
        self.requested_modules = self.get_requested(kwargs)
        module_str = ', '.join(self.requested_modules)
        if self.version is not None:
            self.detect_src_modules()
            self.detect_lib_modules()
            self.validate_requested()
            if self.boost_root is not None:
                info = self.version + ', ' + self.boost_root
            else:
                info = self.version
            mlog.log('Dependency Boost (%s) found:' % module_str, mlog.green('YES'),
                     '(' + info + ')')
        else:
            mlog.log("Dependency Boost (%s) found:" % module_str, mlog.red('NO'))

    def detect_win_root(self):
        globtext = 'c:\\local\\boost_*'
        files = glob.glob(globtext)
        if len(files) > 0:
            return files[0]
        return 'C:\\'

    def get_compile_args(self):
        args = []
        if self.boost_root is not None:
            if mesonlib.is_windows():
                args.append('-I' + self.boost_root)
            else:
                args.append('-I' + os.path.join(self.boost_root, 'include'))
        else:
            args.append('-I' + self.incdir)
        return args

    def get_requested(self, kwargs):
        candidates = kwargs.get('modules', [])
        if isinstance(candidates, str):
            return [candidates]
        for c in candidates:
            if not isinstance(c, str):
                raise DependencyException('Boost module argument is not a string.')
        return candidates

    def validate_requested(self):
        for m in self.requested_modules:
            if m not in self.src_modules:
                raise DependencyException('Requested Boost module "%s" not found.' % m)

    def found(self):
        return self.version is not None

    def get_version(self):
        return self.version

    def detect_version(self):
        try:
            ifile = open(os.path.join(self.boost_inc_subdir, 'version.hpp'))
        except FileNotFoundError:
            self.version = None
            return
        with ifile:
            for line in ifile:
                if line.startswith("#define") and 'BOOST_LIB_VERSION' in line:
                    ver = line.split()[-1]
                    ver = ver[1:-1]
                    self.version = ver.replace('_', '.')
                    return
        self.version = None

    def detect_src_modules(self):
        for entry in os.listdir(self.boost_inc_subdir):
            entry = os.path.join(self.boost_inc_subdir, entry)
            if stat.S_ISDIR(os.stat(entry).st_mode):
                self.src_modules[os.path.split(entry)[-1]] = True

    def detect_lib_modules(self):
        if mesonlib.is_windows():
            return self.detect_lib_modules_win()
        return self.detect_lib_modules_nix()

    def detect_lib_modules_win(self):
        arch = detect_cpu_family(self.environment.coredata.compilers)
        # Guess the libdir
        if arch == 'x86':
            gl = 'lib32*'
        elif arch == 'x86_64':
            gl = 'lib64*'
        else:
            # Does anyone do Boost cross-compiling to other archs on Windows?
            gl = None
        # See if the libdir is valid
        if gl:
            libdir = glob.glob(os.path.join(self.boost_root, gl))
        else:
            libdir = []
        # Can't find libdir, bail
        if len(libdir) == 0:
            return
        libdir = libdir[0]
        self.libdir = libdir
        globber = 'boost_*-gd-*.lib' # FIXME
        for entry in glob.glob(os.path.join(libdir, globber)):
            (_, fname) = os.path.split(entry)
            base = fname.split('_', 1)[1]
            modname = base.split('-', 1)[0]
            self.lib_modules_mt[modname] = fname

    def detect_lib_modules_nix(self):
        libsuffix = None
        if mesonlib.is_osx():
            libsuffix = 'dylib'
        else:
            libsuffix = 'so'

        globber = 'libboost_*.{}'.format(libsuffix)
        if self.boost_root is None:
            libdirs = mesonlib.get_library_dirs()
        else:
            libdirs = [os.path.join(self.boost_root, 'lib')]
        for libdir in libdirs:
            for entry in glob.glob(os.path.join(libdir, globber)):
                lib = os.path.basename(entry)
                name = lib.split('.')[0].split('_', 1)[-1]
                # I'm not 100% sure what to do here. Some distros
                # have modules such as thread only as -mt versions.
                if entry.endswith('-mt.so'):
                    self.lib_modules_mt[name] = True
                else:
                    self.lib_modules[name] = True

    def get_win_link_args(self):
        args = []
        if self.boost_root:
            args.append('-L' + self.libdir)
        for module in self.requested_modules:
            module = BoostDependency.name2lib.get(module, module)
            if module in self.lib_modules_mt:
                args.append(self.lib_modules_mt[module])
        return args

    def get_link_args(self):
        if mesonlib.is_windows():
            return self.get_win_link_args()
        args = []
        if self.boost_root:
            args.append('-L' + os.path.join(self.boost_root, 'lib'))
        for module in self.requested_modules:
            module = BoostDependency.name2lib.get(module, module)
            if module in self.lib_modules or module in self.lib_modules_mt:
                linkcmd = '-lboost_' + module
                args.append(linkcmd)
                # FIXME a hack, but Boost's testing framework has a lot of
                # different options and it's hard to determine what to do
                # without feedback from actual users. Update this
                # as we get more bug reports.
                if module == 'unit_testing_framework':
                    args.append('-lboost_test_exec_monitor')
            elif module + '-mt' in self.lib_modules_mt:
                linkcmd = '-lboost_' + module + '-mt'
                args.append(linkcmd)
                if module == 'unit_testing_framework':
                    args.append('-lboost_test_exec_monitor-mt')
        return args

    def get_sources(self):
        return []

    def need_threads(self):
        return 'thread' in self.requested_modules

class GTestDependency(Dependency):
    def __init__(self, environment, kwargs):
        Dependency.__init__(self)
        self.main = kwargs.get('main', False)
        self.name = 'gtest'
        self.libname = 'libgtest.so'
        self.libmain_name = 'libgtest_main.so'
        self.include_dir = '/usr/include'
        self.src_include_dir = '/usr/src/gtest'
        self.src_dir = '/usr/src/gtest/src'
        self.all_src = mesonlib.File.from_absolute_file(
            os.path.join(self.src_dir, 'gtest-all.cc'))
        self.main_src = mesonlib.File.from_absolute_file(
            os.path.join(self.src_dir, 'gtest_main.cc'))
        self.detect()

    def found(self):
        return self.is_found

    def detect(self):
        trial_dirs = mesonlib.get_library_dirs()
        glib_found = False
        gmain_found = False
        for d in trial_dirs:
            if os.path.isfile(os.path.join(d, self.libname)):
                glib_found = True
            if os.path.isfile(os.path.join(d, self.libmain_name)):
                gmain_found = True
        if glib_found and gmain_found:
            self.is_found = True
            self.compile_args = []
            self.link_args = ['-lgtest']
            if self.main:
                self.link_args.append('-lgtest_main')
            self.sources = []
            mlog.log('Dependency GTest found:', mlog.green('YES'), '(prebuilt)')
        elif os.path.exists(self.src_dir):
            self.is_found = True
            self.compile_args = ['-I' + self.src_include_dir]
            self.link_args = []
            if self.main:
                self.sources = [self.all_src, self.main_src]
            else:
                self.sources = [self.all_src]
            mlog.log('Dependency GTest found:', mlog.green('YES'), '(building self)')
        else:
            mlog.log('Dependency GTest found:', mlog.red('NO'))
            self.is_found = False
        return self.is_found

    def get_compile_args(self):
        arr = []
        if self.include_dir != '/usr/include':
            arr.append('-I' + self.include_dir)
        arr.append('-I' + self.src_include_dir)
        return arr

    def get_link_args(self):
        return self.link_args
    def get_version(self):
        return '1.something_maybe'
    def get_sources(self):
        return self.sources

    def need_threads(self):
        return True

class GMockDependency(Dependency):
    def __init__(self, environment, kwargs):
        Dependency.__init__(self)
        # GMock may be a library or just source.
        # Work with both.
        self.name = 'gmock'
        self.libname = 'libgmock.so'
        trial_dirs = mesonlib.get_library_dirs()
        gmock_found = False
        for d in trial_dirs:
            if os.path.isfile(os.path.join(d, self.libname)):
                gmock_found = True
        if gmock_found:
            self.is_found = True
            self.compile_args = []
            self.link_args = ['-lgmock']
            self.sources = []
            mlog.log('Dependency GMock found:', mlog.green('YES'), '(prebuilt)')
            return

        for d in ['/usr/src/gmock/src', '/usr/src/gmock']:
            if os.path.exists(d):
                self.is_found = True
                # Yes, we need both because there are multiple
                # versions of gmock that do different things.
                self.compile_args = ['-I/usr/src/gmock', '-I/usr/src/gmock/src']
                self.link_args = []
                all_src = mesonlib.File.from_absolute_file(os.path.join(d, 'gmock-all.cc'))
                main_src = mesonlib.File.from_absolute_file(os.path.join(d, 'gmock_main.cc'))
                if kwargs.get('main', False):
                    self.sources = [all_src, main_src]
                else:
                    self.sources = [all_src]
                mlog.log('Dependency GMock found:', mlog.green('YES'), '(building self)')
                return

        mlog.log('Dependency GMock found:', mlog.red('NO'))
        self.is_found = False

    def get_version(self):
        return '1.something_maybe'

    def get_compile_args(self):
        return self.compile_args

    def get_sources(self):
        return self.sources

    def get_link_args(self):
        return self.link_args

    def found(self):
        return self.is_found

class Qt5Dependency(Dependency):
    def __init__(self, environment, kwargs):
        Dependency.__init__(self)
        self.name = 'qt5'
        self.root = '/usr'
        mods = kwargs.get('modules', [])
        self.cargs = []
        self.largs = []
        self.is_found = False
        if isinstance(mods, str):
            mods = [mods]
        if len(mods) == 0:
            raise DependencyException('No Qt5 modules specified.')
        type_text = 'native'
        if environment.is_cross_build() and kwargs.get('native', False):
            type_text = 'cross'
            self.pkgconfig_detect(mods, environment, kwargs)
        elif not environment.is_cross_build() and shutil.which('pkg-config') is not None:
            self.pkgconfig_detect(mods, environment, kwargs)
        elif shutil.which('qmake') is not None:
            self.qmake_detect(mods, kwargs)
        else:
            self.version = 'none'
        if not self.is_found:
            mlog.log('Qt5 %s dependency found: ' % type_text, mlog.red('NO'))
        else:
            mlog.log('Qt5 %s dependency found: ' % type_text, mlog.green('YES'))

    def pkgconfig_detect(self, mods, environment, kwargs):
        modules = []
        for module in mods:
            modules.append(PkgConfigDependency('Qt5' + module, environment, kwargs))
        for m in modules:
            self.cargs += m.get_compile_args()
            self.largs += m.get_link_args()
        self.is_found = True
        self.version = modules[0].modversion

    def qmake_detect(self, mods, kwargs):
        pc = subprocess.Popen(['qmake', '-v'], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        (stdo, _) = pc.communicate()
        if pc.returncode != 0:
            return
        stdo = stdo.decode()
        if not 'version 5' in stdo:
            mlog.log('QMake is not for Qt5.')
            return
        self.version = re.search('5(\.\d+)+', stdo).group(0)
        (stdo, _) = subprocess.Popen(['qmake', '-query'], stdout=subprocess.PIPE).communicate()
        qvars = {}
        for line in stdo.decode().split('\n'):
            line = line.strip()
            if line == '':
                continue
            (k, v) = tuple(line.split(':', 1))
            qvars[k] = v
        if mesonlib.is_osx():
            return self.framework_detect(qvars, mods, kwargs)
        incdir = qvars['QT_INSTALL_HEADERS']
        self.cargs.append('-I' + incdir)
        libdir = qvars['QT_INSTALL_LIBS']
        bindir = qvars['QT_INSTALL_BINS']
        #self.largs.append('-L' + libdir)
        for module in mods:
            mincdir = os.path.join(incdir, 'Qt' + module)
            self.cargs.append('-I' + mincdir)
            libfile = os.path.join(libdir, 'Qt5' + module + '.lib')
            if not os.path.isfile(libfile):
                # MinGW links directly to .dll, not to .lib.
                libfile = os.path.join(bindir, 'Qt5' + module + '.dll')
            self.largs.append(libfile)
        self.is_found = True

    def framework_detect(self, qvars, modules, kwargs):
        libdir = qvars['QT_INSTALL_LIBS']
        for m in modules:
            fname = 'Qt' + m
            fwdep = ExtraFrameworkDependency(fname, kwargs.get('required', True), libdir)
            self.cargs.append('-F' + libdir)
            if fwdep.found():
                self.is_found = True
                self.cargs += fwdep.get_compile_args()
                self.largs += fwdep.get_link_args()


    def get_version(self):
        return self.version

    def get_compile_args(self):
        return self.cargs

    def get_sources(self):
        return []

    def get_link_args(self):
        return self.largs

    def found(self):
        return self.is_found

    def get_exe_args(self):
        # Originally this was -fPIE but nowadays the default
        # for upstream and distros seems to be -reduce-relocations
        # which requires -fPIC. This may cause a performance
        # penalty when using self-built Qt or on platforms
        # where -fPIC is not required. If this is an issue
        # for you, patches are welcome.
        # Fix this to be more portable, especially to MSVC.
        return ['-fPIC']

class Qt4Dependency(Dependency):
    def __init__(self, environment, kwargs):
        Dependency.__init__(self)
        self.name = 'qt4'
        self.root = '/usr'
        self.modules = []
        mods = kwargs.get('modules', [])
        if isinstance(mods, str):
            mods = [mods]
        for module in mods:
            self.modules.append(PkgConfigDependency('Qt' + module, environment, kwargs))
        if len(self.modules) == 0:
            raise DependencyException('No Qt4 modules specified.')

    def get_version(self):
        return self.modules[0].get_version()

    def get_compile_args(self):
        args = []
        for m in self.modules:
            args += m.get_compile_args()
        return args

    def get_sources(self):
        return []

    def get_link_args(self):
        args = []
        for module in self.modules:
            args += module.get_link_args()
        return args

    def found(self):
        for i in self.modules:
            if not i.found():
                return False
        return True

class GnuStepDependency(Dependency):
    def __init__(self, environment, kwargs):
        Dependency.__init__(self)
        self.modules = kwargs.get('modules', [])
        self.detect()

    def detect(self):
        confprog = 'gnustep-config'
        try:
            gp = subprocess.Popen([confprog, '--help'],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            gp.communicate()
        except FileNotFoundError:
            self.args = None
            mlog.log('Dependency GnuStep found:', mlog.red('NO'), '(no gnustep-config)')
            return
        if gp.returncode != 0:
            self.args = None
            mlog.log('Dependency GnuStep found:', mlog.red('NO'))
            return
        if 'gui' in self.modules:
            arg = '--gui-libs'
        else:
            arg = '--base-libs'
        fp = subprocess.Popen([confprog, '--objc-flags'],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (flagtxt, flagerr) = fp.communicate()
        flagtxt = flagtxt.decode()
        flagerr = flagerr.decode()
        if fp.returncode != 0:
            raise DependencyException('Error getting objc-args: %s %s' % (flagtxt, flagerr))
        args = flagtxt.split()
        self.args = self.filter_arsg(args)
        fp = subprocess.Popen([confprog, arg],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (libtxt, liberr) = fp.communicate()
        libtxt = libtxt.decode()
        liberr = liberr.decode()
        if fp.returncode != 0:
            raise DependencyException('Error getting objc-lib args: %s %s' % (libtxt, liberr))
        self.libs = self.weird_filter(libtxt.split())
        mlog.log('Dependency GnuStep found:', mlog.green('YES'))

    def weird_filter(self, elems):
        """When building packages, the output of the enclosing Make
is sometimes mixed among the subprocess output. I have no idea
why. As a hack filter out everything that is not a flag."""
        return [e for e in elems if e.startswith('-')]


    def filter_arsg(self, args):
        """gnustep-config returns a bunch of garbage args such
        as -O2 and so on. Drop everything that is not needed."""
        result = []
        for f in args:
            if f.startswith('-D') or f.startswith('-f') or \
            f.startswith('-I') or f == '-pthread' or\
            (f.startswith('-W') and not f == '-Wall'):
                result.append(f)
        return result

    def found(self):
        return self.args is not None

    def get_compile_args(self):
        if self.args is None:
            return []
        return self.args

    def get_link_args(self):
        return self.libs

class AppleFrameworks(Dependency):
    def __init__(self, environment, kwargs):
        Dependency.__init__(self)
        modules = kwargs.get('modules', [])
        if isinstance(modules, str):
            modules = [modules]
        if len(modules) == 0:
            raise DependencyException("AppleFrameworks dependency requires at least one module.")
        self.frameworks = modules

    def get_link_args(self):
        args = []
        for f in self.frameworks:
            args.append('-framework')
            args.append(f)
        return args

    def found(self):
        return mesonlib.is_osx()

class GLDependency(Dependency):
    def __init__(self, environment, kwargs):
        Dependency.__init__(self)
        self.is_found = False
        self.cargs = []
        self.linkargs = []
        try:
            pcdep = PkgConfigDependency('gl', environment, kwargs)
            if pcdep.found():
                self.is_found = True
                self.cargs = pcdep.get_compile_args()
                self.linkargs = pcdep.get_link_args()
                return
        except Exception:
            pass
        if mesonlib.is_osx():
            self.is_found = True
            self.linkargs = ['-framework', 'OpenGL']
            return
        if mesonlib.is_windows():
            self.is_found = True
            self.linkargs = ['-lopengl32']
            return

    def get_link_args(self):
        return self.linkargs

# There are three different ways of depending on SDL2:
# sdl2-config, pkg-config and OSX framework
class SDL2Dependency(Dependency):
    def __init__(self, environment, kwargs):
        Dependency.__init__(self)
        self.is_found = False
        self.cargs = []
        self.linkargs = []
        try:
            pcdep = PkgConfigDependency('sdl2', environment, kwargs)
            if pcdep.found():
                self.is_found = True
                self.cargs = pcdep.get_compile_args()
                self.linkargs = pcdep.get_link_args()
                self.version = pcdep.get_version()
                return
        except Exception as e:
            mlog.debug('SDL 2 not found via pkgconfig. Trying next, error was:', str(e))
            pass
        sdlconf = shutil.which('sdl2-config')
        if sdlconf:
            pc = subprocess.Popen(['sdl2-config', '--cflags'],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL)
            (stdo, _) = pc.communicate()
            self.cargs = stdo.decode().strip().split()
            pc = subprocess.Popen(['sdl2-config', '--libs'],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL)
            (stdo, _) = pc.communicate()
            self.linkargs = stdo.decode().strip().split()
            self.is_found = True
            mlog.log('Dependency', mlog.bold('sdl2'), 'found:', mlog.green('YES'), '(%s)' % sdlconf)
            self.version = '2' # FIXME
            return
        mlog.debug('Could not find sdl2-config binary, trying next.')
        if mesonlib.is_osx():
            fwdep = ExtraFrameworkDependency('sdl2', kwargs.get('required', True))
            if fwdep.found():
                self.is_found = True
                self.cargs = fwdep.get_compile_args()
                self.linkargs = fwdep.get_link_args()
                self.version = '2' # FIXME
                return
        mlog.log('Dependency', mlog.bold('sdl2'), 'found:', mlog.red('NO'))

    def get_compile_args(self):
        return self.cargs

    def get_link_args(self):
        return self.linkargs

    def found(self):
        return self.is_found

    def get_version(self):
        return self.version

class ExtraFrameworkDependency(Dependency):
    def __init__(self, name, required, path=None):
        Dependency.__init__(self)
        self.name = None
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
                return

    def get_compile_args(self):
        if self.found():
            return ['-I' + os.path.join(self.path, self.name, 'Headers')]
        return []

    def get_link_args(self):
        if self.found():
            return ['-F' + self.path, '-framework', self.name.split('.')[0]]
        return []

    def found(self):
        return self.name is not None

class ThreadDependency(Dependency):
    def __init__(self, environment, kwargs):
        super().__init__()
        self.name = 'threads'
        self.is_found = True
        mlog.log('Dependency', mlog.bold(self.name), 'found:', mlog.green('YES'))

    def need_threads(self):
        return True

class Python3Dependency(Dependency):
    def __init__(self, environment, kwargs):
        super().__init__()
        self.name = 'python3'
        self.is_found = False
        self.version = "3.something_maybe"
        try:
            pkgdep = PkgConfigDependency('python3', environment, kwargs)
            if pkgdep.found():
                self.cargs = pkgdep.cargs
                self.libs = pkgdep.libs
                self.version = pkgdep.get_version()
                self.is_found = True
                return
        except Exception:
            pass
        if not self.is_found:
            if mesonlib.is_windows():
                inc = sysconfig.get_path('include')
                platinc = sysconfig.get_path('platinclude')
                self.cargs = ['-I' + inc]
                if inc != platinc:
                    self.cargs.append('-I' + platinc)
                # Nothing exposes this directly that I coulf find
                basedir = sysconfig.get_config_var('base')
                vernum = sysconfig.get_config_var('py_version_nodot')
                self.libs = ['-L{}/libs'.format(basedir),
                             '-lpython{}'.format(vernum)]
                self.is_found = True
                self.version = sysconfig.get_config_var('py_version_short')
            elif mesonlib.is_osx():
                # In OSX the Python 3 framework does not have a version
                # number in its name.
                fw = ExtraFrameworkDependency('python', False)
                if fw.found():
                    self.cargs = fw.get_compile_args()
                    self.libs = fw.get_link_args()
                    self.is_found = True
        if self.is_found:
            mlog.log('Dependency', mlog.bold(self.name), 'found:', mlog.green('YES'))
        else:
            mlog.log('Dependency', mlog.bold(self.name), 'found:', mlog.red('NO'))

    def get_compile_args(self):
        return self.cargs

    def get_link_args(self):
        return self.libs

    def get_version(self):
        return self.version

def get_dep_identifier(name, kwargs):
    elements = [name]
    modlist = kwargs.get('modules', [])
    if isinstance(modlist, str):
        modlist = [modlist]
    for module in modlist:
        elements.append(module)
    # We use a tuple because we need a non-mutable structure to use as the key
    # of a dictionary and a string has potential for name collisions
    identifier = tuple(elements)
    identifier += ('main', kwargs.get('main', False))
    identifier += ('static', kwargs.get('static', False))
    if 'fallback' in kwargs:
        f = kwargs.get('fallback')
        identifier += ('fallback', f[0], f[1])
    return identifier

def find_external_dependency(name, environment, kwargs):
    required = kwargs.get('required', True)
    if not isinstance(required, bool):
        raise DependencyException('Keyword "required" must be a boolean.')
    lname = name.lower()
    if lname in packages:
        dep = packages[lname](environment, kwargs)
        if required and not dep.found():
            raise DependencyException('Dependency "%s" not found' % name)
        return dep
    pkg_exc = None
    pkgdep = None
    try:
        pkgdep = PkgConfigDependency(name, environment, kwargs)
        if pkgdep.found():
            return pkgdep
    except Exception as e:
        pkg_exc = e
    if mesonlib.is_osx():
        fwdep = ExtraFrameworkDependency(name, required)
        if required and not fwdep.found():
            raise DependencyException('Dependency "%s" not found' % name)
        return fwdep
    if pkg_exc is not None:
        raise pkg_exc
    mlog.log('Dependency', mlog.bold(name), 'found:', mlog.red('NO'))
    return pkgdep

# This has to be at the end so the classes it references
# are defined.
packages = {'boost': BoostDependency,
            'gtest': GTestDependency,
            'gmock': GMockDependency,
            'qt5': Qt5Dependency,
            'qt4': Qt4Dependency,
            'gnustep': GnuStepDependency,
            'appleframeworks': AppleFrameworks,
            'wxwidgets' : WxDependency,
            'sdl2' : SDL2Dependency,
            'gl' : GLDependency,
            'threads' : ThreadDependency,
            'python3' : Python3Dependency,
           }
