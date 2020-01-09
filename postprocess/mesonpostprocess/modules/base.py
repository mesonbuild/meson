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

import typing as T

class PostProcessBase:
    def __init__(self, name: str, imports: T.List[T.Tuple[str, str]]) -> None:
        self.name = name
        self.imports = imports

    def check(self) -> bool:
        raise NotImplementedError(f'check() is not implemented for {self.name}')

    def apply(self, raw: str) -> str:
        raise NotImplementedError(f'apply() is not implemented for {self.name}')
