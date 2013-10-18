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

import pickle, os

version = '0.9.0-research'

# This class contains all data that must persist over multiple
# invocations of Meson. It is roughly the same thing as
# cmakecache.

class CoreData():

    def __init__(self, options):
        self.version = version
        self.prefix = options.prefix
        self.libdir = options.libdir
        self.bindir = options.bindir
        self.includedir = options.includedir
        self.datadir = options.datadir
        self.mandir = options.mandir
        self.localedir = options.localedir
        self.backend = options.backend
        self.buildtype = options.buildtype
        self.strip = options.strip
        self.use_pch = options.use_pch
        self.coverage = options.coverage
        self.user_options = {}
        if options.cross_file is not None:
            self.cross_file = os.path.join(os.getcwd(), options.cross_file)
        else:
            self.cross_file = None

        self.compilers = {}
        self.cross_compilers = {}
        self.deps = {}
        self.ext_progs = {}
        self.ext_libs = {}

def load(filename):
    obj = pickle.load(open(filename, 'rb'))
    if not isinstance(obj, CoreData):
        raise RuntimeError('Core data file is corrupted.')
    if obj.version != version:
        raise RuntimeError('Build tree has been generated with Meson version %s, which is incompatible with current version %s.'%
                           (obj.version, version))
    return obj

def save(obj, filename):
    if obj.version != version:
        raise RuntimeError('Fatal version mismatch corruption.')
    pickle.dump(obj, open(filename, 'wb'))

forbidden_target_names = {'clean': None,
                          'clean-gcno': None,
                          'clean-gcda': None,
                          'coverage-text': None,
                          'coverage-xml': None,
                          'coverage-html': None,
                          'phony': None,
                          'all': None,
                          'test': None,
                          'test-valgrind': None,
                          'install': None,
                          'build.ninja': None,
                          'cppcheck': None,
                          }

class MesonException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
