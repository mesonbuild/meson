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

import parser
import nodes
import environment
import os

class InterpreterException(Exception):
    pass

class InvalidCode(InterpreterException):
    pass

class InvalidArguments(InterpreterException):
    pass

class InterpreterObject():
    
    def __init__(self):
        self.methods = {}

    def method_call(self, method_name, args):
        if method_name in self.methods:
            return self.methods[method_name](args)
        raise InvalidCode('Unknown method "%s" in object.' % method_name)

class Headers(InterpreterObject):
    
    def __init__(self, sources):
        InterpreterObject.__init__(self)
        self.sources = sources
        self.methods.update({'set_subdir' : self.set_subdir})
        self.subdir = ''

    def set_subdir(self, args):
        self.subdir = args[0]

    def get_subdir(self):
        return self.subdir
    
    def get_sources(self):
        return self.sources

class Data(InterpreterObject):
    
    def __init__(self, subdir, sources):
        InterpreterObject.__init__(self)
        self.subdir = subdir
        self.sources = sources

    def get_subdir(self):
        return self.subdir

    def get_sources(self):
        return self.sources

class ConfigureFile(InterpreterObject):
    
    def __init__(self, subdir, sourcename, targetname):
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

    def __init__(self, sources):
        InterpreterObject.__init__(self)
        self.sources = sources
        self.validate_sources()
        
    def validate_sources(self):
        for s in self.sources:
            num = int(s.split('.')[-1])
            if num < 1 or num > 8:
                raise InvalidArguments('Man file must have a file extension of a number between 1 and 8')

    def get_sources(self):
        return self.sources

class BuildTarget(InterpreterObject):

    def __init__(self, name, subdir, sources):
        InterpreterObject.__init__(self)
        self.name = name
        self.subdir = subdir
        self.sources = sources
        self.external_deps = []
        self.methods.update({'add_dep': self.add_dep_method,
                        'link' : self.link_method,
                        'install': self.install_method,
                        'pch' : self.pch_method
                        })
        self.link_targets = []
        self.filename = 'no_name'
        self.need_install = False
        self.pch = []

    def get_filename(self):
        return self.filename
        
    def get_dependencies(self):
        return self.link_targets

    def get_basename(self):
        return self.name

    def get_source_subdir(self):
        return self.subdir

    def get_sources(self):
        return self.sources

    def should_install(self):
        return self.need_install

    def has_pch(self):
        return len(self.pch) > 0

    def get_pch(self):
        return self.pch

    def add_external_dep(self, dep):
        if not isinstance(dep, environment.PkgConfigDependency):
            raise InvalidArguments('Argument is not an external dependency')
        self.external_deps.append(dep)

    def get_external_deps(self):
        return self.external_deps

    def add_dep_method(self, args):
        [self.add_external_dep(dep) for dep in args]

    def link_method(self, args):
        target = args[0]
        if not isinstance(target, StaticLibrary) and \
        not isinstance(target, SharedLibrary):
            raise InvalidArguments('Link target is not library.')
        self.link_targets.append(target)

    def install_method(self, args):
        if len(args) != 0:
            raise InvalidArguments('Install() takes no arguments.')
        self.need_install = True
    
    def pch_method(self, args):
        if len(args) == 0:
            raise InvalidArguments('Pch requires arguments.')
        for a in args:
            self.pch.append(a)


class Executable(BuildTarget):
    def __init__(self, name, subdir, sources, environment):
        BuildTarget.__init__(self, name, subdir, sources)
        suffix = environment.get_exe_suffix()
        if suffix != '':
            self.filename = self.name + '.' + suffix
        else:
            self.filename = self.name

class StaticLibrary(BuildTarget):
    def __init__(self, name, subdir, sources, environment):
        BuildTarget.__init__(self, name, subdir, sources)
        prefix = environment.get_static_lib_prefix()
        suffix = environment.get_static_lib_suffix()
        self.filename = prefix + self.name + '.' + suffix


class SharedLibrary(BuildTarget):
    def __init__(self, name, subdir, sources, environment):
        BuildTarget.__init__(self, name, subdir, sources)
        prefix = environment.get_shared_lib_prefix()
        suffix = environment.get_shared_lib_suffix()
        self.filename = prefix + self.name + '.' + suffix


class Test(InterpreterObject):
    def __init__(self, name, exe):
        InterpreterObject.__init__(self)
        self.name = name
        self.exe = exe
        
    def get_exe(self):
        return self.exe
    
    def get_name(self):
        return self.name

class Interpreter():

    def __init__(self, code, build):
        self.build = build
        self.ast = parser.build_ast(code)
        self.sanity_check_ast()
        self.variables = {}
        self.environment = build.environment
        self.build_func_dict()
        self.subdir = ''

    def build_func_dict(self):
        self.funcs = {'project' : self.func_project, 
                      'message' : self.func_message,
                      'executable': self.func_executable,
                      'find_dep' : self.func_find_dep,
                      'static_library' : self.func_static_lib,
                      'shared_library' : self.func_shared_lib,
                      'add_test' : self.func_add_test,
                      'headers' : self.func_headers,
                      'man' : self.func_man,
                      'subdir' : self.func_subdir,
                      'data' : self.func_data,
                      'configure_file' : self.func_configure_file
                      }
        
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
        if not isinstance(node, nodes.CodeBlock):
            raise InvalidCode('Tried to execute a non-codeblock. Possibly a bug in the parser.')
        statements = node.get_statements()
        i = 0
        while i < len(statements):
            cur = statements[i]
            self.evaluate_statement(cur)
            i += 1 # In THE FUTURE jump over blocks and stuff.

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
        else:
            raise InvalidCode("Unknown statement in line %d." % cur.lineno())

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

    def func_project(self, node, args):
        if len(args) < 2:
            raise InvalidArguments('Not enough arguments to project(). Needs at least the project name and one language')
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('Line %d: Argument %s is not a string.' % (node.lineno(), str(a)))
        if self.build.project is not None:
            raise InvalidCode('Second call to project() on line %d.' % node.lineno())
        self.build.project = args[0]
        print('Project name is "%s".' % self.build.project)
        self.add_languages(node, args[1:])

    def func_message(self, node, args):
        self.validate_arguments(args, 1, [str])
        print('Message: %s' % args[0])

    def add_languages(self, node, args):
        for lang in args:
            if lang.lower() == 'c':
                comp = self.environment.detect_c_compiler()
                comp.sanity_check(self.environment.get_scratch_dir())
                self.build.compilers.append(comp)
            elif lang.lower() == 'c++':
                comp = self.environment.detect_cxx_compiler()
                comp.sanity_check(self.environment.get_scratch_dir())
                self.build.compilers.append(comp)
            else:
                raise InvalidCode('Tried to use unknown language "%s".' % lang)

    def func_find_dep(self, node, args):
        self.validate_arguments(args, 1, [str])
        name = args[0]
        dep = environment.find_external_dependency(name)
        return dep

    def func_executable(self, node, args):
        return self.build_target(node, args, Executable)

    def func_static_lib(self, node, args):
        return self.build_target(node, args, StaticLibrary)

    def func_shared_lib(self, node, args):
        return self.build_target(node, args, SharedLibrary)
    
    def func_add_test(self, node, args):
        self.validate_arguments(args, 2, [str, Executable])
        t = Test(args[0], args[1])
        self.build.tests.append(t)
        print('Adding test "%s"' % args[0])
        
    def func_headers(self, node, args):
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('Line %d: Argument %s is not a string.' % (node.lineno(), str(a)))
        h = Headers(args)
        self.build.headers.append(h)
        return h
    
    def func_man(self, node, args):
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('Line %d: Argument %s is not a string.' % (node.lineno(), str(a)))
        m = Man(args)
        self.build.man.append(m)
        return m
    
    def func_subdir(self, node, args):
        self.validate_arguments(args, 1, [str])
        prev_subdir = self.subdir
        self.subdir = os.path.join(prev_subdir, args[0])
        buildfilename = os.path.join(self.subdir, environment.builder_filename)
        code = open(os.path.join(self.environment.get_source_dir(), buildfilename)).read()
        assert(isinstance(code, str))
        codeblock = parser.build_ast(code)
        print('Going to subdirectory "%s".' % self.subdir)
        self.evaluate_codeblock(codeblock)
        self.subdir = prev_subdir

    def func_data(self, node, args):
        if len(args ) < 2:
            raise InvalidArguments('Line %d: Data function must have at least two arguments: name and source file(s)' % node.lineno())
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('Line %d: Argument %s is not a string.' % (node.lineno(), str(a)))
        data = Data(args[0], args[1:])
        self.build.data.append(data)
        return data
    
    def func_configure_file(self, node, args):
        self.validate_arguments(args, 2, [str, str])
        c = ConfigureFile(self.subdir, args[0], args[1])
        self.build.configure_files.append(c)

    def build_target(self, node, args, targetclass):
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('Line %d: Argument %s is not a string.' % (node.lineno(), str(a)))
        name= args[0]
        sources = args[1:]
        if len(sources) == 0:
            raise InvalidArguments('Line %d: target has no source files.' % node.lineno())
        if name in self.build.targets:
            raise InvalidCode('Line %d: tried to create target "%s", but a target of that name already exists.' % (node.lineno(), name))
        l = targetclass(name, self.subdir, sources, self.environment)
        self.build.targets[name] = l
        print('Creating build target "%s" with %d files.' % (name, len(sources)))
        return l

    def function_call(self, node):
        func_name = node.get_function_name()
        args = self.reduce_arguments(node.arguments)
        if func_name in self.funcs:
            return self.funcs[func_name](node, args)
        else:
            raise InvalidCode('Unknown function "%s".' % func_name)

    def is_assignable(self, value):
        if isinstance(value, InterpreterObject) or \
            isinstance(value, environment.PkgConfigDependency) or\
            isinstance(value, nodes.StringStatement) or\
            isinstance(value, nodes.BoolStatement):
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
        self.variables[var_name] = value
        return value
    
    def reduce_arguments(self, args):
        assert(isinstance(args, nodes.Arguments))
        reduced = []
        for arg in args.arguments:
            if isinstance(arg, nodes.AtomExpression) or isinstance(arg, nodes.AtomStatement):
                r = self.variables[arg.value]
            elif isinstance(arg, nodes.StringExpression) or isinstance(arg, nodes.StringStatement):
                r = arg.get_string()
            elif isinstance(arg, nodes.FunctionCall):
                r  = self.function_call(arg)
            elif isinstance(arg, nodes.MethodCall):
                r = self.method_call(arg)
            else:
                raise InvalidCode('Line %d: Irreducible argument.' % args.lineno())
            reduced.append(r)
        assert(len(reduced) == len(args))
        return reduced

    def method_call(self, node):
        object_name = node.object_name.get_value()
        method_name = node.method_name.get_value()
        args = node.arguments
        if not object_name in self.variables:
            raise InvalidArguments('Line %d: unknown variable "%s".' % (node.lineno(), object_name))
        obj = self.variables[object_name]
        if not isinstance(obj, InterpreterObject):
            raise InvalidArguments('Line %d: variable "%s" is not callable.' % (node.lineno(), object_name))
        return obj.method_call(method_name, self.reduce_arguments(args))

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
