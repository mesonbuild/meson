# Copyright 2022 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from .backends import Backend
from .. import mlog
from ..mesonlib import MesonBugException


class NoneBackend(Backend):

    name = 'none'

    def generate(self):
        if self.build.get_targets():
            raise MesonBugException('None backend cannot generate target rules, but should have failed earlier.')
        mlog.log('Generating simple install-only backend')
        self.serialize_tests()
        self.create_install_data_files()
