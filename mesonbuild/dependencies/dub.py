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

from .base import ExternalDependency, DependencyException, DependencyTypeName
from .pkgconfig import PkgConfigDependency
from ..mesonlib import (Popen_safe, OptionKey)
from ..programs import ExternalProgram
from ..compilers import DCompiler
from ..compilers.d import d_feature_args
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

        # if an explicit version spec was stated, use this when querying Dub
        main_pack_spec = name
        if 'version' in kwargs:
            main_pack_spec = f'{name}@{kwargs["version"]}'

        # we need to know the target architecture
        arch = self.compiler.arch

        # we need to know the build type as well
        buildtype = 'debug'
        if OptionKey('buildtype') in environment.options:
            buildtype = environment.options[OptionKey('buildtype')]
        elif OptionKey('optimize') in environment.options:
            buildtype = 'release'

        def dub_fetch_package(pack_spec):
            mlog.debug('Running DUB with', describe_cmd)
            fetch_cmd = ['fetch', pack_spec]
            ret, _, fetch_err = self._call_dubbin(fetch_cmd)
            if ret != 0:
                mlog.debug('DUB fetch failed: ' + fetch_err)
            return ret == 0

        def dub_build_package(pack_id: str, conf: str):
            cmd = [
                'build', pack_id, '--config='+conf, '--arch='+arch, '--build='+buildtype,
                '--compiler='+self.compiler.get_exelist()[-1]
            ]
            mlog.log('Building DUB package', mlog.bold(pack_id))
            mlog.debug('Running DUB with' , cmd)
            ret, res, err = self._call_dubbin(cmd)
            if ret != 0:
                mlog.debug('DUB build failed: ', err)
            return ret == 0

        # Ask dub for the package
        describe_cmd = [
            'describe', main_pack_spec, '--arch=' + arch,
            '--build=' + buildtype, '--compiler=' + self.compiler.get_exelist()[-1]
        ]
        ret, res, err = self._call_dubbin(describe_cmd)

        # If not present, fetch and repeat
        if ret != 0 and 'locally' in err:
            mlog.log(mlog.bold(name), 'is not present locally. Attempting to fetch on Dub registry.')
            if dub_fetch_package(main_pack_spec):
                ret, res, err = self._call_dubbin(describe_cmd)

        if ret != 0:
            mlog.debug('DUB describe failed: ' + err)
            self.is_found = False
            return

        comp_id = self.compiler.get_id().replace('llvm', 'ldc').replace('gcc', 'gdc')
        description = json.loads(res)

        self.compile_args = []
        self.link_args = self.raw_link_args = []

        def build_if_needed(pkg):
            # try to find a static library in a DUB folder corresponding to
            # version, configuration, compiler, arch and build-type
            # if can't find, ask DUB to build it and repeat find operation
            pack_id = f'{pkg["name"]}@{pkg["version"]}'
            tgt_file = self._find_dub_build_target(description, pkg, comp_id)
            if tgt_file is None and dub_build_package(pack_id, pkg['configuration']):
                tgt_file = self._find_dub_build_target(description, pkg, comp_id)
            if tgt_file is None:
                mlog.error('Could not find a suitable target for', mlog.bold(pack_id))
                return False
            self.link_args.append(tgt_file)
            return True

        # Main algorithm:
        # 1. Ensure that the target is a compatible library type (not dynamic)
        # 2. Build the main target if needed and add to link_args
        # 3. Do the same for each dependency.
        #    link_args MUST be in the same order than the "linkDependencies" of the main target
        # 4. Add other build settings (imports, versions etc.)

        # 1
        self.is_found = False
        packages = {}
        for pkg in description['packages']:
            packages[pkg['name']] = pkg

            if not pkg['active']:
                continue

            if pkg['targetType'] == 'dynamicLibrary':
                mlog.error('DUB dynamic library dependencies are not supported')
                self.is_found = False
                return

            ## check that the dependency is indeed a library
            if pkg['name'] == name:
                self.is_found = True

                if pkg['targetType'] not in ['library', 'sourceLibrary', 'staticLibrary']:
                    mlog.error(mlog.bold(name), "found but it isn't a library")
                    self.is_found = False
                    return

                self.version = pkg['version']
                self.pkg = pkg

        targets = {}
        for tgt in description['targets']:
            targets[tgt['rootPackage']] = tgt

        if not name in targets:
            self.is_found = False
            if self.pkg['targetType'] == 'sourceLibrary':
                # target libraries have no associated targets,
                # but some build settings like import folders must be found from the package object.
                # Current algo only get these from "buildSettings" in the target object.
                # Let's save this for a future PR.
                # (See openssl DUB package for example of sourceLibrary)
                mlog.error('DUB targets of type', mlog.bold('sourceLibrary'), 'are not supported yet.')
            else:
                mlog.error('Could not find target description for', mlog.bold(main_pack_spec))

        if not self.is_found:
            mlog.error(f'Could not find {name} in DUB description')
            return

        # Current impl only supports static libraries
        self.static = True

        # 2
        build_if_needed(self.pkg)

        # 3
        for link_dep in targets[name]['linkDependencies']:
            pkg = packages[link_dep]
            build_if_needed(pkg)

        # 4
        bs = targets[name]['buildSettings']

        for flag in bs['dflags']:
            self.compile_args.append(flag)

        for path in bs['importPaths']:
            self.compile_args.append('-I=' + path)

        for path in bs['stringImportPaths']:
            if not 'import_dir' in d_feature_args[self.compiler.id]:
                break
            flag = d_feature_args[self.compiler.id]['import_dir']
            self.compile_args.append(f'{flag}={path}')

        for ver in bs['versions']:
            if not 'version' in d_feature_args[self.compiler.id]:
                break
            flag = d_feature_args[self.compiler.id]['version']
            self.compile_args.append(f'{flag}={ver}')

        if bs['mainSourceFile']:
            self.compile_args.append(bs['mainSourceFile'])

        # pass static libraries
        # linkerFiles are added during step 3
        # for file in bs['linkerFiles']:
        #     self.link_args.append(file)

        for file in bs['sourceFiles']:
            # sourceFiles may contain static libraries
            if file.endswith('.lib') or file.endswith('.a'):
                self.link_args.append(file)

        for flag in bs['lflags']:
            self.link_args.append(flag)

        for lib in bs['libs']:
            if os.name != 'nt':
                # trying to add system libraries by pkg-config
                pkgdep = PkgConfigDependency(lib, environment, {'required': 'true', 'silent': 'true'})
                if pkgdep.is_found:
                    for arg in pkgdep.get_compile_args():
                        self.compile_args.append(arg)
                    for arg in pkgdep.get_link_args():
                        self.link_args.append(arg)
                    for arg in pkgdep.get_link_args(raw=True):
                        self.raw_link_args.append(arg)
                    continue
            # fallback
            self.link_args.append('-l'+lib)

    # This function finds the target of the provided JSON package, built for the right
    # compiler, architecture, configuration...
    # A value is returned only if the file exists
    def _find_dub_build_target(self, jdesc: T.Dict[str, str], jpack: T.Dict[str, str], comp_id: str):
        dub_build_path = os.path.join(jpack['path'], '.dub', 'build')

        if not os.path.exists(dub_build_path):
            return None

        # try to find a dir like library-debug-linux.posix-x86_64-ldc_2081-EF934983A3319F8F8FF2F0E107A363BA

        # fields are:
        #  - configuration
        #  - build type
        #  - platform
        #  - architecture
        #  - compiler id (dmd, ldc, gdc)
        #  - compiler version or frontend id or frontend version?

        conf = jpack['configuration']
        build_type = jdesc['buildType']
        platform = '.'.join(jdesc['platform'])
        arch = '.'.join(jdesc['architecture'])

        # Get D frontend version implemented in the compiler
        # gdc doesn't support this
        frontend_id = None
        frontend_version = None
        if comp_id in ['dmd', 'ldc']:
            ret, res = self._call_compbin(['--version'])[0:2]
            if ret != 0:
                mlog.error('Failed to run {!r}', mlog.bold(comp_id))
                return None
            d_ver_reg = re.search('v[0-9].[0-9][0-9][0-9].[0-9]', res) # Ex.: v2.081.2
            if d_ver_reg is not None:
                frontend_version = d_ver_reg.group()
                frontend_id = frontend_version.rsplit('.', 1)[0].replace('v', '').replace('.', '') # Fix structure. Ex.: 2081

        build_id = f'{conf}-{build_type}-{platform}-{arch}-{comp_id}'

        for entry in os.listdir(dub_build_path):
            if not build_id in entry:
                continue

            found_version = False
            if self.compiler.version in entry:
                found_version = True
            elif frontend_id and frontend_id in entry:
                found_version = True
            elif frontend_version and frontend_version in entry:
                found_version = True
            if not found_version:
                continue

            target = os.path.join(dub_build_path, entry, jpack['targetFileName'])
            if os.path.exists(target):
                return target

        return None


    def _call_dubbin(self, args: T.List[str], env: T.Optional[T.Dict[str, str]] = None) -> T.Tuple[int, str]:
        assert isinstance(self.dubbin, ExternalProgram)
        p, out, err = Popen_safe(self.dubbin.get_command() + args, env=env)
        return p.returncode, out.strip(), err.strip()

    def _call_compbin(self, args: T.List[str], env: T.Optional[T.Dict[str, str]] = None) -> T.Tuple[int, str]:
        p, out, err = Popen_safe(self.compiler.get_exelist() + args, env=env)
        return p.returncode, out.strip(), err.strip()

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
