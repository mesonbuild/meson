# SPDX-License-Identifier: Apache-2.0
# Copyright 2012-2021 The Meson development team
# Copyright © 2021-2023 Intel Corporation

"""Utility functions with platform specific implementations."""

from __future__ import annotations

import enum
import os
import sys
import typing as T

from .. import mlog
from .core import MesonException

__all__ = ['DirectoryLock', 'DirectoryLockAction']

class DirectoryLockAction(enum.Enum):
    IGNORE = 0
    WAIT = 1
    FAIL = 2

class DirectoryLockBase:

    lockfile: T.Optional[T.TextIO] = None

    def __init__(self, directory: str, lockfile: str, action: DirectoryLockAction, err: str,
                 optional: bool = False) -> None:
        self.action = action
        self.err = err
        self.lockpath = os.path.join(directory, lockfile)
        self.optional = optional

    def _lock(self) -> None:
        mlog.debug('Calling the no-op version of DirectoryLock')

    def _unlock(self, *args: T.Any) -> None:
        pass

    def __enter__(self) -> None:
        try:
            self.lockfile = open(self.lockpath, 'w+', encoding='utf-8')
        except (FileNotFoundError, IsADirectoryError):
            # For FileNotFoundError, there is nothing to lock.
            # For IsADirectoryError, something is seriously wrong.
            raise
        except OSError:
            if self.action == DirectoryLockAction.IGNORE or self.optional:
                return
            raise

        try:
            self._lock()
        except BlockingIOError:
            self.lockfile.close()
            if self.action == DirectoryLockAction.IGNORE:
                return
            raise MesonException(self.err)
        except PermissionError:
            self.lockfile.close()
            raise MesonException(self.err)

    def __exit__(self, *args: T.Any) -> None:
        if self.lockfile is None or self.lockfile.closed:
            return
        self._unlock()
        self.lockfile.close()

if sys.platform == 'win32':
    import msvcrt

    class DirectoryLock(DirectoryLockBase):
        def _lock(self) -> None:
            mode = msvcrt.LK_LOCK
            if self.action != DirectoryLockAction.WAIT:
                mode = msvcrt.LK_NBLCK
            msvcrt.locking(self.lockfile.fileno(), mode, 1)

        def _unlock(self) -> None:
            msvcrt.locking(self.lockfile.fileno(), msvcrt.LK_UNLCK, 1)
else:
    import fcntl

    class DirectoryLock(DirectoryLockBase):
        def _lock(self) -> None:
            flags = fcntl.LOCK_EX
            if self.action != DirectoryLockAction.WAIT:
                flags = flags | fcntl.LOCK_NB
            fcntl.flock(self.lockfile, flags)

        def _unlock(self) -> None:
            fcntl.flock(self.lockfile, fcntl.LOCK_UN)
