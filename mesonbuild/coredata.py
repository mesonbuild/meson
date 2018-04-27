# Copyright 2012-2018 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from . import mlog
import pickle, os, uuid
import sys
from pathlib import PurePath
from collections import OrderedDict
from .mesonlib import MesonException
from .mesonlib import default_libdir, default_libexecdir, default_prefix
import ast
import argparse

version = '0.47.0.dev1'
backendlist = ['ninja', 'vs', 'vs2010', 'vs2015', 'vs2017', 'xcode']

default_yielding = False

class UserOption:
    def __init__(self, name, description, choices, yielding):
        super().__init__()
        self.name = name
        self.choices = choices
        self.description = description
        if yielding is None:
            yielding = default_yielding
        if not isinstance(yielding, bool):
            raise MesonException('Value of "yielding" must be a boolean.')
        self.yielding = yielding

    # Check that the input is a valid value and return the
    # "cleaned" or "native" version. For example the Boolean
    # option could take the string "true" and return True.
    def validate_value(self, value):
        raise RuntimeError('Derived option class did not override validate_value.')

    def set_value(self, newvalue):
        self.value = self.validate_value(newvalue)

class UserStringOption(UserOption):
    def __init__(self, name, description, value, choices=None, yielding=None):
        super().__init__(name, description, choices, yielding)
        self.set_value(value)

    def validate_value(self, value):
        if not isinstance(value, str):
            raise MesonException('Value "%s" for string option "%s" is not a string.' % (str(value), self.name))
        return value

class UserBooleanOption(UserOption):
    def __init__(self, name, description, value, yielding=None):
        super().__init__(name, description, [True, False], yielding)
        self.set_value(value)

    def __bool__(self):
        return self.value

    def validate_value(self, value):
        if isinstance(value, bool):
            return value
        if value.lower() == 'true':
            return True
        if value.lower() == 'false':
            return False
        raise MesonException('Value %s is not boolean (true or false).' % value)

class UserIntegerOption(UserOption):
    def __init__(self, name, description, min_value, max_value, value, yielding=None):
        super().__init__(name, description, [True, False], yielding)
        self.min_value = min_value
        self.max_value = max_value
        self.set_value(value)
        c = []
        if min_value is not None:
            c.append('>=' + str(min_value))
        if max_value is not None:
            c.append('<=' + str(max_value))
        self.choices = ', '.join(c)

    def validate_value(self, value):
        if isinstance(value, str):
            value = self.toint(value)
        if not isinstance(value, int):
            raise MesonException('New value for integer option is not an integer.')
        if self.min_value is not None and value < self.min_value:
            raise MesonException('New value %d is less than minimum value %d.' % (value, self.min_value))
        if self.max_value is not None and value > self.max_value:
            raise MesonException('New value %d is more than maximum value %d.' % (value, self.max_value))
        return value

    def toint(self, valuestring):
        try:
            return int(valuestring)
        except ValueError:
            raise MesonException('Value string "%s" is not convertable to an integer.' % valuestring)

class UserUmaskOption(UserIntegerOption):
    def __init__(self, name, description, value, yielding=None):
        super().__init__(name, description, 0, 0o777, value, yielding)

    def set_value(self, newvalue):
        if newvalue is None or newvalue == 'preserve':
            self.value = None
        else:
            super().set_value(newvalue)

    def toint(self, valuestring):
        try:
            return int(valuestring, 8)
        except ValueError as e:
            raise MesonException('Invalid mode: {}'.format(e))

class UserComboOption(UserOption):
    def __init__(self, name, description, choices, value, yielding=None):
        super().__init__(name, description, choices, yielding)
        if not isinstance(self.choices, list):
            raise MesonException('Combo choices must be an array.')
        for i in self.choices:
            if not isinstance(i, str):
                raise MesonException('Combo choice elements must be strings.')
        self.set_value(value)

    def validate_value(self, value):
        if value not in self.choices:
            optionsstring = ', '.join(['"%s"' % (item,) for item in self.choices])
            raise MesonException('Value "%s" for combo option "%s" is not one of the choices. Possible choices are: %s.' % (value, self.name, optionsstring))
        return value

class UserArrayOption(UserOption):
    def __init__(self, name, description, value, **kwargs):
        super().__init__(name, description, kwargs.get('choices', []), yielding=kwargs.get('yielding', None))
        self.value = self.validate_value(value, user_input=False)

    def validate_value(self, value, user_input=True):
        # User input is for options defined on the command line (via -D
        # options). Users can put their input in as a comma separated
        # string, but for defining options in meson_options.txt the format
        # should match that of a combo
        if not user_input:
            if isinstance(value, str):
                if not value.startswith('['):
                    raise MesonException('Valuestring does not define an array: ' + value)
                newvalue = ast.literal_eval(value)
            else:
                newvalue = value
        else:
            assert isinstance(value, str)
            if value.startswith('['):
                newvalue = ast.literal_eval(value)
            else:
                newvalue = [v.strip() for v in value.split(',')]
                if len(set(newvalue)) != len(newvalue):
                    mlog.log(mlog.red('DEPRECATION:'), '''Duplicated values in an array type is deprecated.
This will become a hard error in the future.''')
        if not isinstance(newvalue, list):
            raise MesonException('"{0}" should be a string array, but it is not'.format(str(newvalue)))
        for i in newvalue:
            if not isinstance(i, str):
                raise MesonException('String array element "{0}" is not a string.'.format(str(newvalue)))
        if self.choices:
            bad = [x for x in newvalue if x not in self.choices]
            if bad:
                raise MesonException('Options "{}" are not in allowed choices: "{}"'.format(
                    ', '.join(bad), ', '.join(self.choices)))
        return newvalue

# This class contains all data that must persist over multiple
# invocations of Meson. It is roughly the same thing as
# cmakecache.

class CoreData:

    def __init__(self, options):
        self.lang_guids = {
            'default': '8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942',
            'c': '8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942',
            'cpp': '8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942',
            'test': '3AC096D0-A1C2-E12C-1390-A8335801FDAB',
            'directory': '2150E333-8FDC-42A3-9474-1A3956D46DE8',
        }
        self.test_guid = str(uuid.uuid4()).upper()
        self.regen_guid = str(uuid.uuid4()).upper()
        self.target_guids = {}
        self.version = version
        self.init_builtins(options)
        self.init_backend_options(self.builtins['backend'].value)
        self.user_options = {}
        self.compiler_options = {}
        self.base_options = {}
        # These external_*args, are set via env vars CFLAGS, LDFLAGS, etc
        # but only when not cross-compiling.
        self.external_preprocess_args = {} # CPPFLAGS only
        self.external_args = {} # CPPFLAGS + CFLAGS
        self.external_link_args = {} # CFLAGS + LDFLAGS (with MSVC: only LDFLAGS)
        self.cross_file = self.__load_cross_file(options.cross_file)
        self.wrap_mode = options.wrap_mode
        self.compilers = OrderedDict()
        self.cross_compilers = OrderedDict()
        self.deps = OrderedDict()
        # Only to print a warning if it changes between Meson invocations.
        self.pkgconf_envvar = os.environ.get('PKG_CONFIG_PATH', '')

    @staticmethod
    def __load_cross_file(filename):
        """Try to load the cross file.

        If the filename is None return None. If the filename is an absolute
        (after resolving variables and ~), return that absolute path. Next,
        check if the file is relative to the current source dir. If the path
        still isn't resolved do the following:
            Windows:
                - Error
            *:
                - $XDG_DATA_HOME/meson/cross (or ~/.local/share/meson/cross if
                  undefined)
                - $XDG_DATA_DIRS/meson/cross (or
                  /usr/local/share/meson/cross:/usr/share/meson/cross if undefined)
                - Error

        Non-Windows follows the Linux path and will honor XDG_* if set. This
        simplifies the implementation somewhat.
        """
        if filename is None:
            return None
        filename = os.path.expanduser(os.path.expandvars(filename))
        if os.path.isabs(filename):
            return filename
        path_to_try = os.path.abspath(filename)
        if os.path.exists(path_to_try):
            return path_to_try
        if sys.platform != 'win32':
            paths = [
                os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share')),
            ] + os.environ.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share').split(':')
            for path in paths:
                path_to_try = os.path.join(path, 'meson', 'cross', filename)
                if os.path.exists(path_to_try):
                    return path_to_try
            raise MesonException('Cannot find specified cross file: ' + filename)

        raise MesonException('Cannot find specified cross file: ' + filename)

    def sanitize_prefix(self, prefix):
        if not os.path.isabs(prefix):
            raise MesonException('prefix value {!r} must be an absolute path'
                                 ''.format(prefix))
        if prefix.endswith('/') or prefix.endswith('\\'):
            # On Windows we need to preserve the trailing slash if the
            # string is of type 'C:\' because 'C:' is not an absolute path.
            if len(prefix) == 3 and prefix[1] == ':':
                pass
            # If prefix is a single character, preserve it since it is
            # the root directory.
            elif len(prefix) == 1:
                pass
            else:
                prefix = prefix[:-1]
        return prefix

    def sanitize_dir_option_value(self, prefix, option, value):
        '''
        If the option is an installation directory option and the value is an
        absolute path, check that it resides within prefix and return the value
        as a path relative to the prefix.

        This way everyone can do f.ex, get_option('libdir') and be sure to get
        the library directory relative to prefix.
        '''
        if option.endswith('dir') and os.path.isabs(value) and \
           option not in builtin_dir_noprefix_options:
            # Value must be a subdir of the prefix
            # commonpath will always return a path in the native format, so we
            # must use pathlib.PurePath to do the same conversion before
            # comparing.
            if os.path.commonpath([value, prefix]) != str(PurePath(prefix)):
                m = 'The value of the {!r} option is {!r} which must be a ' \
                    'subdir of the prefix {!r}.\nNote that if you pass a ' \
                    'relative path, it is assumed to be a subdir of prefix.'
                raise MesonException(m.format(option, value, prefix))
            # Convert path to be relative to prefix
            skip = len(prefix) + 1
            value = value[skip:]
        return value

    def init_builtins(self, options):
        self.builtins = {}
        # Sanitize prefix
        options.prefix = self.sanitize_prefix(options.prefix)
        # Initialize other builtin options
        for key in get_builtin_options():
            if hasattr(options, key):
                value = getattr(options, key)
                value = self.sanitize_dir_option_value(options.prefix, key, value)
                setattr(options, key, value)
            else:
                value = get_builtin_option_default(key, prefix=options.prefix)
            args = [key] + builtin_options[key][1:-1] + [value]
            self.builtins[key] = builtin_options[key][0](*args)

    def init_backend_options(self, backend_name):
        self.backend_options = {}
        if backend_name == 'ninja':
            self.backend_options['backend_max_links'] = UserIntegerOption('backend_max_links',
                                                                          'Maximum number of linker processes to run or 0 for no limit',
                                                                          0, None, 0)

    def get_builtin_option(self, optname):
        if optname in self.builtins:
            return self.builtins[optname].value
        raise RuntimeError('Tried to get unknown builtin option %s.' % optname)

    def set_builtin_option(self, optname, value):
        if optname == 'prefix':
            value = self.sanitize_prefix(value)
        elif optname in self.builtins:
            prefix = self.builtins['prefix'].value
            value = self.sanitize_dir_option_value(prefix, optname, value)
        else:
            raise RuntimeError('Tried to set unknown builtin option %s.' % optname)
        self.builtins[optname].set_value(value)

    def validate_option_value(self, option_name, override_value):
        for opts in (self.builtins, self.base_options, self.compiler_options, self.user_options):
            if option_name in opts:
                opt = opts[option_name]
                return opt.validate_value(override_value)
        raise MesonException('Tried to validate unknown option %s.' % option_name)

def load(build_dir):
    filename = os.path.join(build_dir, 'meson-private', 'coredata.dat')
    load_fail_msg = 'Coredata file {!r} is corrupted. Try with a fresh build tree.'.format(filename)
    try:
        with open(filename, 'rb') as f:
            obj = pickle.load(f)
    except pickle.UnpicklingError:
        raise MesonException(load_fail_msg)
    if not isinstance(obj, CoreData):
        raise MesonException(load_fail_msg)
    if obj.version != version:
        raise MesonException('Build directory has been generated with Meson version %s, which is incompatible with current version %s.\nPlease delete this build directory AND create a new one.' %
                             (obj.version, version))
    return obj

def save(obj, build_dir):
    filename = os.path.join(build_dir, 'meson-private', 'coredata.dat')
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
        if builtin_options[optname][0] == UserComboOption:
            return builtin_options[optname][2]
        elif builtin_options[optname][0] == UserBooleanOption:
            return [True, False]
        else:
            return None
    else:
        raise RuntimeError('Tried to get the supported values for an unknown builtin option \'%s\'.' % optname)

def get_builtin_option_description(optname):
    if is_builtin_option(optname):
        return builtin_options[optname][1]
    else:
        raise RuntimeError('Tried to get the description for an unknown builtin option \'%s\'.' % optname)

def get_builtin_option_action(optname):
    default = builtin_options[optname][2]
    if default is True:
        return 'store_false'
    elif default is False:
        return 'store_true'
    return None

def get_builtin_option_default(optname, prefix='', noneIfSuppress=False):
    if is_builtin_option(optname):
        o = builtin_options[optname]
        if o[0] == UserComboOption:
            return o[3]
        if o[0] == UserIntegerOption:
            return o[4]
        if optname in builtin_dir_noprefix_options:
            if noneIfSuppress:
                # Return None if argparse defaulting should be suppressed for
                # this option (so we can determine the default later based on
                # prefix)
                return None
            elif prefix in builtin_dir_noprefix_options[optname]:
                return builtin_dir_noprefix_options[optname][prefix]
        return o[2]
    else:
        raise RuntimeError('Tried to get the default value for an unknown builtin option \'%s\'.' % optname)

def get_builtin_option_cmdline_name(name):
    if name == 'warning_level':
        return '--warnlevel'
    else:
        return '--' + name.replace('_', '-')

def add_builtin_argument(p, name):
    kwargs = {}
    c = get_builtin_option_choices(name)
    b = get_builtin_option_action(name)
    h = get_builtin_option_description(name)
    if not b:
        h = h.rstrip('.') + ' (default: %s).' % get_builtin_option_default(name)
    else:
        kwargs['action'] = b
    if c and not b:
        kwargs['choices'] = c
    default = get_builtin_option_default(name, noneIfSuppress=True)
    if default is not None:
        kwargs['default'] = default
    else:
        kwargs['default'] = argparse.SUPPRESS
    kwargs['dest'] = name

    cmdline_name = get_builtin_option_cmdline_name(name)
    p.add_argument(cmdline_name, help=h, **kwargs)

def register_builtin_arguments(parser):
    for n in builtin_options:
        add_builtin_argument(parser, n)
    parser.add_argument('-D', action='append', dest='projectoptions', default=[], metavar="option",
                        help='Set the value of an option, can be used several times to set multiple options.')

def filter_builtin_options(args, original_args):
    """Filter out any builtin arguments passed as -- instead of -D.

    Error if an argument is passed with -- and -D
    """
    for name in builtin_options:
        # Check if user passed --option. Cannot use hasattr(args, name) here
        # because they are all set with default value if user didn't pass it.
        cmdline_name = get_builtin_option_cmdline_name(name)
        has_dashdash = any([a.startswith(cmdline_name) for a in original_args])

        # Chekc if user passed -Doption=value
        has_dashd = any([a.startswith('{}='.format(name)) for a in args.projectoptions])

        # Passing both is ambigous, abort
        if has_dashdash and has_dashd:
            raise MesonException(
                'Got argument {0} as both -D{0} and {1}. Pick one.'.format(name, cmdline_name))

        # Pretend --option never existed
        if has_dashdash:
            args.projectoptions.append('{}={}'.format(name, getattr(args, name)))
        if hasattr(args, name):
            delattr(args, name)


builtin_options = {
    'buildtype':  [UserComboOption, 'Build type to use.', ['plain', 'debug', 'debugoptimized', 'release', 'minsize'], 'debug'],
    'strip':      [UserBooleanOption, 'Strip targets on install.', False],
    'unity':      [UserComboOption, 'Unity build.', ['on', 'off', 'subprojects'], 'off'],
    'prefix':     [UserStringOption, 'Installation prefix.', default_prefix()],
    'libdir':     [UserStringOption, 'Library directory.', default_libdir()],
    'libexecdir': [UserStringOption, 'Library executable directory.', default_libexecdir()],
    'bindir':     [UserStringOption, 'Executable directory.', 'bin'],
    'sbindir':    [UserStringOption, 'System executable directory.', 'sbin'],
    'includedir': [UserStringOption, 'Header file directory.', 'include'],
    'datadir':    [UserStringOption, 'Data file directory.', 'share'],
    'mandir':     [UserStringOption, 'Manual page directory.', 'share/man'],
    'infodir':    [UserStringOption, 'Info page directory.', 'share/info'],
    'localedir':  [UserStringOption, 'Locale data directory.', 'share/locale'],
    'sysconfdir':      [UserStringOption, 'Sysconf data directory.', 'etc'],
    'localstatedir':   [UserStringOption, 'Localstate data directory.', 'var'],
    'sharedstatedir':  [UserStringOption, 'Architecture-independent data directory.', 'com'],
    'werror':          [UserBooleanOption, 'Treat warnings as errors.', False],
    'warning_level':   [UserComboOption, 'Compiler warning level to use.', ['1', '2', '3'], '1'],
    'layout':          [UserComboOption, 'Build directory layout.', ['mirror', 'flat'], 'mirror'],
    'default_library': [UserComboOption, 'Default library type.', ['shared', 'static', 'both'], 'shared'],
    'backend':         [UserComboOption, 'Backend to use.', backendlist, 'ninja'],
    'stdsplit':        [UserBooleanOption, 'Split stdout and stderr in test logs.', True],
    'errorlogs':       [UserBooleanOption, "Whether to print the logs from failing tests.", True],
    'install_umask':   [UserUmaskOption, 'Default umask to apply on permissions of installed files.', '022'],
}

# Special prefix-dependent defaults for installation directories that reside in
# a path outside of the prefix in FHS and common usage.
builtin_dir_noprefix_options = {
    'sysconfdir':     {'/usr': '/etc'},
    'localstatedir':  {'/usr': '/var',     '/usr/local': '/var/local'},
    'sharedstatedir': {'/usr': '/var/lib', '/usr/local': '/var/local/lib'},
}

forbidden_target_names = {'clean': None,
                          'clean-ctlist': None,
                          'clean-gcno': None,
                          'clean-gcda': None,
                          'coverage': None,
                          'coverage-text': None,
                          'coverage-xml': None,
                          'coverage-html': None,
                          'phony': None,
                          'PHONY': None,
                          'all': None,
                          'test': None,
                          'benchmark': None,
                          'install': None,
                          'uninstall': None,
                          'build.ninja': None,
                          'scan-build': None,
                          'reconfigure': None,
                          'dist': None,
                          'distcheck': None,
                          }
