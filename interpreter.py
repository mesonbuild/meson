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
    pass

class Executable(InterpreterObject):
    
    def __init__(self, name, sources):
        self.name = name
        self.sources = sources
        
    def get_basename(self):
        return self.name
    
    def get_sources(self):
        return self.sources


class Interpreter():
    
    def __init__(self, code):
        self.ast = parser.build_ast(code)
        self.sanity_check_ast()
        self.project = None
        self.compilers = []
        self.executables = {}
        
    def get_project(self):
        return self.project

    def get_executables(self):
        return self.executables

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
            if isinstance(cur, nodes.FunctionCall):
                self.function_call(cur)
            else:
                print("Unknown statement in line %d." % cur.lineno())
            i += 1

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
        self.validate_arguments(args, 1, [nodes.StringStatement])
        if self.project is not None:
            raise InvalidCode('Second call to project() on line %d.' % node.lineno())
        self.project = args[0].get_string()
        print("Project name is %s." % self.project)

    def func_message(self, node, args):
        self.validate_arguments(args, 1, [nodes.StringStatement])
        print('Message: %s' % args[0].get_string())
        
    def func_language(self, node, args):
        self.validate_arguments(args, 1, [nodes.StringStatement])
        if len(self.compilers) > 0:
            raise InvalidCode('Function language() can only be called once (line %d).' % node.lineno())
        lang = args[0].get_string()
        if lang.lower() == 'c':
            self.compilers.append(environment.detect_c_compiler('gcc'))
        else:
            raise InvalidCode('Tried to use unknown language "%s".' % lang)

    def func_executable(self, node, args):
        self.validate_arguments(args, 2, (nodes.StringStatement, nodes.StringStatement))
        name = args[0].get_string()
        sources = [args[1].get_string()]
        if name in self.executables:
            raise InvalidCode('Line %d, tried to create executable "%s", which already exists.' % (node.lineno(), name))
        exe = Executable(name, sources)
        self.executables[name] = exe
        print('Creating executable %s with file %s' % (name, sources[0]))
        return exe

    def function_call(self, node):
        func_name = node.get_function_name()
        args = node.arguments.arguments
        if func_name == 'project':
            self.func_project(node, args)
        elif func_name == 'message':
            self.func_message(node, args)
        elif func_name == 'language':
            self.func_language(node, args)
        elif func_name == 'executable':
            self.func_executable(node, args)
        else:
            raise InvalidCode('Unknown function "%s".' % func_name)

if __name__ == '__main__':
    code = """project('myawesomeproject')
    message('I can haz text printed out?')
    message('It workses!')
    language('c')
    executable('prog', 'prog.c')
    """
    i = Interpreter(code)
    i.run()
