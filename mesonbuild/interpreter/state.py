# SPDX-License-Identifier: Apache-2.0
# Copyright © 2024 Intel Corporation

"""Implementation of Interpreter state for the primary Interpreter."""

from __future__ import annotations
import dataclasses
import typing as T

from ..interpreterbase.state import State, LocalState, GlobalState

if T.TYPE_CHECKING:
    from .interpreter import Summary


@dataclasses.dataclass
class LocalInterpreterState(LocalState):

    project_name: str = dataclasses.field(default='', init=False)
    """A machine readable name of the project currently running.

    :attr:`self.subproject` represents a human readable name.
    """


@dataclasses.dataclass
class GlobalInterpreterState(GlobalState):

    summary: T.Dict[str, Summary] = dataclasses.field(default_factory=dict, init=False)


@dataclasses.dataclass
class InterpreterState(State):

    local: LocalInterpreterState
    world: GlobalInterpreterState
