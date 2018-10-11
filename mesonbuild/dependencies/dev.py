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

import functools
import glob
import os
import re

from .. import mesonlib
from ..mesonlib import version_compare, stringlistify, extract_as_list
from .base import (
    DependencyException, DependencyMethods, ExternalDependency, PkgConfigDependency,
    strip_system_libdirs, ConfigToolDependency,
)


def get_shared_library_suffix(environment, native):
    """This is only gauranteed to work for languages that compile to machine
    code, not for languages like C# that use a bytecode and always end in .dll
    """
    if mesonlib.for_windows(native, environment):
        return '.dll'
    elif mesonlib.for_darwin(native, environment):
        return '.dylib'
    return '.so'


class GTestDependency(ExternalDependency):
    def __init__(self, environment, kwargs):
        super().__init__('gtest', environment, 'cpp', kwargs)
        self.main = kwargs.get('main', False)
        self.src_dirs = ['/usr/src/gtest/src', '/usr/src/googletest/googletest/src']
        self.detect()

    def detect(self):
        gtest_detect = self.clib_compiler.find_library("gtest", self.env, [])
        gtest_main_detect = self.clib_compiler.find_library("gtest_main", self.env, [])
        if gtest_detect and (not self.main or gtest_main_detect):
            self.is_found = True
            self.compile_args = []
            self.link_args = gtest_detect
            if self.main:
                self.link_args += gtest_main_detect
            self.sources = []
            self.prebuilt = True
        elif self.detect_srcdir():
            self.is_found = True
            self.compile_args = ['-I' + d for d in self.src_include_dirs]
            self.link_args = []
            if self.main:
                self.sources = [self.all_src, self.main_src]
            else:
                self.sources = [self.all_src]
            self.prebuilt = False
        else:
            self.is_found = False

    def detect_srcdir(self):
        for s in self.src_dirs:
            if os.path.exists(s):
                self.src_dir = s
                self.all_src = mesonlib.File.from_absolute_file(
                    os.path.join(self.src_dir, 'gtest-all.cc'))
                self.main_src = mesonlib.File.from_absolute_file(
                    os.path.join(self.src_dir, 'gtest_main.cc'))
                self.src_include_dirs = [os.path.normpath(os.path.join(self.src_dir, '..')),
                                         os.path.normpath(os.path.join(self.src_dir, '../include')),
                                         ]
                return True
        return False

    def need_threads(self):
        return True

    def log_info(self):
        if self.prebuilt:
            return 'prebuilt'
        else:
            return 'building self'

    def log_tried(self):
        return 'system'

    @classmethod
    def _factory(cls, environment, kwargs):
        methods = cls._process_method_kw(kwargs)
        candidates = []

        if DependencyMethods.PKGCONFIG in methods:
            pcname = 'gtest_main' if kwargs.get('main', False) else 'gtest'
            candidates.append(functools.partial(PkgConfigDependency, pcname, environment, kwargs))

        if DependencyMethods.SYSTEM in methods:
            candidates.append(functools.partial(GTestDependency, environment, kwargs))

        return candidates

    @staticmethod
    def get_methods():
        return [DependencyMethods.PKGCONFIG, DependencyMethods.SYSTEM]


class GMockDependency(ExternalDependency):
    def __init__(self, environment, kwargs):
        super().__init__('gmock', environment, 'cpp', kwargs)
        self.main = kwargs.get('main', False)

        # If we are getting main() from GMock, we definitely
        # want to avoid linking in main() from GTest
        gtest_kwargs = kwargs.copy()
        if self.main:
            gtest_kwargs['main'] = False

        # GMock without GTest is pretty much useless
        # this also mimics the structure given in WrapDB,
        # where GMock always pulls in GTest
        gtest_dep = GTestDependency(environment, gtest_kwargs)
        if not gtest_dep.is_found:
            self.is_found = False
            return

        self.compile_args = gtest_dep.compile_args
        self.link_args = gtest_dep.link_args
        self.sources = gtest_dep.sources

        # GMock may be a library or just source.
        # Work with both.
        gmock_detect = self.clib_compiler.find_library("gmock", self.env, [])
        gmock_main_detect = self.clib_compiler.find_library("gmock_main", self.env, [])
        if gmock_detect and (not self.main or gmock_main_detect):
            self.is_found = True
            self.link_args += gmock_detect
            if self.main:
                self.link_args += gmock_main_detect
            self.prebuilt = True
            return

        for d in ['/usr/src/googletest/googlemock/src', '/usr/src/gmock/src', '/usr/src/gmock']:
            if os.path.exists(d):
                self.is_found = True
                # Yes, we need both because there are multiple
                # versions of gmock that do different things.
                d2 = os.path.normpath(os.path.join(d, '..'))
                self.compile_args += ['-I' + d, '-I' + d2, '-I' + os.path.join(d2, 'include')]
                all_src = mesonlib.File.from_absolute_file(os.path.join(d, 'gmock-all.cc'))
                main_src = mesonlib.File.from_absolute_file(os.path.join(d, 'gmock_main.cc'))
                if self.main:
                    self.sources += [all_src, main_src]
                else:
                    self.sources += [all_src]
                self.prebuilt = False
                return

        self.is_found = False

    def need_threads(self):
        return True

    def log_info(self):
        if self.prebuilt:
            return 'prebuilt'
        else:
            return 'building self'

    def log_tried(self):
        return 'system'

    @classmethod
    def _factory(cls, environment, kwargs):
        methods = cls._process_method_kw(kwargs)
        candidates = []

        if DependencyMethods.PKGCONFIG in methods:
            pcname = 'gmock_main' if kwargs.get('main', False) else 'gmock'
            candidates.append(functools.partial(PkgConfigDependency, pcname, environment, kwargs))

        if DependencyMethods.SYSTEM in methods:
            candidates.append(functools.partial(GMockDependency, environment, kwargs))

        return candidates

    @staticmethod
    def get_methods():
        return [DependencyMethods.PKGCONFIG, DependencyMethods.SYSTEM]


class LLVMDependency(ConfigToolDependency):
    """
    LLVM uses a special tool, llvm-config, which has arguments for getting
    c args, cxx args, and ldargs as well as version.
    """

    # Ordered list of llvm-config binaries to try. Start with base, then try
    # newest back to oldest (3.5 is arbitrary), and finally the devel version.
    # Please note that llvm-config-6.0 is a development snapshot and it should
    # not be moved to the beginning of the list. The only difference between
    # llvm-config-8 and llvm-config-devel is that the former is used by
    # Debian and the latter is used by FreeBSD.
    tools = [
        'llvm-config', # base
        'llvm-config-7',   'llvm-config70',
        'llvm-config-6.0', 'llvm-config60',
        'llvm-config-5.0', 'llvm-config50',
        'llvm-config-4.0', 'llvm-config40',
        'llvm-config-3.9', 'llvm-config39',
        'llvm-config-3.8', 'llvm-config38',
        'llvm-config-3.7', 'llvm-config37',
        'llvm-config-3.6', 'llvm-config36',
        'llvm-config-3.5', 'llvm-config35',
        'llvm-config-8',   'llvm-config-devel', # development snapshot
    ]
    tool_name = 'llvm-config'
    __cpp_blacklist = {'-DNDEBUG'}

    def __init__(self, environment, kwargs):
        # It's necessary for LLVM <= 3.8 to use the C++ linker. For 3.9 and 4.0
        # the C linker works fine if only using the C API.
        super().__init__('LLVM', environment, 'cpp', kwargs)
        self.provided_modules = []
        self.required_modules = set()
        self.module_details = []
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
            self._set_new_link_args(environment)
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

    def __check_libfiles(self, shared):
        """Use llvm-config's --libfiles to check if libraries exist."""
        mode = '--link-shared' if shared else '--link-static'

        # Set self.required to true to force an exception in get_config_value
        # if the returncode != 0
        restore = self.required
        self.required = True

        try:
            # It doesn't matter what the stage is, the caller needs to catch
            # the exception anyway.
            self.link_args = self.get_config_value(['--libfiles', mode], '')
        finally:
            self.required = restore

    def _set_new_link_args(self, environment):
        """How to set linker args for LLVM versions >= 3.9"""
        mode = self.get_config_value(['--shared-mode'], 'link_args')[0]
        if not self.static and mode == 'static':
            # If llvm is configured with LLVM_BUILD_LLVM_DYLIB but not with
            # LLVM_LINK_LLVM_DYLIB and not LLVM_BUILD_SHARED_LIBS (which
            # upstreams doesn't recomend using), then llvm-config will lie to
            # you about how to do shared-linking. It wants to link to a a bunch
            # of individual shared libs (which don't exist because llvm wasn't
            # built with LLVM_BUILD_SHARED_LIBS.
            #
            # Therefore, we'll try to get the libfiles, if the return code is 0
            # or we get an empty list, then we'll try to build a working
            # configuration by hand.
            try:
                self.__check_libfiles(True)
            except DependencyException:
                lib_ext = get_shared_library_suffix(environment, self.native)
                libdir = self.get_config_value(['--libdir'], 'link_args')[0]
                # Sort for reproducability
                matches = sorted(glob.iglob(os.path.join(libdir, 'libLLVM*{}'.format(lib_ext))))
                if not matches:
                    if self.required:
                        raise
                    self.is_found = False
                    return

                self.link_args = self.get_config_value(['--ldflags'], 'link_args')
                libname = os.path.basename(matches[0]).rstrip(lib_ext).lstrip('lib')
                self.link_args.append('-l{}'.format(libname))
                return
        elif self.static and mode == 'shared':
            # If, however LLVM_BUILD_SHARED_LIBS is true # (*cough* gentoo *cough*)
            # then this is correct. Building with LLVM_BUILD_SHARED_LIBS has a side
            # effect, it stops the generation of static archives. Therefore we need
            # to check for that and error out on static if this is the case
            try:
                self.__check_libfiles(False)
            except DependencyException:
                if self.required:
                    raise
                self.is_found = False
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
            re_name = re.compile(r'{}.(so|dll|dylib)$'.format(expected_name))

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
            status = ''

            if mod not in self.provided_modules:
                if required:
                    self.is_found = False
                    if self.required:
                        raise DependencyException(
                            'Could not find required LLVM Component: {}'.format(mod))
                    status = '(missing)'
                else:
                    status = '(missing but optional)'
            else:
                self.required_modules.add(mod)

            self.module_details.append(mod + status)

    def need_threads(self):
        return True

    def log_details(self):
        if self.module_details:
            return 'modules: ' + ', '.join(self.module_details)
        return ''


class ValgrindDependency(PkgConfigDependency):
    '''
    Consumers of Valgrind usually only need the compile args and do not want to
    link to its (static) libraries.
    '''
    def __init__(self, env, kwargs):
        super().__init__('valgrind', env, kwargs)

    def get_link_args(self, **kwargs):
        return []
