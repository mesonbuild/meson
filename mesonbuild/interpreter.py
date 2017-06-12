# Copyright 2012-2017 The Meson development team

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
from .mesonlib import FileMode, Popen_safe, get_meson_script
from .dependencies import ExternalProgram
from .dependencies import InternalDependency, Dependency, DependencyException
from .interpreterbase import InterpreterBase
from .interpreterbase import check_stringlist, noPosargs, noKwargs, stringArgs
from .interpreterbase import InterpreterException, InvalidArguments, InvalidCode
from .interpreterbase import InterpreterObject, MutableInterpreterObject
from .modules import ModuleReturnValue

import os, sys, shutil, uuid
import re
from collections import namedtuple

import importlib

run_depr_printed = False

def stringifyUserArguments(args):
    if isinstance(args, list):
        return '[%s]' % ', '.join([stringifyUserArguments(x) for x in args])
    elif isinstance(args, int):
        return str(args)
    elif isinstance(args, str):
        return "'%s'" % args
    raise InvalidArguments('Function accepts only strings, integers, lists and lists thereof.')


class TryRunResultHolder(InterpreterObject):
    def __init__(self, res):
        super().__init__()
        self.res = res
        self.methods.update({'returncode': self.returncode_method,
                             'compiled': self.compiled_method,
                             'stdout': self.stdout_method,
                             'stderr': self.stderr_method,
                             })

    def returncode_method(self, args, kwargs):
        return self.res.returncode

    def compiled_method(self, args, kwargs):
        return self.res.compiled

    def stdout_method(self, args, kwargs):
        return self.res.stdout

    def stderr_method(self, args, kwargs):
        return self.res.stderr

class RunProcess(InterpreterObject):

    def __init__(self, cmd, args, source_dir, build_dir, subdir, mesonintrospect, in_builddir=False):
        super().__init__()
        if not isinstance(cmd, ExternalProgram):
            raise AssertionError('BUG: RunProcess must be passed an ExternalProgram')
        pc, self.stdout, self.stderr = self.run_command(cmd, args, source_dir, build_dir, subdir, mesonintrospect, in_builddir)
        self.returncode = pc.returncode
        self.methods.update({'returncode': self.returncode_method,
                             'stdout': self.stdout_method,
                             'stderr': self.stderr_method,
                             })

    def run_command(self, cmd, args, source_dir, build_dir, subdir, mesonintrospect, in_builddir):
        command_array = cmd.get_command() + args
        env = {'MESON_SOURCE_ROOT': source_dir,
               'MESON_BUILD_ROOT': build_dir,
               'MESON_SUBDIR': subdir,
               'MESONINTROSPECT': mesonintrospect}
        if in_builddir:
            cwd = os.path.join(build_dir, subdir)
        else:
            cwd = os.path.join(source_dir, subdir)
        child_env = os.environ.copy()
        child_env.update(env)
        mlog.debug('Running command:', ' '.join(command_array))
        try:
            return Popen_safe(command_array, env=child_env, cwd=cwd)
        except FileNotFoundError:
            raise InterpreterException('Could not execute command "%s".' % ' '.join(command_array))

    def returncode_method(self, args, kwargs):
        return self.returncode

    def stdout_method(self, args, kwargs):
        return self.stdout

    def stderr_method(self, args, kwargs):
        return self.stderr

class ConfigureFileHolder(InterpreterObject):

    def __init__(self, subdir, sourcename, targetname, configuration_data):
        InterpreterObject.__init__(self)
        self.held_object = build.ConfigureFile(subdir, sourcename, targetname, configuration_data)


class EnvironmentVariablesHolder(MutableInterpreterObject):
    def __init__(self):
        super().__init__()
        self.held_object = build.EnvironmentVariables()
        self.methods.update({'set': self.set_method,
                             'append': self.append_method,
                             'prepend': self.prepend_method,
                             })

    def __repr__(self):
        repr_str = "<{0}: {1}>"
        return repr_str.format(self.__class__.__name__, self.held_object.envvars)

    @stringArgs
    def add_var(self, method, args, kwargs):
        if not isinstance(kwargs.get("separator", ""), str):
            raise InterpreterException("EnvironmentVariablesHolder methods 'separator'"
                                       " argument needs to be a string.")
        if len(args) < 2:
            raise InterpreterException("EnvironmentVariablesHolder methods require at least"
                                       "2 arguments, first is the name of the variable and"
                                       " following one are values")
        self.held_object.envvars.append((method, args[0], args[1:], kwargs))

    def set_method(self, args, kwargs):
        self.add_var(self.held_object.set, args, kwargs)

    def append_method(self, args, kwargs):
        self.add_var(self.held_object.append, args, kwargs)

    def prepend_method(self, args, kwargs):
        self.add_var(self.held_object.prepend, args, kwargs)


class ConfigurationDataHolder(MutableInterpreterObject):
    def __init__(self):
        super().__init__()
        self.used = False # These objects become immutable after use in configure_file.
        self.held_object = build.ConfigurationData()
        self.methods.update({'set': self.set_method,
                             'set10': self.set10_method,
                             'set_quoted': self.set_quoted_method,
                             'has': self.has_method,
                             'get': self.get_method,
                             })

    def is_used(self):
        return self.used

    def mark_used(self):
        self.used = True

    def validate_args(self, args, kwargs):
        if len(args) != 2:
            raise InterpreterException("Configuration set requires 2 arguments.")
        if self.used:
            raise InterpreterException("Can not set values on configuration object that has been used.")
        name = args[0]
        val = args[1]
        desc = kwargs.get('description', None)
        if not isinstance(name, str):
            raise InterpreterException("First argument to set must be a string.")
        if desc is not None and not isinstance(desc, str):
            raise InterpreterException('Description must be a string.')

        return name, val, desc

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

    def get_method(self, args, kwargs):
        if len(args) < 1 or len(args) > 2:
            raise InterpreterException('Get method takes one or two arguments.')
        name = args[0]
        if name in self.held_object:
            return self.held_object.get(name)[0]
        if len(args) > 1:
            return args[1]
        raise InterpreterException('Entry %s not in configuration data.' % name)

    def get(self, name):
        return self.held_object.values[name]     # (val, desc)

    def keys(self):
        return self.held_object.values.keys()

# Interpreter objects can not be pickled so we must have
# these wrappers.

class DependencyHolder(InterpreterObject):
    def __init__(self, dep):
        InterpreterObject.__init__(self)
        self.held_object = dep
        self.methods.update({'found': self.found_method,
                             'type_name': self.type_name_method,
                             'version': self.version_method,
                             'get_pkgconfig_variable': self.pkgconfig_method,
                             })

    def type_name_method(self, args, kwargs):
        return self.held_object.type_name

    def found_method(self, args, kwargs):
        if self.held_object.type_name == 'internal':
            return True
        return self.held_object.found()

    def version_method(self, args, kwargs):
        return self.held_object.get_version()

    def pkgconfig_method(self, args, kwargs):
        if not isinstance(args, list):
            args = [args]
        if len(args) != 1:
            raise InterpreterException('get_pkgconfig_variable takes exactly one argument.')
        varname = args[0]
        if not isinstance(varname, str):
            raise InterpreterException('Variable name must be a string.')
        return self.held_object.get_pkgconfig_variable(varname)

class InternalDependencyHolder(InterpreterObject):
    def __init__(self, dep):
        InterpreterObject.__init__(self)
        self.held_object = dep
        self.methods.update({'found': self.found_method,
                             'version': self.version_method,
                             })

    def found_method(self, args, kwargs):
        return True

    def version_method(self, args, kwargs):
        return self.held_object.get_version()

class ExternalProgramHolder(InterpreterObject):
    def __init__(self, ep):
        InterpreterObject.__init__(self)
        self.held_object = ep
        self.methods.update({'found': self.found_method,
                             'path': self.path_method})

    def found_method(self, args, kwargs):
        return self.found()

    def path_method(self, args, kwargs):
        return self.held_object.get_path()

    def found(self):
        return self.held_object.found()

    def get_command(self):
        return self.held_object.get_command()

    def get_name(self):
        return self.held_object.get_name()

class ExternalLibraryHolder(InterpreterObject):
    def __init__(self, el):
        InterpreterObject.__init__(self)
        self.held_object = el
        self.methods.update({'found': self.found_method})

    def found(self):
        return self.held_object.found()

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

class GeneratorHolder(InterpreterObject):
    def __init__(self, interpreter, args, kwargs):
        super().__init__()
        self.interpreter = interpreter
        self.held_object = build.Generator(args, kwargs)
        self.methods.update({'process': self.process_method})

    def process_method(self, args, kwargs):
        extras = mesonlib.stringlistify(kwargs.get('extra_args', []))
        gl = self.held_object.process_files('Generator', args, self.interpreter, extra_args=extras)
        return GeneratedListHolder(gl)


class GeneratedListHolder(InterpreterObject):
    def __init__(self, arg1, extra_args=[]):
        super().__init__()
        if isinstance(arg1, GeneratorHolder):
            self.held_object = build.GeneratedList(arg1.held_object, extra_args)
        else:
            self.held_object = arg1

    def __repr__(self):
        r = '<{}: {!r}>'
        return r.format(self.__class__.__name__, self.held_object.get_outputs())

    def add_file(self, a):
        self.held_object.add_file(a)

class BuildMachine(InterpreterObject):
    def __init__(self, compilers):
        self.compilers = compilers
        InterpreterObject.__init__(self)
        self.held_object = environment.MachineInfo(environment.detect_system(),
                                                   environment.detect_cpu_family(self.compilers),
                                                   environment.detect_cpu(self.compilers),
                                                   sys.byteorder)
        self.methods.update({'system': self.system_method,
                             'cpu_family': self.cpu_family_method,
                             'cpu': self.cpu_method,
                             'endian': self.endian_method,
                             })

    def cpu_family_method(self, args, kwargs):
        return self.held_object.cpu_family

    def cpu_method(self, args, kwargs):
        return self.held_object.cpu

    def system_method(self, args, kwargs):
        return self.held_object.system

    def endian_method(self, args, kwargs):
        return self.held_object.endian

# This class will provide both host_machine and
# target_machine
class CrossMachineInfo(InterpreterObject):
    def __init__(self, cross_info):
        InterpreterObject.__init__(self)
        minimum_cross_info = {'cpu', 'cpu_family', 'endian', 'system'}
        if set(cross_info) < minimum_cross_info:
            raise InterpreterException(
                'Machine info is currently {}\n'.format(cross_info) +
                'but is missing {}.'.format(minimum_cross_info - set(cross_info)))
        self.info = cross_info
        self.held_object = environment.MachineInfo(cross_info['system'],
                                                   cross_info['cpu_family'],
                                                   cross_info['cpu'],
                                                   cross_info['endian'])
        self.methods.update({'system': self.system_method,
                             'cpu': self.cpu_method,
                             'cpu_family': self.cpu_family_method,
                             'endian': self.endian_method,
                             })

    def cpu_family_method(self, args, kwargs):
        return self.held_object.cpu_family

    def cpu_method(self, args, kwargs):
        return self.held_object.cpu

    def system_method(self, args, kwargs):
        return self.held_object.system

    def endian_method(self, args, kwargs):
        return self.held_object.endian

class IncludeDirsHolder(InterpreterObject):
    def __init__(self, idobj):
        super().__init__()
        self.held_object = idobj

class Headers(InterpreterObject):

    def __init__(self, sources, kwargs):
        InterpreterObject.__init__(self)
        self.sources = sources
        self.install_subdir = kwargs.get('subdir', '')
        self.custom_install_dir = kwargs.get('install_dir', None)
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

class DataHolder(InterpreterObject):
    def __init__(self, data):
        super().__init__()
        self.held_object = data

    def get_source_subdir(self):
        return self.held_object.source_subdir

    def get_sources(self):
        return self.held_object.sources

    def get_install_dir(self):
        return self.held_object.install_dir

class InstallDir(InterpreterObject):
    def __init__(self, src_subdir, inst_subdir, install_dir, install_mode):
        InterpreterObject.__init__(self)
        self.source_subdir = src_subdir
        self.installable_subdir = inst_subdir
        self.install_dir = install_dir
        self.install_mode = install_mode

class Man(InterpreterObject):

    def __init__(self, source_subdir, sources, kwargs):
        InterpreterObject.__init__(self)
        self.source_subdir = source_subdir
        self.sources = sources
        self.validate_sources()
        if len(kwargs) > 1:
            raise InvalidArguments('Man function takes at most one keyword arguments.')
        self.custom_install_dir = kwargs.get('install_dir', None)
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

    def get_sources(self):
        return self.sources

    def get_source_subdir(self):
        return self.source_subdir

class GeneratedObjectsHolder(InterpreterObject):
    def __init__(self, held_object):
        super().__init__()
        self.held_object = held_object

class TargetHolder(InterpreterObject):
    def __init__(self):
        super().__init__()

class BuildTargetHolder(TargetHolder):
    def __init__(self, target, interp):
        super().__init__()
        self.held_object = target
        self.interpreter = interp
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

    def private_dir_include_method(self, args, kwargs):
        return IncludeDirsHolder(build.IncludeDirs('', [], False,
                                                   [self.interpreter.backend.get_target_private_dir(self.held_object)]))

    def full_path_method(self, args, kwargs):
        return self.interpreter.backend.get_target_filename_abs(self.held_object)

    def outdir_method(self, args, kwargs):
        return self.interpreter.backend.get_target_dir(self.held_object)

    def extract_objects_method(self, args, kwargs):
        gobjs = self.held_object.extract_objects(args)
        return GeneratedObjectsHolder(gobjs)

    def extract_all_objects_method(self, args, kwargs):
        gobjs = self.held_object.extract_all_objects()
        return GeneratedObjectsHolder(gobjs)

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

class SharedModuleHolder(BuildTargetHolder):
    def __init__(self, target, interp):
        super().__init__(target, interp)

class JarHolder(BuildTargetHolder):
    def __init__(self, target, interp):
        super().__init__(target, interp)

class CustomTargetHolder(TargetHolder):
    def __init__(self, object_to_hold, interp):
        super().__init__()
        self.held_object = object_to_hold
        self.interpreter = interp
        self.methods.update({'full_path': self.full_path_method,
                             })

    def __repr__(self):
        r = '<{} {}: {}>'
        h = self.held_object
        return r.format(self.__class__.__name__, h.get_id(), h.command)

    def full_path_method(self, args, kwargs):
        return self.interpreter.backend.get_target_filename_abs(self.held_object)

class RunTargetHolder(InterpreterObject):
    def __init__(self, name, command, args, dependencies, subdir):
        super().__init__()
        self.held_object = build.RunTarget(name, command, args, dependencies, subdir)

    def __repr__(self):
        r = '<{} {}: {}>'
        h = self.held_object
        return r.format(self.__class__.__name__, h.get_id(), h.command)

class Test(InterpreterObject):
    def __init__(self, name, suite, exe, is_parallel, cmd_args, env, should_fail, timeout, workdir):
        InterpreterObject.__init__(self)
        self.name = name
        self.suite = suite
        self.exe = exe
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

class SubprojectHolder(InterpreterObject):

    def __init__(self, subinterpreter):
        super().__init__()
        self.held_object = subinterpreter
        self.methods.update({'get_variable': self.get_variable_method,
                             })

    def get_variable_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Get_variable takes one argument.')
        varname = args[0]
        if not isinstance(varname, str):
            raise InterpreterException('Get_variable takes a string argument.')
        return self.held_object.variables[varname]

class CompilerHolder(InterpreterObject):
    def __init__(self, compiler, env):
        InterpreterObject.__init__(self)
        self.compiler = compiler
        self.environment = env
        self.methods.update({'compiles': self.compiles_method,
                             'links': self.links_method,
                             'get_id': self.get_id_method,
                             'compute_int': self.compute_int_method,
                             'sizeof': self.sizeof_method,
                             'get_define': self.get_define_method,
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
                             'has_multi_arguments': self.has_multi_arguments_method,
                             'first_supported_argument': self.first_supported_argument_method,
                             'unittest_args': self.unittest_args_method,
                             'symbols_have_underscore_prefix': self.symbols_have_underscore_prefix_method,
                             })

    def version_method(self, args, kwargs):
        return self.compiler.version

    def cmd_array_method(self, args, kwargs):
        return self.compiler.exelist

    def determine_args(self, kwargs):
        nobuiltins = kwargs.get('no_builtin_args', False)
        if not isinstance(nobuiltins, bool):
            raise InterpreterException('Type of no_builtin_args not a boolean.')
        args = []
        incdirs = kwargs.get('include_directories', [])
        if not isinstance(incdirs, list):
            incdirs = [incdirs]
        for i in incdirs:
            if not isinstance(i, IncludeDirsHolder):
                raise InterpreterException('Include directories argument must be an include_directories object.')
            for idir in i.held_object.get_incdirs():
                idir = os.path.join(self.environment.get_source_dir(), idir)
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
            if not isinstance(deps, list):
                deps = [deps]
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
        mlog.log('Checking for alignment of "', mlog.bold(typename), '": ', result, sep='')
        return result

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
            mlog.log('Checking if "', mlog.bold(testname), '" runs: ', h, sep='')
        return TryRunResultHolder(result)

    def get_id_method(self, args, kwargs):
        return self.compiler.get_id()

    def symbols_have_underscore_prefix_method(self, args, kwargs):
        '''
        Check if the compiler prefixes _ (underscore) to global C symbols
        See: https://en.wikipedia.org/wiki/Name_mangling#C
        '''
        return self.compiler.symbols_have_underscore_prefix(self.environment)

    def unittest_args_method(self, args, kwargs):
        # At time, only D compilers have this feature.
        if not hasattr(self.compiler, 'get_unittest_args'):
            raise InterpreterException('This {} compiler has no unittest arguments.'.format(self.compiler.language))
        return self.compiler.get_unittest_args()

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
        mlog.log('Checking whether type "', mlog.bold(typename),
                 '" has member "', mlog.bold(membername), '": ', hadtxt, sep='')
        return had

    def has_members_method(self, args, kwargs):
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
        mlog.log('Checking whether type "', mlog.bold(typename),
                 '" has members ', members, ': ', hadtxt, sep='')
        return had

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
        mlog.log('Checking for function "', mlog.bold(funcname), '": ', hadtxt, sep='')
        return had

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
        mlog.log('Checking for type "', mlog.bold(typename), '": ', hadtxt, sep='')
        return had

    def compute_int_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Compute_int takes exactly one argument.')
        check_stringlist(args)
        expression = args[0]
        prefix = kwargs.get('prefix', '')
        l = kwargs.get('low', -1024)
        h = kwargs.get('high', 1024)
        guess = kwargs.get('guess', None)
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of compute_int must be a string.')
        if not isinstance(l, int):
            raise InterpreterException('Low argument of compute_int must be an int.')
        if not isinstance(h, int):
            raise InterpreterException('High argument of compute_int must be an int.')
        if guess is not None and not isinstance(guess, int):
            raise InterpreterException('Guess argument of compute_int must be an int.')
        extra_args = self.determine_args(kwargs)
        deps = self.determine_dependencies(kwargs)
        res = self.compiler.compute_int(expression, l, h, guess, prefix, self.environment, extra_args, deps)
        mlog.log('Computing int of "%s": %d' % (expression, res))
        return res

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
        mlog.log('Checking for value of define "%s": %s' % (element, value))
        return value

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
            mlog.log('Checking if "', mlog.bold(testname), '" compiles: ', h, sep='')
        return result

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
            mlog.log('Checking if "', mlog.bold(testname), '" links: ', h, sep='')
        return result

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

    def find_library_method(self, args, kwargs):
        # TODO add dependencies support?
        if len(args) != 1:
            raise InterpreterException('find_library method takes one argument.')
        libname = args[0]
        if not isinstance(libname, str):
            raise InterpreterException('Library name not a string.')
        required = kwargs.get('required', True)
        if not isinstance(required, bool):
            raise InterpreterException('required must be boolean.')
        search_dirs = mesonlib.stringlistify(kwargs.get('dirs', []))
        for i in search_dirs:
            if not os.path.isabs(i):
                raise InvalidCode('Search directory %s is not an absolute path.' % i)
        linkargs = self.compiler.find_library(libname, self.environment, search_dirs)
        if required and not linkargs:
            l = self.compiler.language.capitalize()
            raise InterpreterException('{} library {!r} not found'.format(l, libname))
        lib = dependencies.ExternalLibrary(libname, linkargs, self.environment,
                                           self.compiler.language)
        return ExternalLibraryHolder(lib)

    def has_argument_method(self, args, kwargs):
        args = mesonlib.stringlistify(args)
        if len(args) != 1:
            raise InterpreterException('Has_arg takes exactly one argument.')
        result = self.compiler.has_argument(args[0], self.environment)
        if result:
            h = mlog.green('YES')
        else:
            h = mlog.red('NO')
        mlog.log('Compiler for {} supports argument {}:'.format(self.compiler.language, args[0]), h)
        return result

    def has_multi_arguments_method(self, args, kwargs):
        args = mesonlib.stringlistify(args)
        result = self.compiler.has_multi_arguments(args, self.environment)
        if result:
            h = mlog.green('YES')
        else:
            h = mlog.red('NO')
        mlog.log(
            'Compiler for {} supports arguments {}:'.format(
                self.compiler.language, ' '.join(args)),
            h)
        return result

    def first_supported_argument_method(self, args, kwargs):
        for i in mesonlib.stringlistify(args):
            if self.compiler.has_argument(i, self.environment):
                mlog.log('First supported argument:', mlog.bold(i))
                return [i]
        mlog.log('First supported argument:', mlog.red('None'))
        return []

ModuleState = namedtuple('ModuleState', [
    'build_to_src', 'subdir', 'environment', 'project_name', 'project_version',
    'backend', 'compilers', 'targets', 'data', 'headers', 'man', 'global_args',
    'project_args', 'build_machine', 'host_machine', 'target_machine'])

class ModuleHolder(InterpreterObject):
    def __init__(self, modname, module, interpreter):
        InterpreterObject.__init__(self)
        self.modname = modname
        self.held_object = module
        self.interpreter = interpreter

    def method_call(self, method_name, args, kwargs):
        try:
            fn = getattr(self.held_object, method_name)
        except AttributeError:
            raise InvalidArguments('Module %s does not have method %s.' % (self.modname, method_name))
        if method_name.startswith('_'):
            raise InvalidArguments('Function {!r} in module {!r} is private.'.format(method_name, self.modname))
        # This is not 100% reliable but we can't use hash()
        # because the Build object contains dicts and lists.
        num_targets = len(self.interpreter.build.targets)
        state = ModuleState(
            build_to_src=os.path.relpath(self.interpreter.environment.get_source_dir(),
                                         self.interpreter.environment.get_build_dir()),
            subdir=self.interpreter.subdir,
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
                             'install_dependency_manifest': self.install_dependency_manifest_method,
                             'project_version': self.project_version_method,
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

    def add_install_script_method(self, args, kwargs):
        if len(args) < 1:
            raise InterpreterException('add_install_script takes one or more arguments')
        check_stringlist(args, 'add_install_script args must be strings')
        script = self._find_source_script(args[0], args[1:])
        self.build.install_scripts.append(script)

    def add_postconf_script_method(self, args, kwargs):
        if len(args) < 1:
            raise InterpreterException('add_postconf_script takes one or more arguments')
        check_stringlist(args, 'add_postconf_script arguments must be strings')
        script = self._find_source_script(args[0], args[1:])
        self.build.postconf_scripts.append(script)

    def current_source_dir_method(self, args, kwargs):
        src = self.interpreter.environment.source_dir
        sub = self.interpreter.subdir
        if sub == '':
            return src
        return os.path.join(src, sub)

    def current_build_dir_method(self, args, kwargs):
        src = self.interpreter.environment.build_dir
        sub = self.interpreter.subdir
        if sub == '':
            return src
        return os.path.join(src, sub)

    def backend_method(self, args, kwargs):
        return self.interpreter.backend.name

    def source_root_method(self, args, kwargs):
        return self.interpreter.environment.source_dir

    def build_root_method(self, args, kwargs):
        return self.interpreter.environment.build_dir

    def has_exe_wrapper_method(self, args, kwargs):
        if self.is_cross_build_method(None, None) and \
           'binaries' in self.build.environment.cross_info.config and \
           self.build.environment.cross_info.need_exe_wrapper():
            exe_wrap = self.build.environment.cross_info.config['binaries'].get('exe_wrapper', None)
            if exe_wrap is None:
                return False
        # We return True when exe_wrap is defined, when it's not needed, and
        # when we're compiling natively. The last two are semantically confusing.
        # Need to revisit this.
        return True

    def is_cross_build_method(self, args, kwargs):
        return self.build.environment.is_cross_build()

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
            return CompilerHolder(clist[cname], self.build.environment)
        raise InterpreterException('Tried to access compiler for unspecified language "%s".' % cname)

    def is_unity_method(self, args, kwargs):
        optval = self.interpreter.environment.coredata.get_builtin_option('unity')
        if optval == 'on' or (optval == 'subprojects' and self.interpreter.subproject != ''):
            return True
        return False

    def is_subproject_method(self, args, kwargs):
        return self.interpreter.is_subproject()

    def install_dependency_manifest_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Must specify manifest install file name')
        if not isinstance(args[0], str):
            raise InterpreterException('Argument must be a string.')
        self.build.dep_manifest_name = args[0]

    def project_version_method(self, args, kwargs):
        return self.build.dep_manifest[self.interpreter.active_projectname]['version']

    def version_method(self, args, kwargs):
        return coredata.version

    def project_name_method(self, args, kwargs):
        return self.interpreter.active_projectname

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

class Interpreter(InterpreterBase):

    def __init__(self, build, backend, subproject='', subdir='', subproject_dir='subprojects',
                 default_project_options=[]):
        super().__init__(build.environment.get_source_dir(), subdir)
        self.build = build
        self.environment = build.environment
        self.coredata = self.environment.get_coredata()
        self.backend = backend
        self.subproject = subproject
        self.subproject_dir = subproject_dir
        self.option_file = os.path.join(self.source_root, self.subdir, 'meson_options.txt')
        self.load_root_meson_file()
        self.sanity_check_ast()
        self.builtin.update({'meson': MesonMain(build, self)})
        self.generators = []
        self.visited_subdirs = {}
        self.project_args_frozen = False
        self.global_args_frozen = False  # implies self.project_args_frozen
        self.subprojects = {}
        self.subproject_stack = []
        self.default_project_options = default_project_options[:] # Passed from the outside, only used in subprojects.
        self.build_func_dict()
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
        self.build_def_files = [os.path.join(self.subdir, environment.build_filename)]

    def build_func_dict(self):
        self.funcs.update({'project': self.func_project,
                           'message': self.func_message,
                           'error': self.func_error,
                           'executable': self.func_executable,
                           'dependency': self.func_dependency,
                           'static_library': self.func_static_lib,
                           'shared_library': self.func_shared_lib,
                           'shared_module': self.func_shared_module,
                           'library': self.func_library,
                           'jar': self.func_jar,
                           'build_target': self.func_build_target,
                           'custom_target': self.func_custom_target,
                           'run_target': self.func_run_target,
                           'generator': self.func_generator,
                           'test': self.func_test,
                           'benchmark': self.func_benchmark,
                           'install_headers': self.func_install_headers,
                           'install_man': self.func_install_man,
                           'subdir': self.func_subdir,
                           'install_data': self.func_install_data,
                           'install_subdir': self.func_install_subdir,
                           'configure_file': self.func_configure_file,
                           'include_directories': self.func_include_directories,
                           'add_global_arguments': self.func_add_global_arguments,
                           'add_project_arguments': self.func_add_project_arguments,
                           'add_global_link_arguments': self.func_add_global_link_arguments,
                           'add_project_link_arguments': self.func_add_project_link_arguments,
                           'add_test_setup': self.func_add_test_setup,
                           'add_languages': self.func_add_languages,
                           'find_program': self.func_find_program,
                           'find_library': self.func_find_library,
                           'configuration_data': self.func_configuration_data,
                           'run_command': self.func_run_command,
                           'gettext': self.func_gettext,
                           'option': self.func_option,
                           'get_option': self.func_get_option,
                           'subproject': self.func_subproject,
                           'vcs_tag': self.func_vcs_tag,
                           'set_variable': self.func_set_variable,
                           'is_variable': self.func_is_variable,
                           'get_variable': self.func_get_variable,
                           'import': self.func_import,
                           'files': self.func_files,
                           'declare_dependency': self.func_declare_dependency,
                           'assert': self.func_assert,
                           'environment': self.func_environment,
                           'join_paths': self.func_join_paths,
                           })

    def holderify(self, item):
        if isinstance(item, list):
            return [self.holderify(x) for x in item]
        if isinstance(item, build.CustomTarget):
            return CustomTargetHolder(item, self)
        elif isinstance(item, (int, str)) or item is None:
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
            return InternalDependencyHolder(item)
        elif isinstance(item, dependencies.ExternalProgram):
            return ExternalProgramHolder(item)
        elif hasattr(item, 'held_object'):
            return item
        else:
            raise InterpreterException('Module returned a value of unknown type.')

    def process_new_values(self, invalues):
        if not isinstance(invalues, list):
            invalues = [invalues]
        for v in invalues:
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

    @stringArgs
    @noKwargs
    def func_import(self, node, args, kwargs):
        if len(args) != 1:
            raise InvalidCode('Import takes one argument.')
        modname = args[0]
        if modname not in self.environment.coredata.modules:
            try:
                module = importlib.import_module('mesonbuild.modules.' + modname)
            except ImportError:
                raise InvalidArguments('Module "%s" does not exist' % (modname, ))
            self.environment.coredata.modules[modname] = module.initialize()
        return ModuleHolder(modname, self.environment.coredata.modules[modname], self)

    @stringArgs
    @noKwargs
    def func_files(self, node, args, kwargs):
        return [mesonlib.File.from_source_file(self.environment.source_dir, self.subdir, fname) for fname in args]

    @noPosargs
    def func_declare_dependency(self, node, args, kwargs):
        version = kwargs.get('version', self.project_version)
        if not isinstance(version, str):
            raise InterpreterException('Version must be a string.')
        incs = kwargs.get('include_directories', [])
        if not isinstance(incs, list):
            incs = [incs]
        libs = kwargs.get('link_with', [])
        if not isinstance(libs, list):
            libs = [libs]
        sources = kwargs.get('sources', [])
        if not isinstance(sources, list):
            sources = [sources]
        sources = self.source_strings_to_files(self.flatten(sources))
        deps = self.flatten(kwargs.get('dependencies', []))
        if not isinstance(deps, list):
            deps = [deps]
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
        dep = dependencies.InternalDependency(version, incs, compile_args, link_args, libs, sources, final_deps)
        return DependencyHolder(dep)

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

    def func_run_command(self, node, args, kwargs):
        if len(args) < 1:
            raise InterpreterException('Not enough arguments')
        cmd = args[0]
        cargs = args[1:]
        srcdir = self.environment.get_source_dir()
        builddir = self.environment.get_build_dir()
        m = 'must be a string, or the output of find_program(), files(), or ' \
            'configure_file(); not {!r}'
        if isinstance(cmd, ExternalProgramHolder):
            cmd = cmd.held_object
        else:
            if isinstance(cmd, mesonlib.File):
                cmd = cmd.absolute_path(srcdir, builddir)
            elif not isinstance(cmd, str):
                raise InterpreterException('First argument ' + m.format(cmd))
            # Prefer scripts in the current source directory
            search_dir = os.path.join(srcdir, self.subdir)
            prog = ExternalProgram(cmd, silent=True, search_dir=search_dir)
            if not prog.found():
                raise InterpreterException('Program or command {!r} not found'
                                           'or not executable'.format(cmd))
            cmd = prog
        expanded_args = []
        for a in mesonlib.flatten(cargs):
            if isinstance(a, str):
                expanded_args.append(a)
            elif isinstance(a, mesonlib.File):
                expanded_args.append(a.absolute_path(srcdir, builddir))
            elif isinstance(a, ExternalProgramHolder):
                expanded_args.append(a.held_object.get_path())
            else:
                raise InterpreterException('Arguments ' + m.format(a))
        in_builddir = kwargs.get('in_builddir', False)
        if not isinstance(in_builddir, bool):
            raise InterpreterException('in_builddir must be boolean.')
        return RunProcess(cmd, expanded_args, srcdir, builddir, self.subdir,
                          get_meson_script(self.environment, 'mesonintrospect'), in_builddir)

    @stringArgs
    def func_gettext(self, nodes, args, kwargs):
        raise InterpreterException('Gettext() function has been moved to module i18n. Import it and use i18n.gettext() instead')

    def func_option(self, nodes, args, kwargs):
        raise InterpreterException('Tried to call option() in build description file. All options must be in the option file.')

    @stringArgs
    def func_subproject(self, nodes, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Subproject takes exactly one argument')
        dirname = args[0]
        return self.do_subproject(dirname, kwargs)

    def do_subproject(self, dirname, kwargs):
        if dirname in self.subproject_stack:
            fullstack = self.subproject_stack + [dirname]
            incpath = ' => '.join(fullstack)
            raise InvalidCode('Recursive include of subprojects: %s.' % incpath)
        if dirname in self.subprojects:
            return self.subprojects[dirname]
        subproject_dir_abs = os.path.join(self.environment.get_source_dir(), self.subproject_dir)
        r = wrap.Resolver(subproject_dir_abs, self.coredata.wrap_mode)
        try:
            resolved = r.resolve(dirname)
        except RuntimeError as e:
            msg = 'Subproject directory {!r} does not exist and cannot be downloaded:\n{}'
            raise InterpreterException(msg.format(os.path.join(self.subproject_dir, dirname), e))
        subdir = os.path.join(self.subproject_dir, resolved)
        os.makedirs(os.path.join(self.build.environment.get_build_dir(), subdir), exist_ok=True)
        self.global_args_frozen = True
        mlog.log('\nExecuting subproject ', mlog.bold(dirname), '.\n', sep='')
        subi = Interpreter(self.build, self.backend, dirname, subdir, self.subproject_dir,
                           mesonlib.stringlistify(kwargs.get('default_options', [])))
        subi.subprojects = self.subprojects

        subi.subproject_stack = self.subproject_stack + [dirname]
        current_active = self.active_projectname
        subi.run()
        if 'version' in kwargs:
            pv = subi.project_version
            wanted = kwargs['version']
            if pv == 'undefined' or not mesonlib.version_compare(pv, wanted):
                raise InterpreterException('Subproject %s version is %s but %s required.' % (dirname, pv, wanted))
        self.active_projectname = current_active
        mlog.log('\nSubproject', mlog.bold(dirname), 'finished.')
        self.build.subprojects[dirname] = subi.project_version
        self.subprojects.update(subi.subprojects)
        self.subprojects[dirname] = SubprojectHolder(subi)
        self.build_def_files += subi.build_def_files
        return self.subprojects[dirname]

    @stringArgs
    @noKwargs
    def func_get_option(self, nodes, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Argument required for get_option.')
        optname = args[0]
        try:
            return self.environment.get_coredata().get_builtin_option(optname)
        except RuntimeError:
            pass
        try:
            return self.environment.coredata.compiler_options[optname].value
        except KeyError:
            pass
        if not coredata.is_builtin_option(optname) and self.is_subproject():
            optname = self.subproject + ':' + optname
        try:
            return self.environment.coredata.user_options[optname].value
        except KeyError:
            pass
        if optname.endswith('_link_args'):
            try:
                lang = optname[:-10]
                return self.coredata.external_link_args[lang]
            except KeyError:
                pass
        if optname.endswith('_args'):
            try:
                lang = optname[:-5]
                return self.coredata.external_args[lang]
            except KeyError:
                pass
        raise InterpreterException('Tried to access unknown option "%s".' % optname)

    @noKwargs
    def func_configuration_data(self, node, args, kwargs):
        if args:
            raise InterpreterException('configuration_data takes no arguments')
        return ConfigurationDataHolder()

    def parse_default_options(self, default_options):
        if not isinstance(default_options, list):
            default_options = [default_options]
        for option in default_options:
            if not isinstance(option, str):
                mlog.debug(option)
                raise InterpreterException('Default options must be strings')
            if '=' not in option:
                raise InterpreterException('All default options must be of type key=value.')
            key, value = option.split('=', 1)
            if coredata.is_builtin_option(key):
                if self.subproject != '':
                    continue # Only the master project is allowed to set global options.
                if not self.environment.had_argument_for(key):
                    self.coredata.set_builtin_option(key, value)
                # If this was set on the command line, do not override.
            else:
                # Option values set with subproject() default_options override those
                # set in project() default_options.
                pref = key + '='
                for i in self.default_project_options:
                    if i.startswith(pref):
                        option = i
                        break
                # If we are in a subproject, add the subproject prefix to option
                # name.
                if self.subproject != '':
                    option = self.subproject + ':' + option
                newoptions = [option] + self.environment.cmd_line_options.projectoptions
                self.environment.cmd_line_options.projectoptions = newoptions
        # Add options that are only in default_options.
        for defopt in self.default_project_options:
            key, value = defopt.split('=')
            pref = key + '='
            for i in default_options:
                if i.startswith(pref):
                    break
            else:
                defopt = self.subproject + ':' + defopt
                newoptions = [defopt] + self.environment.cmd_line_options.projectoptions
                self.environment.cmd_line_options.projectoptions = newoptions

    @stringArgs
    def func_project(self, node, args, kwargs):
        if len(args) < 1:
            raise InvalidArguments('Not enough arguments to project(). Needs at least the project name.')
        proj_name = args[0]
        proj_langs = args[1:]
        if ':' in proj_name:
            raise InvalidArguments("Project name {!r} must not contain ':'".format(proj_name))
        default_options = kwargs.get('default_options', [])
        if self.environment.first_invocation and (len(default_options) > 0 or
                                                  len(self.default_project_options) > 0):
            self.parse_default_options(default_options)
        if not self.is_subproject():
            self.build.project_name = proj_name
        if os.path.exists(self.option_file):
            oi = optinterpreter.OptionInterpreter(self.subproject,
                                                  self.build.environment.cmd_line_options.projectoptions,
                                                  )
            oi.process(self.option_file)
            self.build.environment.merge_options(oi.options)
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
            self.subproject_dir = kwargs['subproject_dir']

        if 'meson_version' in kwargs:
            cv = coredata.version
            pv = kwargs['meson_version']
            if not mesonlib.version_compare(cv, pv):
                raise InterpreterException('Meson version is %s but project requires %s.' % (cv, pv))
        self.build.projects[self.subproject] = proj_name
        mlog.log('Project name: ', mlog.bold(proj_name), sep='')
        self.add_languages(proj_langs, True)
        langs = self.coredata.compilers.keys()
        if 'vala' in langs:
            if 'c' not in langs:
                raise InterpreterException('Compiling Vala requires C. Add C to your project languages and rerun Meson.')
        if not self.is_subproject():
            self.check_cross_stdlibs()

    @stringArgs
    def func_add_languages(self, node, args, kwargs):
        return self.add_languages(args, kwargs.get('required', True))

    @noKwargs
    def func_message(self, node, args, kwargs):
        # reduce arguments again to avoid flattening posargs
        (posargs, _) = self.reduce_arguments(node.args)
        if len(posargs) != 1:
            raise InvalidArguments('Expected 1 argument, got %d' % len(posargs))

        arg = posargs[0]
        if isinstance(arg, list):
            argstr = stringifyUserArguments(arg)
        elif isinstance(arg, str):
            argstr = arg
        elif isinstance(arg, int):
            argstr = str(arg)
        else:
            raise InvalidArguments('Function accepts only strings, integers, lists and lists thereof.')

        mlog.log(mlog.bold('Message:'), argstr)

    @noKwargs
    def func_error(self, node, args, kwargs):
        self.validate_arguments(args, 1, [str])
        raise InterpreterException('Error encountered: ' + args[0])

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
            comp = self.environment.detect_rust_compiler()
            if need_cross_compiler:
                cross_comp = comp  # FIXME, not correct.
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
        for i in new_options:
            if not i.startswith(optprefix):
                raise InterpreterException('Internal error, %s has incorrect prefix.' % i)
            cmd_prefix = i + '='
            for cmd_arg in self.environment.cmd_line_options.projectoptions:
                if cmd_arg.startswith(cmd_prefix):
                    value = cmd_arg.split('=', 1)[1]
                    new_options[i].set_value(value)
        new_options.update(self.coredata.compiler_options)
        self.coredata.compiler_options = new_options
        return comp, cross_comp

    def add_languages(self, args, required):
        success = True
        need_cross_compiler = self.environment.is_cross_build() and self.environment.cross_info.need_cross_compiler()
        for lang in sorted(args, key=compilers.sort_clike):
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
            mlog.log('Native %s compiler: ' % lang, mlog.bold(' '.join(comp.get_exelist())), ' (%s %s)' % (comp.id, comp.version), sep='')
            if not comp.get_language() in self.coredata.external_args:
                (preproc_args, compile_args, link_args) = environment.get_args_from_envvars(comp)
                self.coredata.external_preprocess_args[comp.get_language()] = preproc_args
                self.coredata.external_args[comp.get_language()] = compile_args
                self.coredata.external_link_args[comp.get_language()] = link_args
            self.build.add_compiler(comp)
            if need_cross_compiler:
                mlog.log('Cross %s compiler: ' % lang, mlog.bold(' '.join(cross_comp.get_exelist())), ' (%s %s)' % (cross_comp.id, cross_comp.version), sep='')
                self.build.add_cross_compiler(cross_comp)
            if self.environment.is_cross_build() and not need_cross_compiler:
                self.build.add_cross_compiler(comp)
            self.add_base_options(comp)
        return success

    def add_base_options(self, compiler):
        proj_opt = self.environment.cmd_line_options.projectoptions
        for optname in compiler.base_options:
            if optname in self.coredata.base_options:
                continue
            oobj = compilers.base_options[optname]
            for po in proj_opt:
                if po.startswith(optname + '='):
                    oobj.set_value(po.split('=', 1)[1])
                    break
            self.coredata.base_options[optname] = oobj

    def func_find_program(self, node, args, kwargs):
        if not args:
            raise InterpreterException('No program name specified.')
        required = kwargs.get('required', True)
        if not isinstance(required, bool):
            raise InvalidArguments('"required" argument must be a boolean.')
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
            extprog = dependencies.ExternalProgram(exename, search_dir=search_dir)
            progobj = ExternalProgramHolder(extprog)
            if progobj.found():
                return progobj
        if required and not progobj.found():
            raise InvalidArguments('Program "%s" not found or not executable' % exename)
        return progobj

    def func_find_library(self, node, args, kwargs):
        mlog.log(mlog.red('DEPRECATION:'), 'find_library() is removed, use the corresponding method in compiler object instead.')

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

    def func_dependency(self, node, args, kwargs):
        self.validate_arguments(args, 1, [str])
        name = args[0]
        if '<' in name or '>' in name or '=' in name:
            raise InvalidArguments('Characters <, > and = are forbidden in dependency names. To specify'
                                   'version\n requirements use the \'version\' keyword argument instead.')
        identifier, cached_dep = self._find_cached_dep(name, kwargs)

        if cached_dep:
            if kwargs.get('required', True) and not cached_dep.found():
                m = 'Dependency {!r} was already checked and was not found'
                raise DependencyException(m.format(name))
            dep = cached_dep
        else:
            # We need to actually search for this dep
            exception = None
            dep = None
            # If the dependency has already been configured, possibly by
            # a higher level project, try to use it first.
            if 'fallback' in kwargs:
                dirname, varname = self.get_subproject_infos(kwargs)
                if dirname in self.subprojects:
                    subproject = self.subprojects[dirname]
                    try:
                        # Never add fallback deps to self.coredata.deps
                        return subproject.get_variable_method([varname], {})
                    except KeyError:
                        pass

            # Search for it outside the project
            if not dep:
                try:
                    dep = dependencies.find_external_dependency(name, self.environment, kwargs)
                except DependencyException as e:
                    exception = e
                    pass

            # Search inside the projects list
            if not dep or not dep.found():
                if 'fallback' in kwargs:
                    fallback_dep = self.dependency_fallback(name, kwargs)
                    if fallback_dep:
                        # Never add fallback deps to self.coredata.deps since we
                        # cannot cache them. They must always be evaluated else
                        # we won't actually read all the build files.
                        return fallback_dep
                if not dep:
                    raise exception

        # Only store found-deps in the cache
        if dep.found():
            self.coredata.deps[identifier] = dep
        return DependencyHolder(dep)

    def get_subproject_infos(self, kwargs):
        fbinfo = kwargs['fallback']
        check_stringlist(fbinfo)
        if len(fbinfo) != 2:
            raise InterpreterException('Fallback info must have exactly two items.')
        return fbinfo

    def dependency_fallback(self, name, kwargs):
        if self.coredata.wrap_mode in (WrapMode.nofallback, WrapMode.nodownload):
            mlog.log('Not looking for a fallback subproject for the dependency',
                     mlog.bold(name), 'because:\nAutomatic wrap-based fallback '
                     'dependency downloading is disabled.')
            return None
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
        except:
            mlog.log('Also couldn\'t find a fallback subproject in',
                     mlog.bold(os.path.join(self.subproject_dir, dirname)),
                     'for the dependency', mlog.bold(name))
            return None
        try:
            dep = self.subprojects[dirname].get_variable_method([varname], {})
        except KeyError:
            if kwargs.get('required', True):
                m = 'Fallback variable {!r} in the subproject {!r} does not exist'
                raise DependencyException(m.format(varname, dirname))
            # If the dependency is not required, don't raise an exception
            mlog.log('Also couldn\'t find the dependency', mlog.bold(name),
                     'in the fallback subproject',
                     mlog.bold(os.path.join(self.subproject_dir, dirname)))
            return None
        if not isinstance(dep, DependencyHolder):
            raise InvalidCode('Fallback variable {!r} in the subproject {!r} is '
                              'not a dependency object.'.format(varname, dirname))
        # Check if the version of the declared dependency matches what we want
        if 'version' in kwargs:
            wanted = kwargs['version']
            found = dep.version_method([], {})
            if found == 'undefined' or not mesonlib.version_compare(found, wanted):
                mlog.log('Subproject', mlog.bold(dirname), 'dependency',
                         mlog.bold(varname), 'version is', mlog.bold(found),
                         'but', mlog.bold(wanted), 'is required.')
                return None
        mlog.log('Found a', mlog.green('fallback'), 'subproject',
                 mlog.bold(os.path.join(self.subproject_dir, dirname)), 'for',
                 mlog.bold(name))
        return dep

    def func_executable(self, node, args, kwargs):
        return self.build_target(node, args, kwargs, ExecutableHolder)

    def func_static_lib(self, node, args, kwargs):
        return self.build_target(node, args, kwargs, StaticLibraryHolder)

    def func_shared_lib(self, node, args, kwargs):
        return self.build_target(node, args, kwargs, SharedLibraryHolder)

    def func_shared_module(self, node, args, kwargs):
        return self.build_target(node, args, kwargs, SharedModuleHolder)

    def func_library(self, node, args, kwargs):
        if self.coredata.get_builtin_option('default_library') == 'shared':
            return self.func_shared_lib(node, args, kwargs)
        return self.func_static_lib(node, args, kwargs)

    def func_jar(self, node, args, kwargs):
        return self.build_target(node, args, kwargs, JarHolder)

    def func_build_target(self, node, args, kwargs):
        if 'target_type' not in kwargs:
            raise InterpreterException('Missing target_type keyword argument')
        target_type = kwargs.pop('target_type')
        if target_type == 'executable':
            return self.func_executable(node, args, kwargs)
        elif target_type == 'shared_library':
            return self.func_shared_lib(node, args, kwargs)
        elif target_type == 'static_library':
            return self.func_static_lib(node, args, kwargs)
        elif target_type == 'library':
            return self.func_library(node, args, kwargs)
        elif target_type == 'jar':
            return self.func_jar(node, args, kwargs)
        else:
            raise InterpreterException('Unknown target_type.')

    def func_vcs_tag(self, node, args, kwargs):
        if 'input' not in kwargs or 'output' not in kwargs:
            raise InterpreterException('Keyword arguments input and output must exist')
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
        kwargs['command'] = [sys.executable,
                             self.environment.get_build_command(),
                             '--internal',
                             'vcstagger',
                             '@INPUT0@',
                             '@OUTPUT0@',
                             fallback,
                             source_dir,
                             replace_string,
                             regex_selector] + vcs_cmd
        kwargs.setdefault('build_always', True)
        return self.func_custom_target(node, [kwargs['output']], kwargs)

    @stringArgs
    def func_custom_target(self, node, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('custom_target: Only one positional argument is allowed, and it must be a string name')
        name = args[0]
        tg = CustomTargetHolder(build.CustomTarget(name, self.subdir, kwargs), self)
        self.add_target(name, tg.held_object)
        return tg

    def func_run_target(self, node, args, kwargs):
        global run_depr_printed
        if len(args) > 1:
            if not run_depr_printed:
                mlog.log(mlog.red('DEPRECATION'), 'positional version of run_target is deprecated, use the keyword version instead.')
                run_depr_printed = True
            if 'command' in kwargs:
                raise InterpreterException('Can not have command both in positional and keyword arguments.')
            all_args = args[1:]
            deps = []
        elif len(args) == 1:
            if 'command' not in kwargs:
                raise InterpreterException('Missing "command" keyword argument')
            all_args = kwargs['command']
            if not isinstance(all_args, list):
                all_args = [all_args]
            deps = kwargs.get('depends', [])
            if not isinstance(deps, list):
                deps = [deps]
        else:
            raise InterpreterException('Run_target needs at least one positional argument.')

        cleaned_args = []
        for i in mesonlib.flatten(all_args):
            try:
                i = i.held_object
            except AttributeError:
                pass
            if not isinstance(i, (str, build.BuildTarget, build.CustomTarget, dependencies.ExternalProgram, mesonlib.File)):
                mlog.debug('Wrong type:', str(i))
                raise InterpreterException('Invalid argument to run_target.')
            cleaned_args.append(i)
        name = args[0]
        if not isinstance(name, str):
            raise InterpreterException('First argument must be a string.')
        cleaned_deps = []
        for d in deps:
            try:
                d = d.held_object
            except AttributeError:
                pass
            if not isinstance(d, (build.BuildTarget, build.CustomTarget)):
                raise InterpreterException('Depends items must be build targets.')
            cleaned_deps.append(d)
        command = cleaned_args[0]
        cmd_args = cleaned_args[1:]
        tg = RunTargetHolder(name, command, cmd_args, cleaned_deps, self.subdir)
        self.add_target(name, tg.held_object)
        return tg

    def func_generator(self, node, args, kwargs):
        gen = GeneratorHolder(self, args, kwargs)
        self.generators.append(gen)
        return gen

    def func_benchmark(self, node, args, kwargs):
        self.add_test(node, args, kwargs, False)

    def func_test(self, node, args, kwargs):
        self.add_test(node, args, kwargs, True)

    def unpack_env_kwarg(self, kwargs):
        envlist = kwargs.get('env', EnvironmentVariablesHolder())
        if isinstance(envlist, EnvironmentVariablesHolder):
            env = envlist.held_object
        else:
            if not isinstance(envlist, list):
                envlist = [envlist]
            env = {}
            for e in envlist:
                if '=' not in e:
                    raise InterpreterException('Env var definition must be of type key=val.')
                (k, val) = e.split('=', 1)
                k = k.strip()
                val = val.strip()
                if ' ' in k:
                    raise InterpreterException('Env var key must not have spaces in it.')
                env[k] = val
        return env

    def add_test(self, node, args, kwargs, is_base_test):
        if len(args) != 2:
            raise InterpreterException('Incorrect number of arguments')
        if not isinstance(args[0], str):
            raise InterpreterException('First argument of test must be a string.')
        if not isinstance(args[1], (ExecutableHolder, JarHolder, ExternalProgramHolder)):
            raise InterpreterException('Second argument must be executable.')
        par = kwargs.get('is_parallel', True)
        if not isinstance(par, bool):
            raise InterpreterException('Keyword argument is_parallel must be a boolean.')
        cmd_args = kwargs.get('args', [])
        if not isinstance(cmd_args, list):
            cmd_args = [cmd_args]
        for i in cmd_args:
            if not isinstance(i, (str, mesonlib.File, TargetHolder)):
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
        for s in mesonlib.stringlistify(kwargs.get('suite', '')):
            if len(s) > 0:
                s = ':' + s
            if self.is_subproject():
                suite.append(self.subproject.replace(' ', '_').replace(':', '_') + s)
            else:
                suite.append(self.build.project_name.replace(' ', '_').replace(':', '_') + s)
        t = Test(args[0], suite, args[1].held_object, par, cmd_args, env, should_fail, timeout, workdir)
        if is_base_test:
            self.build.tests.append(t)
            mlog.debug('Adding test "', mlog.bold(args[0]), '".', sep='')
        else:
            self.build.benchmarks.append(t)
            mlog.debug('Adding benchmark "', mlog.bold(args[0]), '".', sep='')

    def func_install_headers(self, node, args, kwargs):
        source_files = self.source_strings_to_files(args)
        h = Headers(source_files, kwargs)
        self.build.headers.append(h)
        return h

    @stringArgs
    def func_install_man(self, node, args, kwargs):
        m = Man(self.subdir, args, kwargs)
        self.build.man.append(m)
        return m

    @noKwargs
    def func_subdir(self, node, args, kwargs):
        self.validate_arguments(args, 1, [str])
        if '..' in args[0]:
            raise InvalidArguments('Subdir contains ..')
        if self.subdir == '' and args[0] == self.subproject_dir:
            raise InvalidArguments('Must not go into subprojects dir with subdir(), use subproject() instead.')
        if self.subdir == '' and args[0].startswith('meson-'):
            raise InvalidArguments('The "meson-" prefix is reserved and cannot be used for top-level subdir().')
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
        self.evaluate_codeblock(codeblock)
        self.subdir = prev_subdir

    def _get_kwarg_install_mode(self, kwargs):
        if 'install_mode' not in kwargs:
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
        data = DataHolder(build.Data(sources, install_dir, install_mode))
        self.build.data.append(data.held_object)
        return data

    @stringArgs
    def func_install_subdir(self, node, args, kwargs):
        if len(args) != 1:
            raise InvalidArguments('Install_subdir requires exactly one argument.')
        if 'install_dir' not in kwargs:
            raise InvalidArguments('Missing keyword argument install_dir')
        install_dir = kwargs['install_dir']
        if not isinstance(install_dir, str):
            raise InvalidArguments('Keyword argument install_dir not a string.')
        install_mode = self._get_kwarg_install_mode(kwargs)
        idir = InstallDir(self.subdir, args[0], install_dir, install_mode)
        self.build.install_dirs.append(idir)
        return idir

    def func_configure_file(self, node, args, kwargs):
        if len(args) > 0:
            raise InterpreterException("configure_file takes only keyword arguments.")
        if 'output' not in kwargs:
            raise InterpreterException('Required keyword argument "output" not defined.')
        if 'configuration' in kwargs and 'command' in kwargs:
            raise InterpreterException('Must not specify both "configuration" '
                                       'and "command" keyword arguments since '
                                       'they are mutually exclusive.')
        if 'capture' in kwargs:
            if not isinstance(kwargs['capture'], bool):
                raise InterpreterException('"capture" keyword must be a boolean.')
            if 'command' not in kwargs:
                raise InterpreterException('"capture" keyword requires "command" keyword.')

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
                inputfile = os.path.join(self.subdir, inputfile)
                ifile_abs = os.path.join(self.environment.source_dir, inputfile)
            else:
                ifile_abs = inputfile.absolute_path(self.environment.source_dir,
                                                    self.environment.build_dir)
                inputfile = inputfile.relative_name()
        elif 'command' in kwargs and '@INPUT@' in kwargs['command']:
            raise InterpreterException('@INPUT@ used as command argument, but no input file specified.')
        # Validate output
        output = kwargs['output']
        if not isinstance(output, str):
            raise InterpreterException('Output file name must be a string')
        if ifile_abs:
            values = mesonlib.get_filenames_templates_dict([ifile_abs], None)
            outputs = mesonlib.substitute_values([output], values)
            output = outputs[0]
        if os.path.split(output)[0] != '':
            raise InterpreterException('Output file name must not contain a subdirectory.')
        (ofile_path, ofile_fname) = os.path.split(os.path.join(self.subdir, output))
        ofile_abs = os.path.join(self.environment.build_dir, ofile_path, ofile_fname)
        if 'configuration' in kwargs:
            conf = kwargs['configuration']
            if not isinstance(conf, ConfigurationDataHolder):
                raise InterpreterException('Argument "configuration" is not of type configuration_data')
            mlog.log('Configuring', mlog.bold(output), 'using configuration')
            if inputfile is not None:
                # Normalize the path of the conffile to avoid duplicates
                # This is especially important to convert '/' to '\' on Windows
                conffile = os.path.normpath(inputfile)
                if conffile not in self.build_def_files:
                    self.build_def_files.append(conffile)
                os.makedirs(os.path.join(self.environment.build_dir, self.subdir), exist_ok=True)
                mesonlib.do_conf_file(ifile_abs, ofile_abs, conf.held_object)
            else:
                mesonlib.dump_conf_header(ofile_abs, conf.held_object)
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
            res = self.func_run_command(node, cmd, {'in_builddir': True})
            if res.returncode != 0:
                raise InterpreterException('Running configure command failed.\n%s\n%s' %
                                           (res.stdout, res.stderr))
            if 'capture' in kwargs and kwargs['capture']:
                dst_tmp = ofile_abs + '~'
                with open(dst_tmp, 'w', encoding='utf-8') as f:
                    f.writelines(res.stdout)
                if ifile_abs:
                    shutil.copymode(ifile_abs, dst_tmp)
                mesonlib.replace_if_different(ofile_abs, dst_tmp)
        else:
            raise InterpreterException('Configure_file must have either "configuration" or "command".')
        idir = kwargs.get('install_dir', None)
        if isinstance(idir, str):
            cfile = mesonlib.File.from_built_file(ofile_path, ofile_fname)
            self.build.data.append(build.Data([cfile], idir))
        return mesonlib.File.from_built_file(self.subdir, output)

    @stringArgs
    def func_include_directories(self, node, args, kwargs):
        src_root = self.environment.get_source_dir()
        build_root = self.environment.get_build_dir()
        absbase_src = os.path.join(src_root, self.subdir)
        absbase_build = os.path.join(build_root, self.subdir)

        for a in args:
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
        is_system = kwargs.get('is_system', False)
        if not isinstance(is_system, bool):
            raise InvalidArguments('Is_system must be boolean.')
        i = IncludeDirsHolder(build.IncludeDirs(self.subdir, args, is_system))
        return i

    @stringArgs
    def func_add_test_setup(self, node, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Add_test_setup needs one argument for the setup name.')
        setup_name = args[0]
        if re.fullmatch('[_a-zA-Z][_0-9a-zA-Z]*', setup_name) is None:
            raise InterpreterException('Setup name may only contain alphanumeric characters.')
        try:
            inp = kwargs.get('exe_wrapper', [])
            if not isinstance(inp, list):
                inp = [inp]
            exe_wrapper = []
            for i in inp:
                if hasattr(i, 'held_object'):
                    i = i.held_object
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
        setupobj = build.TestSetup(exe_wrapper=exe_wrapper,
                                   gdb=gdb,
                                   timeout_multiplier=timeout_multiplier,
                                   env=env)
        if self.subproject == '':
            # Dunno what we should do with subprojects really. Let's start simple
            # and just use the master project ones.
            self.build.test_setups[setup_name] = setupobj

    @stringArgs
    def func_add_global_arguments(self, node, args, kwargs):
        self.add_global_arguments(node, self.build.global_args, args, kwargs)

    @stringArgs
    def func_add_global_link_arguments(self, node, args, kwargs):
        self.add_global_arguments(node, self.build.global_link_args, args, kwargs)

    @stringArgs
    def func_add_project_arguments(self, node, args, kwargs):
        self.add_project_arguments(node, self.build.projects_args, args, kwargs)

    @stringArgs
    def func_add_project_link_arguments(self, node, args, kwargs):
        self.add_project_arguments(node, self.build.projects_link_args, args, kwargs)

    def add_global_arguments(self, node, argsdict, args, kwargs):
        if self.subproject != '':
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

    def func_environment(self, node, args, kwargs):
        return EnvironmentVariablesHolder()

    @stringArgs
    @noKwargs
    def func_join_paths(self, node, args, kwargs):
        return os.path.join(*args).replace('\\', '/')

    def run(self):
        super().run()
        mlog.log('Build targets in project:', mlog.bold(str(len(self.build.targets))))

    def source_strings_to_files(self, sources):
        results = []
        for s in sources:
            if isinstance(s, (mesonlib.File, GeneratedListHolder,
                              CustomTargetHolder)):
                pass
            elif isinstance(s, str):
                s = mesonlib.File.from_source_file(self.environment.source_dir, self.subdir, s)
            else:
                raise InterpreterException("Source item is not string or File-type object.")
            results.append(s)
        return results

    def add_target(self, name, tobj):
        if name == '':
            raise InterpreterException('Target name must not be empty.')
        if name in coredata.forbidden_target_names:
            raise InvalidArguments('Target name "%s" is reserved for Meson\'s internal use. Please rename.'
                                   % name)
        # To permit an executable and a shared library to have the
        # same name, such as "foo.exe" and "libfoo.a".
        idname = tobj.get_id()
        if idname in self.build.targets:
            raise InvalidCode('Tried to create target "%s", but a target of that name already exists.' % name)
        self.build.targets[idname] = tobj
        if idname not in self.coredata.target_guids:
            self.coredata.target_guids[idname] = str(uuid.uuid4()).upper()

    def build_target(self, node, args, kwargs, targetholder):
        if not args:
            raise InterpreterException('Target does not have a name.')
        name = args[0]
        sources = args[1:]
        if self.environment.is_cross_build():
            if kwargs.get('native', False):
                is_cross = False
            else:
                is_cross = True
        else:
            is_cross = False
        try:
            kw_src = self.flatten(kwargs['sources'])
            if not isinstance(kw_src, list):
                kw_src = [kw_src]
        except KeyError:
            kw_src = []
        sources += kw_src
        sources = self.source_strings_to_files(sources)
        objs = self.flatten(kwargs.get('objects', []))
        kwargs['dependencies'] = self.flatten(kwargs.get('dependencies', []))
        if 'extra_files' in kwargs:
            ef = kwargs['extra_files']
            if not isinstance(ef, list):
                ef = [ef]
            kwargs['extra_files'] = self.source_strings_to_files(ef)
        if not isinstance(objs, list):
            objs = [objs]
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
        target = targetclass(name, self.subdir, self.subproject, is_cross, sources, objs, self.environment, kwargs)
        if is_cross:
            self.add_cross_stdlib_info(target)
        l = targetholder(target, self)
        self.add_target(name, l.held_object)
        self.project_args_frozen = True
        return l

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
        for (i, arg) in enumerate(args):
            arg = self.evaluate_statement(arg)
            if isinstance(arg, bool): # Python boolean is upper case.
                arg = str(arg).lower()
            templ = templ.replace('@{}@'.format(i), str(arg))
        return templ

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
            try:
                if element == item:
                    return True
            except Exception:
                pass
        return False

    def is_subproject(self):
        return self.subproject != ''
