# Copyright 2012-2019 The Meson development team

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
import pickle, os, uuid, shlex
import sys
from itertools import chain
from pathlib import PurePath
from collections import OrderedDict
from .mesonlib import (
    MesonException, default_libdir, default_libexecdir, default_prefix
)
from .wrap import WrapMode
import ast
import argparse
import configparser

version = '0.49.999'
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

    def printable_value(self):
        return self.value

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
        self.choices = ['preserve', '0000-0777']

    def printable_value(self):
        if self.value == 'preserve':
            return self.value
        return format(self.value, '04o')

    def validate_value(self, value):
        if value is None or value == 'preserve':
            return 'preserve'
        return super().validate_value(value)

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
    def __init__(self, name, description, value, shlex_split=False, user_input=False, allow_dups=False, **kwargs):
        super().__init__(name, description, kwargs.get('choices', []), yielding=kwargs.get('yielding', None))
        self.shlex_split = shlex_split
        self.allow_dups = allow_dups
        self.value = self.validate_value(value, user_input=user_input)

    def validate_value(self, value, user_input=True):
        # User input is for options defined on the command line (via -D
        # options). Users can put their input in as a comma separated
        # string, but for defining options in meson_options.txt the format
        # should match that of a combo
        if not user_input and isinstance(value, str) and not value.startswith('['):
            raise MesonException('Value does not define an array: ' + value)

        if isinstance(value, str):
            if value.startswith('['):
                newvalue = ast.literal_eval(value)
            elif value == '':
                newvalue = []
            else:
                if self.shlex_split:
                    newvalue = shlex.split(value)
                else:
                    newvalue = [v.strip() for v in value.split(',')]
        elif isinstance(value, list):
            newvalue = value
        else:
            raise MesonException('"{0}" should be a string array, but it is not'.format(str(newvalue)))

        if not self.allow_dups and len(set(newvalue)) != len(newvalue):
            msg = 'Duplicated values in array option "%s" is deprecated. ' \
                  'This will become a hard error in the future.' % (self.name)
            mlog.deprecation(msg)
        for i in newvalue:
            if not isinstance(i, str):
                raise MesonException('String array element "{0}" is not a string.'.format(str(newvalue)))
        if self.choices:
            bad = [x for x in newvalue if x not in self.choices]
            if bad:
                raise MesonException('Options "{}" are not in allowed choices: "{}"'.format(
                    ', '.join(bad), ', '.join(self.choices)))
        return newvalue


class UserFeatureOption(UserComboOption):
    static_choices = ['enabled', 'disabled', 'auto']

    def __init__(self, name, description, value, yielding=None):
        super().__init__(name, description, self.static_choices, value, yielding)

    def is_enabled(self):
        return self.value == 'enabled'

    def is_disabled(self):
        return self.value == 'disabled'

    def is_auto(self):
        return self.value == 'auto'


def load_configs(filenames):
    """Load native files."""
    def gen():
        for f in filenames:
            f = os.path.expanduser(os.path.expandvars(f))
            if os.path.exists(f):
                yield f
                continue
            elif sys.platform != 'win32':
                f = os.path.basename(f)
                paths = [
                    os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share')),
                ] + os.environ.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share').split(':')
                for path in paths:
                    path_to_try = os.path.join(path, 'meson', 'native', f)
                    if os.path.isfile(path_to_try):
                        yield path_to_try
                        break
                else:
                    raise MesonException('Cannot find specified native file: ' + f)
                continue

            raise MesonException('Cannot find specified native file: ' + f)

    config = configparser.ConfigParser()
    config.read(gen())
    return config


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
        self.install_guid = str(uuid.uuid4()).upper()
        self.target_guids = {}
        self.version = version
        self.init_builtins()
        self.backend_options = {}
        self.user_options = {}
        self.compiler_options = {}
        self.base_options = {}
        self.external_preprocess_args = {} # CPPFLAGS only
        self.cross_file = self.__load_cross_file(options.cross_file)
        self.compilers = OrderedDict()
        self.cross_compilers = OrderedDict()
        self.deps = OrderedDict()
        # Only to print a warning if it changes between Meson invocations.
        self.pkgconf_envvar = os.environ.get('PKG_CONFIG_PATH', '')
        self.config_files = self.__load_config_files(options.native_file)
        self.libdir_cross_fixup()

    @staticmethod
    def __load_config_files(filenames):
        if not filenames:
            return []
        filenames = [os.path.abspath(os.path.expanduser(os.path.expanduser(f)))
                     for f in filenames]
        return filenames

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
        if os.path.isfile(path_to_try):
            return path_to_try
        if sys.platform != 'win32':
            paths = [
                os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share')),
            ] + os.environ.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share').split(':')
            for path in paths:
                path_to_try = os.path.join(path, 'meson', 'cross', filename)
                if os.path.isfile(path_to_try):
                    return path_to_try
            raise MesonException('Cannot find specified cross file: ' + filename)

        raise MesonException('Cannot find specified cross file: ' + filename)

    def libdir_cross_fixup(self):
        # By default set libdir to "lib" when cross compiling since
        # getting the "system default" is always wrong on multiarch
        # platforms as it gets a value like lib/x86_64-linux-gnu.
        if self.cross_file is not None:
            self.builtins['libdir'].value = 'lib'

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

    def init_builtins(self):
        # Create builtin options with default values
        self.builtins = {}
        prefix = get_builtin_option_default('prefix')
        for key in get_builtin_options():
            value = get_builtin_option_default(key, prefix)
            args = [key] + builtin_options[key][1:-1] + [value]
            self.builtins[key] = builtin_options[key][0](*args)

    def init_backend_options(self, backend_name):
        if backend_name == 'ninja':
            self.backend_options['backend_max_links'] = \
                UserIntegerOption(
                    'backend_max_links',
                    'Maximum number of linker processes to run or 0 for no '
                    'limit',
                    0, None, 0)
        elif backend_name.startswith('vs'):
            self.backend_options['backend_startup_project'] = \
                UserStringOption(
                    'backend_startup_project',
                    'Default project to execute in Visual Studio',
                    '')

    def get_builtin_option(self, optname):
        if optname in self.builtins:
            v = self.builtins[optname]
            if optname == 'wrap_mode':
                return WrapMode.from_string(v.value)
            return v.value
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

        # Make sure that buildtype matches other settings.
        if optname == 'buildtype':
            self.set_others_from_buildtype(value)
        else:
            self.set_buildtype_from_others()

    def set_others_from_buildtype(self, value):
        if value == 'plain':
            opt = '0'
            debug = False
        elif value == 'debug':
            opt = '0'
            debug = True
        elif value == 'debugoptimized':
            opt = '2'
            debug = True
        elif value == 'release':
            opt = '3'
            debug = False
        elif value == 'minsize':
            opt = 's'
            debug = True
        else:
            assert(value == 'custom')
            return
        self.builtins['optimization'].set_value(opt)
        self.builtins['debug'].set_value(debug)

    def set_buildtype_from_others(self):
        opt = self.builtins['optimization'].value
        debug = self.builtins['debug'].value
        if opt == '0' and not debug:
            mode = 'plain'
        elif opt == '0' and debug:
            mode = 'debug'
        elif opt == '2' and debug:
            mode = 'debugoptimized'
        elif opt == '3' and not debug:
            mode = 'release'
        elif opt == 's' and debug:
            mode = 'minsize'
        else:
            mode = 'custom'
        self.builtins['buildtype'].set_value(mode)

    def _get_all_nonbuiltin_options(self):
        yield self.backend_options
        yield self.user_options
        yield self.compiler_options
        yield self.base_options

    def get_all_options(self):
        return chain(
            iter([self.builtins]),
            self._get_all_nonbuiltin_options())

    def validate_option_value(self, option_name, override_value):
        for opts in self.get_all_options():
            if option_name in opts:
                opt = opts[option_name]
                return opt.validate_value(override_value)
        raise MesonException('Tried to validate unknown option %s.' % option_name)

    def get_external_args(self, lang):
        return self.compiler_options[lang + '_args'].value

    def get_external_link_args(self, lang):
        return self.compiler_options[lang + '_link_args'].value

    def get_external_preprocess_args(self, lang):
        return self.external_preprocess_args[lang]

    def merge_user_options(self, options):
        for (name, value) in options.items():
            if name not in self.user_options:
                self.user_options[name] = value
            else:
                oldval = self.user_options[name]
                if type(oldval) != type(value):
                    self.user_options[name] = value

    def set_options(self, options, subproject=''):
        # Set prefix first because it's needed to sanitize other options
        prefix = self.builtins['prefix'].value
        if 'prefix' in options:
            prefix = self.sanitize_prefix(options['prefix'])
            self.builtins['prefix'].set_value(prefix)
            for key in builtin_dir_noprefix_options:
                if key not in options:
                    self.builtins[key].set_value(get_builtin_option_default(key, prefix))

        unknown_options = []
        for k, v in options.items():
            if k == 'prefix':
                pass
            elif k in self.builtins:
                self.set_builtin_option(k, v)
            else:
                for opts in self._get_all_nonbuiltin_options():
                    if k in opts:
                        tgt = opts[k]
                        tgt.set_value(v)
                        break
                else:
                    unknown_options.append(k)

        if unknown_options:
            unknown_options = ', '.join(sorted(unknown_options))
            sub = 'In subproject {}: '.format(subproject) if subproject else ''
            mlog.warning('{}Unknown options: "{}"'.format(sub, unknown_options))

    def set_default_options(self, default_options, subproject, cmd_line_options):
        # Set default options as if they were passed to the command line.
        # Subprojects can only define default for user options.
        from . import optinterpreter
        for k, v in default_options.items():
            if subproject:
                if optinterpreter.is_invalid_name(k):
                    continue
                k = subproject + ':' + k
            cmd_line_options.setdefault(k, v)

        # Create a subset of cmd_line_options, keeping only options for this
        # subproject. Also take builtin options if it's the main project.
        # Language and backend specific options will be set later when adding
        # languages and setting the backend (builtin options must be set first
        # to know which backend we'll use).
        options = {}
        for k, v in cmd_line_options.items():
            if subproject:
                if not k.startswith(subproject + ':'):
                    continue
            elif k not in get_builtin_options():
                if ':' in k:
                    continue
                if optinterpreter.is_invalid_name(k):
                    continue
            options[k] = v

        self.set_options(options, subproject)

    def process_new_compilers(self, lang: str, comp, cross_comp, cmd_line_options):
        from . import compilers
        self.compilers[lang] = comp
        # Native compiler always exist so always add its options.
        new_options = comp.get_options()
        if cross_comp is not None:
            self.cross_compilers[lang] = cross_comp
            new_options.update(cross_comp.get_options())

        optprefix = lang + '_'
        for k, o in new_options.items():
            if not k.startswith(optprefix):
                raise MesonException('Internal error, %s has incorrect prefix.' % k)
            if k in cmd_line_options:
                o.set_value(cmd_line_options[k])
            self.compiler_options.setdefault(k, o)

        # Unlike compiler and linker flags, preprocessor flags are not in
        # compiler_options because they are not visible to user.
        preproc_flags = comp.get_preproc_flags()
        preproc_flags = shlex.split(preproc_flags)
        self.external_preprocess_args.setdefault(lang, preproc_flags)

        enabled_opts = []
        for optname in comp.base_options:
            if optname in self.base_options:
                continue
            oobj = compilers.base_options[optname]
            if optname in cmd_line_options:
                oobj.set_value(cmd_line_options[optname])
                enabled_opts.append(optname)
            self.base_options[optname] = oobj
        self.emit_base_options_warnings(enabled_opts)

    def emit_base_options_warnings(self, enabled_opts: list):
        if 'b_bitcode' in enabled_opts:
            mlog.warning('Base option \'b_bitcode\' is enabled, which is incompatible with many linker options. Incompatible options such as such as \'b_asneeded\' have been disabled.')
            mlog.warning('Please see https://mesonbuild.com/Builtin-options.html#Notes_about_Apple_Bitcode_support for more details.')

class CmdLineFileParser(configparser.ConfigParser):
    def __init__(self):
        # We don't want ':' as key delimiter, otherwise it would break when
        # storing subproject options like "subproject:option=value"
        super().__init__(delimiters=['='])

def get_cmd_line_file(build_dir):
    return os.path.join(build_dir, 'meson-private', 'cmd_line.txt')

def read_cmd_line_file(build_dir, options):
    filename = get_cmd_line_file(build_dir)
    config = CmdLineFileParser()
    config.read(filename)

    # Do a copy because config is not really a dict. options.cmd_line_options
    # overrides values from the file.
    d = dict(config['options'])
    d.update(options.cmd_line_options)
    options.cmd_line_options = d

    properties = config['properties']
    if options.cross_file is None:
        options.cross_file = properties.get('cross_file', None)
    if not options.native_file:
        # This will be a string in the form: "['first', 'second', ...]", use
        # literal_eval to get it into the list of strings.
        options.native_file = ast.literal_eval(properties.get('native_file', '[]'))

def write_cmd_line_file(build_dir, options):
    filename = get_cmd_line_file(build_dir)
    config = CmdLineFileParser()

    properties = {}
    if options.cross_file is not None:
        properties['cross_file'] = options.cross_file
    if options.native_file:
        properties['native_file'] = options.native_file

    config['options'] = options.cmd_line_options
    config['properties'] = properties
    with open(filename, 'w') as f:
        config.write(f)

def update_cmd_line_file(build_dir, options):
    filename = get_cmd_line_file(build_dir)
    config = CmdLineFileParser()
    config.read(filename)
    config['options'].update(options.cmd_line_options)
    with open(filename, 'w') as f:
        config.write(f)

def major_versions_differ(v1, v2):
    return v1.split('.')[0:2] != v2.split('.')[0:2]

def load(build_dir):
    filename = os.path.join(build_dir, 'meson-private', 'coredata.dat')
    load_fail_msg = 'Coredata file {!r} is corrupted. Try with a fresh build tree.'.format(filename)
    try:
        with open(filename, 'rb') as f:
            obj = pickle.load(f)
    except (pickle.UnpicklingError, EOFError):
        raise MesonException(load_fail_msg)
    except AttributeError:
        raise MesonException(
            "Coredata file {!r} references functions or classes that don't "
            "exist. This probably means that it was generated with an old "
            "version of meson.".format(filename))
    if not isinstance(obj, CoreData):
        raise MesonException(load_fail_msg)
    if major_versions_differ(obj.version, version):
        raise MesonException('Build directory has been generated with Meson version %s, '
                             'which is incompatible with current version %s.\n' %
                             (obj.version, version))
    return obj

def save(obj, build_dir):
    filename = os.path.join(build_dir, 'meson-private', 'coredata.dat')
    prev_filename = filename + '.prev'
    tempfilename = filename + '~'
    if major_versions_differ(obj.version, version):
        raise MesonException('Fatal version mismatch corruption.')
    if os.path.exists(filename):
        import shutil
        shutil.copyfile(filename, prev_filename)
    with open(tempfilename, 'wb') as f:
        pickle.dump(obj, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tempfilename, filename)
    return filename

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
        elif builtin_options[optname][0] == UserFeatureOption:
            return UserFeatureOption.static_choices
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

def get_builtin_option_default(optname, prefix=''):
    if is_builtin_option(optname):
        o = builtin_options[optname]
        if o[0] == UserComboOption:
            return o[3]
        if o[0] == UserIntegerOption:
            return o[4]
        try:
            return builtin_dir_noprefix_options[optname][prefix]
        except KeyError:
            pass
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
    kwargs['default'] = argparse.SUPPRESS
    kwargs['dest'] = name

    cmdline_name = get_builtin_option_cmdline_name(name)
    p.add_argument(cmdline_name, help=h, **kwargs)

def register_builtin_arguments(parser):
    for n in builtin_options:
        add_builtin_argument(parser, n)
    parser.add_argument('-D', action='append', dest='projectoptions', default=[], metavar="option",
                        help='Set the value of an option, can be used several times to set multiple options.')

def create_options_dict(options):
    result = {}
    for o in options:
        try:
            (key, value) = o.split('=', 1)
        except ValueError:
            raise MesonException('Option {!r} must have a value separated by equals sign.'.format(o))
        result[key] = value
    return result

def parse_cmd_line_options(args):
    args.cmd_line_options = create_options_dict(args.projectoptions)

    # Merge builtin options set with --option into the dict.
    for name in builtin_options:
        value = getattr(args, name, None)
        if value is not None:
            if name in args.cmd_line_options:
                cmdline_name = get_builtin_option_cmdline_name(name)
                raise MesonException(
                    'Got argument {0} as both -D{0} and {1}. Pick one.'.format(name, cmdline_name))
            args.cmd_line_options[name] = value
            delattr(args, name)

builtin_options = {
    'buildtype':  [UserComboOption, 'Build type to use', ['plain', 'debug', 'debugoptimized', 'release', 'minsize', 'custom'], 'debug'],
    'strip':      [UserBooleanOption, 'Strip targets on install', False],
    'unity':      [UserComboOption, 'Unity build', ['on', 'off', 'subprojects'], 'off'],
    'prefix':     [UserStringOption, 'Installation prefix', default_prefix()],
    'libdir':     [UserStringOption, 'Library directory', default_libdir()],
    'libexecdir': [UserStringOption, 'Library executable directory', default_libexecdir()],
    'bindir':     [UserStringOption, 'Executable directory', 'bin'],
    'sbindir':    [UserStringOption, 'System executable directory', 'sbin'],
    'includedir': [UserStringOption, 'Header file directory', 'include'],
    'datadir':    [UserStringOption, 'Data file directory', 'share'],
    'mandir':     [UserStringOption, 'Manual page directory', 'share/man'],
    'infodir':    [UserStringOption, 'Info page directory', 'share/info'],
    'localedir':  [UserStringOption, 'Locale data directory', 'share/locale'],
    'sysconfdir':      [UserStringOption, 'Sysconf data directory', 'etc'],
    'localstatedir':   [UserStringOption, 'Localstate data directory', 'var'],
    'sharedstatedir':  [UserStringOption, 'Architecture-independent data directory', 'com'],
    'werror':          [UserBooleanOption, 'Treat warnings as errors', False],
    'warning_level':   [UserComboOption, 'Compiler warning level to use', ['1', '2', '3'], '1'],
    'layout':          [UserComboOption, 'Build directory layout', ['mirror', 'flat'], 'mirror'],
    'default_library': [UserComboOption, 'Default library type', ['shared', 'static', 'both'], 'shared'],
    'backend':         [UserComboOption, 'Backend to use', backendlist, 'ninja'],
    'stdsplit':        [UserBooleanOption, 'Split stdout and stderr in test logs', True],
    'errorlogs':       [UserBooleanOption, "Whether to print the logs from failing tests", True],
    'install_umask':   [UserUmaskOption, 'Default umask to apply on permissions of installed files', '022'],
    'auto_features':   [UserFeatureOption, "Override value of all 'auto' features", 'auto'],
    'optimization':    [UserComboOption, 'Optimization level', ['0', 'g', '1', '2', '3', 's'], '0'],
    'debug':           [UserBooleanOption, 'Debug', True],
    'wrap_mode':       [UserComboOption, 'Wrap mode', ['default',
                                                       'nofallback',
                                                       'nodownload',
                                                       'forcefallback'], 'default'],
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
