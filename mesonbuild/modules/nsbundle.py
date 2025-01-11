# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 Marco Rebhan <me@dblsaiko.net>

from __future__ import annotations

import typing as T

from . import NewExtensionModule, ModuleInfo

if T.TYPE_CHECKING:
    from mesonbuild.interpreter import Interpreter


def initialize(*args: T.Any, **kwargs: T.Any) -> NSBundleModule:
    return NSBundleModule(*args, **kwargs)


class NSBundleModule(NewExtensionModule):
    INFO = ModuleInfo('nsbundle', '1.7.99')

    def __init__(self, interpreter: Interpreter):
        super().__init__()
        self.methods.update({
        })
