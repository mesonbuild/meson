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
import tempfile

class TypeHintsRemover(PostProcessBase):
    def __init__(self):
        super().__init__('strip-hints', [('strip-hints', 'https://pypi.org/project/strip-hints')])

    def check(self) -> bool:
        try:
            import strip_hints  # type: ignore # noqa
        except ImportError:
            return False
        return True

    def apply(self, raw: str) -> str:
        import strip_hints  # type: ignore
        with tempfile.NamedTemporaryFile(mode='w', prefix='meson_strip_hints_', suffix='.py') as fp:
            fp.write(raw)
            fp.flush()
            return strip_hints.strip_file_to_string(fp.name)
