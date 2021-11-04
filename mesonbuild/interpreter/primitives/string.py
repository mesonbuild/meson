# Copyright 2021 The Meson development team
# SPDX-license-identifier: Apache-2.0

import re
import os
from pathlib import PurePath

import typing as T

from ...mesonlib import version_compare
from ...interpreterbase import (
    ObjectHolder,
    MesonOperator,
    FeatureNew,
    typed_operator,
    noArgsFlattening,
    noKwargs,
    noPosargs,
    typed_pos_args,

    TYPE_var,
    TYPE_kwargs,

    InvalidArguments,
)


if T.TYPE_CHECKING:
    # Object holders need the actual interpreter
    from ...interpreter import Interpreter

class StringHolder(ObjectHolder[str]):
    def __init__(self, obj: str, interpreter: 'Interpreter') -> None:
        super().__init__(obj, interpreter)
        self.methods.update({
            'contains': self.contains_method,
            'startswith': self.startswith_method,
            'endswith': self.endswith_method,
            'format': self.format_method,
            'join': self.join_method,
            'replace': self.replace_method,
            'split': self.split_method,
            'strip': self.strip_method,
            'substring': self.substring_method,
            'to_int': self.to_int_method,
            'to_lower': self.to_lower_method,
            'to_upper': self.to_upper_method,
            'underscorify': self.underscorify_method,
            'version_compare': self.version_compare_method,
        })

        self.trivial_operators.update({
            # Arithmetic
            MesonOperator.PLUS: (str, lambda x: self.held_object + x),

            # Comparison
            MesonOperator.EQUALS: (str, lambda x: self.held_object == x),
            MesonOperator.NOT_EQUALS: (str, lambda x: self.held_object != x),
            MesonOperator.GREATER: (str, lambda x: self.held_object > x),
            MesonOperator.LESS: (str, lambda x: self.held_object < x),
            MesonOperator.GREATER_EQUALS: (str, lambda x: self.held_object >= x),
            MesonOperator.LESS_EQUALS: (str, lambda x: self.held_object <= x),
        })

        # Use actual methods for functions that require additional checks
        self.operators.update({
            MesonOperator.DIV: self.op_div,
            MesonOperator.INDEX: self.op_index,
        })

    def display_name(self) -> str:
        return 'str'

    @noKwargs
    @typed_pos_args('str.contains', str)
    def contains_method(self, args: T.Tuple[str], kwargs: TYPE_kwargs) -> bool:
        return self.held_object.find(args[0]) >= 0

    @noKwargs
    @typed_pos_args('str.startswith', str)
    def startswith_method(self, args: T.Tuple[str], kwargs: TYPE_kwargs) -> bool:
        return self.held_object.startswith(args[0])

    @noKwargs
    @typed_pos_args('str.endswith', str)
    def endswith_method(self, args: T.Tuple[str], kwargs: TYPE_kwargs) -> bool:
        return self.held_object.endswith(args[0])

    @noArgsFlattening
    @noKwargs
    @typed_pos_args('str.format', varargs=object)
    def format_method(self, args: T.Tuple[T.List[object]], kwargs: TYPE_kwargs) -> str:
        arg_strings: T.List[str] = []
        for arg in args[0]:
            if isinstance(arg, bool): # Python boolean is upper case.
                arg = str(arg).lower()
            arg_strings.append(str(arg))

        def arg_replace(match: T.Match[str]) -> str:
            idx = int(match.group(1))
            if idx >= len(arg_strings):
                raise InvalidArguments(f'Format placeholder @{idx}@ out of range.')
            return arg_strings[idx]

        return re.sub(r'@(\d+)@', arg_replace, self.held_object)

    @noKwargs
    @typed_pos_args('str.join', varargs=str)
    def join_method(self, args: T.Tuple[T.List[str]], kwargs: TYPE_kwargs) -> str:
        return self.held_object.join(args[0])

    @noKwargs
    @typed_pos_args('str.replace', str, str)
    def replace_method(self, args: T.Tuple[str, str], kwargs: TYPE_kwargs) -> str:
        return self.held_object.replace(args[0], args[1])

    @noKwargs
    @typed_pos_args('str.split', optargs=[str])
    def split_method(self, args: T.Tuple[T.Optional[str]], kwargs: TYPE_kwargs) -> T.List[str]:
        return self.held_object.split(args[0])

    @noKwargs
    @typed_pos_args('str.strip', optargs=[str])
    def strip_method(self, args: T.Tuple[T.Optional[str]], kwargs: TYPE_kwargs) -> str:
        return self.held_object.strip(args[0])

    @noKwargs
    @typed_pos_args('str.substring', optargs=[int, int])
    def substring_method(self, args: T.Tuple[T.Optional[int], T.Optional[int]], kwargs: TYPE_kwargs) -> str:
        start = args[0] if args[0] is not None else 0
        end   = args[1] if args[1] is not None else len(self.held_object)
        return self.held_object[start:end]

    @noKwargs
    @noPosargs
    def to_int_method(self, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> int:
        try:
            return int(self.held_object)
        except ValueError:
            raise InvalidArguments(f'String {self.held_object!r} cannot be converted to int')

    @noKwargs
    @noPosargs
    def to_lower_method(self, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> str:
        return self.held_object.lower()

    @noKwargs
    @noPosargs
    def to_upper_method(self, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> str:
        return self.held_object.upper()

    @noKwargs
    @noPosargs
    def underscorify_method(self, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> str:
        return re.sub(r'[^a-zA-Z0-9]', '_', self.held_object)

    @noKwargs
    @typed_pos_args('str.version_compare', str)
    def version_compare_method(self, args: T.Tuple[str], kwargs: TYPE_kwargs) -> bool:
        return version_compare(self.held_object, args[0])

    @FeatureNew('/ with string arguments', '0.49.0')
    @typed_operator(MesonOperator.DIV, str)
    def op_div(self, other: str) -> str:
        return os.path.join(self.held_object, other).replace('\\', '/')

    @typed_operator(MesonOperator.INDEX, int)
    def op_index(self, other: int) -> str:
        try:
            return self.held_object[other]
        except IndexError:
            raise InvalidArguments(f'Index {other} out of bounds of string of size {len(self.held_object)}.')


class MesonVersionString(str):
    pass

class MesonVersionStringHolder(StringHolder):
    @noKwargs
    @typed_pos_args('str.version_compare', str)
    def version_compare_method(self, args: T.Tuple[str], kwargs: TYPE_kwargs) -> bool:
        self.interpreter.tmp_meson_version = args[0]
        return version_compare(self.held_object, args[0])
