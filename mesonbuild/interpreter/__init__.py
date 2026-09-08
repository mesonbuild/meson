# SPDX-License-Identifier: Apache-2.0
# Copyright 2012-2021 The Meson development team
# Copyright © 2021-2024 Intel Corporation

"""Meson interpreter."""

__all__ = [
    'Interpreter',

    'CompilerHolder',

    'ExecutableHolder',
    'BuildTargetHolder',
    'CustomTargetHolder',
    'CustomTargetIndexHolder',
    'MachineHolder',
    'Test',
    'ConfigurationDataHolder',
    'SubprojectHolder',
    'DependencyHolder',
    'GeneratedListHolder',
    'extract_required_kwarg',

    'ArrayHolder',
    'BooleanHolder',
    'DictHolder',
    'IntegerHolder',
    'StringHolder',
]

from .compiler import CompilerHolder
from .interpreter import Interpreter
from .interpreterobjects import (
    BuildTargetHolder,
    ConfigurationDataHolder,
    CustomTargetHolder,
    CustomTargetIndexHolder,
    DependencyHolder,
    ExecutableHolder,
    GeneratedListHolder,
    MachineHolder,
    SubprojectHolder,
    Test,
    extract_required_kwarg,
)
from .primitives import (
    ArrayHolder,
    BooleanHolder,
    DictHolder,
    IntegerHolder,
    StringHolder,
)
