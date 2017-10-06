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

# This file contains the detection logic for external dependencies useful for
# development purposes, such as testing, debugging, etc..

import os
import shlex
import shutil

from .. import mlog
from .. import mesonlib
from ..mesonlib import version_compare, Popen_safe, stringlistify, extract_as_list
from .base import DependencyException, ExternalDependency, PkgConfigDependency

class GTestDependency(ExternalDependency):
    def __init__(self, environment, kwargs):
        super().__init__('gtest', environment, 'cpp', kwargs)
        self.main = kwargs.get('main', False)
        self.src_dirs = ['/usr/src/gtest/src', '/usr/src/googletest/googletest/src']
        self.detect()

    def detect(self):
        self.version = '1.something_maybe'
        gtest_detect = self.compiler.find_library("gtest", self.env, [])
        gtest_main_detect = self.compiler.find_library("gtest_main", self.env, [])
        if gtest_detect and (not self.main or gtest_main_detect):
            self.is_found = True
            self.compile_args = []
            self.link_args = gtest_detect
            if self.main:
                self.link_args += gtest_main_detect
            self.sources = []
            mlog.log('Dependency GTest found:', mlog.green('YES'), '(prebuilt)')
        elif self.detect_srcdir():
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

    def detect_srcdir(self):
        for s in self.src_dirs:
            if os.path.exists(s):
                self.src_dir = s
                self.all_src = mesonlib.File.from_absolute_file(
                    os.path.join(self.src_dir, 'gtest-all.cc'))
                self.main_src = mesonlib.File.from_absolute_file(
                    os.path.join(self.src_dir, 'gtest_main.cc'))
                self.src_include_dir = os.path.normpath(os.path.join(self.src_dir, '..'))
                return True
        return False

    def need_threads(self):
        return True


class GMockDependency(ExternalDependency):
    def __init__(self, environment, kwargs):
        super().__init__('gmock', environment, 'cpp', kwargs)
        self.version = '1.something_maybe'
        # GMock may be a library or just source.
        # Work with both.
        gmock_detect = self.compiler.find_library("gmock", self.env, [])
        if gmock_detect:
            self.is_found = True
            self.compile_args = []
            self.link_args = gmock_detect
            self.sources = []
            mlog.log('Dependency GMock found:', mlog.green('YES'), '(prebuilt)')
            return

        for d in ['/usr/src/googletest/googlemock/src', '/usr/src/gmock/src', '/usr/src/gmock']:
            if os.path.exists(d):
                self.is_found = True
                # Yes, we need both because there are multiple
                # versions of gmock that do different things.
                d2 = os.path.normpath(os.path.join(d, '..'))
                self.compile_args = ['-I' + d, '-I' + d2]
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


class LLVMDependency(ExternalDependency):
    """
    LLVM uses a special tool, llvm-config, which has arguments for getting
    c args, cxx args, and ldargs as well as version.
    """

    # Ordered list of llvm-config binaries to try. Start with base, then try
    # newest back to oldest (3.5 is abitrary), and finally the devel version.
    # Please note that llvm-config-5.0 is a development snapshot and it should
    # not be moved to the beginning of the list. The only difference between
    # llvm-config-5.0 and llvm-config-devel is that the former is used by
    # Debian and the latter is used by FreeBSD.
    llvm_config_bins = [
        'llvm-config', # base
        'llvm-config-4.0', 'llvm-config40', # latest stable release
        'llvm-config-3.9', 'llvm-config39', # old stable releases
        'llvm-config-3.8', 'llvm-config38',
        'llvm-config-3.7', 'llvm-config37',
        'llvm-config-3.6', 'llvm-config36',
        'llvm-config-3.5', 'llvm-config35',
        'llvm-config-5.0', 'llvm-config-devel', # development snapshot
    ]
    __cpp_blacklist = {'-DNDEBUG'}

    def __init__(self, environment, kwargs):
        # It's necessary for LLVM <= 3.8 to use the C++ linker. For 3.9 and 4.0
        # the C linker works fine if only using the C API.
        super().__init__('llvm-config', environment, 'cpp', kwargs)
        self.modules = []
        self.llvmconfig = None
        self.__best_found = None
        # FIXME: Support multiple version requirements ala PkgConfigDependency
        req_version = kwargs.get('version', None)
        self.check_llvmconfig(req_version)
        if self.llvmconfig is None:
            if self.__best_found is not None:
                mlog.log('found {!r} but need:'.format(self.__best_found),
                         req_version)
            else:
                mlog.log("No llvm-config found; can't detect dependency")
            mlog.log('Dependency LLVM found:', mlog.red('NO'))
            if self.required:
                raise DependencyException('Dependency LLVM not found')
            return

        p, out, err = Popen_safe([self.llvmconfig, '--version'])
        if p.returncode != 0:
            mlog.debug('stdout: {}\nstderr: {}'.format(out, err))
            if self.required:
                raise DependencyException('Dependency LLVM not found')
            mlog.log('Dependency LLVM found:', mlog.red('NO'))
            return

        mlog.log('Dependency LLVM found:', mlog.green('YES'))
        self.is_found = True

        # Currently meson doesn't really atempt to handle pre-release versions,
        # so strip the 'svn' off the end, since it will probably cuase problems
        # for users who want the patch version.
        self.version = out.strip().rstrip('svn')

        p, out = Popen_safe(
            [self.llvmconfig, '--libs', '--ldflags'])[:2]
        if p.returncode != 0:
            raise DependencyException('Could not generate libs for LLVM.')
        self.link_args = shlex.split(out)

        p, out = Popen_safe([self.llvmconfig, '--cppflags'])[:2]
        if p.returncode != 0:
            raise DependencyException('Could not generate includedir for LLVM.')
        cargs = mesonlib.OrderedSet(shlex.split(out))
        self.compile_args = list(cargs.difference(self.__cpp_blacklist))

        p, out = Popen_safe([self.llvmconfig, '--components'])[:2]
        if p.returncode != 0:
            raise DependencyException('Could not generate modules for LLVM.')
        self.modules = shlex.split(out)

        modules = stringlistify(extract_as_list(kwargs, 'modules'))
        for mod in sorted(set(modules)):
            if mod not in self.modules:
                mlog.log('LLVM module', mod, 'found:', mlog.red('NO'))
                self.is_found = False
                if self.required:
                    raise DependencyException(
                        'Could not find required LLVM Component: {}'.format(mod))
            else:
                mlog.log('LLVM module', mod, 'found:', mlog.green('YES'))

    def check_llvmconfig(self, version_req):
        """Try to find the highest version of llvm-config."""
        for llvmconfig in self.llvm_config_bins:
            try:
                p, out = Popen_safe([llvmconfig, '--version'])[0:2]
                out = out.strip()
                if p.returncode != 0:
                    continue
                if version_req:
                    if version_compare(out, version_req, strict=True):
                        if self.__best_found and version_compare(
                                out, '<={}'.format(self.__best_found), strict=True):
                            continue
                        self.__best_found = out
                        self.llvmconfig = llvmconfig
                else:
                    # If no specific version is requested use the first version
                    # found, since that should be the best.
                    self.__best_found = out
                    self.llvmconfig = llvmconfig
                    break
            except (FileNotFoundError, PermissionError):
                pass
        if self.__best_found:
            mlog.log('Found llvm-config:',
                     mlog.bold(shutil.which(self.llvmconfig)),
                     '({})'.format(out.strip()))

    def need_threads(self):
        return True


class ValgrindDependency(PkgConfigDependency):
    '''
    Consumers of Valgrind usually only need the compile args and do not want to
    link to its (static) libraries.
    '''
    def __init__(self, env, kwargs):
        super().__init__('valgrind', env, kwargs)

    def get_link_args(self):
        return []
