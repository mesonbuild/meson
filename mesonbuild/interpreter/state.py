# SPDX-License-Identifier: Apache-2.0
# Copyright © 2024 Intel Corporation

"""Implementation of Interpreter state for the primary Interpreter."""

from __future__ import annotations
import dataclasses
import typing as T

from ..interpreterbase.state import State, LocalState, GlobalState
from ..utils.universal import OrderedSet, PerMachine

if T.TYPE_CHECKING:
    from .interpreter import Summary, InterpreterRuleRelaxation
    from ..build import Build
    from ..compilers.compilers import Compiler
    from ..utils.universal import OptionKey


@dataclasses.dataclass
class LocalInterpreterState(LocalState):

    project_name: str = dataclasses.field(default='', init=False)
    """A machine readable name of the project currently running.

    :attr:`self.subproject` represents a human readable name.
    """

    project_version: T.Optional[str] = dataclasses.field(default=None, init=False)
    """The version of the project currently being evaluated.

    see :attr:`Interpreter.state.global.build.project_version` to get the root
    project version.
    """

    rule_relaxations: T.Set[InterpreterRuleRelaxation] = dataclasses.field(
        default_factory=set)
    """Relaxations of normal Meson rules.

    These are used by convertors from other build systems into Meson, where
    certain Meson rules may not be enforceable.
    """

    subproject_stack: T.List[str] = dataclasses.field(default_factory=list)
    """All subprojects being currently evaluated, in order.

    This is for tracking nested subprojects (A -> B -> C), but does not contain
    any subprojects that have already fully finished evaluation.
    """

    args_frozen: bool = dataclasses.field(default=False, init=False)
    """Whether calls to `add_project*_args is an error.

    Once the first target has been defined in a project such calls are not
    allowed.
    """

    compilers: PerMachine[T.Dict[str, Compiler]] = dataclasses.field(
        default_factory=lambda: PerMachine({}, {}), init=False)
    """Compilers that have been enabled in this subproject.

    This is a subset of all compilers enabled in the entire build, and prevents
    language leaks from one project to another.
    """

    configure_file_outputs: T.Dict[str, int] = dataclasses.field(default_factory=dict, init=False)
    """The outputs of calls to `configure_file()`.

    Maps the path relative to the source root of the meson.build file to the
    line number of the first definition. Used to warn when a configure_file
    output will be overwritten.
    """

    default_subproject_options: T.Dict[OptionKey, str] = dataclasses.field(
        default_factory=dict, init=False)
    """Options passed to subprojects via the `dependency(default_options)` keyword argument.

    See also :attr:`project_default_options`.
    """


@dataclasses.dataclass
class GlobalInterpreterState(GlobalState):

    build: Build
    """Presistant build information."""

    summary: T.Dict[str, Summary] = dataclasses.field(default_factory=dict, init=False)

    args_frozen: bool = dataclasses.field(default=False, init=False)
    """Whether calls to `add_global*_args is an error.

    Once the first target has been defined in *any* project such calls are not
    allowed.
    """

    build_def_files: OrderedSet[str] = dataclasses.field(default_factory=OrderedSet, init=False)
    """Files which, when changed, should trigger a reconfigure."""

    @property
    def subproject_dir(self) -> str:
        # Provides consistant API with ASTInterpreter, which doesn't have a Build
        return self.build.subproject_dir


@dataclasses.dataclass
class InterpreterState(State):

    local: LocalInterpreterState
    world: GlobalInterpreterState
