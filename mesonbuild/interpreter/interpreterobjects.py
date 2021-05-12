import os
import shlex
import subprocess
import re

from pathlib import Path, PurePath

from .. import mesonlib
from .. import coredata
from .. import build
from .. import mlog

from ..modules import ModuleReturnValue, ModuleObject, ModuleState
from ..backend.backends import TestProtocol
from ..interpreterbase import (InterpreterObject, ObjectHolder, MutableInterpreterObject,
                               FeatureNewKwargs, FeatureNew, FeatureDeprecated,
                               typed_pos_args, stringArgs, permittedKwargs,
                               noArgsFlattening, noPosargs, TYPE_var, TYPE_nkwargs,
                               flatten, InterpreterException, InvalidArguments, InvalidCode)
from ..dependencies import Dependency, ExternalLibrary, InternalDependency
from ..programs import ExternalProgram
from ..mesonlib import FileMode, OptionKey, listify, Popen_safe

import typing as T

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
            raise InvalidCode(f'Search directory {d} is not an absolute path.')
    return list(map(str, search_dirs))

class FeatureOptionHolder(InterpreterObject, ObjectHolder[coredata.UserFeatureOption]):
    def __init__(self, env: 'Environment', name: str, option: coredata.UserFeatureOption):
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, option)
        if option.is_auto():
            # TODO: we need to case here because options is not a TypedDict
            self.held_object = T.cast(coredata.UserFeatureOption, env.coredata.options[OptionKey('auto_features')])
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

class EnvironmentVariablesHolder(MutableInterpreterObject, ObjectHolder[build.EnvironmentVariables]):
    def __init__(self, initial_values=None, subproject: str = ''):
        MutableInterpreterObject.__init__(self)
        ObjectHolder.__init__(self, build.EnvironmentVariables(), subproject)
        self.methods.update({'set': self.set_method,
                             'append': self.append_method,
                             'prepend': self.prepend_method,
                             })
        if isinstance(initial_values, dict):
            for k, v in initial_values.items():
                self.set_method([k, v], {})
        elif initial_values is not None:
            for e in mesonlib.listify(initial_values):
                if not isinstance(e, str):
                    raise InterpreterException('Env var definition must be a list of strings.')
                if '=' not in e:
                    raise InterpreterException('Env var definition must be of type key=val.')
                (k, val) = e.split('=', 1)
                k = k.strip()
                val = val.strip()
                if ' ' in k:
                    raise InterpreterException('Env var key must not have spaces in it.')
                self.set_method([k, val], {})

    def __repr__(self) -> str:
        repr_str = "<{0}: {1}>"
        return repr_str.format(self.__class__.__name__, self.held_object.envvars)

    def unpack_separator(self, kwargs: T.Dict[str, T.Any]) -> str:
        separator = kwargs.get('separator', os.pathsep)
        if not isinstance(separator, str):
            raise InterpreterException("EnvironmentVariablesHolder methods 'separator'"
                                       " argument needs to be a string.")
        return separator

    def warn_if_has_name(self, name: str) -> None:
        # Multiple append/prepend operations was not supported until 0.58.0.
        if self.held_object.has_name(name):
            m = f'Overriding previous value of environment variable {name!r} with a new one'
            FeatureNew('0.58.0', m).use(self.subproject)

    @stringArgs
    @permittedKwargs({'separator'})
    @typed_pos_args('environment.set', str, varargs=str, min_varargs=1)
    def set_method(self, args: T.Tuple[str, T.List[str]], kwargs: T.Dict[str, T.Any]) -> None:
        name, values = args
        separator = self.unpack_separator(kwargs)
        self.held_object.set(name, values, separator)

    @stringArgs
    @permittedKwargs({'separator'})
    @typed_pos_args('environment.append', str, varargs=str, min_varargs=1)
    def append_method(self, args: T.Tuple[str, T.List[str]], kwargs: T.Dict[str, T.Any]) -> None:
        name, values = args
        separator = self.unpack_separator(kwargs)
        self.warn_if_has_name(name)
        self.held_object.append(name, values, separator)

    @stringArgs
    @permittedKwargs({'separator'})
    @typed_pos_args('environment.prepend', str, varargs=str, min_varargs=1)
    def prepend_method(self, args: T.Tuple[str, T.List[str]], kwargs: T.Dict[str, T.Any]) -> None:
        name, values = args
        separator = self.unpack_separator(kwargs)
        self.warn_if_has_name(name)
        self.held_object.prepend(name, values, separator)


class ConfigurationDataHolder(MutableInterpreterObject, ObjectHolder[build.ConfigurationData]):
    def __init__(self, pv, initial_values=None):
        MutableInterpreterObject.__init__(self)
        self.used = False # These objects become immutable after use in configure_file.
        ObjectHolder.__init__(self, build.ConfigurationData(), pv)
        self.methods.update({'set': self.set_method,
                             'set10': self.set10_method,
                             'set_quoted': self.set_quoted_method,
                             'has': self.has_method,
                             'get': self.get_method,
                             'keys': self.keys_method,
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

    @FeatureNew('configuration_data.keys()', '0.57.0')
    @noPosargs
    def keys_method(self, args, kwargs):
        return sorted(self.keys())

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

permitted_partial_dependency_kwargs = {
    'compile_args', 'link_args', 'links', 'includes', 'sources'
}

class DependencyHolder(InterpreterObject, ObjectHolder[Dependency]):
    def __init__(self, dep: Dependency, pv: str):
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
    @permittedKwargs(permitted_partial_dependency_kwargs)
    def partial_dependency_method(self, args, kwargs):
        pdep = self.held_object.get_partial_dependency(**kwargs)
        return DependencyHolder(pdep, self.subproject)

    @FeatureNew('dep.get_variable', '0.51.0')
    @typed_pos_args('dep.get_variable', optargs=[str])
    @permittedKwargs({'cmake', 'pkgconfig', 'configtool', 'internal', 'default_value', 'pkgconfig_define'})
    @FeatureNewKwargs('dep.get_variable', '0.54.0', ['internal'])
    def variable_method(self, args: T.Tuple[T.Optional[str]], kwargs: T.Dict[str, T.Any]) -> str:
        default_varname = args[0]
        if default_varname is not None:
            FeatureNew('0.58.0', 'Positional argument to dep.get_variable()').use(self.subproject)
            for k in ['cmake', 'pkgconfig', 'configtool', 'internal']:
                kwargs.setdefault(k, default_varname)
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

class ExternalProgramHolder(InterpreterObject, ObjectHolder[ExternalProgram]):
    def __init__(self, ep: ExternalProgram, subproject: str, backend=None):
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

class ExternalLibraryHolder(InterpreterObject, ObjectHolder[ExternalLibrary]):
    def __init__(self, el: ExternalLibrary, pv: str):
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
    @permittedKwargs(permitted_partial_dependency_kwargs)
    def partial_dependency_method(self, args, kwargs):
        pdep = self.held_object.get_partial_dependency(**kwargs)
        return DependencyHolder(pdep, self.subproject)

class GeneratorHolder(InterpreterObject, ObjectHolder[build.Generator]):
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


class GeneratedListHolder(InterpreterObject, ObjectHolder[build.GeneratedList]):
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
class MachineHolder(InterpreterObject, ObjectHolder['MachineInfo']):
    def __init__(self, machine_info: 'MachineInfo'):
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

class IncludeDirsHolder(InterpreterObject, ObjectHolder[build.IncludeDirs]):
    def __init__(self, idobj: build.IncludeDirs):
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, idobj)

class HeadersHolder(InterpreterObject, ObjectHolder[build.Headers]):

    def __init__(self, obj: build.Headers):
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, obj)

    def set_install_subdir(self, subdir):
        self.held_object.install_subdir = subdir

    def get_install_subdir(self):
        return self.held_object.install_subdir

    def get_sources(self):
        return self.held_object.sources

    def get_custom_install_dir(self):
        return self.held_object.custom_install_dir

    def get_custom_install_mode(self):
        return self.held_object.custom_install_mode

class DataHolder(InterpreterObject, ObjectHolder[build.Data]):
    def __init__(self, data: build.Data):
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, data)

    def get_source_subdir(self):
        return self.held_object.source_subdir

    def get_sources(self):
        return self.held_object.sources

    def get_install_dir(self):
        return self.held_object.install_dir

class InstallDirHolder(InterpreterObject, ObjectHolder[build.IncludeDirs]):

    def __init__(self, obj: build.InstallDir):
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, obj)

class ManHolder(InterpreterObject, ObjectHolder[build.Man]):

    def __init__(self, obj: build.Man):
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, obj)

    def get_custom_install_dir(self) -> T.Optional[str]:
        return self.held_object.custom_install_dir

    def get_custom_install_mode(self) -> T.Optional[FileMode]:
        return self.held_object.custom_install_mode

    def locale(self) -> T.Optional[str]:
        return self.held_object.locale

    def get_sources(self) -> T.List[mesonlib.File]:
        return self.held_object.sources

class GeneratedObjectsHolder(InterpreterObject, ObjectHolder[build.ExtractedObjects]):
    def __init__(self, held_object: build.ExtractedObjects):
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, held_object)

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

class SubprojectHolder(InterpreterObject, ObjectHolder[T.Optional['Interpreter']]):

    def __init__(self, subinterpreter: T.Optional['Interpreter'], subdir: str, warnings=0, disabled_feature=None,
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

        raise InvalidArguments(f'Requested variable "{varname}" not found.')

class ModuleObjectHolder(InterpreterObject, ObjectHolder['ModuleObject']):
    def __init__(self, modobj: 'ModuleObject', interpreter: 'Interpreter'):
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, modobj)
        self.interpreter = interpreter

    def method_call(self, method_name, args, kwargs):
        modobj = self.held_object
        method = modobj.methods.get(method_name)
        if not method and not modobj.methods:
            # FIXME: Port all modules to use the methods dict.
            method = getattr(modobj, method_name, None)
            if method_name.startswith('_'):
                raise InvalidArguments(f'Method {method_name!r} is private.')
        if not method:
            raise InvalidCode('Unknown method "%s" in object.' % method_name)
        if not getattr(method, 'no-args-flattening', False):
            args = flatten(args)
        state = ModuleState(self.interpreter)
        # Many modules do for example self.interpreter.find_program_impl(),
        # so we have to ensure they use the current interpreter and not the one
        # that first imported that module, otherwise it will use outdated
        # overrides.
        modobj.interpreter = self.interpreter
        if method_name in modobj.snippets:
            ret = method(self.interpreter, state, args, kwargs)
        else:
            # This is not 100% reliable but we can't use hash()
            # because the Build object contains dicts and lists.
            num_targets = len(self.interpreter.build.targets)
            ret = method(state, args, kwargs)
            if num_targets != len(self.interpreter.build.targets):
                raise InterpreterException('Extension module altered internal state illegally.')
            if isinstance(ret, ModuleReturnValue):
                self.interpreter.process_new_values(ret.new_objects)
                ret = ret.return_value
        return self.interpreter.holderify(ret)

_Target = T.TypeVar('_Target', bound=build.Target)


class TargetHolder(InterpreterObject, ObjectHolder[_Target]):
    def __init__(self, target: _Target, interp: 'Interpreter'):
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, target, interp.subproject)
        self.interpreter = interp


_BuildTarget = T.TypeVar('_BuildTarget', bound=build.BuildTarget)

class BuildTargetHolder(TargetHolder[_BuildTarget]):
    def __init__(self, target: _BuildTarget, interp: 'Interpreter'):
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

class ExecutableHolder(BuildTargetHolder[build.Executable]):
    pass

class StaticLibraryHolder(BuildTargetHolder[build.StaticLibrary]):
    pass

class SharedLibraryHolder(BuildTargetHolder[build.SharedLibrary]):
    def __init__(self, target: build.SharedLibrary, interp: 'Interpreter'):
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

class SharedModuleHolder(BuildTargetHolder[build.SharedModule]):
    pass

class JarHolder(BuildTargetHolder[build.Jar]):
    pass

class CustomTargetIndexHolder(TargetHolder[build.CustomTargetIndex]):
    def __init__(self, target: build.CustomTargetIndex, interp: 'Interpreter'):
        super().__init__(target, interp)
        self.methods.update({'full_path': self.full_path_method,
                             })

    @FeatureNew('custom_target[i].full_path', '0.54.0')
    @noPosargs
    @permittedKwargs({})
    def full_path_method(self, args, kwargs):
        return self.interpreter.backend.get_target_filename_abs(self.held_object)

class CustomTargetHolder(TargetHolder):
    def __init__(self, target: 'build.CustomTarget', interp: 'Interpreter'):
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
