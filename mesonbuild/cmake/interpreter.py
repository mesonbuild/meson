# Copyright 2019 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This class contains the basic functionality needed to run any interpreter
# or an interpreter-based tool.

from .common import CMakeException
from .client import CMakeClient
from .. import mlog
from ..build import Build
from ..environment import Environment
from ..backend.backends import Backend
import os

CMAKE_BACKEND_GENERATOR_MAP = {
    'ninja': 'Ninja',
    'xcode': 'Xcode',
    'vs2010': 'Visual Studio 10 2010',
    'vs2015': 'Visual Studio 15 2017',
    'vs2017': 'Visual Studio 15 2017',
}

class CMakeInterpreter:
    def __init__(self, build: Build, src_dir: str, build_dir: str, env: Environment, backend: Backend):
        assert(hasattr(backend, 'name'))
        self.build = build
        self.src_dir = src_dir
        self.build_dir = build_dir
        self.env = env
        self.backend_name = backend.name
        self.client = CMakeClient(self.env)
        os.makedirs(self.build_dir, exist_ok=True)

    def run(self) -> None:
        with self.client.connect():
            generator = CMAKE_BACKEND_GENERATOR_MAP[self.backend_name]
            self.client.do_handshake(self.src_dir, self.build_dir, generator, 1)
