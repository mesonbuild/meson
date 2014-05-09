# Copyright 2012 Jussi Pakkanen

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mparser
import environment
import coredata
import dependencies
import mlog
import build
import optinterpreter
import os, sys, platform, subprocess, shutil, uuid

class InterpreterException(coredata.MesonException):
    pass

class InvalidCode(InterpreterException):
    pass

class InvalidArguments(InterpreterException):
    pass

class InterpreterObject():
    def __init__(self):
        self.methods = {}

    def method_call(self, method_name, args, kwargs):
        if method_name in self.methods:
            return self.methods[method_name](args, kwargs)
        raise InvalidCode('Unknown method "%s" in object.' % method_name)

class TryRunResultHolder(InterpreterObject):
    def __init__(self, res):
        super().__init__()
        self.res = res
        self.methods.update({'returncode' : self.returncode_method,
                             'compiled' : self.compiled_method,
                             'stdout' : self.stdout_method,
                             'stderr' : self.stderr_method,
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

    def __init__(self, command_array, source_dir, build_dir, subdir):
        super().__init__()
        pc = self.run_command(command_array, source_dir, build_dir, subdir)
        (stdout, stderr) = pc.communicate()
        self.returncode = pc.returncode
        self.stdout = stdout.decode().replace('\r\n', '\n')
        self.stderr = stderr.decode().replace('\r\n', '\n')
        self.methods.update({'returncode' : self.returncode_method,
                             'stdout' : self.stdout_method,
                             'stderr' : self.stderr_method,
                             })
        
    def run_command(self, command_array, source_dir, build_dir, subdir):
        cmd_name = command_array[0]
        env = {'MESON_SOURCE_ROOT' : source_dir,
               'MESON_BUILD_ROOT' : build_dir,
               'MESON_SUBDIR' : subdir}
        cwd = os.path.join(source_dir, subdir)
        child_env = os.environ.copy()
        child_env.update(env)
        try:
            return subprocess.Popen(command_array, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    env=child_env, cwd=cwd)
        except FileNotFoundError:
            pass
        # Was not a command, is a program in path?
        exe = shutil.which(cmd_name)
        if exe is not None:
            command_array = [exe] + command_array[1:]
            return subprocess.Popen(command_array, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    env=child_env, cwd=cwd)
        # No? Maybe it is a script in the source tree.
        fullpath = os.path.join(source_dir, subdir, cmd_name)
        command_array = [fullpath] + command_array[1:]
        try:
            return subprocess.Popen(command_array, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    env=child_env, cwd=cwd)
        except FileNotFoundError:
            raise InterpreterException('Could not execute command "%s".' % cmd_name)

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

class ConfigurationDataHolder(InterpreterObject):
    def __init__(self):
        super().__init__()
        self.used = False # These objects become immutable after use in configure_file.
        self.held_object = build.ConfigurationData()
        self.methods.update({'set': self.set_method,
                             'set10': self.set10_method,
                             })

    def is_used(self):
        return self.used

    def mark_used(self):
        self.used = True

    def validate_args(self, args):
        if len(args) != 2:
            raise InterpreterException("Configuration set requires 2 arguments.")
        if self.used:
            raise InterpreterException("Can not set values on configuration object that has been used.")
        name = args[0]
        val = args[1]
        if not isinstance(name, str):
            raise InterpreterException("First argument to set must be a string.")
        return (name, val)

    def set_method(self, args, kwargs):
        (name, val) = self.validate_args(args)
        self.held_object.values[name] = val

    def set10_method(self, args, kwargs):
        (name, val) = self.validate_args(args)
        if val:
            self.held_object.values[name] = 1
        else:
            self.held_object.values[name] = 0

    def get(self, name):
        return self.held_object.values[name]

    def keys(self):
        return self.held_object.values.keys()

# Interpreter objects can not be pickled so we must have
# these wrappers.

class ExternalProgramHolder(InterpreterObject):
    def __init__(self, ep):
        InterpreterObject.__init__(self)
        self.ep = ep
        self.methods.update({'found': self.found_method})

    def found_method(self, args, kwargs):
        return self.found()

    def found(self):
        return self.ep.found()

    def get_command(self):
        return self.ep.fullpath

    def get_name(self):
        return self.ep.name

class ExternalLibraryHolder(InterpreterObject):
    def __init__(self, el):
        InterpreterObject.__init__(self)
        self.el = el
        self.methods.update({'found': self.found_method})

    def found(self):
        return self.el.found()

    def found_method(self, args, kwargs):
        return self.found()

    def get_filename(self):
        return self.el.fullpath

    def get_name(self):
        return self.el.name
    
    def get_compile_flags(self):
        return self.el.get_compile_flags()
    
    def get_link_flags(self):
        return self.el.get_link_flags()
    
    def get_exe_flags(self):
        return self.el.get_exe_flags()

class GeneratorHolder(InterpreterObject):
    def __init__(self, args, kwargs):
        super().__init__()
        self.generator = build.Generator(args, kwargs)
        self.methods.update({'process' : self.process_method})

    def process_method(self, args, kwargs):
        if len(kwargs) > 0:
            raise InvalidArguments('Process does not take keyword arguments.')
        if isinstance(args, str):
            args = [args]
        if not isinstance(args, list):
            raise InvalidArguments('Argument to "process" must be a string or a list of strings.')
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('A non-string object in "process" arguments.')
        gl = GeneratedListHolder(self)
        [gl.add_file(a) for a in args]
        return gl

class GeneratedListHolder(InterpreterObject):
    def __init__(self, generator):
        super().__init__()
        self.glist = build.GeneratedList(generator)

    def add_file(self, a):
        self.glist.add_file(a)

class Build(InterpreterObject):
    def __init__(self):
        InterpreterObject.__init__(self)
        self.methods.update({'name' : self.get_name_method,
                             })

    def get_name_method(self, args, kwargs):
        return platform.system().lower()

# This currently returns data for the current environment.
# It should return info for the target host.
class Host(InterpreterObject):
    def __init__(self, envir):
        InterpreterObject.__init__(self)
        self.environment = envir
        self.methods.update({'name' : self.get_name_method,
                             'is_big_endian' : self.is_big_endian_method,
                             })

    def get_name_method(self, args, kwargs):
        if self.environment.is_cross_build():
            return self.environment.cross_info.get('name')
        return platform.system().lower()
    
    def is_big_endian_method(self, args, kwargs):
        return sys.byteorder != 'little'

class IncludeDirsHolder(InterpreterObject):
    def __init__(self, curdir, dirs, kwargs):
        super().__init__()
        self.includedirs = build.IncludeDirs(curdir, dirs, kwargs)

class Headers(InterpreterObject):

    def __init__(self, sources, kwargs):
        InterpreterObject.__init__(self)
        self.sources = sources
        self.subdir = kwargs.get('subdir', '')
        self.custom_install_dir = kwargs.get('install_dir', None)
        if self.custom_install_dir is not None:
            if not isinstance(self.custom_install_dir, str):
                raise InterpreterException('Custom_install_dir must be a string.')

    def set_subdir(self, subdir):
        self.subdir = subdir

    def get_subdir(self):
        return self.subdir
    
    def get_sources(self):
        return self.sources

    def get_custom_install_dir(self):
        return self.custom_install_dir

class Data(InterpreterObject):
    def __init__(self, subdir, sources, kwargs):
        InterpreterObject.__init__(self)
        self.subdir = subdir
        self.sources = sources
        kwsource = kwargs.get('sources', [])
        if not isinstance(kwsource, list):
            kwsource = [kwsource]
        self.sources += kwsource
        self.custom_install_dir = kwargs.get('install_dir', None)
        if self.custom_install_dir is not None and not isinstance(self.custom_install_dir, str):
            raise InterpreterException('Custom_install_dir must be a string.')

    def get_subdir(self):
        return self.subdir

    def get_sources(self):
        return self.sources

    def get_custom_install_dir(self):
        return self.custom_install_dir

class Man(InterpreterObject):

    def __init__(self, sources, kwargs):
        InterpreterObject.__init__(self)
        self.sources = sources
        self.validate_sources()
        if len(kwargs) > 1:
            raise InvalidArguments('Man function takes at most one keyword arguments.')
        self.custom_install_dir = kwargs.get('install_dir', None)
        if self.custom_install_dir is not None and not isinstance(self.custom_install_dir, str):
            raise InterpreterException('Custom_install_dir must be a string.')

    def validate_sources(self):
        for s in self.sources:
            num = int(s.split('.')[-1])
            if num < 1 or num > 8:
                raise InvalidArguments('Man file must have a file extension of a number between 1 and 8')

    def get_custom_install_dir(self):
        return self.custom_install_dir

    def get_sources(self):
        return self.sources

class GeneratedObjectsHolder(InterpreterObject):
    def __init__(self, held_object):
        super().__init__()
        self.held_object = held_object

class BuildTargetHolder(InterpreterObject):
    def __init__(self, targetttype, name, subdir, is_cross, sources, objects, environment, kwargs):
        super().__init__()
        self.held_object = targetttype(name, subdir, is_cross, sources, objects, environment, kwargs)
        self.methods.update({'extract_objects' : self.extract_objects_method})

    def is_cross(self):
        return self.held_object.is_cross()

    def extract_objects_method(self, args, kwargs):
        gobjs = self.held_object.extract_objects(args)
        return GeneratedObjectsHolder(gobjs)

class ExecutableHolder(BuildTargetHolder):
    def __init__(self, name, subdir, is_cross, sources, objects, environment, kwargs):
        super().__init__(build.Executable, name, subdir, is_cross, sources, objects, environment, kwargs)

class StaticLibraryHolder(BuildTargetHolder):
    def __init__(self, name, subdir, is_cross, sources, objects, environment, kwargs):
        super().__init__(build.StaticLibrary, name, subdir, is_cross, sources, objects, environment, kwargs)

class SharedLibraryHolder(BuildTargetHolder):
    def __init__(self, name, subdir, is_cross, sources, objects, environment, kwargs):
        super().__init__(build.SharedLibrary, name, subdir, is_cross, sources, objects, environment, kwargs)

class JarHolder(BuildTargetHolder):
    def __init__(self, name, subdir, is_cross, sources, objects, environment, kwargs):
        super().__init__(build.Jar, name, subdir, is_cross, sources, objects, environment, kwargs)

class Test(InterpreterObject):
    def __init__(self, name, exe, is_parallel, cmd_args, env):
        InterpreterObject.__init__(self)
        self.name = name
        self.exe = exe
        self.is_parallel = is_parallel
        self.cmd_args = cmd_args
        self.env = env
        
    def get_exe(self):
        return self.exe
    
    def get_name(self):
        return self.name

class SubprojectHolder(InterpreterObject):

    def __init__(self, subinterpreter):
        super().__init__()
        self.subinterpreter = subinterpreter
        self.methods.update({
                             'get_variable' : self.get_variable_method,
                             })

    def get_variable_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Get_variable takes one argument.')
        varname = args[0]
        if not isinstance(varname, str):
            raise InterpreterException('Get_variable takes a string argument.')
        return self.subinterpreter.variables[varname]

class CompilerHolder(InterpreterObject):
    def __init__(self, compiler, env):
        InterpreterObject.__init__(self)
        self.compiler = compiler
        self.environment = env
        self.methods.update({'compiles': self.compiles_method,
                             'get_id': self.get_id_method,
                             'sizeof': self.sizeof_method,
                             'has_header': self.has_header_method,
                             'run' : self.run_method,
                             'has_function' : self.has_function_method,
                             'has_member' : self.has_member_method,
                             'alignment' : self.alignment_method,
                             'version' : self.version_method
                             })

    def version_method(self, args, kwargs):
        return self.compiler.version

    def alignment_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Alignment method takes exactly one positional argument.')
        typename = args[0]
        if not isinstance(typename, str):
            raise InterpreterException('First argument is not a string.')
        result = self.compiler.alignment(typename, self.environment)
        mlog.log('Checking for alignment of "', mlog.bold(typename), '": ', result, sep='')
        return result

    def run_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Run method takes exactly one positional argument.')
        code = args[0]
        testname = kwargs.get('name', '')
        if not isinstance(testname, str):
            raise InterpreterException('Testname argument must be a string.')
        if not isinstance(code, str):
            raise InterpreterException('First argument is not a string.')
        result = self.compiler.run(code)
        if len(testname) > 0:
            if not result.compiled:
                h = mlog.red('DID NOT COMPILE')
            elif result.returncode == 0:
                h = mlog.green('YES')
            else:
                h = mlog.red('NO (%d)' % result.returncode)
            mlog.log('Checking if "', mlog.bold(testname), '" runs : ', h, sep='')
        return TryRunResultHolder(result)

    def get_id_method(self, args, kwargs):
        return self.compiler.get_id()

    def has_member_method(self, args, kwargs):
        if len(args) != 2:
            raise InterpreterException('Has_member takes exactly two arguments.')
        typename = args[0]
        if not isinstance(typename, str):
            raise InterpreterException('Name of type must be a string.')
        membername = args[1]
        if not isinstance(membername, str):
            raise InterpreterException('Name of member must be a string.')
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of has_function must be a string.')
        had = self.compiler.has_member(typename, membername, prefix)
        if had:
            hadtxt = mlog.green('YES')
        else:
            hadtxt = mlog.red('NO')
        mlog.log('Checking whether type "', mlog.bold(typename), 
                 '" has member "', mlog.bold(membername), '": ', hadtxt, sep='')
        return had

    def has_function_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Has_function takes exactly one argument.')
        funcname = args[0]
        if not isinstance(funcname, str):
            raise InterpreterException('Argument to has_function must be a string.')
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of has_function must be a string.')
        had = self.compiler.has_function(funcname, prefix, self.environment)
        if had:
            hadtxt = mlog.green('YES')
        else:
            hadtxt = mlog.red('NO')
        mlog.log('Checking for function "', mlog.bold(funcname), '": ', hadtxt, sep='')
        return had

    def sizeof_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Sizeof takes exactly one argument.')
        element = args[0]
        if not isinstance(element, str):
            raise InterpreterException('Argument to sizeof must be a string.')
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of sizeof must be a string.')
        esize = self.compiler.sizeof(element, prefix, self.environment)
        mlog.log('Checking for size of "%s": %d' % (element, esize))
        return esize

    def compiles_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('compiles method takes exactly one argument.')
        string = args[0]
        testname = kwargs.get('name', '')
        if not isinstance(testname, str):
            raise InterpreterException('Testname argument must be a string.')
        if not isinstance(string, str):
            raise InterpreterException('Argument to compiles() must be a string')
        result = self.compiler.compiles(string)
        if len(testname) > 0:
            if result:
                h = mlog.green('YES')
            else:
                h = mlog.red('NO')
            mlog.log('Checking if "', mlog.bold(testname), '" compiles : ', h, sep='')
        return result

    def has_header_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('has_header method takes exactly one argument.')
        string = args[0]
        if not isinstance(string, str):
            raise InterpreterException('Argument to has_header() must be a string')
        haz = self.compiler.has_header(string)
        if haz:
            h = mlog.green('YES')
        else:
            h = mlog.red('NO')
        mlog.log('Has header "%s":' % string, h)
        return haz

class MesonMain(InterpreterObject):
    def __init__(self, build, interpreter):
        InterpreterObject.__init__(self)
        self.build = build
        self.interpreter = interpreter
        self.methods.update({'get_compiler': self.get_compiler_method,
                             'is_cross_build' : self.is_cross_build_method,
                             'has_exe_wrapper' : self.has_exe_wrapper_method,
                             'is_unity' : self.is_unity_method,
                             'current_source_dir' : self.current_source_dir_method,
                             'current_build_dir' : self.current_build_dir_method,
                             })

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

    def has_exe_wrapper_method(self, args, kwargs):
        if self.is_cross_build_method(None, None):
            return 'exe_wrap' in  self.build.environment.cross_info
        return True # This is semantically confusing.

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
        for c in clist:
            if c.get_language() == cname:
                return CompilerHolder(c, self.build.environment)
        raise InterpreterException('Tried to access compiler for unspecified language "%s".' % cname)

    def is_unity_method(self, args, kwargs):
        return self.build.environment.coredata.unity

class Interpreter():

    def __init__(self, build, subproject='', subdir=''):
        self.build = build
        self.subproject = subproject
        self.subdir = subdir
        self.source_root = build.environment.get_source_dir()
        option_file = os.path.join(self.source_root, self.subdir, 'meson_options.txt')
        if os.path.exists(option_file):
            oi = optinterpreter.OptionInterpreter(self.subproject)
            oi.process(option_file)
            self.build.environment.merge_options(oi.options)
        mesonfile = os.path.join(self.source_root, self.subdir, environment.build_filename)
        if not os.path.isfile(mesonfile):
            raise InvalidArguments('Missing Meson file in %s' % mesonfile)
        code = open(mesonfile).read()
        if len(code.strip()) == 0:
            raise InvalidCode('Builder file is empty.')
        assert(isinstance(code, str))
        try:
            self.ast = mparser.Parser(code).parse()
        except coredata.MesonException as me:
            me.file = environment.build_filename
            raise me
        self.sanity_check_ast()
        self.variables = {}
        self.builtin = {}
        self.builtin['build'] = Build()
        self.builtin['host'] = Host(build.environment)
        self.builtin['meson'] = MesonMain(build, self)
        self.environment = build.environment
        self.build_func_dict()
        self.build_def_files = [os.path.join(self.subdir, environment.build_filename)]
        self.coredata = self.environment.get_coredata()
        self.generators = []
        self.visited_subdirs = {}
        self.global_flags_frozen = False
        self.subprojects = {}
        self.subproject_stack = []

    def build_func_dict(self):
        self.funcs = {'project' : self.func_project, 
                      'message' : self.func_message,
                      'error' : self.func_error,
                      'executable': self.func_executable,
                      'dependency' : self.func_dependency,
                      'static_library' : self.func_static_lib,
                      'shared_library' : self.func_shared_lib,
                      'jar' : self.func_jar,
                      'generator' : self.func_generator,
                      'test' : self.func_test,
                      'headers' : self.func_headers,
                      'man' : self.func_man,
                      'subdir' : self.func_subdir,
                      'data' : self.func_data,
                      'configure_file' : self.func_configure_file,
                      'include_directories' : self.func_include_directories,
                      'add_global_arguments' : self.func_add_global_arguments,
                      'find_program' : self.func_find_program,
                      'find_library' : self.func_find_library,
                      'configuration_data' : self.func_configuration_data,
                      'run_command' : self.func_run_command,
                      'gettext' : self.func_gettext,
                      'option' : self.func_option,
                      'get_option' : self.func_get_option,
                      'subproject' : self.func_subproject,
                      'is_subproject' : self.func_is_subproject,
                      'pkgconfig_gen' : self.func_pkgconfig_gen,
                      }

    def get_build_def_files(self):
        return self.build_def_files

    def get_variables(self):
        return self.variables

    def sanity_check_ast(self):
        if not isinstance(self.ast, mparser.CodeBlockNode):
            raise InvalidCode('AST is of invalid type. Possibly a bug in the parser.')
        if len(self.ast.lines) == 0:
            raise InvalidCode('No statements in code.')
        first = self.ast.lines[0]
        if not isinstance(first, mparser.FunctionNode) or first.func_name != 'project':
            raise InvalidCode('First statement must be a call to project')

    def run(self):
        self.evaluate_codeblock(self.ast)

    def evaluate_codeblock(self, node):
        if node is None:
            return
        if not isinstance(node, mparser.CodeBlockNode):
            e = InvalidCode('Tried to execute a non-codeblock. Possibly a bug in the parser.')
            e.lineno = node.lineno
            e.colno = node.colno
            raise e
        statements = node.lines
        i = 0
        while i < len(statements):
            cur = statements[i]
            try:
                self.evaluate_statement(cur)
            except Exception as e:
                e.lineno = cur.lineno
                e.colno = cur.colno
                e.file = os.path.join(self.subdir, 'meson.build')
                raise e
            i += 1 # In THE FUTURE jump over blocks and stuff.

    def get_variable(self, varname):
        if varname in self.builtin:
            return self.builtin[varname]
        if varname in self.variables:
            return self.variables[varname]
        raise InvalidCode('Unknown variable "%s".' % varname)

    def set_variable(self, varname, variable):
        if varname in self.builtin:
            raise InvalidCode('Tried to overwrite internal variable "%s"' % varname)
        self.variables[varname] = variable

    def evaluate_statement(self, cur):
        if isinstance(cur, mparser.FunctionNode):
            return self.function_call(cur)
        elif isinstance(cur, mparser.AssignmentNode):
            return self.assignment(cur)
        elif isinstance(cur, mparser.MethodNode):
            return self.method_call(cur)
        elif isinstance(cur, mparser.StringNode):
            return cur.value
        elif isinstance(cur, mparser.BooleanNode):
            return cur.value
        elif isinstance(cur, mparser.IfClauseNode):
            return self.evaluate_if(cur)
        elif isinstance(cur, mparser.IdNode):
            return self.get_variable(cur.value)
        elif isinstance(cur, mparser.ComparisonNode):
            return self.evaluate_comparison(cur)
        elif isinstance(cur, mparser.ArrayNode):
            return self.evaluate_arraystatement(cur)
        elif isinstance(cur, mparser.NumberNode):
            return cur
        elif isinstance(cur, mparser.AndNode):
            return self.evaluate_andstatement(cur)
        elif isinstance(cur, mparser.OrNode):
            return self.evaluate_orstatement(cur)
        elif isinstance(cur, mparser.NotNode):
            return self.evaluate_notstatement(cur)
        else:
            raise InvalidCode("Unknown statement.")

    def validate_arguments(self, args, argcount, arg_types):
        if argcount is not None:
            if argcount != len(args):
                raise InvalidArguments('Expected %d arguments, got %d',
                                       argcount, len(args))
        for i in range(min(len(args), len(arg_types))):
            wanted = arg_types[i]
            actual = args[i]
            if wanted != None:
                if not isinstance(actual, wanted):
                    raise InvalidArguments('Incorrect argument type.')
                
    def func_run_command(self, node, args, kwargs):
        if len(args) < 1:
            raise InterpreterException('Not enough arguments')
        cmd = args[0]
        cargs = args[1:]
        if isinstance(cmd, ExternalProgramHolder):
            cmd = cmd.get_command()
        elif not isinstance(cmd, str):
            raise InterpreterException('First argument is of incorrect type.')
        for i in cargs:
            if not isinstance(i, str):
                raise InterpreterException('Run_command arguments must be strings.')
        args = [cmd] + cargs
        return RunProcess(args, self.environment.source_dir, self.environment.build_dir, self.subdir)

    def func_gettext(self, nodes, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Gettext requires one positional argument (package name).')
        packagename = args[0]
        if not isinstance(packagename, str):
            raise InterpreterException('Gettext argument is not a string.')
        languages = kwargs.get('languages', None)
        if not isinstance(languages, list):
            raise InterpreterException('Argument languages must be a list of strings.')
        # TODO: check that elements are strings
        if len(self.build.pot) > 0:
            raise InterpreterException('More than one gettext definition currently not supported.')
        self.build.pot.append((packagename, languages, self.subdir))

    def func_option(self, nodes, args, kwargs):
        raise InterpreterException('Tried to call option() in build description file. All options must be in the option file.')

    def func_pkgconfig_gen(self, nodes, args, kwargs):
        if len(args) > 0:
            raise InterpreterException('Pkgconfig_gen takes no positional arguments.')
        libs = kwargs.get('libraries', [])
        if not isinstance(libs, list):
            libs = [libs]
        for l in libs:
            if not (isinstance(l, SharedLibraryHolder) or isinstance(l, StaticLibraryHolder)):
                raise InterpreterException('Library argument not a library object.')
        subdirs = kwargs.get('subdirs', ['.'])
        if not isinstance(subdirs, list):
            subdirs = [subdirs]
        for h in subdirs:
            if not isinstance(h, str):
                raise InterpreterException('Header argument not string.')
        version = kwargs.get('version', '')
        if not isinstance(version, str):
            raise InterpreterException('Version must be a string.')
        name = kwargs.get('name', None)
        if not isinstance(name, str):
            raise InterpreterException('Name not specified.')
        filebase = kwargs.get('filebase', name)
        if not isinstance(filebase, str):
            raise InterpreterException('Filebase must be a string.')
        description = kwargs.get('description', None)
        if not isinstance(description, str):
            raise InterpreterException('Description is not a string.')
        p = build.PkgConfigGenerator(libs, subdirs, name, description, version, filebase)
        self.build.pkgconfig_gens.append(p)

    def func_is_subproject(self, nodes, args, kwargs):
        return self.subproject != ''

    def func_subproject(self, nodes, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Subproject takes exactly one argument')
        dirname = args[0]
        if not isinstance(dirname, str):
            raise InterpreterException('Subproject argument must be a string')
        if self.subdir != '':
            segs = os.path.split(self.subdir)
            if len(segs) != 2 or segs[0] != 'subprojects':
                raise InterpreterException('Subprojects must be defined at the root directory.')
        if dirname in self.subproject_stack:
            fullstack = self.subproject_stack + [dirname]
            incpath = ' => '.join(fullstack)
            raise InterpreterException('Recursive include of subprojects: %s.' % incpath)
        if dirname == self.subprojects:
            return self.subprojects[dirname]
        subdir = os.path.join('subprojects', dirname)
        abs_subdir = os.path.join(self.build.environment.get_source_dir(), subdir)
        if not os.path.isdir(abs_subdir):
            raise InterpreterException('Subproject directory does not exist.')
        self.global_flags_frozen = True
        mlog.log('\nExecuting subproject ', mlog.bold(dirname), '.\n', sep='')
        subi = Interpreter(self.build, dirname, subdir)

        subi.subproject_stack = self.subproject_stack + [dirname]
        subi.run()
        mlog.log('\nSubproject', mlog.bold(dirname), 'finished.')
        self.build.subprojects[dirname] = True
        self.subprojects[dirname] = SubprojectHolder(subi)
        self.build_def_files += subi.build_def_files
        return self.subprojects[dirname]

    def func_get_option(self, nodes, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Argument required for get_option.')
        optname = args[0]
        if not isinstance(optname, str):
            raise InterpreterException('Argument of get_option must be a string.')
        if self.subproject != '':
            optname = self.subproject + '-' + optname
        if optname not in self.environment.coredata.user_options:
            raise InterpreterException('Tried to access unknown option "%s".' % optname)
        return self.environment.coredata.user_options[optname].value

    def func_configuration_data(self, node, args, kwargs):
        if len(args) != 0:
            raise InterpreterException('configuration_data takes no arguments')
        return ConfigurationDataHolder()

    def func_project(self, node, args, kwargs):
        if len(args)< 2:
            raise InvalidArguments('Not enough arguments to project(). Needs at least the project name and one language')
        if len(kwargs) > 0:
            raise InvalidArguments('Project() does not take keyword arguments.')
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('Argument %s is not a string.' % str(a))
        if self.subproject == '':
            self.build.project_name = args[0]
        if self.subproject in self.build.projects:
            raise InvalidCode('Second call to project().')
        self.build.projects[self.subproject] = args[0]
        mlog.log('Project name is "', mlog.bold(args[0]), '".', sep='')
        self.add_languages(node, args[1:])
        langs = self.coredata.compilers.keys()
        if 'vala' in langs:
            if not 'c' in langs:
                raise InterpreterException('Compiling Vala requires a C compiler')
            # These are the implicit dependencies of Vala.
            self.func_dependency(None, ['glib-2.0'], {})
            self.func_dependency(None, ['gobject-2.0'], {})

    def func_message(self, node, args, kwargs):
        self.validate_arguments(args, 1, [str])
        mlog.log(mlog.bold('Message:'), args[0])

    def func_error(self, node, args, kwargs):
        self.validate_arguments(args, 1, [str])
        raise InterpreterException('Error encountered: ' + args[0])

    def add_languages(self, node, args):
        is_cross = self.environment.is_cross_build()
        for lang in args:
            lang = lang.lower()
            if lang in self.coredata.compilers:
                comp = self.coredata.compilers[lang]
                cross_comp = self.coredata.cross_compilers.get(lang, None)
            else:
                cross_comp = None
                if lang == 'c':
                    comp = self.environment.detect_c_compiler(False)
                    if is_cross:
                        cross_comp = self.environment.detect_c_compiler(True)
                elif lang == 'cpp':
                    comp = self.environment.detect_cpp_compiler(False)
                    if is_cross:
                        cross_comp = self.environment.detect_cpp_compiler(True)
                elif lang == 'objc':
                    comp = self.environment.detect_objc_compiler(False)
                    if is_cross:
                        cross_comp = self.environment.detect_objc_compiler(True)
                elif lang == 'objcpp':
                    comp = self.environment.detect_objcpp_compiler(False)
                    if is_cross:
                        cross_comp = self.environment.detect_objcpp_compiler(True)
                elif lang == 'java':
                    comp = self.environment.detect_java_compiler()
                    if is_cross:
                        cross_comp = comp # Java is platform independent.
                elif lang == 'vala':
                    comp = self.environment.detect_vala_compiler()
                    if is_cross:
                        cross_comp = comp # Vala is too (I think).
                else:
                    raise InvalidCode('Tried to use unknown language "%s".' % lang)
                comp.sanity_check(self.environment.get_scratch_dir())
                self.coredata.compilers[lang] = comp
                if cross_comp is not None:
                    self.coredata.cross_compilers[lang] = cross_comp
            mlog.log('Using native %s compiler "' % lang, mlog.bold(' '.join(comp.get_exelist())), '". (%s %s)' % (comp.id, comp.version), sep='')
            self.build.add_compiler(comp)
            if is_cross:
                mlog.log('Using cross %s compiler "' % lang, mlog.bold(' '.join(cross_comp.get_exelist())), '". (%s %s)' % (cross_comp.id, cross_comp.version), sep='')
                self.build.add_cross_compiler(cross_comp)

    def func_find_program(self, node, args, kwargs):
        self.validate_arguments(args, 1, [str])
        required = kwargs.get('required', True)
        if not isinstance(required, bool):
            raise InvalidArguments('"required" argument must be a boolean.')
        exename = args[0]
        if exename in self.coredata.ext_progs and\
           self.coredata.ext_progs[exename].found():
            return ExternalProgramHolder(self.coredata.ext_progs[exename])
        # Search for scripts relative to current subdir.
        search_dir = os.path.join(self.environment.get_source_dir(), self.subdir)
        extprog = dependencies.ExternalProgram(exename, search_dir=search_dir)
        progobj = ExternalProgramHolder(extprog)
        self.coredata.ext_progs[exename] = extprog
        if required and not progobj.found():
            raise InvalidArguments('Program "%s" not found.' % exename)
        return progobj

    def func_find_library(self, node, args, kwargs):
        self.validate_arguments(args, 1, [str])
        required = kwargs.get('required', True)
        if not isinstance(required, bool):
            raise InvalidArguments('"required" argument must be a boolean.')
        libname = args[0]
        if libname in self.coredata.ext_libs and\
           self.coredata.ext_libs[libname].found():
            return ExternalLibraryHolder(self.coredata.ext_libs[libname])
        result = self.environment.find_library(libname)
        extlib = dependencies.ExternalLibrary(libname, result)
        libobj = ExternalLibraryHolder(extlib)
        self.coredata.ext_libs[libname] = extlib
        if required and not libobj.found():
            raise InvalidArguments('External library "%s" not found.' % libname)
        return libobj

    def func_dependency(self, node, args, kwargs):
        self.validate_arguments(args, 1, [str])
        name = args[0]
        identifier = dependencies.get_dep_identifier(name, kwargs)
        if identifier in self.coredata.deps:
            dep = self.coredata.deps[identifier]
        else:
            dep = dependencies.Dependency() # Returns always false for dep.found()
        if not dep.found():
            dep = dependencies.find_external_dependency(name, kwargs)
        self.coredata.deps[identifier] = dep
        return dep

    def func_executable(self, node, args, kwargs):
        return self.build_target(node, args, kwargs, ExecutableHolder)

    def func_static_lib(self, node, args, kwargs):
        return self.build_target(node, args, kwargs, StaticLibraryHolder)

    def func_shared_lib(self, node, args, kwargs):
        return self.build_target(node, args, kwargs, SharedLibraryHolder)

    def func_jar(self, node, args, kwargs):
        return self.build_target(node, args, kwargs, JarHolder)

    def func_generator(self, node, args, kwargs):
        gen = GeneratorHolder(args, kwargs)
        self.generators.append(gen)
        return gen

    def func_test(self, node, args, kwargs):
        if len(args) != 2:
            raise InterpreterException('Incorrect number of arguments')
        if not isinstance(args[0], str):
            raise InterpreterException('First argument of test must be a string.')
        if not isinstance(args[1], ExecutableHolder) and not isinstance(args[1], JarHolder):
            raise InterpreterException('Second argument must be executable.')
        par = kwargs.get('is_parallel', True)
        if not isinstance(par, bool):
            raise InterpreterException('Keyword argument is_parallel must be a boolean.')
        cmd_args = kwargs.get('args', [])
        if not isinstance(cmd_args, list):
            cmd_args = [cmd_args]
        for i in cmd_args:
            if not isinstance(i, str):
                raise InterpreterException('Command line arguments must be strings')
        envlist = kwargs.get('env', [])
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
        t = Test(args[0], args[1].held_object, par, cmd_args, env)
        self.build.tests.append(t)
        mlog.debug('Adding test "', mlog.bold(args[0]), '".', sep='')

    def func_headers(self, node, args, kwargs):
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('Argument %s is not a string.' % str(a))
        h = Headers(args, kwargs)
        self.build.headers.append(h)
        return h
    
    def func_man(self, node, args, kwargs):
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('Argument %s is not a string.' % str(a))
        m = Man(args, kwargs)
        self.build.man.append(m)
        return m
    
    def func_subdir(self, node, args, kwargs):
        if len(kwargs) > 0:
            raise InvalidArguments('subdir command takes no keyword arguments.')
        self.validate_arguments(args, 1, [str])
        if '..' in args[0]:
            raise InvalidArguments('Subdir contains ..')
        if self.subdir == '' and args[0] == 'subprojects':
            raise InvalidArguments('Must not go into subprojects dir with subdir(), use subproject() instead.')
        prev_subdir = self.subdir
        subdir = os.path.join(prev_subdir, args[0])
        if subdir in self.visited_subdirs:
            raise InvalidArguments('Tried to enter directory "%s", which has already been visited.'\
                                   % subdir)
        self.visited_subdirs[subdir] = True
        self.subdir = subdir
        buildfilename = os.path.join(self.subdir, environment.build_filename)
        self.build_def_files.append(buildfilename)
        absname = os.path.join(self.environment.get_source_dir(), buildfilename)
        if not os.path.isfile(absname):
            raise InterpreterException('Nonexistant build def file %s.' % buildfilename)
        code = open(absname).read()
        assert(isinstance(code, str))
        try:
            codeblock = mparser.Parser(code).parse()
        except coredata.MesonException as me:
            me.file = buildfilename
            raise me
        self.evaluate_codeblock(codeblock)
        self.subdir = prev_subdir

    def func_data(self, node, args, kwargs):
        if len(args ) < 1:
            raise InvalidArguments('Data function must have at least one argument: the subdirectory.')
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('Argument %s is not a string.' % str(a))
        data = Data(args[0], args[1:], kwargs)
        self.build.data.append(data)
        return data
    
    def func_configure_file(self, node, args, kwargs):
        if len(args) > 0:
            raise InterpreterException("configure_file takes only keyword arguments.")
        if not 'input' in kwargs:
            raise InterpreterException('Required keyword argument "input" not defined.')
        if not 'output' in kwargs:
            raise InterpreterException('Required keyword argument "output" not defined.')
        if 'configuration' in kwargs:
            inputfile = kwargs['input']
            output = kwargs['output']
            conf = kwargs['configuration']
            if not isinstance(conf, ConfigurationDataHolder):
                raise InterpreterException('Argument "configuration" is not of type configuration_data')

            conffile = os.path.join(self.subdir, inputfile)
            self.build_def_files.append(conffile)
            c = ConfigureFileHolder(self.subdir, inputfile, output, conf.held_object)
            self.build.configure_files.append(c.held_object)
            conf.mark_used()
        elif 'command' in kwargs:
            res = self.func_run_command(node, kwargs['command'], {})
            if res.returncode != 0:
                raise InterpreterException('Running configure command failed.')
        else:
            raise InterpreterException('Configure_file must have either "configuration" or "command".')

    def func_include_directories(self, node, args, kwargs):
        absbase = os.path.join(self.environment.get_source_dir(), self.subdir)
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('Argument %s is not a string.' % str(a))
            absdir = os.path.join(absbase, a)
            if not os.path.isdir(absdir):
                raise InvalidArguments('Include dir %s does not exist.' % a)
        i = IncludeDirsHolder(self.subdir, args, kwargs)
        return i

    def func_add_global_arguments(self, node, args, kwargs):
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('Argument %s is not a string.' % str(a))
        if self.subproject != '':
            raise InvalidCode('Global flags can not be set in subprojects because there is no way to make that reliable.')
        if self.global_flags_frozen:
            raise InvalidCode('Tried to set global flags after they have become immutable.')
        if not 'language' in kwargs:
            raise InvalidCode('Missing language definition in add_global_arguments')
        lang = kwargs['language'].lower()
        if lang in self.build.global_args:
            self.build.global_args[lang] += args
        else:
            self.build.global_args[lang] = args

    def flatten(self, args):
        if isinstance(args, mparser.StringNode):
            return args.value
        if isinstance(args, str):
            return args
        if isinstance(args, InterpreterObject):
            return args
        result = []
        for a in args:
            if isinstance(a, list):
                rest = self.flatten(a)
                result = result + rest
            elif isinstance(a, mparser.StringNode):
                result.append(a.value)
            else:
                result.append(a)
        return result

    def build_target(self, node, args, kwargs, targetclass):
        args = self.flatten(args)
        name = args[0]
        sources = args[1:]
        if self.environment.is_cross_build():
            if kwargs.get('native', False):
                is_cross = False
            else:
                is_cross = True
        else:
            is_cross = False
        if name in coredata.forbidden_target_names:
            raise InvalidArguments('Target name "%s" is reserved for Meson\'s internal use. Please rename.'\
                                   % name)
        try:
            kw_src = self.flatten(kwargs['sources'])
            if not isinstance(kw_src, list):
                kw_src = [kw_src]
        except KeyError:
            kw_src = []
        sources += kw_src
        objs = self.flatten(kwargs.get('objects', []))
        if not isinstance(objs, list):
            objs = [objs]
        if name in self.build.targets:
            raise InvalidCode('Tried to create target "%s", but a target of that name already exists.' % name)
        self.check_sources_exist(os.path.join(self.source_root, self.subdir), sources)
        l = targetclass(name, self.subdir, is_cross, sources, objs, self.environment, kwargs)
        self.build.targets[name] = l.held_object
        if name not in self.coredata.target_guids:
            self.coredata.target_guids[name] = str(uuid.uuid4()).upper()
        if self.environment.is_cross_build() and l.is_cross:
            txt = ' cross build '
        else:
            txt = ' build '
        displayname = os.path.join(l.held_object.subdir, name)
        mlog.log('Creating', txt, 'target ', mlog.bold(displayname), ' with %d files.' % len(sources), sep='')
        self.global_flags_frozen = True
        return l

    def check_sources_exist(self, subdir, sources):
        for s in sources:
            if not isinstance(s, str):
                continue # This means a generated source and they always exist.
            fname = os.path.join(subdir, s)
            if not os.path.isfile(fname):
                raise InterpreterException('Tried to add non-existing source %s.' % s)

    def function_call(self, node):
        func_name = node.func_name
        (posargs, kwargs) = self.reduce_arguments(node.args)
        if func_name in self.funcs:
            return self.funcs[func_name](node, posargs, kwargs)
        else:
            raise InvalidCode('Unknown function "%s".' % func_name)

    def is_assignable(self, value):
        if isinstance(value, InterpreterObject) or \
            isinstance(value, dependencies.Dependency) or\
            isinstance(value, str) or\
            isinstance(value, int) or \
            isinstance(value, list):
            return True
        return False
    
    def assignment(self, node):
        assert(isinstance(node, mparser.AssignmentNode))
        var_name = node.var_name
        if not isinstance(var_name, str):
            raise InvalidArguments('Tried to assign value to a non-variable.')
        value = self.evaluate_statement(node.value)
        if value is None:
            raise InvalidCode('Can not assign None to variable.')
        value = self.to_native(value)
        if not self.is_assignable(value):
            raise InvalidCode('Tried to assign an invalid value to variable.')
        self.set_variable(var_name, value)
        return value

    def reduce_single(self, arg):
        if isinstance(arg, mparser.IdNode):
            return self.get_variable(arg.value)
        elif isinstance(arg, str):
            return arg
        elif isinstance(arg, mparser.StringNode):
            return arg.value
        elif isinstance(arg, mparser.FunctionNode):
            return self.function_call(arg)
        elif isinstance(arg, mparser.MethodNode):
            return self.method_call(arg)
        elif isinstance(arg, mparser.BooleanNode):
            return arg.value
        elif isinstance(arg, mparser.ArrayNode):
            return [self.reduce_single(curarg) for curarg in arg.args.arguments]
        elif isinstance(arg, mparser.NumberNode):
            return arg.value
        else:
            raise InvalidCode('Irreducible argument.')

    def reduce_arguments(self, args):
        assert(isinstance(args, mparser.ArgumentNode))
        if args.incorrect_order():
            raise InvalidArguments('All keyword arguments must be after positional arguments.')
        reduced_pos = [self.reduce_single(arg) for arg in args.arguments]
        reduced_kw = {}
        for key in args.kwargs.keys():
            if not isinstance(key, str):
                raise InvalidArguments('Keyword argument name is not a string.')
            a = args.kwargs[key]
            reduced_kw[key] = self.reduce_single(a)
        return (reduced_pos, reduced_kw)

    def string_method_call(self, obj, method_name, args):
        obj = self.to_native(obj)
        if method_name == 'strip':
            return obj.strip()
        elif method_name == 'format':
            return self.format_string(obj, args)
        elif method_name == 'split':
            (posargs, _) = self.reduce_arguments(args)
            if len(posargs) > 1:
                raise InterpreterException('Split()  must have at most one argument.')
            elif len(posargs) == 1:
                s = posargs[0]
                if not isinstance(s, str):
                    raise InterpreterException('Split() argument must be a string')
                return obj.split(s)
            else:
                return obj.split()
        raise InterpreterException('Unknown method "%s" for a string.' % method_name)

    def to_native(self, arg):
        if isinstance(arg, mparser.StringNode) or \
           isinstance(arg, mparser.NumberNode) or \
           isinstance(arg, mparser.BooleanNode):
            return arg.value
        return arg

    def format_string(self, templ, args):
        templ = self.to_native(templ)
        if isinstance(args, mparser.ArgumentNode):
            args = args.arguments
        for (i, arg) in enumerate(args):
            arg = self.to_native(self.reduce_single(arg))
            if isinstance(arg, bool): # Python boolean is upper case.
                arg = str(arg).lower()
            templ = templ.replace('@{}@'.format(i), str(arg))
        return templ

    def method_call(self, node):
        invokable = node.source_object
        if isinstance(invokable, mparser.IdNode):
            object_name = invokable.value
            obj = self.get_variable(object_name)
        else:
            obj = self.evaluate_statement(invokable)
        method_name = node.name
        if method_name == 'extract_objects' and self.environment.coredata.unity:
            raise InterpreterException('Single object files can not be extracted in Unity builds.')
        args = node.args
        if isinstance(obj, mparser.StringNode):
            obj = obj.get_value()
        if isinstance(obj, str):
            return self.string_method_call(obj, method_name, args)
        if not isinstance(obj, InterpreterObject):
            raise InvalidArguments('Variable "%s" is not callable.' % object_name)
        (args, kwargs) = self.reduce_arguments(args)
        return obj.method_call(method_name, args, kwargs)
    
    def evaluate_if(self, node):
        assert(isinstance(node, mparser.IfClauseNode))
        for i in node.ifs:
            result = self.evaluate_statement(i.condition)
            if not(isinstance(result, bool)):
                raise InvalidCode('If clause does not evaluate to true or false.')
            if result:
                self.evaluate_codeblock(i.block)
                return
        if not isinstance(node.elseblock, mparser.EmptyNode):
            self.evaluate_codeblock(node.elseblock)

    def is_elementary_type(self, v):
        if isinstance(v, int) or isinstance(v, str) or isinstance(v, bool):
            return True
        return False

    def evaluate_comparison(self, node):
        v1 = self.evaluate_statement(node.left)
        v2 = self.evaluate_statement(node.right)
        if self.is_elementary_type(v1):
            val1 = v1
        else:
            val1 = v1.value
        if self.is_elementary_type(v2):
            val2 = v2
        else:
            val2 = v2.value
        if type(val1) != type(val2):
            raise InterpreterException('Comparison of different types %s and %s.' %
                                       (str(type(val1)), str(type(val2))))
        if node.ctype == '==':
            return val1 == val2
        elif node.ctype == '!=':
            return val1 != val2
        else:
            raise InvalidCode('You broke me.')

    def evaluate_andstatement(self, cur):
        l = self.evaluate_statement(cur.left)
        if isinstance(l, mparser.BooleanNode):
            l = l.value
        if not isinstance(l, bool):
            raise InterpreterException('First argument to "and" is not a boolean.')
        if not l:
            return False
        r = self.evaluate_statement(cur.right)
        if isinstance(r, mparser.BooleanNode):
            r = r.value
        if not isinstance(r, bool):
            raise InterpreterException('Second argument to "and" is not a boolean.')
        return r

    def evaluate_orstatement(self, cur):
        l = self.evaluate_statement(cur.left)
        if isinstance(l, mparser.BooleanNode):
            l = l.get_value()
        if not isinstance(l, bool):
            raise InterpreterException('First argument to "or" is not a boolean.')
        if l:
            return True
        r = self.evaluate_statement(cur.right)
        if isinstance(r, mparser.BooleanNode):
            r = r.get_value()
        if not isinstance(r, bool):
            raise InterpreterException('Second argument to "or" is not a boolean.')
        return r
    
    def evaluate_notstatement(self, cur):
        v = self.evaluate_statement(cur.value)
        if isinstance(v, mparser.BooleanNode):
            v = v.value
        if not isinstance(v, bool):
            raise InterpreterException('Argument to "not" is not a boolean.')
        return not v

    def evaluate_arraystatement(self, cur):
        (arguments, kwargs) = self.reduce_arguments(cur.args)
        if len(kwargs) > 0:
            raise InvalidCode('Keyword arguments are invalid in array construction.')
        return arguments
