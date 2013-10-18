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
import nodes
import environment
import coredata
import dependencies
import mlog
import build
import os, sys, platform, subprocess, shutil

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

    def __init__(self, command_array, curdir):
        super().__init__()
        pc = self.run_command(command_array, curdir)
        (stdout, stderr) = pc.communicate()
        self.returncode = pc.returncode
        self.stdout = stdout.decode()
        self.stderr = stderr.decode()
        self.methods.update({'returncode' : self.returncode_method,
                             'stdout' : self.stdout_method,
                             'stderr' : self.stderr_method,
                             })
        
    def run_command(self, command_array, curdir):
        cmd_name = command_array[0]
        try:
            return subprocess.Popen(command_array, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except FileNotFoundError:
            pass
        # Was not a command, is a program in path?
        exe = shutil.which(cmd_name)
        if exe is not None:
            command_array = [exe] + command_array[1:]
            return subprocess.Popen(command_array, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # No? Maybe it is a script in the source tree.
        fullpath = os.path.join(curdir, cmd_name)
        command_array = [fullpath] + command_array[1:]
        try:
            return subprocess.Popen(command_array, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
        self.methods.update({'pointer_size' : self.get_ptrsize_method,
                             'name' : self.get_name_method,
                             'is_big_endian' : self.is_big_endian_method,
                             })
    # Is this needed any more since we have proper compiler
    # based tests? Consider removing it.
    def get_ptrsize_method(self, args, kwargs):
        if sys.maxsize > 2**32:
            return 64
        return 32

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

    def set_subdir(self, subdir):
        self.subdir = subdir

    def get_subdir(self):
        return self.subdir
    
    def get_sources(self):
        return self.sources

class Data(InterpreterObject):
    
    def __init__(self, subdir, sources, kwargs):
        InterpreterObject.__init__(self)
        self.subdir = subdir
        self.sources = sources
        kwsource = kwargs.get('sources', [])
        if not isinstance(kwsource, list):
            kwsource = [kwsource]
        self.sources += kwsource

    def get_subdir(self):
        return self.subdir

    def get_sources(self):
        return self.sources

class Man(InterpreterObject):

    def __init__(self, sources, kwargs):
        InterpreterObject.__init__(self)
        self.sources = sources
        self.validate_sources()
        if len(kwargs) > 0:
            raise InvalidArguments('Man function takes no keyword arguments.')
        
    def validate_sources(self):
        for s in self.sources:
            num = int(s.split('.')[-1])
            if num < 1 or num > 8:
                raise InvalidArguments('Man file must have a file extension of a number between 1 and 8')

    def get_sources(self):
        return self.sources

class BuildTargetHolder(InterpreterObject):
    def __init__(self, targetttype, name, subdir, is_cross, sources, environment, kwargs):
        self.target = targetttype(name, subdir, is_cross, sources, environment, kwargs)
    
    def is_cross(self):
        return self.target.is_cross()

class ExecutableHolder(BuildTargetHolder):
    def __init__(self, name, subdir, is_cross, sources, environment, kwargs):
        super().__init__(build.Executable, name, subdir, is_cross, sources, environment, kwargs)

class StaticLibraryHolder(BuildTargetHolder):
    def __init__(self, name, subdir, is_cross, sources, environment, kwargs):
        super().__init__(build.StaticLibrary, name, subdir, is_cross, sources, environment, kwargs)

class SharedLibraryHolder(BuildTargetHolder):
    def __init__(self, name, subdir, is_cross, sources, environment, kwargs):
        super().__init__(build.SharedLibrary, name, subdir, is_cross, sources, environment, kwargs)

class Test(InterpreterObject):
    def __init__(self, name, exe, is_parallel):
        InterpreterObject.__init__(self)
        self.name = name
        self.exe = exe
        self.is_parallel = is_parallel
        
    def get_exe(self):
        return self.exe
    
    def get_name(self):
        return self.name

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
        if isinstance(code, nodes.StringStatement):
            code = code.get_value()
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
        if isinstance(string, nodes.StringStatement):
            string = string.value
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
        if isinstance(string, nodes.StringStatement):
            string = string.value
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
    def __init__(self, build):
        InterpreterObject.__init__(self)
        self.build = build
        self.methods.update({'get_compiler': self.get_compiler_method,
                             'is_cross_build' : self.is_cross_build_method,
                             'has_exe_wrapper' : self.has_exe_wrapper_method,
                             })

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

class Interpreter():

    def __init__(self, build):
        self.build = build
        code = open(os.path.join(build.environment.get_source_dir(),\
                                 environment.build_filename)).read()
        if len(code.strip()) == 0:
            raise InvalidCode('Builder file is empty.')
        assert(isinstance(code, str))
        try:
            self.ast = mparser.build_ast(code)
        except coredata.MesonException as me:
            me.file = environment.build_filename
            raise me
        self.sanity_check_ast()
        self.variables = {}
        self.builtin = {}
        self.builtin['build'] = Build()
        self.builtin['host'] = Host(build.environment)
        self.builtin['meson'] = MesonMain(build)
        self.environment = build.environment
        self.build_func_dict()
        self.build_def_files = [environment.build_filename]
        self.coredata = self.environment.get_coredata()
        self.subdir = ''
        self.generators = []
        self.visited_subdirs = {}

    def build_func_dict(self):
        self.funcs = {'project' : self.func_project, 
                      'message' : self.func_message,
                      'error' : self.func_error,
                      'executable': self.func_executable,
                      'dependency' : self.func_dependency,
                      'static_library' : self.func_static_lib,
                      'shared_library' : self.func_shared_lib,
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
                      }

    def get_build_def_files(self):
        return self.build_def_files

    def get_variables(self):
        return self.variables

    def sanity_check_ast(self):
        if not isinstance(self.ast, nodes.CodeBlock):
            raise InvalidCode('AST is of invalid type. Possibly a bug in the parser.')
        if len(self.ast.get_statements()) == 0:
            raise InvalidCode('No statements in code.')
        first = self.ast.get_statements()[0]
        if not isinstance(first, nodes.FunctionCall) or first.get_function_name() != 'project':
            raise InvalidCode('First statement must be a call to project')

    def run(self):
        self.evaluate_codeblock(self.ast)

    def evaluate_codeblock(self, node):
        if node is None:
            return
        if not isinstance(node, nodes.CodeBlock):
            e = InvalidCode('Tried to execute a non-codeblock. Possibly a bug in the parser.')
            e.lineno = node.lineno()
            raise e
        statements = node.get_statements()
        i = 0
        while i < len(statements):
            cur = statements[i]
            try:
                self.evaluate_statement(cur)
            except Exception as e:
                e.lineno = cur.lineno()
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
        if isinstance(cur, nodes.FunctionCall):
            return self.function_call(cur)
        elif isinstance(cur, nodes.Assignment):
            return self.assignment(cur)
        elif isinstance(cur, nodes.MethodCall):
            return self.method_call(cur)
        elif isinstance(cur, nodes.StringStatement):
            return cur
        elif isinstance(cur, nodes.BoolStatement):
            return cur
        elif isinstance(cur, nodes.IfStatement):
            return self.evaluate_if(cur)
        elif isinstance(cur, nodes.AtomStatement):
            return self.get_variable(cur.get_value())
        elif isinstance(cur, nodes.Comparison):
            return self.evaluate_comparison(cur)
        elif isinstance(cur, nodes.ArrayStatement):
            return self.evaluate_arraystatement(cur)
        elif isinstance(cur, nodes.IntStatement):
            return cur
        elif isinstance(cur, nodes.AndStatement):
            return self.evaluate_andstatement(cur)
        elif isinstance(cur, nodes.OrStatement):
            return self.evaluate_orstatement(cur)
        elif isinstance(cur, nodes.NotStatement):
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
        for i in args:
            if not isinstance(i, str):
                raise InterpreterObject('Run_command arguments must be strings.')
        return RunProcess(args, os.path.join(self.environment.source_dir, self.subdir))

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
            raise InterpreterException('More than one gettext definitions currently not supported.')
        self.build.pot.append((packagename, languages, self.subdir))

    def func_option(self, nodes, args, kwargs):
        raise InterpreterException('Tried to call option() in build description file. All options must be in the option file.')

    def func_get_option(self, nodes, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Argument required for get_option.')
        optname = args[0]
        if not isinstance(optname, str):
            raise InterpreterException('Argument of get_option must be a string.')
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
        if self.build.project is not None:
            raise InvalidCode('Second call to project().')
        self.build.project = args[0]
        mlog.log('Project name is "', mlog.bold(self.build.project), '".', sep='')
        self.add_languages(node, args[1:])

    def func_message(self, node, args, kwargs):
        self.validate_arguments(args, 1, [str])
        mlog.log(mlog.bold('Message:'), args[0])

    def func_error(self, node, args, kwargs):
        self.validate_arguments(args, 1, [str])
        raise InterpreterException('Error encountered: ' + args[0])

    def add_languages(self, node, args):
        is_cross = self.environment.is_cross_build()
        for lang in args:
            if lang in self.coredata.compilers:
                comp = self.coredata.compilers[lang]
                cross_comp = self.coredata.cross_compilers.get(lang, None)
            else:
                cross_comp = None
                if lang.lower() == 'c':
                    comp = self.environment.detect_c_compiler(False)
                    if is_cross:
                        cross_comp = self.environment.detect_c_compiler(True)
                elif lang.lower() == 'cpp':
                    comp = self.environment.detect_cpp_compiler(False)
                    if is_cross:
                        cross_comp = self.environment.detect_cpp_compiler(True)
                elif lang.lower() == 'objc':
                    comp = self.environment.detect_objc_compiler(False)
                    if is_cross:
                        cross_comp = self.environment.detect_objc_compiler(True)
                elif lang.lower() == 'objcpp':
                    comp = self.environment.detect_objcpp_compiler(False)
                    if is_cross:
                        cross_comp = self.environment.detect_objcpp_compiler(True)
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
        extprog = dependencies.ExternalProgram(exename)
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

    def func_generator(self, node, args, kwargs):
        gen = GeneratorHolder(args, kwargs)
        self.generators.append(gen)
        return gen

    def func_test(self, node, args, kwargs):
        self.validate_arguments(args, 2, [str, ExecutableHolder])
        par = kwargs.get('is_parallel', True)
        if not isinstance(par, bool):
            raise InterpreterException('Keyword argument is_parallel must be a boolean.')
        t = Test(args[0], args[1].target, par)
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
            codeblock = mparser.build_ast(code)
        except coredata.MesonException as me:
            me.file = buildfilename
            raise me
        mlog.log('Going to subdirectory "%s".' % self.subdir)
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
        if not 'configuration' in kwargs:
            raise InterpreterException('Required keyword argument "configuration" not defined.')
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

    def func_include_directories(self, node, args, kwargs):
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('Argument %s is not a string.' % str(a))
        i = IncludeDirsHolder(self.subdir, args, kwargs)
        return i

    def func_add_global_arguments(self, node, args, kwargs):
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('Argument %s is not a string.' % str(a))
        if len(self.build.get_targets()) > 0:
            raise InvalidCode('Global flags can not be set once any build target is defined.')
        if not 'language' in kwargs:
            raise InvalidCode('Missing language definition in add_global_arguments')
        lang = kwargs['language'].lower()
        if lang in self.build.global_args:
            self.build.global_args[lang] += args
        else:
            self.build.global_args[lang] = args

    def flatten(self, args):
        if isinstance(args, nodes.StringStatement):
            return args.get_value()
        if isinstance(args, str):
            return args
        result = []
        for a in args:
            if isinstance(a, list):
                rest = self.flatten(a)
                result = result + rest
            elif isinstance(a, nodes.StringStatement):
                result.append(a.get_value())
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
        if name in self.build.targets:
            raise InvalidCode('Tried to create target "%s", but a target of that name already exists.' % name)
        self.check_sources_exist(os.path.join(self.environment.source_dir, self.subdir), sources)
        l = targetclass(name, self.subdir, is_cross, sources, self.environment, kwargs)
        self.build.targets[name] = l.target
        if self.environment.is_cross_build() and l.is_cross:
            txt = ' cross build '
        else:
            txt = ' build '
        mlog.log('Creating', txt, 'target "', mlog.bold(name), '" with %d files.' % len(sources), sep='')
        return l

    def check_sources_exist(self, subdir, sources):
        for s in sources:
            if not isinstance(s, str):
                continue # This means a generated source and they always exist.
            fname = os.path.join(subdir, s)
            if not os.path.isfile(fname):
                raise InterpreterException('Tried to add non-existing source %s.' % s)

    def function_call(self, node):
        func_name = node.get_function_name()
        (posargs, kwargs) = self.reduce_arguments(node.arguments)
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
        var_name = node.var_name
        if not isinstance(var_name, nodes.AtomExpression):
            raise InvalidArguments('Tried to assign value to a non-variable.')
        var_name = var_name.get_value()
        value = self.evaluate_statement(node.value)
        if value is None:
            raise InvalidCode('Can not assign None to variable.')
        value = self.to_native(value)
        if not self.is_assignable(value):
            raise InvalidCode('Tried to assign an invalid value to variable.')
        self.set_variable(var_name, value)
        return value

    def reduce_single(self, arg):
        if isinstance(arg, nodes.AtomExpression) or isinstance(arg, nodes.AtomStatement):
            return self.get_variable(arg.value)
        elif isinstance(arg, str):
            return arg
        elif isinstance(arg, nodes.StringExpression) or isinstance(arg, nodes.StringStatement):
            return arg.get_value()
        elif isinstance(arg, nodes.FunctionCall):
            return self.function_call(arg)
        elif isinstance(arg, nodes.MethodCall):
            return self.method_call(arg)
        elif isinstance(arg, nodes.BoolStatement) or isinstance(arg, nodes.BoolExpression):
            return arg.get_value()
        elif isinstance(arg, nodes.ArrayStatement):
            return [self.reduce_single(curarg) for curarg in arg.args.arguments]
        elif isinstance(arg, nodes.IntStatement):
            return arg.get_value()
        else:
            raise InvalidCode('Irreducible argument.')

    def reduce_arguments(self, args):
        assert(isinstance(args, nodes.Arguments))
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
        if method_name == 'strip':
            return self.to_native(obj).strip()
        if method_name == 'format':
            return self.format_string(obj, args)
        raise InterpreterException('Unknown method "%s" for a string.' % method_name)

    def to_native(self, arg):
        if isinstance(arg, nodes.StringStatement) or \
           isinstance(arg, nodes.IntStatement) or \
           isinstance(arg, nodes.BoolStatement):
            return arg.get_value()
        return arg

    def format_string(self, templ, args):
        templ = self.to_native(templ)
        if isinstance(args, nodes.Arguments):
            args = args.arguments
        for (i, arg) in enumerate(args):
            arg = self.to_native(self.reduce_single(arg))
            if isinstance(arg, bool): # Python boolean is upper case.
                arg = str(arg).lower()
            templ = templ.replace('@{}@'.format(i), str(arg))
        return templ

    def method_call(self, node):
        invokable = node.invokable
        if isinstance(invokable, nodes.AtomStatement):
            object_name = invokable.get_value()
            obj = self.get_variable(object_name)
        else:
            obj = self.evaluate_statement(invokable)
        method_name = node.method_name.get_value()
        args = node.arguments
        if isinstance(obj, nodes.StringStatement):
            obj = obj.get_value()
        if isinstance(obj, str):
            return self.string_method_call(obj, method_name, args)
        if not isinstance(obj, InterpreterObject):
            raise InvalidArguments('Variable "%s" is not callable.' % object_name)
        (args, kwargs) = self.reduce_arguments(args)
        return obj.method_call(method_name, args, kwargs)
    
    def evaluate_if(self, node):
        result = self.evaluate_statement(node.clause)
        cond = None
        if isinstance(result, nodes.BoolExpression) or \
           isinstance(result, nodes.BoolStatement):
            cond = result.get_value()
        if isinstance(result, bool):
            cond = result
        if cond is not None:
            if cond:
                self.evaluate_codeblock(node.trueblock)
            else:
                block = node.falseblock
                if isinstance(block, nodes.IfStatement):
                    self.evaluate_if(block)
                else:
                    self.evaluate_codeblock(block)
        else:
            raise InvalidCode('If clause does not evaluate to true or false.')

    def is_elementary_type(self, v):
        if isinstance(v, int) or isinstance(v, str) or isinstance(v, bool):
            return True
        return False

    def evaluate_comparison(self, node):
        v1 = self.evaluate_statement(node.get_first())
        v2 = self.evaluate_statement(node.get_second())
        if self.is_elementary_type(v1):
            val1 = v1
        else:
            val1 = v1.get_value()
        if self.is_elementary_type(v2):
            val2 = v2
        else:
            val2 = v2.get_value()
        if type(val1) != type(val2):
            raise InterpreterException('Comparison of different types %s and %s.' %
                                       (str(type(val1)), str(type(val2))))
        if node.get_ctype() == '==':
            return val1 == val2
        elif node.get_ctype() == '!=':
            return val1 != val2
        else:
            raise InvalidCode('You broke me.')

    def evaluate_andstatement(self, cur):
        l = self.evaluate_statement(cur.left)
        if isinstance(l, nodes.BoolStatement):
            l = l.get_value()
        if not isinstance(l, bool):
            raise InterpreterException('First argument to "and" is not a boolean.')
        if not l:
            return False
        r = self.evaluate_statement(cur.right)
        if isinstance(r, nodes.BoolStatement):
            r = r.get_value()
        if not isinstance(r, bool):
            raise InterpreterException('Second argument to "and" is not a boolean.')
        return r

    def evaluate_orstatement(self, cur):
        l = self.evaluate_statement(cur.left)
        if isinstance(l, nodes.BoolStatement):
            l = l.get_value()
        if not isinstance(l, bool):
            raise InterpreterException('First argument to "or" is not a boolean.')
        if l:
            return True
        r = self.evaluate_statement(cur.right)
        if isinstance(r, nodes.BoolStatement):
            r = r.get_value()
        if not isinstance(r, bool):
            raise InterpreterException('Second argument to "or" is not a boolean.')
        return r
    
    def evaluate_notstatement(self, cur):
        v = self.evaluate_statement(cur.val)
        if isinstance(v, nodes.BoolStatement):
            v = v.get_value()
        if not isinstance(v, bool):
            raise InterpreterException('Argument to "not" is not a boolean.')
        return not v

    def evaluate_arraystatement(self, cur):
        (arguments, kwargs) = self.reduce_arguments(cur.get_args())
        if len(kwargs) > 0:
            raise InvalidCode('Keyword arguments are invalid in array construction.')
        return arguments
