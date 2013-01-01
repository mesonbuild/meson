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

class InterpreterException(Exception):
    pass

class InvalidCode(InterpreterException):
    pass

class InvalidArguments(InterpreterException):
    pass

class InterpreterObject():
    
    def method_call(self, method_name):
        raise InvalidCode('Object does not have method %s.' % method_name)

class BuildTarget(InterpreterObject):
    
    def __init__(self, name, sources):
        self.name = name
        self.sources = sources
        self.external_deps = []
        
    def get_basename(self):
        return self.name
    
    def get_sources(self):
        return self.sources
    
    def add_external_dep(self, dep):
        if not isinstance(dep, environment.PkgConfigDependency):
            print(dep)
            print(type(dep))
            raise InvalidArguments('Argument is not an external dependency')
        self.external_deps.append(dep)
        
    def get_external_deps(self):
        return self.external_deps

    def method_call(self, method_name, args):
        if method_name == 'add_dep':
            [self.add_external_dep(dep) for dep in args]
            return
        raise InvalidCode('Unknown method "%s" in BuildTarget.' % method_name)

class Executable(BuildTarget):
    pass

class Interpreter():

    def __init__(self, code, environment):
        self.ast = parser.build_ast(code)
        self.sanity_check_ast()
        self.project = None
        self.compilers = []
        self.targets = {}
        self.variables = {}
        self.environment = environment

    def get_project(self):
        return self.project

    def get_targets(self):
        return self.targets

    def sanity_check_ast(self):
        if not isinstance(self.ast, nodes.CodeBlock):
            raise InvalidCode('AST is of invalid type. Possibly a bug in the parser.')
        if len(self.ast.get_statements()) == 0:
            raise InvalidCode('No statements in code.')
        first = self.ast.get_statements()[0]
        if not isinstance(first, nodes.FunctionCall) or first.get_function_name() != 'project':
            raise InvalidCode('First statement must be a call to project')

    def run(self):
        i = 0
        statements = self.ast.get_statements()
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
        self.validate_arguments(args, 1, [str])
        if self.project is not None:
            raise InvalidCode('Second call to project() on line %d.' % node.lineno())
        self.project = args[0]
        print('Project name is "%s".' % self.project)

    def func_message(self, node, args):
        self.validate_arguments(args, 1, [str])
        print('Message: %s' % args[0])

    def func_language(self, node, args):
        if len(args) == 0:
            raise InvalidArguments('Line %d: no arguments to function language.' % node.lineno())
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('Line %d: Argument %s is not a string.' % (node.lineno(), str(a)))
        if len(self.compilers) > 0:
            raise InvalidCode('Function language() can only be called once (line %d).' % node.lineno())
        for lang in args:
            if lang.lower() == 'c':
                comp = self.environment.detect_c_compiler()
                comp.sanity_check(self.environment.get_scratch_dir())
                self.compilers.append(comp)
            else:
                raise InvalidCode('Tried to use unknown language "%s".' % lang)

    def func_executable(self, node, args):
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('Line %d: Argument %s is not a string.' % (node.lineno(), str(a)))
        name = args[0]
        sources = args[1:]
        if name in self.targets:
            raise InvalidCode('Line %d, tried to create executable "%s", but a build target of that name already exists.' % (node.lineno(), name))
        exe = Executable(name, sources)
        self.targets[name] = exe
        print('Creating executable %s with %d files.' % (name, len(sources)))
        return exe
    
    def func_find_dep(self, node, args):
        self.validate_arguments(args, 1, [str])
        name = args[0]
        dep = environment.find_external_dependency(name)
        return dep

    def function_call(self, node):
        func_name = node.get_function_name()
        args = self.reduce_arguments(node.arguments)
        if func_name == 'project':
            return self.func_project(node, args)
        elif func_name == 'message':
            return self.func_message(node, args)
        elif func_name == 'language':
            return self.func_language(node, args)
        elif func_name == 'executable':
            return self.func_executable(node, args)
        elif func_name == 'find_dep':
            return self.func_find_dep(node, args)
        else:
            raise InvalidCode('Unknown function "%s".' % func_name)
    
    def is_assignable(self, value):
        if isinstance(value, InterpreterObject) or \
            isinstance(value, environment.PkgConfigDependency):
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
                raise InvalidCode('Line %d: Irreducable argument.' % args.lineno())
            reduced.append(r)
        assert(len(reduced) == len(args))
        return reduced

    def method_call(self, node):
        object_name = node.object_name.get_value()
        method_name = node.method_name.get_value()
        args = node.arguments
        if not object_name in self.variables:
            raise InvalidArguments('Line %d: unknown variable %s.' % (node.lineno(), object_name))
        obj = self.variables[object_name]
        if not isinstance(obj, InterpreterObject):
            raise InvalidArguments('Line %d: variable %s can not be called.' % (node.lineno(), object_name))
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
