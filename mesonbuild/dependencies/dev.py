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
import re

from .. import mlog
from .. import mesonlib
from ..mesonlib import version_compare, stringlistify, extract_as_list
from .base import (
    DependencyException, ExternalDependency, PkgConfigDependency,
    strip_system_libdirs, ConfigToolDependency,
)


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


class LLVMDependency(ConfigToolDependency):
    """
    LLVM uses a special tool, llvm-config, which has arguments for getting
    c args, cxx args, and ldargs as well as version.
    """

    # Ordered list of llvm-config binaries to try. Start with base, then try
    # newest back to oldest (3.5 is arbitrary), and finally the devel version.
    # Please note that llvm-config-6.0 is a development snapshot and it should
    # not be moved to the beginning of the list. The only difference between
    # llvm-config-6.0 and llvm-config-devel is that the former is used by
    # Debian and the latter is used by FreeBSD.
    tools = [
        'llvm-config', # base
        'llvm-config-5.0', 'llvm-config50', # latest stable release
        'llvm-config-4.0', 'llvm-config40', # old stable releases
        'llvm-config-3.9', 'llvm-config39',
        'llvm-config-3.8', 'llvm-config38',
        'llvm-config-3.7', 'llvm-config37',
        'llvm-config-3.6', 'llvm-config36',
        'llvm-config-3.5', 'llvm-config35',
        'llvm-config-6.0', 'llvm-config-devel', # development snapshot
    ]
    tool_name = 'llvm-config'
    __cpp_blacklist = {'-DNDEBUG'}

    def __init__(self, environment, kwargs):
        # It's necessary for LLVM <= 3.8 to use the C++ linker. For 3.9 and 4.0
        # the C linker works fine if only using the C API.
        super().__init__('LLVM', environment, 'cpp', kwargs)
        self.provided_modules = []
        self.required_modules = set()
        if not self.is_found:
            return
        self.static = kwargs.get('static', False)

        self.provided_modules = self.get_config_value(['--components'], 'modules')
        modules = stringlistify(extract_as_list(kwargs, 'modules'))
        self.check_components(modules)
        opt_modules = stringlistify(extract_as_list(kwargs, 'optional_modules'))
        self.check_components(opt_modules, required=False)

        cargs = set(self.get_config_value(['--cppflags'], 'compile_args'))
        self.compile_args = list(cargs.difference(self.__cpp_blacklist))

        if version_compare(self.version, '>= 3.9'):
            self._set_new_link_args()
        else:
            self._set_old_link_args()
        self.link_args = strip_system_libdirs(environment, self.link_args)
        self.link_args = self.__fix_bogus_link_args(self.link_args)

    @staticmethod
    def __fix_bogus_link_args(args):
        """This function attempts to fix bogus link arguments that llvm-config
        generates.

        Currently it works around the following:
            - FreeBSD: when statically linking -l/usr/lib/libexecinfo.so will
              be generated, strip the -l in cases like this.
        """
        new_args = []
        for arg in args:
            if arg.startswith('-l') and arg.endswith('.so'):
                new_args.append(arg.lstrip('-l'))
            else:
                new_args.append(arg)
        return new_args

    def _set_new_link_args(self):
        """How to set linker args for LLVM versions >= 3.9"""
        if ((mesonlib.is_dragonflybsd() or mesonlib.is_freebsd()) and not
                self.static and version_compare(self.version, '>= 4.0')):
            # llvm-config on DragonFly BSD and FreeBSD for versions 4.0, 5.0,
            # and 6.0 have an error when generating arguments for shared mode
            # linking, even though libLLVM.so is installed, because for some
            # reason the tool expects to find a .so for each static library.
            # This works around that.
            self.link_args = self.get_config_value(['--ldflags'], 'link_args')
            self.link_args.append('-lLLVM')
            return
        link_args = ['--link-static', '--system-libs'] if self.static else ['--link-shared']
        self.link_args = self.get_config_value(
            ['--libs', '--ldflags'] + link_args + list(self.required_modules),
            'link_args')

    def _set_old_link_args(self):
        """Setting linker args for older versions of llvm.

        Old versions of LLVM bring an extra level of insanity with them.
        llvm-config will provide the correct arguments for static linking, but
        not for shared-linnking, we have to figure those out ourselves, because
        of course we do.
        """
        if self.static:
            self.link_args = self.get_config_value(
                ['--libs', '--ldflags', '--system-libs'] + list(self.required_modules),
                'link_args')
        else:
            # llvm-config will provide arguments for static linking, so we get
            # to figure out for ourselves what to link with. We'll do that by
            # checking in the directory provided by --libdir for a library
            # called libLLVM-<ver>.(so|dylib|dll)
            libdir = self.get_config_value(['--libdir'], 'link_args')[0]

            expected_name = 'libLLVM-{}'.format(self.version)
            re_name = re.compile(r'{}.(so|dll|dylib)'.format(expected_name))

            for file_ in os.listdir(libdir):
                if re_name.match(file_):
                    self.link_args = ['-L{}'.format(libdir),
                                      '-l{}'.format(os.path.splitext(file_.lstrip('lib'))[0])]
                    break
            else:
                raise DependencyException(
                    'Could not find a dynamically linkable library for LLVM.')

    def check_components(self, modules, required=True):
        """Check for llvm components (modules in meson terms).

        The required option is whether the module is required, not whether LLVM
        is required.
        """
        for mod in sorted(set(modules)):
            if mod not in self.provided_modules:
                mlog.log('LLVM module', mlog.bold(mod), 'found:', mlog.red('NO'),
                         '(optional)' if not required else '')
                if required:
                    self.is_found = False
                    if self.required:
                        raise DependencyException(
                            'Could not find required LLVM Component: {}'.format(mod))
            else:
                self.required_modules.add(mod)
                mlog.log('LLVM module', mlog.bold(mod), 'found:', mlog.green('YES'))

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
