# SPDX-license-identifier: Apache-2.0
# Copyright 2012-2021 The Meson development team
# Copyright © 2021-2023 Intel Corporation

"""Meson interpreter."""

from __future__ import annotations

from .compiler import CompilerHolder
from .interpreter import Interpreter, permitted_dependency_kwargs
from .interpreterobjects import (
    BuildTargetHolder, ConfigurationDataHolder, CustomTargetHolder, CustomTargetIndexHolder,
    DependencyHolder, ExecutableHolder, ExternalProgramHolder, GeneratedListHolder, MachineHolder,
    SubprojectHolder, Test, extract_required_kwarg
)
from .primitives import ArrayHolder, BooleanHolder, DictHolder, IntegerHolder, StringHolder

__all__ = [
    'Interpreter',
    'permitted_dependency_kwargs',

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
    'ExternalProgramHolder',
    'extract_required_kwarg',

    'ArrayHolder',
    'BooleanHolder',
    'DictHolder',
    'IntegerHolder',
    'StringHolder',
]
