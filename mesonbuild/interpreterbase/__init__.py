# SPDX-License-Identifier: Apache-2.0
# Copyright 2013-2021 The Meson development team

from __future__ import annotations

from .baseobjects import (
    ContextManagerObject, HoldableTypes, InterpreterObject, IterableObject, MesonInterpreterObject,
    MutableInterpreterObject, ObjectHolder, SubProject, TV_func, TYPE_elementary,
    TYPE_HoldableTypes, TYPE_key_resolver, TYPE_kwargs, TYPE_nkwargs, TYPE_nvar, TYPE_var
)
from .decorators import (
    ContainerTypeInfo, FeatureBroken, FeatureCheckBase, FeatureDeprecated, FeatureDeprecatedKwargs,
    FeatureNew, FeatureNewKwargs, KwargInfo, disablerIfNotFound, noArgsFlattening, noKwargs,
    noPosargs, noSecondLevelHolderResolving, permittedKwargs, stringArgs, typed_kwargs,
    typed_operator, typed_pos_args, unholder_return
)
from .disabler import Disabler, is_disabled
from .exceptions import (
    BreakRequest, ContinueRequest, InterpreterException, InvalidArguments, InvalidCode,
    SubdirDoneRequest
)
from .helpers import (
    default_resolve_key, flatten, resolve_second_level_holders, stringifyUserArguments
)
from .interpreterbase import InterpreterBase
from .operator import MesonOperator

__all__ = [
    'InterpreterObject',
    'MesonInterpreterObject',
    'ObjectHolder',
    'IterableObject',
    'MutableInterpreterObject',
    'ContextManagerObject',

    'MesonOperator',

    'Disabler',
    'is_disabled',

    'InterpreterException',
    'InvalidCode',
    'InvalidArguments',
    'SubdirDoneRequest',
    'ContinueRequest',
    'BreakRequest',

    'default_resolve_key',
    'flatten',
    'resolve_second_level_holders',
    'stringifyUserArguments',

    'noPosargs',
    'noKwargs',
    'stringArgs',
    'noArgsFlattening',
    'noSecondLevelHolderResolving',
    'unholder_return',
    'disablerIfNotFound',
    'permittedKwargs',
    'typed_operator',
    'typed_pos_args',
    'ContainerTypeInfo',
    'KwargInfo',
    'typed_kwargs',
    'FeatureCheckBase',
    'FeatureNew',
    'FeatureDeprecated',
    'FeatureBroken',
    'FeatureNewKwargs',
    'FeatureDeprecatedKwargs',

    'InterpreterBase',

    'SubProject',

    'TV_func',
    'TYPE_elementary',
    'TYPE_var',
    'TYPE_nvar',
    'TYPE_kwargs',
    'TYPE_nkwargs',
    'TYPE_key_resolver',
    'TYPE_HoldableTypes',

    'HoldableTypes',
]
