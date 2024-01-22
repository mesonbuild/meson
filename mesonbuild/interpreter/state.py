# SPDX-License-Identifier: Apache-2.0
# Copyright © 2024 Intel Corporation

"""Implementation of Interpreter state for the primary Interpreter."""

from __future__ import annotations
import dataclasses

from ..interpreterbase.state import State, LocalState, GlobalState


@dataclasses.dataclass
class LocalInterpreterState(LocalState):

    pass


@dataclasses.dataclass
class GlobalInterpreterState(GlobalState):

    pass


@dataclasses.dataclass
class InterpreterState(State):

    local: LocalInterpreterState
    world: GlobalInterpreterState
