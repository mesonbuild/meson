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

version = '0.27.0-research'

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
                   'warning_level': True,
                   'layout' : True,
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
        self.builtin_options = {}
        self.init_builtins(options)
        self.user_options = {}
        self.compiler_options = {}
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

    def init_builtins(self, options):
        self.builtin_options['prefix'] = options.prefix
        self.builtin_options['libdir'] = options.libdir
        self.builtin_options['bindir'] = options.bindir
        self.builtin_options['includedir'] = options.includedir
        self.builtin_options['datadir'] = options.datadir
        self.builtin_options['mandir'] = options.mandir
        self.builtin_options['localedir'] = options.localedir
        self.builtin_options['backend'] = options.backend
        self.builtin_options['buildtype'] = options.buildtype
        self.builtin_options['strip'] = options.strip
        self.builtin_options['use_pch'] = options.use_pch
        self.builtin_options['unity'] = options.unity
        self.builtin_options['coverage'] = options.coverage
        self.builtin_options['warning_level'] = options.warning_level
        self.builtin_options['werror'] = options.werror
        self.builtin_options['layout'] = options.layout
        self.builtin_options['default_library'] = options.default_library

    def get_builtin_option(self, optname):
        if optname in self.builtin_options:
            return self.builtin_options[optname]
        raise RuntimeError('Tried to get unknown builtin option %s' % optname)

    def set_builtin_option(self, optname, value):
        if optname in self.builtin_options:
            self.builtin_options[optname] = value
        else:
            raise RuntimeError('Tried to set unknown builtin option %s' % optname)

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
