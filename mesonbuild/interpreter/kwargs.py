# SPDX-License-Identifier: Apache-2.0
# Copyright © 2021 The Meson Developers
# Copyright © 2021 Intel Corporation

"""Keyword Argument type annotations."""

import typing as T

from typing_extensions import TypedDict, Literal

from ..mesonlib import MachineChoice, File
from .interpreterobjects import BuildTargetHolder, CustomTargetHolder, EnvironmentVariablesHolder, TargetHolder


class FuncAddProjectArgs(TypedDict):

    """Keyword Arguments for the add_*_arguments family of arguments.

    including `add_global_arguments`, `add_project_arguments`, and their
    link variants

    Because of the use of a convertor function, we get the native keyword as
    a MachineChoice instance already.
    """

    native: MachineChoice
    language: T.List[str]


class BaseTest(TypedDict):

    """Shared base for the Rust module."""

    args: T.List[T.Union[str, File, TargetHolder]]
    should_fail: bool
    timeout: int
    workdir: T.Optional[str]
    depends: T.List[T.Union[CustomTargetHolder, BuildTargetHolder]]
    priority: int
    env: T.Union[EnvironmentVariablesHolder, T.List[str], T.Dict[str, str], str]
    suite: T.List[str]


class FuncBenchmark(BaseTest):

    """Keyword Arguments shared between `test` and `benchmark`."""

    protocol: Literal['exitcode', 'tap', 'gtest', 'rust']


class FuncTest(FuncBenchmark):

    """Keyword Arguments for `test`

    `test` only adds the `is_prallel` argument over benchmark, so inherintance
    is helpful here.
    """

    is_parallel: bool
