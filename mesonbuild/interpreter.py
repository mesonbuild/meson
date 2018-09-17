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
from .mesonlib import FileMode, Popen_safe, listify, extract_as_list, has_path_sep
from .dependencies import ExternalProgram
from .dependencies import InternalDependency, Dependency, NotFoundDependency, DependencyException
from .interpreterbase import InterpreterBase
from .interpreterbase import check_stringlist, flatten, noPosargs, noKwargs, stringArgs, permittedKwargs, noArgsFlattening
from .interpreterbase import InterpreterException, InvalidArguments, InvalidCode, SubdirDoneRequest
from .interpreterbase import InterpreterObject, MutableInterpreterObject, Disabler
from .interpreterbase import FeatureNew, FeatureDeprecated, FeatureNewKwargs
from .modules import ModuleReturnValue

import os, sys, shutil, uuid
import re, shlex
import subprocess
from collections import namedtuple
from pathlib import PurePath
import traceback

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


class ObjectHolder:
    def __init__(self, obj, subproject=None):
        self.held_object = obj
        self.subproject = subproject

    def __repr__(self):
        return '<Holder: {!r}>'.format(self.held_object)

class FeatureOptionHolder(InterpreterObject, ObjectHolder):
    def __init__(self, env, option):
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, option)
        if option.is_auto():
            self.held_object = env.coredata.builtins['auto_features']
        self.name = option.name
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

def extract_required_kwarg(kwargs, subproject, feature_check=None):
    val = kwargs.get('required', True)
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
    elif isinstance(required, bool):
        required = val
    else:
        raise InterpreterException('required keyword argument must be boolean or a feature option')

    # Keep boolean value in kwargs to simplify other places where this kwarg is
    # checked.
    kwargs['required'] = required

    return disabled, required, feature

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

    def __init__(self, cmd, args, source_dir, build_dir, subdir, mesonintrospect, in_builddir=False, check=False, capture=True):
        super().__init__()
        if not isinstance(cmd, ExternalProgram):
            raise AssertionError('BUG: RunProcess must be passed an ExternalProgram')
        self.capture = capture
        pc, self.stdout, self.stderr = self.run_command(cmd, args, source_dir, build_dir, subdir, mesonintrospect, in_builddir, check)
        self.returncode = pc.returncode
        self.methods.update({'returncode': self.returncode_method,
                             'stdout': self.stdout_method,
                             'stderr': self.stderr_method,
                             })

    def run_command(self, cmd, args, source_dir, build_dir, subdir, mesonintrospect, in_builddir, check=False):
        command_array = cmd.get_command() + args
        env = {'MESON_SOURCE_ROOT': source_dir,
               'MESON_BUILD_ROOT': build_dir,
               'MESON_SUBDIR': subdir,
               'MESONINTROSPECT': ' '.join([shlex.quote(x) for x in mesonintrospect]),
               }
        if in_builddir:
            cwd = os.path.join(build_dir, subdir)
        else:
            cwd = os.path.join(source_dir, subdir)
        child_env = os.environ.copy()
        child_env.update(env)
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
    def __init__(self):
        MutableInterpreterObject.__init__(self)
        ObjectHolder.__init__(self, build.EnvironmentVariables())
        self.methods.update({'set': self.set_method,
                             'append': self.append_method,
                             'prepend': self.prepend_method,
                             })

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
        self.held_object.envvars.append((method, args[0], args[1:], kwargs))

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
    def __init__(self, pv):
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

    def is_used(self):
        return self.used

    def mark_used(self):
        self.used = True

    def validate_args(self, args, kwargs):
        if len(args) == 1 and isinstance(args[0], list) and len(args[0]) == 2:
            mlog.deprecation('Passing a list as the single argument to '
                             'configuration_data.set is deprecated. This will '
                             'become a hard error in the future.')
            args = args[0]

        if len(args) != 2:
            raise InterpreterException("Configuration set requires 2 arguments.")
        if self.used:
            raise InterpreterException("Can not set values on configuration object that has been used.")
        name = args[0]
        val = args[1]
        if not isinstance(val, (int, str)):
            msg = 'Setting a configuration data value to {!r} is invalid, ' \
                  'and will fail at configure_file(). If you are using it ' \
                  'just to store some values, please use a dict instead.'
            mlog.deprecation(msg.format(val))
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
                             'partial_dependency': self.partial_dependency_method,
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

class InternalDependencyHolder(InterpreterObject, ObjectHolder):
    def __init__(self, dep, pv):
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, dep, pv)
        self.methods.update({'found': self.found_method,
                             'version': self.version_method,
                             'partial_dependency': self.partial_dependency_method,
                             })

    @noPosargs
    @permittedKwargs({})
    def found_method(self, args, kwargs):
        return True

    @noPosargs
    @permittedKwargs({})
    def version_method(self, args, kwargs):
        return self.held_object.get_version()

    @FeatureNew('dep.partial_dependency', '0.46.0')
    @noPosargs
    @permittedKwargs(permitted_method_kwargs['partial_dependency'])
    def partial_dependency_method(self, args, kwargs):
        pdep = self.held_object.get_partial_dependency(**kwargs)
        return DependencyHolder(pdep, self.subproject)

class ExternalProgramHolder(InterpreterObject, ObjectHolder):
    def __init__(self, ep):
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, ep)
        self.methods.update({'found': self.found_method,
                             'path': self.path_method})

    @noPosargs
    @permittedKwargs({})
    def found_method(self, args, kwargs):
        return self.found()

    @noPosargs
    @permittedKwargs({})
    def path_method(self, args, kwargs):
        return self.held_object.get_path()

    def found(self):
        return isinstance(self.held_object, build.Executable) or self.held_object.found()

    def get_command(self):
        return self.held_object.get_command()

    def get_name(self):
        return self.held_object.get_name()

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
    def __init__(self, arg1, extra_args=[]):
        InterpreterObject.__init__(self)
        if isinstance(arg1, GeneratorHolder):
            ObjectHolder.__init__(self, build.GeneratedList(arg1.held_object, extra_args))
        else:
            ObjectHolder.__init__(self, arg1)

    def __repr__(self):
        r = '<{}: {!r}>'
        return r.format(self.__class__.__name__, self.held_object.get_outputs())

    def add_file(self, a):
        self.held_object.add_file(a)

class BuildMachine(InterpreterObject, ObjectHolder):
    def __init__(self, compilers):
        self.compilers = compilers
        InterpreterObject.__init__(self)
        held_object = environment.MachineInfo(environment.detect_system(),
                                              environment.detect_cpu_family(self.compilers),
                                              environment.detect_cpu(self.compilers),
                                              sys.byteorder)
        ObjectHolder.__init__(self, held_object)
        self.methods.update({'system': self.system_method,
                             'cpu_family': self.cpu_family_method,
                             'cpu': self.cpu_method,
                             'endian': self.endian_method,
                             })

    @noPosargs
    @permittedKwargs({})
    def cpu_family_method(self, args, kwargs):
        return self.held_object.cpu_family

    @noPosargs
    @permittedKwargs({})
    def cpu_method(self, args, kwargs):
        return self.held_object.cpu

    @noPosargs
    @permittedKwargs({})
    def system_method(self, args, kwargs):
        return self.held_object.system

    @noPosargs
    @permittedKwargs({})
    def endian_method(self, args, kwargs):
        return self.held_object.endian

# This class will provide both host_machine and
# target_machine
class CrossMachineInfo(InterpreterObject, ObjectHolder):
    def __init__(self, cross_info):
        InterpreterObject.__init__(self)
        minimum_cross_info = {'cpu', 'cpu_family', 'endian', 'system'}
        if set(cross_info) < minimum_cross_info:
            raise InterpreterException(
                'Machine info is currently {}\n'.format(cross_info) +
                'but is missing {}.'.format(minimum_cross_info - set(cross_info)))
        self.info = cross_info
        minfo = environment.MachineInfo(cross_info['system'],
                                        cross_info['cpu_family'],
                                        cross_info['cpu'],
                                        cross_info['endian'])
        ObjectHolder.__init__(self, minfo)
        self.methods.update({'system': self.system_method,
                             'cpu': self.cpu_method,
                             'cpu_family': self.cpu_family_method,
                             'endian': self.endian_method,
                             })

    @noPosargs
    @permittedKwargs({})
    def cpu_family_method(self, args, kwargs):
        return self.held_object.cpu_family

    @noPosargs
    @permittedKwargs({})
    def cpu_method(self, args, kwargs):
        return self.held_object.cpu

    @noPosargs
    @permittedKwargs({})
    def system_method(self, args, kwargs):
        return self.held_object.system

    @noPosargs
    @permittedKwargs({})
    def endian_method(self, args, kwargs):
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
    def __init__(self, src_subdir, inst_subdir, install_dir, install_mode, exclude, strip_directory):
        InterpreterObject.__init__(self)
        self.source_subdir = src_subdir
        self.installable_subdir = inst_subdir
        self.install_dir = install_dir
        self.install_mode = install_mode
        self.exclude = exclude
        self.strip_directory = strip_directory

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
        return self.held_object.is_cross()

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
                         'the default will be changed in the future.')
        return GeneratedObjectsHolder(gobjs)

    @noPosargs
    @permittedKwargs({})
    def get_id_method(self, args, kwargs):
        return self.held_object.get_id()

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

class CustomTargetIndexHolder(InterpreterObject, ObjectHolder):
    def __init__(self, object_to_hold):
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, object_to_hold)

class CustomTargetHolder(TargetHolder):
    def __init__(self, target, interp):
        super().__init__(target, interp)
        self.methods.update({'full_path': self.full_path_method,
                             })

    def __repr__(self):
        r = '<{} {}: {}>'
        h = self.held_object
        return r.format(self.__class__.__name__, h.get_id(), h.command)

    @noPosargs
    @permittedKwargs({})
    def full_path_method(self, args, kwargs):
        return self.interpreter.backend.get_target_filename_abs(self.held_object)

    def __getitem__(self, index):
        return CustomTargetIndexHolder(self.held_object[index])

    def __setitem__(self, index, value):
        raise InterpreterException('Cannot set a member of a CustomTarget')

    def __delitem__(self, index):
        raise InterpreterException('Cannot delete a member of a CustomTarget')

    def outdir_include(self):
        return IncludeDirsHolder(build.IncludeDirs('', [], False,
                                                   [os.path.join('@BUILD_ROOT@', self.interpreter.backend.get_target_dir(self.held_object))]))

class RunTargetHolder(InterpreterObject, ObjectHolder):
    def __init__(self, name, command, args, dependencies, subdir, subproject):
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, build.RunTarget(name, command, args, dependencies, subdir, subproject))

    def __repr__(self):
        r = '<{} {}: {}>'
        h = self.held_object
        return r.format(self.__class__.__name__, h.get_id(), h.command)

class Test(InterpreterObject):
    def __init__(self, name, project, suite, exe, depends, is_parallel,
                 cmd_args, env, should_fail, timeout, workdir):
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

    def get_exe(self):
        return self.exe

    def get_name(self):
        return self.name

class SubprojectHolder(InterpreterObject, ObjectHolder):

    def __init__(self, subinterpreter, subproject_dir, name):
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, subinterpreter)
        self.name = name
        self.subproject_dir = subproject_dir
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
    def get_variable_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Get_variable takes one argument.')
        if not self.found():
            raise InterpreterException('Subproject "%s/%s" disabled can\'t get_variable on it.' % (
                self.subproject_dir, self.name))
        varname = args[0]
        if not isinstance(varname, str):
            raise InterpreterException('Get_variable takes a string argument.')
        if varname not in self.held_object.variables:
            raise InvalidArguments('Requested variable "{0}" not found.'.format(varname))
        return self.held_object.variables[varname]

class CompilerHolder(InterpreterObject):
    def __init__(self, compiler, env, subproject):
        InterpreterObject.__init__(self)
        self.compiler = compiler
        self.environment = env
        self.subproject = subproject
        self.methods.update({'compiles': self.compiles_method,
                             'links': self.links_method,
                             'get_id': self.get_id_method,
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
                             })

    @noPosargs
    @permittedKwargs({})
    def version_method(self, args, kwargs):
        return self.compiler.version

    @noPosargs
    @permittedKwargs({})
    def cmd_array_method(self, args, kwargs):
        return self.compiler.exelist

    def determine_args(self, kwargs):
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
            opts = self.environment.coredata.compiler_options
            args += self.compiler.get_option_compile_args(opts)
            args += self.compiler.get_option_link_args(opts)
        args += mesonlib.stringlistify(kwargs.get('args', []))
        return args

    def determine_dependencies(self, kwargs):
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
        return deps

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
            raise InterpreterException('Prefix argument of sizeof must be a string.')
        extra_args = mesonlib.stringlistify(kwargs.get('args', []))
        deps = self.determine_dependencies(kwargs)
        result = self.compiler.alignment(typename, prefix, self.environment, extra_args, deps)
        mlog.log('Checking for alignment of', mlog.bold(typename, True), ':', result)
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
        extra_args = self.determine_args(kwargs)
        deps = self.determine_dependencies(kwargs)
        result = self.compiler.run(code, self.environment, extra_args, deps)
        if len(testname) > 0:
            if not result.compiled:
                h = mlog.red('DID NOT COMPILE')
            elif result.returncode == 0:
                h = mlog.green('YES')
            else:
                h = mlog.red('NO (%d)' % result.returncode)
            mlog.log('Checking if', mlog.bold(testname, True), 'runs:', h)
        return TryRunResultHolder(result)

    @noPosargs
    @permittedKwargs({})
    def get_id_method(self, args, kwargs):
        return self.compiler.get_id()

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
        typename = args[0]
        membername = args[1]
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of has_member must be a string.')
        extra_args = self.determine_args(kwargs)
        deps = self.determine_dependencies(kwargs)
        had = self.compiler.has_members(typename, [membername], prefix,
                                        self.environment, extra_args, deps)
        if had:
            hadtxt = mlog.green('YES')
        else:
            hadtxt = mlog.red('NO')
        mlog.log('Checking whether type', mlog.bold(typename, True),
                 'has member', mlog.bold(membername, True), ':', hadtxt)
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
        typename = args[0]
        membernames = args[1:]
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of has_members must be a string.')
        extra_args = self.determine_args(kwargs)
        deps = self.determine_dependencies(kwargs)
        had = self.compiler.has_members(typename, membernames, prefix,
                                        self.environment, extra_args, deps)
        if had:
            hadtxt = mlog.green('YES')
        else:
            hadtxt = mlog.red('NO')
        members = mlog.bold(', '.join(['"{}"'.format(m) for m in membernames]))
        mlog.log('Checking whether type', mlog.bold(typename, True),
                 'has members', members, ':', hadtxt)
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
        deps = self.determine_dependencies(kwargs)
        had = self.compiler.has_function(funcname, prefix, self.environment, extra_args, deps)
        if had:
            hadtxt = mlog.green('YES')
        else:
            hadtxt = mlog.red('NO')
        mlog.log('Checking for function', mlog.bold(funcname, True), ':', hadtxt)
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
        extra_args = self.determine_args(kwargs)
        deps = self.determine_dependencies(kwargs)
        had = self.compiler.has_type(typename, prefix, self.environment, extra_args, deps)
        if had:
            hadtxt = mlog.green('YES')
        else:
            hadtxt = mlog.red('NO')
        mlog.log('Checking for type', mlog.bold(typename, True), ':', hadtxt)
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
        extra_args = self.determine_args(kwargs)
        deps = self.determine_dependencies(kwargs)
        res = self.compiler.compute_int(expression, low, high, guess, prefix, self.environment, extra_args, deps)
        mlog.log('Computing int of "%s": %d' % (expression, res))
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
        extra_args = self.determine_args(kwargs)
        deps = self.determine_dependencies(kwargs)
        esize = self.compiler.sizeof(element, prefix, self.environment, extra_args, deps)
        mlog.log('Checking for size of "%s": %d' % (element, esize))
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
        extra_args = self.determine_args(kwargs)
        deps = self.determine_dependencies(kwargs)
        value = self.compiler.get_define(element, prefix, self.environment, extra_args, deps)
        mlog.log('Fetching value of define "%s": %s' % (element, value))
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
        extra_args = self.determine_args(kwargs)
        deps = self.determine_dependencies(kwargs)
        result = self.compiler.compiles(code, self.environment, extra_args, deps)
        if len(testname) > 0:
            if result:
                h = mlog.green('YES')
            else:
                h = mlog.red('NO')
            mlog.log('Checking if', mlog.bold(testname, True), 'compiles:', h)
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
        extra_args = self.determine_args(kwargs)
        deps = self.determine_dependencies(kwargs)
        result = self.compiler.links(code, self.environment, extra_args, deps)
        if len(testname) > 0:
            if result:
                h = mlog.green('YES')
            else:
                h = mlog.red('NO')
            mlog.log('Checking if', mlog.bold(testname, True), 'links:', h)
        return result

    @FeatureNew('compiler.check_header', '0.47.0')
    @permittedKwargs({
        'prefix',
        'no_builtin_args',
        'include_directories',
        'args',
        'dependencies',
    })
    def check_header_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('check_header method takes exactly one argument.')
        check_stringlist(args)
        hname = args[0]
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of has_header must be a string.')
        extra_args = self.determine_args(kwargs)
        deps = self.determine_dependencies(kwargs)
        haz = self.compiler.check_header(hname, prefix, self.environment, extra_args, deps)
        if haz:
            h = mlog.green('YES')
        else:
            h = mlog.red('NO')
        mlog.log('Check usable header "%s":' % hname, h)
        return haz

    @permittedKwargs({
        'prefix',
        'no_builtin_args',
        'include_directories',
        'args',
        'dependencies',
    })
    def has_header_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('has_header method takes exactly one argument.')
        check_stringlist(args)
        hname = args[0]
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of has_header must be a string.')
        extra_args = self.determine_args(kwargs)
        deps = self.determine_dependencies(kwargs)
        haz = self.compiler.has_header(hname, prefix, self.environment, extra_args, deps)
        if haz:
            h = mlog.green('YES')
        else:
            h = mlog.red('NO')
        mlog.log('Has header "%s":' % hname, h)
        return haz

    @permittedKwargs({
        'prefix',
        'no_builtin_args',
        'include_directories',
        'args',
        'dependencies',
    })
    def has_header_symbol_method(self, args, kwargs):
        if len(args) != 2:
            raise InterpreterException('has_header_symbol method takes exactly two arguments.')
        check_stringlist(args)
        hname = args[0]
        symbol = args[1]
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of has_header_symbol must be a string.')
        extra_args = self.determine_args(kwargs)
        deps = self.determine_dependencies(kwargs)
        haz = self.compiler.has_header_symbol(hname, symbol, prefix, self.environment, extra_args, deps)
        if haz:
            h = mlog.green('YES')
        else:
            h = mlog.red('NO')
        mlog.log('Header <{0}> has symbol "{1}":'.format(hname, symbol), h)
        return haz

    @permittedKwargs({
        'required',
        'dirs',
    })
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
            lib = dependencies.ExternalLibrary(libname, None,
                                               self.environment,
                                               self.compiler.language,
                                               silent=True)
            return ExternalLibraryHolder(lib, self.subproject)

        search_dirs = mesonlib.stringlistify(kwargs.get('dirs', []))
        for i in search_dirs:
            if not os.path.isabs(i):
                raise InvalidCode('Search directory %s is not an absolute path.' % i)
        linkargs = self.compiler.find_library(libname, self.environment, search_dirs)
        if required and not linkargs:
            raise InterpreterException('{} library {!r} not found'.format(self.compiler.get_display_language(), libname))
        lib = dependencies.ExternalLibrary(libname, linkargs, self.environment,
                                           self.compiler.language)
        return ExternalLibraryHolder(lib, self.subproject)

    @permittedKwargs({})
    def has_argument_method(self, args, kwargs):
        args = mesonlib.stringlistify(args)
        if len(args) != 1:
            raise InterpreterException('has_argument takes exactly one argument.')
        return self.has_multi_arguments_method(args, kwargs)

    @permittedKwargs({})
    def has_multi_arguments_method(self, args, kwargs):
        args = mesonlib.stringlistify(args)
        result = self.compiler.has_multi_arguments(args, self.environment)
        if result:
            h = mlog.green('YES')
        else:
            h = mlog.red('NO')
        mlog.log(
            'Compiler for {} supports arguments {}:'.format(
                self.compiler.get_display_language(), ' '.join(args)),
            h)
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
    def first_supported_argument_method(self, args, kwargs):
        for i in mesonlib.stringlistify(args):
            if self.has_argument_method(i, kwargs):
                mlog.log('First supported argument:', mlog.bold(i))
                return [i]
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
        result = self.compiler.has_multi_link_arguments(args, self.environment)
        if result:
            h = mlog.green('YES')
        else:
            h = mlog.red('NO')
        mlog.log(
            'Compiler for {} supports link arguments {}:'.format(
                self.compiler.get_display_language(), ' '.join(args)),
            h)
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
        result = self.compiler.has_func_attribute(args[0], self.environment)
        h = mlog.green('YES') if result else mlog.red('NO')
        mlog.log('Compiler for {} supports function attribute {}:'.format(self.compiler.get_display_language(), args[0]), h)
        return result

    @FeatureNew('compiler.get_supported_function_attributes', '0.48.0')
    @permittedKwargs({})
    def get_supported_function_attributes_method(self, args, kwargs):
        args = mesonlib.stringlistify(args)
        return [a for a in args if self.has_func_attribute_method(a, kwargs)]


ModuleState = namedtuple('ModuleState', [
    'build_to_src', 'subproject', 'subdir', 'current_lineno', 'environment',
    'project_name', 'project_version', 'backend', 'compilers', 'targets',
    'data', 'headers', 'man', 'global_args', 'project_args', 'build_machine',
    'host_machine', 'target_machine'])

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
            build_to_src=os.path.relpath(self.interpreter.environment.get_source_dir(),
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
            compilers=self.interpreter.build.compilers,
            targets=self.interpreter.build.targets,
            data=self.interpreter.build.data,
            headers=self.interpreter.build.get_headers(),
            man=self.interpreter.build.get_man(),
            global_args=self.interpreter.build.global_args,
            project_args=self.interpreter.build.projects_args.get(self.interpreter.subproject, {}),
            build_machine=self.interpreter.builtin['build_machine'].held_object,
            host_machine=self.interpreter.builtin['host_machine'].held_object,
            target_machine=self.interpreter.builtin['target_machine'].held_object,
        )
        if self.held_object.is_snippet(method_name):
            value = fn(self.interpreter, state, args, kwargs)
            return self.interpreter.holderify(value)
        else:
            value = fn(state, args, kwargs)
            if num_targets != len(self.interpreter.build.targets):
                raise InterpreterException('Extension module altered internal state illegally.')
            return self.interpreter.module_method_callback(value)

class MesonMain(InterpreterObject):
    def __init__(self, build, interpreter):
        InterpreterObject.__init__(self)
        self.build = build
        self.interpreter = interpreter
        self._found_source_scripts = {}
        self.methods.update({'get_compiler': self.get_compiler_method,
                             'is_cross_build': self.is_cross_build_method,
                             'has_exe_wrapper': self.has_exe_wrapper_method,
                             'is_unity': self.is_unity_method,
                             'is_subproject': self.is_subproject_method,
                             'current_source_dir': self.current_source_dir_method,
                             'current_build_dir': self.current_build_dir_method,
                             'source_root': self.source_root_method,
                             'build_root': self.build_root_method,
                             'add_install_script': self.add_install_script_method,
                             'add_postconf_script': self.add_postconf_script_method,
                             'add_dist_script': self.add_dist_script_method,
                             'install_dependency_manifest': self.install_dependency_manifest_method,
                             'override_find_program': self.override_find_program_method,
                             'project_version': self.project_version_method,
                             'project_license': self.project_license_method,
                             'version': self.version_method,
                             'project_name': self.project_name_method,
                             'get_cross_property': self.get_cross_property_method,
                             'backend': self.backend_method,
                             })

    def _find_source_script(self, name, args):
        # Prefer scripts in the current source directory
        search_dir = os.path.join(self.interpreter.environment.source_dir,
                                  self.interpreter.subdir)
        key = (name, search_dir)
        if key in self._found_source_scripts:
            found = self._found_source_scripts[key]
        else:
            found = dependencies.ExternalProgram(name, search_dir=search_dir)
            if found.found():
                self._found_source_scripts[key] = found
            else:
                m = 'Script or command {!r} not found or not executable'
                raise InterpreterException(m.format(name))
        return build.RunScript(found.get_command(), args)

    @permittedKwargs({})
    def add_install_script_method(self, args, kwargs):
        if len(args) < 1:
            raise InterpreterException('add_install_script takes one or more arguments')
        check_stringlist(args, 'add_install_script args must be strings')
        script = self._find_source_script(args[0], args[1:])
        self.build.install_scripts.append(script)

    @permittedKwargs({})
    def add_postconf_script_method(self, args, kwargs):
        if len(args) < 1:
            raise InterpreterException('add_postconf_script takes one or more arguments')
        check_stringlist(args, 'add_postconf_script arguments must be strings')
        script = self._find_source_script(args[0], args[1:])
        self.build.postconf_scripts.append(script)

    @permittedKwargs({})
    def add_dist_script_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('add_dist_script takes exactly one argument')
        check_stringlist(args, 'add_dist_script argument must be a string')
        if self.interpreter.subproject != '':
            raise InterpreterException('add_dist_script may not be used in a subproject.')
        self.build.dist_scripts.append(os.path.join(self.interpreter.subdir, args[0]))

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
    def source_root_method(self, args, kwargs):
        return self.interpreter.environment.source_dir

    @noPosargs
    @permittedKwargs({})
    def build_root_method(self, args, kwargs):
        return self.interpreter.environment.build_dir

    @noPosargs
    @permittedKwargs({})
    def has_exe_wrapper_method(self, args, kwargs):
        if self.is_cross_build_method(None, None) and \
           self.build.environment.cross_info.need_exe_wrapper():
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
        native = kwargs.get('native', None)
        if native is None:
            if self.build.environment.is_cross_build():
                native = False
            else:
                native = True
        if not isinstance(native, bool):
            raise InterpreterException('Type of "native" must be a boolean.')
        if native:
            clist = self.build.compilers
        else:
            clist = self.build.cross_compilers
        if cname in clist:
            return CompilerHolder(clist[cname], self.build.environment, self.interpreter.subproject)
        raise InterpreterException('Tried to access compiler for unspecified language "%s".' % cname)

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
        name = args[0]
        exe = args[1]
        if not isinstance(name, str):
            raise InterpreterException('First argument must be a string')
        if hasattr(exe, 'held_object'):
            exe = exe.held_object
        if isinstance(exe, mesonlib.File):
            abspath = exe.absolute_path(self.interpreter.environment.source_dir,
                                        self.interpreter.environment.build_dir)
            if not os.path.exists(abspath):
                raise InterpreterException('Tried to override %s with a file that does not exist.' % name)
            exe = dependencies.ExternalProgram(abspath)
        if not isinstance(exe, (dependencies.ExternalProgram, build.Executable)):
            raise InterpreterException('Second argument must be an external program or executable.')
        self.interpreter.add_find_program_override(name, exe)

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
        return coredata.version

    @noPosargs
    @permittedKwargs({})
    def project_name_method(self, args, kwargs):
        return self.interpreter.active_projectname

    @noArgsFlattening
    @permittedKwargs({})
    def get_cross_property_method(self, args, kwargs):
        if len(args) < 1 or len(args) > 2:
            raise InterpreterException('Must have one or two arguments.')
        propname = args[0]
        if not isinstance(propname, str):
            raise InterpreterException('Property name must be string.')
        try:
            props = self.interpreter.environment.cross_info.get_properties()
            return props[propname]
        except Exception:
            if len(args) == 2:
                return args[1]
            raise InterpreterException('Unknown cross property: %s.' % propname)


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

permitted_kwargs = {'add_global_arguments': {'language', 'native'},
                    'add_global_link_arguments': {'language', 'native'},
                    'add_languages': {'required'},
                    'add_project_link_arguments': {'language', 'native'},
                    'add_project_arguments': {'language', 'native'},
                    'add_test_setup': {'exe_wrapper', 'gdb', 'timeout_multiplier', 'env'},
                    'benchmark': {'args', 'env', 'should_fail', 'timeout', 'workdir', 'suite'},
                    'build_target': known_build_target_kwargs,
                    'configure_file': {'input', 'output', 'configuration', 'command', 'copy', 'install_dir', 'install_mode', 'capture', 'install', 'format', 'output_format', 'encoding'},
                    'custom_target': {'input', 'output', 'command', 'install', 'install_dir', 'install_mode', 'build_always', 'capture', 'depends', 'depend_files', 'depfile', 'build_by_default', 'build_always_stale', 'console'},
                    'dependency': {'default_options', 'fallback', 'language', 'main', 'method', 'modules', 'optional_modules', 'native', 'required', 'static', 'version', 'private_headers'},
                    'declare_dependency': {'include_directories', 'link_with', 'sources', 'dependencies', 'compile_args', 'link_args', 'link_whole', 'version'},
                    'executable': build.known_exe_kwargs,
                    'find_program': {'required', 'native'},
                    'generator': {'arguments', 'output', 'depfile', 'capture', 'preserve_path_from'},
                    'include_directories': {'is_system'},
                    'install_data': {'install_dir', 'install_mode', 'rename', 'sources'},
                    'install_headers': {'install_dir', 'install_mode', 'subdir'},
                    'install_man': {'install_dir', 'install_mode'},
                    'install_subdir': {'exclude_files', 'exclude_directories', 'install_dir', 'install_mode', 'strip_directory'},
                    'jar': build.known_jar_kwargs,
                    'project': {'version', 'meson_version', 'default_options', 'license', 'subproject_dir'},
                    'run_command': {'check', 'capture'},
                    'run_target': {'command', 'depends'},
                    'shared_library': build.known_shlib_kwargs,
                    'shared_module': build.known_shmod_kwargs,
                    'static_library': build.known_stlib_kwargs,
                    'both_libraries': known_library_kwargs,
                    'library': known_library_kwargs,
                    'subdir': {'if_found'},
                    'subproject': {'version', 'default_options', 'required'},
                    'test': {'args', 'depends', 'env', 'is_parallel', 'should_fail', 'timeout', 'workdir', 'suite'},
                    'vcs_tag': {'input', 'output', 'fallback', 'command', 'replace_string'},
                    }


class Interpreter(InterpreterBase):

    def __init__(self, build, backend=None, subproject='', subdir='', subproject_dir='subprojects',
                 modules = None, default_project_options=None, mock=False):
        super().__init__(build.environment.get_source_dir(), subdir)
        self.an_unpicklable_object = mesonlib.an_unpicklable_object
        self.build = build
        self.environment = build.environment
        self.coredata = self.environment.get_coredata()
        self.backend = backend
        self.subproject = subproject
        if modules is None:
            self.modules = {}
        else:
            self.modules = modules
        # Subproject directory is usually the name of the subproject, but can
        # be different for dependencies provided by wrap files.
        self.subproject_directory_name = subdir.split(os.path.sep)[-1]
        self.subproject_dir = subproject_dir
        self.option_file = os.path.join(self.source_root, self.subdir, 'meson_options.txt')
        if not mock:
            self.load_root_meson_file()
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
        self.builtin['build_machine'] = BuildMachine(self.coredata.compilers)
        if not self.build.environment.is_cross_build():
            self.builtin['host_machine'] = self.builtin['build_machine']
            self.builtin['target_machine'] = self.builtin['build_machine']
        else:
            cross_info = self.build.environment.cross_info
            if cross_info.has_host():
                self.builtin['host_machine'] = CrossMachineInfo(cross_info.config['host_machine'])
            else:
                self.builtin['host_machine'] = self.builtin['build_machine']
            if cross_info.has_target():
                self.builtin['target_machine'] = CrossMachineInfo(cross_info.config['target_machine'])
            else:
                self.builtin['target_machine'] = self.builtin['host_machine']

    def get_non_matching_default_options(self):
        env = self.environment
        for def_opt_name, def_opt_value in self.project_default_options.items():
            for option_type in [
                    env.coredata.builtins, env.coredata.compiler_options,
                    env.coredata.backend_options, env.coredata.base_options,
                    env.coredata.user_options]:
                for cur_opt_name, cur_opt_value in option_type.items():
                    if (def_opt_name == cur_opt_name and
                            def_opt_value != cur_opt_value.value):
                        yield (def_opt_name, def_opt_value, cur_opt_value.value)

    def build_func_dict(self):
        self.funcs.update({'add_global_arguments': self.func_add_global_arguments,
                           'add_project_arguments': self.func_add_project_arguments,
                           'add_global_link_arguments': self.func_add_global_link_arguments,
                           'add_project_link_arguments': self.func_add_project_link_arguments,
                           'add_test_setup': self.func_add_test_setup,
                           'add_languages': self.func_add_languages,
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
        if isinstance(item, build.CustomTarget):
            return CustomTargetHolder(item, self)
        elif isinstance(item, (int, str, bool)) or item is None:
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
        elif isinstance(item, dependencies.InternalDependency):
            return InternalDependencyHolder(item, self.subproject)
        elif isinstance(item, dependencies.ExternalDependency):
            return DependencyHolder(item, self.subproject)
        elif isinstance(item, dependencies.ExternalProgram):
            return ExternalProgramHolder(item)
        elif hasattr(item, 'held_object'):
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
                return ExternalProgramHolder(v)
            elif isinstance(v, dependencies.InternalDependency):
                # FIXME: This is special cased and not ideal:
                # The first source is our new VapiTarget, the rest are deps
                self.process_new_values(v.sources[0])
            elif hasattr(v, 'held_object'):
                pass
            elif isinstance(v, (int, str, bool)):
                pass
            else:
                raise InterpreterException('Module returned a value of unknown type.')

    def module_method_callback(self, return_object):
        if not isinstance(return_object, ModuleReturnValue):
            raise InterpreterException('Bug in module, it returned an invalid object')
        invalues = return_object.new_objects
        self.process_new_values(invalues)
        return self.holderify(return_object.return_value)

    def get_build_def_files(self):
        return self.build_def_files

    def get_variables(self):
        return self.variables

    def check_cross_stdlibs(self):
        if self.build.environment.is_cross_build():
            cross_info = self.build.environment.cross_info
            for l, c in self.build.cross_compilers.items():
                try:
                    di = mesonlib.stringlistify(cross_info.get_stdlib(l))
                    if len(di) != 2:
                        raise InterpreterException('Stdlib definition for %s should have exactly two elements.'
                                                   % l)
                    projname, depname = di
                    subproj = self.do_subproject(projname, {})
                    self.build.cross_stdlibs[l] = subproj.get_variable_method([depname], {})
                except KeyError:
                    pass
                except InvalidArguments:
                    pass

    @stringArgs
    @noKwargs
    def func_import(self, node, args, kwargs):
        if len(args) != 1:
            raise InvalidCode('Import takes one argument.')
        modname = args[0]
        if modname.startswith('unstable-'):
            plainname = modname.split('-', 1)[1]
            mlog.warning('Module %s has no backwards or forwards compatibility and might not exist in future releases.' % modname, location=node)
            modname = 'unstable_' + plainname
        if modname not in self.modules:
            try:
                module = importlib.import_module('mesonbuild.modules.' + modname)
            except ImportError:
                raise InvalidArguments('Module "%s" does not exist' % (modname, ))
            self.modules[modname] = module.initialize(self)
        return ModuleHolder(modname, self.modules[modname], self)

    @stringArgs
    @noKwargs
    def func_files(self, node, args, kwargs):
        return [mesonlib.File.from_source_file(self.environment.source_dir, self.subdir, fname) for fname in args]

    @FeatureNewKwargs('declare_dependency', '0.46.0', ['link_whole'])
    @permittedKwargs(permitted_kwargs['declare_dependency'])
    @noPosargs
    def func_declare_dependency(self, node, args, kwargs):
        version = kwargs.get('version', self.project_version)
        if not isinstance(version, str):
            raise InterpreterException('Version must be a string.')
        incs = extract_as_list(kwargs, 'include_directories', unholder=True)
        libs = extract_as_list(kwargs, 'link_with', unholder=True)
        libs_whole = extract_as_list(kwargs, 'link_whole', unholder=True)
        sources = extract_as_list(kwargs, 'sources')
        sources = listify(self.source_strings_to_files(sources), unholder=True)
        deps = extract_as_list(kwargs, 'dependencies', unholder=True)
        compile_args = mesonlib.stringlistify(kwargs.get('compile_args', []))
        link_args = mesonlib.stringlistify(kwargs.get('link_args', []))
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
                                              link_args, libs, libs_whole, sources, final_deps)
        return DependencyHolder(dep, self.subproject)

    @noKwargs
    def func_assert(self, node, args, kwargs):
        if len(args) != 2:
            raise InterpreterException('Assert takes exactly two arguments')
        value, message = args
        if not isinstance(value, bool):
            raise InterpreterException('Assert value not bool.')
        if not isinstance(message, str):
            raise InterpreterException('Assert message not a string.')
        if not value:
            raise InterpreterException('Assert failed: ' + message)

    def validate_arguments(self, args, argcount, arg_types):
        if argcount is not None:
            if argcount != len(args):
                raise InvalidArguments('Expected %d arguments, got %d.' %
                                       (argcount, len(args)))
        for i in range(min(len(args), len(arg_types))):
            wanted = arg_types[i]
            actual = args[i]
            if wanted is not None:
                if not isinstance(actual, wanted):
                    raise InvalidArguments('Incorrect argument type.')

    @FeatureNewKwargs('run_command', '0.47.0', ['check', 'capture'])
    @permittedKwargs(permitted_kwargs['run_command'])
    def func_run_command(self, node, args, kwargs):
        return self.run_command_impl(node, args, kwargs)

    def run_command_impl(self, node, args, kwargs, in_builddir=False):
        if len(args) < 1:
            raise InterpreterException('Not enough arguments')
        cmd = args[0]
        cargs = args[1:]
        capture = kwargs.get('capture', True)
        srcdir = self.environment.get_source_dir()
        builddir = self.environment.get_build_dir()

        check = kwargs.get('check', False)
        if not isinstance(check, bool):
            raise InterpreterException('Check must be boolean.')

        m = 'must be a string, or the output of find_program(), files() '\
            'or configure_file(), or a compiler object; not {!r}'
        if isinstance(cmd, ExternalProgramHolder):
            cmd = cmd.held_object
            if isinstance(cmd, build.Executable):
                progname = node.args.arguments[0].value
                msg = 'Program {!r} was overridden with the compiled executable {!r}'\
                      ' and therefore cannot be used during configuration'
                raise InterpreterException(msg.format(progname, cmd.description()))
        elif isinstance(cmd, CompilerHolder):
            cmd = cmd.compiler.get_exelist()[0]
            prog = ExternalProgram(cmd, silent=True)
            if not prog.found():
                raise InterpreterException('Program {!r} not found '
                                           'or not executable'.format(cmd))
            cmd = prog
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
        try:
            cmd_path = os.path.relpath(cmd.get_path(), start=srcdir)
        except ValueError:
            # On Windows a relative path can't be evaluated for
            # paths on two different drives (i.e. c:\foo and f:\bar).
            # The only thing left to is is to use the original absolute
            # path.
            cmd_path = cmd.get_path()
        if not cmd_path.startswith('..') and cmd_path not in self.build_def_files:
            self.build_def_files.append(cmd_path)
        expanded_args = []
        for a in listify(cargs):
            if isinstance(a, str):
                expanded_args.append(a)
            elif isinstance(a, mesonlib.File):
                expanded_args.append(a.absolute_path(srcdir, builddir))
            elif isinstance(a, ExternalProgramHolder):
                expanded_args.append(a.held_object.get_path())
            else:
                raise InterpreterException('Arguments ' + m.format(a))
        for a in expanded_args:
            if not os.path.isabs(a):
                a = os.path.join(builddir if in_builddir else srcdir, self.subdir, a)
            if os.path.isfile(a):
                a = os.path.relpath(a, start=srcdir)
                if not a.startswith('..'):
                    if a not in self.build_def_files:
                        self.build_def_files.append(a)
        return RunProcess(cmd, expanded_args, srcdir, builddir, self.subdir,
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
        dirname = args[0]
        return self.do_subproject(dirname, kwargs)

    def disabled_subproject(self, dirname):
        self.subprojects[dirname] = SubprojectHolder(None, self.subproject_dir, dirname)
        return self.subprojects[dirname]

    def do_subproject(self, dirname, kwargs):
        disabled, required, feature = extract_required_kwarg(kwargs, self.subproject)
        if disabled:
            mlog.log('\nSubproject', mlog.bold(dirname), ':', 'skipped: feature', mlog.bold(feature), 'disabled')
            return self.disabled_subproject(dirname)

        default_options = mesonlib.stringlistify(kwargs.get('default_options', []))
        default_options = coredata.create_options_dict(default_options)
        if dirname == '':
            raise InterpreterException('Subproject dir name must not be empty.')
        if dirname[0] == '.':
            raise InterpreterException('Subproject dir name must not start with a period.')
        if '..' in dirname:
            raise InterpreterException('Subproject name must not contain a ".." path segment.')
        if os.path.isabs(dirname):
            raise InterpreterException('Subproject name must not be an absolute path.')
        if has_path_sep(dirname):
            mlog.warning('Subproject name has a path separator. This may cause unexpected behaviour.')
        if dirname in self.subproject_stack:
            fullstack = self.subproject_stack + [dirname]
            incpath = ' => '.join(fullstack)
            raise InvalidCode('Recursive include of subprojects: %s.' % incpath)
        if dirname in self.subprojects:
            subproject = self.subprojects[dirname]

            if required and not subproject.found():
                raise InterpreterException('Subproject "%s/%s" required but not found.' % (
                                           self.subproject_dir, dirname))

            return subproject
        subproject_dir_abs = os.path.join(self.environment.get_source_dir(), self.subproject_dir)
        r = wrap.Resolver(subproject_dir_abs, self.coredata.wrap_mode)
        try:
            resolved = r.resolve(dirname)
        except RuntimeError as e:
            # if the reason subproject execution failed was because
            # the directory doesn't exist, try to give some helpful
            # advice if it's a nested subproject that needs
            # promotion...
            self.print_nested_info(dirname)

            if required:
                msg = 'Subproject directory {!r} does not exist and cannot be downloaded:\n{}'
                raise InterpreterException(msg.format(os.path.join(self.subproject_dir, dirname), e))

            mlog.log('\nSubproject ', mlog.bold(dirname), 'is buildable:', mlog.red('NO'), '(disabling)\n')
            return self.disabled_subproject(dirname)

        subdir = os.path.join(self.subproject_dir, resolved)
        os.makedirs(os.path.join(self.build.environment.get_build_dir(), subdir), exist_ok=True)
        self.global_args_frozen = True
        mlog.log()
        with mlog.nested():
            try:
                mlog.log('\nExecuting subproject', mlog.bold(dirname), '\n')
                subi = Interpreter(self.build, self.backend, dirname, subdir, self.subproject_dir,
                                   self.modules, default_options)
                subi.subprojects = self.subprojects

                subi.subproject_stack = self.subproject_stack + [dirname]
                current_active = self.active_projectname
                subi.run()
                mlog.log('\nSubproject', mlog.bold(dirname), 'finished.')
            except Exception as e:
                if not required:
                    mlog.log(e)
                    mlog.log('\nSubproject', mlog.bold(dirname), 'is buildable:', mlog.red('NO'), '(disabling)')
                    return self.disabled_subproject(dirname)
                else:
                    raise e

        if 'version' in kwargs:
            pv = subi.project_version
            wanted = kwargs['version']
            if pv == 'undefined' or not mesonlib.version_compare_many(pv, wanted)[0]:
                raise InterpreterException('Subproject %s version is %s but %s required.' % (dirname, pv, wanted))
        self.active_projectname = current_active
        self.build.subprojects[dirname] = subi.project_version
        self.subprojects.update(subi.subprojects)
        self.subprojects[dirname] = SubprojectHolder(subi, self.subproject_dir, dirname)
        self.build_def_files += subi.build_def_files
        return self.subprojects[dirname]

    def get_option_internal(self, optname):
        # Some base options are not defined in some environments, return the
        # default value from compilers.base_options in that case.
        for d in [self.coredata.base_options, compilers.base_options,
                  self.coredata.builtins, self.coredata.compiler_options]:
            try:
                return d[optname]
            except KeyError:
                pass

        raw_optname = optname
        if self.is_subproject():
            optname = self.subproject + ':' + optname

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
                                 '.'.format(raw_optname, opt_type, self.subproject, popt_type))
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
            return FeatureOptionHolder(self.environment, opt)
        elif isinstance(opt, coredata.UserOption):
            return opt.value
        return opt

    @noKwargs
    def func_configuration_data(self, node, args, kwargs):
        if args:
            raise InterpreterException('configuration_data takes no arguments')
        return ConfigurationDataHolder(self.subproject)

    def set_options(self, default_options):
        # Set default options as if they were passed to the command line.
        # Subprojects can only define default for user options.
        for k, v in default_options.items():
            if self.subproject:
                if optinterpreter.is_invalid_name(k):
                    continue
                k = self.subproject + ':' + k
            self.environment.cmd_line_options.setdefault(k, v)

        # Create a subset of cmd_line_options, keeping only options for this
        # subproject. Also take builtin options if it's the main project.
        # Language and backend specific options will be set later when adding
        # languages and setting the backend (builtin options must be set first
        # to know which backend we'll use).
        options = {}
        for k, v in self.environment.cmd_line_options.items():
            if self.subproject:
                if not k.startswith(self.subproject + ':'):
                    continue
            elif k not in coredata.get_builtin_options():
                if ':' in k:
                    continue
                if optinterpreter.is_invalid_name(k):
                    continue
            options[k] = v

        self.coredata.set_options(options, self.subproject)

    def set_backend(self):
        # The backend is already set when parsing subprojects
        if self.backend is not None:
            return
        backend = self.coredata.get_builtin_option('backend')
        if backend == 'ninja':
            from .backend import ninjabackend
            self.backend = ninjabackend.NinjaBackend(self.build)
        elif backend == 'vs':
            from .backend import vs2010backend
            self.backend = vs2010backend.autodetect_vs_version(self.build)
            self.coredata.set_builtin_option('backend', self.backend.name)
            mlog.log('Auto detected Visual Studio backend:', mlog.bold(self.backend.name))
        elif backend == 'vs2010':
            from .backend import vs2010backend
            self.backend = vs2010backend.Vs2010Backend(self.build)
        elif backend == 'vs2015':
            from .backend import vs2015backend
            self.backend = vs2015backend.Vs2015Backend(self.build)
        elif backend == 'vs2017':
            from .backend import vs2017backend
            self.backend = vs2017backend.Vs2017Backend(self.build)
        elif backend == 'xcode':
            from .backend import xcodebackend
            self.backend = xcodebackend.XCodeBackend(self.build)
        else:
            raise InterpreterException('Unknown backend "%s".' % backend)

        # Only init backend options on first invocation otherwise it would
        # override values previously set from command line.
        if self.environment.first_invocation:
            self.coredata.init_backend_options(backend)

        options = {k: v for k, v in self.environment.cmd_line_options.items() if k.startswith('backend_')}
        self.coredata.set_options(options)

    @stringArgs
    @permittedKwargs(permitted_kwargs['project'])
    def func_project(self, node, args, kwargs):
        if len(args) < 1:
            raise InvalidArguments('Not enough arguments to project(). Needs at least the project name.')
        proj_name = args[0]
        proj_langs = args[1:]
        if ':' in proj_name:
            raise InvalidArguments("Project name {!r} must not contain ':'".format(proj_name))

        if os.path.exists(self.option_file):
            oi = optinterpreter.OptionInterpreter(self.subproject)
            oi.process(self.option_file)
            self.coredata.merge_user_options(oi.options)

        # Do not set default_options on reconfigure otherwise it would override
        # values previously set from command line. That means that changing
        # default_options in a project will trigger a reconfigure but won't
        # have any effect.
        self.project_default_options = mesonlib.stringlistify(kwargs.get('default_options', []))
        self.project_default_options = coredata.create_options_dict(self.project_default_options)
        if self.environment.first_invocation:
            default_options = self.project_default_options
            default_options.update(self.default_project_options)
        else:
            default_options = {}
        self.set_options(default_options)
        self.set_backend()

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
        if not self.is_subproject() and 'subproject_dir' in kwargs:
            spdirname = kwargs['subproject_dir']
            if not isinstance(spdirname, str):
                raise InterpreterException('Subproject_dir must be a string')
            if os.path.isabs(spdirname):
                raise InterpreterException('Subproject_dir must not be an absolute path.')
            if spdirname.startswith('.'):
                raise InterpreterException('Subproject_dir must not begin with a period.')
            if '..' in spdirname:
                raise InterpreterException('Subproject_dir must not contain a ".." segment.')
            self.subproject_dir = spdirname

        self.build.subproject_dir = self.subproject_dir

        mesonlib.project_meson_versions[self.subproject] = ''
        if 'meson_version' in kwargs:
            cv = coredata.version
            pv = kwargs['meson_version']
            mesonlib.project_meson_versions[self.subproject] = pv
            if not mesonlib.version_compare(cv, pv):
                raise InterpreterException('Meson version is %s but project requires %s.' % (cv, pv))
        self.build.projects[self.subproject] = proj_name
        mlog.log('Project name:', mlog.bold(proj_name))
        mlog.log('Project version:', mlog.bold(self.project_version))
        self.add_languages(proj_langs, True)
        langs = self.coredata.compilers.keys()
        if 'vala' in langs:
            if 'c' not in langs:
                raise InterpreterException('Compiling Vala requires C. Add C to your project languages and rerun Meson.')
        if not self.is_subproject():
            self.check_cross_stdlibs()

    @permittedKwargs(permitted_kwargs['add_languages'])
    @stringArgs
    def func_add_languages(self, node, args, kwargs):
        disabled, required, feature = extract_required_kwarg(kwargs, self.subproject)
        if disabled:
            for lang in sorted(args, key=compilers.sort_clink):
                mlog.log('Compiler for language', mlog.bold(lang), 'skipped: feature', mlog.bold(feature), 'disabled')
            return False
        return self.add_languages(args, required)

    def get_message_string_arg(self, node):
        # reduce arguments again to avoid flattening posargs
        (posargs, _) = self.reduce_arguments(node.args)
        if len(posargs) != 1:
            raise InvalidArguments('Expected 1 argument, got %d' % len(posargs))

        arg = posargs[0]
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

    @noKwargs
    def func_message(self, node, args, kwargs):
        argstr = self.get_message_string_arg(node)
        mlog.log(mlog.bold('Message:'), argstr)

    @FeatureNew('warning', '0.44.0')
    @noKwargs
    def func_warning(self, node, args, kwargs):
        argstr = self.get_message_string_arg(node)
        mlog.warning(argstr, location=node)

    @noKwargs
    def func_error(self, node, args, kwargs):
        self.validate_arguments(args, 1, [str])
        raise InterpreterException('Problem encountered: ' + args[0])

    @noKwargs
    def func_exception(self, node, args, kwargs):
        self.validate_arguments(args, 0, [])
        raise Exception()

    def detect_compilers(self, lang, need_cross_compiler):
        cross_comp = None
        if lang == 'c':
            comp = self.environment.detect_c_compiler(False)
            if need_cross_compiler:
                cross_comp = self.environment.detect_c_compiler(True)
        elif lang == 'cpp':
            comp = self.environment.detect_cpp_compiler(False)
            if need_cross_compiler:
                cross_comp = self.environment.detect_cpp_compiler(True)
        elif lang == 'objc':
            comp = self.environment.detect_objc_compiler(False)
            if need_cross_compiler:
                cross_comp = self.environment.detect_objc_compiler(True)
        elif lang == 'objcpp':
            comp = self.environment.detect_objcpp_compiler(False)
            if need_cross_compiler:
                cross_comp = self.environment.detect_objcpp_compiler(True)
        elif lang == 'java':
            comp = self.environment.detect_java_compiler()
            if need_cross_compiler:
                cross_comp = comp  # Java is platform independent.
        elif lang == 'cs':
            comp = self.environment.detect_cs_compiler()
            if need_cross_compiler:
                cross_comp = comp  # C# is platform independent.
        elif lang == 'vala':
            comp = self.environment.detect_vala_compiler()
            if need_cross_compiler:
                cross_comp = comp  # Vala compiles to platform-independent C
        elif lang == 'd':
            comp = self.environment.detect_d_compiler(False)
            if need_cross_compiler:
                cross_comp = self.environment.detect_d_compiler(True)
        elif lang == 'rust':
            comp = self.environment.detect_rust_compiler(False)
            if need_cross_compiler:
                cross_comp = self.environment.detect_rust_compiler(True)
        elif lang == 'fortran':
            comp = self.environment.detect_fortran_compiler(False)
            if need_cross_compiler:
                cross_comp = self.environment.detect_fortran_compiler(True)
        elif lang == 'swift':
            comp = self.environment.detect_swift_compiler()
            if need_cross_compiler:
                raise InterpreterException('Cross compilation with Swift is not working yet.')
                # cross_comp = self.environment.detect_fortran_compiler(True)
        else:
            raise InvalidCode('Tried to use unknown language "%s".' % lang)
        comp.sanity_check(self.environment.get_scratch_dir(), self.environment)
        self.coredata.compilers[lang] = comp
        # Native compiler always exist so always add its options.
        new_options = comp.get_options()
        if cross_comp is not None:
            cross_comp.sanity_check(self.environment.get_scratch_dir(), self.environment)
            self.coredata.cross_compilers[lang] = cross_comp
            new_options.update(cross_comp.get_options())

        optprefix = lang + '_'
        for k, o in new_options.items():
            if not k.startswith(optprefix):
                raise InterpreterException('Internal error, %s has incorrect prefix.' % k)
            if k in self.environment.cmd_line_options:
                o.set_value(self.environment.cmd_line_options[k])
            self.coredata.compiler_options.setdefault(k, o)

        # Unlike compiler and linker flags, preprocessor flags are not in
        # compiler_options because they are not visible to user.
        preproc_flags = comp.get_preproc_flags()
        preproc_flags = shlex.split(preproc_flags)
        self.coredata.external_preprocess_args.setdefault(lang, preproc_flags)

        return comp, cross_comp

    def add_languages(self, args, required):
        success = True
        need_cross_compiler = self.environment.is_cross_build() and self.environment.cross_info.need_cross_compiler()
        for lang in sorted(args, key=compilers.sort_clink):
            lang = lang.lower()
            if lang in self.coredata.compilers:
                comp = self.coredata.compilers[lang]
                cross_comp = self.coredata.cross_compilers.get(lang, None)
            else:
                try:
                    (comp, cross_comp) = self.detect_compilers(lang, need_cross_compiler)
                except Exception:
                    if not required:
                        mlog.log('Compiler for language', mlog.bold(lang), 'not found.')
                        success = False
                        continue
                    else:
                        raise
            if comp.full_version is not None:
                version_string = '(%s %s "%s")' % (comp.id, comp.version, comp.full_version)
            else:
                version_string = '(%s %s)' % (comp.id, comp.version)
            mlog.log('Native', comp.get_display_language(), 'compiler:',
                     mlog.bold(' '.join(comp.get_exelist())), version_string)
            self.build.add_compiler(comp)
            if need_cross_compiler:
                version_string = '(%s %s)' % (cross_comp.id, cross_comp.version)
                mlog.log('Cross', cross_comp.get_display_language(), 'compiler:',
                         mlog.bold(' '.join(cross_comp.get_exelist())), version_string)
                self.build.add_cross_compiler(cross_comp)
            if self.environment.is_cross_build() and not need_cross_compiler:
                self.build.add_cross_compiler(comp)
            self.add_base_options(comp)
        return success

    def emit_base_options_warnings(self, enabled_opts):
        if 'b_bitcode' in enabled_opts:
            mlog.warning('Base option \'b_bitcode\' is enabled, which is incompatible with many linker options. Incompatible options such as such as \'b_asneeded\' have been disabled.')
            mlog.warning('Please see https://mesonbuild.com/Builtin-options.html#Notes_about_Apple_Bitcode_support for more details.')

    def add_base_options(self, compiler):
        enabled_opts = []
        for optname in compiler.base_options:
            if optname in self.coredata.base_options:
                continue
            oobj = compilers.base_options[optname]
            if optname in self.environment.cmd_line_options:
                oobj.set_value(self.environment.cmd_line_options[optname])
                enabled_opts.append(optname)
            self.coredata. base_options[optname] = oobj
        self.emit_base_options_warnings(enabled_opts)

    def program_from_cross_file(self, prognames, silent=False):
        cross_info = self.environment.cross_info
        for p in prognames:
            if hasattr(p, 'held_object'):
                p = p.held_object
            if isinstance(p, mesonlib.File):
                continue # Always points to a local (i.e. self generated) file.
            if not isinstance(p, str):
                raise InterpreterException('Executable name must be a string')
            prog = ExternalProgram.from_cross_info(cross_info, p)
            if prog.found():
                return ExternalProgramHolder(prog)
        return None

    def program_from_system(self, args, silent=False):
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
            elif isinstance(exename, str):
                search_dir = source_dir
            else:
                raise InvalidArguments('find_program only accepts strings and '
                                       'files, not {!r}'.format(exename))
            extprog = dependencies.ExternalProgram(exename, search_dir=search_dir,
                                                   silent=silent)
            progobj = ExternalProgramHolder(extprog)
            if progobj.found():
                return progobj

    def program_from_overrides(self, command_names, silent=False):
        for name in command_names:
            if not isinstance(name, str):
                continue
            if name in self.build.find_overrides:
                exe = self.build.find_overrides[name]
                if not silent:
                    mlog.log('Program', mlog.bold(name), 'found:', mlog.green('YES'),
                             '(overridden: %s)' % exe.description())
                return ExternalProgramHolder(exe)
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

    def find_program_impl(self, args, native=False, required=True, silent=True):
        if not isinstance(args, list):
            args = [args]
        progobj = self.program_from_overrides(args, silent=silent)
        if progobj is None and self.build.environment.is_cross_build():
            if not native:
                progobj = self.program_from_cross_file(args, silent=silent)
        if progobj is None:
            progobj = self.program_from_system(args, silent=silent)
        if required and (progobj is None or not progobj.found()):
            raise InvalidArguments('Program(s) {!r} not found or not executable'.format(args))
        if progobj is None:
            return ExternalProgramHolder(dependencies.NonExistingExternalProgram())
        # Only store successful lookups
        self.store_name_lookups(args)
        return progobj

    @permittedKwargs(permitted_kwargs['find_program'])
    def func_find_program(self, node, args, kwargs):
        if not args:
            raise InterpreterException('No program name specified.')

        disabled, required, feature = extract_required_kwarg(kwargs, self.subproject)
        if disabled:
            mlog.log('Program', mlog.bold(' '.join(args)), 'skipped: feature', mlog.bold(feature), 'disabled')
            return ExternalProgramHolder(dependencies.NonExistingExternalProgram())

        if not isinstance(required, bool):
            raise InvalidArguments('"required" argument must be a boolean.')
        use_native = kwargs.get('native', False)
        if not isinstance(use_native, bool):
            raise InvalidArguments('Argument to "native" must be a boolean.')
        return self.find_program_impl(args, native=use_native, required=required, silent=False)

    def func_find_library(self, node, args, kwargs):
        raise InvalidCode('find_library() is removed, use meson.get_compiler(\'name\').find_library() instead.\n'
                          'Look here for documentation: http://mesonbuild.com/Reference-manual.html#compiler-object\n'
                          'Look here for example: http://mesonbuild.com/howtox.html#add-math-library-lm-portably\n'
                          )

    def _find_cached_dep(self, name, kwargs):
        # Check if we want this as a cross-dep or a native-dep
        # FIXME: Not all dependencies support such a distinction right now,
        # and we repeat this check inside dependencies that do. We need to
        # consolidate this somehow.
        is_cross = self.environment.is_cross_build()
        if 'native' in kwargs and is_cross:
            want_cross = not kwargs['native']
        else:
            want_cross = is_cross
        identifier = dependencies.get_dep_identifier(name, kwargs, want_cross)
        cached_dep = None
        # Check if we've already searched for and found this dep
        if identifier in self.coredata.deps:
            cached_dep = self.coredata.deps[identifier]
            mlog.log('Dependency', mlog.bold(name),
                     'found:', mlog.green('YES'), '(cached)')
        else:
            # Check if exactly the same dep with different version requirements
            # was found already.
            wanted = identifier[1]
            for trial, trial_dep in self.coredata.deps.items():
                # trial[1], identifier[1] are the version requirements
                if trial[0] != identifier[0] or trial[2:] != identifier[2:]:
                    continue
                found = trial_dep.get_version()
                if not wanted or mesonlib.version_compare_many(found, wanted)[0]:
                    # We either don't care about the version, or our
                    # version requirements matched the trial dep's version.
                    cached_dep = trial_dep
                    break
        return identifier, cached_dep

    @staticmethod
    def check_subproject_version(wanted, found):
        if wanted == 'undefined':
            return True
        if found == 'undefined' or not mesonlib.version_compare_many(found, wanted)[0]:
            return False
        return True

    def get_subproject_dep(self, name, dirname, varname, required):
        try:
            subproject = self.subprojects[dirname]
            if not subproject.found():
                if not required:
                    return DependencyHolder(NotFoundDependency(self.environment), self.subproject)

                raise DependencyException('Subproject %s was not found.' % (name))

            dep = self.subprojects[dirname].get_variable_method([varname], {})
        except InvalidArguments as e:
            if required:
                raise DependencyException('Could not find dependency {} in subproject {}; {}'
                                          ''.format(varname, dirname, str(e)))
            # If the dependency is not required, don't raise an exception
            subproj_path = os.path.join(self.subproject_dir, dirname)
            mlog.log('Dependency', mlog.bold(name), 'from subproject',
                     mlog.bold(subproj_path), 'found:', mlog.red('NO'))
            return None
        if not isinstance(dep, DependencyHolder):
            raise InvalidCode('Fetched variable {!r} in the subproject {!r} is '
                              'not a dependency object.'.format(varname, dirname))
        return dep

    def _find_cached_fallback_dep(self, name, dirname, varname, wanted, required):
        if dirname not in self.subprojects:
            return False
        dep = self.get_subproject_dep(name, dirname, varname, required)
        if not dep:
            return False
        if not dep.found():
            return dep

        found = dep.version_method([], {})
        # Don't do a version check if the dependency is not found and not required
        if not dep.found_method([], {}) and not required:
            subproj_path = os.path.join(self.subproject_dir, dirname)
            mlog.log('Dependency', mlog.bold(name), 'from subproject',
                     mlog.bold(subproj_path), 'found:', mlog.red('NO'), '(cached)')
            return dep
        if self.check_subproject_version(wanted, found):
            subproj_path = os.path.join(self.subproject_dir, dirname)
            mlog.log('Dependency', mlog.bold(name), 'from subproject',
                     mlog.bold(subproj_path), 'found:', mlog.green('YES'), '(cached)')
            return dep
        if required:
            raise DependencyException('Version {} of subproject dependency {} already '
                                      'cached, requested incompatible version {} for '
                                      'dep {}'.format(found, dirname, wanted, name))
        return None

    def _handle_featurenew_dependencies(self, name):
        'Do a feature check on dependencies used by this subproject'
        if name == 'mpi':
            FeatureNew('MPI Dependency', '0.42.0').use(self.subproject)
        elif name == 'pcap':
            FeatureNew('Pcap Dependency', '0.42.0').use(self.subproject)
        elif name == 'vulkan':
            FeatureNew('Vulkan Dependency', '0.42.0').use(self.subproject)
        elif name == 'libwmf':
            FeatureNew('LibWMF Dependency', '0.44.0').use(self.subproject)
        elif name == 'openmp':
            FeatureNew('OpenMP Dependency', '0.46.0').use(self.subproject)

    @FeatureNewKwargs('dependency', '0.40.0', ['method'])
    @FeatureNewKwargs('dependency', '0.38.0', ['default_options'])
    @permittedKwargs(permitted_kwargs['dependency'])
    def func_dependency(self, node, args, kwargs):
        self.validate_arguments(args, 1, [str])
        name = args[0]
        display_name = name if name else '(anonymous)'

        disabled, required, feature = extract_required_kwarg(kwargs, self.subproject)
        if disabled:
            mlog.log('Dependency', mlog.bold(display_name), 'skipped: feature', mlog.bold(feature), 'disabled')
            return DependencyHolder(NotFoundDependency(self.environment), self.subproject)

        # writing just "dependency('')" is an error, because it can only fail
        if name == '' and required and 'fallback' not in kwargs:
            raise InvalidArguments('Dependency is both required and not-found')

        if '<' in name or '>' in name or '=' in name:
            raise InvalidArguments('Characters <, > and = are forbidden in dependency names. To specify'
                                   'version\n requirements use the \'version\' keyword argument instead.')
        identifier, cached_dep = self._find_cached_dep(name, kwargs)

        if cached_dep:
            if required and not cached_dep.found():
                m = 'Dependency {!r} was already checked and was not found'
                raise DependencyException(m.format(display_name))
            dep = cached_dep
        else:
            # If the dependency has already been configured, possibly by
            # a higher level project, try to use it first.
            if 'fallback' in kwargs:
                dirname, varname = self.get_subproject_infos(kwargs)
                wanted = kwargs.get('version', 'undefined')
                dep = self._find_cached_fallback_dep(name, dirname, varname, wanted, required)
                if dep:
                    return dep

            # We need to actually search for this dep
            exception = None
            dep = NotFoundDependency(self.environment)

            # Unless a fallback exists and is forced ...
            if self.coredata.wrap_mode == WrapMode.forcefallback and 'fallback' in kwargs:
                pass
            # ... search for it outside the project
            elif name != '':
                self._handle_featurenew_dependencies(name)
                try:
                    dep = dependencies.find_external_dependency(name, self.environment, kwargs)
                except DependencyException as e:
                    exception = e

            # Search inside the projects list
            if not dep.found():
                if 'fallback' in kwargs:
                    if not exception:
                        exception = DependencyException("fallback for %s not found" % display_name)
                    fallback_dep = self.dependency_fallback(name, kwargs)
                    if fallback_dep:
                        # Never add fallback deps to self.coredata.deps since we
                        # cannot cache them. They must always be evaluated else
                        # we won't actually read all the build files.
                        return fallback_dep
                if required:
                    assert(exception is not None)
                    raise exception

        # Only store found-deps in the cache
        if dep.found():
            self.coredata.deps[identifier] = dep
        return DependencyHolder(dep, self.subproject)

    @FeatureNew('disabler', '0.44.0')
    @noKwargs
    @noPosargs
    def func_disabler(self, node, args, kwargs):
        return Disabler()

    def print_nested_info(self, dependency_name):
        message_templ = '''\nDependency %s not found but it is available in a sub-subproject.
To use it in the current project, promote it by going in the project source
root and issuing %s.

'''
        sprojs = mesonlib.detect_subprojects('subprojects', self.source_root)
        if dependency_name not in sprojs:
            return
        found = sprojs[dependency_name]
        if len(found) > 1:
            suffix = 'one of the following commands'
        else:
            suffix = 'the following command'
        message = message_templ % (dependency_name, suffix)
        cmds = []
        command_templ = 'meson wrap promote '
        for l in found:
            cmds.append(command_templ + l[len(self.source_root) + 1:])
        final_message = message + '\n'.join(cmds)
        print(final_message)

    def get_subproject_infos(self, kwargs):
        fbinfo = kwargs['fallback']
        check_stringlist(fbinfo)
        if len(fbinfo) != 2:
            raise InterpreterException('Fallback info must have exactly two items.')
        return fbinfo

    def dependency_fallback(self, name, kwargs):
        display_name = name if name else '(anonymous)'
        if self.coredata.wrap_mode in (WrapMode.nofallback, WrapMode.nodownload):
            mlog.log('Not looking for a fallback subproject for the dependency',
                     mlog.bold(display_name), 'because:\nUse of fallback'
                     'dependencies is disabled.')
            return None
        elif self.coredata.wrap_mode == WrapMode.forcefallback:
            mlog.log('Looking for a fallback subproject for the dependency',
                     mlog.bold(display_name), 'because:\nUse of fallback dependencies is forced.')
        else:
            mlog.log('Looking for a fallback subproject for the dependency',
                     mlog.bold(display_name))
        dirname, varname = self.get_subproject_infos(kwargs)
        # Try to execute the subproject
        try:
            sp_kwargs = {}
            try:
                sp_kwargs['default_options'] = kwargs['default_options']
            except KeyError:
                pass
            self.do_subproject(dirname, sp_kwargs)
        # Invalid code is always an error
        except InvalidCode:
            raise
        # If the subproject execution failed in a non-fatal way, don't raise an
        # exception; let the caller handle things.
        except Exception as e:
            msg = ['Couldn\'t use fallback subproject in',
                   mlog.bold(os.path.join(self.subproject_dir, dirname)),
                   'for the dependency', mlog.bold(display_name), '\nReason:']
            if isinstance(e, mesonlib.MesonException):
                msg.append(e.get_msg_with_context())
            else:
                msg.append(traceback.format_exc())
            mlog.log(*msg)
            return None
        required = kwargs.get('required', True)
        dep = self.get_subproject_dep(name, dirname, varname, required)
        if not dep:
            return None
        subproj_path = os.path.join(self.subproject_dir, dirname)
        # Check if the version of the declared dependency matches what we want
        if 'version' in kwargs:
            wanted = kwargs['version']
            found = dep.version_method([], {})
            # Don't do a version check if the dependency is not found and not required
            if not dep.found_method([], {}) and not required:
                subproj_path = os.path.join(self.subproject_dir, dirname)
                mlog.log('Dependency', mlog.bold(display_name), 'from subproject',
                         mlog.bold(subproj_path), 'found:', mlog.red('NO'))
                return dep
            if not self.check_subproject_version(wanted, found):
                mlog.log('Subproject', mlog.bold(subproj_path), 'dependency',
                         mlog.bold(display_name), 'version is', mlog.bold(found),
                         'but', mlog.bold(wanted), 'is required.')
                return None
        mlog.log('Dependency', mlog.bold(display_name), 'from subproject',
                 mlog.bold(subproj_path), 'found:', mlog.green('YES'))
        return dep

    @FeatureNewKwargs('executable', '0.42.0', ['implib'])
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
    def func_vcs_tag(self, node, args, kwargs):
        if 'input' not in kwargs or 'output' not in kwargs:
            raise InterpreterException('Keyword arguments input and output must exist')
        if 'fallback' not in kwargs:
            FeatureNew('Optional fallback in vcs_tag', '0.41.0').use(self.subproject)
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
            FeatureNew('substitutions in custom_target depfile', '0.47.0').use(self.subproject)
        return self._func_custom_target_impl(node, args, kwargs)

    def _func_custom_target_impl(self, node, args, kwargs):
        'Implementation-only, without FeatureNew checks, for internal use'
        name = args[0]
        kwargs['install_mode'] = self._get_kwarg_install_mode(kwargs)
        tg = CustomTargetHolder(build.CustomTarget(name, self.subdir, self.subproject, kwargs), self)
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
            deps = extract_as_list(kwargs, 'depends', unholder=True)
        else:
            raise InterpreterException('Run_target needs at least one positional argument.')

        cleaned_args = []
        for i in listify(all_args, unholder=True):
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
        command = cleaned_args[0]
        cmd_args = cleaned_args[1:]
        tg = RunTargetHolder(name, command, cmd_args, cleaned_deps, self.subdir, self.subproject)
        self.add_target(name, tg.held_object)
        return tg

    @permittedKwargs(permitted_kwargs['generator'])
    def func_generator(self, node, args, kwargs):
        gen = GeneratorHolder(self, args, kwargs)
        self.generators.append(gen)
        return gen

    @permittedKwargs(permitted_kwargs['benchmark'])
    def func_benchmark(self, node, args, kwargs):
        self.add_test(node, args, kwargs, False)

    @FeatureNewKwargs('test', '0.46.0', ['depends'])
    @permittedKwargs(permitted_kwargs['test'])
    def func_test(self, node, args, kwargs):
        self.add_test(node, args, kwargs, True)

    def unpack_env_kwarg(self, kwargs):
        envlist = kwargs.get('env', EnvironmentVariablesHolder())
        if isinstance(envlist, EnvironmentVariablesHolder):
            env = envlist.held_object
        else:
            envlist = listify(envlist)
            # Convert from array to environment object
            env = EnvironmentVariablesHolder()
            for e in envlist:
                if '=' not in e:
                    raise InterpreterException('Env var definition must be of type key=val.')
                (k, val) = e.split('=', 1)
                k = k.strip()
                val = val.strip()
                if ' ' in k:
                    raise InterpreterException('Env var key must not have spaces in it.')
                env.set_method([k, val], {})
            env = env.held_object
        return env

    def add_test(self, node, args, kwargs, is_base_test):
        if len(args) != 2:
            raise InterpreterException('Incorrect number of arguments')
        if not isinstance(args[0], str):
            raise InterpreterException('First argument of test must be a string.')
        exe = args[1]
        if not isinstance(exe, (ExecutableHolder, JarHolder, ExternalProgramHolder)):
            if isinstance(exe, mesonlib.File):
                exe = self.func_find_program(node, args[1], {})
            else:
                raise InterpreterException('Second argument must be executable.')
        par = kwargs.get('is_parallel', True)
        if not isinstance(par, bool):
            raise InterpreterException('Keyword argument is_parallel must be a boolean.')
        cmd_args = extract_as_list(kwargs, 'args', unholder=True)
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
        suite = []
        prj = self.subproject if self.is_subproject() else self.build.project_name
        for s in mesonlib.stringlistify(kwargs.get('suite', '')):
            if len(s) > 0:
                s = ':' + s
            suite.append(prj.replace(' ', '_').replace(':', '_') + s)
        depends = extract_as_list(kwargs, 'depends', unholder=True)
        for dep in depends:
            if not isinstance(dep, (build.CustomTarget, build.BuildTarget)):
                raise InterpreterException('Depends items must be build targets.')
        t = Test(args[0], prj, suite, exe.held_object, depends, par, cmd_args,
                 env, should_fail, timeout, workdir)
        if is_base_test:
            self.build.tests.append(t)
            mlog.debug('Adding test', mlog.bold(args[0], True))
        else:
            self.build.benchmarks.append(t)
            mlog.debug('Adding benchmark', mlog.bold(args[0], True))

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
            raise InterpreterException('Non-existent build file {!r}'.format(buildfilename))
        with open(absname, encoding='utf8') as f:
            code = f.read()
        assert(isinstance(code, str))
        try:
            codeblock = mparser.Parser(code, self.subdir).parse()
        except mesonlib.MesonException as me:
            me.file = buildfilename
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
            else:
                source_strings.append(s)
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

        # Validate input
        inputfile = None
        ifile_abs = None
        if 'input' in kwargs:
            inputfile = kwargs['input']
            if isinstance(inputfile, list):
                if len(inputfile) != 1:
                    m = "Keyword argument 'input' requires exactly one file"
                    raise InterpreterException(m)
                inputfile = inputfile[0]
            if not isinstance(inputfile, (str, mesonlib.File)):
                raise InterpreterException('Input must be a string or a file')
            if isinstance(inputfile, str):
                inputfile = mesonlib.File.from_source_file(self.environment.source_dir,
                                                           self.subdir, inputfile)
            ifile_abs = inputfile.absolute_path(self.environment.source_dir,
                                                self.environment.build_dir)
        elif 'command' in kwargs and '@INPUT@' in kwargs['command']:
            raise InterpreterException('@INPUT@ used as command argument, but no input file specified.')
        # Validate output
        output = kwargs['output']
        ofile_rpath = os.path.join(self.subdir, output)
        if not isinstance(output, str):
            raise InterpreterException('Output file name must be a string')
        if ofile_rpath in self.configure_file_outputs:
            mesonbuildfile = os.path.join(self.subdir, 'meson.build')
            current_call = "{}:{}".format(mesonbuildfile, self.current_lineno)
            first_call = "{}:{}".format(mesonbuildfile, self.configure_file_outputs[ofile_rpath])
            mlog.warning('Output file', mlog.bold(ofile_rpath, True), 'for configure_file() at', current_call, 'overwrites configure_file() output at', first_call)
        else:
            self.configure_file_outputs[ofile_rpath] = self.current_lineno
        if ifile_abs:
            values = mesonlib.get_filenames_templates_dict([ifile_abs], None)
            outputs = mesonlib.substitute_values([output], values)
            output = outputs[0]
        if os.path.dirname(output) != '':
            raise InterpreterException('Output file name must not contain a subdirectory.')
        (ofile_path, ofile_fname) = os.path.split(os.path.join(self.subdir, output))
        ofile_abs = os.path.join(self.environment.build_dir, ofile_path, ofile_fname)
        # Perform the appropriate action
        if 'configuration' in kwargs:
            conf = kwargs['configuration']
            if not isinstance(conf, ConfigurationDataHolder):
                raise InterpreterException('Argument "configuration" is not of type configuration_data')
            mlog.log('Configuring', mlog.bold(output), 'using configuration')
            if inputfile is not None:
                os.makedirs(os.path.join(self.environment.build_dir, self.subdir), exist_ok=True)
                file_encoding = kwargs.setdefault('encoding', 'utf-8')
                missing_variables, confdata_useless = \
                    mesonlib.do_conf_file(ifile_abs, ofile_abs, conf.held_object,
                                          fmt, file_encoding)
                if missing_variables:
                    var_list = ", ".join(map(repr, sorted(missing_variables)))
                    mlog.warning(
                        "The variable(s) %s in the input file '%s' are not "
                        "present in the given configuration data." % (
                            var_list, inputfile), location=node)
                if confdata_useless:
                    ifbase = os.path.basename(ifile_abs)
                    mlog.warning('Got an empty configuration_data() object and found no '
                                 'substitutions in the input file {!r}. If you want to '
                                 'copy a file to the build dir, use the \'copy:\' keyword '
                                 'argument added in 0.47.0'.format(ifbase), location=node)
            else:
                mesonlib.dump_conf_header(ofile_abs, conf.held_object, output_format)
            conf.mark_used()
        elif 'command' in kwargs:
            # We use absolute paths for input and output here because the cwd
            # that the command is run from is 'unspecified', so it could change.
            # Currently it's builddir/subdir for in_builddir else srcdir/subdir.
            if ifile_abs:
                values = mesonlib.get_filenames_templates_dict([ifile_abs], [ofile_abs])
            else:
                values = mesonlib.get_filenames_templates_dict(None, [ofile_abs])
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
                if ifile_abs:
                    shutil.copymode(ifile_abs, dst_tmp)
                mesonlib.replace_if_different(ofile_abs, dst_tmp)
        elif 'copy' in kwargs:
            os.makedirs(os.path.join(self.environment.build_dir, self.subdir), exist_ok=True)
            shutil.copyfile(ifile_abs, ofile_abs)
            shutil.copymode(ifile_abs, ofile_abs)
        else:
            # Not reachable
            raise AssertionError
        # If the input is a source file, add it to the list of files that we
        # need to reconfigure on when they change. FIXME: Do the same for
        # files() objects in the command: kwarg.
        if inputfile and not inputfile.is_built:
            # Normalize the path of the conffile (relative to the
            # source root) to avoid duplicates. This is especially
            # important to convert '/' to '\' on Windows
            conffile = os.path.normpath(inputfile.relative_name())
            if conffile not in self.build_def_files:
                self.build_def_files.append(conffile)
        # Install file if requested, we check for the empty string
        # for backwards compatibility. That was the behaviour before
        # 0.45.0 so preserve it.
        idir = kwargs.get('install_dir', None)
        if isinstance(idir, str) and idir:
            cfile = mesonlib.File.from_built_file(ofile_path, ofile_fname)
            install_mode = self._get_kwarg_install_mode(kwargs)
            self.build.data.append(build.Data([cfile], idir, install_mode))
        return mesonlib.File.from_built_file(self.subdir, output)

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
                raise InvalidArguments('''Tried to form an absolute path to a source dir. You should not do that but use
relative paths instead.

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
            inp = extract_as_list(kwargs, 'exe_wrapper', unholder=True)
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
        env = self.unpack_env_kwarg(kwargs)
        self.build.test_setups[setup_name] = build.TestSetup(exe_wrapper=exe_wrapper,
                                                             gdb=gdb,
                                                             timeout_multiplier=timeout_multiplier,
                                                             env=env)

    def get_argdict_on_crossness(self, native_dict, cross_dict, kwargs):
        for_native = kwargs.get('native', not self.environment.is_cross_build())
        if not isinstance(for_native, bool):
            raise InterpreterException('Keyword native must be a boolean.')
        if for_native:
            return native_dict
        else:
            return cross_dict

    @permittedKwargs(permitted_kwargs['add_global_arguments'])
    @stringArgs
    def func_add_global_arguments(self, node, args, kwargs):
        argdict = self.get_argdict_on_crossness(self.build.global_args,
                                                self.build.cross_global_args,
                                                kwargs)
        self.add_global_arguments(node, argdict, args, kwargs)

    @permittedKwargs(permitted_kwargs['add_global_link_arguments'])
    @stringArgs
    def func_add_global_link_arguments(self, node, args, kwargs):
        argdict = self.get_argdict_on_crossness(self.build.global_link_args,
                                                self.build.cross_global_link_args,
                                                kwargs)
        self.add_global_arguments(node, argdict, args, kwargs)

    @permittedKwargs(permitted_kwargs['add_project_arguments'])
    @stringArgs
    def func_add_project_arguments(self, node, args, kwargs):
        argdict = self.get_argdict_on_crossness(self.build.projects_args,
                                                self.build.cross_projects_args,
                                                kwargs)
        self.add_project_arguments(node, argdict, args, kwargs)

    @permittedKwargs(permitted_kwargs['add_project_link_arguments'])
    @stringArgs
    def func_add_project_link_arguments(self, node, args, kwargs):
        argdict = self.get_argdict_on_crossness(self.build.projects_link_args,
                                                self.build.cross_projects_link_args, kwargs)
        self.add_project_arguments(node, argdict, args, kwargs)

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

        for lang in mesonlib.stringlistify(kwargs['language']):
            lang = lang.lower()
            argsdict[lang] = argsdict.get(lang, []) + args

    @noKwargs
    @noPosargs
    def func_environment(self, node, args, kwargs):
        return EnvironmentVariablesHolder()

    @stringArgs
    @noKwargs
    def func_join_paths(self, node, args, kwargs):
        return os.path.join(*args).replace('\\', '/')

    def run(self):
        super().run()
        mlog.log('Build targets in project:', mlog.bold(str(len(self.build.targets))))
        FeatureNew.report(self.subproject)
        FeatureDeprecated.report(self.subproject)
        if not self.is_subproject():
            self.print_extra_warnings()

    def print_extra_warnings(self):
        for c in self.build.compilers.values():
            if c.get_id() == 'clang':
                self.check_clang_asan_lundef()
                break

    def check_clang_asan_lundef(self):
        if 'b_lundef' not in self.coredata.base_options:
            return
        if 'b_sanitize' not in self.coredata.base_options:
            return
        if self.coredata.base_options['b_lundef'].value:
            mlog.warning('''Trying to use {} sanitizer on Clang with b_lundef.
This will probably not work.
Try setting b_lundef to false instead.'''.format(self.coredata.base_options['b_sanitize'].value))

    def evaluate_subproject_info(self, path_from_source_root, subproject_dirname):
        depth = 0
        subproj_name = ''
        segs = PurePath(path_from_source_root).parts
        segs_spd = PurePath(subproject_dirname).parts
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
                              CustomTargetHolder, CustomTargetIndexHolder)):
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
        if name in coredata.forbidden_target_names:
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
        default_library = self.coredata.get_builtin_option('default_library')
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
        name = args[0]
        sources = listify(args[1:])
        if self.environment.is_cross_build():
            if kwargs.get('native', False):
                is_cross = False
            else:
                is_cross = True
        else:
            is_cross = False
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
        if targetholder is ExecutableHolder:
            targetclass = build.Executable
        elif targetholder is SharedLibraryHolder:
            targetclass = build.SharedLibrary
        elif targetholder is SharedModuleHolder:
            targetclass = build.SharedModule
        elif targetholder is StaticLibraryHolder:
            targetclass = build.StaticLibrary
        elif targetholder is JarHolder:
            targetclass = build.Jar
        else:
            mlog.debug('Unknown target type:', str(targetholder))
            raise RuntimeError('Unreachable code')
        self.kwarg_strings_to_includedirs(kwargs)

        # Filter out kwargs from other target types. For example 'soversion'
        # passed to library() when default_library == 'static'.
        kwargs = {k: v for k, v in kwargs.items() if k in targetclass.known_kwargs}

        target = targetclass(name, self.subdir, self.subproject, is_cross, sources, objs, self.environment, kwargs)

        if is_cross:
            self.add_cross_stdlib_info(target)
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
This will become a hard error in the future.''')
                        i = os.path.relpath(i, os.path.join(self.environment.get_source_dir(), self.subdir))
                        i = self.build_incdir_object([i])
                cleaned_items.append(i)
            kwargs['d_import_dirs'] = cleaned_items

    def get_used_languages(self, target):
        result = {}
        for i in target.sources:
            for lang, c in self.build.compilers.items():
                if c.can_compile(i):
                    result[lang] = True
                    break
        return result

    def add_cross_stdlib_info(self, target):
        for l in self.get_used_languages(target):
            if self.environment.cross_info.has_stdlib(l) \
                    and self.subproject != self.environment.cross_info.get_stdlib(l)[0]:
                target.add_deps(self.build.cross_stdlibs[l])

    def check_sources_exist(self, subdir, sources):
        for s in sources:
            if not isinstance(s, str):
                continue # This means a generated source and they always exist.
            fname = os.path.join(subdir, s)
            if not os.path.isfile(fname):
                raise InterpreterException('Tried to add non-existing source file %s.' % s)

    def format_string(self, templ, args):
        if isinstance(args, mparser.ArgumentNode):
            args = args.arguments
        arg_strings = []
        for arg in args:
            arg = self.evaluate_statement(arg)
            if isinstance(arg, bool): # Python boolean is upper case.
                arg = str(arg).lower()
            arg_strings.append(str(arg))

        def arg_replace(match):
            idx = int(match.group(1))
            if idx >= len(arg_strings):
                raise InterpreterException('Format placeholder @{}@ out of range.'.format(idx))
            return arg_strings[idx]

        return re.sub(r'@(\d+)@', arg_replace, templ)

    # Only permit object extraction from the same subproject
    def validate_extraction(self, buildtarget):
        if not self.subdir.startswith(self.subproject_dir):
            if buildtarget.subdir.startswith(self.subproject_dir):
                raise InterpreterException('Tried to extract objects from a subproject target.')
        else:
            if not buildtarget.subdir.startswith(self.subproject_dir):
                raise InterpreterException('Tried to extract objects from the main project from a subproject.')
            if self.subdir.split('/')[1] != buildtarget.subdir.split('/')[1]:
                raise InterpreterException('Tried to extract objects from a different subproject.')

    def check_contains(self, obj, args):
        if len(args) != 1:
            raise InterpreterException('Contains method takes exactly one argument.')
        item = args[0]
        for element in obj:
            if isinstance(element, list):
                found = self.check_contains(element, args)
                if found:
                    return True
            if element == item:
                return True
        return False

    def is_subproject(self):
        return self.subproject != ''

    @noKwargs
    @noArgsFlattening
    def func_set_variable(self, node, args, kwargs):
        if len(args) != 2:
            raise InvalidCode('Set_variable takes two arguments.')
        varname = args[0]
        value = args[1]
        self.set_variable(varname, value)

    @noKwargs
    @noArgsFlattening
    def func_get_variable(self, node, args, kwargs):
        if len(args) < 1 or len(args) > 2:
            raise InvalidCode('Get_variable takes one or two arguments.')
        varname = args[0]
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
