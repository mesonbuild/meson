# SPDX-License-Identifier: Apache-2.0
# Copyright 2021 The Meson development team
from __future__ import annotations

from ...interpreterbase import (
    InterpreterObject, MesonOperator, ObjectHolder,
    FeatureBroken, InvalidArguments, KwargInfo,
    noKwargs, noPosargs, typed_operator, typed_kwargs
)
from ..type_checking import in_set_validator

import typing as T

if T.TYPE_CHECKING:
    from typing_extensions import Literal, TypedDict

    from ...interpreterbase import TYPE_var, TYPE_kwargs

    class ToStringKw(TypedDict):

        fill: int
        format: Literal['dec', 'hex', 'oct', 'bin']

class IntegerHolder(ObjectHolder[int]):
    # Operators that only require type checks
    TRIVIAL_OPERATORS = {
        # Arithmetic
        MesonOperator.UMINUS: (None, lambda obj, x: -obj.held_object),
        MesonOperator.PLUS: (int, lambda obj, x: obj.held_object + x),
        MesonOperator.MINUS: (int, lambda obj, x: obj.held_object - x),
        MesonOperator.TIMES: (int, lambda obj, x: obj.held_object * x),

        # Comparison
        MesonOperator.EQUALS: (int, lambda obj, x: obj.held_object == x),
        MesonOperator.NOT_EQUALS: (int, lambda obj, x: obj.held_object != x),
        MesonOperator.GREATER: (int, lambda obj, x: obj.held_object > x),
        MesonOperator.LESS: (int, lambda obj, x: obj.held_object < x),
        MesonOperator.GREATER_EQUALS: (int, lambda obj, x: obj.held_object >= x),
        MesonOperator.LESS_EQUALS: (int, lambda obj, x: obj.held_object <= x),
    }

    def display_name(self) -> str:
        return 'int'

    def operator_call(self, operator: MesonOperator, other: TYPE_var) -> TYPE_var:
        if isinstance(other, bool):
            FeatureBroken.single_use('int operations with non-int', '1.2.0', self.subproject,
                                     'It is not commutative and only worked because of leaky Python abstractions.',
                                     location=self.current_node)
        return super().operator_call(operator, other)

    @noKwargs
    @noPosargs
    @InterpreterObject.method('is_even')
    def is_even_method(self, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> bool:
        return self.held_object % 2 == 0

    @noKwargs
    @noPosargs
    @InterpreterObject.method('is_odd')
    def is_odd_method(self, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> bool:
        return self.held_object % 2 != 0

    @typed_kwargs(
        'to_string',
        KwargInfo('fill', int, default=0, since='1.3.0'),
        KwargInfo(
            "format",
            str,
            default="dec",
            since="1.10.0",
            validator=in_set_validator({"dec", "hex", "oct", "bin"}),
        ),
    )
    @noPosargs
    @InterpreterObject.method('to_string')
    def to_string_method(self, args: T.List[TYPE_var], kwargs: 'ToStringKw') -> str:
        format_codes = {"hex": "x", "oct": "o", "bin": "b", "dec": "d"}
        return '{:#{padding}{format}}'.format(self.held_object,
                                              padding=f'0{kwargs["fill"]}' if kwargs['fill'] > 0 else '',
                                              format=format_codes[kwargs['format']])

    @typed_operator(MesonOperator.DIV, int)
    @InterpreterObject.operator(MesonOperator.DIV)
    def op_div(self, other: int) -> int:
        if other == 0:
            raise InvalidArguments('Tried to divide by 0')
        return self.held_object // other

    @typed_operator(MesonOperator.MOD, int)
    @InterpreterObject.operator(MesonOperator.MOD)
    def op_mod(self, other: int) -> int:
        if other == 0:
            raise InvalidArguments('Tried to divide by 0')
        return self.held_object % other
