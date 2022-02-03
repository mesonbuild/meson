# Copyright 2021 The Meson development team
# SPDX-license-identifier: Apache-2.0

from .baseobjects import ObjectHolder, TYPE_var, TYPE_kwargs, InvalidCode, MesonOperator
import typing as T

class VoidObject(ObjectHolder[None]):
    @property
    def is_assignable(self) -> bool:
        return False

    def method_call(self, method_name: str, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> TYPE_var:
        raise InvalidCode(f'Tried to call method {method_name} on void.')

    def operator_call(self, operator: MesonOperator, other: TYPE_var) -> TYPE_var:
        raise InvalidCode(f'Tried use operator {operator.value} on void.')
