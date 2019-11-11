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
import hashlib
from pathlib import Path, PurePath

from .. import mlog
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

    def _resolve_dir(self, state: 'ModuleState', arg: str) -> Path:
        """
        resolves (makes absolute) a directory relative to calling meson.build,
        if not already absolute
        """
        return Path(state.source_root) / state.subdir / Path(arg).expanduser()

    def _check(self, check: str, state: 'ModuleState', args: typing.Sequence[str]) -> ModuleReturnValue:
        if len(args) != 1:
            MesonException('fs.{} takes exactly one argument.'.format(check))
        test_file = self._resolve_dir(state, args[0])
        return ModuleReturnValue(getattr(test_file, check)(), [])

    @stringArgs
    @noKwargs
    def exists(self, state: 'ModuleState', args: typing.Sequence[str], kwargs: dict) -> ModuleReturnValue:
        return self._check('exists', state, args)

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

    @stringArgs
    @noKwargs
    def hash(self, state: 'ModuleState', args: typing.Sequence[str], kwargs: dict) -> ModuleReturnValue:
        if len(args) != 2:
            MesonException('method takes exactly two arguments.')
        file = self._resolve_dir(state, args[0])
        if not file.is_file():
            raise MesonException('{} is not a file and therefore cannot be hashed'.format(file))
        try:
            h = hashlib.new(args[1])
        except ValueError:
            raise MesonException('hash algorithm {} is not available'.format(args[1]))
        mlog.debug('computing {} sum of {} size {} bytes'.format(args[1], file, file.stat().st_size))
        h.update(file.read_bytes())
        return ModuleReturnValue(h.hexdigest(), [])

    @stringArgs
    @noKwargs
    def size(self, state: 'ModuleState', args: typing.Sequence[str], kwargs: dict) -> ModuleReturnValue:
        if len(args) != 1:
            MesonException('method takes exactly one argument.')
        file = self._resolve_dir(state, args[0])
        if not file.is_file():
            raise MesonException('{} is not a file and therefore cannot be sized'.format(file))
        try:
            return ModuleReturnValue(file.stat().st_size, [])
        except ValueError:
            raise MesonException('{} size could not be determined'.format(args[0]))

    @stringArgs
    @noKwargs
    def samefile(self, state: 'ModuleState', args: typing.Sequence[str], kwargs: dict) -> ModuleReturnValue:
        if len(args) != 2:
            MesonException('method takes exactly two arguments.')
        file1 = self._resolve_dir(state, args[0])
        file2 = self._resolve_dir(state, args[1])
        if not file1.exists():
            raise MesonException('{} is not a file, symlink or directory and therefore cannot be compared'.format(file1))
        if not file2.exists():
            raise MesonException('{} is not a file, symlink or directory and therefore cannot be compared'.format(file2))
        try:
            return ModuleReturnValue(file1.samefile(file2), [])
        except OSError:
            raise MesonException('{} could not be compared to {}'.format(file1, file2))

    @stringArgs
    @noKwargs
    def with_suffix(self, state: 'ModuleState', args: typing.Sequence[str], kwargs: dict) -> ModuleReturnValue:
        if len(args) != 2:
            MesonException('method takes exactly two arguments.')
        original = PurePath(state.source_root) / state.subdir / args[0]
        new = original.with_suffix(args[1])
        return ModuleReturnValue(str(new), [])


def initialize(*args, **kwargs) -> FSModule:
    return FSModule(*args, **kwargs)
