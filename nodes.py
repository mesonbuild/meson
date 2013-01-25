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
    def __init__(self, lineno):
        self.line_number = lineno
    
    def lineno(self):
        return self.line_number

class Expression(Node):
    pass

class Statement(Node):
    pass

class BoolExpression(Expression):
    def __init__(self, value, lineno):
        Expression.__init__(self, lineno)
        self.value = value
        assert(isinstance(value, bool))
    
    def get_value(self):
        return self.value

class AtomExpression(Expression):
    def __init__(self, value, lineno):
        Expression.__init__(self, lineno)
        self.value = value
        
    def get_value(self):
        return self.value

class StringExpression(Expression):
    def __init__(self, value, lineno):
        Expression.__init__(self, lineno)
        self.value = value

class AtomStatement(Statement):
    def __init__(self, value, lineno):
        Statement.__init__(self, lineno)
        assert(type(value) == type(''))
        self.value = value
        
    def get_value(self):
        return self.value

class BoolStatement(Statement):
    def __init__(self, value, lineno):
        Statement.__init__(self, lineno)
        assert(isinstance(value, bool))
        self.value = value

    def get_value(self):
        return self.value

class StringStatement(Statement):
    def __init__(self, value, lineno):
        assert(type(value) == type(''))
        Statement.__init__(self, lineno)
        self.value = value
        
    def get_string(self):
        return self.value

class FunctionCall(Statement):
    def __init__(self, func_name, arguments, lineno):
        Statement.__init__(self, lineno)
        self.func_name = func_name
        self.arguments = arguments
        
    def get_function_name(self):
        return self.func_name.value

class MethodCall(Statement):
    def __init__(self, object_name, method_name, arguments, lineno):
        Statement.__init__(self, lineno)
        self.object_name = object_name
        self.method_name = method_name
        self.arguments = arguments

class Assignment(Statement):
    def __init__(self, var_name, value, lineno):
        Statement.__init__(self, lineno)
        self.var_name = var_name
        self.value = value

class CodeBlock(Statement):
    def __init__(self, lineno):
        Statement.__init__(self, lineno)
        self.statements = []
        
    def prepend(self, statement):
        self.statements = [statement] + self.statements
        
    def get_statements(self):
        return self.statements

class Arguments(Statement):
    def __init__(self, lineno):
        Statement.__init__(self, lineno)
        self.arguments = []
        
    def prepend(self, statement):
        self.arguments = [statement] + self.arguments

    def __len__(self):
        return len(self.arguments)

def statement_from_expression(expr):
    if isinstance(expr, AtomExpression):
        return AtomStatement(expr.value, expr.lineno())
    if isinstance(expr, StringExpression):
        return StringStatement(expr.value, expr.lineno())
    if isinstance(expr, BoolExpression):
        return BoolStatement(expr.value, expr.lineno())
    raise RuntimeError('Can not convert unknown expression to a statement.')
