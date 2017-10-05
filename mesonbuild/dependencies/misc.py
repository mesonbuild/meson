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

from .. import mlog
from .. import mesonlib
from ..mesonlib import Popen_safe, extract_as_list
from ..environment import detect_cpu_family

from .base import DependencyException, DependencyMethods
from .base import ExternalDependency, ExternalProgram, ExtraFrameworkDependency, PkgConfigDependency

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
# NOTE: -gb means runtime and build time debugging is on
#       -mt means threading=multi
#
# The `modules` argument accept library names. This is because every module that
# has libraries to link against also has multiple options regarding how to
# link. See for example:
# * http://www.boost.org/doc/libs/1_65_1/libs/test/doc/html/boost_test/usage_variants.html
# * http://www.boost.org/doc/libs/1_65_1/doc/html/stacktrace/configuration_and_build.html
# * http://www.boost.org/doc/libs/1_65_1/libs/math/doc/html/math_toolkit/main_tr1.html

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

        if self.incdir is None:
            self.log_fail()
            return

        mlog.debug('Boost library root dir is', mlog.bold(self.boost_root))
        mlog.debug('Boost include directory is', mlog.bold(self.incdir))

        self.lib_modules = {}
        self.detect_version()
        if self.is_found:
            self.detect_lib_modules()
            mlog.debug('Boost library directory is', mlog.bold(self.libdir))
            self.validate_requested()
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
        for root in self.boost_roots:
            incdir = os.path.join(root, 'include', 'boost')
            if os.path.isdir(incdir):
                return os.path.join(root, 'include')
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
        candidates = extract_as_list(kwargs, 'modules')
        for c in candidates:
            if not isinstance(c, str):
                raise DependencyException('Boost module argument is not a string.')
            if 'boost_' + c not in BOOST_LIBS:
                raise DependencyException('Dependency {} not found. It is not a valid boost library.'.format(c))
        return candidates

    def validate_requested(self):
        for m in self.requested_modules:
            if 'boost_' + m not in self.lib_modules:
                msg = 'Requested Boost library {!r} not found'
                raise DependencyException(msg.format(m))

    def detect_version(self):
        try:
            ifile = open(os.path.join(self.incdir, 'boost', 'version.hpp'))
        except FileNotFoundError:
            return
        except TypeError:
            return
        with ifile:
            for line in ifile:
                if line.startswith("#define") and 'BOOST_LIB_VERSION' in line:
                    ver = line.split()[-1]
                    ver = ver[1:-1]
                    self.version = ver.replace('_', '.')
                    self.is_found = True
                    return

    def detect_lib_modules(self):
        if mesonlib.is_windows():
            return self.detect_lib_modules_win()
        return self.detect_lib_modules_nix()

    def detect_lib_modules_win(self):
        arch = detect_cpu_family(self.env.coredata.compilers)
        compiler_ts = self.env.detect_cpp_compiler(self.want_cross).get_toolset_version().split('.')
        compiler = 'vc{}{}'.format(compiler_ts[0], compiler_ts[1])
        if not self.libdir:
            # The libdirs in the distributed binaries
            if arch == 'x86':
                gl = 'lib32*'
            elif arch == 'x86_64':
                gl = 'lib64*'
            else:
                # Does anyone do Boost cross-compiling to other archs on Windows?
                gl = None
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
                if gl:
                    tmp = glob.glob(os.path.join(root, gl))
                    if len(tmp) > 0:
                        # FIXME: Should pick the correct version
                        self.libdir = tmp[0]
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
                modname = libname.split('-', 1)[0][3:]
                self.lib_modules[modname] = libname
            else:
                libname = "lib{}.lib".format(name)
                if os.path.isfile(os.path.join(self.libdir, libname)):
                    self.lib_modules[name[3:]] = libname

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
            (_, fname) = os.path.split(entry)
            modname = fname.split('-', 1)
            if len(modname) > 1:
                modname = modname[0]
            else:
                modname = modname.split('.', 1)[0]
            if self.static:
                modname = modname[3:]
            self.lib_modules[modname] = fname
        if len(globber2_matches) == 0:
            for entry in glob.glob(os.path.join(self.libdir, globber1 + '.lib')):
                (_, fname) = os.path.split(entry)
                modname = fname.split('.', 1)[0]
                if self.static:
                    modname = modname[3:]
                    self.lib_modules[modname] = fname

    def detect_lib_modules_nix(self):
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
                    self.lib_modules[name] = libname
            for entry in glob.glob(os.path.join(libdir, globber)):
                lib = os.path.basename(entry)
                name = lib.split('.')[0][3:]
                # I'm not 100% sure what to do here. Some distros
                # have modules such as thread only as -mt versions.
                # On debian all packages are built threading=multi
                # but not suffixed with -mt.
                # FIXME: implement detect_lib_modules_{debian, redhat, ...}
                if self.is_multithreading and mesonlib.is_debianlike():
                    self.lib_modules[name] = lib
                elif self.is_multithreading and entry.endswith('-mt.{}'.format(libsuffix)):
                    self.lib_modules[name] = lib
                elif not entry.endswith('-mt.{}'.format(libsuffix)):
                    self.lib_modules[name] = lib

    def get_win_link_args(self):
        args = []
        # TODO: should this check self.libdir?
        if self.libdir:
            args.append('-L' + self.libdir)
        for lib in self.requested_modules:
            args.append(self.lib_modules['boost_' + lib])
        return args

    def get_link_args(self):
        if mesonlib.is_windows():
            return self.get_win_link_args()
        args = []
        if self.boost_root:
            args.append('-L' + os.path.join(self.boost_root, 'lib'))
        elif self.libdir:
            args.append('-L' + self.libdir)
        for lib in self.requested_modules:
            # The compiler's library detector is the most reliable so use that first.
            default_detect = self.compiler.find_library('boost_' + lib, self.env, [])
            if default_detect is not None:
                args += default_detect
            elif lib in self.lib_modules:
                linkcmd = '-l' + lib
                args.append(linkcmd)
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
                pkgdep = PkgConfigDependency(pkg, environment, kwargs)
                if pkgdep.found():
                    self.compile_args = pkgdep.get_compile_args()
                    self.link_args = pkgdep.get_link_args()
                    self.version = pkgdep.get_version()
                    self.is_found = True
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
        # We can only be sure that it is Python 3 at this point
        self.version = '3'
        if DependencyMethods.PKGCONFIG in self.methods:
            try:
                pkgdep = PkgConfigDependency('python3', environment, kwargs)
                if pkgdep.found():
                    self.compile_args = pkgdep.get_compile_args()
                    self.link_args = pkgdep.get_link_args()
                    self.version = pkgdep.get_version()
                    self.is_found = True
                    return
            except Exception:
                pass
        if not self.is_found:
            if mesonlib.is_windows() and DependencyMethods.SYSCONFIG in self.methods:
                self._find_libpy3_windows(environment)
            elif mesonlib.is_osx() and DependencyMethods.EXTRAFRAMEWORK in self.methods:
                # In OSX the Python 3 framework does not have a version
                # number in its name.
                fw = ExtraFrameworkDependency('python', False, None, self.env,
                                              self.language, kwargs)
                if fw.found():
                    self.compile_args = fw.get_compile_args()
                    self.link_args = fw.get_link_args()
                    self.is_found = True
        if self.is_found:
            mlog.log('Dependency', mlog.bold(self.name), 'found:', mlog.green('YES'))
        else:
            mlog.log('Dependency', mlog.bold(self.name), 'found:', mlog.red('NO'))

    def _find_libpy3_windows(self, env):
        '''
        Find python3 libraries on Windows and also verify that the arch matches
        what we are building for.
        '''
        pyarch = sysconfig.get_platform()
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
        if arch != pyarch[-2:]:
            mlog.log('Need', mlog.bold(self.name),
                     'for {}-bit, but found {}-bit'.format(arch, pyarch[-2:]))
            self.is_found = False
            return
        inc = sysconfig.get_path('include')
        platinc = sysconfig.get_path('platinclude')
        self.compile_args = ['-I' + inc]
        if inc != platinc:
            self.compile_args.append('-I' + platinc)
        # Nothing exposes this directly that I coulf find
        basedir = sysconfig.get_config_var('base')
        vernum = sysconfig.get_config_var('py_version_nodot')
        self.link_args = ['-L{}/libs'.format(basedir),
                          '-lpython{}'.format(vernum)]
        self.version = sysconfig.get_config_var('py_version_short')
        self.is_found = True

    def get_methods(self):
        if mesonlib.is_windows():
            return [DependencyMethods.PKGCONFIG, DependencyMethods.SYSCONFIG]
        elif mesonlib.is_osx():
            return [DependencyMethods.PKGCONFIG, DependencyMethods.EXTRAFRAMEWORK]
        else:
            return [DependencyMethods.PKGCONFIG]


class PcapDependency(ExternalDependency):
    def __init__(self, environment, kwargs):
        super().__init__('pcap', environment, None, kwargs)
        if DependencyMethods.PKGCONFIG in self.methods:
            try:
                kwargs['required'] = False
                pcdep = PkgConfigDependency('pcap', environment, kwargs)
                if pcdep.found():
                    self.type_name = 'pkgconfig'
                    self.is_found = True
                    self.compile_args = pcdep.get_compile_args()
                    self.link_args = pcdep.get_link_args()
                    self.version = pcdep.get_version()
                    return
            except Exception as e:
                mlog.debug('Pcap not found via pkgconfig. Trying next, error was:', str(e))
        if DependencyMethods.PCAPCONFIG in self.methods:
            pcapconf = shutil.which('pcap-config')
            if pcapconf:
                stdo = Popen_safe(['pcap-config', '--cflags'])[1]
                self.compile_args = stdo.strip().split()
                stdo = Popen_safe(['pcap-config', '--libs'])[1]
                self.link_args = stdo.strip().split()
                self.version = self.get_pcap_lib_version()
                self.is_found = True
                mlog.log('Dependency', mlog.bold('pcap'), 'found:',
                         mlog.green('YES'), '(%s)' % pcapconf)
                return
            mlog.debug('Could not find pcap-config binary, trying next.')

    def get_methods(self):
        if mesonlib.is_osx():
            return [DependencyMethods.PKGCONFIG, DependencyMethods.PCAPCONFIG, DependencyMethods.EXTRAFRAMEWORK]
        else:
            return [DependencyMethods.PKGCONFIG, DependencyMethods.PCAPCONFIG]

    def get_pcap_lib_version(self):
        return self.compiler.get_return_value('pcap_lib_version', 'string',
                                              '#include <pcap.h>', self.env, [], [self])


class CupsDependency(ExternalDependency):
    def __init__(self, environment, kwargs):
        super().__init__('cups', environment, None, kwargs)
        if DependencyMethods.PKGCONFIG in self.methods:
            try:
                kwargs['required'] = False
                pcdep = PkgConfigDependency('cups', environment, kwargs)
                if pcdep.found():
                    self.type_name = 'pkgconfig'
                    self.is_found = True
                    self.compile_args = pcdep.get_compile_args()
                    self.link_args = pcdep.get_link_args()
                    self.version = pcdep.get_version()
                    return
            except Exception as e:
                mlog.debug('cups not found via pkgconfig. Trying next, error was:', str(e))
        if DependencyMethods.CUPSCONFIG in self.methods:
            cupsconf = shutil.which('cups-config')
            if cupsconf:
                stdo = Popen_safe(['cups-config', '--cflags'])[1]
                self.compile_args = stdo.strip().split()
                stdo = Popen_safe(['cups-config', '--libs'])[1]
                self.link_args = stdo.strip().split()
                stdo = Popen_safe(['cups-config', '--version'])[1]
                self.version = stdo.strip().split()
                self.is_found = True
                mlog.log('Dependency', mlog.bold('cups'), 'found:',
                         mlog.green('YES'), '(%s)' % cupsconf)
                return
            mlog.debug('Could not find cups-config binary, trying next.')
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
            return [DependencyMethods.PKGCONFIG, DependencyMethods.CUPSCONFIG, DependencyMethods.EXTRAFRAMEWORK]
        else:
            return [DependencyMethods.PKGCONFIG, DependencyMethods.CUPSCONFIG]

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
