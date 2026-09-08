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

    'noPosargs',
    'noKwargs',
    'noArgsFlattening',
    'noSecondLevelHolderResolving',
    'unholder_return',
    'disablerIfNotFound',
    'typed_operator',
    'typed_pos_args',
    'ContainerTypeInfo',
    'KwargInfo',
    'typed_kwargs',
    'FeatureCheckBase',
    'FeatureNew',
    'FeatureDeprecated',
    'FeatureBroken',

    'InterpreterBase',

    'TV_func',
    'TYPE_elementary',
    'TYPE_var',
    'TYPE_kwargs',
    'TYPE_key_resolver',
    'TYPE_HoldableTypes',

    'HoldableTypes',

    'UnknownValue',
    'UndefinedVariable',
]

from .baseobjects import (
    ContextManagerObject,
    DefaultObject,
    HoldableTypes,
    InterpreterObject,
    IterableObject,
    MesonInterpreterObject,
    MutableInterpreterObject,
    ObjectHolder,
    TV_func,
    TYPE_elementary,
    TYPE_HoldableTypes,
    TYPE_key_resolver,
    TYPE_kwargs,
    TYPE_var,
    UndefinedVariable,
    UnknownValue,
)
from .decorators import (
    ContainerTypeInfo,
    FeatureBroken,
    FeatureCheckBase,
    FeatureDeprecated,
    FeatureNew,
    KwargInfo,
    disablerIfNotFound,
    noArgsFlattening,
    noKwargs,
    noPosargs,
    noSecondLevelHolderResolving,
    typed_kwargs,
    typed_operator,
    typed_pos_args,
    unholder_return,
)
from .disabler import Disabler, is_disabled
from .exceptions import (
    BreakRequest,
    ContinueRequest,
    InterpreterException,
    InvalidArguments,
    InvalidCode,
    SubdirDoneRequest,
)
from .helpers import (
    Feature,
    FeatureValue,
    default_resolve_key,
    flatten,
    resolve_second_level_holders,
    stringifyUserArguments,
)
from .interpreterbase import InterpreterBase
from .operator import MesonOperator
