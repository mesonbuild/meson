# Copyright 2014-2016 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .vs2010backend import Vs2010Backend


class Vs2015Backend(Vs2010Backend):
    def __init__(self, build):
        super().__init__(build)
        self.name = 'vs2015'
        self.platform_toolset = 'v140'
        self.vs_version = '2015'
