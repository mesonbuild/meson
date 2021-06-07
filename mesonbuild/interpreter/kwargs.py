# SPDX-License-Identifier: Apache-2.0
# Copyright © 2021 The Meson Developers
# Copyright © 2021 Intel Corporation

"""Keyword Argument type annotations."""

import typing as T

from typing_extensions import TypedDict

from ..mesonlib import MachineChoice


class FuncAddProjectArgs(TypedDict):

    """Keyword Arguments for the add_*_arguments family of arguments.

    including `add_global_arguments`, `add_project_arguments`, and their
    link variants

    Because of the use of a convertor function, we get the native keyword as
    a MachineChoice instance already.
    """

    native: MachineChoice
    language: T.List[str]
