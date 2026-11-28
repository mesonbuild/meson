# SPDX-License-Identifier: Apache-2.0
# Copyright 2025 The Meson development team

from __future__ import annotations

import os
import sys
from pathlib import Path
import typing as T

from ..mesonlib import MesonException


class CrossConfigNotFoundError(MesonException):
    """Raised when no cross-config file matches the requested (os, arch) pair."""


def _xdg_cross_dirs() -> T.List[Path]:
    """Return XDG data directories with ``meson/cross`` appended.

    Mirrors the search logic in ``coredata.__load_config_files``.
    """
    if sys.platform == 'win32':
        return []
    data_home = os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share'))
    data_dirs = os.environ.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share')
    return [Path(data_home) / 'meson' / 'cross'] + [
        Path(d) / 'meson' / 'cross' for d in data_dirs.split(':')
    ]


class CrossConfigRegistry:
    """Registry of built-in and user-override cross-compilation configuration files.

    Search order for a given ``(os, arch)`` pair:
    1. ``~/.meson/cross/<os>-<arch>.ini`` (user override)
    2. ``<repo_root>/cross/<os>-<arch>.ini`` (built-in, source tree)
    3. ``$XDG_DATA_DIRS/meson/cross/<os>-<arch>.ini`` (system install)
    """

    def __init__(self) -> None:
        self._user_dir = Path.home() / '.meson' / 'cross'
        # Source tree: the top-level cross/ directory (relative to this module)
        self._sourcedir_cross = Path(__file__).parent.parent.parent / 'cross'
        self._cache: T.Dict[T.Tuple[str, str], Path] = {}

    def _search_dirs(self) -> T.List[Path]:
        """Return all directories to search, in priority order."""
        dirs = [self._user_dir, self._sourcedir_cross]
        dirs += _xdg_cross_dirs()
        # Also cover pip/virtualenv installs where data_files lands under sys.prefix
        dirs.append(Path(sys.prefix) / 'share' / 'meson' / 'cross')
        return dirs

    def resolve(self, os_name: str, arch: str) -> Path:
        """Resolve a cross-config file for the given target.

        :returns: Absolute path to the ``.ini`` file.
        :raises CrossConfigNotFoundError: if no config matches the pair.
        """
        key = (os_name, arch)
        if key in self._cache:
            return self._cache[key]

        filename = f'{os_name}-{arch}.ini'

        for base_dir in self._search_dirs():
            if not base_dir.is_dir():
                continue
            candidate = base_dir / filename
            if candidate.is_file():
                self._cache[key] = candidate
                return candidate

        known = self.list_available()
        raise CrossConfigNotFoundError(
            f'No cross-compilation configuration found for OS={os_name}, ARCH={arch}.\n'
            f'Available built-in targets: {", ".join(known) if known else "(none)"}\n'
            f'You can create ~/.meson/cross/{filename} to define a custom cross-compilation config.'
        )

    def list_available(self) -> T.List[str]:
        """Return sorted list of available target names (e.g. ``'linux-aarch32'``)."""
        names: T.List[str] = []
        for d in self._search_dirs():
            if d.is_dir():
                for f in d.iterdir():
                    if f.suffix == '.ini':
                        names.append(f.stem)
        return sorted(set(names))
