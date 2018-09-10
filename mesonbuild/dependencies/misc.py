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

import functools
import os
import re
import shlex
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


class MPIDependency(ExternalDependency):

    def __init__(self, environment, kwargs):
        language = kwargs.get('language', 'c')
        super().__init__('mpi', environment, language, kwargs)
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
                version = None

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

            version = None

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
            return (None,
                    ['-I' + incdir, '-I' + os.path.join(incdir, post)],
                    [os.path.join(libdir, 'msmpi.lib'), os.path.join(libdir, 'msmpifec.lib')])
        else:
            return (None,
                    ['-I' + incdir, '-I' + os.path.join(incdir, post)],
                    [os.path.join(libdir, 'msmpi.lib')])


class OpenMPDependency(ExternalDependency):
    # Map date of specification release (which is the macro value) to a version.
    VERSIONS = {
        '201511': '4.5',
        '201307': '4.0',
        '201107': '3.1',
        '200805': '3.0',
        '200505': '2.5',
        '200203': '2.0',
        '199810': '1.0',
    }

    def __init__(self, environment, kwargs):
        language = kwargs.get('language')
        super().__init__('openmp', environment, language, kwargs)
        self.is_found = False
        try:
            openmp_date = self.clib_compiler.get_define('_OPENMP', '', self.env, [], [self])
        except mesonlib.EnvironmentException as e:
            mlog.debug('OpenMP support not available in the compiler')
            mlog.debug(e)
            openmp_date = False

        if openmp_date:
            self.version = self.VERSIONS[openmp_date]
            if self.clib_compiler.has_header('omp.h', '', self.env, dependencies=[self]):
                self.is_found = True
            else:
                mlog.log(mlog.yellow('WARNING:'), 'OpenMP found but omp.h missing.')

    def need_openmp(self):
        return True


class ThreadDependency(ExternalDependency):
    def __init__(self, environment, kwargs):
        super().__init__('threads', environment, None, kwargs)
        self.name = 'threads'
        self.is_found = True

    def need_threads(self):
        return True


class Python3Dependency(ExternalDependency):
    def __init__(self, environment, kwargs):
        super().__init__('python3', environment, None, kwargs)
        self.name = 'python3'
        self.static = kwargs.get('static', False)
        # We can only be sure that it is Python 3 at this point
        self.version = '3'
        self.pkgdep = None
        self._find_libpy3_windows(environment)

    @classmethod
    def _factory(cls, environment, kwargs):
        methods = cls._process_method_kw(kwargs)
        candidates = []

        if DependencyMethods.PKGCONFIG in methods:
            candidates.append(functools.partial(PkgConfigDependency, 'python3', environment, kwargs))

        if DependencyMethods.SYSCONFIG in methods:
            candidates.append(functools.partial(Python3Dependency, environment, kwargs))

        if DependencyMethods.EXTRAFRAMEWORK in methods:
            # In OSX the Python 3 framework does not have a version
            # number in its name.
            # There is a python in /System/Library/Frameworks, but that's
            # python 2, Python 3 will always be in /Library
            candidates.append(functools.partial(
                ExtraFrameworkDependency, 'python', False, '/Library/Frameworks',
                environment, kwargs.get('language', None), kwargs))

        return candidates

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

    @staticmethod
    def get_methods():
        if mesonlib.is_windows():
            return [DependencyMethods.PKGCONFIG, DependencyMethods.SYSCONFIG]
        elif mesonlib.is_osx():
            return [DependencyMethods.PKGCONFIG, DependencyMethods.EXTRAFRAMEWORK]
        else:
            return [DependencyMethods.PKGCONFIG]

    def log_tried(self):
        return 'sysconfig'

class PcapDependency(ExternalDependency):

    def __init__(self, environment, kwargs):
        super().__init__('pcap', environment, None, kwargs)

    @classmethod
    def _factory(cls, environment, kwargs):
        methods = cls._process_method_kw(kwargs)
        candidates = []

        if DependencyMethods.PKGCONFIG in methods:
            candidates.append(functools.partial(PkgConfigDependency, 'pcap', environment, kwargs))

        if DependencyMethods.CONFIG_TOOL in methods:
            candidates.append(functools.partial(ConfigToolDependency.factory,
                                                'pcap', environment, None,
                                                kwargs, ['pcap-config'],
                                                'pcap-config',
                                                PcapDependency.tool_finish_init))

        return candidates

    @staticmethod
    def tool_finish_init(ctdep):
        ctdep.compile_args = ctdep.get_config_value(['--cflags'], 'compile_args')
        ctdep.link_args = ctdep.get_config_value(['--libs'], 'link_args')
        ctdep.version = PcapDependency.get_pcap_lib_version(ctdep)

    @staticmethod
    def get_methods():
        return [DependencyMethods.PKGCONFIG, DependencyMethods.CONFIG_TOOL]

    @staticmethod
    def get_pcap_lib_version(ctdep):
        v = ctdep.clib_compiler.get_return_value('pcap_lib_version', 'string',
                                                 '#include <pcap.h>', ctdep.env, [], [ctdep])
        v = re.sub(r'libpcap version ', '', v)
        v = re.sub(r' -- Apple version.*$', '', v)
        return v


class CupsDependency(ExternalDependency):
    def __init__(self, environment, kwargs):
        super().__init__('cups', environment, None, kwargs)

    @classmethod
    def _factory(cls, environment, kwargs):
        methods = cls._process_method_kw(kwargs)
        candidates = []

        if DependencyMethods.PKGCONFIG in methods:
            candidates.append(functools.partial(PkgConfigDependency, 'cups', environment, kwargs))

        if DependencyMethods.CONFIG_TOOL in methods:
            candidates.append(functools.partial(ConfigToolDependency.factory,
                                                'cups', environment, None,
                                                kwargs, ['cups-config'],
                                                'cups-config', CupsDependency.tool_finish_init))

        if DependencyMethods.EXTRAFRAMEWORK in methods:
            if mesonlib.is_osx():
                candidates.append(functools.partial(
                    ExtraFrameworkDependency, 'cups', False, None, environment,
                    kwargs.get('language', None), kwargs))

        return candidates

    @staticmethod
    def tool_finish_init(ctdep):
        ctdep.compile_args = ctdep.get_config_value(['--cflags'], 'compile_args')
        ctdep.link_args = ctdep.get_config_value(['--ldflags', '--libs'], 'link_args')

    @staticmethod
    def get_methods():
        if mesonlib.is_osx():
            return [DependencyMethods.PKGCONFIG, DependencyMethods.CONFIG_TOOL, DependencyMethods.EXTRAFRAMEWORK]
        else:
            return [DependencyMethods.PKGCONFIG, DependencyMethods.CONFIG_TOOL]


class LibWmfDependency(ExternalDependency):
    def __init__(self, environment, kwargs):
        super().__init__('libwmf', environment, None, kwargs)

    @classmethod
    def _factory(cls, environment, kwargs):
        methods = cls._process_method_kw(kwargs)
        candidates = []

        if DependencyMethods.PKGCONFIG in methods:
            candidates.append(functools.partial(PkgConfigDependency, 'libwmf', environment, kwargs))

        if DependencyMethods.CONFIG_TOOL in methods:
            candidates.append(functools.partial(ConfigToolDependency.factory,
                                                'libwmf', environment, None, kwargs, ['libwmf-config'], 'libwmf-config', LibWmfDependency.tool_finish_init))

        return candidates

    @staticmethod
    def tool_finish_init(ctdep):
        ctdep.compile_args = ctdep.get_config_value(['--cflags'], 'compile_args')
        ctdep.link_args = ctdep.get_config_value(['--libs'], 'link_args')

    @staticmethod
    def get_methods():
        return [DependencyMethods.PKGCONFIG, DependencyMethods.CONFIG_TOOL]
