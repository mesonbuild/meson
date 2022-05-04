# SPDX-License-Identifier: MIT
# Copyright 2022 The Meson development team

"""Helpers for meson project testing.

These are not inended to be used except by meson itself
"""

from __future__ import annotations

import typing as T
import os

from mesonbuild import interpreter

from . import ExtensionModule
from .. import mlog
from ..interpreterbase.decorators import FeatureNew, noArgsFlattening, typed_pos_args
from ..mesonlib import MesonException

if T.TYPE_CHECKING:
    from . import ModuleState
    from ..interpreter import Interpreter
    from interpreterbase.baseobjects import InterpreterObject, TYPE_kwargs


class MesonTestModule(ExtensionModule):
    def __init__(self, interp: Interpreter) -> None:
        super().__init__(interp)
        self.methods.update({
            'catch': self.catch_method,
        })

    @noArgsFlattening
    @typed_pos_args('meson_test.catch', object, str, str, varargs=object)
    def catch_method(self, state: ModuleState, args: T.Tuple[object, str, str, T.List[object]],
                     kwargs: TYPE_kwargs) -> bool:
        robj, attr, msg, fargs = args
        # We want to call a method on the object, and the only reliable way to
        # do that is is via holderification
        obj = self.interpreter._holderify(robj)  # type: ignore
        try:
            obj.method_call(attr, fargs, kwargs)  # type: ignore
        except MesonException as e:
            # We only check that the message is in the error for convenience, otherwise line
            # Changes become significant.
            if msg in str(e):
                return True
            mlog.debug('catch: caught', str(e), 'which did not contain', msg)
        else:
            mlog.debug('catch: did not catch any exception')
        return False


def initialize(interp: Interpreter) -> MesonTestModule:
    FeatureNew.single_use('Meson Project Test Module', '0.63.0', interp.subproject, location=interp.current_node)
    return MesonTestModule(interp)


# Ensure that we only load this module when we're running tests
if int(os.environ.get('MESON_IS_PROJECT_TEST', 0)) == 0:
    raise ImportError
