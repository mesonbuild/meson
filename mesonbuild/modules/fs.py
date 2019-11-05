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

import os

from . import ExtensionModule
from . import ModuleReturnValue
from ..mesonlib import MesonException

from ..interpreterbase import stringArgs, noKwargs

class FSModule(ExtensionModule):

    def __init__(self, interpreter):
        super().__init__(interpreter)
        self.snippets.add('generate_dub_file')

    @stringArgs
    @noKwargs
    def exists(self, state, args, kwargs):
        if len(args) != 1:
            MesonException('method takes exactly one argument.')
        test_file = os.path.join(state.source_root, state.subdir, args[0])
        return ModuleReturnValue(os.path.exists(test_file), [])

    def _check(self, check_fun, state, args):
        if len(args) != 1:
            MesonException('method takes exactly one argument.')
        test_file = os.path.join(state.source_root, state.subdir, args[0])
        return ModuleReturnValue(check_fun(test_file), [])

    @stringArgs
    @noKwargs
    def is_symlink(self, state, args, kwargs):
        return self._check(os.path.islink, state, args)

    @stringArgs
    @noKwargs
    def is_file(self, state, args, kwargs):
        return self._check(os.path.isfile, state, args)

    @stringArgs
    @noKwargs
    def is_dir(self, state, args, kwargs):
        return self._check(os.path.isdir, state, args)

def initialize(*args, **kwargs):
    return FSModule(*args, **kwargs)
