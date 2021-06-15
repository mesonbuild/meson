# Copyright 2013-2021 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .base import ExternalDependency, DependencyException, DependencyMethods, DependencyTypeName
from .pkgconfig import PkgConfigDependency
from ..mesonlib import Popen_safe
from ..programs import ExternalProgram
from ..compilers import DCompiler
from .. import mlog
import re
import os
import copy
import json
import platform
import typing as T

if T.TYPE_CHECKING:
    from ..environment import Environment

class DubDependency(ExternalDependency):
    class_dubbin = None

    def __init__(self, name: str, environment: 'Environment', kwargs: T.Dict[str, T.Any]):
        super().__init__(DependencyTypeName('dub'), environment, kwargs, language='d')
        self.name = name
        self.module_path: T.Optional[str] = None

        _temp_comp = super().get_compiler()
        assert isinstance(_temp_comp, DCompiler)
        self.compiler = _temp_comp

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

        assert isinstance(self.dubbin, ExternalProgram)
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

        def add_lib_args(field_name: str, target: T.Dict[str, T.Dict[str, str]]) -> None:
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
                add_lib_args(f'libs-{platform.machine()}', target)
                for file in target['buildSettings']['linkerFiles']:
                    lib_path = self._find_right_lib_path(file, comp, description)
                    if lib_path:
                        self.link_args.append(lib_path)
                    else:
                        self.is_found = False

    def _find_right_lib_path(self,
                             default_path: str,
                             comp: str,
                             description: T.Dict[str, str],
                             folder_only: bool = False,
                             file_name: str = '') -> T.Optional[str]:
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
            return None

        d_ver_reg = re.search('v[0-9].[0-9][0-9][0-9].[0-9]', res) # Ex.: v2.081.2
        if d_ver_reg is not None:
            d_ver = d_ver_reg.group().rsplit('.', 1)[0].replace('v', '').replace('.', '') # Fix structure. Ex.: 2081
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

    def _call_dubbin(self, args: T.List[str], env: T.Optional[T.Dict[str, str]] = None) -> T.Tuple[int, str]:
        assert isinstance(self.dubbin, ExternalProgram)
        p, out = Popen_safe(self.dubbin.get_command() + args, env=env)[0:2]
        return p.returncode, out.strip()

    def _call_copmbin(self, args: T.List[str], env: T.Optional[T.Dict[str, str]] = None) -> T.Tuple[int, str]:
        p, out = Popen_safe(self.compiler.get_exelist() + args, env=env)[0:2]
        return p.returncode, out.strip()

    def _check_dub(self) -> T.Union[bool, ExternalProgram]:
        dubbin: T.Union[bool, ExternalProgram] = ExternalProgram('dub', silent=True)
        assert isinstance(dubbin, ExternalProgram)
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
        if isinstance(dubbin, ExternalProgram):
            mlog.log('Found DUB:', mlog.bold(dubbin.get_path()),
                     '(%s)' % out.strip())
        else:
            mlog.log('Found DUB:', mlog.red('NO'))
        return dubbin

    @staticmethod
    def get_methods() -> T.List[DependencyMethods]:
        return [DependencyMethods.DUB]
