# Copyright 2016-2017 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This class contains the basic functionality needed to run any interpreter
# or an interpreter-based tool.

from . import mparser, mesonlib, mlog
from . import environment, dependencies

import os, copy, re, types
from functools import wraps

# Decorators for method calls.

def check_stringlist(a, msg='Arguments must be strings.'):
    if not isinstance(a, list):
        mlog.debug('Not a list:', str(a))
        raise InvalidArguments('Argument not a list.')
    if not all(isinstance(s, str) for s in a):
        mlog.debug('Element not a string:', str(a))
        raise InvalidArguments(msg)

def _get_callee_args(wrapped_args, want_subproject=False):
    s = wrapped_args[0]
    n = len(wrapped_args)
    # Raise an error if the codepaths are not there
    subproject = None
    if want_subproject and n == 2:
        if hasattr(s, 'subproject'):
            # Interpreter base types have 2 args: self, node
            node_or_state = wrapped_args[1]
            # args and kwargs are inside the node
            args = None
            kwargs = None
            subproject = s.subproject
        elif hasattr(wrapped_args[1], 'subproject'):
            # Module objects have 2 args: self, interpreter
            node_or_state = wrapped_args[1]
            # args and kwargs are inside the node
            args = None
            kwargs = None
            subproject = wrapped_args[1].subproject
        else:
            raise AssertionError('Unknown args: {!r}'.format(wrapped_args))
    elif n == 3:
        # Methods on objects (*Holder, MesonMain, etc) have 3 args: self, args, kwargs
        node_or_state = None # FIXME
        args = wrapped_args[1]
        kwargs = wrapped_args[2]
        if want_subproject:
            if hasattr(s, 'subproject'):
                subproject = s.subproject
            elif hasattr(s, 'interpreter'):
                subproject = s.interpreter.subproject
    elif n == 4:
        # Meson functions have 4 args: self, node, args, kwargs
        # Module functions have 4 args: self, state, args, kwargs; except,
        # PythonInstallation methods have self, interpreter, args, kwargs
        node_or_state = wrapped_args[1]
        args = wrapped_args[2]
        kwargs = wrapped_args[3]
        if want_subproject:
            if isinstance(s, InterpreterBase):
                subproject = s.subproject
            else:
                subproject = node_or_state.subproject
    elif n == 5:
        # Module snippets have 5 args: self, interpreter, state, args, kwargs
        node_or_state = wrapped_args[2]
        args = wrapped_args[3]
        kwargs = wrapped_args[4]
        if want_subproject:
            subproject = node_or_state.subproject
    else:
        raise AssertionError('Unknown args: {!r}'.format(wrapped_args))
    # Sometimes interpreter methods are called internally with None instead of
    # empty list/dict
    args = args if args is not None else []
    kwargs = kwargs if kwargs is not None else {}
    return s, node_or_state, args, kwargs, subproject

def flatten(args):
    if isinstance(args, mparser.StringNode):
        return args.value
    if isinstance(args, (int, str, mesonlib.File, InterpreterObject)):
        return args
    result = []
    for a in args:
        if isinstance(a, list):
            rest = flatten(a)
            result = result + rest
        elif isinstance(a, mparser.StringNode):
            result.append(a.value)
        else:
            result.append(a)
    return result

def noPosargs(f):
    @wraps(f)
    def wrapped(*wrapped_args, **wrapped_kwargs):
        args = _get_callee_args(wrapped_args)[2]
        if args:
            raise InvalidArguments('Function does not take positional arguments.')
        return f(*wrapped_args, **wrapped_kwargs)
    return wrapped

def noKwargs(f):
    @wraps(f)
    def wrapped(*wrapped_args, **wrapped_kwargs):
        kwargs = _get_callee_args(wrapped_args)[3]
        if kwargs:
            raise InvalidArguments('Function does not take keyword arguments.')
        return f(*wrapped_args, **wrapped_kwargs)
    return wrapped

def stringArgs(f):
    @wraps(f)
    def wrapped(*wrapped_args, **wrapped_kwargs):
        args = _get_callee_args(wrapped_args)[2]
        assert(isinstance(args, list))
        check_stringlist(args)
        return f(*wrapped_args, **wrapped_kwargs)
    return wrapped

def noArgsFlattening(f):
    setattr(f, 'no-args-flattening', True)
    return f

class permittedKwargs:

    def __init__(self, permitted):
        self.permitted = permitted

    def __call__(self, f):
        @wraps(f)
        def wrapped(*wrapped_args, **wrapped_kwargs):
            s, node_or_state, args, kwargs, _ = _get_callee_args(wrapped_args)
            loc = types.SimpleNamespace()
            if hasattr(s, 'subdir'):
                loc.subdir = s.subdir
                loc.lineno = s.current_lineno
            elif node_or_state and hasattr(node_or_state, 'subdir'):
                loc.subdir = node_or_state.subdir
                loc.lineno = node_or_state.current_lineno
            else:
                loc = None
            for k in kwargs:
                if k not in self.permitted:
                    mlog.warning('''Passed invalid keyword argument "{}".'''.format(k), location=loc)
                    mlog.warning('This will become a hard error in the future.')
            return f(*wrapped_args, **wrapped_kwargs)
        return wrapped


class FeatureCheckBase:
    "Base class for feature version checks"

    def __init__(self, feature_name, version):
        self.feature_name = feature_name
        self.feature_version = version

    @staticmethod
    def get_target_version(subproject):
        # Don't do any checks if project() has not been parsed yet
        if subproject not in mesonlib.project_meson_versions:
            return ''
        return mesonlib.project_meson_versions[subproject]

    def use(self, subproject):
        tv = self.get_target_version(subproject)
        # No target version
        if tv == '':
            return
        # Target version is new enough
        if mesonlib.version_compare_condition_with_min(tv, self.feature_version):
            return
        # Feature is too new for target version, register it
        if subproject not in self.feature_registry:
            self.feature_registry[subproject] = {self.feature_version: set()}
        register = self.feature_registry[subproject]
        if self.feature_version not in register:
            register[self.feature_version] = set()
        if self.feature_name in register[self.feature_version]:
            # Don't warn about the same feature multiple times
            # FIXME: This is needed to prevent duplicate warnings, but also
            # means we won't warn about a feature used in multiple places.
            return
        register[self.feature_version].add(self.feature_name)
        self.log_usage_warning(tv)

    @classmethod
    def report(cls, subproject):
        if subproject not in cls.feature_registry:
            return
        warning_str = cls.get_warning_str_prefix(cls.get_target_version(subproject))
        fv = cls.feature_registry[subproject]
        for version in sorted(fv.keys()):
            warning_str += '\n * {}: {}'.format(version, fv[version])
        mlog.warning(warning_str)

    def __call__(self, f):
        @wraps(f)
        def wrapped(*wrapped_args, **wrapped_kwargs):
            subproject = _get_callee_args(wrapped_args, want_subproject=True)[4]
            if subproject is None:
                raise AssertionError('{!r}'.format(wrapped_args))
            self.use(subproject)
            return f(*wrapped_args, **wrapped_kwargs)
        return wrapped

class FeatureNew(FeatureCheckBase):
    """Checks for new features"""
    # Class variable, shared across all instances
    #
    # Format: {subproject: {feature_version: set(feature_names)}}
    feature_registry = {}

    @staticmethod
    def get_warning_str_prefix(tv):
        return 'Project specifies a minimum meson_version \'{}\' but uses features which were added in newer versions:'.format(tv)

    def log_usage_warning(self, tv):
        mlog.warning('Project targetting \'{}\' but tried to use feature introduced '
                     'in \'{}\': {}'.format(tv, self.feature_version, self.feature_name))

class FeatureDeprecated(FeatureCheckBase):
    """Checks for deprecated features"""
    # Class variable, shared across all instances
    #
    # Format: {subproject: {feature_version: set(feature_names)}}
    feature_registry = {}

    @staticmethod
    def get_warning_str_prefix(tv):
        return 'Deprecated features used:'

    def log_usage_warning(self, tv):
        mlog.deprecation('Project targetting \'{}\' but tried to use feature '
                         'deprecated since \'{}\': {}'
                         ''.format(tv, self.feature_version, self.feature_name))


class FeatureCheckKwargsBase:
    def __init__(self, feature_name, feature_version, kwargs):
        self.feature_name = feature_name
        self.feature_version = feature_version
        self.kwargs = kwargs

    def __call__(self, f):
        @wraps(f)
        def wrapped(*wrapped_args, **wrapped_kwargs):
            # Which FeatureCheck class to invoke
            FeatureCheckClass = self.feature_check_class
            kwargs, subproject = _get_callee_args(wrapped_args, want_subproject=True)[3:5]
            if subproject is None:
                raise AssertionError('{!r}'.format(wrapped_args))
            for arg in self.kwargs:
                if arg not in kwargs:
                    continue
                name = arg + ' arg in ' + self.feature_name
                FeatureCheckClass(name, self.feature_version).use(subproject)
            return f(*wrapped_args, **wrapped_kwargs)
        return wrapped

class FeatureNewKwargs(FeatureCheckKwargsBase):
    feature_check_class = FeatureNew

class FeatureDeprecatedKwargs(FeatureCheckKwargsBase):
    feature_check_class = FeatureDeprecated


class InterpreterException(mesonlib.MesonException):
    pass

class InvalidCode(InterpreterException):
    pass

class InvalidArguments(InterpreterException):
    pass

class SubdirDoneRequest(BaseException):
    pass

class InterpreterObject:
    def __init__(self):
        self.methods = {}

    def method_call(self, method_name, args, kwargs):
        if method_name in self.methods:
            method = self.methods[method_name]
            if not getattr(method, 'no-args-flattening', False):
                args = flatten(args)
            return method(args, kwargs)
        raise InvalidCode('Unknown method "%s" in object.' % method_name)

class MutableInterpreterObject(InterpreterObject):
    def __init__(self):
        super().__init__()

class Disabler(InterpreterObject):
    def __init__(self):
        super().__init__()
        self.methods.update({'found': self.found_method})

    def found_method(self, args, kwargs):
        return False

def is_disabler(i):
    return isinstance(i, Disabler)

def is_disabled(args, kwargs):
    for i in args:
        if isinstance(i, Disabler):
            return True
    for i in kwargs.values():
        if isinstance(i, Disabler):
            return True
        if isinstance(i, list):
            for j in i:
                if isinstance(j, Disabler):
                    return True
    return False

class InterpreterBase:
    def __init__(self, source_root, subdir):
        self.source_root = source_root
        self.funcs = {}
        self.builtin = {}
        self.subdir = subdir
        self.variables = {}
        self.argument_depth = 0
        self.current_lineno = -1

    def load_root_meson_file(self):
        mesonfile = os.path.join(self.source_root, self.subdir, environment.build_filename)
        if not os.path.isfile(mesonfile):
            raise InvalidArguments('Missing Meson file in %s' % mesonfile)
        with open(mesonfile, encoding='utf8') as mf:
            code = mf.read()
        if code.isspace():
            raise InvalidCode('Builder file is empty.')
        assert(isinstance(code, str))
        try:
            self.ast = mparser.Parser(code, self.subdir).parse()
        except mesonlib.MesonException as me:
            me.file = environment.build_filename
            raise me

    def parse_project(self):
        """
        Parses project() and initializes languages, compilers etc. Do this
        early because we need this before we parse the rest of the AST.
        """
        self.evaluate_codeblock(self.ast, end=1)

    def sanity_check_ast(self):
        if not isinstance(self.ast, mparser.CodeBlockNode):
            raise InvalidCode('AST is of invalid type. Possibly a bug in the parser.')
        if not self.ast.lines:
            raise InvalidCode('No statements in code.')
        first = self.ast.lines[0]
        if not isinstance(first, mparser.FunctionNode) or first.func_name != 'project':
            raise InvalidCode('First statement must be a call to project')

    def run(self):
        # Evaluate everything after the first line, which is project() because
        # we already parsed that in self.parse_project()
        try:
            self.evaluate_codeblock(self.ast, start=1)
        except SubdirDoneRequest:
            pass

    def evaluate_codeblock(self, node, start=0, end=None):
        if node is None:
            return
        if not isinstance(node, mparser.CodeBlockNode):
            e = InvalidCode('Tried to execute a non-codeblock. Possibly a bug in the parser.')
            e.lineno = node.lineno
            e.colno = node.colno
            raise e
        statements = node.lines[start:end]
        i = 0
        while i < len(statements):
            cur = statements[i]
            try:
                self.current_lineno = cur.lineno
                self.evaluate_statement(cur)
            except Exception as e:
                if not hasattr(e, 'lineno'):
                    e.lineno = cur.lineno
                    e.colno = cur.colno
                    e.file = os.path.join(self.subdir, 'meson.build')
                raise e
            i += 1 # In THE FUTURE jump over blocks and stuff.

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
        elif isinstance(cur, mparser.DictNode):
            return self.evaluate_dictstatement(cur)
        elif isinstance(cur, mparser.NumberNode):
            return cur.value
        elif isinstance(cur, mparser.AndNode):
            return self.evaluate_andstatement(cur)
        elif isinstance(cur, mparser.OrNode):
            return self.evaluate_orstatement(cur)
        elif isinstance(cur, mparser.NotNode):
            return self.evaluate_notstatement(cur)
        elif isinstance(cur, mparser.UMinusNode):
            return self.evaluate_uminusstatement(cur)
        elif isinstance(cur, mparser.ArithmeticNode):
            return self.evaluate_arithmeticstatement(cur)
        elif isinstance(cur, mparser.ForeachClauseNode):
            return self.evaluate_foreach(cur)
        elif isinstance(cur, mparser.PlusAssignmentNode):
            return self.evaluate_plusassign(cur)
        elif isinstance(cur, mparser.IndexNode):
            return self.evaluate_indexing(cur)
        elif isinstance(cur, mparser.TernaryNode):
            return self.evaluate_ternary(cur)
        elif self.is_elementary_type(cur):
            return cur
        else:
            raise InvalidCode("Unknown statement.")

    def evaluate_arraystatement(self, cur):
        (arguments, kwargs) = self.reduce_arguments(cur.args)
        if len(kwargs) > 0:
            raise InvalidCode('Keyword arguments are invalid in array construction.')
        return arguments

    @FeatureNew('dict', '0.47.0')
    def evaluate_dictstatement(self, cur):
        (arguments, kwargs) = self.reduce_arguments(cur.args)
        assert (not arguments)
        return kwargs

    def evaluate_notstatement(self, cur):
        v = self.evaluate_statement(cur.value)
        if not isinstance(v, bool):
            raise InterpreterException('Argument to "not" is not a boolean.')
        return not v

    def evaluate_if(self, node):
        assert(isinstance(node, mparser.IfClauseNode))
        for i in node.ifs:
            result = self.evaluate_statement(i.condition)
            if is_disabler(result):
                return result
            if not(isinstance(result, bool)):
                raise InvalidCode('If clause {!r} does not evaluate to true or false.'.format(result))
            if result:
                self.evaluate_codeblock(i.block)
                return
        if not isinstance(node.elseblock, mparser.EmptyNode):
            self.evaluate_codeblock(node.elseblock)

    def validate_comparison_types(self, val1, val2):
        if type(val1) != type(val2):
            return False
        return True

    def evaluate_comparison(self, node):
        val1 = self.evaluate_statement(node.left)
        if is_disabler(val1):
            return val1
        val2 = self.evaluate_statement(node.right)
        if is_disabler(val2):
            return val2
        valid = self.validate_comparison_types(val1, val2)
        # Ordering comparisons of different types isn't allowed since PR #1810
        # (0.41.0).  Since PR #2884 we also warn about equality comparisons of
        # different types, which will one day become an error.
        if not valid and (node.ctype == '==' or node.ctype == '!='):
            mlog.warning('''Trying to compare values of different types ({}, {}) using {}.
The result of this is undefined and will become a hard error in a future Meson release.'''
                         .format(type(val1).__name__, type(val2).__name__, node.ctype), location=node)
        if node.ctype == '==':
            return val1 == val2
        elif node.ctype == '!=':
            return val1 != val2
        elif not valid:
            raise InterpreterException(
                'Values of different types ({}, {}) cannot be compared using {}.'.format(type(val1).__name__,
                                                                                         type(val2).__name__,
                                                                                         node.ctype))
        elif not self.is_elementary_type(val1):
            raise InterpreterException('{} can only be compared for equality.'.format(node.left.value))
        elif not self.is_elementary_type(val2):
            raise InterpreterException('{} can only be compared for equality.'.format(node.right.value))
        elif node.ctype == '<':
            return val1 < val2
        elif node.ctype == '<=':
            return val1 <= val2
        elif node.ctype == '>':
            return val1 > val2
        elif node.ctype == '>=':
            return val1 >= val2
        else:
            raise InvalidCode('You broke my compare eval.')

    def evaluate_andstatement(self, cur):
        l = self.evaluate_statement(cur.left)
        if is_disabler(l):
            return l
        if not isinstance(l, bool):
            raise InterpreterException('First argument to "and" is not a boolean.')
        if not l:
            return False
        r = self.evaluate_statement(cur.right)
        if is_disabler(r):
            return r
        if not isinstance(r, bool):
            raise InterpreterException('Second argument to "and" is not a boolean.')
        return r

    def evaluate_orstatement(self, cur):
        l = self.evaluate_statement(cur.left)
        if is_disabler(l):
            return l
        if not isinstance(l, bool):
            raise InterpreterException('First argument to "or" is not a boolean.')
        if l:
            return True
        r = self.evaluate_statement(cur.right)
        if is_disabler(r):
            return r
        if not isinstance(r, bool):
            raise InterpreterException('Second argument to "or" is not a boolean.')
        return r

    def evaluate_uminusstatement(self, cur):
        v = self.evaluate_statement(cur.value)
        if is_disabler(v):
            return v
        if not isinstance(v, int):
            raise InterpreterException('Argument to negation is not an integer.')
        return -v

    def evaluate_arithmeticstatement(self, cur):
        l = self.evaluate_statement(cur.left)
        if is_disabler(l):
            return l
        r = self.evaluate_statement(cur.right)
        if is_disabler(r):
            return r

        if cur.operation == 'add':
            if isinstance(l, dict) and isinstance(r, dict):
                return {**l, **r}
            try:
                return l + r
            except Exception as e:
                raise InvalidCode('Invalid use of addition: ' + str(e))
        elif cur.operation == 'sub':
            if not isinstance(l, int) or not isinstance(r, int):
                raise InvalidCode('Subtraction works only with integers.')
            return l - r
        elif cur.operation == 'mul':
            if not isinstance(l, int) or not isinstance(r, int):
                raise InvalidCode('Multiplication works only with integers.')
            return l * r
        elif cur.operation == 'div':
            if not isinstance(l, int) or not isinstance(r, int):
                raise InvalidCode('Division works only with integers.')
            return l // r
        elif cur.operation == 'mod':
            if not isinstance(l, int) or not isinstance(r, int):
                raise InvalidCode('Modulo works only with integers.')
            return l % r
        else:
            raise InvalidCode('You broke me.')

    def evaluate_ternary(self, node):
        assert(isinstance(node, mparser.TernaryNode))
        result = self.evaluate_statement(node.condition)
        if is_disabler(result):
            return result
        if not isinstance(result, bool):
            raise InterpreterException('Ternary condition is not boolean.')
        if result:
            return self.evaluate_statement(node.trueblock)
        else:
            return self.evaluate_statement(node.falseblock)

    def evaluate_foreach(self, node):
        assert(isinstance(node, mparser.ForeachClauseNode))
        items = self.evaluate_statement(node.items)

        if isinstance(items, list):
            if len(node.varnames) != 1:
                raise InvalidArguments('Foreach on array does not unpack')
            varname = node.varnames[0].value
            if is_disabler(items):
                return items
            for item in items:
                self.set_variable(varname, item)
                self.evaluate_codeblock(node.block)
        elif isinstance(items, dict):
            if len(node.varnames) != 2:
                raise InvalidArguments('Foreach on dict unpacks key and value')
            if is_disabler(items):
                return items
            for key, value in items.items():
                self.set_variable(node.varnames[0].value, key)
                self.set_variable(node.varnames[1].value, value)
                self.evaluate_codeblock(node.block)
        else:
            raise InvalidArguments('Items of foreach loop must be an array or a dict')

    def evaluate_plusassign(self, node):
        assert(isinstance(node, mparser.PlusAssignmentNode))
        varname = node.var_name
        addition = self.evaluate_statement(node.value)
        if is_disabler(addition):
            self.set_variable(varname, addition)
            return
        # Remember that all variables are immutable. We must always create a
        # full new variable and then assign it.
        old_variable = self.get_variable(varname)
        if isinstance(old_variable, str):
            if not isinstance(addition, str):
                raise InvalidArguments('The += operator requires a string on the right hand side if the variable on the left is a string')
            new_value = old_variable + addition
        elif isinstance(old_variable, int):
            if not isinstance(addition, int):
                raise InvalidArguments('The += operator requires an int on the right hand side if the variable on the left is an int')
            new_value = old_variable + addition
        elif isinstance(old_variable, list):
            if isinstance(addition, list):
                new_value = old_variable + addition
            else:
                new_value = old_variable + [addition]
        elif isinstance(old_variable, dict):
            if not isinstance(addition, dict):
                raise InvalidArguments('The += operator requires a dict on the right hand side if the variable on the left is a dict')
            new_value = {**old_variable, **addition}
        # Add other data types here.
        else:
            raise InvalidArguments('The += operator currently only works with arrays, dicts, strings or ints ')
        self.set_variable(varname, new_value)

    def evaluate_indexing(self, node):
        assert(isinstance(node, mparser.IndexNode))
        iobject = self.evaluate_statement(node.iobject)
        if is_disabler(iobject):
            return iobject
        if not hasattr(iobject, '__getitem__'):
            raise InterpreterException(
                'Tried to index an object that doesn\'t support indexing.')
        index = self.evaluate_statement(node.index)

        if isinstance(iobject, dict):
            if not isinstance(index, str):
                raise InterpreterException('Key is not a string')
            try:
                return iobject[index]
            except KeyError:
                raise InterpreterException('Key %s is not in dict' % index)
        else:
            if not isinstance(index, int):
                raise InterpreterException('Index value is not an integer.')
            try:
                return iobject[index]
            except IndexError:
                raise InterpreterException('Index %d out of bounds of array of size %d.' % (index, len(iobject)))

    def function_call(self, node):
        func_name = node.func_name
        (posargs, kwargs) = self.reduce_arguments(node.args)
        if is_disabled(posargs, kwargs):
            return Disabler()
        if func_name in self.funcs:
            func = self.funcs[func_name]
            if not getattr(func, 'no-args-flattening', False):
                posargs = flatten(posargs)

            return func(node, posargs, kwargs)
        else:
            self.unknown_function_called(func_name)

    def method_call(self, node):
        invokable = node.source_object
        if isinstance(invokable, mparser.IdNode):
            object_name = invokable.value
            obj = self.get_variable(object_name)
        else:
            obj = self.evaluate_statement(invokable)
        method_name = node.name
        args = node.args
        if isinstance(obj, str):
            return self.string_method_call(obj, method_name, args)
        if isinstance(obj, bool):
            return self.bool_method_call(obj, method_name, args)
        if isinstance(obj, int):
            return self.int_method_call(obj, method_name, args)
        if isinstance(obj, list):
            return self.array_method_call(obj, method_name, args)
        if isinstance(obj, dict):
            return self.dict_method_call(obj, method_name, args)
        if isinstance(obj, mesonlib.File):
            raise InvalidArguments('File object "%s" is not callable.' % obj)
        if not isinstance(obj, InterpreterObject):
            raise InvalidArguments('Variable "%s" is not callable.' % object_name)
        (args, kwargs) = self.reduce_arguments(args)
        # Special case. This is the only thing you can do with a disabler
        # object. Every other use immediately returns the disabler object.
        if isinstance(obj, Disabler) and method_name == 'found':
            return False
        if is_disabled(args, kwargs):
            return Disabler()
        if method_name == 'extract_objects':
            self.validate_extraction(obj.held_object)
        return obj.method_call(method_name, args, kwargs)

    def bool_method_call(self, obj, method_name, args):
        (posargs, kwargs) = self.reduce_arguments(args)
        if is_disabled(posargs, kwargs):
            return Disabler()
        if method_name == 'to_string':
            if not posargs:
                if obj:
                    return 'true'
                else:
                    return 'false'
            elif len(posargs) == 2 and isinstance(posargs[0], str) and isinstance(posargs[1], str):
                if obj:
                    return posargs[0]
                else:
                    return posargs[1]
            else:
                raise InterpreterException('bool.to_string() must have either no arguments or exactly two string arguments that signify what values to return for true and false.')
        elif method_name == 'to_int':
            if obj:
                return 1
            else:
                return 0
        else:
            raise InterpreterException('Unknown method "%s" for a boolean.' % method_name)

    def int_method_call(self, obj, method_name, args):
        (posargs, kwargs) = self.reduce_arguments(args)
        if is_disabled(posargs, kwargs):
            return Disabler()
        if method_name == 'is_even':
            if not posargs:
                return obj % 2 == 0
            else:
                raise InterpreterException('int.is_even() must have no arguments.')
        elif method_name == 'is_odd':
            if not posargs:
                return obj % 2 != 0
            else:
                raise InterpreterException('int.is_odd() must have no arguments.')
        elif method_name == 'to_string':
            if not posargs:
                return str(obj)
            else:
                raise InterpreterException('int.to_string() must have no arguments.')
        else:
            raise InterpreterException('Unknown method "%s" for an integer.' % method_name)

    @staticmethod
    def _get_one_string_posarg(posargs, method_name):
        if len(posargs) > 1:
            m = '{}() must have zero or one arguments'
            raise InterpreterException(m.format(method_name))
        elif len(posargs) == 1:
            s = posargs[0]
            if not isinstance(s, str):
                m = '{}() argument must be a string'
                raise InterpreterException(m.format(method_name))
            return s
        return None

    def string_method_call(self, obj, method_name, args):
        (posargs, kwargs) = self.reduce_arguments(args)
        if is_disabled(posargs, kwargs):
            return Disabler()
        if method_name == 'strip':
            s = self._get_one_string_posarg(posargs, 'strip')
            if s is not None:
                return obj.strip(s)
            return obj.strip()
        elif method_name == 'format':
            return self.format_string(obj, args)
        elif method_name == 'to_upper':
            return obj.upper()
        elif method_name == 'to_lower':
            return obj.lower()
        elif method_name == 'underscorify':
            return re.sub(r'[^a-zA-Z0-9]', '_', obj)
        elif method_name == 'split':
            s = self._get_one_string_posarg(posargs, 'split')
            if s is not None:
                return obj.split(s)
            return obj.split()
        elif method_name == 'startswith' or method_name == 'contains' or method_name == 'endswith':
            s = posargs[0]
            if not isinstance(s, str):
                raise InterpreterException('Argument must be a string.')
            if method_name == 'startswith':
                return obj.startswith(s)
            elif method_name == 'contains':
                return obj.find(s) >= 0
            return obj.endswith(s)
        elif method_name == 'to_int':
            try:
                return int(obj)
            except Exception:
                raise InterpreterException('String {!r} cannot be converted to int'.format(obj))
        elif method_name == 'join':
            if len(posargs) != 1:
                raise InterpreterException('Join() takes exactly one argument.')
            strlist = posargs[0]
            check_stringlist(strlist)
            return obj.join(strlist)
        elif method_name == 'version_compare':
            if len(posargs) != 1:
                raise InterpreterException('Version_compare() takes exactly one argument.')
            cmpr = posargs[0]
            if not isinstance(cmpr, str):
                raise InterpreterException('Version_compare() argument must be a string.')
            return mesonlib.version_compare(obj, cmpr)
        raise InterpreterException('Unknown method "%s" for a string.' % method_name)

    def unknown_function_called(self, func_name):
        raise InvalidCode('Unknown function "%s".' % func_name)

    def array_method_call(self, obj, method_name, args):
        (posargs, kwargs) = self.reduce_arguments(args)
        if is_disabled(posargs, kwargs):
            return Disabler()
        if method_name == 'contains':
            return self.check_contains(obj, posargs)
        elif method_name == 'length':
            return len(obj)
        elif method_name == 'get':
            index = posargs[0]
            fallback = None
            if len(posargs) == 2:
                fallback = posargs[1]
            elif len(posargs) > 2:
                m = 'Array method \'get()\' only takes two arguments: the ' \
                    'index and an optional fallback value if the index is ' \
                    'out of range.'
                raise InvalidArguments(m)
            if not isinstance(index, int):
                raise InvalidArguments('Array index must be a number.')
            if index < -len(obj) or index >= len(obj):
                if fallback is None:
                    m = 'Array index {!r} is out of bounds for array of size {!r}.'
                    raise InvalidArguments(m.format(index, len(obj)))
                return fallback
            return obj[index]
        m = 'Arrays do not have a method called {!r}.'
        raise InterpreterException(m.format(method_name))

    def dict_method_call(self, obj, method_name, args):
        (posargs, kwargs) = self.reduce_arguments(args)
        if is_disabled(posargs, kwargs):
            return Disabler()

        if method_name in ('has_key', 'get'):
            if method_name == 'has_key':
                if len(posargs) != 1:
                    raise InterpreterException('has_key() takes exactly one argument.')
            else:
                if len(posargs) not in (1, 2):
                    raise InterpreterException('get() takes one or two arguments.')

            key = posargs[0]
            if not isinstance(key, (str)):
                raise InvalidArguments('Dictionary key must be a string.')

            has_key = key in obj

            if method_name == 'has_key':
                return has_key

            if has_key:
                return obj[key]

            if len(posargs) == 2:
                return posargs[1]

            raise InterpreterException('Key {!r} is not in the dictionary.'.format(key))

        if method_name == 'keys':
            if len(posargs) != 0:
                raise InterpreterException('keys() takes no arguments.')
            return list(obj.keys())

        raise InterpreterException('Dictionaries do not have a method called "%s".' % method_name)

    def reduce_arguments(self, args):
        assert(isinstance(args, mparser.ArgumentNode))
        if args.incorrect_order():
            raise InvalidArguments('All keyword arguments must be after positional arguments.')
        self.argument_depth += 1
        reduced_pos = [self.evaluate_statement(arg) for arg in args.arguments]
        reduced_kw = {}
        for key in args.kwargs.keys():
            if not isinstance(key, str):
                raise InvalidArguments('Keyword argument name is not a string.')
            a = args.kwargs[key]
            reduced_kw[key] = self.evaluate_statement(a)
        self.argument_depth -= 1
        return reduced_pos, reduced_kw

    def assignment(self, node):
        assert(isinstance(node, mparser.AssignmentNode))
        if self.argument_depth != 0:
            raise InvalidArguments('''Tried to assign values inside an argument list.
To specify a keyword argument, use : instead of =.''')
        var_name = node.var_name
        if not isinstance(var_name, str):
            raise InvalidArguments('Tried to assign value to a non-variable.')
        value = self.evaluate_statement(node.value)
        if not self.is_assignable(value):
            raise InvalidCode('Tried to assign an invalid value to variable.')
        # For mutable objects we need to make a copy on assignment
        if isinstance(value, MutableInterpreterObject):
            value = copy.deepcopy(value)
        self.set_variable(var_name, value)
        return None

    def set_variable(self, varname, variable):
        if variable is None:
            raise InvalidCode('Can not assign None to variable.')
        if not isinstance(varname, str):
            raise InvalidCode('First argument to set_variable must be a string.')
        if not self.is_assignable(variable):
            raise InvalidCode('Assigned value not of assignable type.')
        if re.match('[_a-zA-Z][_0-9a-zA-Z]*$', varname) is None:
            raise InvalidCode('Invalid variable name: ' + varname)
        if varname in self.builtin:
            raise InvalidCode('Tried to overwrite internal variable "%s"' % varname)
        self.variables[varname] = variable

    def get_variable(self, varname):
        if varname in self.builtin:
            return self.builtin[varname]
        if varname in self.variables:
            return self.variables[varname]
        raise InvalidCode('Unknown variable "%s".' % varname)

    def is_assignable(self, value):
        return isinstance(value, (InterpreterObject, dependencies.Dependency,
                                  str, int, list, dict, mesonlib.File))

    def is_elementary_type(self, v):
        return isinstance(v, (int, float, str, bool, list))
