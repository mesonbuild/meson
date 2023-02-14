# Copyright 2022 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import annotations

import json, sysconfig
from pathlib import Path
import typing as T

from .. import mesonlib, mlog
from .base import DependencyMethods, SystemDependency
from .factory import DependencyFactory
from ..environment import detect_cpu_family
from ..programs import ExternalProgram

if T.TYPE_CHECKING:
    from typing_extensions import TypedDict

    from ..environment import Environment

    class PythonIntrospectionDict(TypedDict):

        install_paths: T.Dict[str, str]
        is_pypy: bool
        is_venv: bool
        link_libpython: bool
        sysconfig_paths: T.Dict[str, str]
        paths: T.Dict[str, str]
        platform: str
        suffix: str
        variables: T.Dict[str, str]
        version: str


class BasicPythonExternalProgram(ExternalProgram):
    def __init__(self, name: str, command: T.Optional[T.List[str]] = None,
                 ext_prog: T.Optional[ExternalProgram] = None):
        if ext_prog is None:
            super().__init__(name, command=command, silent=True)
        else:
            self.name = name
            self.command = ext_prog.command
            self.path = ext_prog.path

        # We want strong key values, so we always populate this with bogus data.
        # Otherwise to make the type checkers happy we'd have to do .get() for
        # everycall, even though we know that the introspection data will be
        # complete
        self.info: 'PythonIntrospectionDict' = {
            'install_paths': {},
            'is_pypy': False,
            'is_venv': False,
            'link_libpython': False,
            'sysconfig_paths': {},
            'paths': {},
            'platform': 'sentinal',
            'suffix': 'sentinel',
            'variables': {},
            'version': '0.0',
        }
        self.pure: bool = True

    def _check_version(self, version: str) -> bool:
        if self.name == 'python2':
            return mesonlib.version_compare(version, '< 3.0')
        elif self.name == 'python3':
            return mesonlib.version_compare(version, '>= 3.0')
        return True

    def sanity(self) -> bool:
        # Sanity check, we expect to have something that at least quacks in tune

        import importlib.resources

        with importlib.resources.path('mesonbuild.scripts', 'python_info.py') as f:
            cmd = self.get_command() + [str(f)]
            p, stdout, stderr = mesonlib.Popen_safe(cmd)

        try:
            info = json.loads(stdout)
        except json.JSONDecodeError:
            info = None
            mlog.debug('Could not introspect Python (%s): exit code %d' % (str(p.args), p.returncode))
            mlog.debug('Program stdout:\n')
            mlog.debug(stdout)
            mlog.debug('Program stderr:\n')
            mlog.debug(stderr)

        if info is not None and self._check_version(info['version']):
            self.info = T.cast('PythonIntrospectionDict', info)
            return True
        else:
            return False


class Python3DependencySystem(SystemDependency):
    def __init__(self, name: str, environment: 'Environment', kwargs: T.Dict[str, T.Any]) -> None:
        super().__init__(name, environment, kwargs)

        if not environment.machines.matches_build_machine(self.for_machine):
            return
        if not environment.machines[self.for_machine].is_windows():
            return

        self.name = 'python3'
        # We can only be sure that it is Python 3 at this point
        self.version = '3'
        self._find_libpy3_windows(environment)

    @staticmethod
    def get_windows_python_arch() -> T.Optional[str]:
        pyplat = sysconfig.get_platform()
        if pyplat == 'mingw':
            pycc = sysconfig.get_config_var('CC')
            if pycc.startswith('x86_64'):
                return '64'
            elif pycc.startswith(('i686', 'i386')):
                return '32'
            else:
                mlog.log(f'MinGW Python built with unknown CC {pycc!r}, please file a bug')
                return None
        elif pyplat == 'win32':
            return '32'
        elif pyplat in {'win64', 'win-amd64'}:
            return '64'
        mlog.log(f'Unknown Windows Python platform {pyplat!r}')
        return None

    def get_windows_link_args(self) -> T.Optional[T.List[str]]:
        pyplat = sysconfig.get_platform()
        if pyplat.startswith('win'):
            vernum = sysconfig.get_config_var('py_version_nodot')
            if self.static:
                libpath = Path('libs') / f'libpython{vernum}.a'
            else:
                comp = self.get_compiler()
                if comp.id == "gcc":
                    libpath = Path(f'python{vernum}.dll')
                else:
                    libpath = Path('libs') / f'python{vernum}.lib'
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

    def _find_libpy3_windows(self, env: 'Environment') -> None:
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
            mlog.log(f'Unknown architecture {arch!r} for',
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
    def log_tried() -> str:
        return 'sysconfig'


python3_factory = DependencyFactory(
    'python3',
    [DependencyMethods.PKGCONFIG, DependencyMethods.SYSTEM, DependencyMethods.EXTRAFRAMEWORK],
    system_class=Python3DependencySystem,
    # There is no version number in the macOS version number
    framework_name='Python',
    # There is a python in /System/Library/Frameworks, but that's python 2.x,
    # Python 3 will always be in /Library
    extra_kwargs={'paths': ['/Library/Frameworks']},
)
