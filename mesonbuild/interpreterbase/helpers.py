# SPDX-License-Identifier: Apache-2.0
# Copyright 2013-2021 The Meson development team

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

from .. import mesonlib, mparser
from .exceptions import InterpreterException, InvalidArguments
from ..mesonlib import HoldableObject


import collections.abc
import typing as T

if T.TYPE_CHECKING:
    from .baseobjects import TYPE_var, TYPE_kwargs, SubProject

def flatten(args: T.Union['TYPE_var', T.List['TYPE_var']]) -> T.List['TYPE_var']:
    if isinstance(args, mparser.StringNode):
        assert isinstance(args.value, str)
        return [args.value]
    if not isinstance(args, collections.abc.Sequence):
        return [args]
    result: T.List['TYPE_var'] = []
    for a in args:
        if isinstance(a, list):
            rest = flatten(a)
            result = result + rest
        elif isinstance(a, mparser.StringNode):
            result.append(a.value)
        else:
            result.append(a)
    return result

def resolve_second_level_holders(args: T.List['TYPE_var'], kwargs: 'TYPE_kwargs') -> T.Tuple[T.List['TYPE_var'], 'TYPE_kwargs']:
    def resolver(arg: 'TYPE_var') -> 'TYPE_var':
        if isinstance(arg, list):
            return [resolver(x) for x in arg]
        if isinstance(arg, dict):
            return {k: resolver(v) for k, v in arg.items()}
        if isinstance(arg, mesonlib.SecondLevelHolder):
            return arg.get_default_object()
        return arg
    return [resolver(x) for x in args], {k: resolver(v) for k, v in kwargs.items()}

def default_resolve_key(key: mparser.BaseNode) -> str:
    if not isinstance(key, mparser.IdNode):
        raise InterpreterException('Invalid kwargs format.')
    return key.value

def stringifyUserArguments(args: TYPE_var, subproject: SubProject, quote: bool = False) -> str:
    if isinstance(args, str):
        return f"'{args}'" if quote else args
    elif isinstance(args, bool):
        return 'true' if args else 'false'
    elif isinstance(args, int):
        return str(args)
    elif isinstance(args, list):
        return '[%s]' % ', '.join([stringifyUserArguments(x, subproject, True) for x in args])
    elif isinstance(args, dict):
        l = ['{} : {}'.format(stringifyUserArguments(k, subproject, True),
                              stringifyUserArguments(v, subproject, True)) for k, v in args.items()]
        return '{%s}' % ', '.join(l)
    elif isinstance(args, Feature):
        from .decorators import FeatureNew
        FeatureNew.single_use('User option in string format', '1.3.0', subproject)
        return str(args)
    raise InvalidArguments('Value other than strings, integers, bools, options, dictionaries and lists thereof.')


class FeatureValue(Enum):
    ENABLED = 'enabled'
    DISABLED = 'disabled'
    AUTO = 'auto'

    def __str__(self) -> str:
        return self.value


@dataclass
class Feature(HoldableObject):
    name: str
    value: FeatureValue

    def is_enabled(self) -> bool:
        return self.value is FeatureValue.ENABLED

    def is_disabled(self) -> bool:
        return self.value is FeatureValue.DISABLED

    def is_auto(self) -> bool:
        return self.value is FeatureValue.AUTO

    def with_value(self, value: FeatureValue) -> Feature:
        if value is self.value:
            return self
        return Feature(self.name, value)

    def as_enabled(self) -> Feature:
        return self.with_value(FeatureValue.ENABLED)

    def as_disabled(self) -> Feature:
        return self.with_value(FeatureValue.DISABLED)

    def __str__(self) -> str:
        return str(self.value)
