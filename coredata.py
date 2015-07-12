# Copyright 2012-2015 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pickle, os, uuid

version = '0.26.0-research'

builtin_options = {'buildtype': True,
                          'strip': True,
                          'coverage': True,
                          'pch': True,
                          'unity': True,
                          'prefix': True,
                          'libdir' : True,
                          'bindir' : True,
                          'includedir' : True,
                          'datadir' : True,
                          'mandir' : True,
                          'localedir' : True,
                          'werror' : True,
                         }
# This class contains all data that must persist over multiple
# invocations of Meson. It is roughly the same thing as
# cmakecache.

class CoreData():

    def __init__(self, options):
        self.guid = str(uuid.uuid4()).upper()
        self.test_guid = str(uuid.uuid4()).upper()
        self.target_guids = {}
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
        self.unity = options.unity
        self.coverage = options.coverage
        self.werror = options.werror
        self.user_options = {}
        self.external_args = {} # These are set from "the outside" with e.g. mesonconf
        self.external_link_args = {}
        if options.cross_file is not None:
            self.cross_file = os.path.join(os.getcwd(), options.cross_file)
        else:
            self.cross_file = None

        self.compilers = {}
        self.cross_compilers = {}
        self.deps = {}
        self.ext_progs = {}
        self.ext_libs = {}
        self.modules = {}

    def get_builtin_option(self, optname):
        if optname == 'buildtype':
            return self.buildtype
        if optname == 'strip':
            return self.strip
        if optname == 'coverage':
            return self.coverage
        if optname == 'pch':
            return self.use_pch
        if optname == 'unity':
            return self.unity
        if optname == 'prefix':
            return self.prefix
        if optname == 'libdir':
            return self.libdir
        if optname == 'bindir':
            return self.bindir
        if optname == 'includedir':
            return self.includedir
        if optname == 'datadir':
            return self.datadir
        if optname == 'mandir':
            return self.mandir
        if optname == 'localedir':
            return self.localedir
        raise RuntimeError('Tried to get unknown builtin option %s' % optname)

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
                          'PHONY': None,
                          'all': None,
                          'test': None,
                          'test-valgrind': None,
                          'install': None,
                          'build.ninja': None,
                         }

class MesonException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
