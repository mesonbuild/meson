# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson development team

"""Pickling of objects that refer to the Environment, CoreData and compilers.

The CoreData is saved in its own file.  The Environment that owns it is saved
through the Build object, without the CoreData which is added separately by
build.load().

References from the CoreData to the Environment
are saved through persistent IDs; these are tuples where the first item is its kind:

* ``('environment',)``: the Environment, in files that are loaded after it
  has been created (the CoreData).
"""

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

_ENVIRONMENT = 'environment'
_COMPILER = 'compiler'


class MesonPickler(pickle.Pickler):
    """Pickler for objects that cannot refer to the Environment.

    The Environment is rejected, because it would be saved without its CoreData.
    """

    def persistent_id(self, obj: object) -> T.Optional[T.Tuple[T.Any, ...]]:
        from .environment import Environment

        if isinstance(obj, Environment):
            raise pickle.PicklingError('reference to Environment but none provided')
        return None


class CoreDataPickler(MesonPickler):
    """Pickler that saves references to the Environment instead of the object.

    This is used for the CoreData, which is loaded after the Environment.
    """

    def __init__(self, file: T.IO[bytes], env: Environment) -> None:
        super().__init__(file)
        self.env = env

    def persistent_id(self, obj: object) -> T.Optional[T.Tuple[T.Any, ...]]:
        from .environment import Environment

        if isinstance(obj, Environment):
            if obj is not self.env:
                raise pickle.PicklingError('reference to unknown Environment')
            return (_ENVIRONMENT,)
        return super().persistent_id(obj)


class BuildPickler(MesonPickler):
    """Pickler that saves the Environment of a Build object as an object.

    All references must be to the Environment of the Build, and
    compilers are saved as persistent IDs that will be later resolved
    from the CoreData.
    """

    def __init__(self, file: T.IO[bytes], env: Environment) -> None:
        super().__init__(file)
        self.env = env

    def persistent_id(self, obj: object) -> T.Optional[T.Tuple[T.Any, ...]]:
        from .environment import Environment
        from .coredata import CoreData
        from .compilers import Compiler

        if isinstance(obj, Environment):
            if obj is not self.env:
                raise pickle.PicklingError('reference to unknown Environment')
        elif isinstance(obj, CoreData):
            raise pickle.PicklingError('CoreData must not be included in build.dat')
        elif isinstance(obj, Compiler):
            if self.env.coredata.compilers[obj.for_machine].get(obj.language) is obj:
                return (_COMPILER, obj.for_machine.value, obj.language)
        return None


class Unpickler(pickle.Unpickler):
    """Unpickler that resolves the references saved by the picklers
       through :param env:, which can be None if the
       caller knows that the object does not contain any.
    """

    def __init__(self, file: T.IO[bytes], env: T.Optional[Environment] = None) -> None:
        super().__init__(file)
        self.env = env

    def persistent_load(self, pid: T.Any) -> object:
        kind = pid[0]
        if self.env is None:
            raise pickle.UnpicklingError(f'reference to {kind} without an Environment')
        if kind == _ENVIRONMENT:
            return self.env
        if kind == _COMPILER:
            from .mesonlib import MachineChoice
            try:
                return self.env.coredata.compilers[MachineChoice(pid[1])][pid[2]]
            except KeyError:
                raise pickle.UnpicklingError(f'compiler {pid!r} is not in the CoreData')
        raise pickle.UnpicklingError(f'unsupported persistent ID {pid!r}')


def dump(obj: object, file: T.IO[bytes], env: T.Optional[Environment] = None) -> None:
    """Save an object, using references to the Environment if one is provided."""
    if env is None:
        MesonPickler(file).dump(obj)
    else:
        CoreDataPickler(file, env).dump(obj)


def load_unchecked(file: T.IO[bytes], env: T.Optional[Environment] = None) -> T.Any:
    """Load an object without checking its type or version.

    References are resolved through :param env:.
    """
    return Unpickler(file, env).load()


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
        obj = load_unchecked(f, env)
    return check_loaded(obj, filename, object_name, object_type, suggest_reconfigure)
