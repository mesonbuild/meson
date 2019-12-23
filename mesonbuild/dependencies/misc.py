# Copyright 2013-2019 The Meson development team

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

from pathlib import Path
import functools
import re
import sysconfig

from .. import mlog
from .. import mesonlib
from ..environment import detect_cpu_family
from ..mesonlib import listify

from .base import (
    DependencyException, DependencyMethods, ExternalDependency,
    ExtraFrameworkDependency, PkgConfigDependency,
    CMakeDependency, ConfigToolDependency,
)


class NetCDFDependency(ExternalDependency):

    def __init__(self, environment, kwargs):
        language = kwargs.get('language', 'c')
        super().__init__('netcdf', environment, language, kwargs)
        kwargs['required'] = False
        kwargs['silent'] = True
        self.is_found = False
        methods = listify(self.methods)

        if language not in ('c', 'cpp', 'fortran'):
            raise DependencyException('Language {} is not supported with NetCDF.'.format(language))

        if set([DependencyMethods.AUTO, DependencyMethods.PKGCONFIG]).intersection(methods):
            pkgconfig_files = ['netcdf']

            if language == 'fortran':
                pkgconfig_files.append('netcdf-fortran')

            self.compile_args = []
            self.link_args = []
            self.pcdep = []
            for pkg in pkgconfig_files:
                pkgdep = PkgConfigDependency(pkg, environment, kwargs, language=self.language)
                if pkgdep.found():
                    self.compile_args.extend(pkgdep.get_compile_args())
                    self.link_args.extend(pkgdep.get_link_args())
                    self.version = pkgdep.get_version()
                    self.is_found = True
                    self.pcdep.append(pkgdep)
            if self.is_found:
                return

        if set([DependencyMethods.AUTO, DependencyMethods.CMAKE]).intersection(methods):
            cmakedep = CMakeDependency('NetCDF', environment, kwargs, language=self.language)
            if cmakedep.found():
                self.compile_args = cmakedep.get_compile_args()
                self.link_args = cmakedep.get_link_args()
                self.version = cmakedep.get_version()
                self.is_found = True
                return

    @staticmethod
    def get_methods():
        return [DependencyMethods.AUTO, DependencyMethods.PKGCONFIG, DependencyMethods.CMAKE]


class OpenMPDependency(ExternalDependency):
    # Map date of specification release (which is the macro value) to a version.
    VERSIONS = {
        '201811': '5.0',
        '201611': '5.0-revision1',  # This is supported by ICC 19.x
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
        if self.clib_compiler.get_id() == 'pgi':
            # through at least PGI 19.4, there is no macro defined for OpenMP, but OpenMP 3.1 is supported.
            self.version = '3.1'
            self.is_found = True
            self.compile_args = self.link_args = self.clib_compiler.openmp_flags()
            return
        try:
            openmp_date = self.clib_compiler.get_define(
                '_OPENMP', '', self.env, self.clib_compiler.openmp_flags(), [self], disable_cache=True)[0]
        except mesonlib.EnvironmentException as e:
            mlog.debug('OpenMP support not available in the compiler')
            mlog.debug(e)
            openmp_date = None

        if openmp_date:
            self.version = self.VERSIONS[openmp_date]
            # Flang has omp_lib.h
            header_names = ('omp.h', 'omp_lib.h')
            for name in header_names:
                if self.clib_compiler.has_header(name, '', self.env, dependencies=[self], disable_cache=True)[0]:
                    self.is_found = True
                    self.compile_args = self.link_args = self.clib_compiler.openmp_flags()
                    break
            if not self.is_found:
                mlog.log(mlog.yellow('WARNING:'), 'OpenMP found but omp.h missing.')


class ThreadDependency(ExternalDependency):
    def __init__(self, environment, kwargs):
        super().__init__('threads', environment, None, kwargs)
        self.name = 'threads'
        self.is_found = False
        methods = listify(self.methods)
        if DependencyMethods.AUTO in methods:
            self.is_found = True
            # Happens if you are using a language with threads
            # concept without C, such as plain Cuda.
            if self.clib_compiler is None:
                self.compile_args = []
                self.link_args = []
            else:
                self.compile_args = self.clib_compiler.thread_flags(environment)
                self.link_args = self.clib_compiler.thread_link_flags(environment)
            return

        if DependencyMethods.CMAKE in methods:
            # for unit tests and for those who simply want
            # dependency('threads', method: 'cmake')
            cmakedep = CMakeDependency('Threads', environment, kwargs)
            if cmakedep.found():
                self.compile_args = cmakedep.get_compile_args()
                self.link_args = cmakedep.get_link_args()
                self.version = cmakedep.get_version()
                self.is_found = True
                return

    @staticmethod
    def get_methods():
        return [DependencyMethods.AUTO, DependencyMethods.CMAKE]


class BlocksDependency(ExternalDependency):
    def __init__(self, environment, kwargs):
        super().__init__('blocks', environment, None, kwargs)
        self.name = 'blocks'
        self.is_found = False

        if self.env.machines[self.for_machine].is_darwin():
            self.compile_args = []
            self.link_args = []
        else:
            self.compile_args = ['-fblocks']
            self.link_args = ['-lBlocksRuntime']

            if not self.clib_compiler.has_header('Block.h', '', environment, disable_cache=True) or \
               not self.clib_compiler.find_library('BlocksRuntime', environment, []):
                mlog.log(mlog.red('ERROR:'), 'BlocksRuntime not found.')
                return

        source = '''
            int main(int argc, char **argv)
            {
                int (^callback)(void) = ^ int (void) { return 0; };
                return callback();
            }'''

        with self.clib_compiler.compile(source, extra_args=self.compile_args + self.link_args) as p:
            if p.returncode != 0:
                mlog.log(mlog.red('ERROR:'), 'Compiler does not support blocks extension.')
                return

            self.is_found = True


class Python3Dependency(ExternalDependency):
    def __init__(self, environment, kwargs):
        super().__init__('python3', environment, None, kwargs)

        if not environment.machines.matches_build_machine(self.for_machine):
            return

        self.name = 'python3'
        self.static = kwargs.get('static', False)
        # We can only be sure that it is Python 3 at this point
        self.version = '3'
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
                ExtraFrameworkDependency, 'Python', False, ['/Library/Frameworks'],
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
                libpath = Path('libs') / 'libpython{}.a'.format(vernum)
            else:
                comp = self.get_compiler()
                if comp.id == "gcc":
                    libpath = 'python{}.dll'.format(vernum)
                else:
                    libpath = Path('libs') / 'python{}.lib'.format(vernum)
            lib = Path(sysconfig.get_config_var('base')) / libpath
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
        arch = detect_cpu_family(env.coredata.compilers.host)
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
        # Since we seem to need to run a program to discover the pcap version,
        # we can't do that when cross-compiling
        if not ctdep.env.machines.matches_build_machine(ctdep.for_machine):
            return None

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

        if DependencyMethods.CMAKE in methods:
            candidates.append(functools.partial(CMakeDependency, 'Cups', environment, kwargs))

        return candidates

    @staticmethod
    def tool_finish_init(ctdep):
        ctdep.compile_args = ctdep.get_config_value(['--cflags'], 'compile_args')
        ctdep.link_args = ctdep.get_config_value(['--ldflags', '--libs'], 'link_args')

    @staticmethod
    def get_methods():
        if mesonlib.is_osx():
            return [DependencyMethods.PKGCONFIG, DependencyMethods.CONFIG_TOOL, DependencyMethods.EXTRAFRAMEWORK, DependencyMethods.CMAKE]
        else:
            return [DependencyMethods.PKGCONFIG, DependencyMethods.CONFIG_TOOL, DependencyMethods.CMAKE]


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


class LibGCryptDependency(ExternalDependency):
    def __init__(self, environment, kwargs):
        super().__init__('libgcrypt', environment, None, kwargs)

    @classmethod
    def _factory(cls, environment, kwargs):
        methods = cls._process_method_kw(kwargs)
        candidates = []

        if DependencyMethods.PKGCONFIG in methods:
            candidates.append(functools.partial(PkgConfigDependency, 'libgcrypt', environment, kwargs))

        if DependencyMethods.CONFIG_TOOL in methods:
            candidates.append(functools.partial(ConfigToolDependency.factory,
                                                'libgcrypt', environment, None, kwargs, ['libgcrypt-config'],
                                                'libgcrypt-config',
                                                LibGCryptDependency.tool_finish_init))

        return candidates

    @staticmethod
    def tool_finish_init(ctdep):
        ctdep.compile_args = ctdep.get_config_value(['--cflags'], 'compile_args')
        ctdep.link_args = ctdep.get_config_value(['--libs'], 'link_args')
        ctdep.version = ctdep.get_config_value(['--version'], 'version')[0]

    @staticmethod
    def get_methods():
        return [DependencyMethods.PKGCONFIG, DependencyMethods.CONFIG_TOOL]


class GpgmeDependency(ExternalDependency):
    def __init__(self, environment, kwargs):
        super().__init__('gpgme', environment, None, kwargs)

    @classmethod
    def _factory(cls, environment, kwargs):
        methods = cls._process_method_kw(kwargs)
        candidates = []

        if DependencyMethods.PKGCONFIG in methods:
            candidates.append(functools.partial(PkgConfigDependency, 'gpgme', environment, kwargs))

        if DependencyMethods.CONFIG_TOOL in methods:
            candidates.append(functools.partial(ConfigToolDependency.factory,
                                                'gpgme', environment, None, kwargs, ['gpgme-config'],
                                                'gpgme-config',
                                                GpgmeDependency.tool_finish_init))

        return candidates

    @staticmethod
    def tool_finish_init(ctdep):
        ctdep.compile_args = ctdep.get_config_value(['--cflags'], 'compile_args')
        ctdep.link_args = ctdep.get_config_value(['--libs'], 'link_args')
        ctdep.version = ctdep.get_config_value(['--version'], 'version')[0]

    @staticmethod
    def get_methods():
        return [DependencyMethods.PKGCONFIG, DependencyMethods.CONFIG_TOOL]


class ShadercDependency(ExternalDependency):

    def __init__(self, environment, kwargs):
        super().__init__('shaderc', environment, None, kwargs)

        static_lib = 'shaderc_combined'
        shared_lib = 'shaderc_shared'

        libs = [shared_lib, static_lib]
        if self.static:
            libs.reverse()

        cc = self.get_compiler()

        for lib in libs:
            self.link_args = cc.find_library(lib, environment, [])
            if self.link_args is not None:
                self.is_found = True

                if self.static and lib != static_lib:
                    mlog.warning('Static library {!r} not found for dependency {!r}, may '
                                 'not be statically linked'.format(static_lib, self.name))

                break

    def log_tried(self):
        return 'system'

    @classmethod
    def _factory(cls, environment, kwargs):
        methods = cls._process_method_kw(kwargs)
        candidates = []

        if DependencyMethods.PKGCONFIG in methods:
            # ShaderC packages their shared and static libs together
            # and provides different pkg-config files for each one. We
            # smooth over this difference by handling the static
            # keyword before handing off to the pkg-config handler.
            shared_libs = ['shaderc']
            static_libs = ['shaderc_combined', 'shaderc_static']

            if kwargs.get('static', False):
                c = [functools.partial(PkgConfigDependency, name, environment, kwargs)
                     for name in static_libs + shared_libs]
            else:
                c = [functools.partial(PkgConfigDependency, name, environment, kwargs)
                     for name in shared_libs + static_libs]
            candidates.extend(c)

        if DependencyMethods.SYSTEM in methods:
            candidates.append(functools.partial(ShadercDependency, environment, kwargs))

        return candidates

    @staticmethod
    def get_methods():
        return [DependencyMethods.SYSTEM, DependencyMethods.PKGCONFIG]
