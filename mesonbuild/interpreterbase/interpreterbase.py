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

from .. import mparser, mesonlib, mlog
from .. import environment

from .baseobjects import (
    InterpreterObject,
    MesonInterpreterObject,
    MutableInterpreterObject,
    InterpreterObjectTypeVar,
    ObjectHolder,
    RangeHolder,

    TYPE_elementary,
    TYPE_var,
    TYPE_kwargs,
)

from .exceptions import (
    InterpreterException,
    InvalidCode,
    InvalidArguments,
    SubdirDoneRequest,
    ContinueRequest,
    BreakRequest
)

from .decorators import FeatureNew, builtinMethodNoKwargs
from .disabler import Disabler, is_disabled
from .helpers import check_stringlist, default_resolve_key, flatten, resolve_second_level_holders
from ._unholder import _unholder

import os, copy, re
import typing as T

if T.TYPE_CHECKING:
    from ..interpreter import Interpreter

HolderMapType = T.Dict[
    T.Type[mesonlib.HoldableObject],
    # For some reason, this has to be a callable and can't just be ObjectHolder[InterpreterObjectTypeVar]
    T.Callable[[InterpreterObjectTypeVar, 'Interpreter'], ObjectHolder[InterpreterObjectTypeVar]]
]

FunctionType = T.Dict[
    str,
    T.Callable[[mparser.BaseNode, T.List[TYPE_var], T.Dict[str, TYPE_var]], TYPE_var]
]

class MesonVersionString(str):
    pass

class InterpreterBase:
    elementary_types = (int, str, bool, list)

    def __init__(self, source_root: str, subdir: str, subproject: str):
        self.source_root = source_root
        self.funcs: FunctionType = {}
        self.builtin: T.Dict[str, InterpreterObject] = {}
        # Holder maps store a mapping from an HoldableObject to a class ObjectHolder
        self.holder_map: HolderMapType = {}
        self.bound_holder_map: HolderMapType = {}
        self.subdir = subdir
        self.root_subdir = subdir
        self.subproject = subproject
        # TODO: This should actually be more strict: T.Union[TYPE_elementary, InterpreterObject]
        self.variables: T.Dict[str, T.Union[TYPE_var, InterpreterObject]] = {}
        self.argument_depth = 0
        self.current_lineno = -1
        # Current node set during a function call. This can be used as location
        # when printing a warning message during a method call.
        self.current_node = None  # type: mparser.BaseNode
        # This is set to `version_string` when this statement is evaluated:
        # meson.version().compare_version(version_string)
        # If it was part of a if-clause, it is used to temporally override the
        # current meson version target within that if-block.
        self.tmp_meson_version = None # type: T.Optional[str]

    def load_root_meson_file(self) -> None:
        mesonfile = os.path.join(self.source_root, self.subdir, environment.build_filename)
        if not os.path.isfile(mesonfile):
            raise InvalidArguments('Missing Meson file in %s' % mesonfile)
        with open(mesonfile, encoding='utf-8') as mf:
            code = mf.read()
        if code.isspace():
            raise InvalidCode('Builder file is empty.')
        assert(isinstance(code, str))
        try:
            self.ast = mparser.Parser(code, mesonfile).parse()
        except mesonlib.MesonException as me:
            me.file = mesonfile
            raise me

    def join_path_strings(self, args: T.Sequence[str]) -> str:
        return os.path.join(*args).replace('\\', '/')

    def parse_project(self) -> None:
        """
        Parses project() and initializes languages, compilers etc. Do this
        early because we need this before we parse the rest of the AST.
        """
        self.evaluate_codeblock(self.ast, end=1)

    def sanity_check_ast(self) -> None:
        if not isinstance(self.ast, mparser.CodeBlockNode):
            raise InvalidCode('AST is of invalid type. Possibly a bug in the parser.')
        if not self.ast.lines:
            raise InvalidCode('No statements in code.')
        first = self.ast.lines[0]
        if not isinstance(first, mparser.FunctionNode) or first.func_name != 'project':
            raise InvalidCode('First statement must be a call to project')

    def run(self) -> None:
        # Evaluate everything after the first line, which is project() because
        # we already parsed that in self.parse_project()
        try:
            self.evaluate_codeblock(self.ast, start=1)
        except SubdirDoneRequest:
            pass

    def evaluate_codeblock(self, node: mparser.CodeBlockNode, start: int = 0, end: T.Optional[int] = None) -> None:
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
                if getattr(e, 'lineno', None) is None:
                    # We are doing the equivalent to setattr here and mypy does not like it
                    e.lineno = cur.lineno                                                             # type: ignore
                    e.colno = cur.colno                                                               # type: ignore
                    e.file = os.path.join(self.source_root, self.subdir, environment.build_filename)  # type: ignore
                raise e
            i += 1 # In THE FUTURE jump over blocks and stuff.

    def evaluate_statement(self, cur: mparser.BaseNode) -> T.Optional[T.Union[TYPE_var, InterpreterObject]]:
        self.current_node = cur
        if isinstance(cur, mparser.FunctionNode):
            return self.function_call(cur)
        elif isinstance(cur, mparser.AssignmentNode):
            self.assignment(cur)
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
            self.evaluate_foreach(cur)
        elif isinstance(cur, mparser.PlusAssignmentNode):
            self.evaluate_plusassign(cur)
        elif isinstance(cur, mparser.IndexNode):
            return self.evaluate_indexing(cur)
        elif isinstance(cur, mparser.TernaryNode):
            return self.evaluate_ternary(cur)
        elif isinstance(cur, mparser.FormatStringNode):
            return self.evaluate_fstring(cur)
        elif isinstance(cur, mparser.ContinueNode):
            raise ContinueRequest()
        elif isinstance(cur, mparser.BreakNode):
            raise BreakRequest()
        elif isinstance(cur, self.elementary_types):
            return cur
        else:
            raise InvalidCode("Unknown statement.")
        return None

    def evaluate_arraystatement(self, cur: mparser.ArrayNode) -> T.List[T.Union[TYPE_var, InterpreterObject]]:
        (arguments, kwargs) = self.reduce_arguments(cur.args)
        if len(kwargs) > 0:
            raise InvalidCode('Keyword arguments are invalid in array construction.')
        return arguments

    @FeatureNew('dict', '0.47.0')
    def evaluate_dictstatement(self, cur: mparser.DictNode) -> T.Union[TYPE_var, InterpreterObject]:
        def resolve_key(key: mparser.BaseNode) -> str:
            if not isinstance(key, mparser.StringNode):
                FeatureNew.single_use('Dictionary entry using non literal key', '0.53.0', self.subproject)
            str_key = self.evaluate_statement(key)
            if not isinstance(str_key, str):
                raise InvalidArguments('Key must be a string')
            return str_key
        arguments, kwargs = self.reduce_arguments(cur.args, key_resolver=resolve_key, duplicate_key_error='Duplicate dictionary key: {}')
        assert not arguments
        return kwargs

    def evaluate_notstatement(self, cur: mparser.NotNode) -> T.Union[bool, Disabler]:
        v = self.evaluate_statement(cur.value)
        if isinstance(v, Disabler):
            return v
        if not isinstance(v, bool):
            raise InterpreterException('Argument to "not" is not a boolean.')
        return not v

    def evaluate_if(self, node: mparser.IfClauseNode) -> T.Optional[Disabler]:
        assert(isinstance(node, mparser.IfClauseNode))
        for i in node.ifs:
            # Reset self.tmp_meson_version to know if it gets set during this
            # statement evaluation.
            self.tmp_meson_version = None
            result = self.evaluate_statement(i.condition)
            if isinstance(result, Disabler):
                return result
            if not(isinstance(result, bool)):
                raise InvalidCode(f'If clause {result!r} does not evaluate to true or false.')
            if result:
                prev_meson_version = mesonlib.project_meson_versions[self.subproject]
                if self.tmp_meson_version:
                    mesonlib.project_meson_versions[self.subproject] = self.tmp_meson_version
                try:
                    self.evaluate_codeblock(i.block)
                finally:
                    mesonlib.project_meson_versions[self.subproject] = prev_meson_version
                return None
        if not isinstance(node.elseblock, mparser.EmptyNode):
            self.evaluate_codeblock(node.elseblock)
        return None

    def validate_comparison_types(self, val1: T.Any, val2: T.Any) -> bool:
        if type(val1) != type(val2):
            return False
        return True

    def evaluate_in(self, val1: T.Any, val2: T.Any) -> bool:
        if not isinstance(val1, (str, int, float, mesonlib.HoldableObject)):
            raise InvalidArguments('lvalue of "in" operator must be a string, integer, float, or object')
        if not isinstance(val2, (list, dict)):
            raise InvalidArguments('rvalue of "in" operator must be an array or a dict')
        return val1 in val2

    def evaluate_comparison(self, node: mparser.ComparisonNode) -> T.Union[bool, Disabler]:
        val1 = self.evaluate_statement(node.left)
        if isinstance(val1, Disabler):
            return val1
        val2 = self.evaluate_statement(node.right)
        if isinstance(val2, Disabler):
            return val2
        # Do not compare the ObjectHolders but the actual held objects
        val1 = _unholder(val1)
        val2 = _unholder(val2)
        if node.ctype == 'in':
            return self.evaluate_in(val1, val2)
        elif node.ctype == 'notin':
            return not self.evaluate_in(val1, val2)
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
        elif not isinstance(val1, self.elementary_types):
            raise InterpreterException('{} can only be compared for equality.'.format(getattr(node.left, 'value', '<ERROR>')))
        elif not isinstance(val2, self.elementary_types):
            raise InterpreterException('{} can only be compared for equality.'.format(getattr(node.right, 'value', '<ERROR>')))
        # Use type: ignore because mypy will complain that we are comparing two Unions,
        # but we actually guarantee earlier that both types are the same
        elif node.ctype == '<':
            return val1 < val2   # type: ignore
        elif node.ctype == '<=':
            return val1 <= val2  # type: ignore
        elif node.ctype == '>':
            return val1 > val2   # type: ignore
        elif node.ctype == '>=':
            return val1 >= val2  # type: ignore
        else:
            raise InvalidCode('You broke my compare eval.')

    def evaluate_andstatement(self, cur: mparser.AndNode) -> T.Union[bool, Disabler]:
        l = self.evaluate_statement(cur.left)
        if isinstance(l, Disabler):
            return l
        if not isinstance(l, bool):
            raise InterpreterException('First argument to "and" is not a boolean.')
        if not l:
            return False
        r = self.evaluate_statement(cur.right)
        if isinstance(r, Disabler):
            return r
        if not isinstance(r, bool):
            raise InterpreterException('Second argument to "and" is not a boolean.')
        return r

    def evaluate_orstatement(self, cur: mparser.OrNode) -> T.Union[bool, Disabler]:
        l = self.evaluate_statement(cur.left)
        if isinstance(l, Disabler):
            return l
        if not isinstance(l, bool):
            raise InterpreterException('First argument to "or" is not a boolean.')
        if l:
            return True
        r = self.evaluate_statement(cur.right)
        if isinstance(r, Disabler):
            return r
        if not isinstance(r, bool):
            raise InterpreterException('Second argument to "or" is not a boolean.')
        return r

    def evaluate_uminusstatement(self, cur: mparser.UMinusNode) -> T.Union[int, Disabler]:
        v = self.evaluate_statement(cur.value)
        if isinstance(v, Disabler):
            return v
        if not isinstance(v, int):
            raise InterpreterException('Argument to negation is not an integer.')
        return -v

    @FeatureNew('/ with string arguments', '0.49.0')
    def evaluate_path_join(self, l: str, r: str) -> str:
        if not isinstance(l, str):
            raise InvalidCode('The division operator can only append to a string.')
        if not isinstance(r, str):
            raise InvalidCode('The division operator can only append a string.')
        return self.join_path_strings((l, r))

    def evaluate_division(self, l: T.Any, r: T.Any) -> T.Union[int, str]:
        if isinstance(l, str) or isinstance(r, str):
            return self.evaluate_path_join(l, r)
        if isinstance(l, int) and isinstance(r, int):
            if r == 0:
                raise InvalidCode('Division by zero.')
            return l // r
        raise InvalidCode('Division works only with strings or integers.')

    def evaluate_arithmeticstatement(self, cur: mparser.ArithmeticNode) -> T.Union[int, str, dict, list, Disabler]:
        l = self.evaluate_statement(cur.left)
        if isinstance(l, Disabler):
            return l
        r = self.evaluate_statement(cur.right)
        if isinstance(r, Disabler):
            return r

        if cur.operation == 'add':
            if isinstance(l, dict) and isinstance(r, dict):
                return {**l, **r}
            try:
                # MyPy error due to handling two Unions (we are catching all exceptions anyway)
                return l + r  # type: ignore
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
            return self.evaluate_division(l, r)
        elif cur.operation == 'mod':
            if not isinstance(l, int) or not isinstance(r, int):
                raise InvalidCode('Modulo works only with integers.')
            return l % r
        else:
            raise InvalidCode('You broke me.')

    def evaluate_ternary(self, node: mparser.TernaryNode) -> T.Union[TYPE_var, InterpreterObject]:
        assert(isinstance(node, mparser.TernaryNode))
        result = self.evaluate_statement(node.condition)
        if isinstance(result, Disabler):
            return result
        if not isinstance(result, bool):
            raise InterpreterException('Ternary condition is not boolean.')
        if result:
            return self.evaluate_statement(node.trueblock)
        else:
            return self.evaluate_statement(node.falseblock)

    @FeatureNew('format strings', '0.58.0')
    def evaluate_fstring(self, node: mparser.FormatStringNode) -> TYPE_var:
        assert(isinstance(node, mparser.FormatStringNode))

        def replace(match: T.Match[str]) -> str:
            var = str(match.group(1))
            try:
                val = self.variables[var]
                if not isinstance(val, (str, int, float, bool)):
                    raise InvalidCode(f'Identifier "{var}" does not name a formattable variable ' +
                        '(has to be an integer, a string, a floating point number or a boolean).')

                return str(val)
            except KeyError:
                raise InvalidCode(f'Identifier "{var}" does not name a variable.')

        return re.sub(r'@([_a-zA-Z][_0-9a-zA-Z]*)@', replace, node.value)

    def evaluate_foreach(self, node: mparser.ForeachClauseNode) -> None:
        assert(isinstance(node, mparser.ForeachClauseNode))
        items = self.evaluate_statement(node.items)

        if isinstance(items, (list, RangeHolder)):
            if len(node.varnames) != 1:
                raise InvalidArguments('Foreach on array does not unpack')
            varname = node.varnames[0]
            for item in items:
                self.set_variable(varname, item)
                try:
                    self.evaluate_codeblock(node.block)
                except ContinueRequest:
                    continue
                except BreakRequest:
                    break
        elif isinstance(items, dict):
            if len(node.varnames) != 2:
                raise InvalidArguments('Foreach on dict unpacks key and value')
            for key, value in sorted(items.items()):
                self.set_variable(node.varnames[0], key)
                self.set_variable(node.varnames[1], value)
                try:
                    self.evaluate_codeblock(node.block)
                except ContinueRequest:
                    continue
                except BreakRequest:
                    break
        else:
            raise InvalidArguments('Items of foreach loop must be an array or a dict')

    def evaluate_plusassign(self, node: mparser.PlusAssignmentNode) -> None:
        assert(isinstance(node, mparser.PlusAssignmentNode))
        varname = node.var_name
        addition = self.evaluate_statement(node.value)

        # Remember that all variables are immutable. We must always create a
        # full new variable and then assign it.
        old_variable = self.get_variable(varname)
        new_value = None  # type: T.Union[str, int, float, bool, dict, list]
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
            raise InvalidArguments('The += operator currently only works with arrays, dicts, strings or ints')
        self.set_variable(varname, new_value)

    def evaluate_indexing(self, node: mparser.IndexNode) -> T.Union[TYPE_elementary, InterpreterObject]:
        assert(isinstance(node, mparser.IndexNode))
        iobject = self.evaluate_statement(node.iobject)
        if isinstance(iobject, Disabler):
            return iobject
        if not hasattr(iobject, '__getitem__'):
            raise InterpreterException(
                'Tried to index an object that doesn\'t support indexing.')
        index = self.evaluate_statement(node.index)

        if isinstance(iobject, dict):
            if not isinstance(index, str):
                raise InterpreterException('Key is not a string')
            try:
                # The cast is required because we don't have recursive types...
                return T.cast(T.Union[TYPE_elementary, InterpreterObject], iobject[index])
            except KeyError:
                raise InterpreterException('Key %s is not in dict' % index)
        else:
            if not isinstance(index, int):
                raise InterpreterException('Index value is not an integer.')
            try:
                # Ignore the MyPy error, since we don't know all indexable types here
                # and we handle non indexable types with an exception
                # TODO maybe find a better solution
                res = iobject[index]  # type: ignore
                # Only holderify if we are dealing with `InterpreterObject`, since raw
                # lists already store ObjectHolders
                if isinstance(iobject, InterpreterObject):
                    return self._holderify(res)
                else:
                    return res
            except IndexError:
                # We are already checking for the existence of __getitem__, so this should be save
                raise InterpreterException('Index %d out of bounds of array of size %d.' % (index, len(iobject)))  # type: ignore

    def function_call(self, node: mparser.FunctionNode) -> T.Optional[T.Union[TYPE_elementary, InterpreterObject]]:
        func_name = node.func_name
        (h_posargs, h_kwargs) = self.reduce_arguments(node.args)
        (posargs, kwargs) = self._unholder_args(h_posargs, h_kwargs)
        if is_disabled(posargs, kwargs) and func_name not in {'get_variable', 'set_variable', 'is_disabler'}:
            return Disabler()
        if func_name in self.funcs:
            func = self.funcs[func_name]
            func_args = posargs
            if not getattr(func, 'no-args-flattening', False):
                func_args = flatten(posargs)
            if not getattr(func, 'no-second-level-holder-flattening', False):
                func_args, kwargs = resolve_second_level_holders(func_args, kwargs)
            res = func(node, func_args, kwargs)
            return self._holderify(res)
        else:
            self.unknown_function_called(func_name)
            return None

    def method_call(self, node: mparser.MethodNode) -> T.Optional[T.Union[TYPE_var, InterpreterObject]]:
        invokable = node.source_object
        obj: T.Union[TYPE_var, InterpreterObject]
        if isinstance(invokable, mparser.IdNode):
            object_name = invokable.value
            obj = self.get_variable(object_name)
        else:
            obj = self.evaluate_statement(invokable)
        method_name = node.name
        (h_args, h_kwargs) = self.reduce_arguments(node.args)
        (args, kwargs) = self._unholder_args(h_args, h_kwargs)
        if is_disabled(args, kwargs):
            return Disabler()
        if isinstance(obj, str):
            return self.string_method_call(obj, method_name, args, kwargs)
        if isinstance(obj, bool):
            return self.bool_method_call(obj, method_name, args, kwargs)
        if isinstance(obj, int):
            return self.int_method_call(obj, method_name, args, kwargs)
        if isinstance(obj, list):
            return self.array_method_call(obj, method_name, args, kwargs)
        if isinstance(obj, dict):
            return self.dict_method_call(obj, method_name, args, kwargs)
        if not isinstance(obj, InterpreterObject):
            raise InvalidArguments('Variable "%s" is not callable.' % object_name)
        # Special case. This is the only thing you can do with a disabler
        # object. Every other use immediately returns the disabler object.
        if isinstance(obj, Disabler):
            if method_name == 'found':
                return False
            else:
                return Disabler()
        # TODO: InterpreterBase **really** shouldn't be in charge of checking this
        if method_name == 'extract_objects':
            if not isinstance(obj, ObjectHolder):
                raise InvalidArguments(f'Invalid operation "extract_objects" on variable "{object_name}" of type {type(obj).__name__}')
            self.validate_extraction(obj.held_object)
        obj.current_node = node
        return self._holderify(obj.method_call(method_name, args, kwargs))

    def _holderify(self, res: T.Union[TYPE_var, InterpreterObject, None]) -> T.Union[TYPE_elementary, InterpreterObject]:
        if res is None:
            return None
        if isinstance(res, (int, bool, str)):
            return res
        elif isinstance(res, list):
            return [self._holderify(x) for x in res]
        elif isinstance(res, dict):
            return {k: self._holderify(v) for k, v in res.items()}
        elif isinstance(res, mesonlib.HoldableObject):
            # Always check for an exact match first.
            cls = self.holder_map.get(type(res), None)
            if cls is not None:
                # Casts to Interpreter are required here since an assertion would
                # not work for the `ast` module.
                return cls(res, T.cast('Interpreter', self))
            # Try the boundary types next.
            for typ, cls in self.bound_holder_map.items():
                if isinstance(res, typ):
                    return cls(res, T.cast('Interpreter', self))
            raise mesonlib.MesonBugException(f'Object {res} of type {type(res).__name__} is neither in self.holder_map nor self.bound_holder_map.')
        elif isinstance(res, ObjectHolder):
            raise mesonlib.MesonBugException(f'Returned object {res} of type {type(res).__name__} is an object holder.')
        elif isinstance(res, MesonInterpreterObject):
            return res
        raise mesonlib.MesonBugException(f'Unknown returned object {res} of type {type(res).__name__} in the parameters.')

    def _unholder_args(self,
                       args: T.List[T.Union[TYPE_var, InterpreterObject]],
                       kwargs: T.Dict[str, T.Union[TYPE_var, InterpreterObject]]) -> T.Tuple[T.List[TYPE_var], TYPE_kwargs]:
        return [_unholder(x) for x in args], {k: _unholder(v) for k, v in kwargs.items()}

    @builtinMethodNoKwargs
    def bool_method_call(self, obj: bool, method_name: str, posargs: T.List[TYPE_var], kwargs: TYPE_kwargs) -> T.Union[str, int]:
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

    @builtinMethodNoKwargs
    def int_method_call(self, obj: int, method_name: str, posargs: T.List[TYPE_var], kwargs: TYPE_kwargs) -> T.Union[str, bool]:
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
    def _get_one_string_posarg(posargs: T.List[TYPE_var], method_name: str) -> str:
        if len(posargs) > 1:
            raise InterpreterException(f'{method_name}() must have zero or one arguments')
        elif len(posargs) == 1:
            s = posargs[0]
            if not isinstance(s, str):
                raise InterpreterException(f'{method_name}() argument must be a string')
            return s
        return None

    @builtinMethodNoKwargs
    def string_method_call(self, obj: str, method_name: str, posargs: T.List[TYPE_var], kwargs: TYPE_kwargs) -> T.Union[str, int, bool, T.List[str]]:
        if method_name == 'strip':
            s1 = self._get_one_string_posarg(posargs, 'strip')
            if s1 is not None:
                return obj.strip(s1)
            return obj.strip()
        elif method_name == 'format':
            return self.format_string(obj, posargs)
        elif method_name == 'to_upper':
            return obj.upper()
        elif method_name == 'to_lower':
            return obj.lower()
        elif method_name == 'underscorify':
            return re.sub(r'[^a-zA-Z0-9]', '_', obj)
        elif method_name == 'split':
            s2 = self._get_one_string_posarg(posargs, 'split')
            if s2 is not None:
                return obj.split(s2)
            return obj.split()
        elif method_name == 'startswith' or method_name == 'contains' or method_name == 'endswith':
            s3 = posargs[0]
            if not isinstance(s3, str):
                raise InterpreterException('Argument must be a string.')
            if method_name == 'startswith':
                return obj.startswith(s3)
            elif method_name == 'contains':
                return obj.find(s3) >= 0
            return obj.endswith(s3)
        elif method_name == 'to_int':
            try:
                return int(obj)
            except Exception:
                raise InterpreterException(f'String {obj!r} cannot be converted to int')
        elif method_name == 'join':
            if len(posargs) != 1:
                raise InterpreterException('Join() takes exactly one argument.')
            strlist = posargs[0]
            check_stringlist(strlist)
            assert isinstance(strlist, list)  # Required for mypy
            return obj.join(strlist)
        elif method_name == 'version_compare':
            if len(posargs) != 1:
                raise InterpreterException('Version_compare() takes exactly one argument.')
            cmpr = posargs[0]
            if not isinstance(cmpr, str):
                raise InterpreterException('Version_compare() argument must be a string.')
            if isinstance(obj, MesonVersionString):
                self.tmp_meson_version = cmpr
            return mesonlib.version_compare(obj, cmpr)
        elif method_name == 'substring':
            if len(posargs) > 2:
                raise InterpreterException('substring() takes maximum two arguments.')
            start = 0
            end = len(obj)
            if len (posargs) > 0:
                if not isinstance(posargs[0], int):
                    raise InterpreterException('substring() argument must be an int')
                start = posargs[0]
            if len (posargs) > 1:
                if not isinstance(posargs[1], int):
                    raise InterpreterException('substring() argument must be an int')
                end = posargs[1]
            return obj[start:end]
        elif method_name == 'replace':
            FeatureNew.single_use('str.replace', '0.58.0', self.subproject)
            if len(posargs) != 2:
                raise InterpreterException('replace() takes exactly two arguments.')
            if not isinstance(posargs[0], str) or not isinstance(posargs[1], str):
                raise InterpreterException('replace() requires that both arguments be strings')
            return obj.replace(posargs[0], posargs[1])
        raise InterpreterException('Unknown method "%s" for a string.' % method_name)

    def format_string(self, templ: str, args: T.List[TYPE_var]) -> str:
        arg_strings = []
        for arg in args:
            if isinstance(arg, mparser.BaseNode):
                arg = self.evaluate_statement(arg)
            if isinstance(arg, bool): # Python boolean is upper case.
                arg = str(arg).lower()
            arg_strings.append(str(arg))

        def arg_replace(match: T.Match[str]) -> str:
            idx = int(match.group(1))
            if idx >= len(arg_strings):
                raise InterpreterException(f'Format placeholder @{idx}@ out of range.')
            return arg_strings[idx]

        return re.sub(r'@(\d+)@', arg_replace, templ)

    def unknown_function_called(self, func_name: str) -> None:
        raise InvalidCode('Unknown function "%s".' % func_name)

    @builtinMethodNoKwargs
    def array_method_call(self,
                          obj: T.List[T.Union[TYPE_elementary, InterpreterObject]],
                          method_name: str,
                          posargs: T.List[TYPE_var],
                          kwargs: TYPE_kwargs) -> T.Union[TYPE_var, InterpreterObject]:
        if method_name == 'contains':
            def check_contains(el: list) -> bool:
                if len(posargs) != 1:
                    raise InterpreterException('Contains method takes exactly one argument.')
                item = posargs[0]
                for element in el:
                    if isinstance(element, list):
                        found = check_contains(element)
                        if found:
                            return True
                    if element == item:
                        return True
                return False
            return check_contains(obj)
        elif method_name == 'length':
            return len(obj)
        elif method_name == 'get':
            index = posargs[0]
            fallback = None
            if len(posargs) == 2:
                fallback = self._holderify(posargs[1])
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
                if isinstance(fallback, mparser.BaseNode):
                    return self.evaluate_statement(fallback)
                return fallback
            return obj[index]
        raise InterpreterException(f'Arrays do not have a method called {method_name!r}.')

    @builtinMethodNoKwargs
    def dict_method_call(self,
                         obj: T.Dict[str, T.Union[TYPE_elementary, InterpreterObject]],
                         method_name: str,
                         posargs: T.List[TYPE_var],
                         kwargs: TYPE_kwargs) -> T.Union[TYPE_var, InterpreterObject]:
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
                fallback = self._holderify(posargs[1])
                if isinstance(fallback, mparser.BaseNode):
                    return self.evaluate_statement(fallback)
                return fallback

            raise InterpreterException(f'Key {key!r} is not in the dictionary.')

        if method_name == 'keys':
            if len(posargs) != 0:
                raise InterpreterException('keys() takes no arguments.')
            return sorted(obj.keys())

        raise InterpreterException('Dictionaries do not have a method called "%s".' % method_name)

    def reduce_arguments(
                self,
                args: mparser.ArgumentNode,
                key_resolver: T.Callable[[mparser.BaseNode], str] = default_resolve_key,
                duplicate_key_error: T.Optional[str] = None,
            ) -> T.Tuple[
                T.List[T.Union[TYPE_var, InterpreterObject]],
                T.Dict[str, T.Union[TYPE_var, InterpreterObject]]
            ]:
        assert(isinstance(args, mparser.ArgumentNode))
        if args.incorrect_order():
            raise InvalidArguments('All keyword arguments must be after positional arguments.')
        self.argument_depth += 1
        reduced_pos: T.List[T.Union[TYPE_var, InterpreterObject]] = [self.evaluate_statement(arg) for arg in args.arguments]
        reduced_kw: T.Dict[str, T.Union[TYPE_var, InterpreterObject]] = {}
        for key, val in args.kwargs.items():
            reduced_key = key_resolver(key)
            assert isinstance(val, mparser.BaseNode)
            reduced_val = self.evaluate_statement(val)
            if duplicate_key_error and reduced_key in reduced_kw:
                raise InvalidArguments(duplicate_key_error.format(reduced_key))
            reduced_kw[reduced_key] = reduced_val
        self.argument_depth -= 1
        final_kw = self.expand_default_kwargs(reduced_kw)
        return reduced_pos, final_kw

    def expand_default_kwargs(self, kwargs: T.Dict[str, T.Union[TYPE_var, InterpreterObject]]) -> T.Dict[str, T.Union[TYPE_var, InterpreterObject]]:
        if 'kwargs' not in kwargs:
            return kwargs
        to_expand = kwargs.pop('kwargs')
        if not isinstance(to_expand, dict):
            raise InterpreterException('Value of "kwargs" must be dictionary.')
        if 'kwargs' in to_expand:
            raise InterpreterException('Kwargs argument must not contain a "kwargs" entry. Points for thinking meta, though. :P')
        for k, v in to_expand.items():
            if k in kwargs:
                raise InterpreterException(f'Entry "{k}" defined both as a keyword argument and in a "kwarg" entry.')
            kwargs[k] = v
        return kwargs

    def assignment(self, node: mparser.AssignmentNode) -> None:
        assert(isinstance(node, mparser.AssignmentNode))
        if self.argument_depth != 0:
            raise InvalidArguments('''Tried to assign values inside an argument list.
To specify a keyword argument, use : instead of =.''')
        var_name = node.var_name
        if not isinstance(var_name, str):
            raise InvalidArguments('Tried to assign value to a non-variable.')
        value = self.evaluate_statement(node.value)
        if not self.is_assignable(value):
            raise InvalidCode(f'Tried to assign the invalid value "{value}" of type {type(value).__name__} to variable.')
        # For mutable objects we need to make a copy on assignment
        if isinstance(value, MutableInterpreterObject):
            value = copy.deepcopy(value)
        self.set_variable(var_name, value)
        return None

    def set_variable(self, varname: str, variable: T.Union[TYPE_var, InterpreterObject], *, holderify: bool = False) -> None:
        if variable is None:
            raise InvalidCode('Can not assign None to variable.')
        if holderify:
            variable = self._holderify(variable)
        else:
            # Ensure that we are never storing a HoldableObject
            def check(x: T.Union[TYPE_var, InterpreterObject]) -> None:
                if isinstance(x, mesonlib.HoldableObject):
                    raise mesonlib.MesonBugException(f'set_variable in InterpreterBase called with a HoldableObject {x} of type {type(x).__name__}')
                elif isinstance(x, list):
                    for y in x:
                        check(y)
                elif isinstance(x, dict):
                    for v in x.values():
                        check(v)
            check(variable)
        if not isinstance(varname, str):
            raise InvalidCode('First argument to set_variable must be a string.')
        if not self.is_assignable(variable):
            raise InvalidCode(f'Assigned value "{variable}" of type {type(variable).__name__} is not an assignable type.')
        if re.match('[_a-zA-Z][_0-9a-zA-Z]*$', varname) is None:
            raise InvalidCode('Invalid variable name: ' + varname)
        if varname in self.builtin:
            raise InvalidCode('Tried to overwrite internal variable "%s"' % varname)
        self.variables[varname] = variable

    def get_variable(self, varname: str) -> T.Union[TYPE_var, InterpreterObject]:
        if varname in self.builtin:
            return self.builtin[varname]
        if varname in self.variables:
            return self.variables[varname]
        raise InvalidCode('Unknown variable "%s".' % varname)

    def is_assignable(self, value: T.Any) -> bool:
        return isinstance(value, (InterpreterObject, str, int, list, dict))

    def validate_extraction(self, buildtarget: mesonlib.HoldableObject) -> None:
        raise InterpreterException('validate_extraction is not implemented in this context (please file a bug)')
