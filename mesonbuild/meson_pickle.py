# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson development team

from __future__ import annotations

import contextlib
import pickle
import typing as T

from .mesonlib import MesonException

if T.TYPE_CHECKING:
    from typing_extensions import Protocol

    from .environment import Environment

    class _EnvPickleLoadable(Protocol):

        environment: Environment

    class _VerPickleLoadable(Protocol):

        version: str

    # A generic type for pickle_load. This allows any type that has either a
    # .version or a .environment to be passed.
    _PL = T.TypeVar('_PL', bound=T.Union[_EnvPickleLoadable, _VerPickleLoadable])


def dump(obj: object, file: T.IO[bytes]) -> None:
    pickle.dump(obj, file)


def load_unchecked(file: T.IO[bytes]) -> T.Any:
    """Load an object without checking its type or version."""
    return pickle.load(file)


class PickleLoadException(MesonException):
    """A saved file cannot be used, because it is corrupted or outdated.

    If :param suggest_reconfigure: is set, the message suggests to recreate the file.
    """

    HINT = ' Consider reconfiguring the directory with "meson setup --reconfigure".'

    def __init__(self, message: str, suggest_reconfigure: bool = True) -> None:
        super().__init__(message + (self.HINT if suggest_reconfigure else ''))


@contextlib.contextmanager
def open_pickle(filename: str, object_name: str,
                suggest_reconfigure: bool = True) -> T.Iterator[T.IO[bytes]]:
    """Open a file for loading, and report corrupted or outdated contents as MesonException."""
    with open(filename, 'rb') as f:
        try:
            yield f
        except (pickle.UnpicklingError, EOFError):
            raise PickleLoadException(f'{object_name} file {filename!r} is corrupted.',
                                      suggest_reconfigure)
        except (TypeError, ModuleNotFoundError, AttributeError):
            raise PickleLoadException(
                f"{object_name} file {filename!r} references functions or classes that don't "
                "exist. This probably means that it was generated with an old "
                "version of meson.", suggest_reconfigure)


def check_loaded(obj: object, filename: str, object_name: str, object_type: T.Type[_PL],
                 suggest_reconfigure: bool = True) -> _PL:
    """Check the type of a loaded object and the version of Meson that saved it."""
    if not isinstance(obj, object_type):
        raise PickleLoadException(f'{object_name} file {filename!r} is corrupted.',
                                  suggest_reconfigure)

    # Because these Protocols are not available at runtime (and cannot be made
    # available at runtime until we drop support for Python < 3.8), we have to
    # do a bit of hackery so that mypy understands what's going on here
    version: str
    if hasattr(obj, 'version'):
        version = T.cast('_VerPickleLoadable', obj).version
    else:
        version = T.cast('_EnvPickleLoadable', obj).environment.coredata.version

    from .coredata import version as coredata_version
    from .coredata import major_versions_differ, MesonVersionMismatchException
    if major_versions_differ(version, coredata_version):
        raise MesonVersionMismatchException(version, coredata_version, suggest_reconfigure)
    return obj


def load(filename: str, object_name: str, object_type: T.Type[_PL], suggest_reconfigure: bool = True,
         env: T.Optional[Environment] = None) -> _PL:
    """Load an object from a file, checking its type and the version of Meson that saved it."""
    with open_pickle(filename, object_name, suggest_reconfigure) as f:
        obj = load_unchecked(f)
    return check_loaded(obj, filename, object_name, object_type, suggest_reconfigure)
