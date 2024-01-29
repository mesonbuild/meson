# SPDX-License-Identifier: Apache-2.0
# Copyright © 2024 Intel Corporation

"""Implementation of Interpreter state for the base Interpreter."""

from __future__ import annotations
import dataclasses
import typing as T

from .. mparser import BaseNode

if T.TYPE_CHECKING:
    from . import InterpreterObject, SubProject
    from ..utils.universal import OptionKey

@dataclasses.dataclass
class LocalState:

    """State that is local to a single subproject."""

    subproject: SubProject

    subdir: str

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

    variables: T.Dict[str, InterpreterObject] = dataclasses.field(
        default_factory=dict, init=False)
    """All variables assigned during a subproject."""

    processed_buildfiles: T.Set[str] = dataclasses.field(default_factory=set, init=False)
    """All build files of the current project that have been read already."""

    project_default_options: T.Dict[OptionKey, str] = dataclasses.field(
        default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self.root_subdir = self.subdir


@dataclasses.dataclass
class GlobalState:

    """State that is global, it applies to all subprojects."""

    source_root: str
    """The root of the source directory of the main project."""

    tmp_meson_version: T.Optional[str] = dataclasses.field(default=None, init=False)
    """This is set to `version_string` when this statement is evaluated:
    meson.version().compare_version(version_string)

    If it was part of an if-clause, it is used to temporally override the current
    meson version target within that if-block.
    """


@dataclasses.dataclass
class State:

    local: LocalState
    world: GlobalState
