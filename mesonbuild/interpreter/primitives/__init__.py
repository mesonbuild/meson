# SPDX-License-Identifier: Apache-2.0
# Copyright 2021 The Meson development team

from __future__ import annotations

from .array import ArrayHolder
from .boolean import BooleanHolder
from .dict import DictHolder
from .integer import IntegerHolder
from .range import RangeHolder
from .string import (
    DependencyVariableString, DependencyVariableStringHolder, MesonVersionString,
    MesonVersionStringHolder, OptionString, OptionStringHolder, StringHolder
)

__all__ = [
    'ArrayHolder',
    'BooleanHolder',
    'DictHolder',
    'IntegerHolder',
    'RangeHolder',
    'StringHolder',
    'MesonVersionString',
    'MesonVersionStringHolder',
    'DependencyVariableString',
    'DependencyVariableStringHolder',
    'OptionString',
    'OptionStringHolder',
]
