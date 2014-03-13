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

class IntExpression(Expression):
    def __init__(self, value, lineno):
        Expression.__init__(self, lineno)
        self.value = value

    def get_value(self):
        return self.value

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

class IntStatement(Statement):
    def __init__(self, value, lineno):
        Statement.__init__(self, lineno)
        assert(isinstance(value, int))
        self.value = value

    def get_value(self):
        return self.value

class AndStatement(Statement):
    def __init__(self, left, right):
        Statement.__init__(self, left.lineno)
        self.left = left
        self.right = right

class OrStatement(Statement):
    def __init__(self, left, right):
        Statement.__init__(self, left.lineno)
        self.left = left
        self.right = right

class NotStatement(Statement):
    def __init__(self, val):
        Statement.__init__(self, val.lineno)
        self.val = val

class IfStatement(Statement):
    def __init__(self, clause, trueblock, falseblock, lineno):
        Statement.__init__(self, lineno)
        self.clause = clause
        self.trueblock = trueblock
        self.falseblock = falseblock

    def get_clause(self):
        return self.clause

    def get_trueblock(self):
        return self.trueblock

    def get_falseblock(self):
        return self.falseblock

class Comparison(Statement):
    def __init__(self, first, ctype, second, lineno):
        Statement.__init__(self, lineno)
        self.first = first
        self.ctype = ctype
        self.second = second
    
    def get_first(self):
        return self.first

    def get_ctype(self):
        return self.ctype

    def get_second(self):
        return self.second

class ArrayStatement(Statement):
    def __init__(self, args, lineno):
        Statement.__init__(self, lineno)
        self.args = args

    def get_args(self):
        return self.args

class StringStatement(Statement):
    def __init__(self, value, lineno):
        assert(type(value) == type(''))
        Statement.__init__(self, lineno)
        self.value = value

    def get_value(self):
        return self.value

class FunctionCall(Statement):
    def __init__(self, func_name, arguments, lineno):
        Statement.__init__(self, lineno)
        self.func_name = func_name
        self.arguments = arguments
        
    def get_function_name(self):
        return self.func_name.value

class MethodCall(Statement):
    def __init__(self, invokable, method_name, arguments, lineno):
        Statement.__init__(self, lineno)
        self.invokable = invokable
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
        self.kwargs = {}
        self.order_error = False

    def prepend(self, statement):
        self.arguments = [statement] + self.arguments

    def set_kwarg(self, name, value):
        if self.num_args() > 0:
            self.order_error = True
        self.kwargs[name.get_value()] = value

    def num_args(self):
        return len(self.arguments)

    def num_kwargs(self):
        return len(self.kwargs)
    
    def incorrect_order(self):
        return self.order_error

    def __len__(self):
        return self.num_args() # Fixme

def statement_from_expression(expr):
    if isinstance(expr, AtomExpression):
        return AtomStatement(expr.value, expr.lineno())
    if isinstance(expr, StringExpression):
        return StringStatement(expr.value, expr.lineno())
    if isinstance(expr, BoolExpression):
        return BoolStatement(expr.value, expr.lineno())
    if isinstance(expr, IntExpression):
        return IntStatement(expr.get_value(), expr.lineno())
    raise RuntimeError('Can not convert unknown expression to a statement.')
