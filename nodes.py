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

class Node():
    pass

class Expression(Node):
    pass

class Statement(Node):
    pass

class AtomExpression(Expression):
    def __init__(self, value):
        Expression.__init__(self)
        self.value = value

class StringExpression(Expression):
    def __init__(self, value):
        Expression.__init__(self)
        self.value = value

class AtomStatement(Statement):
    def __init__(self, value):
        Statement.__init__(self)
        assert(type(value) == type(''))
        self.value = value

class StringStatement(Statement):
    def __init__(self, value):
        assert(type(value) == type(''))
        Statement.__init__(self)
        self.value = value

class FunctionCall(Statement):
    def __init__(self, func_name, arguments):
        Statement.__init__(self)
        self.func_name = func_name
        self.arguments = arguments
        
    def get_function_name(self):
        return self.func_name.value

class MethodCall(Statement):
    def __init__(self, object_name, method_name, arguments):
        Statement.__init__(self)
        self.object_name = object_name
        self.method_name = method_name
        self.arguments = arguments

class Assignment(Statement):
    def __init__(self, var_name, value):
        Statement.__init__(self)
        self.var_name = var_name
        self.value = value

class CodeBlock(Statement):
    def __init__(self):
        Statement.__init__(self)
        self.statements = []
        
    def prepend(self, statement):
        self.statements = [statement] + self.statements
        
    def get_statements(self):
        return self.statements

class Arguments(Statement):
    def __init__(self):
        Statement.__init__(self)
        self.arguments = []
        
    def prepend(self, statement):
        self.arguments = [statement] + self.arguments

def statement_from_expression(expr):
    if isinstance(expr, AtomExpression):
        return AtomStatement(expr.value)
    if isinstance(expr, StringExpression):
        return StringStatement(expr.value)
    raise RuntimeError('Can not convert unknown expression to a statement.')
