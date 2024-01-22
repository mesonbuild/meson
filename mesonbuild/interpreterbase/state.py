# SPDX-License-Identifier: Apache-2.0
# Copyright © 2024 Intel Corporation

"""Implementation of Interpreter state for the base Interpreter."""

from __future__ import annotations
import dataclasses
import typing as T

if T.TYPE_CHECKING:
    from . import SubProject

@dataclasses.dataclass
class LocalState:

    """State that is local to a single subproject."""

    subproject: SubProject


@dataclasses.dataclass
class GlobalState:

    """State that is global, it applies to all subprojects."""

    source_root: str
    """The root of the source directory of the main project."""


@dataclasses.dataclass
class State:

    local: LocalState
    world: GlobalState
