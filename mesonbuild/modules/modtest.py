# SPDX-License-Identifier: Apache-2.0
# Copyright 2015 The Meson development team

from __future__ import annotations
import typing as T

from . import NewExtensionModule, ModuleInfo
from ..interpreterbase import TypedArgs, noPosargs

if T.TYPE_CHECKING:
    from . import ModuleState
    from ..interpreter.interpreter import Interpreter
    from ..interpreterbase.baseobjects import TYPE_kwargs, TYPE_var


class TestModule(NewExtensionModule):

    INFO = ModuleInfo('modtest')

    def __init__(self, interpreter: Interpreter) -> None:
        super().__init__()
        self.methods.update({
            'print_hello': self.print_hello,
        })

    @noPosargs
    @TypedArgs('modtest.print_hello')
    def print_hello(self, state: ModuleState, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> None:
        print('Hello from a Meson module')


def initialize(interp: Interpreter) -> TestModule:
    return TestModule(interp)
