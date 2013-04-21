#!/usr/bin/python3 -tt

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
import os, sys, platform, copy

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

class Generator(InterpreterObject):

    def __init__(self, args, kwargs):
        InterpreterObject.__init__(self)
        if len(args) != 1:
            raise InvalidArguments('Generator requires one and only one positional argument')
        if not isinstance(args[0], Executable) and \
           not isinstance(args[0], ExternalProgramHolder):
            raise InvalidArguments('First generator argument must be an executable object.')
        self.exe = args[0]
        self.methods.update({'process' : self.process_method})
        self.process_kwargs(kwargs)
    
    def get_exe(self):
        return self.exe

    def process_kwargs(self, kwargs):
        if 'arguments' not in kwargs:
            raise InvalidArguments('Generator must have "arguments" keyword argument.')
        args = kwargs['arguments']
        if isinstance(args, str):
            args = [args]
        if not isinstance(args, list):
            raise InvalidArguments('"Arguments" keyword argument must be a string or a list of strings.')
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('A non-string object in "arguments" keyword argument.')
        self.arglist = args
        
        if 'output_name' not in kwargs:
            raise InvalidArguments('Generator must have "output_name" keyword argument.')
        rule = kwargs['output_name']
        if not isinstance(rule, str):
            raise InvalidArguments('"output_name" keyword argument must be a string.')
        if not '@BASENAME@' in rule and not '@PLAINNAME@' in rule:
            raise InvalidArguments('"output_name" must contain @BASENAME@ or @PLAINNAME@.')
        if '/' in rule:
            raise InvalidArguments('"output_name" must not contain a slash.')
        self.name_rule = rule

    def get_base_outname(self, inname):
        plainname = os.path.split(inname)[1]
        basename = plainname.split('.')[0]
        return self.name_rule.replace('@BASENAME@', basename).replace('@PLAINNAME@', plainname)

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
        gl = GeneratedList(self)
        [gl.add_file(a) for a in args]
        return gl

    def get_arglist(self):
        return self.arglist

class GeneratedList(InterpreterObject):
    def __init__(self, generator):
        InterpreterObject.__init__(self)
        self.generator = generator
        self.infilelist = []
        self.outfilelist = []

    def add_file(self, newfile):
        self.infilelist.append(newfile)
        self.outfilelist.append(self.generator.get_base_outname(newfile))

    def get_infilelist(self):
        return self.infilelist

    def get_outfilelist(self):
        return self.outfilelist

    def get_generator(self):
        return self.generator

# This currently returns data for the current environment.
# It should return info for the target host.
class Host(InterpreterObject):

    def __init__(self):
        InterpreterObject.__init__(self)
        self.methods.update({'pointer_size' : self.get_ptrsize_method,
                             'name' : self.get_name_method,
                             'is_big_endian' : self.is_big_endian_method,
                             })

    def get_ptrsize_method(self, args, kwargs):
        if sys.maxsize > 2**32:
            return 64
        return 32

    def get_name_method(self, args, kwargs):
        return platform.system().lower()
    
    def is_big_endian_method(self, args, kwargs):
        return sys.byteorder != 'little'

class IncludeDirs(InterpreterObject):
    def __init__(self, curdir, dirs, kwargs):
        InterpreterObject.__init__(self)
        self.curdir = curdir
        self.incdirs = dirs
        # Fixme: check that the directories actually exist.
        # Also that they don't contain ".." or somesuch.
        if len(kwargs) > 0:
            raise InvalidCode('Includedirs function does not take keyword arguments.')

    def get_curdir(self):
        return self.curdir

    def get_incdirs(self):
        return self.incdirs

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

class ConfigureFile(InterpreterObject):
    
    def __init__(self, subdir, sourcename, targetname, kwargs):
        InterpreterObject.__init__(self)
        self.subdir = subdir
        self.sourcename = sourcename
        self.targetname = targetname

    def get_sources(self):
        return self.sources
    
    def get_subdir(self):
        return self.subdir

    def get_source_name(self):
        return self.sourcename

    def get_target_name(self):
        return self.targetname

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

class BuildTarget(InterpreterObject):

    def __init__(self, name, subdir, sources, kwargs):
        InterpreterObject.__init__(self)
        self.name = name
        self.subdir = subdir
        self.sources = []
        self.external_deps = []
        self.include_dirs = []
        self.link_targets = []
        self.filename = 'no_name'
        self.need_install = False
        self.pch = []
        self.extra_args = {}
        self.generated = []
        self.process_sourcelist(sources)
        self.process_kwargs(kwargs)
        if len(self.sources) == 0 and len(self.generated) == 0:
            raise InvalidArguments('Build target %s has no sources.' % name)
    
    def process_sourcelist(self, sources):
        if not isinstance(sources, list):
            sources = [sources]
        for s in sources:
            if isinstance(s, str):
                self.sources.append(s)
            elif isinstance(s, GeneratedList):
                self.generated.append(s)
            else:
                raise InvalidArguments('Bad source in target %s.' % self.name)

    def get_original_kwargs(self):
        return self.kwargs

    def process_kwargs(self, kwargs):
        self.kwargs = copy.copy(kwargs)
        kwargs.get('modules', [])
        self.need_install = kwargs.get('install', self.need_install)
        llist = kwargs.get('link_with', [])
        if not isinstance(llist, list):
            llist = [llist]
        for linktarget in llist:
            self.link(linktarget)
        pchlist = kwargs.get('pch', [])
        if not isinstance(pchlist, list):
            pchlist = [pchlist]
        self.add_pch(pchlist)
        clist = kwargs.get('c_args', [])
        if not isinstance(clist, list):
            clist = [clist]
        self.add_compiler_args('c', clist)
        cxxlist = kwargs.get('cxx_args', [])
        if not isinstance(cxxlist, list):
            cxxlist = [cxxlist]
        self.add_compiler_args('cxx', cxxlist)
        if 'version' in kwargs:
            self.set_version(kwargs['version'])
        if 'soversion' in kwargs:
            self.set_soversion(kwargs['soversion'])
        inclist = kwargs.get('include_dirs', [])
        if not isinstance(inclist, list):
            inclist = [inclist]
        self.add_include_dirs(inclist)
        deplist = kwargs.get('deps', [])
        if not isinstance(deplist, list):
            deplist = [deplist]
        self.add_external_deps(deplist)

    def get_subdir(self):
        return self.subdir

    def get_filename(self):
        return self.filename

    def get_extra_args(self, language):
        return self.extra_args.get(language, [])

    def get_dependencies(self):
        return self.link_targets

    def get_basename(self):
        return self.name

    def get_source_subdir(self):
        return self.subdir

    def get_sources(self):
        return self.sources

    def get_generated_sources(self):
        return self.generated

    def should_install(self):
        return self.need_install

    def has_pch(self):
        return len(self.pch) > 0

    def get_pch(self):
        return self.pch

    def get_include_dirs(self):
        return self.include_dirs

    def add_external_deps(self, deps):
        for dep in deps:
            if not isinstance(dep, dependencies.Dependency) and\
               not isinstance(dep, ExternalLibraryHolder):
                raise InvalidArguments('Argument is not an external dependency')
            self.external_deps.append(dep)
            if isinstance(dep, dependencies.Dependency):
                self.process_sourcelist(dep.get_sources())

    def get_external_deps(self):
        return self.external_deps

    def add_dep(self, args):
        [self.add_external_dep(dep) for dep in args]

    def link(self, target):
        if not isinstance(target, StaticLibrary) and \
        not isinstance(target, SharedLibrary):
            raise InvalidArguments('Link target is not library.')
        self.link_targets.append(target)

    def set_generated(self, genlist):
        for g in genlist:
            if not(isinstance(g, GeneratedList)):
                raise InvalidArguments('Generated source argument is not the output of a generator.')
            self.generated.append(g)

    def add_pch(self, pchlist):
        for a in pchlist:
            self.pch.append(a)

    def add_include_dirs(self, args):
        for a in args:
            if not isinstance(a, IncludeDirs):
                raise InvalidArguments('Include directory to be added is not an include directory object.')
        self.include_dirs += args

    def add_compiler_args(self, language, flags):
        for a in flags:
            if not isinstance(a, str):
                raise InvalidArguments('A non-string passed to compiler args.')
        if language in self.extra_args:
            self.extra_args[language] += flags
        else:
            self.extra_args[language] = flags

    def get_aliaslist(self):
        return []

class Executable(BuildTarget):
    def __init__(self, name, subdir, sources, environment, kwargs):
        BuildTarget.__init__(self, name, subdir, sources, kwargs)
        suffix = environment.get_exe_suffix()
        if suffix != '':
            self.filename = self.name + '.' + suffix
        else:
            self.filename = self.name

class StaticLibrary(BuildTarget):
    def __init__(self, name, subdir, sources, environment, kwargs):
        BuildTarget.__init__(self, name, subdir, sources, kwargs)
        prefix = environment.get_static_lib_prefix()
        suffix = environment.get_static_lib_suffix()
        self.filename = prefix + self.name + '.' + suffix

class SharedLibrary(BuildTarget):
    def __init__(self, name, subdir, sources, environment, kwargs):
        self.version = None
        self.soversion = None
        BuildTarget.__init__(self, name, subdir, sources, kwargs)
        self.prefix = environment.get_shared_lib_prefix()
        self.suffix = environment.get_shared_lib_suffix()

    def get_shbase(self):
        return self.prefix + self.name + '.' + self.suffix

    def get_filename(self):
        fname = self.get_shbase()
        if self.version is None:
            return fname
        else:
            return fname + '.' + self.version

    def set_version(self, version):
        if not isinstance(version, str):
            raise InvalidArguments('Shared library version is not a string.')
        self.version = version

    def set_soversion(self, version):
        if not isinstance(version, str):
            raise InvalidArguments('Shared library soversion is not a string.')
        self.soversion = version

    def get_aliaslist(self):
        aliases = []
        if self.soversion is not None:
            aliases.append(self.get_shbase() + '.' + self.soversion)
        if self.version is not None:
            aliases.append(self.get_shbase())
        return aliases

class Test(InterpreterObject):
    def __init__(self, name, exe):
        InterpreterObject.__init__(self)
        self.name = name
        self.exe = exe
        
    def get_exe(self):
        return self.exe
    
    def get_name(self):
        return self.name

class CompilerHolder(InterpreterObject):
    def __init__(self, compiler):
        InterpreterObject.__init__(self)
        self.compiler = compiler
        self.methods.update({'compiles': self.compiles_method,
                             'get_id': self.get_id_method,
                             })

    def get_id_method(self, args, kwargs):
        return self.compiler.get_id()

    def compiles_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('compiles method takes exactly one argument.')
        string = args[0]
        if isinstance(string, nodes.StringStatement):
            string = string.value
        if not isinstance(string, str):
            raise InterpreterException('Argument to compiles() must be a string')
        return self.compiler.compiles(string)

class MesonMain(InterpreterObject):
    def __init__(self, build):
        InterpreterObject.__init__(self)
        self.build = build
        self.methods.update({'get_compiler': self.get_compiler_method})
        
    def get_compiler_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('get_compiler_method must have one and only one argument.')
        cname = args[0]
        for c in self.build.compilers:
            if c.get_language() == cname:
                return CompilerHolder(c)
        raise InterpreterException('Tried to access compiler for unspecified language "%s".' % cname)
        

class Interpreter():

    def __init__(self, build):
        self.build = build
        code = open(os.path.join(build.environment.get_source_dir(),\
                                 environment.build_filename)).read()
        if len(code.strip()) == 0:
            raise InvalidCode('Builder file is empty.')
        assert(isinstance(code, str))
        self.ast = mparser.build_ast(code)
        self.sanity_check_ast()
        self.variables = {}
        self.builtin = {}
        self.builtin['host'] = Host()
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
                      'executable': self.func_executable,
                      'find_dep' : self.func_find_dep,
                      'static_library' : self.func_static_lib,
                      'shared_library' : self.func_shared_lib,
                      'generator' : self.func_generator,
                      'add_test' : self.func_add_test,
                      'headers' : self.func_headers,
                      'man' : self.func_man,
                      'subdir' : self.func_subdir,
                      'data' : self.func_data,
                      'configure_file' : self.func_configure_file,
                      'include_directories' : self.func_include_directories,
                      'add_global_arguments' : self.func_add_global_arguments,
                      'find_program' : self.func_find_program,
                      'find_library' : self.func_find_library,
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
            raise InvalidCode('Line %d: Tried to execute a non-codeblock. Possibly a bug in the parser.' % node.lineno())
        statements = node.get_statements()
        i = 0
        while i < len(statements):
            cur = statements[i]
            self.evaluate_statement(cur)
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
        else:
            raise InvalidCode("Line %d: Unknown statement." % cur.lineno())

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
                    print(actual)
                    print(wanted)
                    raise InvalidArguments('Incorrect argument type.')

    def func_project(self, node, args, kwargs):
        if len(args)< 2:
            raise InvalidArguments('Not enough arguments to project(). Needs at least the project name and one language')
        if len(kwargs) > 0:
            raise InvalidArguments('Project() does not take keyword arguments.')
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('Line %d: Argument %s is not a string.' % (node.lineno(), str(a)))
        if self.build.project is not None:
            raise InvalidCode('Second call to project() on line %d.' % node.lineno())
        self.build.project = args[0]
        print('Project name is "%s".' % self.build.project)
        self.add_languages(node, args[1:])

    def func_message(self, node, args, kwargs):
        self.validate_arguments(args, 1, [str])
        print('Message: %s' % args[0])

    def add_languages(self, node, args):
        for lang in args:
            if lang in self.coredata.compilers:
                comp = self.coredata.compilers[lang]
            else:
                if lang.lower() == 'c':
                    comp = self.environment.detect_c_compiler()
                elif lang.lower() == 'cxx':
                    comp = self.environment.detect_cxx_compiler()
                elif lang.lower() == 'objc':
                    comp = self.environment.detect_objc_compiler()
                elif lang.lower() == 'objcxx':
                    comp = self.environment.detect_objcxx_compiler()
                else:
                    raise InvalidCode('Tried to use unknown language "%s".' % lang)
                comp.sanity_check(self.environment.get_scratch_dir())
                self.coredata.compilers[lang] = comp
            self.build.add_compiler(comp)

    def func_find_program(self, node, args, kwargs):
        self.validate_arguments(args, 1, [str])
        required = kwargs.get('required', False)
        if not isinstance(required, bool):
            raise InvalidArguments('Line %d: "required" argument must be a boolean.' % node.lineno())
        exename = args[0]
        if exename in self.coredata.ext_progs and\
           self.coredata.ext_progs[exename].found():
            return ExternalProgramHolder(self.coredata.ext_progs[exename])
        extprog = dependencies.ExternalProgram(exename)
        progobj = ExternalProgramHolder(extprog)
        self.coredata.ext_progs[exename] = extprog
        if required and not progobj.found():
            raise InvalidArguments('Line %d: program "%s" not found.' % (node.lineno(), exename))
        return progobj

    def func_find_library(self, node, args, kwargs):
        self.validate_arguments(args, 1, [str])
        required = kwargs.get('required', False)
        if not isinstance(required, bool):
            raise InvalidArguments('Line %d: "required" argument must be a boolean.' % node.lineno())
        libname = args[0]
        if libname in self.coredata.ext_libs and\
           self.coredata.ext_libs[libname].found():
            return ExternalLibraryHolder(self.coredata.ext_libs[libname])
        result = self.environment.find_library(libname)
        extlib = dependencies.ExternalLibrary(libname, result)
        libobj = ExternalLibraryHolder(extlib)
        self.coredata.ext_libs[libname] = extlib
        if required and not libobj.found():
            raise InvalidArguments('Line %d: external library "%s" not found.' % (node.lineno(), libname))
        return libobj

    def func_find_dep(self, node, args, kwargs):
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
        return self.build_target(node, args, kwargs, Executable)

    def func_static_lib(self, node, args, kwargs):
        return self.build_target(node, args, kwargs, StaticLibrary)

    def func_shared_lib(self, node, args, kwargs):
        return self.build_target(node, args, kwargs, SharedLibrary)

    def func_generator(self, node, args, kwargs):
        gen = Generator(args, kwargs)
        self.generators.append(gen)
        return gen

    def func_add_test(self, node, args, kwargs):
        self.validate_arguments(args, 2, [str, Executable])
        t = Test(args[0], args[1])
        self.build.tests.append(t)
        print('Adding test "%s"' % args[0])

    def func_headers(self, node, args, kwargs):
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('Line %d: Argument %s is not a string.' % (node.lineno(), str(a)))
        h = Headers(args, kwargs)
        self.build.headers.append(h)
        return h
    
    def func_man(self, node, args, kwargs):
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('Line %d: Argument %s is not a string.' % (node.lineno(), str(a)))
        m = Man(args, kwargs)
        self.build.man.append(m)
        return m
    
    def func_subdir(self, node, args, kwargs):
        if len(kwargs) > 0:
            raise InvalidArguments('Line %d: subdir command takes no keyword arguments.' % node.lineno())
        self.validate_arguments(args, 1, [str])
        prev_subdir = self.subdir
        subdir = os.path.join(prev_subdir, args[0])
        if subdir in self.visited_subdirs:
            raise InvalidArguments('Line %d: tried to enter directory "%s", which has already been visited.'\
                                   % (node.lineno(), subdir))
        self.visited_subdirs[subdir] = True
        self.subdir = subdir
        buildfilename = os.path.join(self.subdir, environment.build_filename)
        self.build_def_files.append(buildfilename)
        code = open(os.path.join(self.environment.get_source_dir(), buildfilename)).read()
        assert(isinstance(code, str))
        codeblock = mparser.build_ast(code)
        print('Going to subdirectory "%s".' % self.subdir)
        self.evaluate_codeblock(codeblock)
        self.subdir = prev_subdir

    def func_data(self, node, args, kwargs):
        if len(args ) < 1:
            raise InvalidArguments('Line %d: Data function must have at least one argument: the subdirectory.' % node.lineno())
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('Line %d: Argument %s is not a string.' % (node.lineno(), str(a)))
        data = Data(args[0], args[1:], kwargs)
        self.build.data.append(data)
        return data
    
    def func_configure_file(self, node, args, kwargs):
        self.validate_arguments(args, 2, [str, str])
        conffile = os.path.join(self.subdir, args[0])
        self.build_def_files.append(conffile)
        c = ConfigureFile(self.subdir, args[0], args[1], kwargs)
        self.build.configure_files.append(c)

    def func_include_directories(self, node, args, kwargs):
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('Line %d: Argument %s is not a string.' % (node.lineno(), str(a)))
        i = IncludeDirs(self.subdir, args, kwargs)
        return i

    def func_add_global_arguments(self, node, args, kwargs):
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('Line %d: Argument %s is not a string.' % (node.lineno(), str(a)))
        if len(self.build.get_targets()) > 0:
            raise InvalidCode('Line %d: global flags can not be set once any build target is defined.' % node.lineno())
        if not 'language' in kwargs:
            raise InvalidCode('Line %d: missing language definition in add_global_arguments' % node.lineno())
        lang = kwargs['language'].lower()
        if lang in self.build.global_args:
            self.build.global_args[lang] += args
        else:
            self.build.global_args[lang] = args

    def flatten(self, args):
        if isinstance(args, nodes.StringStatement):
            return args.get_value()
        result = []
        for a in args:
            if isinstance(a, list):
                result = result + self.flatten(a)
            if isinstance(a, nodes.StringStatement):
                result.append(a.get_value())
            else:
                result.append(a)
        return result

    def build_target(self, node, args, kwargs, targetclass):
        args = self.flatten(args)
        name = args[0]
        sources = args[1:]
        if name in coredata.forbidden_target_names:
            raise InvalidArguments('Line %d: target name "%s" is reserved for Meson\'s internal use. Please rename.'\
                                   % (node.lineno(), name))
        try:
            kw_src = self.flatten(kwargs['sources'])
            if not isinstance(kw_src, list):
                kw_src = [kw_src]
        except KeyError:
            kw_src = []
        sources += kw_src
        if name in self.build.targets:
            raise InvalidCode('Line %d: tried to create target "%s", but a target of that name already exists.' % (node.lineno(), name))
        l = targetclass(name, self.subdir, sources, self.environment, kwargs)
        self.build.targets[name] = l
        print('Creating build target "%s" with %d files.' % (name, len(sources)))
        return l

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
            isinstance(value, nodes.StringStatement) or\
            isinstance(value, str) or\
            isinstance(value, nodes.BoolStatement) or\
            isinstance(value, nodes.IntStatement) or\
            isinstance(value, list):
            return True
        return False
    
    def assignment(self, node):
        var_name = node.var_name
        if not isinstance(var_name, nodes.AtomExpression):
            raise InvalidArguments('Line %d: Tried to assign value to a non-variable.' % node.lineno())
        var_name = var_name.get_value()
        value = self.evaluate_statement(node.value)
        if value is None:
            raise InvalidCode('Line %d: Can not assign None to variable.' % node.lineno())
        if not self.is_assignable(value):
            raise InvalidCode('Line %d: Tried to assign an invalid value to variable.' % node.lineno())
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
            raise InvalidCode('Line %d: Irreducible argument.' % arg.lineno())

    def reduce_arguments(self, args):
        assert(isinstance(args, nodes.Arguments))
        if args.incorrect_order():
            raise InvalidArguments('Line %d: all keyword arguments must be after positional arguments.' % args.lineno())
        reduced_pos = [self.reduce_single(arg) for arg in args.arguments]
        reduced_kw = {}
        for key in args.kwargs.keys():
            if not isinstance(key, str):
                raise InvalidArguments('Line %d: keyword argument name is not a string.' % args.lineno())
            a = args.kwargs[key]
            reduced_kw[key] = self.reduce_single(a)
        return (reduced_pos, reduced_kw)

    def method_call(self, node):
        object_name = node.object_name.get_value()
        method_name = node.method_name.get_value()
        args = node.arguments
        obj = self.get_variable(object_name)
        if not isinstance(obj, InterpreterObject):
            raise InvalidArguments('Line %d: variable "%s" is not callable.' % (node.lineno(), object_name))
        (args, kwargs) = self.reduce_arguments(args)
        return obj.method_call(method_name, args, kwargs)
    
    def evaluate_if(self, node):
        result = self.evaluate_statement(node.get_clause())
        cond = None
        if isinstance(result, nodes.BoolExpression) or \
           isinstance(result, nodes.BoolStatement):
            cond = result.get_value()
        if isinstance(result, bool):
            cond = result
        
        if cond is not None:
            if cond:
                self.evaluate_codeblock(node.get_trueblock())
            else:
                self.evaluate_codeblock(node.get_falseblock())
        else:
            print(node.get_clause())
            print(result)
            raise InvalidCode('Line %d: If clause does not evaluate to true or false.' % node.lineno())
    
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
        assert(type(val1) == type(val2))
        if node.get_ctype() == '==':
            return val1 == val2
        elif node.get_ctype() == '!=':
            return val1 != val2
        else:
            raise InvalidCode('You broke me.')
    
    def evaluate_arraystatement(self, cur):
        (arguments, kwargs) = self.reduce_arguments(cur.get_args())
        if len(kwargs) > 0:
            raise InvalidCode('Line %d: Keyword arguments are invalid in array construction.' % cur.lineno())
        return arguments

if __name__ == '__main__':
    code = """project('myawesomeproject')
    message('I can haz text printed out?')
    language('c')
    prog = executable('prog', 'prog.c', 'subfile.c')
    dep = find_dep('gtk+-3.0')
    prog.add_dep(dep)
    """
    i = Interpreter(code, environment.Environment('.', 'work area'))
    i.run()
