# Copyright 2013-2021 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__all__ = [
    'InterpreterObject',
    'MesonInterpreterObject',
    'ObjectHolder',
    'RangeHolder',
    'MesonVersionString',
    'MutableInterpreterObject',

    'Disabler',
    'is_disabled',

    'InterpreterException',
    'InvalidCode',
    'InvalidArguments',
    'SubdirDoneRequest',
    'ContinueRequest',
    'BreakRequest',

    'check_stringlist',
    'default_resolve_key',
    'flatten',
    'resolve_second_level_holders',

    'noPosargs',
    'builtinMethodNoKwargs',
    'noKwargs',
    'stringArgs',
    'noArgsFlattening',
    'noSecondLevelHolderResolving',
    'permissive_unholder_return',
    'disablerIfNotFound',
    'permittedKwargs',
    'typed_pos_args',
    'ContainerTypeInfo',
    'KwargInfo',
    'typed_kwargs',
    'FeatureCheckBase',
    'FeatureNew',
    'FeatureDeprecated',
    'FeatureNewKwargs',
    'FeatureDeprecatedKwargs',

    'InterpreterBase',

    'TV_fw_var',
    'TV_fw_args',
    'TV_fw_kwargs',
    'TV_func',
    'TYPE_elementary',
    'TYPE_var',
    'TYPE_nvar',
    'TYPE_kwargs',
    'TYPE_nkwargs',
    'TYPE_key_resolver',
]

from .baseobjects import (
    InterpreterObject,
    MesonInterpreterObject,
    ObjectHolder,
    RangeHolder,
    MutableInterpreterObject,

    TV_fw_var,
    TV_fw_args,
    TV_fw_kwargs,
    TV_func,
    TYPE_elementary,
    TYPE_var,
    TYPE_nvar,
    TYPE_kwargs,
    TYPE_nkwargs,
    TYPE_key_resolver,
)

from .decorators import (
    noPosargs,
    builtinMethodNoKwargs,
    noKwargs,
    stringArgs,
    noArgsFlattening,
    noSecondLevelHolderResolving,
    permissive_unholder_return,
    disablerIfNotFound,
    permittedKwargs,
    typed_pos_args,
    ContainerTypeInfo,
    KwargInfo,
    typed_kwargs,
    FeatureCheckBase,
    FeatureNew,
    FeatureDeprecated,
    FeatureNewKwargs,
    FeatureDeprecatedKwargs,
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
from .helpers import check_stringlist, default_resolve_key, flatten, resolve_second_level_holders
from .interpreterbase import MesonVersionString, InterpreterBase
