#!/usr/bin/env python3 -tt

# Copyright 2013 Jussi Pakkanen

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This file contains the detection logic for all those
# packages and frameworks that either don't provide
# a pkg-confg file or require extra functionality
# that can't be expressed with it.

# Currently one file, should probably be split into a
# package before this gets too big.

import os, stat, glob
from interpreter import InvalidArguments

class BoostDependency():
    def __init__(self, kwargs):
        self.incdir = '/usr/include/boost'
        self.libdir = '/usr/lib'
        self.src_modules = {}
        self.lib_modules = {}
        self.detect_version()
        self.requested_modules = self.get_requested(kwargs)

        if self.version is not None:
            self.detect_src_modules()
            self.detect_lib_modules()
            self.validate_requested()
    
    def get_compile_flags(self):
        return []

    def get_requested(self, kwargs):
        modules = 'modules'
        if not modules in kwargs:
            raise InvalidArguments('Boost dependency must specify "%s" keyword.' % modules)
        candidates = kwargs[modules]
        if isinstance(candidates, str):
            return [candidates]
        for c in candidates:
            if not isinstance(c, str):
                raise InvalidArguments('Boost module argument is not a string.')
        return candidates

    def validate_requested(self):
        for m in self.requested_modules:
            if m not in self.src_modules:
                raise InvalidArguments('Requested Boost module "%s" not found.' % m)

    def found(self):
        return self.version is not None

    def get_version(self):
        return self.version

    def detect_version(self):
        ifile = open(os.path.join(self.incdir, 'version.hpp'))
        for line in ifile:
            if line.startswith("#define") and 'BOOST_LIB_VERSION' in line:
                ver = line.split()[-1]
                ver = ver[1:-1]
                self.version = ver.replace('_', '.')
                return
        self.version = None

    def detect_src_modules(self):
        for entry in os.listdir(self.incdir):
            entry = os.path.join(self.incdir, entry)
            if stat.S_ISDIR(os.stat(entry).st_mode):
                self.src_modules[os.path.split(entry)[-1]] = True

    def detect_lib_modules(self):
        globber = 'libboost_*.so' # FIXME, make platform independent.
        for entry in glob.glob(os.path.join(self.libdir, globber)):
            if entry.endswith('-mt.so'): # Fixme, seems to be Windows specific.
                continue
            lib = os.path.basename(entry)
            self.lib_modules[(lib.split('.')[0].split('_', 1)[-1])] = True

    def get_link_flags(self):
        flags = [] # Fixme, add -L if necessary.
        for module in self.requested_modules:
            if module in self.lib_modules:
                linkcmd = '-lboost_' + module
                flags.append(linkcmd)
        return flags

    def get_sources(self):
        return []

class GTestDependency():
    def __init__(self, kwargs):
        self.include_dir = '/usr/include'
        self.src_include_dir = '/usr/src/gtest'
        self.src_dir = '/usr/src/gtest/src'
        self.all_src = os.path.join(self.src_dir, 'gtest-all.cc')
        self.main_src = os.path.join(self.src_dir, 'gtest_main.cc')

    def found(self):
        return os.path.exists(self.all_src)
    def get_compile_flags(self):
        return ['-I' + self.include_dir, '-I' + self.src_include_dir]
    def get_link_flags(self):
        return []
    def get_version(self):
        return '1.something_maybe'

    def get_sources(self):
        return [self.all_src, self.main_src]

packages = {'boost': BoostDependency,
            'gtest': GTestDependency,
            }
