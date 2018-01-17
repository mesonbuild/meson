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

# This file contains the detection logic for miscellaneous external dependencies.

import glob
import os
import re
import shlex
import shutil
import sysconfig

from pathlib import Path

from .. import mlog
from .. import mesonlib
from ..environment import detect_cpu_family

from .base import (
    DependencyException, DependencyMethods, ExternalDependency,
    ExternalProgram, ExtraFrameworkDependency, PkgConfigDependency,
    ConfigToolDependency,
)

# On windows 3 directory layouts are supported:
# * The default layout (versioned) installed:
#   - $BOOST_ROOT/include/boost-x_x/boost/*.hpp
#   - $BOOST_ROOT/lib/*.lib
# * The non-default layout (system) installed:
#   - $BOOST_ROOT/include/boost/*.hpp
#   - $BOOST_ROOT/lib/*.lib
# * The pre-built binaries from sf.net:
#   - $BOOST_ROOT/boost/*.hpp
#   - $BOOST_ROOT/lib<arch>-<compiler>/*.lib where arch=32/64 and compiler=msvc-14.1
#
# Library names supported:
#   - libboost_<module>-<compiler>-mt-gd-x_x.lib (static)
#   - boost_<module>-<compiler>-mt-gd-x_x.lib|.dll (shared)
#   - libboost_<module>.lib (static)
#   - boost_<module>.lib|.dll (shared)
#   where compiler is vc141 for example.
#
# NOTE: -gd means runtime and build time debugging is on
#       -mt means threading=multi
#
# The `modules` argument accept library names. This is because every module that
# has libraries to link against also has multiple options regarding how to
# link. See for example:
# * http://www.boost.org/doc/libs/1_65_1/libs/test/doc/html/boost_test/usage_variants.html
# * http://www.boost.org/doc/libs/1_65_1/doc/html/stacktrace/configuration_and_build.html
# * http://www.boost.org/doc/libs/1_65_1/libs/math/doc/html/math_toolkit/main_tr1.html

# **On Unix**, official packaged versions of boost libraries follow the following schemes:
#
# Linux / Debian:   libboost_<module>.so.1.66.0 -> libboost_<module>.so
# Linux / Red Hat:  libboost_<module>.so.1.66.0 -> libboost_<module>.so
# Linux / OpenSuse: libboost_<module>.so.1.66.0 -> libboost_<module>.so
# Mac   / homebrew: libboost_<module>.dylib + libboost_<module>-mt.dylib    (location = /usr/local/lib)
# Mac   / macports: libboost_<module>.dylib + libboost_<module>-mt.dylib    (location = /opt/local/lib)
#
# Its not clear that any other abi tags (e.g. -gd) are used in official packages.
#
# On Linux systems, boost libs have multithreading support enabled, but without the -mt tag.
#
# Boost documentation recommends using complex abi tags like "-lboost_regex-gcc34-mt-d-1_36".
# (See http://www.boost.org/doc/libs/1_66_0/more/getting_started/unix-variants.html#library-naming)
# However, its not clear that any Unix distribution follows this scheme.
# Furthermore, the boost documentation for unix above uses examples from windows like
#   "libboost_regex-vc71-mt-d-x86-1_34.lib", so apparently the abi tags may be more aimed at windows.
#
# Probably we should use the linker search path to decide which libraries to use.  This will
# make it possible to find the macports boost libraries without setting BOOST_ROOT, and will
# also mean that it would be possible to use user-installed boost libraries when official
# packages are installed.
#
# We thus follow the following strategy:
# 1. Look for libraries using compiler.find_library( )
#   1.1 On Linux, just look for boost_<module>
#   1.2 On other systems (e.g. Mac) look for boost_<module>-mt if multithreading.
#   1.3 Otherwise look for boost_<module>
# 2. Fall back to previous approach
#   2.1. Search particular directories.
#   2.2. Find boost libraries with unknown suffixes using file-name globbing.

# TODO: Unix: Don't assume we know where the boost dir is, rely on -Idir and -Ldir being set.
# TODO: Determine a suffix (e.g. "-mt" or "") and use it.
# TODO: Get_win_link_args( ) and get_link_args( )
# TODO: Genericize: 'args += ['-L' + dir] => args += self.compiler.get_linker_search_args(dir)
# TODO: Allow user to specify suffix in BOOST_SUFFIX, or add specific options like BOOST_DEBUG for 'd' for debug.
# TODO: fix cross:
#          is_windows() -> for_windows(self.want_cross, self.env)
#          is_osx() and self.want_cross -> for_darwin(self.want_cross, self.env)

class BoostDependency(ExternalDependency):
    def __init__(self, environment, kwargs):
        super().__init__('boost', environment, 'cpp', kwargs)
        self.need_static_link = ['boost_exception', 'boost_test_exec_monitor']
        self.is_debug = environment.cmd_line_options.buildtype.startswith('debug')
        threading = kwargs.get("threading", "multi")
        self.is_multithreading = threading == "multi"

        self.requested_modules = self.get_requested(kwargs)

        self.boost_root = None
        self.boost_roots = []
        self.incdir = None
        self.libdir = None

        if 'BOOST_ROOT' in os.environ:
            self.boost_root = os.environ['BOOST_ROOT']
            self.boost_roots = [self.boost_root]
            if not os.path.isabs(self.boost_root):
                raise DependencyException('BOOST_ROOT must be an absolute path.')
        if 'BOOST_INCLUDEDIR' in os.environ:
            self.incdir = os.environ['BOOST_INCLUDEDIR']
        if 'BOOST_LIBRARYDIR' in os.environ:
            self.libdir = os.environ['BOOST_LIBRARYDIR']

        if self.boost_root is None:
            if mesonlib.is_windows():
                self.boost_roots = self.detect_win_roots()
            else:
                self.boost_roots = self.detect_nix_roots()

        if self.boost_root is None and not self.boost_roots:
            self.log_fail()
            return

        if self.incdir is None:
            if mesonlib.is_windows():
                self.incdir = self.detect_win_incdir()
            else:
                self.incdir = self.detect_nix_incdir()

        if self.incdir is None and mesonlib.is_windows():
            self.log_fail()
            return

        invalid_modules = [c for c in self.requested_modules if 'boost_' + c not in BOOST_LIBS]

        # previous versions of meson allowed include dirs as modules
        remove = []
        for m in invalid_modules:
            if m in BOOST_DIRS:
                mlog.warning('Requested boost library', mlog.bold(m), 'that doesn\'t exist. '
                             'This will be an error in the future')
                remove.append(m)

        self.requested_modules = [x for x in self.requested_modules if x not in remove]
        invalid_modules = [x for x in invalid_modules if x not in remove]

        if invalid_modules:
            mlog.log(mlog.red('ERROR:'), 'Invalid Boost modules: ' + ', '.join(invalid_modules))
            self.log_fail()
            return

        mlog.debug('Boost library root dir is', mlog.bold(self.boost_root))
        mlog.debug('Boost include directory is', mlog.bold(self.incdir))

        self.lib_modules = {}
        self.detect_version()
        if self.is_found:
            self.detect_lib_modules()
            mlog.debug('Boost library directory is', mlog.bold(self.libdir))
            for m in self.requested_modules:
                if 'boost_' + m not in self.lib_modules:
                    mlog.debug('Requested Boost library {!r} not found'.format(m))
                    self.log_fail()
                    self.is_found = False
                    return
            self.log_success()
        else:
            self.log_fail()


    def log_fail(self):
        module_str = ', '.join(self.requested_modules)
        mlog.log("Dependency Boost (%s) found:" % module_str, mlog.red('NO'))

    def log_success(self):
        module_str = ', '.join(self.requested_modules)
        if self.boost_root:
            info = self.version + ', ' + self.boost_root
        else:
            info = self.version
        mlog.log('Dependency Boost (%s) found:' % module_str, mlog.green('YES'), info)

    def detect_nix_roots(self):
        return [os.path.abspath(os.path.join(x, '..'))
                for x in self.compiler.get_default_include_dirs()]

    def detect_win_roots(self):
        res = []
        # Where boost documentation says it should be
        globtext = 'C:\\Program Files\\boost\\boost_*'
        files = glob.glob(globtext)
        res.extend(files)

        # Where boost built from source actually installs it
        if os.path.isdir('C:\\Boost'):
            res.append('C:\\Boost')

        # Where boost prebuilt binaries are
        globtext = 'C:\\local\\boost_*'
        files = glob.glob(globtext)
        res.extend(files)
        return res

    def detect_nix_incdir(self):
        if self.boost_root:
            return os.path.join(self.boost_root, 'include')
        return None

    # FIXME: Should pick a version that matches the requested version
    # Returns the folder that contains the boost folder.
    def detect_win_incdir(self):
        for root in self.boost_roots:
            globtext = os.path.join(root, 'include', 'boost-*')
            incdirs = glob.glob(globtext)
            if len(incdirs) > 0:
                return incdirs[0]
            incboostdir = os.path.join(root, 'include', 'boost')
            if os.path.isdir(incboostdir):
                return os.path.join(root, 'include')
            incboostdir = os.path.join(root, 'boost')
            if os.path.isdir(incboostdir):
                return root
        return None

    def get_compile_args(self):
        args = []
        include_dir = self.incdir

        # Use "-isystem" when including boost headers instead of "-I"
        # to avoid compiler warnings/failures when "-Werror" is used

        # Careful not to use "-isystem" on default include dirs as it
        # breaks some of the headers for certain gcc versions

        # For example, doing g++ -isystem /usr/include on a simple
        # "int main()" source results in the error:
        # "/usr/include/c++/6.3.1/cstdlib:75:25: fatal error: stdlib.h: No such file or directory"

        # See https://gcc.gnu.org/bugzilla/show_bug.cgi?id=70129
        # and http://stackoverflow.com/questions/37218953/isystem-on-a-system-include-directory-causes-errors
        # for more details

        if include_dir and include_dir not in self.compiler.get_default_include_dirs():
            args.append("".join(self.compiler.get_include_args(include_dir, True)))
        return args

    def get_requested(self, kwargs):
        candidates = mesonlib.extract_as_list(kwargs, 'modules')
        for c in candidates:
            if not isinstance(c, str):
                raise DependencyException('Boost module argument is not a string.')
        return candidates

    def detect_version(self):
        try:
            version = self.compiler.get_define('BOOST_LIB_VERSION', '#include <boost/version.hpp>', self.env, self.get_compile_args(), [])
        except mesonlib.EnvironmentException:
            return
        except TypeError:
            return
        # Remove quotes
        version = version[1:-1]
        # Fix version string
        self.version = version.replace('_', '.')
        self.is_found = True

    def detect_lib_modules(self):
        if mesonlib.is_windows():
            return self.detect_lib_modules_win()
        return self.detect_lib_modules_nix()

    def modname_from_filename(self, filename):
        modname = os.path.basename(filename)
        modname = modname.split('.', 1)[0]
        modname = modname.split('-', 1)[0]
        if modname.startswith('libboost'):
            modname = modname[3:]
        return modname

    def detect_lib_modules_win(self):
        arch = detect_cpu_family(self.env.coredata.compilers)
        comp_ts_version = self.env.detect_cpp_compiler(self.want_cross).get_toolset_version()
        compiler_ts = comp_ts_version.split('.')
        compiler = 'vc{}{}'.format(compiler_ts[0], compiler_ts[1])
        if not self.libdir:
            # The libdirs in the distributed binaries (from sf)
            if arch == 'x86':
                lib_sf = 'lib32-msvc-{}'.format(comp_ts_version)
            elif arch == 'x86_64':
                lib_sf = 'lib64-msvc-{}'.format(comp_ts_version)
            else:
                # Does anyone do Boost cross-compiling to other archs on Windows?
                lib_sf = None
            if self.boost_root:
                roots = [self.boost_root]
            else:
                roots = self.boost_roots
            for root in roots:
                # The default libdir when building
                libdir = os.path.join(root, 'lib')
                if os.path.isdir(libdir):
                    self.libdir = libdir
                    break
                if lib_sf:
                    full_path = os.path.join(root, lib_sf)
                    if os.path.isdir(full_path):
                        self.libdir = full_path
                        break

        if not self.libdir:
            return

        for name in self.need_static_link:
            libname = "lib{}".format(name) + '-' + compiler
            if self.is_multithreading:
                libname = libname + '-mt'
            if self.is_debug:
                libname = libname + '-gd'
            libname = libname + "-{}.lib".format(self.version.replace('.', '_'))
            if os.path.isfile(os.path.join(self.libdir, libname)):
                self.lib_modules[self.modname_from_filename(libname)] = [libname]
            else:
                libname = "lib{}.lib".format(name)
                if os.path.isfile(os.path.join(self.libdir, libname)):
                    self.lib_modules[name[3:]] = [libname]

        # globber1 applies to a layout=system installation
        # globber2 applies to a layout=versioned installation
        globber1 = 'libboost_*' if self.static else 'boost_*'
        globber2 = globber1 + '-' + compiler
        if self.is_multithreading:
            globber2 = globber2 + '-mt'
        if self.is_debug:
            globber2 = globber2 + '-gd'
        globber2 = globber2 + '-{}'.format(self.version.replace('.', '_'))
        globber2_matches = glob.glob(os.path.join(self.libdir, globber2 + '.lib'))
        for entry in globber2_matches:
            fname = os.path.basename(entry)
            self.lib_modules[self.modname_from_filename(fname)] = [fname]
        if len(globber2_matches) == 0:
            for entry in glob.glob(os.path.join(self.libdir, globber1 + '.lib')):
                if self.static:
                    fname = os.path.basename(entry)
                    self.lib_modules[self.modname_from_filename(fname)] = [fname]

    def detect_lib_modules_nix(self):
        all_found = True
        for module in self.requested_modules:
            args = None
            libname = 'boost_' + module
            if self.is_multithreading and mesonlib.for_darwin(self.want_cross, self.env):
                # - Linux leaves off -mt but libraries are multithreading-aware.
                # - Mac requires -mt for multithreading, so should not fall back to non-mt libraries.
                libname = libname + '-mt'
            args = self.compiler.find_library(libname, self.env, self.extra_lib_dirs())
            if args is None:
                mlog.debug('Couldn\'t find library "{}" for boost module "{}"'.format(module, libname))
                all_found = False
            else:
                mlog.debug('Link args for boost module "{}" are {}'.format(module, args))
                self.lib_modules['boost_' + module] = args
        if all_found:
            return

        if self.static:
            libsuffix = 'a'
        elif mesonlib.is_osx() and not self.want_cross:
            libsuffix = 'dylib'
        else:
            libsuffix = 'so'

        globber = 'libboost_*.{}'.format(libsuffix)
        if self.libdir:
            libdirs = [self.libdir]
        elif self.boost_root is None:
            libdirs = mesonlib.get_library_dirs()
        else:
            libdirs = [os.path.join(self.boost_root, 'lib')]
        for libdir in libdirs:
            for name in self.need_static_link:
                libname = 'lib{}.a'.format(name)
                if os.path.isfile(os.path.join(libdir, libname)):
                    self.lib_modules[name] = [libname]
            for entry in glob.glob(os.path.join(libdir, globber)):
                # I'm not 100% sure what to do here. Some distros
                # have modules such as thread only as -mt versions.
                # On debian all packages are built threading=multi
                # but not suffixed with -mt.
                # FIXME: implement detect_lib_modules_{debian, redhat, ...}
                # FIXME: this wouldn't work with -mt-gd either. -BDR
                if self.is_multithreading and mesonlib.is_debianlike():
                    pass
                elif self.is_multithreading and entry.endswith('-mt.{}'.format(libsuffix)):
                    pass
                elif not entry.endswith('-mt.{}'.format(libsuffix)):
                    pass
                else:
                    continue
                modname = self.modname_from_filename(entry)
                if modname not in self.lib_modules:
                    self.lib_modules[modname] = [entry]

    def get_win_link_args(self):
        args = []
        # TODO: should this check self.libdir?
        if self.libdir:
            args.append('-L' + self.libdir)
        for lib in self.requested_modules:
            args += self.lib_modules['boost_' + lib]
        return args

    def extra_lib_dirs(self):
        dirs = []
        if self.boost_root:
            dirs = [os.path.join(self.boost_root, 'lib')]
        elif self.libdir:
            dirs = [self.libdir]
        return dirs

    def get_link_args(self):
        if mesonlib.is_windows():
            return self.get_win_link_args()
        args = []
        for dir in self.extra_lib_dirs():
            args += ['-L' + dir]
        for lib in self.requested_modules:
            args += self.lib_modules['boost_' + lib]
        return args

    def get_sources(self):
        return []

    def need_threads(self):
        return 'thread' in self.requested_modules


class MPIDependency(ExternalDependency):
    def __init__(self, environment, kwargs):
        language = kwargs.get('language', 'c')
        super().__init__('mpi', environment, language, kwargs)
        required = kwargs.pop('required', True)
        kwargs['required'] = False
        kwargs['silent'] = True
        self.is_found = False

        # NOTE: Only OpenMPI supplies a pkg-config file at the moment.
        if language == 'c':
            env_vars = ['MPICC']
            pkgconfig_files = ['ompi-c']
            default_wrappers = ['mpicc']
        elif language == 'cpp':
            env_vars = ['MPICXX']
            pkgconfig_files = ['ompi-cxx']
            default_wrappers = ['mpic++', 'mpicxx', 'mpiCC']
        elif language == 'fortran':
            env_vars = ['MPIFC', 'MPIF90', 'MPIF77']
            pkgconfig_files = ['ompi-fort']
            default_wrappers = ['mpifort', 'mpif90', 'mpif77']
        else:
            raise DependencyException('Language {} is not supported with MPI.'.format(language))

        for pkg in pkgconfig_files:
            try:
                pkgdep = PkgConfigDependency(pkg, environment, kwargs, language=self.language)
                if pkgdep.found():
                    self.compile_args = pkgdep.get_compile_args()
                    self.link_args = pkgdep.get_link_args()
                    self.version = pkgdep.get_version()
                    self.is_found = True
                    self.pcdep = pkgdep
                    break
            except Exception:
                pass

        if not self.is_found:
            # Prefer environment.
            for var in env_vars:
                if var in os.environ:
                    wrappers = [os.environ[var]]
                    break
            else:
                # Or search for default wrappers.
                wrappers = default_wrappers

            for prog in wrappers:
                result = self._try_openmpi_wrapper(prog)
                if result is not None:
                    self.is_found = True
                    self.version = result[0]
                    self.compile_args = self._filter_compile_args(result[1])
                    self.link_args = self._filter_link_args(result[2])
                    break
                result = self._try_other_wrapper(prog)
                if result is not None:
                    self.is_found = True
                    self.version = result[0]
                    self.compile_args = self._filter_compile_args(result[1])
                    self.link_args = self._filter_link_args(result[2])
                    break

        if not self.is_found and mesonlib.is_windows():
            result = self._try_msmpi()
            if result is not None:
                self.is_found = True
                self.version, self.compile_args, self.link_args = result

        if self.is_found:
            mlog.log('Dependency', mlog.bold(self.name), 'for', self.language, 'found:', mlog.green('YES'), self.version)
        else:
            mlog.log('Dependency', mlog.bold(self.name), 'for', self.language, 'found:', mlog.red('NO'))
            if required:
                raise DependencyException('MPI dependency {!r} not found'.format(self.name))

    def _filter_compile_args(self, args):
        """
        MPI wrappers return a bunch of garbage args.
        Drop -O2 and everything that is not needed.
        """
        result = []
        multi_args = ('-I', )
        if self.language == 'fortran':
            fc = self.env.coredata.compilers['fortran']
            multi_args += fc.get_module_incdir_args()

        include_next = False
        for f in args:
            if f.startswith(('-D', '-f') + multi_args) or f == '-pthread' \
                    or (f.startswith('-W') and f != '-Wall' and not f.startswith('-Werror')):
                result.append(f)
                if f in multi_args:
                    # Path is a separate argument.
                    include_next = True
            elif include_next:
                include_next = False
                result.append(f)
        return result

    def _filter_link_args(self, args):
        """
        MPI wrappers return a bunch of garbage args.
        Drop -O2 and everything that is not needed.
        """
        result = []
        include_next = False
        for f in args:
            if f.startswith(('-L', '-l', '-Xlinker')) or f == '-pthread' \
                    or (f.startswith('-W') and f != '-Wall' and not f.startswith('-Werror')):
                result.append(f)
                if f in ('-L', '-Xlinker'):
                    include_next = True
            elif include_next:
                include_next = False
                result.append(f)
        return result

    def _try_openmpi_wrapper(self, prog):
        prog = ExternalProgram(prog, silent=True)
        if prog.found():
            cmd = prog.get_command() + ['--showme:compile']
            p, o, e = mesonlib.Popen_safe(cmd)
            p.wait()
            if p.returncode != 0:
                mlog.debug('Command', mlog.bold(cmd), 'failed to run:')
                mlog.debug(mlog.bold('Standard output\n'), o)
                mlog.debug(mlog.bold('Standard error\n'), e)
                return
            cargs = shlex.split(o)

            cmd = prog.get_command() + ['--showme:link']
            p, o, e = mesonlib.Popen_safe(cmd)
            p.wait()
            if p.returncode != 0:
                mlog.debug('Command', mlog.bold(cmd), 'failed to run:')
                mlog.debug(mlog.bold('Standard output\n'), o)
                mlog.debug(mlog.bold('Standard error\n'), e)
                return
            libs = shlex.split(o)

            cmd = prog.get_command() + ['--showme:version']
            p, o, e = mesonlib.Popen_safe(cmd)
            p.wait()
            if p.returncode != 0:
                mlog.debug('Command', mlog.bold(cmd), 'failed to run:')
                mlog.debug(mlog.bold('Standard output\n'), o)
                mlog.debug(mlog.bold('Standard error\n'), e)
                return
            version = re.search('\d+.\d+.\d+', o)
            if version:
                version = version.group(0)
            else:
                version = 'none'

            return version, cargs, libs

    def _try_other_wrapper(self, prog):
        prog = ExternalProgram(prog, silent=True)
        if prog.found():
            cmd = prog.get_command() + ['-show']
            p, o, e = mesonlib.Popen_safe(cmd)
            p.wait()
            if p.returncode != 0:
                mlog.debug('Command', mlog.bold(cmd), 'failed to run:')
                mlog.debug(mlog.bold('Standard output\n'), o)
                mlog.debug(mlog.bold('Standard error\n'), e)
                return
            args = shlex.split(o)

            version = 'none'

            return version, args, args

    def _try_msmpi(self):
        if self.language == 'cpp':
            # MS-MPI does not support the C++ version of MPI, only the standard C API.
            return
        if 'MSMPI_INC' not in os.environ:
            return
        incdir = os.environ['MSMPI_INC']
        arch = detect_cpu_family(self.env.coredata.compilers)
        if arch == 'x86':
            if 'MSMPI_LIB32' not in os.environ:
                return
            libdir = os.environ['MSMPI_LIB32']
            post = 'x86'
        elif arch == 'x86_64':
            if 'MSMPI_LIB64' not in os.environ:
                return
            libdir = os.environ['MSMPI_LIB64']
            post = 'x64'
        else:
            return
        if self.language == 'fortran':
            return ('none',
                    ['-I' + incdir, '-I' + os.path.join(incdir, post)],
                    [os.path.join(libdir, 'msmpi.lib'), os.path.join(libdir, 'msmpifec.lib')])
        else:
            return ('none',
                    ['-I' + incdir, '-I' + os.path.join(incdir, post)],
                    [os.path.join(libdir, 'msmpi.lib')])


class ThreadDependency(ExternalDependency):
    def __init__(self, environment, kwargs):
        super().__init__('threads', environment, None, {})
        self.name = 'threads'
        self.is_found = True
        mlog.log('Dependency', mlog.bold(self.name), 'found:', mlog.green('YES'))

    def need_threads(self):
        return True

    def get_version(self):
        return 'unknown'


class Python3Dependency(ExternalDependency):
    def __init__(self, environment, kwargs):
        super().__init__('python3', environment, None, kwargs)
        self.name = 'python3'
        self.static = kwargs.get('static', False)
        # We can only be sure that it is Python 3 at this point
        self.version = '3'
        self.pkgdep = None
        if DependencyMethods.PKGCONFIG in self.methods:
            try:
                self.pkgdep = PkgConfigDependency('python3', environment, kwargs)
                if self.pkgdep.found():
                    self.compile_args = self.pkgdep.get_compile_args()
                    self.link_args = self.pkgdep.get_link_args()
                    self.version = self.pkgdep.get_version()
                    self.is_found = True
                    self.pcdep = self.pkgdep
                    return
                else:
                    self.pkgdep = None
            except Exception:
                pass
        if not self.is_found:
            if mesonlib.is_windows() and DependencyMethods.SYSCONFIG in self.methods:
                self._find_libpy3_windows(environment)
            elif mesonlib.is_osx() and DependencyMethods.EXTRAFRAMEWORK in self.methods:
                # In OSX the Python 3 framework does not have a version
                # number in its name.
                # There is a python in /System/Library/Frameworks, but that's
                # python 2, Python 3 will always bin in /Library
                fw = ExtraFrameworkDependency(
                    'python', False, '/Library/Frameworks', self.env, self.language, kwargs)
                if fw.found():
                    self.compile_args = fw.get_compile_args()
                    self.link_args = fw.get_link_args()
                    self.is_found = True
        if self.is_found:
            mlog.log('Dependency', mlog.bold(self.name), 'found:', mlog.green('YES'))
        else:
            mlog.log('Dependency', mlog.bold(self.name), 'found:', mlog.red('NO'))

    @staticmethod
    def get_windows_python_arch():
        pyplat = sysconfig.get_platform()
        if pyplat == 'mingw':
            pycc = sysconfig.get_config_var('CC')
            if pycc.startswith('x86_64'):
                return '64'
            elif pycc.startswith(('i686', 'i386')):
                return '32'
            else:
                mlog.log('MinGW Python built with unknown CC {!r}, please file'
                         'a bug'.format(pycc))
                return None
        elif pyplat == 'win32':
            return '32'
        elif pyplat in ('win64', 'win-amd64'):
            return '64'
        mlog.log('Unknown Windows Python platform {!r}'.format(pyplat))
        return None

    def get_windows_link_args(self):
        pyplat = sysconfig.get_platform()
        if pyplat.startswith('win'):
            vernum = sysconfig.get_config_var('py_version_nodot')
            if self.static:
                libname = 'libpython{}.a'.format(vernum)
            else:
                libname = 'python{}.lib'.format(vernum)
            lib = Path(sysconfig.get_config_var('base')) / 'libs' / libname
        elif pyplat == 'mingw':
            if self.static:
                libname = sysconfig.get_config_var('LIBRARY')
            else:
                libname = sysconfig.get_config_var('LDLIBRARY')
            lib = Path(sysconfig.get_config_var('LIBDIR')) / libname
        if not lib.exists():
            mlog.log('Could not find Python3 library {!r}'.format(str(lib)))
            return None
        return [str(lib)]

    def _find_libpy3_windows(self, env):
        '''
        Find python3 libraries on Windows and also verify that the arch matches
        what we are building for.
        '''
        pyarch = self.get_windows_python_arch()
        if pyarch is None:
            self.is_found = False
            return
        arch = detect_cpu_family(env.coredata.compilers)
        if arch == 'x86':
            arch = '32'
        elif arch == 'x86_64':
            arch = '64'
        else:
            # We can't cross-compile Python 3 dependencies on Windows yet
            mlog.log('Unknown architecture {!r} for'.format(arch),
                     mlog.bold(self.name))
            self.is_found = False
            return
        # Pyarch ends in '32' or '64'
        if arch != pyarch:
            mlog.log('Need', mlog.bold(self.name), 'for {}-bit, but '
                     'found {}-bit'.format(arch, pyarch))
            self.is_found = False
            return
        # This can fail if the library is not found
        largs = self.get_windows_link_args()
        if largs is None:
            self.is_found = False
            return
        self.link_args = largs
        # Compile args
        inc = sysconfig.get_path('include')
        platinc = sysconfig.get_path('platinclude')
        self.compile_args = ['-I' + inc]
        if inc != platinc:
            self.compile_args.append('-I' + platinc)
        self.version = sysconfig.get_config_var('py_version')
        self.is_found = True

    def get_methods(self):
        if mesonlib.is_windows():
            return [DependencyMethods.PKGCONFIG, DependencyMethods.SYSCONFIG]
        elif mesonlib.is_osx():
            return [DependencyMethods.PKGCONFIG, DependencyMethods.EXTRAFRAMEWORK]
        else:
            return [DependencyMethods.PKGCONFIG]

    def get_pkgconfig_variable(self, variable_name, kwargs):
        if self.pkgdep:
            return self.pkgdep.get_pkgconfig_variable(variable_name, kwargs)
        else:
            return super().get_pkgconfig_variable(variable_name, kwargs)


class PcapDependency(ExternalDependency):
    def __init__(self, environment, kwargs):
        super().__init__('pcap', environment, None, kwargs)
        kwargs['required'] = False
        if DependencyMethods.PKGCONFIG in self.methods:
            try:
                pcdep = PkgConfigDependency('pcap', environment, kwargs)
                if pcdep.found():
                    self.type_name = 'pkgconfig'
                    self.is_found = True
                    self.compile_args = pcdep.get_compile_args()
                    self.link_args = pcdep.get_link_args()
                    self.version = pcdep.get_version()
                    self.pcdep = pcdep
                    return
            except Exception as e:
                mlog.debug('Pcap not found via pkgconfig. Trying next, error was:', str(e))
        if DependencyMethods.CONFIG_TOOL in self.methods:
            try:
                ctdep = ConfigToolDependency.factory(
                    'pcap', environment, None, kwargs, ['pcap-config'], 'pcap-config')
                if ctdep.found():
                    self.config = ctdep.config
                    self.type_name = 'config-tool'
                    self.compile_args = ctdep.get_config_value(['--cflags'], 'compile_args')
                    self.link_args = ctdep.get_config_value(['--libs'], 'link_args')
                    self.version = self.get_pcap_lib_version()
                    self.is_found = True
                    return
            except Exception as e:
                mlog.debug('Pcap not found via pcap-config. Trying next, error was:', str(e))

    def get_methods(self):
        if mesonlib.is_osx():
            return [DependencyMethods.PKGCONFIG, DependencyMethods.CONFIG_TOOL, DependencyMethods.EXTRAFRAMEWORK]
        else:
            return [DependencyMethods.PKGCONFIG, DependencyMethods.CONFIG_TOOL]

    def get_pcap_lib_version(self):
        return self.compiler.get_return_value('pcap_lib_version', 'string',
                                              '#include <pcap.h>', self.env, [], [self])


class CupsDependency(ExternalDependency):
    def __init__(self, environment, kwargs):
        super().__init__('cups', environment, None, kwargs)
        kwargs['required'] = False
        if DependencyMethods.PKGCONFIG in self.methods:
            try:
                pcdep = PkgConfigDependency('cups', environment, kwargs)
                if pcdep.found():
                    self.type_name = 'pkgconfig'
                    self.is_found = True
                    self.compile_args = pcdep.get_compile_args()
                    self.link_args = pcdep.get_link_args()
                    self.version = pcdep.get_version()
                    self.pcdep = pcdep
                    return
            except Exception as e:
                mlog.debug('cups not found via pkgconfig. Trying next, error was:', str(e))
        if DependencyMethods.CONFIG_TOOL in self.methods:
            try:
                ctdep = ConfigToolDependency.factory(
                    'cups', environment, None, kwargs, ['cups-config'], 'cups-config')
                if ctdep.found():
                    self.config = ctdep.config
                    self.type_name = 'config-tool'
                    self.version = ctdep.version
                    self.compile_args = ctdep.get_config_value(['--cflags'], 'compile_args')
                    self.link_args = ctdep.get_config_value(['--ldflags', '--libs'], 'link_args')
                    self.is_found = True
                    return
            except Exception as e:
                mlog.debug('cups not found via cups-config. Trying next, error was:', str(e))
        if DependencyMethods.EXTRAFRAMEWORK in self.methods:
            if mesonlib.is_osx():
                fwdep = ExtraFrameworkDependency('cups', False, None, self.env,
                                                 self.language, kwargs)
                if fwdep.found():
                    self.is_found = True
                    self.compile_args = fwdep.get_compile_args()
                    self.link_args = fwdep.get_link_args()
                    self.version = fwdep.get_version()
                    return
            mlog.log('Dependency', mlog.bold('cups'), 'found:', mlog.red('NO'))

    def get_methods(self):
        if mesonlib.is_osx():
            return [DependencyMethods.PKGCONFIG, DependencyMethods.CONFIG_TOOL, DependencyMethods.EXTRAFRAMEWORK]
        else:
            return [DependencyMethods.PKGCONFIG, DependencyMethods.CONFIG_TOOL]


class LibWmfDependency(ExternalDependency):
    def __init__(self, environment, kwargs):
        super().__init__('libwmf', environment, None, kwargs)
        if DependencyMethods.PKGCONFIG in self.methods:
            try:
                kwargs['required'] = False
                pcdep = PkgConfigDependency('libwmf', environment, kwargs)
                if pcdep.found():
                    self.type_name = 'pkgconfig'
                    self.is_found = True
                    self.compile_args = pcdep.get_compile_args()
                    self.link_args = pcdep.get_link_args()
                    self.version = pcdep.get_version()
                    self.pcdep = pcdep
                    return
            except Exception as e:
                mlog.debug('LibWmf not found via pkgconfig. Trying next, error was:', str(e))
        if DependencyMethods.CONFIG_TOOL in self.methods:
            try:
                ctdep = ConfigToolDependency.factory(
                    'libwmf', environment, None, kwargs, ['libwmf-config'], 'libwmf-config')
                if ctdep.found():
                    self.config = ctdep.config
                    self.type_name = 'config-too'
                    self.version = ctdep.version
                    self.compile_args = ctdep.get_config_value(['--cflags'], 'compile_args')
                    self.link_args = ctdep.get_config_value(['--libs'], 'link_args')
                    self.is_found = True
                    return
            except Exception as e:
                mlog.debug('cups not found via libwmf-config. Trying next, error was:', str(e))

    def get_methods(self):
        if mesonlib.is_osx():
            return [DependencyMethods.PKGCONFIG, DependencyMethods.CONFIG_TOOL, DependencyMethods.EXTRAFRAMEWORK]
        else:
            return [DependencyMethods.PKGCONFIG, DependencyMethods.CONFIG_TOOL]


# Generated with boost_names.py
BOOST_LIBS = [
    'boost_atomic',
    'boost_chrono',
    'boost_chrono',
    'boost_container',
    'boost_context',
    'boost_coroutine',
    'boost_date_time',
    'boost_exception',
    'boost_fiber',
    'boost_filesystem',
    'boost_graph',
    'boost_iostreams',
    'boost_locale',
    'boost_log',
    'boost_log_setup',
    'boost_math_tr1',
    'boost_math_tr1f',
    'boost_math_tr1l',
    'boost_math_c99',
    'boost_math_c99f',
    'boost_math_c99l',
    'boost_math_tr1',
    'boost_math_tr1f',
    'boost_math_tr1l',
    'boost_math_c99',
    'boost_math_c99f',
    'boost_math_c99l',
    'boost_math_tr1',
    'boost_math_tr1f',
    'boost_math_tr1l',
    'boost_math_c99',
    'boost_math_c99f',
    'boost_math_c99l',
    'boost_math_tr1',
    'boost_math_tr1f',
    'boost_math_tr1l',
    'boost_math_c99',
    'boost_math_c99f',
    'boost_math_c99l',
    'boost_math_tr1',
    'boost_math_tr1f',
    'boost_math_tr1l',
    'boost_math_c99',
    'boost_math_c99f',
    'boost_math_c99l',
    'boost_math_tr1',
    'boost_math_tr1f',
    'boost_math_tr1l',
    'boost_math_c99',
    'boost_math_c99f',
    'boost_math_c99l',
    'boost_mpi',
    'boost_program_options',
    'boost_python',
    'boost_python3',
    'boost_numpy',
    'boost_numpy3',
    'boost_random',
    'boost_regex',
    'boost_serialization',
    'boost_wserialization',
    'boost_signals',
    'boost_stacktrace_noop',
    'boost_stacktrace_backtrace',
    'boost_stacktrace_addr2line',
    'boost_stacktrace_basic',
    'boost_stacktrace_windbg',
    'boost_stacktrace_windbg_cached',
    'boost_system',
    'boost_prg_exec_monitor',
    'boost_test_exec_monitor',
    'boost_unit_test_framework',
    'boost_thread',
    'boost_timer',
    'boost_type_erasure',
    'boost_wave'
]

BOOST_DIRS = [
    'lambda',
    'optional',
    'convert',
    'system',
    'uuid',
    'archive',
    'align',
    'timer',
    'chrono',
    'gil',
    'logic',
    'signals',
    'predef',
    'tr1',
    'multi_index',
    'property_map',
    'multi_array',
    'context',
    'random',
    'endian',
    'circular_buffer',
    'proto',
    'assign',
    'format',
    'math',
    'phoenix',
    'graph',
    'locale',
    'mpl',
    'pool',
    'unordered',
    'core',
    'exception',
    'ptr_container',
    'flyweight',
    'range',
    'typeof',
    'thread',
    'move',
    'spirit',
    'dll',
    'compute',
    'serialization',
    'ratio',
    'msm',
    'config',
    'metaparse',
    'coroutine2',
    'qvm',
    'program_options',
    'concept',
    'detail',
    'hana',
    'concept_check',
    'compatibility',
    'variant',
    'type_erasure',
    'mpi',
    'test',
    'fusion',
    'log',
    'sort',
    'local_function',
    'units',
    'functional',
    'preprocessor',
    'integer',
    'container',
    'polygon',
    'interprocess',
    'numeric',
    'iterator',
    'wave',
    'lexical_cast',
    'multiprecision',
    'utility',
    'tti',
    'asio',
    'dynamic_bitset',
    'algorithm',
    'xpressive',
    'bimap',
    'signals2',
    'type_traits',
    'regex',
    'statechart',
    'parameter',
    'icl',
    'python',
    'lockfree',
    'intrusive',
    'io',
    'pending',
    'geometry',
    'tuple',
    'iostreams',
    'heap',
    'atomic',
    'filesystem',
    'smart_ptr',
    'function',
    'fiber',
    'type_index',
    'accumulators',
    'function_types',
    'coroutine',
    'vmd',
    'date_time',
    'property_tree',
    'bind'
]
