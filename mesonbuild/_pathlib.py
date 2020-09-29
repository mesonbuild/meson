# Copyright 2020 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import typing as T

# Python 3.5 does not have the strict kwarg for resolve and always
# behaves like calling resolve with strict=True in Python 3.6+
#
# This module emulates the behavior of Python 3.6+ by in Python 3.5 by
# overriding the resolve method with a bit of custom logic
#
# TODO: Drop this module as soon as Python 3.5 support is dropped

if T.TYPE_CHECKING:
    from pathlib import Path
else:
    if sys.version_info.major <= 3 and sys.version_info.minor <= 5:

        # Inspired by https://codereview.stackexchange.com/questions/162426/subclassing-pathlib-path
        import pathlib
        import os

        # Can not directly inherit from pathlib.Path because the __new__
        # operator of pathlib.Path() returns a {Posix,Windows}Path object.
        class Path(type(pathlib.Path())):
            def resolve(self, strict: bool = False) -> 'Path':
                try:
                    return super().resolve()
                except FileNotFoundError:
                    if strict:
                        raise
                    return Path(os.path.normpath(str(self)))

    else:
        from pathlib import Path

from pathlib import PurePath, PureWindowsPath, PurePosixPath
