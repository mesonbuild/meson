# Copyright 2015 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from . import ExtensionModule
from ..interpreterbase import noKwargs

class TestModule(ExtensionModule):
    def __init__(self, interpreter):
        super().__init__(interpreter)
        self.methods.update({
            'print_hello': self.print_hello,
        })

    @noKwargs
    def print_hello(self, state, args, kwargs):
        print('Hello from a Meson module')

def initialize(*args, **kwargs):
    return TestModule(*args, **kwargs)
