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

class FixUnusedImports(PostProcessBase):
    def __init__(self):
        super().__init__('fix-imports', [('autoflake', 'https://pypi.org/project/autoflake')])

    def check(self) -> bool:
        try:
            import autoflake  # type: ignore # noqa
        except ImportError:
            return False
        return True

    def apply(self, raw: str) -> str:
        import autoflake
        return autoflake.fix_code(raw, remove_duplicate_keys=True, remove_all_unused_imports=True)
