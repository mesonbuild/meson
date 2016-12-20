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
from .mesonlib import MesonException, default_libdir, default_libexecdir, default_prefix

version = '0.37.1'
backendlist = ['ninja', 'vs2010', 'vs2015', 'xcode']

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

    def set_value(self, newvalue):
        self.validate(newvalue)
        self.value = newvalue

class UserBooleanOption(UserOption):
    def __init__(self, name, description, value):
        super().__init__(name, description, [ True, False ])
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

    def __bool__(self):
        return self.value

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
            raise MesonException('"{0}" should be a string array, but it is not'.format(str(newvalue)))
        for i in newvalue:
            if not isinstance(i, str):
                raise MesonException('String array element "{0}" is not a string.'.format(str(newvalue)))
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
        self.init_builtins(options)
        self.user_options = {}
        self.compiler_options = {}
        self.base_options = {}
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
        # Only to print a warning if it changes between Meson invocations.
        self.pkgconf_envvar = os.environ.get('PKG_CONFIG_PATH', '')

    def init_builtins(self, options):
        self.builtins = {}
        for key in get_builtin_options():
            args = [key] + builtin_options[key][1:-1] + [ getattr(options, key, get_builtin_option_default(key)) ]
            self.builtins[key] = builtin_options[key][0](*args)

    def get_builtin_option(self, optname):
        if optname in self.builtins:
            return self.builtins[optname].value
        raise RuntimeError('Tried to get unknown builtin option %s.' % optname)

    def set_builtin_option(self, optname, value):
        if optname in self.builtins:
            self.builtins[optname].set_value(value)
        else:
            raise RuntimeError('Tried to set unknown builtin option %s.' % optname)

def load(filename):
    load_fail_msg = 'Coredata file {!r} is corrupted. Try with a fresh build tree.'.format(filename)
    try:
        with open(filename, 'rb') as f:
            obj = pickle.load(f)
    except pickle.UnpicklingError:
        raise MesonException(load_fail_msg)
    if not isinstance(obj, CoreData):
        raise MesonException(load_fail_msg)
    if obj.version != version:
        raise MesonException('Build directory has been generated with Meson version %s, which is incompatible with current version %s.\nPlease delete this build directory AND create a new one.'%
                           (obj.version, version))
    return obj

def save(obj, filename):
    if obj.version != version:
        raise MesonException('Fatal version mismatch corruption.')
    with open(filename, 'wb') as f:
        pickle.dump(obj, f)

def get_builtin_options():
    return list(builtin_options.keys())

def is_builtin_option(optname):
    return optname in get_builtin_options()

def get_builtin_option_choices(optname):
    if is_builtin_option(optname):
        if builtin_options[optname][0] == UserStringOption:
            return None
        elif builtin_options[optname][0] == UserBooleanOption:
            return [ True, False ]
        else:
            return builtin_options[optname][2]
    else:
        raise RuntimeError('Tried to get the supported values for an unknown builtin option \'%s\'.' % optname)

def get_builtin_option_description(optname):
    if is_builtin_option(optname):
        return builtin_options[optname][1]
    else:
        raise RuntimeError('Tried to get the description for an unknown builtin option \'%s\'.' % optname)

def get_builtin_option_default(optname):
    if is_builtin_option(optname):
        o = builtin_options[optname]
        if o[0] == UserComboOption:
            return o[3]
        return o[2]
    else:
        raise RuntimeError('Tried to get the default value for an unknown builtin option \'%s\'.' % optname)

builtin_options = {
        'buildtype'         : [ UserComboOption, 'Build type to use.', [ 'plain', 'debug', 'debugoptimized', 'release', 'minsize' ], 'debug' ],
        'strip'             : [ UserBooleanOption, 'Strip targets on install.', False ],
        'unity'             : [ UserBooleanOption, 'Unity build.', False ],
        'prefix'            : [ UserStringOption, 'Installation prefix.', default_prefix() ],
        'libdir'            : [ UserStringOption, 'Library directory.', default_libdir() ],
        'libexecdir'        : [ UserStringOption, 'Library executable directory.', default_libexecdir() ],
        'bindir'            : [ UserStringOption, 'Executable directory.', 'bin' ],
        'sbindir'           : [ UserStringOption, 'System executable directory.', 'sbin' ],
        'includedir'        : [ UserStringOption, 'Header file directory.', 'include' ],
        'datadir'           : [ UserStringOption, 'Data file directory.', 'share' ],
        'mandir'            : [ UserStringOption, 'Manual page directory.', 'share/man' ],
        'infodir'           : [ UserStringOption, 'Info page directory.', 'share/info' ],
        'localedir'         : [ UserStringOption, 'Locale data directory.', 'share/locale' ],
    # sysconfdir, localstatedir and sharedstatedir are a bit special. These defaults to ${prefix}/etc,
    # ${prefix}/var and ${prefix}/com but nobody uses that. Instead they always set it
    # manually to /etc, /var and /var/lib. This default values is thus pointless and not really used
    # but we set it to this for consistency with other systems.
    #
    # Projects installing to sysconfdir, localstatedir or sharedstatedir probably want
    # to set the following in project():
    #
    # default_options : ['sysconfdir=/etc', 'localstatedir=/var', 'sharedstatedir=/var/lib']
        'sysconfdir'        : [ UserStringOption, 'Sysconf data directory.', 'etc' ],
        'localstatedir'     : [ UserStringOption, 'Localstate data directory.', 'var' ],
        'sharedstatedir'    : [ UserStringOption, 'Architecture-independent data directory.', 'com' ],
        'werror'            : [ UserBooleanOption, 'Treat warnings as errors.', False ],
        'warning_level'     : [ UserComboOption, 'Compiler warning level to use.', [ '1', '2', '3' ], '1'],
        'layout'            : [ UserComboOption, 'Build directory layout.', ['mirror', 'flat' ], 'mirror' ],
        'default_library'   : [ UserComboOption, 'Default library type.', [ 'shared', 'static' ], 'shared' ],
        'backend'           : [ UserComboOption, 'Backend to use.', backendlist, 'ninja' ],
        'stdsplit'          : [ UserBooleanOption, 'Split stdout and stderr in test logs.', True ],
        'errorlogs'         : [ UserBooleanOption, "Whether to print the logs from failing tests.", True ],
        }

forbidden_target_names = {'clean': None,
                          'clean-ctlist': None,
                          'clean-gcno': None,
                          'clean-gcda': None,
                          'coverage-text': None,
                          'coverage-xml': None,
                          'coverage-html': None,
                          'phony': None,
                          'PHONY': None,
                          'all': None,
                          'test': None,
                          'test:': None,
                          'benchmark': None,
                          'install': None,
                          'build.ninja': None,
                          'scan-build': None,
                          'reconfigure': None,
                         }
