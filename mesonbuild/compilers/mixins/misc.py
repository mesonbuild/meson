# Copyright 2019 The Meson development team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A collection of small unrelated mixins for Compilers."""

import typing as T


class SanitizerMixin:

    def __init__(self):
        if 'b_sanitize' not in self.base_options:
            self.base_options.append('b_sanitize')

    def sanitizer_compile_args(self, value: str) -> T.List[str]:
        if value == 'none':
            return []
        return ['-fsanitize=' + value]
