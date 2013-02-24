#!/usr/bin/python3 -tt

# Copyright 2012 Jussi Pakkanen

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This file contains all data that must persist over multiple
# invocations of Meson. It is roughly the same thing as
# cmakecache.

import pickle

class CoreData():
    
    def __init__(self, options):
        self.prefix = options.prefix
        self.libdir = options.libdir
        self.bindir = options.bindir
        self.includedir = options.includedir
        self.datadir = options.datadir
        self.mandir = options.mandir
        self.backend = options.backend
        self.buildtype = options.buildtype
        self.strip = options.strip
        self.coverage = options.coverage

        self.deps = {}
        # To prevent weird bugs, compiler name can not be altered
        # after it is first declared. So always copy all compilers
        # from old coredata.
        if isinstance(options, CoreData):
            self.compilers = options.compilers.copy()
        else:
            self.compilers = {}

def load(filename):
    obj = pickle.load(open(filename, 'rb'))
    if not isinstance(obj, CoreData):
        raise RuntimeError('Core data file is corrupted.')
    return obj

def save(obj, filename):
    pickle.dump(obj, open(filename, 'wb'))
