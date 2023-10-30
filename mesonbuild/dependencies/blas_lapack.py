# Copyright 2013-2020 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import functools
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import typing as T

from .. import mlog
from .. import mesonlib
from ..mesonlib import MachineChoice, OptionKey

from .base import DependencyMethods, SystemDependency
from .cmake import CMakeDependency
from .detect import packages
from .factory import DependencyFactory, factory_methods
from .pkgconfig import PkgConfigDependency

if T.TYPE_CHECKING:
    from ..environment import Environment


# See https://gist.github.com/rgommers/e10c7cf3ebd88883458544e535d7e54c for details on
# the different libraries, symbol mangling conventions, links to other
# detection implementations and distro recipes, etc.


class BLASLAPACKMixin():
    def parse_modules(self, kwargs: T.Dict[str, T.Any]) -> None:
        modules: T.List[str] = mesonlib.extract_as_list(kwargs, 'modules')
        valid_modules = ['interface: lp64', 'interface: ilp64', 'cblas', 'lapack', 'lapacke']
        for module in modules:
            if module not in valid_modules:
                raise mesonlib.MesonException(f'Unknown modules argument: {module}')

        interface = [s for s in modules if s.startswith('interface')]
        if interface:
            if len(interface) > 1:
                raise mesonlib.MesonException(f'Only one interface must be specified, found: {interface}')
            self.interface = interface[0].split(' ')[1]
        else:
            self.interface = 'lp64'

        self.needs_cblas = 'cblas' in modules
        self.needs_lapack = 'lapack' in modules
        self.needs_lapacke = 'lapacke' in modules

    def check_symbols(self, compile_args, suffix=None) -> None:
        # verify that we've found the right LP64/ILP64 interface
        symbols = ['dgemm_']
        if self.needs_cblas:
            symbols += ['cblas_dgemm']
        if self.needs_lapack:
            symbols += ['zungqr_']
        if self.needs_lapacke:
            symbols += ['LAPACKE_zungqr']

        if suffix is None:
            suffix = self.get_symbol_suffix()

        prototypes = "".join(f"void {symbol}{suffix}();\n" for symbol in symbols)
        calls = "  ".join(f"{symbol}{suffix}();\n" for symbol in symbols)
        code = (f"{prototypes}"
                 "int main(int argc, const char *argv[])\n"
                 "{\n"
                f"  {calls}"
                 "  return 0;\n"
                 "}"
                )
        code = '''#ifdef __cplusplus
               extern "C" {
               #endif
               ''' + code + '''
               #ifdef __cplusplus
               }
               #endif
               '''

        return self.clib_compiler.links(code, self.env, extra_args=compile_args)[0]

    def get_variable(self, **kwargs: T.Dict[str, T.Any]) -> str:
        # TODO: what's going on with `get_variable`? Need to pick from
        # cmake/pkgconfig/internal/..., but not system?
        varname = kwargs['pkgconfig']
        if varname == 'interface':
            return self.interface
        elif varname == 'symbol_suffix':
            return self.get_symbol_suffix()
        return super().get_variable(**kwargs)


class OpenBLASMixin():
    def get_symbol_suffix(self) -> str:
        return '' if self.interface == 'lp64' else self._ilp64_suffix

    def probe_symbols(self, compile_args) -> bool:
        """There are two common ways of building ILP64 BLAS, check which one we're dealing with"""
        if self.interface == 'lp64':
            return self.check_symbols(compile_args)

        if self.check_symbols(compile_args, '64_'):
            self._ilp64_suffix = '64_'
        elif self.check_symbols(compile_args, ''):
            self._ilp64_suffix = ''
        else:
            return False
        return True


class OpenBLASSystemDependency(BLASLAPACKMixin, OpenBLASMixin, SystemDependency):
    def __init__(self, name: str, environment: 'Environment', kwargs: T.Dict[str, T.Any]) -> None:
        super().__init__(name, environment, kwargs)
        self.feature_since = ('1.3.0', '')
        self.parse_modules(kwargs)

        # First, look for paths specified in a machine file
        props = self.env.properties[self.for_machine].properties
        if any(x in props for x in ['openblas_includedir', 'openblas_librarydir']):
            self.detect_openblas_machine_file(props)

        # Then look in standard directories by attempting to link
        if not self.is_found:
            extra_libdirs: T.List[str] = []
            self.detect(extra_libdirs)

        if self.is_found:
            self.version = self.detect_openblas_version()

    def detect(self, lib_dirs: T.Optional[T.List[str]] = None, inc_dirs: T.Optional[T.List[str]] = None) -> None:
        if lib_dirs is None:
            lib_dirs = []
        if inc_dirs is None:
            inc_dirs = []

        if self.interface == 'lp64':
            libnames = ['openblas']
        elif self.interface == 'ilp64':
            libnames = ['openblas64', 'openblas_ilp64', 'openblas']

        for libname in libnames:
            link_arg = self.clib_compiler.find_library(libname, self.env, lib_dirs)
            incdir_args = [f'-I{inc_dir}' for inc_dir in inc_dirs]
            for hdr in ['openblas_config.h', 'openblas/openblas_config.h']:
                found_header, _ = self.clib_compiler.has_header(hdr, '', self.env, dependencies=[self],
                                                                extra_args=incdir_args)
                if found_header:
                    self._openblas_config_header = hdr
                    break

            if link_arg and found_header:
                if not self.probe_symbols(link_arg):
                    continue
                self.is_found = True
                self.link_args += link_arg
                self.compile_args += incdir_args
                break

    def detect_openblas_machine_file(self, props: dict) -> None:
        # TBD: do we need to support multiple extra dirs?
        incdir = props.get('openblas_includedir')
        assert incdir is None or isinstance(incdir, str)
        libdir = props.get('openblas_librarydir')
        assert libdir is None or isinstance(libdir, str)

        if incdir and libdir:
            self.is_found = True
            if not Path(incdir).is_absolute() or not Path(libdir).is_absolute():
                raise mesonlib.MesonException('Paths given for openblas_includedir and '
                                              'openblas_librarydir in machine file must be absolute')
        elif incdir or libdir:
            raise mesonlib.MesonException('Both openblas_includedir *and* openblas_librarydir '
                                          'have to be set in your machine file (one is not enough)')
        else:
            raise mesonlib.MesonBugException('issue with openblas dependency detection, should not '
                                             'be possible to reach this else clause')

        self.detect([libdir], [incdir])

    def detect_openblas_version(self) -> str:
        v, _ = self.clib_compiler.get_define('OPENBLAS_VERSION',
                                             f'#include <{self._openblas_config_header}>',
                                             self.env, [], [self])

        m = re.search(r'\d+(?:\.\d+)+', v)
        if not m:
            mlog.debug('Failed to extract openblas version information')
            return None
        return m.group(0)


class OpenBLASPkgConfigDependency(BLASLAPACKMixin, OpenBLASMixin, PkgConfigDependency):
    def __init__(self, name: str, env: 'Environment', kwargs: T.Dict[str, T.Any]) -> None:
        self.feature_since = ('1.3.0', '')
        self.parse_modules(kwargs)
        if self.interface == 'lp64' and name != 'openblas':
            # Check only for 'openblas' for LP64 (there are multiple names for ILP64)
            self.is_found = False
            return None

        super().__init__(name, env, kwargs)

        if not self.probe_symbols(self.link_args):
            self.is_found = False


class OpenBLASCMakeDependency(BLASLAPACKMixin, OpenBLASMixin, CMakeDependency):
    def __init__(self, name: str, env: 'Environment', kwargs: T.Dict[str, T.Any],
                 language: T.Optional[str] = None, force_use_global_compilers: bool = False) -> None:
        super().__init__('OpenBLAS', env, kwargs, language, force_use_global_compilers)
        self.feature_since = ('1.3.0', '')
        self.parse_modules(kwargs)

        if self.interface == 'ilp64':
            self.is_found = False
        elif not self.probe_symbols(self.link_args):
            self.is_found = False


class NetlibPkgConfigDependency(BLASLAPACKMixin, PkgConfigDependency):
    def __init__(self, name: str, env: 'Environment', kwargs: T.Dict[str, T.Any]) -> None:
        # TODO: add 'cblas'
        super().__init__('blas', env, kwargs)
        self.feature_since = ('1.3.0', '')
        self.parse_modules(kwargs)

    def get_symbol_suffix(self) -> str:
        return ''


class AccelerateSystemDependency(BLASLAPACKMixin, SystemDependency):
    """
    Accelerate is always installed on macOS, and not available on other OSes.
    We only support using Accelerate on macOS >=13.3, where Apple shipped a
    major update to Accelerate, fixed a lot of bugs, and bumped the LAPACK
    version from 3.2 to 3.9. The older Accelerate version is still available,
    and can be obtained as a standard Framework dependency with one of:

        dependency('Accelerate')
        dependency('appleframeworks', modules : 'Accelerate')

    """
    def __init__(self, name: str, environment: 'Environment', kwargs: T.Dict[str, T.Any]) -> None:
        super().__init__(name, environment, kwargs)
        self.feature_since = ('1.3.0', '')
        self.parse_modules(kwargs)

        for_machine = MachineChoice.BUILD if kwargs.get('native', False) else MachineChoice.HOST
        if environment.machines[for_machine].is_darwin() and self.check_macOS_recent_enough():
            self.detect(kwargs)

    def check_macOS_recent_enough(self) -> bool:
        # We need the SDK to be >=13.3 (meaning at least XCode 14.3)
        cmd = ['xcrun', '-sdk', 'macosx', '--show-sdk-version']
        sdk_version = subprocess.run(cmd, capture_output=True, check=True, text=True).stdout.strip()
        macos_version = platform.mac_ver()[0]
        deploy_target = os.environ.get('MACOSX_DEPLOYMENT_TARGET', macos_version)
        return sdk_version >= '13.3' and deploy_target >= '13.3'

    def detect(self, kwargs: T.Dict[str, T.Any]) -> None:
        from .framework import ExtraFrameworkDependency
        dep = ExtraFrameworkDependency('Accelerate', self.env, kwargs)
        self.is_found = dep.is_found
        if self.is_found:
            self.compile_args = dep.compile_args
            self.link_args = dep.link_args
            self.compile_args += ['-DACCELERATE_NEW_LAPACK']
            if self.interface == 'ilp64':
                self.compile_args += ['-DACCELERATE_LAPACK_ILP64']

        # We won't check symbols here, because Accelerate is built in a consistent fashion
        # with known symbol mangling, unlike OpenBLAS or Netlib BLAS/LAPACK.
        return None

    def get_symbol_suffix(self) -> str:
        return '$NEWLAPACK' if self.interface == 'lp64' else '$NEWLAPACK$ILP64'


class MKLMixin():
    def get_symbol_suffix(self) -> str:
        return '' if self.interface == 'lp64' else '_64'

    def parse_mkl_options(self, kwargs: T.Dict[str, T.Any]) -> None:
        """Parse `modules` and remove threading and SDL options from it if they are present.

        Removing 'threading: <val>' and 'sdl' from `modules` is needed to ensure those
        don't get to the generic parse_modules() method for all BLAS/LAPACK dependencies.
        """
        modules: T.List[str] = mesonlib.extract_as_list(kwargs, 'modules')
        threading_module = [s for s in modules if s.startswith('threading')]
        sdl_module = [s for s in modules if s.startswith('sdl')]

        if not threading_module:
            self.threading = 'iomp'
        elif len(threading_module) > 1:
            raise mesonlib.MesonException(f'Multiple threading arguments: {threading_modules}')
        else:
            # We have a single threading option specified - validate and process it
            opt = threading_module[0]
            if opt not in ['threading: ' + s for s in ('seq', 'iomp', 'gomp', 'tbb')]:
                raise mesonlib.MesonException(f'Invalid threading argument: {opt}')

            self.threading = opt.split(' ')[1]
            modules = [s for s in modules if not s == opt]
            kwargs['modules'] = modules

        if not sdl_module:
            self.use_sdl = 'auto'
        elif len(sdl_module) > 1:
            raise mesonlib.MesonException(f'Multiple sdl arguments: {threading_modules}')
        else:
            # We have a single sdl option specified - validate and process it
            opt = sdl_module[0]
            if opt not in ['sdl: ' + s for s in ('true', 'false', 'auto')]:
                raise mesonlib.MesonException(f'Invalid sdl argument: {opt}')

            self.use_sdl = {
                'false': False,
                'true': True,
                'auto': 'auto'
            }.get(opt.split(' ')[1])
            modules = [s for s in modules if not s == opt]
            kwargs['modules'] = modules

        # Parse common BLAS/LAPACK options
        self.parse_modules(kwargs)

        # Check if we don't have conflicting options between SDL's defaults and interface/threading
        self.sdl_default_opts = self.interface == 'lp64' and self.threading == 'iomp'
        if self.use_sdl == 'auto' and not self.sdl_default_opts:
            self.use_sdl = False
        elif self.use_sdl and not self.sdl_default_opts:
            # If we're here, we got an explicit `sdl: 'true'`
            raise mesonlib.MesonException(f'Linking SDL implies using LP64 and Intel OpenMP, found '
                                          f'conflicting options: {self.interface}, {self.threading}')

        return None


class MKLPkgConfigDependency(BLASLAPACKMixin, MKLMixin, PkgConfigDependency):
    """
    pkg-config files for MKL were fixed recently, and should work from 2023.0
    onwards. Directly using a specific one like so should work:

        dependency('mkl-dynamic-ilp64-seq')

    The naming scheme is `mkl-libtype-interface-threading.pc`, with values:
        - libtype: dynamic/static
        - interface: lp64/ilp64
        - threading: seq/iomp/gomp/tbb

    Furthermore there is a pkg-config file for the Single Dynamic Library
    (libmkl_rt.so) named `mkl-sdl.pc` (only added in 2023.0).

    Note that there is also an MKLPkgConfig dependency in scalapack.py, which
    has more manual fixes.
    """
    def __init__(self, name: str, env: 'Environment', kwargs: T.Dict[str, T.Any]) -> None:
        self.feature_since = ('1.3.0', '')
        self.parse_mkl_options(kwargs)
        if self.use_sdl == 'auto':
            # Layered libraries are preferred, and .pc files for layered were
            # available before the .pc file for SDL
            self.use_sdl = False

        static_opt = kwargs.get('static', env.coredata.get_option(OptionKey('prefer_static')))
        libtype = 'static' if static_opt else 'dynamic'

        if self.use_sdl:
            name = 'mkl-sdl'
        else:
            name = f'mkl-{libtype}-{self.interface}-{self.threading}'
        super().__init__(name, env, kwargs)


class MKLSystemDependency(BLASLAPACKMixin, MKLMixin, SystemDependency):
    """This only detects MKL's Single Dynamic Library (SDL)"""
    def __init__(self, name: str, environment: 'Environment', kwargs: T.Dict[str, T.Any]) -> None:
        super().__init__(name, environment, kwargs)
        self.feature_since = ('1.3.0', '')
        self.parse_mkl_options(kwargs)
        if self.use_sdl == 'auto':
            # Too complex to use layered here - only supported with pkg-config
            self.use_sdl = True

        if self.use_sdl:
            self.detect_sdl()
        return None

    def detect_sdl(self) -> None:
        # Use MKLROOT in addition to standard libdir(s)
        _m = os.environ.get('MKLROOT')
        mklroot = Path(_m).resolve() if _m else None
        lib_dirs = []
        inc_dirs = []
        if mklroot is not None:
            libdir = mklroot / 'lib' / 'intel64'
            if not libdir.exists():
                # MKLROOT may be pointing at the prefix where MKL was installed from PyPI
                # or Conda (Intel supports those install methods, but dropped the `intel64`
                # part, libraries go straight into <prefix>/lib
                libdir = mklroot / 'lib'
            incdir = mklroot / 'include'
            lib_dirs += [libdir]
            inc_dirs += [incdir]
            if not libdir.exists() or not incdir.exists():
                mlog.warning(f'MKLROOT env var set to {mklroot}, but not pointing to an MKL install')

        link_arg = self.clib_compiler.find_library('mkl_rt', self.env, lib_dirs)
        incdir_args = [f'-I{inc_dir}' for inc_dir in inc_dirs]
        found_header, _ = self.clib_compiler.has_header('mkl_version.h', '', self.env,
                                                        dependencies=[self], extra_args=incdir_args)
        if link_arg and found_header:
            self.is_found = True
            self.compile_args += incdir_args
            self.link_args += link_arg
            if not sys.platform == 'win32':
                self.link_args += ['-lpthread', '-lm', '-ldl']

            # Determine MKL version
            ver, _ = self.clib_compiler.get_define('INTEL_MKL_VERSION',
                                                   '#include "mkl_version.h"',
                                                   self.env,
                                                   dependencies=[self],
                                                   extra_args=incdir_args)
            if len(ver) == 8:
                year = ver[:4]
                minor = str(int(ver[4:6]))
                update = str(int(ver[6:]))
                # Note: this is the order as of 2023.2.0, but it looks the wrong way around
                # (INTEL_MKL_VERSION is defined as 20230002 in that release), could be swapped in the future perhaps
                self.version = f'{year}.{update}.{minor}'
            else:
                mlog.warning(f'MKL version detection issue, found {ver}')


@factory_methods({DependencyMethods.PKGCONFIG, DependencyMethods.SYSTEM, DependencyMethods.CMAKE})
def openblas_factory(env: 'Environment', for_machine: 'MachineChoice',
                     kwargs: T.Dict[str, T.Any],
                     methods: T.List[DependencyMethods]) -> T.List['DependencyGenerator']:
    candidates: T.List['DependencyGenerator'] = []

    if DependencyMethods.PKGCONFIG in methods:
        for pkg in ['openblas64', 'openblas_ilp64', 'openblas']:
            candidates.append(functools.partial(
                OpenBLASPkgConfigDependency, pkg, env, kwargs))

    if DependencyMethods.SYSTEM in methods:
        candidates.append(functools.partial(
            OpenBLASSystemDependency, 'openblas', env, kwargs))

    if DependencyMethods.CMAKE in methods:
        candidates.append(functools.partial(
            OpenBLASCMakeDependency, 'OpenBLAS', env, kwargs))

    return candidates

packages['openblas'] = openblas_factory


packages['netlib-blas'] = netlib_factory = DependencyFactory(
    'netlib-blas',
    [DependencyMethods.PKGCONFIG],  #, DependencyMethods.SYSTEM],
    #system_class=NetlibSystemDependency,
    pkgconfig_class=NetlibPkgConfigDependency,
)


packages['accelerate'] = accelerate_factory = DependencyFactory(
    'accelerate',
    [DependencyMethods.SYSTEM],
    system_class=AccelerateSystemDependency,
)


packages['mkl'] = mkl_factory = DependencyFactory(
    'mkl',
    [DependencyMethods.PKGCONFIG, DependencyMethods.SYSTEM],
    pkgconfig_class=MKLPkgConfigDependency,
    system_class=MKLSystemDependency,
)
