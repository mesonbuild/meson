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
import os
from pathlib import Path, PurePath, PureWindowsPath

from .. import mlog
from . import ExtensionModule
from . import ModuleReturnValue
from ..mesonlib import (
    File,
    FileOrString,
    MesonException,
    path_is_in_root,
)
from ..interpreterbase import FeatureNew, typed_pos_args, noKwargs, permittedKwargs

if T.TYPE_CHECKING:
    from . import ModuleState
    from ..interpreter import Interpreter


class FSModule(ExtensionModule):

    def __init__(self, interpreter: 'Interpreter') -> None:
        super().__init__(interpreter)
        self.snippets.add('generate_dub_file')

    def _absolute_dir(self, state: 'ModuleState', arg: str) -> Path:
        """
        make an absolute path from a relative path, WITHOUT resolving symlinks
        """
        return Path(state.source_root) / Path(state.subdir) / Path(arg).expanduser()

    def _resolve_dir(self, state: 'ModuleState', arg: str) -> Path:
        """
        resolves symlinks and makes absolute a directory relative to calling meson.build,
        if not already absolute
        """
        path = self._absolute_dir(state, arg)
        try:
            # accommodate unresolvable paths e.g. symlink loops
            path = path.resolve()
        except Exception:
            # return the best we could do
            pass
        return path

    def _check(self, check: str, state: 'ModuleState', args: T.Sequence[str]) -> ModuleReturnValue:
        test_file = self._resolve_dir(state, args[0])
        val = getattr(test_file, check)()
        if isinstance(val, Path):
            val = str(val)
        return ModuleReturnValue(val, [])

    @noKwargs
    @FeatureNew('fs.expanduser', '0.54.0')
    @typed_pos_args('fs.expanduser', str)
    def expanduser(self, state: 'ModuleState', args: T.Tuple[str], kwargs: T.Dict[str, T.Any]) -> ModuleReturnValue:
        return ModuleReturnValue(str(Path(args[0]).expanduser()), [])

    @noKwargs
    @FeatureNew('fs.is_absolute', '0.54.0')
    @typed_pos_args('fs.is_absolute', str)
    def is_absolute(self, state: 'ModuleState', args: T.Tuple[str], kwargs: T.Dict[str, T.Any]) -> ModuleReturnValue:
        return ModuleReturnValue(PurePath(args[0]).is_absolute(), [])

    @noKwargs
    @FeatureNew('fs.as_posix', '0.54.0')
    @typed_pos_args('fs.as_posix', str)
    def as_posix(self, state: 'ModuleState', args: T.Tuple[str], kwargs: T.Dict[str, T.Any]) -> ModuleReturnValue:
        """
        this function assumes you are passing a Windows path, even if on a Unix-like system
        and so ALL '\' are turned to '/', even if you meant to escape a character
        """
        return ModuleReturnValue(PureWindowsPath(args[0]).as_posix(), [])

    @noKwargs
    @typed_pos_args('fs.exists', str)
    def exists(self, state: 'ModuleState', args: T.Tuple[str], kwargs: T.Dict[str, T.Any]) -> ModuleReturnValue:
        return self._check('exists', state, args)

    @noKwargs
    @typed_pos_args('fs.is_symlink', str)
    def is_symlink(self, state: 'ModuleState', args: T.Tuple[str], kwargs: T.Dict[str, T.Any]) -> ModuleReturnValue:
        return ModuleReturnValue(self._absolute_dir(state, args[0]).is_symlink(), [])

    @noKwargs
    @typed_pos_args('fs.is_file', str)
    def is_file(self, state: 'ModuleState', args: T.Tuple[str], kwargs: T.Dict[str, T.Any]) -> ModuleReturnValue:
        return self._check('is_file', state, args)

    @noKwargs
    @typed_pos_args('fs.is_dir', str)
    def is_dir(self, state: 'ModuleState', args: T.Tuple[str], kwargs: T.Dict[str, T.Any]) -> ModuleReturnValue:
        return self._check('is_dir', state, args)

    @noKwargs
    @typed_pos_args('fs.hash', str, str)
    def hash(self, state: 'ModuleState', args: T.Tuple[str, str], kwargs: T.Dict[str, T.Any]) -> ModuleReturnValue:
        file = self._resolve_dir(state, args[0])
        if not file.is_file():
            raise MesonException(f'{file} is not a file and therefore cannot be hashed')
        try:
            h = hashlib.new(args[1])
        except ValueError:
            raise MesonException('hash algorithm {} is not available'.format(args[1]))
        mlog.debug('computing {} sum of {} size {} bytes'.format(args[1], file, file.stat().st_size))
        h.update(file.read_bytes())
        return ModuleReturnValue(h.hexdigest(), [])

    @noKwargs
    @typed_pos_args('fs.size', str)
    def size(self, state: 'ModuleState', args: T.Tuple[str], kwargs: T.Dict[str, T.Any]) -> ModuleReturnValue:
        file = self._resolve_dir(state, args[0])
        if not file.is_file():
            raise MesonException(f'{file} is not a file and therefore cannot be sized')
        try:
            return ModuleReturnValue(file.stat().st_size, [])
        except ValueError:
            raise MesonException('{} size could not be determined'.format(args[0]))

    @noKwargs
    @typed_pos_args('fs.is_samepath', str, str)
    def is_samepath(self, state: 'ModuleState', args: T.Tuple[str, str], kwargs: T.Dict[str, T.Any]) -> ModuleReturnValue:
        file1 = self._resolve_dir(state, args[0])
        file2 = self._resolve_dir(state, args[1])
        if not file1.exists():
            return ModuleReturnValue(False, [])
        if not file2.exists():
            return ModuleReturnValue(False, [])
        try:
            return ModuleReturnValue(file1.samefile(file2), [])
        except OSError:
            return ModuleReturnValue(False, [])

    @noKwargs
    @typed_pos_args('fs.replace_suffix', str, str)
    def replace_suffix(self, state: 'ModuleState', args: T.Tuple[str, str], kwargs: T.Dict[str, T.Any]) -> ModuleReturnValue:
        original = PurePath(args[0])
        new = original.with_suffix(args[1])
        return ModuleReturnValue(str(new), [])

    @noKwargs
    @typed_pos_args('fs.parent', str)
    def parent(self, state: 'ModuleState', args: T.Tuple[str], kwargs: T.Dict[str, T.Any]) -> ModuleReturnValue:
        original = PurePath(args[0])
        new = original.parent
        return ModuleReturnValue(str(new), [])

    @noKwargs
    @typed_pos_args('fs.name', str)
    def name(self, state: 'ModuleState', args: T.Tuple[str], kwargs: T.Dict[str, T.Any]) -> ModuleReturnValue:
        original = PurePath(args[0])
        new = original.name
        return ModuleReturnValue(str(new), [])

    @noKwargs
    @typed_pos_args('fs.stem', str)
    @FeatureNew('fs.stem', '0.54.0')
    def stem(self, state: 'ModuleState', args: T.Tuple[str], kwargs: T.Dict[str, T.Any]) -> ModuleReturnValue:
        original = PurePath(args[0])
        new = original.stem
        return ModuleReturnValue(str(new), [])

    @FeatureNew('fs.read', '0.57.0')
    @permittedKwargs({'encoding'})
    @typed_pos_args('fs.read', (str, File))
    def read(self, state: 'ModuleState', args: T.Tuple['FileOrString'], kwargs: T.Dict[str, T.Any]) -> ModuleReturnValue:
        """Read a file from the source tree and return its value as a decoded
        string.

        If the encoding is not specified, the file is assumed to be utf-8
        encoded. Paths must be relative by default (to prevent accidents) and
        are forbidden to be read from the build directory (to prevent build
        loops)
        """
        path = args[0]
        encoding: str = kwargs.get('encoding', 'utf-8')
        if not isinstance(encoding, str):
            raise MesonException('`encoding` parameter must be a string')

        src_dir = self.interpreter.environment.source_dir
        sub_dir = self.interpreter.subdir
        build_dir = self.interpreter.environment.get_build_dir()

        if isinstance(path, File):
            if path.is_built:
                raise MesonException(
                    'fs.read_file does not accept built files() objects')
            path = os.path.join(src_dir, path.relative_name())
        else:
            if sub_dir:
                src_dir = os.path.join(src_dir, sub_dir)
            path = os.path.join(src_dir, path)

        path = os.path.abspath(path)
        if path_is_in_root(Path(path), Path(build_dir), resolve=True):
            raise MesonException('path must not be in the build tree')
        try:
            with open(path, encoding=encoding) as f:
                data = f.read()
        except UnicodeDecodeError:
            raise MesonException(f'decoding failed for {path}')
        # Reconfigure when this file changes as it can contain data used by any
        # part of the build configuration (e.g. `project(..., version:
        # fs.read_file('VERSION')` or `configure_file(...)`
        self.interpreter.add_build_def_file(path)
        return ModuleReturnValue(data, [])


def initialize(*args: T.Any, **kwargs: T.Any) -> FSModule:
    return FSModule(*args, **kwargs)
