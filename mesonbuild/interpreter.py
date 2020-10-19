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

from . import mparser
from . import environment
from . import coredata
from . import dependencies
from . import mlog
from . import build
from . import optinterpreter
from . import compilers
from .wrap import wrap, WrapMode
from . import mesonlib
from .mesonlib import FileMode, MachineChoice, Popen_safe, listify, extract_as_list, has_path_sep, unholder
from .dependencies import ExternalProgram
from .dependencies import InternalDependency, Dependency, NotFoundDependency, DependencyException
from .depfile import DepFile
from .interpreterbase import InterpreterBase
from .interpreterbase import check_stringlist, flatten, noPosargs, noKwargs, stringArgs, permittedKwargs, noArgsFlattening
from .interpreterbase import InterpreterException, InvalidArguments, InvalidCode, SubdirDoneRequest
from .interpreterbase import InterpreterObject, MutableInterpreterObject, Disabler, disablerIfNotFound
from .interpreterbase import FeatureNew, FeatureDeprecated, FeatureNewKwargs, FeatureDeprecatedKwargs
from .interpreterbase import ObjectHolder, MesonVersionString
from .interpreterbase import TYPE_var, TYPE_nkwargs
from .modules import ModuleReturnValue, ExtensionModule
from .cmake import CMakeInterpreter
from .backend.backends import TestProtocol, Backend

from ._pathlib import Path, PurePath
import os
import shutil
import uuid
import re
import shlex
import stat
import subprocess
import collections
import functools
import typing as T

import importlib

permitted_method_kwargs = {
    'partial_dependency': {'compile_args', 'link_args', 'links', 'includes',
                           'sources'},
}

def stringifyUserArguments(args):
    if isinstance(args, list):
        return '[%s]' % ', '.join([stringifyUserArguments(x) for x in args])
    elif isinstance(args, dict):
        return '{%s}' % ', '.join(['%s : %s' % (stringifyUserArguments(k), stringifyUserArguments(v)) for k, v in args.items()])
    elif isinstance(args, int):
        return str(args)
    elif isinstance(args, str):
        return "'%s'" % args
    raise InvalidArguments('Function accepts only strings, integers, lists and lists thereof.')


class OverrideProgram(dependencies.ExternalProgram):
    pass


class FeatureOptionHolder(InterpreterObject, ObjectHolder):
    def __init__(self, env, name, option):
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, option)
        if option.is_auto():
            self.held_object = env.coredata.builtins['auto_features']
        self.name = name
        self.methods.update({'enabled': self.enabled_method,
                             'disabled': self.disabled_method,
                             'auto': self.auto_method,
                             })

    @noPosargs
    @permittedKwargs({})
    def enabled_method(self, args, kwargs):
        return self.held_object.is_enabled()

    @noPosargs
    @permittedKwargs({})
    def disabled_method(self, args, kwargs):
        return self.held_object.is_disabled()

    @noPosargs
    @permittedKwargs({})
    def auto_method(self, args, kwargs):
        return self.held_object.is_auto()

def extract_required_kwarg(kwargs, subproject, feature_check=None, default=True):
    val = kwargs.get('required', default)
    disabled = False
    required = False
    feature = None
    if isinstance(val, FeatureOptionHolder):
        if not feature_check:
            feature_check = FeatureNew('User option "feature"', '0.47.0')
        feature_check.use(subproject)
        option = val.held_object
        feature = val.name
        if option.is_disabled():
            disabled = True
        elif option.is_enabled():
            required = True
    elif isinstance(val, bool):
        required = val
    else:
        raise InterpreterException('required keyword argument must be boolean or a feature option')

    # Keep boolean value in kwargs to simplify other places where this kwarg is
    # checked.
    kwargs['required'] = required

    return disabled, required, feature

def extract_search_dirs(kwargs):
    search_dirs = mesonlib.stringlistify(kwargs.get('dirs', []))
    search_dirs = [Path(d).expanduser() for d in search_dirs]
    for d in search_dirs:
        if mesonlib.is_windows() and d.root.startswith('\\'):
            # a Unix-path starting with `/` that is not absolute on Windows.
            # discard without failing for end-user ease of cross-platform directory arrays
            continue
        if not d.is_absolute():
            raise InvalidCode('Search directory {} is not an absolute path.'.format(d))
    return list(map(str, search_dirs))

class TryRunResultHolder(InterpreterObject):
    def __init__(self, res):
        super().__init__()
        self.res = res
        self.methods.update({'returncode': self.returncode_method,
                             'compiled': self.compiled_method,
                             'stdout': self.stdout_method,
                             'stderr': self.stderr_method,
                             })

    @noPosargs
    @permittedKwargs({})
    def returncode_method(self, args, kwargs):
        return self.res.returncode

    @noPosargs
    @permittedKwargs({})
    def compiled_method(self, args, kwargs):
        return self.res.compiled

    @noPosargs
    @permittedKwargs({})
    def stdout_method(self, args, kwargs):
        return self.res.stdout

    @noPosargs
    @permittedKwargs({})
    def stderr_method(self, args, kwargs):
        return self.res.stderr

class RunProcess(InterpreterObject):

    def __init__(self, cmd, args, env, source_dir, build_dir, subdir, mesonintrospect, in_builddir=False, check=False, capture=True):
        super().__init__()
        if not isinstance(cmd, ExternalProgram):
            raise AssertionError('BUG: RunProcess must be passed an ExternalProgram')
        self.capture = capture
        pc, self.stdout, self.stderr = self.run_command(cmd, args, env, source_dir, build_dir, subdir, mesonintrospect, in_builddir, check)
        self.returncode = pc.returncode
        self.methods.update({'returncode': self.returncode_method,
                             'stdout': self.stdout_method,
                             'stderr': self.stderr_method,
                             })

    def run_command(self, cmd, args, env, source_dir, build_dir, subdir, mesonintrospect, in_builddir, check=False):
        command_array = cmd.get_command() + args
        menv = {'MESON_SOURCE_ROOT': source_dir,
                'MESON_BUILD_ROOT': build_dir,
                'MESON_SUBDIR': subdir,
                'MESONINTROSPECT': ' '.join([shlex.quote(x) for x in mesonintrospect]),
                }
        if in_builddir:
            cwd = os.path.join(build_dir, subdir)
        else:
            cwd = os.path.join(source_dir, subdir)
        child_env = os.environ.copy()
        child_env.update(menv)
        child_env = env.get_env(child_env)
        stdout = subprocess.PIPE if self.capture else subprocess.DEVNULL
        mlog.debug('Running command:', ' '.join(command_array))
        try:
            p, o, e = Popen_safe(command_array, stdout=stdout, env=child_env, cwd=cwd)
            if self.capture:
                mlog.debug('--- stdout ---')
                mlog.debug(o)
            else:
                o = ''
                mlog.debug('--- stdout disabled ---')
            mlog.debug('--- stderr ---')
            mlog.debug(e)
            mlog.debug('')

            if check and p.returncode != 0:
                raise InterpreterException('Command "{}" failed with status {}.'.format(' '.join(command_array), p.returncode))

            return p, o, e
        except FileNotFoundError:
            raise InterpreterException('Could not execute command "%s".' % ' '.join(command_array))

    @noPosargs
    @permittedKwargs({})
    def returncode_method(self, args, kwargs):
        return self.returncode

    @noPosargs
    @permittedKwargs({})
    def stdout_method(self, args, kwargs):
        return self.stdout

    @noPosargs
    @permittedKwargs({})
    def stderr_method(self, args, kwargs):
        return self.stderr

class ConfigureFileHolder(InterpreterObject, ObjectHolder):

    def __init__(self, subdir, sourcename, targetname, configuration_data):
        InterpreterObject.__init__(self)
        obj = build.ConfigureFile(subdir, sourcename, targetname, configuration_data)
        ObjectHolder.__init__(self, obj)


class EnvironmentVariablesHolder(MutableInterpreterObject, ObjectHolder):
    def __init__(self, initial_values=None):
        MutableInterpreterObject.__init__(self)
        ObjectHolder.__init__(self, build.EnvironmentVariables())
        self.methods.update({'set': self.set_method,
                             'append': self.append_method,
                             'prepend': self.prepend_method,
                             })
        if isinstance(initial_values, dict):
            for k, v in initial_values.items():
                self.set_method([k, v], {})
        elif isinstance(initial_values, list):
            for e in initial_values:
                if '=' not in e:
                    raise InterpreterException('Env var definition must be of type key=val.')
                (k, val) = e.split('=', 1)
                k = k.strip()
                val = val.strip()
                if ' ' in k:
                    raise InterpreterException('Env var key must not have spaces in it.')
                self.set_method([k, val], {})
        elif initial_values:
            raise AssertionError('Unsupported EnvironmentVariablesHolder initial_values')

    def __repr__(self):
        repr_str = "<{0}: {1}>"
        return repr_str.format(self.__class__.__name__, self.held_object.envvars)

    def add_var(self, method, args, kwargs):
        if not isinstance(kwargs.get("separator", ""), str):
            raise InterpreterException("EnvironmentVariablesHolder methods 'separator'"
                                       " argument needs to be a string.")
        if len(args) < 2:
            raise InterpreterException("EnvironmentVariablesHolder methods require at least"
                                       "2 arguments, first is the name of the variable and"
                                       " following one are values")
        # Warn when someone tries to use append() or prepend() on an env var
        # which already has an operation set on it. People seem to think that
        # multiple append/prepend operations stack, but they don't.
        if method != self.held_object.set and self.held_object.has_name(args[0]):
            mlog.warning('Overriding previous value of environment variable {!r} with a new one'
                         .format(args[0]), location=self.current_node)
        self.held_object.add_var(method, args[0], args[1:], kwargs)

    @stringArgs
    @permittedKwargs({'separator'})
    def set_method(self, args, kwargs):
        self.add_var(self.held_object.set, args, kwargs)

    @stringArgs
    @permittedKwargs({'separator'})
    def append_method(self, args, kwargs):
        self.add_var(self.held_object.append, args, kwargs)

    @stringArgs
    @permittedKwargs({'separator'})
    def prepend_method(self, args, kwargs):
        self.add_var(self.held_object.prepend, args, kwargs)


class ConfigurationDataHolder(MutableInterpreterObject, ObjectHolder):
    def __init__(self, pv, initial_values=None):
        MutableInterpreterObject.__init__(self)
        self.used = False # These objects become immutable after use in configure_file.
        ObjectHolder.__init__(self, build.ConfigurationData(), pv)
        self.methods.update({'set': self.set_method,
                             'set10': self.set10_method,
                             'set_quoted': self.set_quoted_method,
                             'has': self.has_method,
                             'get': self.get_method,
                             'get_unquoted': self.get_unquoted_method,
                             'merge_from': self.merge_from_method,
                             })
        if isinstance(initial_values, dict):
            for k, v in initial_values.items():
                self.set_method([k, v], {})
        elif initial_values:
            raise AssertionError('Unsupported ConfigurationDataHolder initial_values')

    def is_used(self):
        return self.used

    def mark_used(self):
        self.used = True

    def validate_args(self, args, kwargs):
        if len(args) == 1 and isinstance(args[0], list) and len(args[0]) == 2:
            mlog.deprecation('Passing a list as the single argument to '
                             'configuration_data.set is deprecated. This will '
                             'become a hard error in the future.',
                             location=self.current_node)
            args = args[0]

        if len(args) != 2:
            raise InterpreterException("Configuration set requires 2 arguments.")
        if self.used:
            raise InterpreterException("Can not set values on configuration object that has been used.")
        name, val = args
        if not isinstance(val, (int, str)):
            msg = 'Setting a configuration data value to {!r} is invalid, ' \
                  'and will fail at configure_file(). If you are using it ' \
                  'just to store some values, please use a dict instead.'
            mlog.deprecation(msg.format(val), location=self.current_node)
        desc = kwargs.get('description', None)
        if not isinstance(name, str):
            raise InterpreterException("First argument to set must be a string.")
        if desc is not None and not isinstance(desc, str):
            raise InterpreterException('Description must be a string.')

        return name, val, desc

    @noArgsFlattening
    def set_method(self, args, kwargs):
        (name, val, desc) = self.validate_args(args, kwargs)
        self.held_object.values[name] = (val, desc)

    def set_quoted_method(self, args, kwargs):
        (name, val, desc) = self.validate_args(args, kwargs)
        if not isinstance(val, str):
            raise InterpreterException("Second argument to set_quoted must be a string.")
        escaped_val = '\\"'.join(val.split('"'))
        self.held_object.values[name] = ('"' + escaped_val + '"', desc)

    def set10_method(self, args, kwargs):
        (name, val, desc) = self.validate_args(args, kwargs)
        if val:
            self.held_object.values[name] = (1, desc)
        else:
            self.held_object.values[name] = (0, desc)

    def has_method(self, args, kwargs):
        return args[0] in self.held_object.values

    @FeatureNew('configuration_data.get()', '0.38.0')
    @noArgsFlattening
    def get_method(self, args, kwargs):
        if len(args) < 1 or len(args) > 2:
            raise InterpreterException('Get method takes one or two arguments.')
        name = args[0]
        if name in self.held_object:
            return self.held_object.get(name)[0]
        if len(args) > 1:
            return args[1]
        raise InterpreterException('Entry %s not in configuration data.' % name)

    @FeatureNew('configuration_data.get_unquoted()', '0.44.0')
    def get_unquoted_method(self, args, kwargs):
        if len(args) < 1 or len(args) > 2:
            raise InterpreterException('Get method takes one or two arguments.')
        name = args[0]
        if name in self.held_object:
            val = self.held_object.get(name)[0]
        elif len(args) > 1:
            val = args[1]
        else:
            raise InterpreterException('Entry %s not in configuration data.' % name)
        if val[0] == '"' and val[-1] == '"':
            return val[1:-1]
        return val

    def get(self, name):
        return self.held_object.values[name] # (val, desc)

    def keys(self):
        return self.held_object.values.keys()

    def merge_from_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Merge_from takes one positional argument.')
        from_object = args[0]
        if not isinstance(from_object, ConfigurationDataHolder):
            raise InterpreterException('Merge_from argument must be a configuration data object.')
        from_object = from_object.held_object
        for k, v in from_object.values.items():
            self.held_object.values[k] = v

# Interpreter objects can not be pickled so we must have
# these wrappers.

class DependencyHolder(InterpreterObject, ObjectHolder):
    def __init__(self, dep, pv):
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, dep, pv)
        self.methods.update({'found': self.found_method,
                             'type_name': self.type_name_method,
                             'version': self.version_method,
                             'name': self.name_method,
                             'get_pkgconfig_variable': self.pkgconfig_method,
                             'get_configtool_variable': self.configtool_method,
                             'get_variable': self.variable_method,
                             'partial_dependency': self.partial_dependency_method,
                             'include_type': self.include_type_method,
                             'as_system': self.as_system_method,
                             'as_link_whole': self.as_link_whole_method,
                             })

    def found(self):
        return self.found_method([], {})

    @noPosargs
    @permittedKwargs({})
    def type_name_method(self, args, kwargs):
        return self.held_object.type_name

    @noPosargs
    @permittedKwargs({})
    def found_method(self, args, kwargs):
        if self.held_object.type_name == 'internal':
            return True
        return self.held_object.found()

    @noPosargs
    @permittedKwargs({})
    def version_method(self, args, kwargs):
        return self.held_object.get_version()

    @noPosargs
    @permittedKwargs({})
    def name_method(self, args, kwargs):
        return self.held_object.get_name()

    @FeatureDeprecated('Dependency.get_pkgconfig_variable', '0.56.0',
                       'use Dependency.get_variable(pkgconfig : ...) instead')
    @permittedKwargs({'define_variable', 'default'})
    def pkgconfig_method(self, args, kwargs):
        args = listify(args)
        if len(args) != 1:
            raise InterpreterException('get_pkgconfig_variable takes exactly one argument.')
        varname = args[0]
        if not isinstance(varname, str):
            raise InterpreterException('Variable name must be a string.')
        return self.held_object.get_pkgconfig_variable(varname, kwargs)

    @FeatureNew('dep.get_configtool_variable', '0.44.0')
    @FeatureDeprecated('Dependency.get_configtool_variable', '0.56.0',
                       'use Dependency.get_variable(configtool : ...) instead')
    @permittedKwargs({})
    def configtool_method(self, args, kwargs):
        args = listify(args)
        if len(args) != 1:
            raise InterpreterException('get_configtool_variable takes exactly one argument.')
        varname = args[0]
        if not isinstance(varname, str):
            raise InterpreterException('Variable name must be a string.')
        return self.held_object.get_configtool_variable(varname)

    @FeatureNew('dep.partial_dependency', '0.46.0')
    @noPosargs
    @permittedKwargs(permitted_method_kwargs['partial_dependency'])
    def partial_dependency_method(self, args, kwargs):
        pdep = self.held_object.get_partial_dependency(**kwargs)
        return DependencyHolder(pdep, self.subproject)

    @FeatureNew('dep.get_variable', '0.51.0')
    @noPosargs
    @permittedKwargs({'cmake', 'pkgconfig', 'configtool', 'internal', 'default_value', 'pkgconfig_define'})
    @FeatureNewKwargs('dep.get_variable', '0.54.0', ['internal'])
    def variable_method(self, args, kwargs):
        return self.held_object.get_variable(**kwargs)

    @FeatureNew('dep.include_type', '0.52.0')
    @noPosargs
    @permittedKwargs({})
    def include_type_method(self, args, kwargs):
        return self.held_object.get_include_type()

    @FeatureNew('dep.as_system', '0.52.0')
    @permittedKwargs({})
    def as_system_method(self, args, kwargs):
        args = listify(args)
        new_is_system = 'system'
        if len(args) > 1:
            raise InterpreterException('as_system takes only one optional value')
        if len(args) == 1:
            new_is_system = args[0]
        new_dep = self.held_object.generate_system_dependency(new_is_system)
        return DependencyHolder(new_dep, self.subproject)

    @FeatureNew('dep.as_link_whole', '0.56.0')
    @permittedKwargs({})
    @noPosargs
    def as_link_whole_method(self, args, kwargs):
        if not isinstance(self.held_object, InternalDependency):
            raise InterpreterException('as_link_whole method is only supported on declare_dependency() objects')
        new_dep = self.held_object.generate_link_whole_dependency()
        return DependencyHolder(new_dep, self.subproject)

class ExternalProgramHolder(InterpreterObject, ObjectHolder):
    def __init__(self, ep, subproject, backend=None):
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, ep)
        self.subproject = subproject
        self.backend = backend
        self.methods.update({'found': self.found_method,
                             'path': self.path_method,
                             'full_path': self.full_path_method})
        self.cached_version = None

    @noPosargs
    @permittedKwargs({})
    def found_method(self, args, kwargs):
        return self.found()

    @noPosargs
    @permittedKwargs({})
    @FeatureDeprecated('ExternalProgram.path', '0.55.0',
                       'use ExternalProgram.full_path() instead')
    def path_method(self, args, kwargs):
        return self._full_path()

    @noPosargs
    @permittedKwargs({})
    @FeatureNew('ExternalProgram.full_path', '0.55.0')
    def full_path_method(self, args, kwargs):
        return self._full_path()

    def _full_path(self):
        exe = self.held_object
        if isinstance(exe, build.Executable):
            return self.backend.get_target_filename_abs(exe)
        return exe.get_path()

    def found(self):
        return isinstance(self.held_object, build.Executable) or self.held_object.found()

    def get_command(self):
        return self.held_object.get_command()

    def get_name(self):
        exe = self.held_object
        if isinstance(exe, build.Executable):
            return exe.name
        return exe.get_name()

    def get_version(self, interpreter):
        if isinstance(self.held_object, build.Executable):
            return self.held_object.project_version
        if not self.cached_version:
            raw_cmd = self.get_command() + ['--version']
            cmd = [self, '--version']
            res = interpreter.run_command_impl(interpreter.current_node, cmd, {}, True)
            if res.returncode != 0:
                m = 'Running {!r} failed'
                raise InterpreterException(m.format(raw_cmd))
            output = res.stdout.strip()
            if not output:
                output = res.stderr.strip()
            match = re.search(r'([0-9][0-9\.]+)', output)
            if not match:
                m = 'Could not find a version number in output of {!r}'
                raise InterpreterException(m.format(raw_cmd))
            self.cached_version = match.group(1)
        return self.cached_version

class ExternalLibraryHolder(InterpreterObject, ObjectHolder):
    def __init__(self, el, pv):
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, el, pv)
        self.methods.update({'found': self.found_method,
                             'type_name': self.type_name_method,
                             'partial_dependency': self.partial_dependency_method,
                             })

    def found(self):
        return self.held_object.found()

    @noPosargs
    @permittedKwargs({})
    def type_name_method(self, args, kwargs):
        return self.held_object.type_name

    @noPosargs
    @permittedKwargs({})
    def found_method(self, args, kwargs):
        return self.found()

    def get_name(self):
        return self.held_object.name

    def get_compile_args(self):
        return self.held_object.get_compile_args()

    def get_link_args(self):
        return self.held_object.get_link_args()

    def get_exe_args(self):
        return self.held_object.get_exe_args()

    @FeatureNew('dep.partial_dependency', '0.46.0')
    @noPosargs
    @permittedKwargs(permitted_method_kwargs['partial_dependency'])
    def partial_dependency_method(self, args, kwargs):
        pdep = self.held_object.get_partial_dependency(**kwargs)
        return DependencyHolder(pdep, self.subproject)

class GeneratorHolder(InterpreterObject, ObjectHolder):
    @FeatureNewKwargs('generator', '0.43.0', ['capture'])
    def __init__(self, interp, args, kwargs):
        self.interpreter = interp
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, build.Generator(args, kwargs), interp.subproject)
        self.methods.update({'process': self.process_method})

    @FeatureNewKwargs('generator.process', '0.45.0', ['preserve_path_from'])
    @permittedKwargs({'extra_args', 'preserve_path_from'})
    def process_method(self, args, kwargs):
        extras = mesonlib.stringlistify(kwargs.get('extra_args', []))
        if 'preserve_path_from' in kwargs:
            preserve_path_from = kwargs['preserve_path_from']
            if not isinstance(preserve_path_from, str):
                raise InvalidArguments('Preserve_path_from must be a string.')
            preserve_path_from = os.path.normpath(preserve_path_from)
            if not os.path.isabs(preserve_path_from):
                # This is a bit of a hack. Fix properly before merging.
                raise InvalidArguments('Preserve_path_from must be an absolute path for now. Sorry.')
        else:
            preserve_path_from = None
        gl = self.held_object.process_files('Generator', args, self.interpreter,
                                            preserve_path_from, extra_args=extras)
        return GeneratedListHolder(gl)


class GeneratedListHolder(InterpreterObject, ObjectHolder):
    def __init__(self, arg1, extra_args=None):
        InterpreterObject.__init__(self)
        if isinstance(arg1, GeneratorHolder):
            ObjectHolder.__init__(self, build.GeneratedList(arg1.held_object, extra_args if extra_args is not None else []))
        else:
            ObjectHolder.__init__(self, arg1)

    def __repr__(self):
        r = '<{}: {!r}>'
        return r.format(self.__class__.__name__, self.held_object.get_outputs())

    def add_file(self, a):
        self.held_object.add_file(a)

# A machine that's statically known from the cross file
class MachineHolder(InterpreterObject, ObjectHolder):
    def __init__(self, machine_info):
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, machine_info)
        self.methods.update({'system': self.system_method,
                             'cpu': self.cpu_method,
                             'cpu_family': self.cpu_family_method,
                             'endian': self.endian_method,
                             })

    @noPosargs
    @permittedKwargs({})
    def cpu_family_method(self, args: T.List[TYPE_var], kwargs: TYPE_nkwargs) -> str:
        return self.held_object.cpu_family

    @noPosargs
    @permittedKwargs({})
    def cpu_method(self, args: T.List[TYPE_var], kwargs: TYPE_nkwargs) -> str:
        return self.held_object.cpu

    @noPosargs
    @permittedKwargs({})
    def system_method(self, args: T.List[TYPE_var], kwargs: TYPE_nkwargs) -> str:
        return self.held_object.system

    @noPosargs
    @permittedKwargs({})
    def endian_method(self, args: T.List[TYPE_var], kwargs: TYPE_nkwargs) -> str:
        return self.held_object.endian

class IncludeDirsHolder(InterpreterObject, ObjectHolder):
    def __init__(self, idobj):
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, idobj)

class Headers(InterpreterObject):

    def __init__(self, sources, kwargs):
        InterpreterObject.__init__(self)
        self.sources = sources
        self.install_subdir = kwargs.get('subdir', '')
        if os.path.isabs(self.install_subdir):
            mlog.deprecation('Subdir keyword must not be an absolute path. This will be a hard error in the next release.')
        self.custom_install_dir = kwargs.get('install_dir', None)
        self.custom_install_mode = kwargs.get('install_mode', None)
        if self.custom_install_dir is not None:
            if not isinstance(self.custom_install_dir, str):
                raise InterpreterException('Custom_install_dir must be a string.')

    def set_install_subdir(self, subdir):
        self.install_subdir = subdir

    def get_install_subdir(self):
        return self.install_subdir

    def get_sources(self):
        return self.sources

    def get_custom_install_dir(self):
        return self.custom_install_dir

    def get_custom_install_mode(self):
        return self.custom_install_mode

class DataHolder(InterpreterObject, ObjectHolder):
    def __init__(self, data):
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, data)

    def get_source_subdir(self):
        return self.held_object.source_subdir

    def get_sources(self):
        return self.held_object.sources

    def get_install_dir(self):
        return self.held_object.install_dir

class InstallDir(InterpreterObject):
    def __init__(self, src_subdir, inst_subdir, install_dir, install_mode,
                 exclude, strip_directory, from_source_dir=True):
        InterpreterObject.__init__(self)
        self.source_subdir = src_subdir
        self.installable_subdir = inst_subdir
        self.install_dir = install_dir
        self.install_mode = install_mode
        self.exclude = exclude
        self.strip_directory = strip_directory
        self.from_source_dir = from_source_dir

class Man(InterpreterObject):

    def __init__(self, sources, kwargs):
        InterpreterObject.__init__(self)
        self.sources = sources
        self.validate_sources()
        self.custom_install_dir = kwargs.get('install_dir', None)
        self.custom_install_mode = kwargs.get('install_mode', None)
        if self.custom_install_dir is not None and not isinstance(self.custom_install_dir, str):
            raise InterpreterException('Custom_install_dir must be a string.')

    def validate_sources(self):
        for s in self.sources:
            try:
                num = int(s.split('.')[-1])
            except (IndexError, ValueError):
                num = 0
            if num < 1 or num > 8:
                raise InvalidArguments('Man file must have a file extension of a number between 1 and 8')

    def get_custom_install_dir(self):
        return self.custom_install_dir

    def get_custom_install_mode(self):
        return self.custom_install_mode

    def get_sources(self):
        return self.sources

class GeneratedObjectsHolder(InterpreterObject, ObjectHolder):
    def __init__(self, held_object):
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, held_object)

class TargetHolder(InterpreterObject, ObjectHolder):
    def __init__(self, target, interp):
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, target, interp.subproject)
        self.interpreter = interp

class BuildTargetHolder(TargetHolder):
    def __init__(self, target, interp):
        super().__init__(target, interp)
        self.methods.update({'extract_objects': self.extract_objects_method,
                             'extract_all_objects': self.extract_all_objects_method,
                             'name': self.name_method,
                             'get_id': self.get_id_method,
                             'outdir': self.outdir_method,
                             'full_path': self.full_path_method,
                             'private_dir_include': self.private_dir_include_method,
                             })

    def __repr__(self):
        r = '<{} {}: {}>'
        h = self.held_object
        return r.format(self.__class__.__name__, h.get_id(), h.filename)

    def is_cross(self):
        return not self.held_object.environment.machines.matches_build_machine(self.held_object.for_machine)

    @noPosargs
    @permittedKwargs({})
    def private_dir_include_method(self, args, kwargs):
        return IncludeDirsHolder(build.IncludeDirs('', [], False,
                                                   [self.interpreter.backend.get_target_private_dir(self.held_object)]))

    @noPosargs
    @permittedKwargs({})
    def full_path_method(self, args, kwargs):
        return self.interpreter.backend.get_target_filename_abs(self.held_object)

    @noPosargs
    @permittedKwargs({})
    def outdir_method(self, args, kwargs):
        return self.interpreter.backend.get_target_dir(self.held_object)

    @permittedKwargs({})
    def extract_objects_method(self, args, kwargs):
        gobjs = self.held_object.extract_objects(args)
        return GeneratedObjectsHolder(gobjs)

    @FeatureNewKwargs('extract_all_objects', '0.46.0', ['recursive'])
    @noPosargs
    @permittedKwargs({'recursive'})
    def extract_all_objects_method(self, args, kwargs):
        recursive = kwargs.get('recursive', False)
        gobjs = self.held_object.extract_all_objects(recursive)
        if gobjs.objlist and 'recursive' not in kwargs:
            mlog.warning('extract_all_objects called without setting recursive '
                         'keyword argument. Meson currently defaults to '
                         'non-recursive to maintain backward compatibility but '
                         'the default will be changed in the future.',
                         location=self.current_node)
        return GeneratedObjectsHolder(gobjs)

    @noPosargs
    @permittedKwargs({})
    def get_id_method(self, args, kwargs):
        return self.held_object.get_id()

    @FeatureNew('name', '0.54.0')
    @noPosargs
    @permittedKwargs({})
    def name_method(self, args, kwargs):
        return self.held_object.name

class ExecutableHolder(BuildTargetHolder):
    def __init__(self, target, interp):
        super().__init__(target, interp)

class StaticLibraryHolder(BuildTargetHolder):
    def __init__(self, target, interp):
        super().__init__(target, interp)

class SharedLibraryHolder(BuildTargetHolder):
    def __init__(self, target, interp):
        super().__init__(target, interp)
        # Set to True only when called from self.func_shared_lib().
        target.shared_library_only = False

class BothLibrariesHolder(BuildTargetHolder):
    def __init__(self, shared_holder, static_holder, interp):
        # FIXME: This build target always represents the shared library, but
        # that should be configurable.
        super().__init__(shared_holder.held_object, interp)
        self.shared_holder = shared_holder
        self.static_holder = static_holder
        self.methods.update({'get_shared_lib': self.get_shared_lib_method,
                             'get_static_lib': self.get_static_lib_method,
                             })

    def __repr__(self):
        r = '<{} {}: {}, {}: {}>'
        h1 = self.shared_holder.held_object
        h2 = self.static_holder.held_object
        return r.format(self.__class__.__name__, h1.get_id(), h1.filename, h2.get_id(), h2.filename)

    @noPosargs
    @permittedKwargs({})
    def get_shared_lib_method(self, args, kwargs):
        return self.shared_holder

    @noPosargs
    @permittedKwargs({})
    def get_static_lib_method(self, args, kwargs):
        return self.static_holder

class SharedModuleHolder(BuildTargetHolder):
    def __init__(self, target, interp):
        super().__init__(target, interp)

class JarHolder(BuildTargetHolder):
    def __init__(self, target, interp):
        super().__init__(target, interp)

class CustomTargetIndexHolder(TargetHolder):
    def __init__(self, target, interp):
        super().__init__(target, interp)
        self.methods.update({'full_path': self.full_path_method,
                             })

    @FeatureNew('custom_target[i].full_path', '0.54.0')
    @noPosargs
    @permittedKwargs({})
    def full_path_method(self, args, kwargs):
        return self.interpreter.backend.get_target_filename_abs(self.held_object)

class CustomTargetHolder(TargetHolder):
    def __init__(self, target, interp):
        super().__init__(target, interp)
        self.methods.update({'full_path': self.full_path_method,
                             'to_list': self.to_list_method,
                             })

    def __repr__(self):
        r = '<{} {}: {}>'
        h = self.held_object
        return r.format(self.__class__.__name__, h.get_id(), h.command)

    @noPosargs
    @permittedKwargs({})
    def full_path_method(self, args, kwargs):
        return self.interpreter.backend.get_target_filename_abs(self.held_object)

    @FeatureNew('custom_target.to_list', '0.54.0')
    @noPosargs
    @permittedKwargs({})
    def to_list_method(self, args, kwargs):
        result = []
        for i in self.held_object:
            result.append(CustomTargetIndexHolder(i, self.interpreter))
        return result

    def __getitem__(self, index):
        return CustomTargetIndexHolder(self.held_object[index], self.interpreter)

    def __setitem__(self, index, value):  # lgtm[py/unexpected-raise-in-special-method]
        raise InterpreterException('Cannot set a member of a CustomTarget')

    def __delitem__(self, index):  # lgtm[py/unexpected-raise-in-special-method]
        raise InterpreterException('Cannot delete a member of a CustomTarget')

    def outdir_include(self):
        return IncludeDirsHolder(build.IncludeDirs('', [], False,
                                                   [os.path.join('@BUILD_ROOT@', self.interpreter.backend.get_target_dir(self.held_object))]))

class RunTargetHolder(TargetHolder):
    def __init__(self, target, interp):
        super().__init__(target, interp)

    def __repr__(self):
        r = '<{} {}: {}>'
        h = self.held_object
        return r.format(self.__class__.__name__, h.get_id(), h.command)

class Test(InterpreterObject):
    def __init__(self, name: str, project: str, suite: T.List[str], exe: build.Executable,
                 depends: T.List[T.Union[build.CustomTarget, build.BuildTarget]],
                 is_parallel: bool, cmd_args: T.List[str], env: build.EnvironmentVariables,
                 should_fail: bool, timeout: int, workdir: T.Optional[str], protocol: str,
                 priority: int):
        InterpreterObject.__init__(self)
        self.name = name
        self.suite = suite
        self.project_name = project
        self.exe = exe
        self.depends = depends
        self.is_parallel = is_parallel
        self.cmd_args = cmd_args
        self.env = env
        self.should_fail = should_fail
        self.timeout = timeout
        self.workdir = workdir
        self.protocol = TestProtocol.from_str(protocol)
        self.priority = priority

    def get_exe(self):
        return self.exe

    def get_name(self):
        return self.name

class SubprojectHolder(InterpreterObject, ObjectHolder):

    def __init__(self, subinterpreter, subdir, warnings=0, disabled_feature=None,
                 exception=None):
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, subinterpreter)
        self.warnings = warnings
        self.disabled_feature = disabled_feature
        self.exception = exception
        self.subdir = PurePath(subdir).as_posix()
        self.methods.update({'get_variable': self.get_variable_method,
                             'found': self.found_method,
                             })

    @noPosargs
    @permittedKwargs({})
    def found_method(self, args, kwargs):
        return self.found()

    def found(self):
        return self.held_object is not None

    @permittedKwargs({})
    @noArgsFlattening
    def get_variable_method(self, args, kwargs):
        if len(args) < 1 or len(args) > 2:
            raise InterpreterException('Get_variable takes one or two arguments.')
        if not self.found():
            raise InterpreterException('Subproject "%s" disabled can\'t get_variable on it.' % (self.subdir))
        varname = args[0]
        if not isinstance(varname, str):
            raise InterpreterException('Get_variable first argument must be a string.')
        try:
            return self.held_object.variables[varname]
        except KeyError:
            pass

        if len(args) == 2:
            return args[1]

        raise InvalidArguments('Requested variable "{0}" not found.'.format(varname))

header_permitted_kwargs = set([
    'required',
    'prefix',
    'no_builtin_args',
    'include_directories',
    'args',
    'dependencies',
])

find_library_permitted_kwargs = set([
    'has_headers',
    'required',
    'dirs',
    'static',
])

find_library_permitted_kwargs |= set(['header_' + k for k in header_permitted_kwargs])

class CompilerHolder(InterpreterObject):
    def __init__(self, compiler, env, subproject):
        InterpreterObject.__init__(self)
        self.compiler = compiler
        self.environment = env
        self.subproject = subproject
        self.methods.update({'compiles': self.compiles_method,
                             'links': self.links_method,
                             'get_id': self.get_id_method,
                             'get_linker_id': self.get_linker_id_method,
                             'compute_int': self.compute_int_method,
                             'sizeof': self.sizeof_method,
                             'get_define': self.get_define_method,
                             'check_header': self.check_header_method,
                             'has_header': self.has_header_method,
                             'has_header_symbol': self.has_header_symbol_method,
                             'run': self.run_method,
                             'has_function': self.has_function_method,
                             'has_member': self.has_member_method,
                             'has_members': self.has_members_method,
                             'has_type': self.has_type_method,
                             'alignment': self.alignment_method,
                             'version': self.version_method,
                             'cmd_array': self.cmd_array_method,
                             'find_library': self.find_library_method,
                             'has_argument': self.has_argument_method,
                             'has_function_attribute': self.has_func_attribute_method,
                             'get_supported_function_attributes': self.get_supported_function_attributes_method,
                             'has_multi_arguments': self.has_multi_arguments_method,
                             'get_supported_arguments': self.get_supported_arguments_method,
                             'first_supported_argument': self.first_supported_argument_method,
                             'has_link_argument': self.has_link_argument_method,
                             'has_multi_link_arguments': self.has_multi_link_arguments_method,
                             'get_supported_link_arguments': self.get_supported_link_arguments_method,
                             'first_supported_link_argument': self.first_supported_link_argument_method,
                             'unittest_args': self.unittest_args_method,
                             'symbols_have_underscore_prefix': self.symbols_have_underscore_prefix_method,
                             'get_argument_syntax': self.get_argument_syntax_method,
                             })

    def _dep_msg(self, deps, endl):
        msg_single = 'with dependency {}'
        msg_many = 'with dependencies {}'
        if not deps:
            return endl
        if endl is None:
            endl = ''
        tpl = msg_many if len(deps) > 1 else msg_single
        names = []
        for d in deps:
            if isinstance(d, dependencies.ExternalLibrary):
                name = '-l' + d.name
            else:
                name = d.name
            names.append(name)
        return tpl.format(', '.join(names)) + endl

    @noPosargs
    @permittedKwargs({})
    def version_method(self, args, kwargs):
        return self.compiler.version

    @noPosargs
    @permittedKwargs({})
    def cmd_array_method(self, args, kwargs):
        return self.compiler.exelist

    def determine_args(self, kwargs, mode='link'):
        nobuiltins = kwargs.get('no_builtin_args', False)
        if not isinstance(nobuiltins, bool):
            raise InterpreterException('Type of no_builtin_args not a boolean.')
        args = []
        incdirs = extract_as_list(kwargs, 'include_directories')
        for i in incdirs:
            if not isinstance(i, IncludeDirsHolder):
                raise InterpreterException('Include directories argument must be an include_directories object.')
            for idir in i.held_object.get_incdirs():
                idir = os.path.join(self.environment.get_source_dir(),
                                    i.held_object.get_curdir(), idir)
                args += self.compiler.get_include_args(idir, False)
        if not nobuiltins:
            for_machine = Interpreter.machine_from_native_kwarg(kwargs)
            opts = self.environment.coredata.compiler_options[for_machine][self.compiler.language]
            args += self.compiler.get_option_compile_args(opts)
            if mode == 'link':
                args += self.compiler.get_option_link_args(opts)
        args += mesonlib.stringlistify(kwargs.get('args', []))
        return args

    def determine_dependencies(self, kwargs, endl=':'):
        deps = kwargs.get('dependencies', None)
        if deps is not None:
            deps = listify(deps)
            final_deps = []
            for d in deps:
                try:
                    d = d.held_object
                except Exception:
                    pass
                if isinstance(d, InternalDependency) or not isinstance(d, Dependency):
                    raise InterpreterException('Dependencies must be external dependencies')
                final_deps.append(d)
            deps = final_deps
        return deps, self._dep_msg(deps, endl)

    @permittedKwargs({
        'prefix',
        'args',
        'dependencies',
    })
    def alignment_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Alignment method takes exactly one positional argument.')
        check_stringlist(args)
        typename = args[0]
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of alignment must be a string.')
        extra_args = mesonlib.stringlistify(kwargs.get('args', []))
        deps, msg = self.determine_dependencies(kwargs)
        result = self.compiler.alignment(typename, prefix, self.environment,
                                         extra_args=extra_args,
                                         dependencies=deps)
        mlog.log('Checking for alignment of', mlog.bold(typename, True), msg, result)
        return result

    @permittedKwargs({
        'name',
        'no_builtin_args',
        'include_directories',
        'args',
        'dependencies',
    })
    def run_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Run method takes exactly one positional argument.')
        code = args[0]
        if isinstance(code, mesonlib.File):
            code = mesonlib.File.from_absolute_file(
                code.rel_to_builddir(self.environment.source_dir))
        elif not isinstance(code, str):
            raise InvalidArguments('Argument must be string or file.')
        testname = kwargs.get('name', '')
        if not isinstance(testname, str):
            raise InterpreterException('Testname argument must be a string.')
        extra_args = functools.partial(self.determine_args, kwargs)
        deps, msg = self.determine_dependencies(kwargs, endl=None)
        result = self.compiler.run(code, self.environment, extra_args=extra_args,
                                   dependencies=deps)
        if len(testname) > 0:
            if not result.compiled:
                h = mlog.red('DID NOT COMPILE')
            elif result.returncode == 0:
                h = mlog.green('YES')
            else:
                h = mlog.red('NO (%d)' % result.returncode)
            mlog.log('Checking if', mlog.bold(testname, True), msg, 'runs:', h)
        return TryRunResultHolder(result)

    @noPosargs
    @permittedKwargs({})
    def get_id_method(self, args, kwargs):
        return self.compiler.get_id()

    @noPosargs
    @permittedKwargs({})
    @FeatureNew('compiler.get_linker_id', '0.53.0')
    def get_linker_id_method(self, args, kwargs):
        return self.compiler.get_linker_id()

    @noPosargs
    @permittedKwargs({})
    def symbols_have_underscore_prefix_method(self, args, kwargs):
        '''
        Check if the compiler prefixes _ (underscore) to global C symbols
        See: https://en.wikipedia.org/wiki/Name_mangling#C
        '''
        return self.compiler.symbols_have_underscore_prefix(self.environment)

    @noPosargs
    @permittedKwargs({})
    def unittest_args_method(self, args, kwargs):
        '''
        This function is deprecated and should not be used.
        It can be removed in a future version of Meson.
        '''
        if not hasattr(self.compiler, 'get_feature_args'):
            raise InterpreterException('This {} compiler has no feature arguments.'.format(self.compiler.get_display_language()))
        build_to_src = os.path.relpath(self.environment.get_source_dir(), self.environment.get_build_dir())
        return self.compiler.get_feature_args({'unittest': 'true'}, build_to_src)

    @permittedKwargs({
        'prefix',
        'no_builtin_args',
        'include_directories',
        'args',
        'dependencies',
    })
    def has_member_method(self, args, kwargs):
        if len(args) != 2:
            raise InterpreterException('Has_member takes exactly two arguments.')
        check_stringlist(args)
        typename, membername = args
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of has_member must be a string.')
        extra_args = functools.partial(self.determine_args, kwargs)
        deps, msg = self.determine_dependencies(kwargs)
        had, cached = self.compiler.has_members(typename, [membername], prefix,
                                                self.environment,
                                                extra_args=extra_args,
                                                dependencies=deps)
        cached = mlog.blue('(cached)') if cached else ''
        if had:
            hadtxt = mlog.green('YES')
        else:
            hadtxt = mlog.red('NO')
        mlog.log('Checking whether type', mlog.bold(typename, True),
                 'has member', mlog.bold(membername, True), msg, hadtxt, cached)
        return had

    @permittedKwargs({
        'prefix',
        'no_builtin_args',
        'include_directories',
        'args',
        'dependencies',
    })
    def has_members_method(self, args, kwargs):
        if len(args) < 2:
            raise InterpreterException('Has_members needs at least two arguments.')
        check_stringlist(args)
        typename, *membernames = args
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of has_members must be a string.')
        extra_args = functools.partial(self.determine_args, kwargs)
        deps, msg = self.determine_dependencies(kwargs)
        had, cached = self.compiler.has_members(typename, membernames, prefix,
                                                self.environment,
                                                extra_args=extra_args,
                                                dependencies=deps)
        cached = mlog.blue('(cached)') if cached else ''
        if had:
            hadtxt = mlog.green('YES')
        else:
            hadtxt = mlog.red('NO')
        members = mlog.bold(', '.join(['"{}"'.format(m) for m in membernames]))
        mlog.log('Checking whether type', mlog.bold(typename, True),
                 'has members', members, msg, hadtxt, cached)
        return had

    @permittedKwargs({
        'prefix',
        'no_builtin_args',
        'include_directories',
        'args',
        'dependencies',
    })
    def has_function_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Has_function takes exactly one argument.')
        check_stringlist(args)
        funcname = args[0]
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of has_function must be a string.')
        extra_args = self.determine_args(kwargs)
        deps, msg = self.determine_dependencies(kwargs)
        had, cached = self.compiler.has_function(funcname, prefix, self.environment,
                                                 extra_args=extra_args,
                                                 dependencies=deps)
        cached = mlog.blue('(cached)') if cached else ''
        if had:
            hadtxt = mlog.green('YES')
        else:
            hadtxt = mlog.red('NO')
        mlog.log('Checking for function', mlog.bold(funcname, True), msg, hadtxt, cached)
        return had

    @permittedKwargs({
        'prefix',
        'no_builtin_args',
        'include_directories',
        'args',
        'dependencies',
    })
    def has_type_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Has_type takes exactly one argument.')
        check_stringlist(args)
        typename = args[0]
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of has_type must be a string.')
        extra_args = functools.partial(self.determine_args, kwargs)
        deps, msg = self.determine_dependencies(kwargs)
        had, cached = self.compiler.has_type(typename, prefix, self.environment,
                                             extra_args=extra_args, dependencies=deps)
        cached = mlog.blue('(cached)') if cached else ''
        if had:
            hadtxt = mlog.green('YES')
        else:
            hadtxt = mlog.red('NO')
        mlog.log('Checking for type', mlog.bold(typename, True), msg, hadtxt, cached)
        return had

    @FeatureNew('compiler.compute_int', '0.40.0')
    @permittedKwargs({
        'prefix',
        'low',
        'high',
        'guess',
        'no_builtin_args',
        'include_directories',
        'args',
        'dependencies',
    })
    def compute_int_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Compute_int takes exactly one argument.')
        check_stringlist(args)
        expression = args[0]
        prefix = kwargs.get('prefix', '')
        low = kwargs.get('low', None)
        high = kwargs.get('high', None)
        guess = kwargs.get('guess', None)
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of compute_int must be a string.')
        if low is not None and not isinstance(low, int):
            raise InterpreterException('Low argument of compute_int must be an int.')
        if high is not None and not isinstance(high, int):
            raise InterpreterException('High argument of compute_int must be an int.')
        if guess is not None and not isinstance(guess, int):
            raise InterpreterException('Guess argument of compute_int must be an int.')
        extra_args = functools.partial(self.determine_args, kwargs)
        deps, msg = self.determine_dependencies(kwargs)
        res = self.compiler.compute_int(expression, low, high, guess, prefix,
                                        self.environment, extra_args=extra_args,
                                        dependencies=deps)
        mlog.log('Computing int of', mlog.bold(expression, True), msg, res)
        return res

    @permittedKwargs({
        'prefix',
        'no_builtin_args',
        'include_directories',
        'args',
        'dependencies',
    })
    def sizeof_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Sizeof takes exactly one argument.')
        check_stringlist(args)
        element = args[0]
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of sizeof must be a string.')
        extra_args = functools.partial(self.determine_args, kwargs)
        deps, msg = self.determine_dependencies(kwargs)
        esize = self.compiler.sizeof(element, prefix, self.environment,
                                     extra_args=extra_args, dependencies=deps)
        mlog.log('Checking for size of', mlog.bold(element, True), msg, esize)
        return esize

    @FeatureNew('compiler.get_define', '0.40.0')
    @permittedKwargs({
        'prefix',
        'no_builtin_args',
        'include_directories',
        'args',
        'dependencies',
    })
    def get_define_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('get_define() takes exactly one argument.')
        check_stringlist(args)
        element = args[0]
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of get_define() must be a string.')
        extra_args = functools.partial(self.determine_args, kwargs)
        deps, msg = self.determine_dependencies(kwargs)
        value, cached = self.compiler.get_define(element, prefix, self.environment,
                                                 extra_args=extra_args,
                                                 dependencies=deps)
        cached = mlog.blue('(cached)') if cached else ''
        mlog.log('Fetching value of define', mlog.bold(element, True), msg, value, cached)
        return value

    @permittedKwargs({
        'name',
        'no_builtin_args',
        'include_directories',
        'args',
        'dependencies',
    })
    def compiles_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('compiles method takes exactly one argument.')
        code = args[0]
        if isinstance(code, mesonlib.File):
            code = mesonlib.File.from_absolute_file(
                code.rel_to_builddir(self.environment.source_dir))
        elif not isinstance(code, str):
            raise InvalidArguments('Argument must be string or file.')
        testname = kwargs.get('name', '')
        if not isinstance(testname, str):
            raise InterpreterException('Testname argument must be a string.')
        extra_args = functools.partial(self.determine_args, kwargs)
        deps, msg = self.determine_dependencies(kwargs, endl=None)
        result, cached = self.compiler.compiles(code, self.environment,
                                                extra_args=extra_args,
                                                dependencies=deps)
        if len(testname) > 0:
            if result:
                h = mlog.green('YES')
            else:
                h = mlog.red('NO')
            cached = mlog.blue('(cached)') if cached else ''
            mlog.log('Checking if', mlog.bold(testname, True), msg, 'compiles:', h, cached)
        return result

    @permittedKwargs({
        'name',
        'no_builtin_args',
        'include_directories',
        'args',
        'dependencies',
    })
    def links_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('links method takes exactly one argument.')
        code = args[0]
        if isinstance(code, mesonlib.File):
            code = mesonlib.File.from_absolute_file(
                code.rel_to_builddir(self.environment.source_dir))
        elif not isinstance(code, str):
            raise InvalidArguments('Argument must be string or file.')
        testname = kwargs.get('name', '')
        if not isinstance(testname, str):
            raise InterpreterException('Testname argument must be a string.')
        extra_args = functools.partial(self.determine_args, kwargs)
        deps, msg = self.determine_dependencies(kwargs, endl=None)
        result, cached = self.compiler.links(code, self.environment,
                                             extra_args=extra_args,
                                             dependencies=deps)
        cached = mlog.blue('(cached)') if cached else ''
        if len(testname) > 0:
            if result:
                h = mlog.green('YES')
            else:
                h = mlog.red('NO')
            mlog.log('Checking if', mlog.bold(testname, True), msg, 'links:', h, cached)
        return result

    @FeatureNew('compiler.check_header', '0.47.0')
    @FeatureNewKwargs('compiler.check_header', '0.50.0', ['required'])
    @permittedKwargs(header_permitted_kwargs)
    def check_header_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('check_header method takes exactly one argument.')
        check_stringlist(args)
        hname = args[0]
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of has_header must be a string.')
        disabled, required, feature = extract_required_kwarg(kwargs, self.subproject, default=False)
        if disabled:
            mlog.log('Check usable header', mlog.bold(hname, True), 'skipped: feature', mlog.bold(feature), 'disabled')
            return False
        extra_args = functools.partial(self.determine_args, kwargs)
        deps, msg = self.determine_dependencies(kwargs)
        haz, cached = self.compiler.check_header(hname, prefix, self.environment,
                                                 extra_args=extra_args,
                                                 dependencies=deps)
        cached = mlog.blue('(cached)') if cached else ''
        if required and not haz:
            raise InterpreterException('{} header {!r} not usable'.format(self.compiler.get_display_language(), hname))
        elif haz:
            h = mlog.green('YES')
        else:
            h = mlog.red('NO')
        mlog.log('Check usable header', mlog.bold(hname, True), msg, h, cached)
        return haz

    @FeatureNewKwargs('compiler.has_header', '0.50.0', ['required'])
    @permittedKwargs(header_permitted_kwargs)
    def has_header_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('has_header method takes exactly one argument.')
        check_stringlist(args)
        hname = args[0]
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of has_header must be a string.')
        disabled, required, feature = extract_required_kwarg(kwargs, self.subproject, default=False)
        if disabled:
            mlog.log('Has header', mlog.bold(hname, True), 'skipped: feature', mlog.bold(feature), 'disabled')
            return False
        extra_args = functools.partial(self.determine_args, kwargs)
        deps, msg = self.determine_dependencies(kwargs)
        haz, cached = self.compiler.has_header(hname, prefix, self.environment,
                                               extra_args=extra_args, dependencies=deps)
        cached = mlog.blue('(cached)') if cached else ''
        if required and not haz:
            raise InterpreterException('{} header {!r} not found'.format(self.compiler.get_display_language(), hname))
        elif haz:
            h = mlog.green('YES')
        else:
            h = mlog.red('NO')
        mlog.log('Has header', mlog.bold(hname, True), msg, h, cached)
        return haz

    @FeatureNewKwargs('compiler.has_header_symbol', '0.50.0', ['required'])
    @permittedKwargs(header_permitted_kwargs)
    def has_header_symbol_method(self, args, kwargs):
        if len(args) != 2:
            raise InterpreterException('has_header_symbol method takes exactly two arguments.')
        check_stringlist(args)
        hname, symbol = args
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of has_header_symbol must be a string.')
        disabled, required, feature = extract_required_kwarg(kwargs, self.subproject, default=False)
        if disabled:
            mlog.log('Header <{0}> has symbol'.format(hname), mlog.bold(symbol, True), 'skipped: feature', mlog.bold(feature), 'disabled')
            return False
        extra_args = functools.partial(self.determine_args, kwargs)
        deps, msg = self.determine_dependencies(kwargs)
        haz, cached = self.compiler.has_header_symbol(hname, symbol, prefix, self.environment,
                                                      extra_args=extra_args,
                                                      dependencies=deps)
        if required and not haz:
            raise InterpreterException('{} symbol {} not found in header {}'.format(self.compiler.get_display_language(), symbol, hname))
        elif haz:
            h = mlog.green('YES')
        else:
            h = mlog.red('NO')
        cached = mlog.blue('(cached)') if cached else ''
        mlog.log('Header <{0}> has symbol'.format(hname), mlog.bold(symbol, True), msg, h, cached)
        return haz

    def notfound_library(self, libname):
        lib = dependencies.ExternalLibrary(libname, None,
                                           self.environment,
                                           self.compiler.language,
                                           silent=True)
        return ExternalLibraryHolder(lib, self.subproject)

    @FeatureNewKwargs('compiler.find_library', '0.51.0', ['static'])
    @FeatureNewKwargs('compiler.find_library', '0.50.0', ['has_headers'])
    @FeatureNewKwargs('compiler.find_library', '0.49.0', ['disabler'])
    @disablerIfNotFound
    @permittedKwargs(find_library_permitted_kwargs)
    def find_library_method(self, args, kwargs):
        # TODO add dependencies support?
        if len(args) != 1:
            raise InterpreterException('find_library method takes one argument.')
        libname = args[0]
        if not isinstance(libname, str):
            raise InterpreterException('Library name not a string.')

        disabled, required, feature = extract_required_kwarg(kwargs, self.subproject)
        if disabled:
            mlog.log('Library', mlog.bold(libname), 'skipped: feature', mlog.bold(feature), 'disabled')
            return self.notfound_library(libname)

        has_header_kwargs = {k[7:]: v for k, v in kwargs.items() if k.startswith('header_')}
        has_header_kwargs['required'] = required
        headers = mesonlib.stringlistify(kwargs.get('has_headers', []))
        for h in headers:
            if not self.has_header_method([h], has_header_kwargs):
                return self.notfound_library(libname)

        search_dirs = extract_search_dirs(kwargs)

        libtype = mesonlib.LibType.PREFER_SHARED
        if 'static' in kwargs:
            if not isinstance(kwargs['static'], bool):
                raise InterpreterException('static must be a boolean')
            libtype = mesonlib.LibType.STATIC if kwargs['static'] else mesonlib.LibType.SHARED
        linkargs = self.compiler.find_library(libname, self.environment, search_dirs, libtype)
        if required and not linkargs:
            if libtype == mesonlib.LibType.PREFER_SHARED:
                libtype = 'shared or static'
            else:
                libtype = libtype.name.lower()
            raise InterpreterException('{} {} library {!r} not found'
                                       .format(self.compiler.get_display_language(),
                                               libtype, libname))
        lib = dependencies.ExternalLibrary(libname, linkargs, self.environment,
                                           self.compiler.language)
        return ExternalLibraryHolder(lib, self.subproject)

    @permittedKwargs({})
    def has_argument_method(self, args: T.Sequence[str], kwargs) -> bool:
        args = mesonlib.stringlistify(args)
        if len(args) != 1:
            raise InterpreterException('has_argument takes exactly one argument.')
        return self.has_multi_arguments_method(args, kwargs)

    @permittedKwargs({})
    def has_multi_arguments_method(self, args: T.Sequence[str], kwargs: dict):
        args = mesonlib.stringlistify(args)
        result, cached = self.compiler.has_multi_arguments(args, self.environment)
        if result:
            h = mlog.green('YES')
        else:
            h = mlog.red('NO')
        cached = mlog.blue('(cached)') if cached else ''
        mlog.log(
            'Compiler for {} supports arguments {}:'.format(
                self.compiler.get_display_language(), ' '.join(args)),
            h, cached)
        return result

    @FeatureNew('compiler.get_supported_arguments', '0.43.0')
    @permittedKwargs({})
    def get_supported_arguments_method(self, args, kwargs):
        args = mesonlib.stringlistify(args)
        supported_args = []
        for arg in args:
            if self.has_argument_method(arg, kwargs):
                supported_args.append(arg)
        return supported_args

    @permittedKwargs({})
    def first_supported_argument_method(self, args: T.Sequence[str], kwargs: dict) -> T.List[str]:
        for arg in mesonlib.stringlistify(args):
            if self.has_argument_method(arg, kwargs):
                mlog.log('First supported argument:', mlog.bold(arg))
                return [arg]
        mlog.log('First supported argument:', mlog.red('None'))
        return []

    @FeatureNew('compiler.has_link_argument', '0.46.0')
    @permittedKwargs({})
    def has_link_argument_method(self, args, kwargs):
        args = mesonlib.stringlistify(args)
        if len(args) != 1:
            raise InterpreterException('has_link_argument takes exactly one argument.')
        return self.has_multi_link_arguments_method(args, kwargs)

    @FeatureNew('compiler.has_multi_link_argument', '0.46.0')
    @permittedKwargs({})
    def has_multi_link_arguments_method(self, args, kwargs):
        args = mesonlib.stringlistify(args)
        result, cached = self.compiler.has_multi_link_arguments(args, self.environment)
        cached = mlog.blue('(cached)') if cached else ''
        if result:
            h = mlog.green('YES')
        else:
            h = mlog.red('NO')
        mlog.log(
            'Compiler for {} supports link arguments {}:'.format(
                self.compiler.get_display_language(), ' '.join(args)),
            h, cached)
        return result

    @FeatureNew('compiler.get_supported_link_arguments_method', '0.46.0')
    @permittedKwargs({})
    def get_supported_link_arguments_method(self, args, kwargs):
        args = mesonlib.stringlistify(args)
        supported_args = []
        for arg in args:
            if self.has_link_argument_method(arg, kwargs):
                supported_args.append(arg)
        return supported_args

    @FeatureNew('compiler.first_supported_link_argument_method', '0.46.0')
    @permittedKwargs({})
    def first_supported_link_argument_method(self, args, kwargs):
        for i in mesonlib.stringlistify(args):
            if self.has_link_argument_method(i, kwargs):
                mlog.log('First supported link argument:', mlog.bold(i))
                return [i]
        mlog.log('First supported link argument:', mlog.red('None'))
        return []

    @FeatureNew('compiler.has_function_attribute', '0.48.0')
    @permittedKwargs({})
    def has_func_attribute_method(self, args, kwargs):
        args = mesonlib.stringlistify(args)
        if len(args) != 1:
            raise InterpreterException('has_func_attribute takes exactly one argument.')
        result, cached = self.compiler.has_func_attribute(args[0], self.environment)
        cached = mlog.blue('(cached)') if cached else ''
        h = mlog.green('YES') if result else mlog.red('NO')
        mlog.log('Compiler for {} supports function attribute {}:'.format(self.compiler.get_display_language(), args[0]), h, cached)
        return result

    @FeatureNew('compiler.get_supported_function_attributes', '0.48.0')
    @permittedKwargs({})
    def get_supported_function_attributes_method(self, args, kwargs):
        args = mesonlib.stringlistify(args)
        return [a for a in args if self.has_func_attribute_method(a, kwargs)]

    @FeatureNew('compiler.get_argument_syntax_method', '0.49.0')
    @noPosargs
    @noKwargs
    def get_argument_syntax_method(self, args, kwargs):
        return self.compiler.get_argument_syntax()


ModuleState = collections.namedtuple('ModuleState', [
    'source_root', 'build_to_src', 'subproject', 'subdir', 'current_lineno', 'environment',
    'project_name', 'project_version', 'backend', 'targets',
    'data', 'headers', 'man', 'global_args', 'project_args', 'build_machine',
    'host_machine', 'target_machine', 'current_node'])

class ModuleHolder(InterpreterObject, ObjectHolder):
    def __init__(self, modname, module, interpreter):
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, module)
        self.modname = modname
        self.interpreter = interpreter

    def method_call(self, method_name, args, kwargs):
        try:
            fn = getattr(self.held_object, method_name)
        except AttributeError:
            raise InvalidArguments('Module %s does not have method %s.' % (self.modname, method_name))
        if method_name.startswith('_'):
            raise InvalidArguments('Function {!r} in module {!r} is private.'.format(method_name, self.modname))
        if not getattr(fn, 'no-args-flattening', False):
            args = flatten(args)
        # This is not 100% reliable but we can't use hash()
        # because the Build object contains dicts and lists.
        num_targets = len(self.interpreter.build.targets)
        state = ModuleState(
            source_root = self.interpreter.environment.get_source_dir(),
            build_to_src=mesonlib.relpath(self.interpreter.environment.get_source_dir(),
                                          self.interpreter.environment.get_build_dir()),
            subproject=self.interpreter.subproject,
            subdir=self.interpreter.subdir,
            current_lineno=self.interpreter.current_lineno,
            environment=self.interpreter.environment,
            project_name=self.interpreter.build.project_name,
            project_version=self.interpreter.build.dep_manifest[self.interpreter.active_projectname],
            # The backend object is under-used right now, but we will need it:
            # https://github.com/mesonbuild/meson/issues/1419
            backend=self.interpreter.backend,
            targets=self.interpreter.build.targets,
            data=self.interpreter.build.data,
            headers=self.interpreter.build.get_headers(),
            man=self.interpreter.build.get_man(),
            #global_args_for_build = self.interpreter.build.global_args.build,
            global_args = self.interpreter.build.global_args.host,
            #project_args_for_build = self.interpreter.build.projects_args.build.get(self.interpreter.subproject, {}),
            project_args = self.interpreter.build.projects_args.host.get(self.interpreter.subproject, {}),
            build_machine=self.interpreter.builtin['build_machine'].held_object,
            host_machine=self.interpreter.builtin['host_machine'].held_object,
            target_machine=self.interpreter.builtin['target_machine'].held_object,
            current_node=self.current_node
        )
        # Many modules do for example self.interpreter.find_program_impl(),
        # so we have to ensure they use the current interpreter and not the one
        # that first imported that module, otherwise it will use outdated
        # overrides.
        self.held_object.interpreter = self.interpreter
        if self.held_object.is_snippet(method_name):
            value = fn(self.interpreter, state, args, kwargs)
            return self.interpreter.holderify(value)
        else:
            value = fn(state, args, kwargs)
            if num_targets != len(self.interpreter.build.targets):
                raise InterpreterException('Extension module altered internal state illegally.')
            return self.interpreter.module_method_callback(value)


class Summary:
    def __init__(self, project_name, project_version):
        self.project_name = project_name
        self.project_version = project_version
        self.sections = collections.defaultdict(dict)
        self.max_key_len = 0

    def add_section(self, section, values, kwargs):
        bool_yn = kwargs.get('bool_yn', False)
        if not isinstance(bool_yn, bool):
            raise InterpreterException('bool_yn keyword argument must be boolean')
        list_sep = kwargs.get('list_sep')
        if list_sep is not None and not isinstance(list_sep, str):
            raise InterpreterException('list_sep keyword argument must be string')
        for k, v in values.items():
            if k in self.sections[section]:
                raise InterpreterException('Summary section {!r} already have key {!r}'.format(section, k))
            formatted_values = []
            for i in listify(v):
                if not isinstance(i, (str, int)):
                    m = 'Summary value in section {!r}, key {!r}, must be string, integer or boolean'
                    raise InterpreterException(m.format(section, k))
                if bool_yn and isinstance(i, bool):
                    formatted_values.append(mlog.green('YES') if i else mlog.red('NO'))
                else:
                    formatted_values.append(str(i))
            self.sections[section][k] = (formatted_values, list_sep)
            self.max_key_len = max(self.max_key_len, len(k))

    def text_len(self, v):
        if isinstance(v, str):
            return len(v)
        elif isinstance(v, mlog.AnsiDecorator):
            return len(v.text)
        else:
            raise RuntimeError('Expecting only strings or AnsiDecorator')

    def dump(self):
        mlog.log(self.project_name, mlog.normal_cyan(self.project_version))
        for section, values in self.sections.items():
            mlog.log('')  # newline
            if section:
                mlog.log(' ', mlog.bold(section))
            for k, v in values.items():
                v, list_sep = v
                indent = self.max_key_len - len(k) + 3
                end = ' ' if v else ''
                mlog.log(' ' * indent, k + ':', end=end)
                indent = self.max_key_len + 6
                self.dump_value(v, list_sep, indent)
        mlog.log('')  # newline

    def dump_value(self, arr, list_sep, indent):
        lines_sep = '\n' + ' ' * indent
        if list_sep is None:
            mlog.log(*arr, sep=lines_sep)
            return
        max_len = shutil.get_terminal_size().columns
        line = []
        line_len = indent
        lines_sep = list_sep.rstrip() + lines_sep
        for v in arr:
            v_len = self.text_len(v) + len(list_sep)
            if line and line_len + v_len > max_len:
                mlog.log(*line, sep=list_sep, end=lines_sep)
                line_len = indent
                line = []
            line.append(v)
            line_len += v_len
        mlog.log(*line, sep=list_sep)

class MesonMain(InterpreterObject):
    def __init__(self, build, interpreter):
        InterpreterObject.__init__(self)
        self.build = build
        self.interpreter = interpreter
        self._found_source_scripts = {}
        self.methods.update({'get_compiler': self.get_compiler_method,
                             'is_cross_build': self.is_cross_build_method,
                             'has_exe_wrapper': self.has_exe_wrapper_method,
                             'can_run_host_binaries': self.can_run_host_binaries_method,
                             'is_unity': self.is_unity_method,
                             'is_subproject': self.is_subproject_method,
                             'current_source_dir': self.current_source_dir_method,
                             'current_build_dir': self.current_build_dir_method,
                             'source_root': self.source_root_method,
                             'build_root': self.build_root_method,
                             'project_source_root': self.project_source_root_method,
                             'project_build_root': self.project_build_root_method,
                             'add_install_script': self.add_install_script_method,
                             'add_postconf_script': self.add_postconf_script_method,
                             'add_dist_script': self.add_dist_script_method,
                             'install_dependency_manifest': self.install_dependency_manifest_method,
                             'override_dependency': self.override_dependency_method,
                             'override_find_program': self.override_find_program_method,
                             'project_version': self.project_version_method,
                             'project_license': self.project_license_method,
                             'version': self.version_method,
                             'project_name': self.project_name_method,
                             'get_cross_property': self.get_cross_property_method,
                             'get_external_property': self.get_external_property_method,
                             'backend': self.backend_method,
                             })

    def _find_source_script(self, prog: T.Union[str, ExecutableHolder], args):
        if isinstance(prog, ExecutableHolder):
            prog_path = self.interpreter.backend.get_target_filename(prog.held_object)
            return build.RunScript([prog_path], args)
        elif isinstance(prog, ExternalProgramHolder):
            return build.RunScript(prog.get_command(), args)

        # Prefer scripts in the current source directory
        search_dir = os.path.join(self.interpreter.environment.source_dir,
                                  self.interpreter.subdir)
        key = (prog, search_dir)
        if key in self._found_source_scripts:
            found = self._found_source_scripts[key]
        else:
            found = dependencies.ExternalProgram(prog, search_dir=search_dir)
            if found.found():
                self._found_source_scripts[key] = found
            else:
                m = 'Script or command {!r} not found or not executable'
                raise InterpreterException(m.format(prog))
        return build.RunScript(found.get_command(), args)

    def _process_script_args(
            self, name: str, args: T.List[T.Union[
                str, mesonlib.File, CustomTargetHolder,
                CustomTargetIndexHolder, ConfigureFileHolder,
                ExternalProgramHolder, ExecutableHolder,
            ]], allow_built: bool = False) -> T.List[str]:
        script_args = []  # T.List[str]
        new = False
        for a in args:
            a = unholder(a)
            if isinstance(a, str):
                script_args.append(a)
            elif isinstance(a, mesonlib.File):
                new = True
                script_args.append(a.rel_to_builddir(self.interpreter.environment.source_dir))
            elif isinstance(a, (build.BuildTarget, build.CustomTarget, build.CustomTargetIndex)):
                if not allow_built:
                    raise InterpreterException('Arguments to {} cannot be built'.format(name))
                new = True
                script_args.extend([os.path.join(a.get_subdir(), o) for o in a.get_outputs()])

                # This feels really hacky, but I'm not sure how else to fix
                # this without completely rewriting install script handling.
                # This is complicated by the fact that the install target
                # depends on all.
                if isinstance(a, build.CustomTargetIndex):
                    a.target.build_by_default = True
                else:
                    a.build_by_default = True
            elif isinstance(a, build.ConfigureFile):
                new = True
                script_args.append(os.path.join(a.subdir, a.targetname))
            elif isinstance(a, dependencies.ExternalProgram):
                script_args.extend(a.command)
                new = True
            else:
                raise InterpreterException(
                    'Arguments to {} must be strings, Files, CustomTargets, '
                    'Indexes of CustomTargets, or ConfigureFiles'.format(name))
        if new:
            FeatureNew.single_use(
                'Calling "{}" with File, CustomTaget, Index of CustomTarget, '
                'ConfigureFile, Executable, or ExternalProgram'.format(name),
                '0.55.0', self.interpreter.subproject)
        return script_args

    @permittedKwargs(set())
    def add_install_script_method(self, args: 'T.Tuple[T.Union[str, ExecutableHolder], T.Union[str, mesonlib.File, CustomTargetHolder, CustomTargetIndexHolder, ConfigureFileHolder], ...]', kwargs):
        if len(args) < 1:
            raise InterpreterException('add_install_script takes one or more arguments')
        script_args = self._process_script_args('add_install_script', args[1:], allow_built=True)
        script = self._find_source_script(args[0], script_args)
        self.build.install_scripts.append(script)

    @permittedKwargs(set())
    def add_postconf_script_method(self, args, kwargs):
        if len(args) < 1:
            raise InterpreterException('add_postconf_script takes one or more arguments')
        script_args = self._process_script_args('add_postconf_script', args[1:], allow_built=True)
        script = self._find_source_script(args[0], script_args)
        self.build.postconf_scripts.append(script)

    @permittedKwargs(set())
    def add_dist_script_method(self, args, kwargs):
        if len(args) < 1:
            raise InterpreterException('add_dist_script takes one or more arguments')
        if len(args) > 1:
            FeatureNew.single_use('Calling "add_dist_script" with multiple arguments',
                                  '0.49.0', self.interpreter.subproject)
        if self.interpreter.subproject != '':
            raise InterpreterException('add_dist_script may not be used in a subproject.')
        script_args = self._process_script_args('add_dist_script', args[1:], allow_built=True)
        script = self._find_source_script(args[0], script_args)
        self.build.dist_scripts.append(script)

    @noPosargs
    @permittedKwargs({})
    def current_source_dir_method(self, args, kwargs):
        src = self.interpreter.environment.source_dir
        sub = self.interpreter.subdir
        if sub == '':
            return src
        return os.path.join(src, sub)

    @noPosargs
    @permittedKwargs({})
    def current_build_dir_method(self, args, kwargs):
        src = self.interpreter.environment.build_dir
        sub = self.interpreter.subdir
        if sub == '':
            return src
        return os.path.join(src, sub)

    @noPosargs
    @permittedKwargs({})
    def backend_method(self, args, kwargs):
        return self.interpreter.backend.name

    @noPosargs
    @permittedKwargs({})
    @FeatureDeprecated('meson.source_root', '0.56.0', 'use meson.current_source_dir instead.')
    def source_root_method(self, args, kwargs):
        return self.interpreter.environment.source_dir

    @noPosargs
    @permittedKwargs({})
    @FeatureDeprecated('meson.build_root', '0.56.0', 'use meson.current_build_dir instead.')
    def build_root_method(self, args, kwargs):
        return self.interpreter.environment.build_dir

    @noPosargs
    @permittedKwargs({})
    @FeatureNew('meson.project_source_root', '0.56.0')
    def project_source_root_method(self, args, kwargs):
        src = self.interpreter.environment.source_dir
        sub = self.interpreter.root_subdir
        if sub == '':
            return src
        return os.path.join(src, sub)

    @noPosargs
    @permittedKwargs({})
    @FeatureNew('meson.project_build_root', '0.56.0')
    def project_build_root_method(self, args, kwargs):
        src = self.interpreter.environment.build_dir
        sub = self.interpreter.root_subdir
        if sub == '':
            return src
        return os.path.join(src, sub)

    @noPosargs
    @permittedKwargs({})
    @FeatureDeprecated('meson.has_exe_wrapper', '0.55.0', 'use meson.can_run_host_binaries instead.')
    def has_exe_wrapper_method(self, args: T.Tuple[object, ...], kwargs: T.Dict[str, object]) -> bool:
        return self.can_run_host_binaries_impl(args, kwargs)

    @noPosargs
    @permittedKwargs({})
    @FeatureNew('meson.can_run_host_binaries', '0.55.0')
    def can_run_host_binaries_method(self, args: T.Tuple[object, ...], kwargs: T.Dict[str, object]) -> bool:
        return self.can_run_host_binaries_impl(args, kwargs)

    def can_run_host_binaries_impl(self, args, kwargs):
        if (self.is_cross_build_method(None, None) and
                self.build.environment.need_exe_wrapper()):
            if self.build.environment.exe_wrapper is None:
                return False
        # We return True when exe_wrap is defined, when it's not needed, and
        # when we're compiling natively. The last two are semantically confusing.
        # Need to revisit this.
        return True

    @noPosargs
    @permittedKwargs({})
    def is_cross_build_method(self, args, kwargs):
        return self.build.environment.is_cross_build()

    @permittedKwargs({'native'})
    def get_compiler_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('get_compiler_method must have one and only one argument.')
        cname = args[0]
        for_machine = Interpreter.machine_from_native_kwarg(kwargs)
        clist = self.interpreter.coredata.compilers[for_machine]
        if cname in clist:
            return CompilerHolder(clist[cname], self.build.environment, self.interpreter.subproject)
        raise InterpreterException('Tried to access compiler for language "%s", not specified for %s machine.' % (cname, for_machine.get_lower_case_name()))

    @noPosargs
    @permittedKwargs({})
    def is_unity_method(self, args, kwargs):
        optval = self.interpreter.environment.coredata.get_builtin_option('unity')
        if optval == 'on' or (optval == 'subprojects' and self.interpreter.is_subproject()):
            return True
        return False

    @noPosargs
    @permittedKwargs({})
    def is_subproject_method(self, args, kwargs):
        return self.interpreter.is_subproject()

    @permittedKwargs({})
    def install_dependency_manifest_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Must specify manifest install file name')
        if not isinstance(args[0], str):
            raise InterpreterException('Argument must be a string.')
        self.build.dep_manifest_name = args[0]

    @FeatureNew('meson.override_find_program', '0.46.0')
    @permittedKwargs({})
    def override_find_program_method(self, args, kwargs):
        if len(args) != 2:
            raise InterpreterException('Override needs two arguments')
        name, exe = args
        if not isinstance(name, str):
            raise InterpreterException('First argument must be a string')
        if hasattr(exe, 'held_object'):
            exe = exe.held_object
        if isinstance(exe, mesonlib.File):
            abspath = exe.absolute_path(self.interpreter.environment.source_dir,
                                        self.interpreter.environment.build_dir)
            if not os.path.exists(abspath):
                raise InterpreterException('Tried to override %s with a file that does not exist.' % name)
            exe = OverrideProgram(name, abspath)
        if not isinstance(exe, (dependencies.ExternalProgram, build.Executable)):
            raise InterpreterException('Second argument must be an external program or executable.')
        self.interpreter.add_find_program_override(name, exe)

    @FeatureNew('meson.override_dependency', '0.54.0')
    @permittedKwargs({'native'})
    def override_dependency_method(self, args, kwargs):
        if len(args) != 2:
            raise InterpreterException('Override needs two arguments')
        name = args[0]
        dep = args[1]
        if not isinstance(name, str) or not name:
            raise InterpreterException('First argument must be a string and cannot be empty')
        if hasattr(dep, 'held_object'):
            dep = dep.held_object
        if not isinstance(dep, dependencies.Dependency):
            raise InterpreterException('Second argument must be a dependency object')
        identifier = dependencies.get_dep_identifier(name, kwargs)
        for_machine = self.interpreter.machine_from_native_kwarg(kwargs)
        override = self.build.dependency_overrides[for_machine].get(identifier)
        if override:
            m = 'Tried to override dependency {!r} which has already been resolved or overridden at {}'
            location = mlog.get_error_location_string(override.node.filename, override.node.lineno)
            raise InterpreterException(m.format(name, location))
        self.build.dependency_overrides[for_machine][identifier] = \
            build.DependencyOverride(dep, self.interpreter.current_node)

    @noPosargs
    @permittedKwargs({})
    def project_version_method(self, args, kwargs):
        return self.build.dep_manifest[self.interpreter.active_projectname]['version']

    @FeatureNew('meson.project_license()', '0.45.0')
    @noPosargs
    @permittedKwargs({})
    def project_license_method(self, args, kwargs):
        return self.build.dep_manifest[self.interpreter.active_projectname]['license']

    @noPosargs
    @permittedKwargs({})
    def version_method(self, args, kwargs):
        return MesonVersionString(coredata.version)

    @noPosargs
    @permittedKwargs({})
    def project_name_method(self, args, kwargs):
        return self.interpreter.active_projectname

    @noArgsFlattening
    @permittedKwargs({})
    def get_cross_property_method(self, args, kwargs) -> str:
        if len(args) < 1 or len(args) > 2:
            raise InterpreterException('Must have one or two arguments.')
        propname = args[0]
        if not isinstance(propname, str):
            raise InterpreterException('Property name must be string.')
        try:
            props = self.interpreter.environment.properties.host
            return props[propname]
        except Exception:
            if len(args) == 2:
                return args[1]
            raise InterpreterException('Unknown cross property: %s.' % propname)

    @noArgsFlattening
    @permittedKwargs({'native'})
    @FeatureNew('meson.get_external_property', '0.54.0')
    def get_external_property_method(self, args: T.Sequence[str], kwargs: dict) -> str:
        if len(args) < 1 or len(args) > 2:
            raise InterpreterException('Must have one or two positional arguments.')
        propname = args[0]
        if not isinstance(propname, str):
            raise InterpreterException('Property name must be string.')

        def _get_native() -> str:
            try:
                props = self.interpreter.environment.properties.build
                return props[propname]
            except Exception:
                if len(args) == 2:
                    return args[1]
                raise InterpreterException('Unknown native property: %s.' % propname)
        if 'native' in kwargs:
            if kwargs['native']:
                return _get_native()
            else:
                return self.get_cross_property_method(args, {})
        else:  # native: not specified
            if self.build.environment.is_cross_build():
                return self.get_cross_property_method(args, kwargs)
            else:
                return _get_native()

known_library_kwargs = (
    build.known_shlib_kwargs |
    build.known_stlib_kwargs
)

known_build_target_kwargs = (
    known_library_kwargs |
    build.known_exe_kwargs |
    build.known_jar_kwargs |
    {'target_type'}
)

_base_test_args = {'args', 'depends', 'env', 'should_fail', 'timeout', 'workdir', 'suite', 'priority', 'protocol'}

permitted_kwargs = {'add_global_arguments': {'language', 'native'},
                    'add_global_link_arguments': {'language', 'native'},
                    'add_languages': {'required', 'native'},
                    'add_project_link_arguments': {'language', 'native'},
                    'add_project_arguments': {'language', 'native'},
                    'add_test_setup': {'exe_wrapper', 'gdb', 'timeout_multiplier', 'env', 'is_default'},
                    'benchmark': _base_test_args,
                    'build_target': known_build_target_kwargs,
                    'configure_file': {'input',
                                       'output',
                                       'configuration',
                                       'command',
                                       'copy',
                                       'depfile',
                                       'install_dir',
                                       'install_mode',
                                       'capture',
                                       'install',
                                       'format',
                                       'output_format',
                                       'encoding'},
                    'custom_target': {'input',
                                      'output',
                                      'command',
                                      'install',
                                      'install_dir',
                                      'install_mode',
                                      'build_always',
                                      'capture',
                                      'depends',
                                      'depend_files',
                                      'depfile',
                                      'build_by_default',
                                      'build_always_stale',
                                      'console'},
                    'dependency': {'default_options',
                                   'embed',
                                   'fallback',
                                   'language',
                                   'main',
                                   'method',
                                   'modules',
                                   'components',
                                   'cmake_module_path',
                                   'optional_modules',
                                   'native',
                                   'not_found_message',
                                   'required',
                                   'static',
                                   'version',
                                   'private_headers',
                                   'cmake_args',
                                   'include_type',
                                   },
                    'declare_dependency': {'include_directories',
                                           'link_with',
                                           'sources',
                                           'dependencies',
                                           'compile_args',
                                           'link_args',
                                           'link_whole',
                                           'version',
                                           'variables',
                                           },
                    'executable': build.known_exe_kwargs,
                    'find_program': {'required', 'native', 'version', 'dirs'},
                    'generator': {'arguments',
                                  'output',
                                  'depends',
                                  'depfile',
                                  'capture',
                                  'preserve_path_from'},
                    'include_directories': {'is_system'},
                    'install_data': {'install_dir', 'install_mode', 'rename', 'sources'},
                    'install_headers': {'install_dir', 'install_mode', 'subdir'},
                    'install_man': {'install_dir', 'install_mode'},
                    'install_subdir': {'exclude_files', 'exclude_directories', 'install_dir', 'install_mode', 'strip_directory'},
                    'jar': build.known_jar_kwargs,
                    'project': {'version', 'meson_version', 'default_options', 'license', 'subproject_dir'},
                    'run_command': {'check', 'capture', 'env'},
                    'run_target': {'command', 'depends'},
                    'shared_library': build.known_shlib_kwargs,
                    'shared_module': build.known_shmod_kwargs,
                    'static_library': build.known_stlib_kwargs,
                    'both_libraries': known_library_kwargs,
                    'library': known_library_kwargs,
                    'subdir': {'if_found'},
                    'subproject': {'version', 'default_options', 'required'},
                    'test': set.union(_base_test_args, {'is_parallel'}),
                    'vcs_tag': {'input', 'output', 'fallback', 'command', 'replace_string'},
                    }


class Interpreter(InterpreterBase):

    def __init__(
                self,
                build: build.Build,
                backend: T.Optional[Backend] = None,
                subproject: str = '',
                subdir: str = '',
                subproject_dir: str = 'subprojects',
                modules: T.Optional[T.Dict[str, ExtensionModule]] = None,
                default_project_options: T.Optional[T.Dict[str, str]] = None,
                mock: bool = False,
                ast: T.Optional[mparser.CodeBlockNode] = None,
            ) -> None:
        super().__init__(build.environment.get_source_dir(), subdir, subproject)
        self.an_unpicklable_object = mesonlib.an_unpicklable_object
        self.build = build
        self.environment = build.environment
        self.coredata = self.environment.get_coredata()
        self.backend = backend
        self.summary = {}
        if modules is None:
            self.modules = {}
        else:
            self.modules = modules
        # Subproject directory is usually the name of the subproject, but can
        # be different for dependencies provided by wrap files.
        self.subproject_directory_name = subdir.split(os.path.sep)[-1]
        self.subproject_dir = subproject_dir
        self.option_file = os.path.join(self.source_root, self.subdir, 'meson_options.txt')
        if not mock and ast is None:
            self.load_root_meson_file()
            self.sanity_check_ast()
        elif ast is not None:
            self.ast = ast
            self.sanity_check_ast()
        self.builtin.update({'meson': MesonMain(build, self)})
        self.generators = []
        self.visited_subdirs = {}
        self.project_args_frozen = False
        self.global_args_frozen = False  # implies self.project_args_frozen
        self.subprojects = {}
        self.subproject_stack = []
        self.configure_file_outputs = {}
        # Passed from the outside, only used in subprojects.
        if default_project_options:
            self.default_project_options = default_project_options.copy()
        else:
            self.default_project_options = {}
        self.project_default_options = {}
        self.build_func_dict()
        # build_def_files needs to be defined before parse_project is called
        self.build_def_files = [os.path.join(self.subdir, environment.build_filename)]
        if not mock:
            self.parse_project()
        self._redetect_machines()

    def _redetect_machines(self):
        # Re-initialize machine descriptions. We can do a better job now because we
        # have the compilers needed to gain more knowledge, so wipe out old
        # inference and start over.
        machines = self.build.environment.machines.miss_defaulting()
        machines.build = environment.detect_machine_info(self.coredata.compilers.build)
        self.build.environment.machines = machines.default_missing()
        assert self.build.environment.machines.build.cpu is not None
        assert self.build.environment.machines.host.cpu is not None
        assert self.build.environment.machines.target.cpu is not None

        self.builtin['build_machine'] = \
            MachineHolder(self.build.environment.machines.build)
        self.builtin['host_machine'] = \
            MachineHolder(self.build.environment.machines.host)
        self.builtin['target_machine'] = \
            MachineHolder(self.build.environment.machines.target)

    # TODO: Why is this in interpreter.py and not CoreData or Environment?
    def get_non_matching_default_options(self) -> T.Iterator[T.Tuple[str, str, coredata.UserOption]]:
        env = self.environment
        for def_opt_name, def_opt_value in self.project_default_options.items():
            for opts in env.coredata.get_all_options():
                cur_opt_value = opts.get(def_opt_name)
                if cur_opt_value is not None:
                    def_opt_value = env.coredata.validate_option_value(def_opt_name, def_opt_value)
                    if def_opt_value != cur_opt_value.value:
                        yield (def_opt_name, def_opt_value, cur_opt_value)

    def build_func_dict(self):
        self.funcs.update({'add_global_arguments': self.func_add_global_arguments,
                           'add_project_arguments': self.func_add_project_arguments,
                           'add_global_link_arguments': self.func_add_global_link_arguments,
                           'add_project_link_arguments': self.func_add_project_link_arguments,
                           'add_test_setup': self.func_add_test_setup,
                           'add_languages': self.func_add_languages,
                           'alias_target': self.func_alias_target,
                           'assert': self.func_assert,
                           'benchmark': self.func_benchmark,
                           'build_target': self.func_build_target,
                           'configuration_data': self.func_configuration_data,
                           'configure_file': self.func_configure_file,
                           'custom_target': self.func_custom_target,
                           'declare_dependency': self.func_declare_dependency,
                           'dependency': self.func_dependency,
                           'disabler': self.func_disabler,
                           'environment': self.func_environment,
                           'error': self.func_error,
                           'executable': self.func_executable,
                           'generator': self.func_generator,
                           'gettext': self.func_gettext,
                           'get_option': self.func_get_option,
                           'get_variable': self.func_get_variable,
                           'files': self.func_files,
                           'find_library': self.func_find_library,
                           'find_program': self.func_find_program,
                           'include_directories': self.func_include_directories,
                           'import': self.func_import,
                           'install_data': self.func_install_data,
                           'install_headers': self.func_install_headers,
                           'install_man': self.func_install_man,
                           'install_subdir': self.func_install_subdir,
                           'is_disabler': self.func_is_disabler,
                           'is_variable': self.func_is_variable,
                           'jar': self.func_jar,
                           'join_paths': self.func_join_paths,
                           'library': self.func_library,
                           'message': self.func_message,
                           'warning': self.func_warning,
                           'option': self.func_option,
                           'project': self.func_project,
                           'run_target': self.func_run_target,
                           'run_command': self.func_run_command,
                           'set_variable': self.func_set_variable,
                           'subdir': self.func_subdir,
                           'subdir_done': self.func_subdir_done,
                           'subproject': self.func_subproject,
                           'summary': self.func_summary,
                           'shared_library': self.func_shared_lib,
                           'shared_module': self.func_shared_module,
                           'static_library': self.func_static_lib,
                           'both_libraries': self.func_both_lib,
                           'test': self.func_test,
                           'vcs_tag': self.func_vcs_tag
                           })
        if 'MESON_UNIT_TEST' in os.environ:
            self.funcs.update({'exception': self.func_exception})

    def holderify(self, item):
        if isinstance(item, list):
            return [self.holderify(x) for x in item]
        if isinstance(item, dict):
            return {k: self.holderify(v) for k, v in item.items()}

        if isinstance(item, build.CustomTarget):
            return CustomTargetHolder(item, self)
        elif isinstance(item, (int, str, bool, Disabler, InterpreterObject)) or item is None:
            return item
        elif isinstance(item, build.Executable):
            return ExecutableHolder(item, self)
        elif isinstance(item, build.GeneratedList):
            return GeneratedListHolder(item)
        elif isinstance(item, build.RunTarget):
            raise RuntimeError('This is not a pipe.')
        elif isinstance(item, build.RunScript):
            raise RuntimeError('Do not do this.')
        elif isinstance(item, build.Data):
            return DataHolder(item)
        elif isinstance(item, dependencies.Dependency):
            return DependencyHolder(item, self.subproject)
        elif isinstance(item, dependencies.ExternalProgram):
            return ExternalProgramHolder(item, self.subproject)
        elif hasattr(item, 'held_object'):
            return item
        elif isinstance(item, InterpreterObject):
            return item
        else:
            raise InterpreterException('Module returned a value of unknown type.')

    def process_new_values(self, invalues):
        invalues = listify(invalues)
        for v in invalues:
            if isinstance(v, (RunTargetHolder, CustomTargetHolder, BuildTargetHolder)):
                v = v.held_object

            if isinstance(v, (build.BuildTarget, build.CustomTarget, build.RunTarget)):
                self.add_target(v.name, v)
            elif isinstance(v, list):
                self.module_method_callback(v)
            elif isinstance(v, build.GeneratedList):
                pass
            elif isinstance(v, build.RunScript):
                self.build.install_scripts.append(v)
            elif isinstance(v, build.Data):
                self.build.data.append(v)
            elif isinstance(v, dependencies.ExternalProgram):
                return ExternalProgramHolder(v, self.subproject)
            elif isinstance(v, dependencies.InternalDependency):
                # FIXME: This is special cased and not ideal:
                # The first source is our new VapiTarget, the rest are deps
                self.process_new_values(v.sources[0])
            elif isinstance(v, InstallDir):
                self.build.install_dirs.append(v)
            elif hasattr(v, 'held_object'):
                pass
            elif isinstance(v, (int, str, bool, Disabler)):
                pass
            else:
                raise InterpreterException('Module returned a value of unknown type.')

    def module_method_callback(self, return_object):
        if not isinstance(return_object, ModuleReturnValue):
            raise InterpreterException('Bug in module, it returned an invalid object')
        invalues = return_object.new_objects
        self.process_new_values(invalues)
        return self.holderify(return_object.return_value)

    def get_build_def_files(self) -> T.List[str]:
        return self.build_def_files

    def add_build_def_file(self, f):
        # Use relative path for files within source directory, and absolute path
        # for system files. Skip files within build directory. Also skip not regular
        # files (e.g. /dev/stdout) Normalize the path to avoid duplicates, this
        # is especially important to convert '/' to '\' on Windows.
        if isinstance(f, mesonlib.File):
            if f.is_built:
                return
            f = os.path.normpath(f.relative_name())
        elif os.path.isfile(f) and not f.startswith('/dev'):
            srcdir = Path(self.environment.get_source_dir())
            builddir = Path(self.environment.get_build_dir())
            try:
                f = Path(f).resolve()
            except OSError:
                f = Path(f)
                s = f.stat()
                if (hasattr(s, 'st_file_attributes') and
                        s.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT != 0 and
                        s.st_reparse_tag == stat.IO_REPARSE_TAG_APPEXECLINK):
                    # This is a Windows Store link which we can't
                    # resolve, so just do our best otherwise.
                    f = f.parent.resolve() / f.name
                else:
                    raise
            if builddir in f.parents:
                return
            if srcdir in f.parents:
                f = f.relative_to(srcdir)
            f = str(f)
        else:
            return
        if f not in self.build_def_files:
            self.build_def_files.append(f)

    def get_variables(self):
        return self.variables

    def check_stdlibs(self):
        machine_choices = [MachineChoice.HOST]
        if self.coredata.is_cross_build():
            machine_choices.append(MachineChoice.BUILD)
        for for_machine in machine_choices:
            props = self.build.environment.properties[for_machine]
            for l in self.coredata.compilers[for_machine].keys():
                try:
                    di = mesonlib.stringlistify(props.get_stdlib(l))
                except KeyError:
                    continue
                if len(di) == 1:
                    FeatureNew.single_use('stdlib without variable name', '0.56.0', self.subproject)
                kwargs = {'fallback': di,
                          'native': for_machine is MachineChoice.BUILD,
                          }
                name = display_name = l + '_stdlib'
                dep = self.dependency_impl(name, display_name, kwargs, force_fallback=True)
                self.build.stdlibs[for_machine][l] = dep

    def import_module(self, modname):
        if modname in self.modules:
            return
        try:
            module = importlib.import_module('mesonbuild.modules.' + modname)
        except ImportError:
            raise InvalidArguments('Module "%s" does not exist' % (modname, ))
        ext_module = module.initialize(self)
        assert isinstance(ext_module, ExtensionModule)
        self.modules[modname] = ext_module

    @stringArgs
    @noKwargs
    def func_import(self, node, args, kwargs):
        if len(args) != 1:
            raise InvalidCode('Import takes one argument.')
        modname = args[0]
        if modname.startswith('unstable-'):
            plainname = modname.split('-', 1)[1]
            try:
                # check if stable module exists
                self.import_module(plainname)
                mlog.warning('Module %s is now stable, please use the %s module instead.' % (modname, plainname))
                modname = plainname
            except InvalidArguments:
                mlog.warning('Module %s has no backwards or forwards compatibility and might not exist in future releases.' % modname, location=node)
                modname = 'unstable_' + plainname
        self.import_module(modname)
        return ModuleHolder(modname, self.modules[modname], self)

    @stringArgs
    @noKwargs
    def func_files(self, node, args, kwargs):
        return [mesonlib.File.from_source_file(self.environment.source_dir, self.subdir, fname) for fname in args]

    # Used by declare_dependency() and pkgconfig.generate()
    def extract_variables(self, kwargs, argname='variables', list_new=False, dict_new=False):
        variables = kwargs.get(argname, {})
        if isinstance(variables, dict):
            if dict_new and variables:
                FeatureNew.single_use('variables as dictionary', '0.56.0', self.subproject)
        else:
            varlist = mesonlib.stringlistify(variables)
            if list_new:
                FeatureNew.single_use('variables as list of strings', '0.56.0', self.subproject)
            variables = {}
            for v in varlist:
                try:
                    (key, value) = v.split('=', 1)
                except ValueError:
                    raise InterpreterException('Variable {!r} must have a value separated by equals sign.'.format(v))
                variables[key.strip()] = value.strip()
        for k, v in variables.items():
            if not k or not v:
                raise InterpreterException('Empty variable name or value')
            if any(c.isspace() for c in k):
                raise InterpreterException('Invalid whitespace in variable name "{}"'.format(k))
            if not isinstance(v, str):
                raise InterpreterException('variables values must be strings.')
        return variables

    @FeatureNewKwargs('declare_dependency', '0.46.0', ['link_whole'])
    @FeatureNewKwargs('declare_dependency', '0.54.0', ['variables'])
    @permittedKwargs(permitted_kwargs['declare_dependency'])
    @noPosargs
    def func_declare_dependency(self, node, args, kwargs):
        version = kwargs.get('version', self.project_version)
        if not isinstance(version, str):
            raise InterpreterException('Version must be a string.')
        incs = self.extract_incdirs(kwargs)
        libs = unholder(extract_as_list(kwargs, 'link_with'))
        libs_whole = unholder(extract_as_list(kwargs, 'link_whole'))
        sources = extract_as_list(kwargs, 'sources')
        sources = unholder(listify(self.source_strings_to_files(sources)))
        deps = unholder(extract_as_list(kwargs, 'dependencies'))
        compile_args = mesonlib.stringlistify(kwargs.get('compile_args', []))
        link_args = mesonlib.stringlistify(kwargs.get('link_args', []))
        variables = self.extract_variables(kwargs, list_new=True)
        final_deps = []
        for d in deps:
            try:
                d = d.held_object
            except Exception:
                pass
            if not isinstance(d, (dependencies.Dependency, dependencies.ExternalLibrary, dependencies.InternalDependency)):
                raise InterpreterException('Dependencies must be external deps')
            final_deps.append(d)
        for l in libs:
            if isinstance(l, dependencies.Dependency):
                raise InterpreterException('''Entries in "link_with" may only be self-built targets,
external dependencies (including libraries) must go to "dependencies".''')
        dep = dependencies.InternalDependency(version, incs, compile_args,
                                              link_args, libs, libs_whole, sources, final_deps,
                                              variables)
        return DependencyHolder(dep, self.subproject)

    @noKwargs
    def func_assert(self, node, args, kwargs):
        if len(args) == 1:
            FeatureNew.single_use('assert function without message argument', '0.53.0', self.subproject)
            value = args[0]
            message = None
        elif len(args) == 2:
            value, message = args
            if not isinstance(message, str):
                raise InterpreterException('Assert message not a string.')
        else:
            raise InterpreterException('Assert takes between one and two arguments')
        if not isinstance(value, bool):
            raise InterpreterException('Assert value not bool.')
        if not value:
            if message is None:
                from .ast import AstPrinter
                printer = AstPrinter()
                node.args.arguments[0].accept(printer)
                message = printer.result
            raise InterpreterException('Assert failed: ' + message)

    def validate_arguments(self, args, argcount, arg_types):
        if argcount is not None:
            if argcount != len(args):
                raise InvalidArguments('Expected %d arguments, got %d.' %
                                       (argcount, len(args)))
        for actual, wanted in zip(args, arg_types):
            if wanted is not None:
                if not isinstance(actual, wanted):
                    raise InvalidArguments('Incorrect argument type.')

    @FeatureNewKwargs('run_command', '0.50.0', ['env'])
    @FeatureNewKwargs('run_command', '0.47.0', ['check', 'capture'])
    @permittedKwargs(permitted_kwargs['run_command'])
    def func_run_command(self, node, args, kwargs):
        return self.run_command_impl(node, args, kwargs)

    def run_command_impl(self, node, args, kwargs, in_builddir=False):
        if len(args) < 1:
            raise InterpreterException('Not enough arguments')
        cmd, *cargs = args
        capture = kwargs.get('capture', True)
        srcdir = self.environment.get_source_dir()
        builddir = self.environment.get_build_dir()

        check = kwargs.get('check', False)
        if not isinstance(check, bool):
            raise InterpreterException('Check must be boolean.')

        env = self.unpack_env_kwarg(kwargs)

        m = 'must be a string, or the output of find_program(), files() '\
            'or configure_file(), or a compiler object; not {!r}'
        expanded_args = []
        if isinstance(cmd, ExternalProgramHolder):
            cmd = cmd.held_object
            if isinstance(cmd, build.Executable):
                progname = node.args.arguments[0].value
                msg = 'Program {!r} was overridden with the compiled executable {!r}'\
                      ' and therefore cannot be used during configuration'
                raise InterpreterException(msg.format(progname, cmd.description()))
            if not cmd.found():
                raise InterpreterException('command {!r} not found or not executable'.format(cmd.get_name()))
        elif isinstance(cmd, CompilerHolder):
            exelist = cmd.compiler.get_exelist()
            cmd = exelist[0]
            prog = ExternalProgram(cmd, silent=True)
            if not prog.found():
                raise InterpreterException('Program {!r} not found '
                                           'or not executable'.format(cmd))
            cmd = prog
            expanded_args = exelist[1:]
        else:
            if isinstance(cmd, mesonlib.File):
                cmd = cmd.absolute_path(srcdir, builddir)
            elif not isinstance(cmd, str):
                raise InterpreterException('First argument ' + m.format(cmd))
            # Prefer scripts in the current source directory
            search_dir = os.path.join(srcdir, self.subdir)
            prog = ExternalProgram(cmd, silent=True, search_dir=search_dir)
            if not prog.found():
                raise InterpreterException('Program or command {!r} not found '
                                           'or not executable'.format(cmd))
            cmd = prog
        for a in listify(cargs):
            if isinstance(a, str):
                expanded_args.append(a)
            elif isinstance(a, mesonlib.File):
                expanded_args.append(a.absolute_path(srcdir, builddir))
            elif isinstance(a, ExternalProgramHolder):
                expanded_args.append(a.held_object.get_path())
            else:
                raise InterpreterException('Arguments ' + m.format(a))
        # If any file that was used as an argument to the command
        # changes, we must re-run the configuration step.
        self.add_build_def_file(cmd.get_path())
        for a in expanded_args:
            if not os.path.isabs(a):
                a = os.path.join(builddir if in_builddir else srcdir, self.subdir, a)
            self.add_build_def_file(a)
        return RunProcess(cmd, expanded_args, env, srcdir, builddir, self.subdir,
                          self.environment.get_build_command() + ['introspect'],
                          in_builddir=in_builddir, check=check, capture=capture)

    @stringArgs
    def func_gettext(self, nodes, args, kwargs):
        raise InterpreterException('Gettext() function has been moved to module i18n. Import it and use i18n.gettext() instead')

    def func_option(self, nodes, args, kwargs):
        raise InterpreterException('Tried to call option() in build description file. All options must be in the option file.')

    @FeatureNewKwargs('subproject', '0.38.0', ['default_options'])
    @permittedKwargs(permitted_kwargs['subproject'])
    @stringArgs
    def func_subproject(self, nodes, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Subproject takes exactly one argument')
        subp_name = args[0]
        return self.do_subproject(subp_name, 'meson', kwargs)

    def disabled_subproject(self, subp_name, disabled_feature=None, exception=None):
        sub = SubprojectHolder(None, os.path.join(self.subproject_dir, subp_name),
                               disabled_feature=disabled_feature, exception=exception)
        self.subprojects[subp_name] = sub
        return sub

    def get_subproject(self, subp_name):
        sub = self.subprojects.get(subp_name)
        if sub and sub.found():
            return sub
        return None

    def do_subproject(self, subp_name: str, method: str, kwargs):
        disabled, required, feature = extract_required_kwarg(kwargs, self.subproject)
        if disabled:
            mlog.log('Subproject', mlog.bold(subp_name), ':', 'skipped: feature', mlog.bold(feature), 'disabled')
            return self.disabled_subproject(subp_name, disabled_feature=feature)

        default_options = mesonlib.stringlistify(kwargs.get('default_options', []))
        default_options = coredata.create_options_dict(default_options)

        if subp_name == '':
            raise InterpreterException('Subproject name must not be empty.')
        if subp_name[0] == '.':
            raise InterpreterException('Subproject name must not start with a period.')
        if '..' in subp_name:
            raise InterpreterException('Subproject name must not contain a ".." path segment.')
        if os.path.isabs(subp_name):
            raise InterpreterException('Subproject name must not be an absolute path.')
        if has_path_sep(subp_name):
            mlog.warning('Subproject name has a path separator. This may cause unexpected behaviour.',
                         location=self.current_node)
        if subp_name in self.subproject_stack:
            fullstack = self.subproject_stack + [subp_name]
            incpath = ' => '.join(fullstack)
            raise InvalidCode('Recursive include of subprojects: %s.' % incpath)
        if subp_name in self.subprojects:
            subproject = self.subprojects[subp_name]
            if required and not subproject.found():
                raise InterpreterException('Subproject "%s" required but not found.' % (subproject.subdir))
            return subproject

        r = self.environment.wrap_resolver
        try:
            subdir = r.resolve(subp_name, method, self.subproject)
        except wrap.WrapException as e:
            if not required:
                mlog.log(e)
                mlog.log('Subproject ', mlog.bold(subp_name), 'is buildable:', mlog.red('NO'), '(disabling)')
                return self.disabled_subproject(subp_name, exception=e)
            raise e

        subdir_abs = os.path.join(self.environment.get_source_dir(), subdir)
        os.makedirs(os.path.join(self.build.environment.get_build_dir(), subdir), exist_ok=True)
        self.global_args_frozen = True

        mlog.log()
        with mlog.nested():
            mlog.log('Executing subproject', mlog.bold(subp_name), 'method', mlog.bold(method), '\n')
        try:
            if method == 'meson':
                return self._do_subproject_meson(subp_name, subdir, default_options, kwargs)
            elif method == 'cmake':
                return self._do_subproject_cmake(subp_name, subdir, subdir_abs, default_options, kwargs)
            else:
                raise InterpreterException('The method {} is invalid for the subproject {}'.format(method, subp_name))
        # Invalid code is always an error
        except InvalidCode:
            raise
        except Exception as e:
            if not required:
                with mlog.nested():
                    # Suppress the 'ERROR:' prefix because this exception is not
                    # fatal and VS CI treat any logs with "ERROR:" as fatal.
                    mlog.exception(e, prefix=mlog.yellow('Exception:'))
                mlog.log('\nSubproject', mlog.bold(subdir), 'is buildable:', mlog.red('NO'), '(disabling)')
                return self.disabled_subproject(subp_name, exception=e)
            raise e

    def _do_subproject_meson(self, subp_name, subdir, default_options, kwargs, ast=None, build_def_files=None):
        with mlog.nested():
            new_build = self.build.copy()
            subi = Interpreter(new_build, self.backend, subp_name, subdir, self.subproject_dir,
                               self.modules, default_options, ast=ast)
            subi.subprojects = self.subprojects

            subi.subproject_stack = self.subproject_stack + [subp_name]
            current_active = self.active_projectname
            current_warnings_counter = mlog.log_warnings_counter
            mlog.log_warnings_counter = 0
            subi.run()
            subi_warnings = mlog.log_warnings_counter
            mlog.log_warnings_counter = current_warnings_counter

            mlog.log('Subproject', mlog.bold(subp_name), 'finished.')

        mlog.log()

        if 'version' in kwargs:
            pv = subi.project_version
            wanted = kwargs['version']
            if pv == 'undefined' or not mesonlib.version_compare_many(pv, wanted)[0]:
                raise InterpreterException('Subproject %s version is %s but %s required.' % (subp_name, pv, wanted))
        self.active_projectname = current_active
        self.subprojects.update(subi.subprojects)
        self.subprojects[subp_name] = SubprojectHolder(subi, subdir, warnings=subi_warnings)
        # Duplicates are possible when subproject uses files from project root
        if build_def_files:
            self.build_def_files = list(set(self.build_def_files + build_def_files))
        else:
            self.build_def_files = list(set(self.build_def_files + subi.build_def_files))
        self.build.merge(subi.build)
        self.build.subprojects[subp_name] = subi.project_version
        self.summary.update(subi.summary)
        return self.subprojects[subp_name]

    def _do_subproject_cmake(self, subp_name, subdir, subdir_abs, default_options, kwargs):
        with mlog.nested():
            new_build = self.build.copy()
            prefix = self.coredata.builtins['prefix'].value

            from .modules.cmake import CMakeSubprojectOptions
            options = kwargs.get('options', CMakeSubprojectOptions())
            if not isinstance(options, CMakeSubprojectOptions):
                raise InterpreterException('"options" kwarg must be CMakeSubprojectOptions'
                                           ' object (created by cmake.subproject_options())')

            cmake_options = mesonlib.stringlistify(kwargs.get('cmake_options', []))
            cmake_options += options.cmake_options
            cm_int = CMakeInterpreter(new_build, Path(subdir), Path(subdir_abs), Path(prefix), new_build.environment, self.backend)
            cm_int.initialise(cmake_options)
            cm_int.analyse()

            # Generate a meson ast and execute it with the normal do_subproject_meson
            ast = cm_int.pretend_to_be_meson(options.target_options)

            mlog.log()
            with mlog.nested():
                mlog.log('Processing generated meson AST')

                # Debug print the generated meson file
                from .ast import AstIndentationGenerator, AstPrinter
                printer = AstPrinter()
                ast.accept(AstIndentationGenerator())
                ast.accept(printer)
                printer.post_process()
                meson_filename = os.path.join(self.build.environment.get_build_dir(), subdir, 'meson.build')
                with open(meson_filename, "w") as f:
                    f.write(printer.result)

                mlog.log('Build file:', meson_filename)
                mlog.cmd_ci_include(meson_filename)
                mlog.log()

            result = self._do_subproject_meson(subp_name, subdir, default_options, kwargs, ast, cm_int.bs_files)
            result.cm_interpreter = cm_int

        mlog.log()
        return result

    def get_option_internal(self, optname):
        raw_optname = optname
        if self.is_subproject():
            optname = self.subproject + ':' + optname


        for opts in [
                self.coredata.base_options, compilers.base_options, self.coredata.builtins,
                dict(self.coredata.get_prefixed_options_per_machine(self.coredata.builtins_per_machine)),
                dict(self.coredata.flatten_lang_iterator(
                    self.coredata.get_prefixed_options_per_machine(self.coredata.compiler_options))),
        ]:
            v = opts.get(optname)
            if v is None or v.yielding:
                v = opts.get(raw_optname)
            if v is not None:
                return v

        try:
            opt = self.coredata.user_options[optname]
            if opt.yielding and ':' in optname and raw_optname in self.coredata.user_options:
                popt = self.coredata.user_options[raw_optname]
                if type(opt) is type(popt):
                    opt = popt
                else:
                    # Get class name, then option type as a string
                    opt_type = opt.__class__.__name__[4:][:-6].lower()
                    popt_type = popt.__class__.__name__[4:][:-6].lower()
                    # This is not a hard error to avoid dependency hell, the workaround
                    # when this happens is to simply set the subproject's option directly.
                    mlog.warning('Option {0!r} of type {1!r} in subproject {2!r} cannot yield '
                                 'to parent option of type {3!r}, ignoring parent value. '
                                 'Use -D{2}:{0}=value to set the value for this option manually'
                                 '.'.format(raw_optname, opt_type, self.subproject, popt_type),
                                 location=self.current_node)
            return opt
        except KeyError:
            pass

        raise InterpreterException('Tried to access unknown option "%s".' % optname)

    @stringArgs
    @noKwargs
    def func_get_option(self, nodes, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Argument required for get_option.')
        optname = args[0]
        if ':' in optname:
            raise InterpreterException('Having a colon in option name is forbidden, '
                                       'projects are not allowed to directly access '
                                       'options of other subprojects.')
        opt = self.get_option_internal(optname)
        if isinstance(opt, coredata.UserFeatureOption):
            return FeatureOptionHolder(self.environment, optname, opt)
        elif isinstance(opt, coredata.UserOption):
            return opt.value
        return opt

    @noKwargs
    def func_configuration_data(self, node, args, kwargs):
        if len(args) > 1:
            raise InterpreterException('configuration_data takes only one optional positional arguments')
        elif len(args) == 1:
            FeatureNew.single_use('configuration_data dictionary', '0.49.0', self.subproject)
            initial_values = args[0]
            if not isinstance(initial_values, dict):
                raise InterpreterException('configuration_data first argument must be a dictionary')
        else:
            initial_values = {}
        return ConfigurationDataHolder(self.subproject, initial_values)

    def set_backend(self):
        # The backend is already set when parsing subprojects
        if self.backend is not None:
            return
        backend = self.coredata.get_builtin_option('backend')
        from .backend import backends
        self.backend = backends.get_backend_from_name(backend, self.build, self)

        if self.backend is None:
            raise InterpreterException('Unknown backend "%s".' % backend)
        if backend != self.backend.name:
            if self.backend.name.startswith('vs'):
                mlog.log('Auto detected Visual Studio backend:', mlog.bold(self.backend.name))
            self.coredata.set_builtin_option('backend', self.backend.name)

        # Only init backend options on first invocation otherwise it would
        # override values previously set from command line.
        if self.environment.first_invocation:
            self.coredata.init_backend_options(backend)

        options = {k: v for k, v in self.environment.raw_options.items() if k.startswith('backend_')}
        self.coredata.set_options(options)

    @stringArgs
    @permittedKwargs(permitted_kwargs['project'])
    def func_project(self, node, args, kwargs):
        if len(args) < 1:
            raise InvalidArguments('Not enough arguments to project(). Needs at least the project name.')
        proj_name, *proj_langs = args
        if ':' in proj_name:
            raise InvalidArguments("Project name {!r} must not contain ':'".format(proj_name))

        # This needs to be evaluated as early as possible, as meson uses this
        # for things like deprecation testing.
        if 'meson_version' in kwargs:
            cv = coredata.version
            pv = kwargs['meson_version']
            if not mesonlib.version_compare(cv, pv):
                raise InterpreterException('Meson version is %s but project requires %s' % (cv, pv))
            mesonlib.project_meson_versions[self.subproject] = kwargs['meson_version']

        if os.path.exists(self.option_file):
            oi = optinterpreter.OptionInterpreter(self.subproject)
            oi.process(self.option_file)
            self.coredata.merge_user_options(oi.options)
            self.add_build_def_file(self.option_file)

        # Do not set default_options on reconfigure otherwise it would override
        # values previously set from command line. That means that changing
        # default_options in a project will trigger a reconfigure but won't
        # have any effect.
        self.project_default_options = mesonlib.stringlistify(kwargs.get('default_options', []))
        self.project_default_options = coredata.create_options_dict(self.project_default_options)
        if self.environment.first_invocation:
            default_options = self.project_default_options.copy()
            default_options.update(self.default_project_options)
            self.coredata.init_builtins(self.subproject)
        else:
            default_options = {}
        self.coredata.set_default_options(default_options, self.subproject, self.environment)

        if not self.is_subproject():
            self.build.project_name = proj_name
        self.active_projectname = proj_name
        self.project_version = kwargs.get('version', 'undefined')
        if self.build.project_version is None:
            self.build.project_version = self.project_version
        proj_license = mesonlib.stringlistify(kwargs.get('license', 'unknown'))
        self.build.dep_manifest[proj_name] = {'version': self.project_version,
                                              'license': proj_license}
        if self.subproject in self.build.projects:
            raise InvalidCode('Second call to project().')

        # spdirname is the subproject_dir for this project, relative to self.subdir.
        # self.subproject_dir is the subproject_dir for the main project, relative to top source dir.
        spdirname = kwargs.get('subproject_dir')
        if spdirname:
            if not isinstance(spdirname, str):
                raise InterpreterException('Subproject_dir must be a string')
            if os.path.isabs(spdirname):
                raise InterpreterException('Subproject_dir must not be an absolute path.')
            if spdirname.startswith('.'):
                raise InterpreterException('Subproject_dir must not begin with a period.')
            if '..' in spdirname:
                raise InterpreterException('Subproject_dir must not contain a ".." segment.')
            if not self.is_subproject():
                self.subproject_dir = spdirname
        else:
            spdirname = 'subprojects'
        self.build.subproject_dir = self.subproject_dir

        # Load wrap files from this (sub)project.
        wrap_mode = self.coredata.get_builtin_option('wrap_mode')
        if not self.is_subproject() or wrap_mode != WrapMode.nopromote:
            subdir = os.path.join(self.subdir, spdirname)
            r = wrap.Resolver(self.environment.get_source_dir(), subdir, wrap_mode)
            if self.is_subproject():
                self.environment.wrap_resolver.merge_wraps(r)
            else:
                self.environment.wrap_resolver = r

        self.build.projects[self.subproject] = proj_name
        mlog.log('Project name:', mlog.bold(proj_name))
        mlog.log('Project version:', mlog.bold(self.project_version))

        self.add_languages(proj_langs, True, MachineChoice.HOST)
        self.add_languages(proj_langs, False, MachineChoice.BUILD)

        self.set_backend()
        if not self.is_subproject():
            self.check_stdlibs()

    @FeatureNewKwargs('add_languages', '0.54.0', ['native'])
    @permittedKwargs(permitted_kwargs['add_languages'])
    @stringArgs
    def func_add_languages(self, node, args, kwargs):
        disabled, required, feature = extract_required_kwarg(kwargs, self.subproject)
        if disabled:
            for lang in sorted(args, key=compilers.sort_clink):
                mlog.log('Compiler for language', mlog.bold(lang), 'skipped: feature', mlog.bold(feature), 'disabled')
            return False
        if 'native' in kwargs:
            return self.add_languages(args, required, self.machine_from_native_kwarg(kwargs))
        else:
            # absent 'native' means 'both' for backwards compatibility
            tv = FeatureNew.get_target_version(self.subproject)
            if FeatureNew.check_version(tv, '0.54.0'):
                mlog.warning('add_languages is missing native:, assuming languages are wanted for both host and build.',
                             location=self.current_node)

            success = self.add_languages(args, False, MachineChoice.BUILD)
            success &= self.add_languages(args, required, MachineChoice.HOST)
            return success

    def get_message_string_arg(self, arg):
        if isinstance(arg, list):
            argstr = stringifyUserArguments(arg)
        elif isinstance(arg, dict):
            argstr = stringifyUserArguments(arg)
        elif isinstance(arg, str):
            argstr = arg
        elif isinstance(arg, int):
            argstr = str(arg)
        else:
            raise InvalidArguments('Function accepts only strings, integers, lists and lists thereof.')

        return argstr

    @noArgsFlattening
    @noKwargs
    def func_message(self, node, args, kwargs):
        if len(args) > 1:
            FeatureNew.single_use('message with more than one argument', '0.54.0', self.subproject)
        args_str = [self.get_message_string_arg(i) for i in args]
        self.message_impl(args_str)

    def message_impl(self, args):
        mlog.log(mlog.bold('Message:'), *args)

    @noArgsFlattening
    @FeatureNewKwargs('summary', '0.54.0', ['list_sep'])
    @permittedKwargs({'section', 'bool_yn', 'list_sep'})
    @FeatureNew('summary', '0.53.0')
    def func_summary(self, node, args, kwargs):
        if len(args) == 1:
            if not isinstance(args[0], dict):
                raise InterpreterException('Summary first argument must be dictionary.')
            values = args[0]
        elif len(args) == 2:
            if not isinstance(args[0], str):
                raise InterpreterException('Summary first argument must be string.')
            values = {args[0]: args[1]}
        else:
            raise InterpreterException('Summary accepts at most 2 arguments.')
        section = kwargs.get('section', '')
        if not isinstance(section, str):
            raise InterpreterException('Summary\'s section keyword argument must be string.')
        self.summary_impl(section, values, kwargs)

    def summary_impl(self, section, values, kwargs):
        if self.subproject not in self.summary:
            self.summary[self.subproject] = Summary(self.active_projectname, self.project_version)
        self.summary[self.subproject].add_section(section, values, kwargs)

    def _print_summary(self):
        # Add automatic 'Supbrojects' section in main project.
        all_subprojects = collections.OrderedDict()
        for name, subp in sorted(self.subprojects.items()):
            value = subp.found()
            if subp.disabled_feature:
                value = [value, 'Feature {!r} disabled'.format(subp.disabled_feature)]
            elif subp.exception:
                value = [value, str(subp.exception)]
            elif subp.warnings > 0:
                value = [value, '{} warnings'.format(subp.warnings)]
            all_subprojects[name] = value
        if all_subprojects:
            self.summary_impl('Subprojects', all_subprojects,
                              {'bool_yn': True,
                               'list_sep': ' ',
                              })
        # Print all summaries, main project last.
        mlog.log('')  # newline
        main_summary = self.summary.pop('', None)
        for _, summary in sorted(self.summary.items()):
            summary.dump()
        if main_summary:
            main_summary.dump()

    @noArgsFlattening
    @FeatureNew('warning', '0.44.0')
    @noKwargs
    def func_warning(self, node, args, kwargs):
        if len(args) > 1:
            FeatureNew.single_use('warning with more than one argument', '0.54.0', self.subproject)
        args_str = [self.get_message_string_arg(i) for i in args]
        mlog.warning(*args_str, location=node)

    @noKwargs
    def func_error(self, node, args, kwargs):
        self.validate_arguments(args, 1, [str])
        raise InterpreterException('Problem encountered: ' + args[0])

    @noKwargs
    def func_exception(self, node, args, kwargs):
        self.validate_arguments(args, 0, [])
        raise Exception()

    def add_languages(self, args: T.Sequence[str], required: bool, for_machine: MachineChoice) -> bool:
        success = self.add_languages_for(args, required, for_machine)
        if not self.coredata.is_cross_build():
            self.coredata.copy_build_options_from_regular_ones()
        self._redetect_machines()
        return success

    def should_skip_sanity_check(self, for_machine: MachineChoice) -> bool:
        should = self.environment.properties.host.get('skip_sanity_check', False)
        if not isinstance(should, bool):
            raise InterpreterException('Option skip_sanity_check must be a boolean.')
        if for_machine != MachineChoice.HOST and not should:
            return False
        if not self.environment.is_cross_build() and not should:
            return False
        return should

    def add_languages_for(self, args, required, for_machine: MachineChoice):
        args = [a.lower() for a in args]
        langs = set(self.coredata.compilers[for_machine].keys())
        langs.update(args)
        if 'vala' in langs:
            if 'c' not in langs:
                raise InterpreterException('Compiling Vala requires C. Add C to your project languages and rerun Meson.')

        success = True
        for lang in sorted(args, key=compilers.sort_clink):
            clist = self.coredata.compilers[for_machine]
            machine_name = for_machine.get_lower_case_name()
            if lang in clist:
                comp = clist[lang]
            else:
                try:
                    comp = self.environment.detect_compiler_for(lang, for_machine)
                    if comp is None:
                        raise InvalidArguments('Tried to use unknown language "%s".' % lang)
                    if self.should_skip_sanity_check(for_machine):
                        mlog.log_once('Cross compiler sanity tests disabled via the cross file.')
                    else:
                        comp.sanity_check(self.environment.get_scratch_dir(), self.environment)
                except Exception:
                    if not required:
                        mlog.log('Compiler for language',
                                 mlog.bold(lang), 'for the', machine_name,
                                 'machine not found.')
                        success = False
                        continue
                    else:
                        raise

            if for_machine == MachineChoice.HOST or self.environment.is_cross_build():
                logger_fun = mlog.log
            else:
                logger_fun = mlog.debug
            logger_fun(comp.get_display_language(), 'compiler for the', machine_name, 'machine:',
                       mlog.bold(' '.join(comp.get_exelist())), comp.get_version_string())
            if comp.linker is not None:
                logger_fun(comp.get_display_language(), 'linker for the', machine_name, 'machine:',
                           mlog.bold(' '.join(comp.linker.get_exelist())), comp.linker.id, comp.linker.version)
            self.build.ensure_static_linker(comp)

        return success

    def program_from_file_for(self, for_machine, prognames):
        for p in unholder(prognames):
            if isinstance(p, mesonlib.File):
                continue # Always points to a local (i.e. self generated) file.
            if not isinstance(p, str):
                raise InterpreterException('Executable name must be a string')
            prog = ExternalProgram.from_bin_list(self.environment, for_machine, p)
            if prog.found():
                return ExternalProgramHolder(prog, self.subproject)
        return None

    def program_from_system(self, args, search_dirs, extra_info):
        # Search for scripts relative to current subdir.
        # Do not cache found programs because find_program('foobar')
        # might give different results when run from different source dirs.
        source_dir = os.path.join(self.environment.get_source_dir(), self.subdir)
        for exename in args:
            if isinstance(exename, mesonlib.File):
                if exename.is_built:
                    search_dir = os.path.join(self.environment.get_build_dir(),
                                              exename.subdir)
                else:
                    search_dir = os.path.join(self.environment.get_source_dir(),
                                              exename.subdir)
                exename = exename.fname
                extra_search_dirs = []
            elif isinstance(exename, str):
                search_dir = source_dir
                extra_search_dirs = search_dirs
            else:
                raise InvalidArguments('find_program only accepts strings and '
                                       'files, not {!r}'.format(exename))
            extprog = dependencies.ExternalProgram(exename, search_dir=search_dir,
                                                   extra_search_dirs=extra_search_dirs,
                                                   silent=True)
            progobj = ExternalProgramHolder(extprog, self.subproject)
            if progobj.found():
                extra_info.append('({})'.format(' '.join(progobj.get_command())))
                return progobj

    def program_from_overrides(self, command_names, extra_info):
        for name in command_names:
            if not isinstance(name, str):
                continue
            if name in self.build.find_overrides:
                exe = self.build.find_overrides[name]
                extra_info.append(mlog.blue('(overriden)'))
                return ExternalProgramHolder(exe, self.subproject, self.backend)
        return None

    def store_name_lookups(self, command_names):
        for name in command_names:
            if isinstance(name, str):
                self.build.searched_programs.add(name)

    def add_find_program_override(self, name, exe):
        if name in self.build.searched_programs:
            raise InterpreterException('Tried to override finding of executable "%s" which has already been found.'
                                       % name)
        if name in self.build.find_overrides:
            raise InterpreterException('Tried to override executable "%s" which has already been overridden.'
                                       % name)
        self.build.find_overrides[name] = exe

    def notfound_program(self, args):
        return ExternalProgramHolder(dependencies.NonExistingExternalProgram(' '.join(args)), self.subproject)

    # TODO update modules to always pass `for_machine`. It is bad-form to assume
    # the host machine.
    def find_program_impl(self, args, for_machine: MachineChoice = MachineChoice.HOST,
                          required=True, silent=True, wanted='', search_dirs=None,
                          version_func=None):
        args = mesonlib.listify(args)

        extra_info = []
        progobj = self.program_lookup(args, for_machine, required, search_dirs, extra_info)
        if progobj is None:
            progobj = self.notfound_program(args)

        if not progobj.found():
            mlog.log('Program', mlog.bold(progobj.get_name()), 'found:', mlog.red('NO'))
            if required:
                m = 'Program {!r} not found'
                raise InterpreterException(m.format(progobj.get_name()))
            return progobj

        if wanted:
            if version_func:
                version = version_func(progobj)
            else:
                version = progobj.get_version(self)
            is_found, not_found, found = mesonlib.version_compare_many(version, wanted)
            if not is_found:
                mlog.log('Program', mlog.bold(progobj.get_name()), 'found:', mlog.red('NO'),
                         'found', mlog.normal_cyan(version), 'but need:',
                         mlog.bold(', '.join(["'{}'".format(e) for e in not_found])), *extra_info)
                if required:
                    m = 'Invalid version of program, need {!r} {!r} found {!r}.'
                    raise InterpreterException(m.format(progobj.get_name(), not_found, version))
                return self.notfound_program(args)
            extra_info.insert(0, mlog.normal_cyan(version))

        # Only store successful lookups
        self.store_name_lookups(args)
        mlog.log('Program', mlog.bold(progobj.get_name()), 'found:', mlog.green('YES'), *extra_info)
        return progobj

    def program_lookup(self, args, for_machine, required, search_dirs, extra_info):
        progobj = self.program_from_overrides(args, extra_info)
        if progobj:
            return progobj

        fallback = None
        wrap_mode = self.coredata.get_builtin_option('wrap_mode')
        if wrap_mode != WrapMode.nofallback and self.environment.wrap_resolver:
            fallback = self.environment.wrap_resolver.find_program_provider(args)
        if fallback and wrap_mode == WrapMode.forcefallback:
            return self.find_program_fallback(fallback, args, required, extra_info)

        progobj = self.program_from_file_for(for_machine, args)
        if progobj is None:
            progobj = self.program_from_system(args, search_dirs, extra_info)
        if progobj is None and args[0].endswith('python3'):
            prog = dependencies.ExternalProgram('python3', mesonlib.python_command, silent=True)
            progobj = ExternalProgramHolder(prog, self.subproject) if prog.found() else None
        if progobj is None and fallback and required:
            progobj = self.find_program_fallback(fallback, args, required, extra_info)

        return progobj

    def find_program_fallback(self, fallback, args, required, extra_info):
        mlog.log('Fallback to subproject', mlog.bold(fallback), 'which provides program',
                 mlog.bold(' '.join(args)))
        sp_kwargs = { 'required': required }
        self.do_subproject(fallback, 'meson', sp_kwargs)
        return self.program_from_overrides(args, extra_info)

    @FeatureNewKwargs('find_program', '0.53.0', ['dirs'])
    @FeatureNewKwargs('find_program', '0.52.0', ['version'])
    @FeatureNewKwargs('find_program', '0.49.0', ['disabler'])
    @disablerIfNotFound
    @permittedKwargs(permitted_kwargs['find_program'])
    def func_find_program(self, node, args, kwargs):
        if not args:
            raise InterpreterException('No program name specified.')

        disabled, required, feature = extract_required_kwarg(kwargs, self.subproject)
        if disabled:
            mlog.log('Program', mlog.bold(' '.join(args)), 'skipped: feature', mlog.bold(feature), 'disabled')
            return self.notfound_program(args)

        search_dirs = extract_search_dirs(kwargs)
        wanted = mesonlib.stringlistify(kwargs.get('version', []))
        for_machine = self.machine_from_native_kwarg(kwargs)
        return self.find_program_impl(args, for_machine, required=required,
                                      silent=False, wanted=wanted,
                                      search_dirs=search_dirs)

    def func_find_library(self, node, args, kwargs):
        raise InvalidCode('find_library() is removed, use meson.get_compiler(\'name\').find_library() instead.\n'
                          'Look here for documentation: http://mesonbuild.com/Reference-manual.html#compiler-object\n'
                          'Look here for example: http://mesonbuild.com/howtox.html#add-math-library-lm-portably\n'
                          )

    def _find_cached_dep(self, name, display_name, kwargs):
        # Check if we want this as a build-time / build machine or runt-time /
        # host machine dep.
        for_machine = self.machine_from_native_kwarg(kwargs)
        identifier = dependencies.get_dep_identifier(name, kwargs)
        wanted_vers = mesonlib.stringlistify(kwargs.get('version', []))

        override = self.build.dependency_overrides[for_machine].get(identifier)
        if override:
            info = [mlog.blue('(overridden)' if override.explicit else '(cached)')]
            cached_dep = override.dep
            # We don't implicitly override not-found dependencies, but user could
            # have explicitly called meson.override_dependency() with a not-found
            # dep.
            if not cached_dep.found():
                mlog.log('Dependency', mlog.bold(display_name),
                         'found:', mlog.red('NO'), *info)
                return identifier, cached_dep
            found_vers = cached_dep.get_version()
            if not self.check_version(wanted_vers, found_vers):
                mlog.log('Dependency', mlog.bold(name),
                         'found:', mlog.red('NO'),
                         'found', mlog.normal_cyan(found_vers), 'but need:',
                         mlog.bold(', '.join(["'{}'".format(e) for e in wanted_vers])),
                         *info)
                return identifier, NotFoundDependency(self.environment)
        else:
            info = [mlog.blue('(cached)')]
            cached_dep = self.coredata.deps[for_machine].get(identifier)
            if cached_dep:
                found_vers = cached_dep.get_version()
                if not self.check_version(wanted_vers, found_vers):
                    return identifier, None

        if cached_dep:
            if found_vers:
                info = [mlog.normal_cyan(found_vers), *info]
            mlog.log('Dependency', mlog.bold(display_name),
                     'found:', mlog.green('YES'), *info)
            return identifier, cached_dep

        return identifier, None

    @staticmethod
    def check_version(wanted, found):
        if not wanted:
            return True
        if found == 'undefined' or not mesonlib.version_compare_many(found, wanted)[0]:
            return False
        return True

    def notfound_dependency(self):
        return DependencyHolder(NotFoundDependency(self.environment), self.subproject)

    def verify_fallback_consistency(self, subp_name, varname, cached_dep):
        subi = self.get_subproject(subp_name)
        if not cached_dep or not varname or not subi or not cached_dep.found():
            return
        dep = subi.get_variable_method([varname], {})
        if dep.held_object != cached_dep:
            m = 'Inconsistency: Subproject has overridden the dependency with another variable than {!r}'
            raise DependencyException(m.format(varname))

    def get_subproject_dep(self, name, display_name, subp_name, varname, kwargs):
        required = kwargs.get('required', True)
        wanted = mesonlib.stringlistify(kwargs.get('version', []))
        dep = self.notfound_dependency()

        # Verify the subproject is found
        subproject = self.subprojects.get(subp_name)
        if not subproject or not subproject.found():
            mlog.log('Dependency', mlog.bold(display_name), 'from subproject',
                     mlog.bold(subproject.subdir), 'found:', mlog.red('NO'),
                     mlog.blue('(subproject failed to configure)'))
            if required:
                m = 'Subproject {} failed to configure for dependency {}'
                raise DependencyException(m.format(subproject.subdir, display_name))
            return dep

        extra_info = []
        try:
            # Check if the subproject overridden the dependency
            _, cached_dep = self._find_cached_dep(name, display_name, kwargs)
            if cached_dep:
                if varname:
                    self.verify_fallback_consistency(subp_name, varname, cached_dep)
                if required and not cached_dep.found():
                    m = 'Dependency {!r} is not satisfied'
                    raise DependencyException(m.format(display_name))
                return DependencyHolder(cached_dep, self.subproject)
            elif varname is None:
                mlog.log('Dependency', mlog.bold(display_name), 'from subproject',
                         mlog.bold(subproject.subdir), 'found:', mlog.red('NO'))
                if required:
                    m = 'Subproject {} did not override dependency {}'
                    raise DependencyException(m.format(subproject.subdir, display_name))
                return self.notfound_dependency()
            else:
                # The subproject did not override the dependency, but we know the
                # variable name to take.
                dep = subproject.get_variable_method([varname], {})
        except InvalidArguments:
            # This is raised by get_variable_method() if varname does no exist
            # in the subproject. Just add the reason in the not-found message
            # that will be printed later.
            extra_info.append(mlog.blue('(Variable {!r} not found)'.format(varname)))

        if not isinstance(dep, DependencyHolder):
            raise InvalidCode('Fetched variable {!r} in the subproject {!r} is '
                              'not a dependency object.'.format(varname, subp_name))

        if not dep.found():
            mlog.log('Dependency', mlog.bold(display_name), 'from subproject',
                     mlog.bold(subproject.subdir), 'found:', mlog.red('NO'), *extra_info)
            if required:
                raise DependencyException('Could not find dependency {} in subproject {}'
                                          ''.format(varname, subp_name))
            return dep

        found = dep.held_object.get_version()
        if not self.check_version(wanted, found):
            mlog.log('Dependency', mlog.bold(display_name), 'from subproject',
                     mlog.bold(subproject.subdir), 'found:', mlog.red('NO'),
                     'found', mlog.normal_cyan(found), 'but need:',
                     mlog.bold(', '.join(["'{}'".format(e) for e in wanted])))
            if required:
                raise DependencyException('Version {} of subproject dependency {} already '
                                          'cached, requested incompatible version {} for '
                                          'dep {}'.format(found, subp_name, wanted, display_name))
            return self.notfound_dependency()

        found = mlog.normal_cyan(found) if found else None
        mlog.log('Dependency', mlog.bold(display_name), 'from subproject',
                 mlog.bold(subproject.subdir), 'found:', mlog.green('YES'), found)
        return dep

    def _handle_featurenew_dependencies(self, name):
        'Do a feature check on dependencies used by this subproject'
        if name == 'mpi':
            FeatureNew.single_use('MPI Dependency', '0.42.0', self.subproject)
        elif name == 'pcap':
            FeatureNew.single_use('Pcap Dependency', '0.42.0', self.subproject)
        elif name == 'vulkan':
            FeatureNew.single_use('Vulkan Dependency', '0.42.0', self.subproject)
        elif name == 'libwmf':
            FeatureNew.single_use('LibWMF Dependency', '0.44.0', self.subproject)
        elif name == 'openmp':
            FeatureNew.single_use('OpenMP Dependency', '0.46.0', self.subproject)

    @FeatureNewKwargs('dependency', '0.54.0', ['components'])
    @FeatureNewKwargs('dependency', '0.52.0', ['include_type'])
    @FeatureNewKwargs('dependency', '0.50.0', ['not_found_message', 'cmake_module_path', 'cmake_args'])
    @FeatureNewKwargs('dependency', '0.49.0', ['disabler'])
    @FeatureNewKwargs('dependency', '0.40.0', ['method'])
    @FeatureNewKwargs('dependency', '0.38.0', ['default_options'])
    @disablerIfNotFound
    @permittedKwargs(permitted_kwargs['dependency'])
    def func_dependency(self, node, args, kwargs):
        self.validate_arguments(args, 1, [str])
        name = args[0]
        display_name = name if name else '(anonymous)'
        mods = extract_as_list(kwargs, 'modules')
        if mods:
            display_name += ' (modules: {})'.format(', '.join(str(i) for i in mods))
        not_found_message = kwargs.get('not_found_message', '')
        if not isinstance(not_found_message, str):
            raise InvalidArguments('The not_found_message must be a string.')
        try:
            d = self.dependency_impl(name, display_name, kwargs)
        except Exception:
            if not_found_message:
                self.message_impl([not_found_message])
            raise
        assert isinstance(d, DependencyHolder)
        if not d.found() and not_found_message:
            self.message_impl([not_found_message])
            self.message_impl([not_found_message])
        # Ensure the correct include type
        if 'include_type' in kwargs:
            wanted = kwargs['include_type']
            actual = d.include_type_method([], {})
            if wanted != actual:
                mlog.debug('Current include type of {} is {}. Converting to requested {}'.format(name, actual, wanted))
                d = d.as_system_method([wanted], {})
        # Override this dependency to have consistent results in subsequent
        # dependency lookups.
        if name and d.found():
            for_machine = self.machine_from_native_kwarg(kwargs)
            identifier = dependencies.get_dep_identifier(name, kwargs)
            if identifier not in self.build.dependency_overrides[for_machine]:
                self.build.dependency_overrides[for_machine][identifier] = \
                    build.DependencyOverride(d.held_object, node, explicit=False)
        return d

    def dependency_impl(self, name, display_name, kwargs, force_fallback=False):
        disabled, required, feature = extract_required_kwarg(kwargs, self.subproject)
        if disabled:
            mlog.log('Dependency', mlog.bold(display_name), 'skipped: feature', mlog.bold(feature), 'disabled')
            return self.notfound_dependency()

        fallback = kwargs.get('fallback', None)
        allow_fallback = kwargs.get('allow_fallback', None)
        if allow_fallback is not None:
            FeatureNew.single_use('"allow_fallback" keyword argument for dependency', '0.56.0', self.subproject)
            if fallback is not None:
                raise InvalidArguments('"fallback" and "allow_fallback" arguments are mutually exclusive')
            if not isinstance(allow_fallback, bool):
                raise InvalidArguments('"allow_fallback" argument must be boolean')

        # If "fallback" is absent, look for an implicit fallback.
        if name and fallback is None and allow_fallback is not False:
            # Add an implicit fallback if we have a wrap file or a directory with the same name,
            # but only if this dependency is required. It is common to first check for a pkg-config,
            # then fallback to use find_library() and only afterward check again the dependency
            # with a fallback. If the fallback has already been configured then we have to use it
            # even if the dependency is not required.
            provider = self.environment.wrap_resolver.find_dep_provider(name)
            if not provider and allow_fallback is True:
                raise InvalidArguments('Fallback wrap or subproject not found for dependency \'%s\'' % name)
            subp_name = mesonlib.listify(provider)[0]
            if provider and (allow_fallback is True or required or self.get_subproject(subp_name)):
                fallback = provider

        if 'default_options' in kwargs and not fallback:
            mlog.warning('The "default_options" keyword argument does nothing without a fallback subproject.',
                         location=self.current_node)

        # writing just "dependency('')" is an error, because it can only fail
        if name == '' and required and not fallback:
            raise InvalidArguments('Dependency is both required and not-found')

        if '<' in name or '>' in name or '=' in name:
            raise InvalidArguments('Characters <, > and = are forbidden in dependency names. To specify'
                                   'version\n requirements use the \'version\' keyword argument instead.')

        identifier, cached_dep = self._find_cached_dep(name, display_name, kwargs)
        if cached_dep:
            if fallback:
                subp_name, varname = self.get_subproject_infos(fallback)
                self.verify_fallback_consistency(subp_name, varname, cached_dep)
            if required and not cached_dep.found():
                m = 'Dependency {!r} was already checked and was not found'
                raise DependencyException(m.format(display_name))
            return DependencyHolder(cached_dep, self.subproject)

        if fallback:
            # If the dependency has already been configured, possibly by
            # a higher level project, try to use it first.
            subp_name, varname = self.get_subproject_infos(fallback)
            if self.get_subproject(subp_name):
                return self.get_subproject_dep(name, display_name, subp_name, varname, kwargs)

            wrap_mode = self.coredata.get_builtin_option('wrap_mode')
            force_fallback_for = self.coredata.get_builtin_option('force_fallback_for')
            force_fallback = (force_fallback or
                              wrap_mode == WrapMode.forcefallback or
                              name in force_fallback_for or
                              subp_name in force_fallback_for)

        if name != '' and (not fallback or not force_fallback):
            self._handle_featurenew_dependencies(name)
            kwargs['required'] = required and not fallback
            dep = dependencies.find_external_dependency(name, self.environment, kwargs)
            kwargs['required'] = required
            # Only store found-deps in the cache
            # Never add fallback deps to self.coredata.deps since we
            # cannot cache them. They must always be evaluated else
            # we won't actually read all the build files.
            if dep.found():
                for_machine = self.machine_from_native_kwarg(kwargs)
                self.coredata.deps[for_machine].put(identifier, dep)
                return DependencyHolder(dep, self.subproject)

        if fallback:
            return self.dependency_fallback(name, display_name, fallback, kwargs)

        return self.notfound_dependency()

    @FeatureNew('disabler', '0.44.0')
    @noKwargs
    @noPosargs
    def func_disabler(self, node, args, kwargs):
        return Disabler()

    def get_subproject_infos(self, fbinfo):
        fbinfo = mesonlib.stringlistify(fbinfo)
        if len(fbinfo) == 1:
            FeatureNew.single_use('Fallback without variable name', '0.53.0', self.subproject)
            return fbinfo[0], None
        elif len(fbinfo) != 2:
            raise InterpreterException('Fallback info must have one or two items.')
        return fbinfo

    def dependency_fallback(self, name, display_name, fallback, kwargs):
        subp_name, varname = self.get_subproject_infos(fallback)
        required = kwargs.get('required', True)

        # Explicitly listed fallback preferences for specific subprojects
        # take precedence over wrap-mode
        force_fallback_for = self.coredata.get_builtin_option('force_fallback_for')
        if name in force_fallback_for or subp_name in force_fallback_for:
            mlog.log('Looking for a fallback subproject for the dependency',
                     mlog.bold(display_name), 'because:\nUse of fallback was forced for that specific subproject')
        elif self.coredata.get_builtin_option('wrap_mode') == WrapMode.nofallback:
            mlog.log('Not looking for a fallback subproject for the dependency',
                     mlog.bold(display_name), 'because:\nUse of fallback '
                     'dependencies is disabled.')
            if required:
                m = 'Dependency {!r} not found and fallback is disabled'
                raise DependencyException(m.format(display_name))
            return self.notfound_dependency()
        elif self.coredata.get_builtin_option('wrap_mode') == WrapMode.forcefallback:
            mlog.log('Looking for a fallback subproject for the dependency',
                     mlog.bold(display_name), 'because:\nUse of fallback dependencies is forced.')
        else:
            mlog.log('Looking for a fallback subproject for the dependency',
                     mlog.bold(display_name))
        sp_kwargs = {
            'default_options': kwargs.get('default_options', []),
            'required': required,
        }
        self.do_subproject(subp_name, 'meson', sp_kwargs)
        return self.get_subproject_dep(name, display_name, subp_name, varname, kwargs)

    @FeatureNewKwargs('executable', '0.42.0', ['implib'])
    @FeatureNewKwargs('executable', '0.56.0', ['win_subsystem'])
    @FeatureDeprecatedKwargs('executable', '0.56.0', ['gui_app'], extra_message="Use 'win_subsystem' instead.")
    @permittedKwargs(permitted_kwargs['executable'])
    def func_executable(self, node, args, kwargs):
        return self.build_target(node, args, kwargs, ExecutableHolder)

    @permittedKwargs(permitted_kwargs['static_library'])
    def func_static_lib(self, node, args, kwargs):
        return self.build_target(node, args, kwargs, StaticLibraryHolder)

    @permittedKwargs(permitted_kwargs['shared_library'])
    def func_shared_lib(self, node, args, kwargs):
        holder = self.build_target(node, args, kwargs, SharedLibraryHolder)
        holder.held_object.shared_library_only = True
        return holder

    @permittedKwargs(permitted_kwargs['both_libraries'])
    def func_both_lib(self, node, args, kwargs):
        return self.build_both_libraries(node, args, kwargs)

    @FeatureNew('shared_module', '0.37.0')
    @permittedKwargs(permitted_kwargs['shared_module'])
    def func_shared_module(self, node, args, kwargs):
        return self.build_target(node, args, kwargs, SharedModuleHolder)

    @permittedKwargs(permitted_kwargs['library'])
    def func_library(self, node, args, kwargs):
        return self.build_library(node, args, kwargs)

    @permittedKwargs(permitted_kwargs['jar'])
    def func_jar(self, node, args, kwargs):
        return self.build_target(node, args, kwargs, JarHolder)

    @FeatureNewKwargs('build_target', '0.40.0', ['link_whole', 'override_options'])
    @permittedKwargs(permitted_kwargs['build_target'])
    def func_build_target(self, node, args, kwargs):
        if 'target_type' not in kwargs:
            raise InterpreterException('Missing target_type keyword argument')
        target_type = kwargs.pop('target_type')
        if target_type == 'executable':
            return self.build_target(node, args, kwargs, ExecutableHolder)
        elif target_type == 'shared_library':
            return self.build_target(node, args, kwargs, SharedLibraryHolder)
        elif target_type == 'shared_module':
            FeatureNew('build_target(target_type: \'shared_module\')',
                       '0.51.0').use(self.subproject)
            return self.build_target(node, args, kwargs, SharedModuleHolder)
        elif target_type == 'static_library':
            return self.build_target(node, args, kwargs, StaticLibraryHolder)
        elif target_type == 'both_libraries':
            return self.build_both_libraries(node, args, kwargs)
        elif target_type == 'library':
            return self.build_library(node, args, kwargs)
        elif target_type == 'jar':
            return self.build_target(node, args, kwargs, JarHolder)
        else:
            raise InterpreterException('Unknown target_type.')

    @permittedKwargs(permitted_kwargs['vcs_tag'])
    @FeatureDeprecatedKwargs('custom_target', '0.47.0', ['build_always'],
                             'combine build_by_default and build_always_stale instead.')
    def func_vcs_tag(self, node, args, kwargs):
        if 'input' not in kwargs or 'output' not in kwargs:
            raise InterpreterException('Keyword arguments input and output must exist')
        if 'fallback' not in kwargs:
            FeatureNew.single_use('Optional fallback in vcs_tag', '0.41.0', self.subproject)
        fallback = kwargs.pop('fallback', self.project_version)
        if not isinstance(fallback, str):
            raise InterpreterException('Keyword argument fallback must be a string.')
        replace_string = kwargs.pop('replace_string', '@VCS_TAG@')
        regex_selector = '(.*)' # default regex selector for custom command: use complete output
        vcs_cmd = kwargs.get('command', None)
        if vcs_cmd and not isinstance(vcs_cmd, list):
            vcs_cmd = [vcs_cmd]
        source_dir = os.path.normpath(os.path.join(self.environment.get_source_dir(), self.subdir))
        if vcs_cmd:
            # Is the command an executable in path or maybe a script in the source tree?
            vcs_cmd[0] = shutil.which(vcs_cmd[0]) or os.path.join(source_dir, vcs_cmd[0])
        else:
            vcs = mesonlib.detect_vcs(source_dir)
            if vcs:
                mlog.log('Found %s repository at %s' % (vcs['name'], vcs['wc_dir']))
                vcs_cmd = vcs['get_rev'].split()
                regex_selector = vcs['rev_regex']
            else:
                vcs_cmd = [' '] # executing this cmd will fail in vcstagger.py and force to use the fallback string
        # vcstagger.py parameters: infile, outfile, fallback, source_dir, replace_string, regex_selector, command...
        kwargs['command'] = self.environment.get_build_command() + \
            ['--internal',
             'vcstagger',
             '@INPUT0@',
             '@OUTPUT0@',
             fallback,
             source_dir,
             replace_string,
             regex_selector] + vcs_cmd
        kwargs.setdefault('build_by_default', True)
        kwargs.setdefault('build_always_stale', True)
        return self._func_custom_target_impl(node, [kwargs['output']], kwargs)

    @FeatureNew('subdir_done', '0.46.0')
    @stringArgs
    def func_subdir_done(self, node, args, kwargs):
        if len(kwargs) > 0:
            raise InterpreterException('exit does not take named arguments')
        if len(args) > 0:
            raise InterpreterException('exit does not take any arguments')
        raise SubdirDoneRequest()

    @stringArgs
    @FeatureNewKwargs('custom_target', '0.48.0', ['console'])
    @FeatureNewKwargs('custom_target', '0.47.0', ['install_mode', 'build_always_stale'])
    @FeatureNewKwargs('custom_target', '0.40.0', ['build_by_default'])
    @permittedKwargs(permitted_kwargs['custom_target'])
    def func_custom_target(self, node, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('custom_target: Only one positional argument is allowed, and it must be a string name')
        if 'depfile' in kwargs and ('@BASENAME@' in kwargs['depfile'] or '@PLAINNAME@' in kwargs['depfile']):
            FeatureNew.single_use('substitutions in custom_target depfile', '0.47.0', self.subproject)
        return self._func_custom_target_impl(node, args, kwargs)

    def _func_custom_target_impl(self, node, args, kwargs):
        'Implementation-only, without FeatureNew checks, for internal use'
        name = args[0]
        kwargs['install_mode'] = self._get_kwarg_install_mode(kwargs)
        if 'input' in kwargs:
            try:
                kwargs['input'] = self.source_strings_to_files(extract_as_list(kwargs, 'input'))
            except mesonlib.MesonException:
                mlog.warning('''Custom target input \'%s\' can\'t be converted to File object(s).
This will become a hard error in the future.''' % kwargs['input'], location=self.current_node)
        tg = CustomTargetHolder(build.CustomTarget(name, self.subdir, self.subproject, kwargs, backend=self.backend), self)
        self.add_target(name, tg.held_object)
        return tg

    @permittedKwargs(permitted_kwargs['run_target'])
    def func_run_target(self, node, args, kwargs):
        if len(args) > 1:
            raise InvalidCode('Run_target takes only one positional argument: the target name.')
        elif len(args) == 1:
            if 'command' not in kwargs:
                raise InterpreterException('Missing "command" keyword argument')
            all_args = extract_as_list(kwargs, 'command')
            deps = unholder(extract_as_list(kwargs, 'depends'))
        else:
            raise InterpreterException('Run_target needs at least one positional argument.')

        cleaned_args = []
        for i in unholder(listify(all_args)):
            if not isinstance(i, (str, build.BuildTarget, build.CustomTarget, dependencies.ExternalProgram, mesonlib.File)):
                mlog.debug('Wrong type:', str(i))
                raise InterpreterException('Invalid argument to run_target.')
            if isinstance(i, dependencies.ExternalProgram) and not i.found():
                raise InterpreterException('Tried to use non-existing executable {!r}'.format(i.name))
            cleaned_args.append(i)
        name = args[0]
        if not isinstance(name, str):
            raise InterpreterException('First argument must be a string.')
        cleaned_deps = []
        for d in deps:
            if not isinstance(d, (build.BuildTarget, build.CustomTarget)):
                raise InterpreterException('Depends items must be build targets.')
            cleaned_deps.append(d)
        command, *cmd_args = cleaned_args
        tg = RunTargetHolder(build.RunTarget(name, command, cmd_args, cleaned_deps, self.subdir, self.subproject), self)
        self.add_target(name, tg.held_object)
        full_name = (self.subproject, name)
        assert(full_name not in self.build.run_target_names)
        self.build.run_target_names.add(full_name)
        return tg

    @FeatureNew('alias_target', '0.52.0')
    @noKwargs
    def func_alias_target(self, node, args, kwargs):
        if len(args) < 2:
            raise InvalidCode('alias_target takes at least 2 arguments.')
        name = args[0]
        if not isinstance(name, str):
            raise InterpreterException('First argument must be a string.')
        deps = unholder(listify(args[1:]))
        for d in deps:
            if not isinstance(d, (build.BuildTarget, build.CustomTarget)):
                raise InterpreterException('Depends items must be build targets.')
        tg = RunTargetHolder(build.AliasTarget(name, deps, self.subdir, self.subproject), self)
        self.add_target(name, tg.held_object)
        return tg

    @permittedKwargs(permitted_kwargs['generator'])
    def func_generator(self, node, args, kwargs):
        gen = GeneratorHolder(self, args, kwargs)
        self.generators.append(gen)
        return gen

    @FeatureNewKwargs('benchmark', '0.46.0', ['depends'])
    @FeatureNewKwargs('benchmark', '0.52.0', ['priority'])
    @permittedKwargs(permitted_kwargs['benchmark'])
    def func_benchmark(self, node, args, kwargs):
        # is_parallel isn't valid here, so make sure it isn't passed
        if 'is_parallel' in kwargs:
            del kwargs['is_parallel']
        self.add_test(node, args, kwargs, False)

    @FeatureNewKwargs('test', '0.46.0', ['depends'])
    @FeatureNewKwargs('test', '0.52.0', ['priority'])
    @permittedKwargs(permitted_kwargs['test'])
    def func_test(self, node, args, kwargs):
        if kwargs.get('protocol') == 'gtest':
            FeatureNew.single_use('"gtest" protocol for tests', '0.55.0', self.subproject)
        self.add_test(node, args, kwargs, True)

    def unpack_env_kwarg(self, kwargs) -> build.EnvironmentVariables:
        envlist = kwargs.get('env', EnvironmentVariablesHolder())
        if isinstance(envlist, EnvironmentVariablesHolder):
            env = envlist.held_object
        elif isinstance(envlist, dict):
            FeatureNew.single_use('environment dictionary', '0.52.0', self.subproject)
            env = EnvironmentVariablesHolder(envlist)
            env = env.held_object
        else:
            envlist = listify(envlist)
            # Convert from array to environment object
            env = EnvironmentVariablesHolder(envlist)
            env = env.held_object
        return env

    def add_test(self, node, args, kwargs, is_base_test):
        if len(args) != 2:
            raise InterpreterException('test expects 2 arguments, {} given'.format(len(args)))
        name = args[0]
        if not isinstance(name, str):
            raise InterpreterException('First argument of test must be a string.')
        if ':' in name:
            mlog.deprecation('":" is not allowed in test name "{}", it has been replaced with "_"'.format(name),
                             location=node)
            name = name.replace(':', '_')
        exe = args[1]
        if not isinstance(exe, (ExecutableHolder, JarHolder, ExternalProgramHolder)):
            if isinstance(exe, mesonlib.File):
                exe = self.func_find_program(node, args[1], {})
            else:
                raise InterpreterException('Second argument must be executable.')
        par = kwargs.get('is_parallel', True)
        if not isinstance(par, bool):
            raise InterpreterException('Keyword argument is_parallel must be a boolean.')
        cmd_args = unholder(extract_as_list(kwargs, 'args'))
        for i in cmd_args:
            if not isinstance(i, (str, mesonlib.File, build.Target)):
                raise InterpreterException('Command line arguments must be strings, files or targets.')
        env = self.unpack_env_kwarg(kwargs)
        should_fail = kwargs.get('should_fail', False)
        if not isinstance(should_fail, bool):
            raise InterpreterException('Keyword argument should_fail must be a boolean.')
        timeout = kwargs.get('timeout', 30)
        if 'workdir' in kwargs:
            workdir = kwargs['workdir']
            if not isinstance(workdir, str):
                raise InterpreterException('Workdir keyword argument must be a string.')
            if not os.path.isabs(workdir):
                raise InterpreterException('Workdir keyword argument must be an absolute path.')
        else:
            workdir = None
        if not isinstance(timeout, int):
            raise InterpreterException('Timeout must be an integer.')
        protocol = kwargs.get('protocol', 'exitcode')
        if protocol not in {'exitcode', 'tap', 'gtest'}:
            raise InterpreterException('Protocol must be "exitcode", "tap", or "gtest".')
        suite = []
        prj = self.subproject if self.is_subproject() else self.build.project_name
        for s in mesonlib.stringlistify(kwargs.get('suite', '')):
            if len(s) > 0:
                s = ':' + s
            suite.append(prj.replace(' ', '_').replace(':', '_') + s)
        depends = unholder(extract_as_list(kwargs, 'depends'))
        for dep in depends:
            if not isinstance(dep, (build.CustomTarget, build.BuildTarget)):
                raise InterpreterException('Depends items must be build targets.')
        priority = kwargs.get('priority', 0)
        if not isinstance(priority, int):
            raise InterpreterException('Keyword argument priority must be an integer.')
        t = Test(name, prj, suite, exe.held_object, depends, par, cmd_args,
                 env, should_fail, timeout, workdir, protocol, priority)
        if is_base_test:
            self.build.tests.append(t)
            mlog.debug('Adding test', mlog.bold(name, True))
        else:
            self.build.benchmarks.append(t)
            mlog.debug('Adding benchmark', mlog.bold(name, True))

    @FeatureNewKwargs('install_headers', '0.47.0', ['install_mode'])
    @permittedKwargs(permitted_kwargs['install_headers'])
    def func_install_headers(self, node, args, kwargs):
        source_files = self.source_strings_to_files(args)
        kwargs['install_mode'] = self._get_kwarg_install_mode(kwargs)
        h = Headers(source_files, kwargs)
        self.build.headers.append(h)
        return h

    @FeatureNewKwargs('install_man', '0.47.0', ['install_mode'])
    @permittedKwargs(permitted_kwargs['install_man'])
    def func_install_man(self, node, args, kwargs):
        fargs = self.source_strings_to_files(args)
        kwargs['install_mode'] = self._get_kwarg_install_mode(kwargs)
        m = Man(fargs, kwargs)
        self.build.man.append(m)
        return m

    @FeatureNewKwargs('subdir', '0.44.0', ['if_found'])
    @permittedKwargs(permitted_kwargs['subdir'])
    def func_subdir(self, node, args, kwargs):
        self.validate_arguments(args, 1, [str])
        mesonlib.check_direntry_issues(args)
        if '..' in args[0]:
            raise InvalidArguments('Subdir contains ..')
        if self.subdir == '' and args[0] == self.subproject_dir:
            raise InvalidArguments('Must not go into subprojects dir with subdir(), use subproject() instead.')
        if self.subdir == '' and args[0].startswith('meson-'):
            raise InvalidArguments('The "meson-" prefix is reserved and cannot be used for top-level subdir().')
        for i in mesonlib.extract_as_list(kwargs, 'if_found'):
            if not hasattr(i, 'found_method'):
                raise InterpreterException('Object used in if_found does not have a found method.')
            if not i.found_method([], {}):
                return
        prev_subdir = self.subdir
        subdir = os.path.join(prev_subdir, args[0])
        if os.path.isabs(subdir):
            raise InvalidArguments('Subdir argument must be a relative path.')
        absdir = os.path.join(self.environment.get_source_dir(), subdir)
        symlinkless_dir = os.path.realpath(absdir)
        if symlinkless_dir in self.visited_subdirs:
            raise InvalidArguments('Tried to enter directory "%s", which has already been visited.'
                                   % subdir)
        self.visited_subdirs[symlinkless_dir] = True
        self.subdir = subdir
        os.makedirs(os.path.join(self.environment.build_dir, subdir), exist_ok=True)
        buildfilename = os.path.join(self.subdir, environment.build_filename)
        self.build_def_files.append(buildfilename)
        absname = os.path.join(self.environment.get_source_dir(), buildfilename)
        if not os.path.isfile(absname):
            self.subdir = prev_subdir
            raise InterpreterException("Non-existent build file '{!s}'".format(buildfilename))
        with open(absname, encoding='utf8') as f:
            code = f.read()
        assert(isinstance(code, str))
        try:
            codeblock = mparser.Parser(code, absname).parse()
        except mesonlib.MesonException as me:
            me.file = absname
            raise me
        try:
            self.evaluate_codeblock(codeblock)
        except SubdirDoneRequest:
            pass
        self.subdir = prev_subdir

    def _get_kwarg_install_mode(self, kwargs):
        if kwargs.get('install_mode', None) is None:
            return None
        install_mode = []
        mode = mesonlib.typeslistify(kwargs.get('install_mode', []), (str, int))
        for m in mode:
            # We skip any arguments that are set to `false`
            if m is False:
                m = None
            install_mode.append(m)
        if len(install_mode) > 3:
            raise InvalidArguments('Keyword argument install_mode takes at '
                                   'most 3 arguments.')
        if len(install_mode) > 0 and install_mode[0] is not None and \
           not isinstance(install_mode[0], str):
            raise InvalidArguments('Keyword argument install_mode requires the '
                                   'permissions arg to be a string or false')
        return FileMode(*install_mode)

    @FeatureNewKwargs('install_data', '0.46.0', ['rename'])
    @FeatureNewKwargs('install_data', '0.38.0', ['install_mode'])
    @permittedKwargs(permitted_kwargs['install_data'])
    def func_install_data(self, node, args, kwargs):
        kwsource = mesonlib.stringlistify(kwargs.get('sources', []))
        raw_sources = args + kwsource
        sources = []
        source_strings = []
        for s in raw_sources:
            if isinstance(s, mesonlib.File):
                sources.append(s)
            elif isinstance(s, str):
                source_strings.append(s)
            else:
                raise InvalidArguments('Argument must be string or file.')
        sources += self.source_strings_to_files(source_strings)
        install_dir = kwargs.get('install_dir', None)
        if not isinstance(install_dir, (str, type(None))):
            raise InvalidArguments('Keyword argument install_dir not a string.')
        install_mode = self._get_kwarg_install_mode(kwargs)
        rename = kwargs.get('rename', None)
        data = DataHolder(build.Data(sources, install_dir, install_mode, rename))
        self.build.data.append(data.held_object)
        return data

    @FeatureNewKwargs('install_subdir', '0.42.0', ['exclude_files', 'exclude_directories'])
    @FeatureNewKwargs('install_subdir', '0.38.0', ['install_mode'])
    @permittedKwargs(permitted_kwargs['install_subdir'])
    @stringArgs
    def func_install_subdir(self, node, args, kwargs):
        if len(args) != 1:
            raise InvalidArguments('Install_subdir requires exactly one argument.')
        subdir = args[0]
        if 'install_dir' not in kwargs:
            raise InvalidArguments('Missing keyword argument install_dir')
        install_dir = kwargs['install_dir']
        if not isinstance(install_dir, str):
            raise InvalidArguments('Keyword argument install_dir not a string.')
        if 'strip_directory' in kwargs:
            if not isinstance(kwargs['strip_directory'], bool):
                raise InterpreterException('"strip_directory" keyword must be a boolean.')
            strip_directory = kwargs['strip_directory']
        else:
            strip_directory = False
        if 'exclude_files' in kwargs:
            exclude = extract_as_list(kwargs, 'exclude_files')
            for f in exclude:
                if not isinstance(f, str):
                    raise InvalidArguments('Exclude argument not a string.')
                elif os.path.isabs(f):
                    raise InvalidArguments('Exclude argument cannot be absolute.')
            exclude_files = set(exclude)
        else:
            exclude_files = set()
        if 'exclude_directories' in kwargs:
            exclude = extract_as_list(kwargs, 'exclude_directories')
            for d in exclude:
                if not isinstance(d, str):
                    raise InvalidArguments('Exclude argument not a string.')
                elif os.path.isabs(d):
                    raise InvalidArguments('Exclude argument cannot be absolute.')
            exclude_directories = set(exclude)
        else:
            exclude_directories = set()
        exclude = (exclude_files, exclude_directories)
        install_mode = self._get_kwarg_install_mode(kwargs)
        idir = InstallDir(self.subdir, subdir, install_dir, install_mode, exclude, strip_directory)
        self.build.install_dirs.append(idir)
        return idir

    @FeatureNewKwargs('configure_file', '0.47.0', ['copy', 'output_format', 'install_mode', 'encoding'])
    @FeatureNewKwargs('configure_file', '0.46.0', ['format'])
    @FeatureNewKwargs('configure_file', '0.41.0', ['capture'])
    @FeatureNewKwargs('configure_file', '0.50.0', ['install'])
    @FeatureNewKwargs('configure_file', '0.52.0', ['depfile'])
    @permittedKwargs(permitted_kwargs['configure_file'])
    def func_configure_file(self, node, args, kwargs):
        if len(args) > 0:
            raise InterpreterException("configure_file takes only keyword arguments.")
        if 'output' not in kwargs:
            raise InterpreterException('Required keyword argument "output" not defined.')
        actions = set(['configuration', 'command', 'copy']).intersection(kwargs.keys())
        if len(actions) == 0:
            raise InterpreterException('Must specify an action with one of these '
                                       'keyword arguments: \'configuration\', '
                                       '\'command\', or \'copy\'.')
        elif len(actions) == 2:
            raise InterpreterException('Must not specify both {!r} and {!r} '
                                       'keyword arguments since they are '
                                       'mutually exclusive.'.format(*actions))
        elif len(actions) == 3:
            raise InterpreterException('Must specify one of {!r}, {!r}, and '
                                       '{!r} keyword arguments since they are '
                                       'mutually exclusive.'.format(*actions))
        if 'capture' in kwargs:
            if not isinstance(kwargs['capture'], bool):
                raise InterpreterException('"capture" keyword must be a boolean.')
            if 'command' not in kwargs:
                raise InterpreterException('"capture" keyword requires "command" keyword.')

        if 'format' in kwargs:
            fmt = kwargs['format']
            if not isinstance(fmt, str):
                raise InterpreterException('"format" keyword must be a string.')
        else:
            fmt = 'meson'

        if fmt not in ('meson', 'cmake', 'cmake@'):
            raise InterpreterException('"format" possible values are "meson", "cmake" or "cmake@".')

        if 'output_format' in kwargs:
            output_format = kwargs['output_format']
            if not isinstance(output_format, str):
                raise InterpreterException('"output_format" keyword must be a string.')
        else:
            output_format = 'c'

        if output_format not in ('c', 'nasm'):
            raise InterpreterException('"format" possible values are "c" or "nasm".')

        if 'depfile' in kwargs:
            depfile = kwargs['depfile']
            if not isinstance(depfile, str):
                raise InterpreterException('depfile file name must be a string')
        else:
            depfile = None

        # Validate input
        inputs = self.source_strings_to_files(extract_as_list(kwargs, 'input'))
        inputs_abs = []
        for f in inputs:
            if isinstance(f, mesonlib.File):
                inputs_abs.append(f.absolute_path(self.environment.source_dir,
                                                  self.environment.build_dir))
                self.add_build_def_file(f)
            else:
                raise InterpreterException('Inputs can only be strings or file objects')
        # Validate output
        output = kwargs['output']
        if not isinstance(output, str):
            raise InterpreterException('Output file name must be a string')
        if inputs_abs:
            values = mesonlib.get_filenames_templates_dict(inputs_abs, None)
            outputs = mesonlib.substitute_values([output], values)
            output = outputs[0]
            if depfile:
                depfile = mesonlib.substitute_values([depfile], values)[0]
        ofile_rpath = os.path.join(self.subdir, output)
        if ofile_rpath in self.configure_file_outputs:
            mesonbuildfile = os.path.join(self.subdir, 'meson.build')
            current_call = "{}:{}".format(mesonbuildfile, self.current_lineno)
            first_call = "{}:{}".format(mesonbuildfile, self.configure_file_outputs[ofile_rpath])
            mlog.warning('Output file', mlog.bold(ofile_rpath, True), 'for configure_file() at', current_call, 'overwrites configure_file() output at', first_call)
        else:
            self.configure_file_outputs[ofile_rpath] = self.current_lineno
        if os.path.dirname(output) != '':
            raise InterpreterException('Output file name must not contain a subdirectory.')
        (ofile_path, ofile_fname) = os.path.split(os.path.join(self.subdir, output))
        ofile_abs = os.path.join(self.environment.build_dir, ofile_path, ofile_fname)
        # Perform the appropriate action
        if 'configuration' in kwargs:
            conf = kwargs['configuration']
            if isinstance(conf, dict):
                FeatureNew.single_use('configure_file.configuration dictionary', '0.49.0', self.subproject)
                conf = ConfigurationDataHolder(self.subproject, conf)
            elif not isinstance(conf, ConfigurationDataHolder):
                raise InterpreterException('Argument "configuration" is not of type configuration_data')
            mlog.log('Configuring', mlog.bold(output), 'using configuration')
            if len(inputs) > 1:
                raise InterpreterException('At most one input file can given in configuration mode')
            if inputs:
                os.makedirs(os.path.join(self.environment.build_dir, self.subdir), exist_ok=True)
                file_encoding = kwargs.setdefault('encoding', 'utf-8')
                missing_variables, confdata_useless = \
                    mesonlib.do_conf_file(inputs_abs[0], ofile_abs, conf.held_object,
                                          fmt, file_encoding)
                if missing_variables:
                    var_list = ", ".join(map(repr, sorted(missing_variables)))
                    mlog.warning(
                        "The variable(s) %s in the input file '%s' are not "
                        "present in the given configuration data." % (
                            var_list, inputs[0]), location=node)
                if confdata_useless:
                    ifbase = os.path.basename(inputs_abs[0])
                    mlog.warning('Got an empty configuration_data() object and found no '
                                 'substitutions in the input file {!r}. If you want to '
                                 'copy a file to the build dir, use the \'copy:\' keyword '
                                 'argument added in 0.47.0'.format(ifbase), location=node)
            else:
                mesonlib.dump_conf_header(ofile_abs, conf.held_object, output_format)
            conf.mark_used()
        elif 'command' in kwargs:
            if len(inputs) > 1:
                FeatureNew.single_use('multiple inputs in configure_file()', '0.52.0', self.subproject)
            # We use absolute paths for input and output here because the cwd
            # that the command is run from is 'unspecified', so it could change.
            # Currently it's builddir/subdir for in_builddir else srcdir/subdir.
            values = mesonlib.get_filenames_templates_dict(inputs_abs, [ofile_abs])
            if depfile:
                depfile = os.path.join(self.environment.get_scratch_dir(), depfile)
                values['@DEPFILE@'] = depfile
            # Substitute @INPUT@, @OUTPUT@, etc here.
            cmd = mesonlib.substitute_values(kwargs['command'], values)
            mlog.log('Configuring', mlog.bold(output), 'with command')
            res = self.run_command_impl(node, cmd,  {}, True)
            if res.returncode != 0:
                raise InterpreterException('Running configure command failed.\n%s\n%s' %
                                           (res.stdout, res.stderr))
            if 'capture' in kwargs and kwargs['capture']:
                dst_tmp = ofile_abs + '~'
                file_encoding = kwargs.setdefault('encoding', 'utf-8')
                with open(dst_tmp, 'w', encoding=file_encoding) as f:
                    f.writelines(res.stdout)
                if inputs_abs:
                    shutil.copymode(inputs_abs[0], dst_tmp)
                mesonlib.replace_if_different(ofile_abs, dst_tmp)
            if depfile:
                mlog.log('Reading depfile:', mlog.bold(depfile))
                with open(depfile, 'r') as f:
                    df = DepFile(f.readlines())
                    deps = df.get_all_dependencies(ofile_fname)
                    for dep in deps:
                        self.add_build_def_file(dep)

        elif 'copy' in kwargs:
            if len(inputs_abs) != 1:
                raise InterpreterException('Exactly one input file must be given in copy mode')
            os.makedirs(os.path.join(self.environment.build_dir, self.subdir), exist_ok=True)
            shutil.copy2(inputs_abs[0], ofile_abs)
        else:
            # Not reachable
            raise AssertionError
        # Install file if requested, we check for the empty string
        # for backwards compatibility. That was the behaviour before
        # 0.45.0 so preserve it.
        idir = kwargs.get('install_dir', '')
        if idir is False:
            idir = ''
            mlog.deprecation('Please use the new `install:` kwarg instead of passing '
                             '`false` to `install_dir:`', location=node)
        if not isinstance(idir, str):
            if isinstance(idir, list) and len(idir) == 0:
                mlog.deprecation('install_dir: kwarg must be a string and not an empty array. '
                                 'Please use the install: kwarg to enable or disable installation. '
                                 'This will be a hard error in the next release.')
            else:
                raise InterpreterException('"install_dir" must be a string')
        install = kwargs.get('install', idir != '')
        if not isinstance(install, bool):
            raise InterpreterException('"install" must be a boolean')
        if install:
            if not idir:
                raise InterpreterException('"install_dir" must be specified '
                                           'when "install" in a configure_file '
                                           'is true')
            cfile = mesonlib.File.from_built_file(ofile_path, ofile_fname)
            install_mode = self._get_kwarg_install_mode(kwargs)
            self.build.data.append(build.Data([cfile], idir, install_mode))
        return mesonlib.File.from_built_file(self.subdir, output)

    def extract_incdirs(self, kwargs):
        prospectives = unholder(extract_as_list(kwargs, 'include_directories'))
        result = []
        for p in prospectives:
            if isinstance(p, build.IncludeDirs):
                result.append(p)
            elif isinstance(p, str):
                result.append(self.build_incdir_object([p]).held_object)
            else:
                raise InterpreterException('Include directory objects can only be created from strings or include directories.')
        return result

    @permittedKwargs(permitted_kwargs['include_directories'])
    @stringArgs
    def func_include_directories(self, node, args, kwargs):
        return self.build_incdir_object(args, kwargs.get('is_system', False))

    def build_incdir_object(self, incdir_strings, is_system=False):
        if not isinstance(is_system, bool):
            raise InvalidArguments('Is_system must be boolean.')
        src_root = self.environment.get_source_dir()
        build_root = self.environment.get_build_dir()
        absbase_src = os.path.join(src_root, self.subdir)
        absbase_build = os.path.join(build_root, self.subdir)

        for a in incdir_strings:
            if a.startswith(src_root):
                raise InvalidArguments('Tried to form an absolute path to a source dir. '
                                       'You should not do that but use relative paths instead.'
                                       '''

To get include path to any directory relative to the current dir do

incdir = include_directories(dirname)

After this incdir will contain both the current source dir as well as the
corresponding build dir. It can then be used in any subdirectory and
Meson will take care of all the busywork to make paths work.

Dirname can even be '.' to mark the current directory. Though you should
remember that the current source and build directories are always
put in the include directories by default so you only need to do
include_directories('.') if you intend to use the result in a
different subdirectory.
''')
            absdir_src = os.path.join(absbase_src, a)
            absdir_build = os.path.join(absbase_build, a)
            if not os.path.isdir(absdir_src) and not os.path.isdir(absdir_build):
                raise InvalidArguments('Include dir %s does not exist.' % a)
        i = IncludeDirsHolder(build.IncludeDirs(self.subdir, incdir_strings, is_system))
        return i

    @permittedKwargs(permitted_kwargs['add_test_setup'])
    @stringArgs
    def func_add_test_setup(self, node, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Add_test_setup needs one argument for the setup name.')
        setup_name = args[0]
        if re.fullmatch('([_a-zA-Z][_0-9a-zA-Z]*:)?[_a-zA-Z][_0-9a-zA-Z]*', setup_name) is None:
            raise InterpreterException('Setup name may only contain alphanumeric characters.')
        if ":" not in setup_name:
            setup_name = (self.subproject if self.subproject else self.build.project_name) + ":" + setup_name
        try:
            inp = unholder(extract_as_list(kwargs, 'exe_wrapper'))
            exe_wrapper = []
            for i in inp:
                if isinstance(i, str):
                    exe_wrapper.append(i)
                elif isinstance(i, dependencies.ExternalProgram):
                    if not i.found():
                        raise InterpreterException('Tried to use non-found executable.')
                    exe_wrapper += i.get_command()
                else:
                    raise InterpreterException('Exe wrapper can only contain strings or external binaries.')
        except KeyError:
            exe_wrapper = None
        gdb = kwargs.get('gdb', False)
        if not isinstance(gdb, bool):
            raise InterpreterException('Gdb option must be a boolean')
        timeout_multiplier = kwargs.get('timeout_multiplier', 1)
        if not isinstance(timeout_multiplier, int):
            raise InterpreterException('Timeout multiplier must be a number.')
        is_default = kwargs.get('is_default', False)
        if not isinstance(is_default, bool):
            raise InterpreterException('is_default option must be a boolean')
        if is_default:
            if self.build.test_setup_default_name is not None:
                raise InterpreterException('\'%s\' is already set as default. '
                                           'is_default can be set to true only once' % self.build.test_setup_default_name)
            self.build.test_setup_default_name = setup_name
        env = self.unpack_env_kwarg(kwargs)
        self.build.test_setups[setup_name] = build.TestSetup(exe_wrapper, gdb, timeout_multiplier, env)

    @permittedKwargs(permitted_kwargs['add_global_arguments'])
    @stringArgs
    def func_add_global_arguments(self, node, args, kwargs):
        for_machine = self.machine_from_native_kwarg(kwargs)
        self.add_global_arguments(node, self.build.global_args[for_machine], args, kwargs)

    @permittedKwargs(permitted_kwargs['add_global_link_arguments'])
    @stringArgs
    def func_add_global_link_arguments(self, node, args, kwargs):
        for_machine = self.machine_from_native_kwarg(kwargs)
        self.add_global_arguments(node, self.build.global_link_args[for_machine], args, kwargs)

    @permittedKwargs(permitted_kwargs['add_project_arguments'])
    @stringArgs
    def func_add_project_arguments(self, node, args, kwargs):
        for_machine = self.machine_from_native_kwarg(kwargs)
        self.add_project_arguments(node, self.build.projects_args[for_machine], args, kwargs)

    @permittedKwargs(permitted_kwargs['add_project_link_arguments'])
    @stringArgs
    def func_add_project_link_arguments(self, node, args, kwargs):
        for_machine = self.machine_from_native_kwarg(kwargs)
        self.add_project_arguments(node, self.build.projects_link_args[for_machine], args, kwargs)

    def warn_about_builtin_args(self, args):
        warnargs = ('/W1', '/W2', '/W3', '/W4', '/Wall', '-Wall', '-Wextra', '-Wpedantic')
        optargs = ('-O0', '-O2', '-O3', '-Os', '/O1', '/O2', '/Os')
        for arg in args:
            if arg in warnargs:
                mlog.warning('Consider using the built-in warning_level option instead of using "{}".'.format(arg),
                             location=self.current_node)
            elif arg in optargs:
                mlog.warning('Consider using the built-in optimization level instead of using "{}".'.format(arg),
                             location=self.current_node)
            elif arg == '-g':
                mlog.warning('Consider using the built-in debug option instead of using "{}".'.format(arg),
                             location=self.current_node)
            elif arg == '-pipe':
                mlog.warning("You don't need to add -pipe, Meson will use it automatically when it is available.",
                             location=self.current_node)
            elif arg.startswith('-fsanitize'):
                mlog.warning('Consider using the built-in option for sanitizers instead of using "{}".'.format(arg),
                             location=self.current_node)
            elif arg.startswith('-std=') or arg.startswith('/std:'):
                mlog.warning('Consider using the built-in option for language standard version instead of using "{}".'.format(arg),
                             location=self.current_node)

    def add_global_arguments(self, node, argsdict, args, kwargs):
        if self.is_subproject():
            msg = 'Function \'{}\' cannot be used in subprojects because ' \
                  'there is no way to make that reliable.\nPlease only call ' \
                  'this if is_subproject() returns false. Alternatively, ' \
                  'define a variable that\ncontains your language-specific ' \
                  'arguments and add it to the appropriate *_args kwarg ' \
                  'in each target.'.format(node.func_name)
            raise InvalidCode(msg)
        frozen = self.project_args_frozen or self.global_args_frozen
        self.add_arguments(node, argsdict, frozen, args, kwargs)

    def add_project_arguments(self, node, argsdict, args, kwargs):
        if self.subproject not in argsdict:
            argsdict[self.subproject] = {}
        self.add_arguments(node, argsdict[self.subproject],
                           self.project_args_frozen, args, kwargs)

    def add_arguments(self, node, argsdict, args_frozen, args, kwargs):
        if args_frozen:
            msg = 'Tried to use \'{}\' after a build target has been declared.\n' \
                  'This is not permitted. Please declare all ' \
                  'arguments before your targets.'.format(node.func_name)
            raise InvalidCode(msg)

        if 'language' not in kwargs:
            raise InvalidCode('Missing language definition in {}'.format(node.func_name))

        self.warn_about_builtin_args(args)

        for lang in mesonlib.stringlistify(kwargs['language']):
            lang = lang.lower()
            argsdict[lang] = argsdict.get(lang, []) + args

    @noKwargs
    @noArgsFlattening
    def func_environment(self, node, args, kwargs):
        if len(args) > 1:
            raise InterpreterException('environment takes only one optional positional arguments')
        elif len(args) == 1:
            FeatureNew.single_use('environment positional arguments', '0.52.0', self.subproject)
            initial_values = args[0]
            if not isinstance(initial_values, dict) and not isinstance(initial_values, list):
                raise InterpreterException('environment first argument must be a dictionary or a list')
        else:
            initial_values = {}
        return EnvironmentVariablesHolder(initial_values)

    @stringArgs
    @noKwargs
    def func_join_paths(self, node, args, kwargs):
        return self.join_path_strings(args)

    def run(self) -> None:
        super().run()
        mlog.log('Build targets in project:', mlog.bold(str(len(self.build.targets))))
        FeatureNew.report(self.subproject)
        FeatureDeprecated.report(self.subproject)
        if not self.is_subproject():
            self.print_extra_warnings()
        if self.subproject == '':
            self._print_summary()

    def print_extra_warnings(self) -> None:
        # TODO cross compilation
        for c in self.coredata.compilers.host.values():
            if c.get_id() == 'clang':
                self.check_clang_asan_lundef()
                break

    def check_clang_asan_lundef(self) -> None:
        if 'b_lundef' not in self.coredata.base_options:
            return
        if 'b_sanitize' not in self.coredata.base_options:
            return
        if (self.coredata.base_options['b_lundef'].value and
                self.coredata.base_options['b_sanitize'].value != 'none'):
            mlog.warning('''Trying to use {} sanitizer on Clang with b_lundef.
This will probably not work.
Try setting b_lundef to false instead.'''.format(self.coredata.base_options['b_sanitize'].value),
                         location=self.current_node)

    def evaluate_subproject_info(self, path_from_source_root, subproject_dir):
        depth = 0
        subproj_name = ''
        segs = PurePath(path_from_source_root).parts
        segs_spd = PurePath(subproject_dir).parts
        while segs and segs[0] == segs_spd[0]:
            if len(segs_spd) == 1:
                subproj_name = segs[1]
                segs = segs[2:]
                depth += 1
            else:
                segs_spd = segs_spd[1:]
                segs = segs[1:]
        return (depth, subproj_name)

    # Check that the indicated file is within the same subproject
    # as we currently are. This is to stop people doing
    # nasty things like:
    #
    # f = files('../../master_src/file.c')
    #
    # Note that this is validated only when the file
    # object is generated. The result can be used in a different
    # subproject than it is defined in (due to e.g. a
    # declare_dependency).
    def validate_within_subproject(self, subdir, fname):
        norm = os.path.normpath(os.path.join(subdir, fname))
        if os.path.isabs(norm):
            if not norm.startswith(self.environment.source_dir):
                # Grabbing files outside the source tree is ok.
                # This is for vendor stuff like:
                #
                # /opt/vendorsdk/src/file_with_license_restrictions.c
                return
            norm = os.path.relpath(norm, self.environment.source_dir)
            assert(not os.path.isabs(norm))
        (num_sps, sproj_name) = self.evaluate_subproject_info(norm, self.subproject_dir)
        plain_filename = os.path.basename(norm)
        if num_sps == 0:
            if not self.is_subproject():
                return
            raise InterpreterException('Sandbox violation: Tried to grab file %s from a different subproject.' % plain_filename)
        if num_sps > 1:
            raise InterpreterException('Sandbox violation: Tried to grab file %s from a nested subproject.' % plain_filename)
        if sproj_name != self.subproject_directory_name:
            raise InterpreterException('Sandbox violation: Tried to grab file %s from a different subproject.' % plain_filename)

    def source_strings_to_files(self, sources):
        results = []
        mesonlib.check_direntry_issues(sources)
        if not isinstance(sources, list):
            sources = [sources]
        for s in sources:
            if isinstance(s, (mesonlib.File, GeneratedListHolder,
                              TargetHolder, CustomTargetIndexHolder,
                              GeneratedObjectsHolder)):
                pass
            elif isinstance(s, str):
                self.validate_within_subproject(self.subdir, s)
                s = mesonlib.File.from_source_file(self.environment.source_dir, self.subdir, s)
            else:
                raise InterpreterException('Source item is {!r} instead of '
                                           'string or File-type object'.format(s))
            results.append(s)
        return results

    def add_target(self, name, tobj):
        if name == '':
            raise InterpreterException('Target name must not be empty.')
        if name.strip() == '':
            raise InterpreterException('Target name must not consist only of whitespace.')
        if name.startswith('meson-'):
            raise InvalidArguments("Target names starting with 'meson-' are reserved "
                                   "for Meson's internal use. Please rename.")
        if name in coredata.FORBIDDEN_TARGET_NAMES:
            raise InvalidArguments("Target name '%s' is reserved for Meson's "
                                   "internal use. Please rename." % name)
        # To permit an executable and a shared library to have the
        # same name, such as "foo.exe" and "libfoo.a".
        idname = tobj.get_id()
        if idname in self.build.targets:
            raise InvalidCode('Tried to create target "%s", but a target of that name already exists.' % name)
        self.build.targets[idname] = tobj
        if idname not in self.coredata.target_guids:
            self.coredata.target_guids[idname] = str(uuid.uuid4()).upper()

    @FeatureNew('both_libraries', '0.46.0')
    def build_both_libraries(self, node, args, kwargs):
        shared_holder = self.build_target(node, args, kwargs, SharedLibraryHolder)

        # Check if user forces non-PIC static library.
        pic = True
        if 'pic' in kwargs:
            pic = kwargs['pic']
        elif 'b_staticpic' in self.environment.coredata.base_options:
            pic = self.environment.coredata.base_options['b_staticpic'].value

        if pic:
            # Exclude sources from args and kwargs to avoid building them twice
            static_args = [args[0]]
            static_kwargs = kwargs.copy()
            static_kwargs['sources'] = []
            static_kwargs['objects'] = shared_holder.held_object.extract_all_objects()
        else:
            static_args = args
            static_kwargs = kwargs

        static_holder = self.build_target(node, static_args, static_kwargs, StaticLibraryHolder)

        return BothLibrariesHolder(shared_holder, static_holder, self)

    def build_library(self, node, args, kwargs):
        default_library = self.coredata.get_builtin_option('default_library', self.subproject)
        if default_library == 'shared':
            return self.build_target(node, args, kwargs, SharedLibraryHolder)
        elif default_library == 'static':
            return self.build_target(node, args, kwargs, StaticLibraryHolder)
        elif default_library == 'both':
            return self.build_both_libraries(node, args, kwargs)
        else:
            raise InterpreterException('Unknown default_library value: %s.', default_library)

    def build_target(self, node, args, kwargs, targetholder):
        @FeatureNewKwargs('build target', '0.42.0', ['rust_crate_type', 'build_rpath', 'implicit_include_directories'])
        @FeatureNewKwargs('build target', '0.41.0', ['rust_args'])
        @FeatureNewKwargs('build target', '0.40.0', ['build_by_default'])
        @FeatureNewKwargs('build target', '0.48.0', ['gnu_symbol_visibility'])
        def build_target_decorator_caller(self, node, args, kwargs):
            return True

        build_target_decorator_caller(self, node, args, kwargs)

        if not args:
            raise InterpreterException('Target does not have a name.')
        name, *sources = args
        for_machine = self.machine_from_native_kwarg(kwargs)
        if 'sources' in kwargs:
            sources += listify(kwargs['sources'])
        sources = self.source_strings_to_files(sources)
        objs = extract_as_list(kwargs, 'objects')
        kwargs['dependencies'] = extract_as_list(kwargs, 'dependencies')
        kwargs['install_mode'] = self._get_kwarg_install_mode(kwargs)
        if 'extra_files' in kwargs:
            ef = extract_as_list(kwargs, 'extra_files')
            kwargs['extra_files'] = self.source_strings_to_files(ef)
        self.check_sources_exist(os.path.join(self.source_root, self.subdir), sources)
        if targetholder == ExecutableHolder:
            targetclass = build.Executable
        elif targetholder == SharedLibraryHolder:
            targetclass = build.SharedLibrary
        elif targetholder == SharedModuleHolder:
            targetclass = build.SharedModule
        elif targetholder == StaticLibraryHolder:
            targetclass = build.StaticLibrary
        elif targetholder == JarHolder:
            targetclass = build.Jar
        else:
            mlog.debug('Unknown target type:', str(targetholder))
            raise RuntimeError('Unreachable code')
        self.kwarg_strings_to_includedirs(kwargs)

        # Filter out kwargs from other target types. For example 'soversion'
        # passed to library() when default_library == 'static'.
        kwargs = {k: v for k, v in kwargs.items() if k in targetclass.known_kwargs}

        kwargs['include_directories'] = self.extract_incdirs(kwargs)
        target = targetclass(name, self.subdir, self.subproject, for_machine, sources, objs, self.environment, kwargs)
        target.project_version = self.project_version

        self.add_stdlib_info(target)
        l = targetholder(target, self)
        self.add_target(name, l.held_object)
        self.project_args_frozen = True
        return l

    def kwarg_strings_to_includedirs(self, kwargs):
        if 'd_import_dirs' in kwargs:
            items = mesonlib.extract_as_list(kwargs, 'd_import_dirs')
            cleaned_items = []
            for i in items:
                if isinstance(i, str):
                    # BW compatibility. This was permitted so we must support it
                    # for a few releases so people can transition to "correct"
                    # path declarations.
                    if os.path.normpath(i).startswith(self.environment.get_source_dir()):
                        mlog.warning('''Building a path to the source dir is not supported. Use a relative path instead.
This will become a hard error in the future.''', location=self.current_node)
                        i = os.path.relpath(i, os.path.join(self.environment.get_source_dir(), self.subdir))
                        i = self.build_incdir_object([i])
                cleaned_items.append(i)
            kwargs['d_import_dirs'] = cleaned_items

    def get_used_languages(self, target):
        result = set()
        for i in target.sources:
            for lang, c in self.coredata.compilers[target.for_machine].items():
                if c.can_compile(i):
                    result.add(lang)
                    break
        return result

    def add_stdlib_info(self, target):
        for l in self.get_used_languages(target):
            dep = self.build.stdlibs[target.for_machine].get(l, None)
            if dep:
                target.add_deps(dep)

    def check_sources_exist(self, subdir, sources):
        for s in sources:
            if not isinstance(s, str):
                continue # This means a generated source and they always exist.
            fname = os.path.join(subdir, s)
            if not os.path.isfile(fname):
                raise InterpreterException('Tried to add non-existing source file %s.' % s)

    # Only permit object extraction from the same subproject
    def validate_extraction(self, buildtarget: InterpreterObject) -> None:
        if self.subproject != buildtarget.subproject:
            raise InterpreterException('Tried to extract objects from a different subproject.')

    def is_subproject(self):
        return self.subproject != ''

    @noKwargs
    @noArgsFlattening
    def func_set_variable(self, node, args, kwargs):
        if len(args) != 2:
            raise InvalidCode('Set_variable takes two arguments.')
        varname, value = args
        self.set_variable(varname, value)

    @noKwargs
    @noArgsFlattening
    def func_get_variable(self, node, args, kwargs):
        if len(args) < 1 or len(args) > 2:
            raise InvalidCode('Get_variable takes one or two arguments.')
        varname = args[0]
        if isinstance(varname, Disabler):
            return varname
        if not isinstance(varname, str):
            raise InterpreterException('First argument must be a string.')
        try:
            return self.variables[varname]
        except KeyError:
            pass
        if len(args) == 2:
            return args[1]
        raise InterpreterException('Tried to get unknown variable "%s".' % varname)

    @stringArgs
    @noKwargs
    def func_is_variable(self, node, args, kwargs):
        if len(args) != 1:
            raise InvalidCode('Is_variable takes two arguments.')
        varname = args[0]
        return varname in self.variables

    @staticmethod
    def machine_from_native_kwarg(kwargs: T.Dict[str, T.Any]) -> MachineChoice:
        native = kwargs.get('native', False)
        if not isinstance(native, bool):
            raise InvalidArguments('Argument to "native" must be a boolean.')
        return MachineChoice.BUILD if native else MachineChoice.HOST

    @FeatureNew('is_disabler', '0.52.0')
    @noKwargs
    def func_is_disabler(self, node, args, kwargs):
        if len(args) != 1:
            raise InvalidCode('Is_disabler takes one argument.')
        varname = args[0]
        return isinstance(varname, Disabler)
