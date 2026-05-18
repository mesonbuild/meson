# SPDX-License-Identifier: Apache-2.0
# Copyright 2021 The Meson development team

'''
    This module soly exists to work around a pathlib.resolve bug on
    certain Windows systems:

    https://github.com/mesonbuild/meson/issues/7295
    https://bugs.python.org/issue31842

    It should **never** be used directly. Instead, it is automatically
    used when `import pathlib` is used. This is achieved by messing with
    `sys.modules['pathlib']` in mesonmain.

    Additionally, the sole purpose of this module is to work around a
    python bug. This only bugfixes to pathlib functions and classes are
    allowed here. Finally, this file should be removed once all upstream
    python bugs are fixed and it is OK to tell our users to "just upgrade
    python".
'''
from __future__ import annotations

import pathlib
import os
import platform
import sys

__all__ = [
    'PurePath',
    'PurePosixPath',
    'PureWindowsPath',
    'Path',
]

PurePath = pathlib.PurePath
PurePosixPath = pathlib.PurePosixPath
PureWindowsPath = pathlib.PureWindowsPath

# Only patch on platforms where the bug occurs
if platform.system().lower() in {'windows'}:
    # Can not directly inherit from pathlib.Path because the __new__
    # operator of pathlib.Path() returns a {Posix,Windows}Path object.
    # Until Python 3.12, when this was changed so that Path can be directly inherited.
    if sys.version_info >= (3, 12):
        _BASE_CLASS = pathlib.Path
    else:
        _BASE_CLASS = type(pathlib.Path())

    class _Path(_BASE_CLASS):
        def resolve(self, strict: bool = False) -> _Path:
            '''
                Work around a resolve bug on certain Windows systems:

                https://github.com/mesonbuild/meson/issues/7295
                https://bugs.python.org/issue31842
            '''

            try:
                return super().resolve(strict=strict)
            except OSError:
                return _Path(os.path.normpath(self))

    Path: type[_BASE_CLASS] = _Path
else:
    Path = pathlib.Path
    PosixPath = pathlib.PosixPath
    WindowsPath = pathlib.WindowsPath

    __all__ += [
        'PosixPath',
        'WindowsPath',
    ]
