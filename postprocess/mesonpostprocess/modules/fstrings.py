#!/usr/bin/env python3

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

from .base import PostProcessBase

class ConvertFStrings(PostProcessBase):
    def __init__(self):
        super().__init__('f-strings', [('f2format', 'https://pypi.org/project/f2format')])

    def check(self) -> bool:
        try:
            import f2format  # type: ignore # noqa
        except ImportError:
            return False
        return True

    def apply(self, raw: str) -> str:
        import f2format
        return f2format.convert(raw)
