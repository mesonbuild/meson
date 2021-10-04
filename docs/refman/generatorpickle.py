# Copyright 2021 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pickle
from pathlib import Path
from .generatorbase import GeneratorBase
from .model import ReferenceManual

class GeneratorPickle(GeneratorBase):
    def __init__(self, manual: ReferenceManual, outpath: Path) -> None:
        self.out = outpath
        super().__init__(manual)

    def generate(self) -> None:
        self.out.write_bytes(pickle.dumps(self.manual))
