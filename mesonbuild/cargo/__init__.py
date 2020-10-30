# SPDX-license-identifier: Apache-2.0
# Copyright © 2020-2021 Intel Corporation

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__all__ = [
    'HAS_TOML',
    'ManifestInterpreter',
]

try:
    import toml
    del toml  # so toml isn't exposed
    HAS_TOML = True
except ImportError:
    HAS_TOML = False
else:
    from .cargo import ManifestInterpreter
