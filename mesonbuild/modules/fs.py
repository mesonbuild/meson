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

import typing
from pathlib import Path

from . import ExtensionModule
from . import ModuleReturnValue
from ..mesonlib import MesonException

from ..interpreterbase import stringArgs, noKwargs
if typing.TYPE_CHECKING:
    from ..interpreter import ModuleState

class FSModule(ExtensionModule):

    def __init__(self, interpreter):
        super().__init__(interpreter)
        self.snippets.add('generate_dub_file')

    @stringArgs
    @noKwargs
    def exists(self, state: 'ModuleState', args: typing.Sequence[str], kwargs: dict) -> ModuleReturnValue:
        if len(args) != 1:
            MesonException('method takes exactly one argument.')
        test_file = Path(state.source_root) / state.subdir / args[0]
        return ModuleReturnValue(test_file.exists(), [])

    def _check(self, check: str, state: 'ModuleState', args: typing.Sequence[str]) -> ModuleReturnValue:
        if len(args) != 1:
            MesonException('method takes exactly one argument.')
        test_file = Path(state.source_root) / state.subdir / args[0]
        return ModuleReturnValue(getattr(test_file, check)(), [])

    @stringArgs
    @noKwargs
    def is_symlink(self, state: 'ModuleState', args: typing.Sequence[str], kwargs: dict) -> ModuleReturnValue:
        return self._check('is_symlink', state, args)

    @stringArgs
    @noKwargs
    def is_file(self, state: 'ModuleState', args: typing.Sequence[str], kwargs: dict) -> ModuleReturnValue:
        return self._check('is_file', state, args)

    @stringArgs
    @noKwargs
    def is_dir(self, state: 'ModuleState', args: typing.Sequence[str], kwargs: dict) -> ModuleReturnValue:
        return self._check('is_dir', state, args)

def initialize(*args, **kwargs) -> FSModule:
    return FSModule(*args, **kwargs)
