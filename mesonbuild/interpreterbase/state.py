# SPDX-License-Identifier: Apache-2.0
# Copyright © 2024 Intel Corporation

"""Implementation of Interpreter state for the base Interpreter."""

from __future__ import annotations
import dataclasses
import typing as T

from .. mparser import BaseNode

if T.TYPE_CHECKING:
    from . import SubProject

@dataclasses.dataclass
class LocalState:

    """State that is local to a single subproject."""

    subproject: SubProject

    current_node: BaseNode = dataclasses.field(
        default_factory=lambda: BaseNode(-1, -1, 'Sentinel Node'),
        init=False)
    """Current node set during a function call.

    This can be used as location when printing a warning message during a method
    call.
    """

    argument_depth: int = dataclasses.field(default=0, init=False)
    """How many nested contexts we've entered.

    Mainly used to track whether assignment is allowed.
    """


@dataclasses.dataclass
class GlobalState:

    """State that is global, it applies to all subprojects."""

    source_root: str
    """The root of the source directory of the main project."""


@dataclasses.dataclass
class State:

    local: LocalState
    world: GlobalState
