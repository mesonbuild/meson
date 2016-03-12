# Copyright 2012-2016 The Meson development team

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

version = '0.30.0'

build_types = ['plain', 'debug', 'debugoptimized', 'release']
layouts = ['mirror', 'flat']
warning_levels = ['1', '2', '3']
libtypelist = ['shared', 'static']

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
                   'default_library': True,
                  }

class MesonException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class UserOption:
    def __init__(self, name, description, choices):
        super().__init__()
        self.name = name
        self.choices = choices
        self.description = description

    def parse_string(self, valuestring):
        return valuestring

class UserStringOption(UserOption):
    def __init__(self, name, description, value, choices=None):
        super().__init__(name, description, choices)
        self.set_value(value)

    def validate(self, value):
        if not isinstance(value, str):
            raise MesonException('Value "%s" for string option "%s" is not a string.' % (str(value), self.name))
        if self.name == 'prefix' and not os.path.isabs(value):
            raise MesonException('Prefix option value \'{0}\' must be an absolute path.'.format(value))
        if self.name in ('libdir', 'bindir', 'includedir', 'datadir', 'mandir', 'localedir') \
            and os.path.isabs(value):
            raise MesonException('Option %s must not be an absolute path.' % self.name)

    def set_value(self, newvalue):
        self.validate(newvalue)
        self.value = newvalue

class UserBooleanOption(UserOption):
    def __init__(self, name, description, value):
        super().__init__(name, description, '[true, false]')
        self.set_value(value)

    def tobool(self, thing):
        if isinstance(thing, bool):
            return thing
        if thing.lower() == 'true':
            return True
        if thing.lower() == 'false':
            return False
        raise MesonException('Value %s is not boolean (true or false).' % thing)

    def set_value(self, newvalue):
        self.value = self.tobool(newvalue)

    def parse_string(self, valuestring):
        if valuestring == 'false':
            return False
        if valuestring == 'true':
            return True
        raise MesonException('Value "%s" for boolean option "%s" is not a boolean.' % (valuestring, self.name))

class UserComboOption(UserOption):
    def __init__(self, name, description, choices, value):
        super().__init__(name, description, choices)
        if not isinstance(self.choices, list):
            raise MesonException('Combo choices must be an array.')
        for i in self.choices:
            if not isinstance(i, str):
                raise MesonException('Combo choice elements must be strings.')
        self.set_value(value)

    def set_value(self, newvalue):
        if newvalue not in self.choices:
            optionsstring = ', '.join(['"%s"' % (item,) for item in self.choices])
            raise MesonException('Value "%s" for combo option "%s" is not one of the choices. Possible choices are: %s.' % (newvalue, self.name, optionsstring))
        self.value = newvalue

class UserStringArrayOption(UserOption):
    def __init__(self, name, description, value, **kwargs):
        super().__init__(name, description, kwargs.get('choices', []))
        self.set_value(value)

    def set_value(self, newvalue):
        if isinstance(newvalue, str):
            if not newvalue.startswith('['):
                raise MesonException('Valuestring does not define an array: ' + newvalue)
            newvalue = eval(newvalue, {}, {}) # Yes, it is unsafe.
        if not isinstance(newvalue, list):
            raise MesonException('String array value is not an array.')
        for i in newvalue:
            if not isinstance(i, str):
                raise MesonException('String array element not a string.')
        self.value = newvalue

# This class contains all data that must persist over multiple
# invocations of Meson. It is roughly the same thing as
# cmakecache.

class CoreData():

    def __init__(self, options):
        self.guid = str(uuid.uuid4()).upper()
        self.test_guid = str(uuid.uuid4()).upper()
        self.regen_guid = str(uuid.uuid4()).upper()
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
        self.modules = {}

    def init_builtins(self, options):
        self.builtin_options['prefix'] = UserStringOption('prefix', 'Installation prefix', options.prefix)
        self.builtin_options['libdir'] = UserStringOption('libdir', 'Library dir', options.libdir)
        self.builtin_options['bindir'] = UserStringOption('bindir', 'Executable dir', options.bindir)
        self.builtin_options['includedir'] = UserStringOption('includedir', 'Include dir', options.includedir)
        self.builtin_options['datadir'] = UserStringOption('datadir', 'Data directory', options.datadir)
        self.builtin_options['mandir'] = UserStringOption('mandir', 'Man page dir', options.mandir)
        self.builtin_options['localedir'] = UserStringOption('localedir', 'Locale dir', options.localedir)
        self.builtin_options['backend'] = UserStringOption('backend', 'Backend to use', options.backend)
        self.builtin_options['buildtype'] = UserComboOption('buildtype', 'Build type', build_types, options.buildtype)
        self.builtin_options['strip'] = UserBooleanOption('strip', 'Strip on install', options.strip)
        self.builtin_options['use_pch'] = UserBooleanOption('use_pch', 'Use precompiled headers', options.use_pch)
        self.builtin_options['unity'] = UserBooleanOption('unity', 'Unity build', options.unity)
        self.builtin_options['coverage'] = UserBooleanOption('coverage', 'Enable coverage', options.coverage)
        self.builtin_options['warning_level'] = UserComboOption('warning_level', 'Warning level', warning_levels, options.warning_level)
        self.builtin_options['werror'] = UserBooleanOption('werror', 'Warnings are errors', options.werror)
        self.builtin_options['layout'] = UserComboOption('layout', 'Build dir layout', layouts, options.layout)
        self.builtin_options['default_library'] = UserComboOption('default_library', 'Default_library type', libtypelist, options.default_library)

    def get_builtin_option(self, optname):
        if optname in self.builtin_options:
            return self.builtin_options[optname].value
        raise RuntimeError('Tried to get unknown builtin option %s' % optname)

    def set_builtin_option(self, optname, value):
        if optname in self.builtin_options:
            self.builtin_options[optname].set_value(value)
        else:
            raise RuntimeError('Tried to set unknown builtin option %s' % optname)

    def is_builtin_option(self, optname):
        return optname in self.builtin_options

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
                          'test-': None,
                          'benchmark': None,
                          'install': None,
                          'build.ninja': None,
                         }
