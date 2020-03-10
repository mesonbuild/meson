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

import typing as T
import hashlib
from pathlib import Path, PurePath, PureWindowsPath

from .. import mlog
from . import ExtensionModule
from . import ModuleReturnValue
from ..mesonlib import MesonException
from ..interpreterbase import FeatureNew

from ..interpreterbase import stringArgs, noKwargs
if T.TYPE_CHECKING:
    from ..interpreter import ModuleState

class FSModule(ExtensionModule):

    def __init__(self, interpreter):
        super().__init__(interpreter)
        self.methods.update({'expanduser': self.expanduser_method,
                             'is_absolute': self.is_absolute_method,
                             'as_posix': self.as_posix_method,
                             'exists': self.exists_method,
                             'is_symlink': self.is_symlink_method,
                             'is_file': self.is_file_method,
                             'is_dir': self.is_dir_method,
                             'hash': self.hash_method,
                             'size': self.size_method,
                             'is_samepath': self.is_samepath_method,
                             'replace_suffix': self.replace_suffix_method,
                             'parent': self.parent_method,
                             'name': self.name_method,
                             'stem': self.stem_method,
                             })

    def _absolute_dir(self, state: 'ModuleState', arg: str) -> Path:
        """
        make an absolute path from a relative path, WITHOUT resolving symlinks
        """
        return Path(state.source_root) / state.subdir / Path(arg).expanduser()

    def _resolve_dir(self, state: 'ModuleState', arg: str) -> Path:
        """
        resolves symlinks and makes absolute a directory relative to calling meson.build,
        if not already absolute
        """
        path = self._absolute_dir(state, arg)
        try:
            # accomodate unresolvable paths e.g. symlink loops
            path = path.resolve()
        except Exception:
            # return the best we could do
            pass
        return path

    def _check(self, check: str, state: 'ModuleState', args: T.Sequence[str]) -> str:
        if len(args) != 1:
            raise MesonException('fs.{} takes exactly one argument.'.format(check))
        test_file = self._resolve_dir(state, args[0])
        val = getattr(test_file, check)()
        if isinstance(val, Path):
            val = str(val)
        return val

    @stringArgs
    @noKwargs
    @FeatureNew('fs.expanduser', '0.54.0')
    def expanduser_method(self, state: 'ModuleState', args: T.Sequence[str], kwargs: dict) -> str:
        if len(args) != 1:
            raise MesonException('fs.expanduser takes exactly one argument.')
        return str(Path(args[0]).expanduser())

    @stringArgs
    @noKwargs
    @FeatureNew('fs.is_absolute', '0.54.0')
    def is_absolute_method(self, state: 'ModuleState', args: T.Sequence[str], kwargs: dict) -> bool:
        if len(args) != 1:
            raise MesonException('fs.is_absolute takes exactly one argument.')
        return PurePath(args[0]).is_absolute()

    @stringArgs
    @noKwargs
    @FeatureNew('fs.as_posix', '0.54.0')
    def as_posix_method(self, state: 'ModuleState', args: T.Sequence[str], kwargs: dict) -> str:
        """
        this function assumes you are passing a Windows path, even if on a Unix-like system
        and so ALL '\' are turned to '/', even if you meant to escape a character
        """
        if len(args) != 1:
            raise MesonException('fs.as_posix takes exactly one argument.')
        return PureWindowsPath(args[0]).as_posix()

    @stringArgs
    @noKwargs
    def exists_method(self, state: 'ModuleState', args: T.Sequence[str], kwargs: dict) -> str:
        return self._check('exists', state, args)

    @stringArgs
    @noKwargs
    def is_symlink_method(self, state: 'ModuleState', args: T.Sequence[str], kwargs: dict) -> bool:
        if len(args) != 1:
            raise MesonException('fs.is_symlink takes exactly one argument.')
        return self._absolute_dir(state, args[0]).is_symlink()

    @stringArgs
    @noKwargs
    def is_file_method(self, state: 'ModuleState', args: T.Sequence[str], kwargs: dict) -> str:
        return self._check('is_file', state, args)

    @stringArgs
    @noKwargs
    def is_dir_method(self, state: 'ModuleState', args: T.Sequence[str], kwargs: dict) -> str:
        return self._check('is_dir', state, args)

    @stringArgs
    @noKwargs
    def hash_method(self, state: 'ModuleState', args: T.Sequence[str], kwargs: dict) -> str:
        if len(args) != 2:
            raise MesonException('fs.hash takes exactly two arguments.')
        file = self._resolve_dir(state, args[0])
        if not file.is_file():
            raise MesonException('{} is not a file and therefore cannot be hashed'.format(file))
        try:
            h = hashlib.new(args[1])
        except ValueError:
            raise MesonException('hash algorithm {} is not available'.format(args[1]))
        mlog.debug('computing {} sum of {} size {} bytes'.format(args[1], file, file.stat().st_size))
        h.update(file.read_bytes())
        return h.hexdigest()

    @stringArgs
    @noKwargs
    def size_method(self, state: 'ModuleState', args: T.Sequence[str], kwargs: dict) -> int:
        if len(args) != 1:
            raise MesonException('fs.size takes exactly one argument.')
        file = self._resolve_dir(state, args[0])
        if not file.is_file():
            raise MesonException('{} is not a file and therefore cannot be sized'.format(file))
        try:
            return file.stat().st_size
        except ValueError:
            raise MesonException('{} size could not be determined'.format(args[0]))

    @stringArgs
    @noKwargs
    def is_samepath_method(self, state: 'ModuleState', args: T.Sequence[str], kwargs: dict) -> bool:
        if len(args) != 2:
            raise MesonException('fs.is_samepath takes exactly two arguments.')
        file1 = self._resolve_dir(state, args[0])
        file2 = self._resolve_dir(state, args[1])
        if not file1.exists():
            return False
        if not file2.exists():
            return False
        try:
            return file1.samefile(file2)
        except OSError:
            return False

    @stringArgs
    @noKwargs
    def replace_suffix_method(self, state: 'ModuleState', args: T.Sequence[str], kwargs: dict) -> str:
        if len(args) != 2:
            raise MesonException('fs.replace_suffix takes exactly two arguments.')
        original = PurePath(args[0])
        new = original.with_suffix(args[1])
        return str(new)

    @stringArgs
    @noKwargs
    def parent_method(self, state: 'ModuleState', args: T.Sequence[str], kwargs: dict) -> str:
        if len(args) != 1:
            raise MesonException('fs.parent takes exactly one argument.')
        original = PurePath(args[0])
        new = original.parent
        return str(new)

    @stringArgs
    @noKwargs
    def name_method(self, state: 'ModuleState', args: T.Sequence[str], kwargs: dict) -> str:
        if len(args) != 1:
            raise MesonException('fs.name takes exactly one argument.')
        original = PurePath(args[0])
        new = original.name
        return str(new)

    @stringArgs
    @noKwargs
    @FeatureNew('fs.stem', '0.54.0')
    def stem_method(self, state: 'ModuleState', args: T.Sequence[str], kwargs: dict) -> str:
        if len(args) != 1:
            raise MesonException('fs.stem takes exactly one argument.')
        original = PurePath(args[0])
        new = original.stem
        return str(new)

def initialize(*args, **kwargs) -> FSModule:
    return FSModule(*args, **kwargs)
