# SPDX-License-Identifier: Apache-2.0
# Copyright 2021 The Meson development team
from __future__ import annotations

import re
import os

import typing as T

from ... import mlog
from ...mesonlib import version_check_to_range, version_compare_many, underscorify
from ...interpreterbase import (
    InterpreterObject,
    MesonOperator,
    ObjectHolder,
    FeatureNew,
    typed_operator,
    noArgsFlattening,
    noPosargs,
    InvalidArguments,
    FeatureBroken,
    TypedArgs,
    stringifyUserArguments,
)
from ...interpreter.type_checking import (
    STR_PARG, STR_OARG, INT_OARG, STR_VARG, STR_VARG_1, OBJ_VARG,
)


if T.TYPE_CHECKING:
    from ...interpreterbase import TYPE_var, TYPE_kwargs

class StringHolder(ObjectHolder[str]):
    TRIVIAL_OPERATORS = {
        # Arithmetic
        MesonOperator.PLUS: (str, lambda obj, x: obj.held_object + x),

        # Comparison
        MesonOperator.EQUALS: (str, lambda obj, x: obj.held_object == x),
        MesonOperator.NOT_EQUALS: (str, lambda obj, x: obj.held_object != x),
        MesonOperator.GREATER: (str, lambda obj, x: obj.held_object > x),
        MesonOperator.LESS: (str, lambda obj, x: obj.held_object < x),
        MesonOperator.GREATER_EQUALS: (str, lambda obj, x: obj.held_object >= x),
        MesonOperator.LESS_EQUALS: (str, lambda obj, x: obj.held_object <= x),
    }

    def display_name(self) -> str:
        return 'str'

    @TypedArgs('str.contains', pos_types=[STR_PARG])
    @InterpreterObject.method('contains')
    def contains_method(self, args: T.Tuple[str], kwargs: TYPE_kwargs) -> bool:
        return self.held_object.find(args[0]) >= 0

    @TypedArgs('str.startswith', pos_types=[STR_PARG])
    @InterpreterObject.method('startswith')
    def startswith_method(self, args: T.Tuple[str], kwargs: TYPE_kwargs) -> bool:
        return self.held_object.startswith(args[0])

    @TypedArgs('str.endswith', pos_types=[STR_PARG])
    @InterpreterObject.method('endswith')
    def endswith_method(self, args: T.Tuple[str], kwargs: TYPE_kwargs) -> bool:
        return self.held_object.endswith(args[0])

    @noArgsFlattening
    @TypedArgs('str.format', var_types=OBJ_VARG)
    @InterpreterObject.method('format')
    def format_method(self, args: T.Tuple[T.List[TYPE_var]], kwargs: TYPE_kwargs) -> str:
        arg_strings: T.List[str] = []
        for arg in args[0]:
            try:
                arg_strings.append(stringifyUserArguments(arg, self.subproject))
            except InvalidArguments as e:
                FeatureBroken.single_use(f'str.format: {str(e)}', '1.3.0', self.subproject, location=self.current_node)
                arg_strings.append(str(arg))

        def arg_replace(match: T.Match[str]) -> str:
            idx = int(match.group(1))
            if idx >= len(arg_strings):
                raise InvalidArguments(f'Format placeholder @{idx}@ out of range.')
            return arg_strings[idx]

        return re.sub(r'@(\d+)@', arg_replace, self.held_object)

    @TypedArgs('str.splitlines')
    @noPosargs
    @FeatureNew('str.splitlines', '1.2.0')
    @InterpreterObject.method('splitlines')
    def splitlines_method(self, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> T.List[str]:
        return self.held_object.splitlines()

    @TypedArgs('str.join', var_types=STR_VARG)
    @InterpreterObject.method('join')
    def join_method(self, args: T.Tuple[T.List[str]], kwargs: TYPE_kwargs) -> str:
        return self.held_object.join(args[0])

    @TypedArgs('str.replace', pos_types=[STR_PARG, STR_PARG])
    @FeatureNew('str.replace', '0.58.0')
    @InterpreterObject.method('replace')
    def replace_method(self, args: T.Tuple[str, str], kwargs: TYPE_kwargs) -> str:
        return self.held_object.replace(args[0], args[1])

    @TypedArgs('str.split', opt_types=[STR_OARG.evolve(validator=lambda x: 'delimiter must not be an empty string' if not x else None)])
    @InterpreterObject.method('split')
    def split_method(self, args: T.Tuple[T.Optional[str]], kwargs: TYPE_kwargs) -> T.List[str]:
        delimiter = args[0]
        return self.held_object.split(delimiter)

    @TypedArgs('str.strip', opt_types=[STR_OARG.evolve(since='0.43.0')])
    @InterpreterObject.method('strip')
    def strip_method(self, args: T.Tuple[T.Optional[str]], kwargs: TYPE_kwargs) -> str:
        return self.held_object.strip(args[0])

    @TypedArgs('str.substring', opt_types=[INT_OARG.evolve(default=0), INT_OARG])
    @FeatureNew('str.substring', '0.56.0')
    @InterpreterObject.method('substring')
    def substring_method(self, args: T.Tuple[int, T.Optional[int]], kwargs: TYPE_kwargs) -> str:
        start = args[0]
        end = args[1] if args[1] is not None else len(self.held_object)
        return self.held_object[start:end]

    @TypedArgs('str.to_int')
    @noPosargs
    @InterpreterObject.method('to_int')
    def to_int_method(self, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> int:
        try:
            s = self.held_object.strip()
            try:
                # For backward compatibility, try to parse the string as a decimal
                # integer first. This is to allow leading zeros which are disallowed
                # when determining the integer base from the string prefix.
                return int(s)
            except ValueError:
                return int(s, base=0)
        except ValueError:
            raise InvalidArguments(f'String {self.held_object!r} cannot be converted to int')

    @TypedArgs('str.to_lower')
    @noPosargs
    @InterpreterObject.method('to_lower')
    def to_lower_method(self, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> str:
        return self.held_object.lower()

    @TypedArgs('str.to_upper')
    @noPosargs
    @InterpreterObject.method('to_upper')
    def to_upper_method(self, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> str:
        return self.held_object.upper()

    @TypedArgs('underscorify')
    @noPosargs
    @InterpreterObject.method('underscorify')
    def underscorify_method(self, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> str:
        return underscorify(self.held_object)

    @TypedArgs('str.version_compare', var_types=STR_VARG_1.evolve(variadic_since='1.8.0'))
    @InterpreterObject.method('version_compare')
    def version_compare_method(self, args: T.Tuple[T.List[str]], kwargs: TYPE_kwargs) -> bool:
        return version_compare_many(self.held_object, args[0])[0]

    @staticmethod
    def _op_div(this: str, other: str) -> str:
        return os.path.join(this, other).replace('\\', '/')

    @FeatureNew('/ with string arguments', '0.49.0')
    @typed_operator(MesonOperator.DIV, str)
    @InterpreterObject.operator(MesonOperator.DIV)
    def op_div(self, other: str) -> str:
        return self._op_div(self.held_object, other)

    @typed_operator(MesonOperator.INDEX, int)
    @InterpreterObject.operator(MesonOperator.INDEX)
    def op_index(self, other: int) -> str:
        try:
            return self.held_object[other]
        except IndexError:
            raise InvalidArguments(f'Index {other} out of bounds of string of size {len(self.held_object)}.')

    @FeatureNew('"in" string operator', '1.0.0')
    @typed_operator(MesonOperator.IN, str)
    @InterpreterObject.operator(MesonOperator.IN)
    def op_in(self, other: str) -> bool:
        return other in self.held_object

    @FeatureNew('"not in" string operator', '1.0.0')
    @typed_operator(MesonOperator.NOT_IN, str)
    @InterpreterObject.operator(MesonOperator.NOT_IN)
    def op_notin(self, other: str) -> bool:
        return other not in self.held_object


class MesonVersionString(str):
    pass

class MesonVersionStringHolder(StringHolder):
    @TypedArgs(
        'str.version_compare',
        var_types=STR_VARG_1.evolve(
            variadic_since='1.10.0',
            variadic_since_message='From 1.8.0 - 1.9.* it failed to match str.version_compare',
        ),
    )
    @InterpreterObject.method('version_compare')
    def version_compare_method(self, args: T.Tuple[T.List[str]], kwargs: TYPE_kwargs) -> bool:
        unsupported = False
        for constraint in args[0]:
            if constraint.strip().startswith('!'):
                unsupported = True
                break
        if unsupported:
            mlog.debug('meson.version().version_compare() with != constraints',
                       'does not support overriding minimum meson_version checks.')
        else:
            self.interpreter.tmp_meson_version = version_check_to_range(args[0])

        return version_compare_many(self.held_object, args[0])[0]


# These special subclasses of string exist to cover the case where a dependency
# exports a string variable interchangeable with a system dependency. This
# matters because a dependency can only have string-type get_variable() return
# values. If at any time dependencies start supporting additional variable
# types, this class could be deprecated.
class DependencyVariableString(str):
    pass

class DependencyVariableStringHolder(StringHolder):
    @InterpreterObject.operator(MesonOperator.DIV)
    def op_div(self, other: str) -> T.Union[str, DependencyVariableString]:
        ret = super().op_div(other)
        if '..' in other:
            return ret
        return DependencyVariableString(ret)


class OptionString(str):
    optname: str

    def __new__(cls, value: str, name: str) -> 'OptionString':
        obj = str.__new__(cls, value)
        obj.optname = name
        return obj

    def __getnewargs__(self) -> T.Tuple[str, str]: # type: ignore # because the entire point of this is to diverge
        return (str(self), self.optname)


class OptionStringHolder(StringHolder):
    held_object: OptionString

    @InterpreterObject.operator(MesonOperator.DIV)
    def op_div(self, other: str) -> T.Union[str, OptionString]:
        ret = super().op_div(other)
        name = self._op_div(self.held_object.optname, other)
        return OptionString(ret, name)
