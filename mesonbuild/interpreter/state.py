# SPDX-License-Identifier: Apache-2.0
# Copyright © 2024 Intel Corporation

"""Implementation of Interpreter state for the primary Interpreter."""

from __future__ import annotations
import dataclasses
import typing as T

from ..interpreterbase.state import State, LocalState, GlobalState

if T.TYPE_CHECKING:
    from .interpreter import Summary, InterpreterRuleRelaxation


@dataclasses.dataclass
class LocalInterpreterState(LocalState):

    project_name: str = dataclasses.field(default='', init=False)
    """A machine readable name of the project currently running.

    :attr:`self.subproject` represents a human readable name.
    """

    rule_relaxations: T.Set[InterpreterRuleRelaxation] = dataclasses.field(
        default_factory=set)
    """Relaxations of normal Meson rules.

    These are used by convertors from other build systems into Meson, where
    certain Meson rules may not be enforceable.
    """

    args_frozen: bool = dataclasses.field(default=False, init=False)
    """Whether calls to `add_project*_args is an error.

    Once the first target has been defined in a project such calls are not
    allowed.
    """


@dataclasses.dataclass
class GlobalInterpreterState(GlobalState):

    summary: T.Dict[str, Summary] = dataclasses.field(default_factory=dict, init=False)


@dataclasses.dataclass
class InterpreterState(State):

    local: LocalInterpreterState
    world: GlobalInterpreterState
