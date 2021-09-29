# Copyright 2016 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# TODO: consider switching to pathlib for this
def destdir_join(d1: str, d2: str) -> str:
    # c:\destdir + c:\prefix must produce c:\destdir\prefix
    if len(d1) > 1 and d1[1] == ':' \
            and len(d2) > 1 and d2[1] == ':':
        return d1 + d2[2:]
    return d1 + d2
