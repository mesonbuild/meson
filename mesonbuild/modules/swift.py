# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Meson development team

from __future__ import annotations

import typing as T

from . import NewExtensionModule, ModuleInfo

if T.TYPE_CHECKING:
    from mesonbuild.interpreter import Interpreter


def initialize(*args: T.Any, **kwargs: T.Any) -> SwiftModule:
    return SwiftModule(*args, **kwargs)


class SwiftModule(NewExtensionModule):
    INFO = ModuleInfo('swift', '1.7.99')

    def __init__(self, interpreter: Interpreter):
        super().__init__()
        self.methods.update({
        })
