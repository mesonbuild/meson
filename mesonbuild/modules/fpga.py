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

from . import ModuleReturnValue
from . import ExtensionModule
from . import noKwargs
from . import permittedKwargs

class FPGAModule(ExtensionModule):

    @permittedKwargs({'device','toolchain','constraints','dependencies',
                     'synth_options','map_options','pr_options'})
    def simulation(self, state, args, kwargs):
        rv = ModuleReturnValue(None, [])
        return rv

    @permittedKwargs({'device','toolchain','constraints','dependencies',
                     'synth_options','map_options','pr_options'})
    def bitstream(self, state, args, kwargs):
        rv = ModuleReturnValue("hello", [])
        return rv


def initialize():
    return FPGAModule()
