# SPDX-License-Identifier: Apache-2.0
# Copyright © 2024 Intel Corporation

"""Common features of LLVM based compilers."""

from __future__ import annotations
import typing as T

if T.TYPE_CHECKING:
    from ...build import BuildTarget
    from ...compilers.compilers import Compiler
else:
    # This is a bit clever, for mypy we pretend that these mixins descend from
    # Compiler, so we get all of the methods and attributes defined for us, but
    # for runtime we make them descend from object (which all classes normally
    # do). This gives up DRYer type checking, with no runtime impact
    Compiler = object


class LLVMCompilerMixin(Compiler):

    def should_pgo_target(self, target: BuildTarget) -> bool:
        return target.typename != 'static library'
