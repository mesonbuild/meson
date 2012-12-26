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

class InterpreterException(Exception):
    pass

class InvalidCode(InterpreterException):
    pass

class Interpreter():
    
    def __init__(self, code):
        self.ast = parser.build_ast(code)
        self.sanity_check_ast()
        self.project = None
        
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

    def function_call(self, node):
        func_name = node.get_function_name()
        if func_name == 'project':
            args = node.arguments.arguments
            if len(args) != 1:
                raise InvalidCode('Project() must have one and only one argument.')
            if not isinstance(args[0], nodes.StringStatement):
                raise InvalidCode('Project() argument must be a string.')
            if self.project is not None:
                raise InvalidCode('Second call to project() on line %d.' % node.lineno())
            self.project = args[0].get_string()
            print("Project name is %s." % self.project)
        elif func_name == 'message':
            args = node.arguments.arguments
            if len(args) != 1:
                raise InvalidCode('Message() must have only one argument')
            if not isinstance(args[0], nodes.StringStatement):
                raise InvalidCode('Argument to Message() must be a string')
            print('Message: %s' % args[0].get_string())

if __name__ == '__main__':
    code = """project('myawesomeproject')
    message('I can haz text printed out?')
    message('It workses!')
    """
    i = Interpreter(code)
    i.run()
