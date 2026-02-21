# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Intel Corporation

from __future__ import annotations
import typing as T

from . import ExtensionModule, ModuleInfo
from ..interpreterbase import typed_pos_args, noKwargs

if T.TYPE_CHECKING:
    from . import ModuleState
    from ..interpreter import Interpreter
    from ..interpreterbase import TYPE_kwargs


class TypesModule(ExtensionModule):

    """A module that holds helper functions for inspecting Meson DSL."""

    INFO = ModuleInfo('types', '1.9', unstable=True)

    def __init__(self, interpreter: Interpreter) -> None:
        super().__init__(interpreter)
        self.methods.update({
            'is_array': self.is_array_method,
            'is_number': self.is_number_method,
            'is_string': self.is_string_method,
        })

    @typed_pos_args('types.is_array', object)
    @noKwargs
    def is_array_method(self, state: ModuleState, args: T.Tuple[object], kwargs: TYPE_kwargs) -> bool:
        return isinstance(args[0], list)

    @typed_pos_args('types.is_number', object)
    @noKwargs
    def is_number_method(self, state: ModuleState, args: T.Tuple[object], kwargs: TYPE_kwargs) -> bool:
        return isinstance(args[0], int)

    @typed_pos_args('types.is_string', object)
    @noKwargs
    def is_string_method(self, state: ModuleState, args: T.Tuple[object], kwargs: TYPE_kwargs) -> bool:
        return isinstance(args[0], str)


def initialize(interp: Interpreter) -> TypesModule:
    return TypesModule(interp)
