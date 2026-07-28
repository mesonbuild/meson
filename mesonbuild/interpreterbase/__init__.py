# SPDX-License-Identifier: Apache-2.0
# Copyright 2013-2021 The Meson development team

__all__ = [
    'InterpreterObject',
    'MesonInterpreterObject',
    'ObjectHolder',
    'IterableObject',
    'MutableInterpreterObject',
    'ContextManagerObject',
    'DefaultObject',

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
    'Feature',
    'FeatureValue',

    'noArgsFlattening',
    'noSecondLevelHolderResolving',
    'unholder_return',
    'disablerIfNotFound',
    'typed_operator',
    'ContainerTypeInfo',
    'KwargInfo',
    'TypedArgs',
    'PosArgInfo',
    'OptArgInfo',
    'VarArgInfo',
    'FeatureCheckBase',
    'FeatureNew',
    'FeatureDeprecated',
    'FeatureBroken',

    'InterpreterBase',

    'TV_func',
    'TYPE_elementary',
    'TYPE_var',
    'TYPE_nvar',
    'TYPE_kwargs',
    'TYPE_nkwargs',
    'TYPE_key_resolver',
    'TYPE_HoldableTypes',

    'HoldableTypes',

    'UnknownValue',
    'UndefinedVariable',
]

from .baseobjects import (
    InterpreterObject,
    MesonInterpreterObject,
    ObjectHolder,
    IterableObject,
    MutableInterpreterObject,
    ContextManagerObject,
    DefaultObject,

    TV_func,
    TYPE_elementary,
    TYPE_var,
    TYPE_nvar,
    TYPE_kwargs,
    TYPE_nkwargs,
    TYPE_key_resolver,
    TYPE_HoldableTypes,

    HoldableTypes,

    UnknownValue,
    UndefinedVariable,
)

from .decorators import (
    noArgsFlattening,
    noSecondLevelHolderResolving,
    unholder_return,
    disablerIfNotFound,
    ContainerTypeInfo,
    KwargInfo,
    typed_operator,
    FeatureCheckBase,
    FeatureNew,
    FeatureDeprecated,
    FeatureBroken,
    TypedArgs,
    PosArgInfo,
    OptArgInfo,
    VarArgInfo,
)

from .exceptions import (
    InterpreterException,
    InvalidCode,
    InvalidArguments,
    SubdirDoneRequest,
    ContinueRequest,
    BreakRequest,
)

from .disabler import Disabler, is_disabled
from .helpers import (
    default_resolve_key,
    flatten,
    resolve_second_level_holders,
    stringifyUserArguments,
    Feature,
    FeatureValue,
)
from .interpreterbase import InterpreterBase
from .operator import MesonOperator
