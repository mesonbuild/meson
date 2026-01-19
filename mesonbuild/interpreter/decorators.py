# SPDX-License-Identifier: Apache-2.0
# Copyright 2012-2021 The Meson development team

from __future__ import annotations

from functools import wraps
import typing as T

from ..interpreterbase import ObjectHolder
from ..interpreterbase.decorators import get_callee_args
from ..mesonlib import MachineChoice, MesonBugException

if T.TYPE_CHECKING:
    from ..interpreterbase import TV_func


def build_only_constraints(f: TV_func) -> TV_func:
    """Enforce build-only subproject constraints on native/install kwargs.

    Must be placed AFTER @typed_kwargs (so converters have run).
    """
    @wraps(f)
    def wrapped(*wrapped_args: T.Any, **wrapped_kwargs: T.Any) -> T.Any:
        # Import here to avoid circular imports at module load time
        from . import Interpreter
        from .mesonmain import MesonMain

        # First argument could be Interpreter, InterpreterObject (with an interpreter
        # attribute) or ModuleObject.  In the case of a ModuleObject it is the 2nd
        # argument (ModuleState) that contains the needed information.
        s: Interpreter
        if not hasattr(wrapped_args[0], 'current_node'):
            s = wrapped_args[1]._interpreter
        elif isinstance(wrapped_args[0], (MesonMain, ObjectHolder)):
            s = wrapped_args[0].interpreter
        elif isinstance(wrapped_args[0], Interpreter):
            s = wrapped_args[0]
        else:
            raise MesonBugException(f'cannot use @build_only_constraints if the object is a {type(wrapped_args[0])}')

        if s.build.is_build_only:
            _, _, kwargs, _ = get_callee_args(wrapped_args)
            if kwargs is not None:
                if 'native' in kwargs:
                    kwargs['native'] = MachineChoice.BUILD
                if 'install' in kwargs:
                    kwargs['install'] = False

        return f(*wrapped_args, **wrapped_kwargs)
    return T.cast('TV_func', wrapped)
