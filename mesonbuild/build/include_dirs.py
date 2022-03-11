# SPDX-License-Identifier: Apache-2.0
# Copyright 2012-2022 The Meson development team
# Copyright © 2022 Intel Corporation

from __future__ import annotations
from dataclasses import dataclass, field
import os
import typing as T

from ..mesonlib import HoldableObject


@dataclass(eq=False)
class IncludeDirs(HoldableObject):

    """Internal representation of an include_directories call."""

    curdir: T.Optional[str]
    incdirs: T.List[str]
    is_system: bool = False
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
        return IncludeDirs(self.curdir, self.incdirs, True, self.extra_build_dirs)

    def to_non_system(self) -> IncludeDirs:
        """Create a shallow copy of this IncludeDirs as a non-system dependency."""
        return IncludeDirs(self.curdir, self.incdirs, False, self.extra_build_dirs)
