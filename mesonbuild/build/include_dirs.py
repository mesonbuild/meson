# SPDX-License-Identifier: Apache-2.0
# Copyright 2012-2022 The Meson development team
# Copyright © 2022 Intel Corporation

from __future__ import annotations
from dataclasses import dataclass, field
import enum
import os
import typing as T

from ..mesonlib import HoldableObject


class IncludeType(enum.Enum):

    """What Kind of include is this"""

    NORMAL = enum.auto()
    SYSTEM = enum.auto()


@dataclass(eq=False)
class IncludeDirs(HoldableObject):

    """Internal representation of paths to be treated as compiler include
    paths.

    The `include_directories` function is lowered into this, and it is used
    internally.

    :param curdir: The current working directory, set to none for system
        dependencies
    :param incdirs: a list of paths, either relative to the source dir, or
        absolute
    :param kind: What kind of
        with `-isystem` (or equivalent) when possible
    :param extra_build_dirs: Extra build directory relative paths to include
    """

    curdir: T.Optional[str]
    incdirs: T.List[str]
    kind: IncludeType = IncludeType.NORMAL
    # Interpreter has validated that all given directories
    # actually exist.
    extra_build_dirs: T.List[str] = field(default_factory=list)

    def get_curdir(self) -> T.Optional[str]:
        return self.curdir

    def get_incdirs(self) -> T.List[str]:
        return self.incdirs

    def get_extra_build_dirs(self) -> T.List[str]:
        return self.extra_build_dirs

    def to_string_list(self, sourcedir: str, builddir: str) -> T.List[str]:
        """Convert IncludeDirs object to a list of strings.

        :param sourcedir: The absolute source directory
        :param builddir: The absolute build directory, option, build dir will not
            be added if this is unset
        :returns: A list of strings (without compiler argument)
        """
        strlist: T.List[str] = []
        # If curdir is `None`, then we are dealing with some kind of external
        # dependency include paths, and we don't want to make them relative to
        # the source or builddir. Otherwise, we do.
        if self.curdir is None:
            return self.incdirs
        for idir in self.incdirs:
            strlist.append(os.path.join(sourcedir, self.curdir, idir))
            strlist.append(os.path.join(builddir, self.curdir, idir))
        return strlist

    def to_system(self) -> IncludeDirs:
        """Create a shallow copy of this IncludeDirs as a system dependency."""
        return IncludeDirs(self.curdir, self.incdirs, IncludeType.SYSTEM, self.extra_build_dirs)

    def to_non_system(self) -> IncludeDirs:
        """Create a shallow copy of this IncludeDirs as a non-system dependency."""
        return IncludeDirs(self.curdir, self.incdirs, IncludeType.NORMAL, self.extra_build_dirs)
