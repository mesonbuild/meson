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
    'ObjectHolder',
    'RangeHolder',
    'MesonVersionString',
    'MutableInterpreterObject',

    'Disabler',
    'is_disabler',
    'is_arg_disabled',
    'is_disabled',

    'check_stringlist',
    'flatten',
    'noPosargs',
    'builtinMethodNoKwargs',
    'noKwargs',
    'stringArgs',
    'noArgsFlattening',
    'disablerIfNotFound',
    'permittedKwargs',
    'typed_pos_args',
    'ContainerTypeInfo',
    'KwargInfo',
    'typed_kwargs',
    'FeatureNew',
    'FeatureDeprecated',
    'FeatureNewKwargs',
    'FeatureDeprecatedKwargs',

    'InterpreterBase',
    'default_resolve_key',

    'InterpreterException',
    'InvalidCode',
    'InvalidArguments',
    'SubdirDoneRequest',
    'ContinueRequest',
    'BreakRequest',

    'TV_fw_var',
    'TV_fw_args',
    'TV_fw_kwargs',
    'TV_func',
    'TYPE_elementary',
    'TYPE_var',
    'TYPE_nvar',
    'TYPE_nkwargs',
    'TYPE_key_resolver',
]

from .exceptions import (
    InterpreterException,
    InvalidCode,
    InvalidArguments,
    SubdirDoneRequest,
    ContinueRequest,
    BreakRequest,
)

from .interpreterbase import (
    InterpreterObject,
    ObjectHolder,
    RangeHolder,
    MesonVersionString,
    MutableInterpreterObject,

    Disabler,
    is_disabler,
    is_arg_disabled,
    is_disabled,

    check_stringlist,
    flatten,
    noPosargs,
    builtinMethodNoKwargs,
    noKwargs,
    stringArgs,
    noArgsFlattening,
    disablerIfNotFound,
    permittedKwargs,
    typed_pos_args,
    ContainerTypeInfo,
    KwargInfo,
    typed_kwargs,
    FeatureNew,
    FeatureDeprecated,
    FeatureNewKwargs,
    FeatureDeprecatedKwargs,

    InterpreterBase,
    default_resolve_key,

    TV_fw_var,
    TV_fw_args,
    TV_fw_kwargs,
    TV_func,
    TYPE_elementary,
    TYPE_var,
    TYPE_nvar,
    TYPE_nkwargs,
    TYPE_key_resolver,
)
