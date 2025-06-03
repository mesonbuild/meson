# SPDX-License-Identifier: Apache-2.0
# Copyright © 2022-2024 Intel Corporation

"""Type definitions for cargo manifest files."""

from __future__ import annotations

import dataclasses
import typing as T

from .. import mlog

if T.TYPE_CHECKING:
    from typing_extensions import Protocol

    from . import raw

    # Copied from typeshed. Blarg that they don't expose this
    class DataclassInstance(Protocol):
        __dataclass_fields__: T.ClassVar[dict[str, dataclasses.Field[T.Any]]]

_DI = T.TypeVar('_DI', bound='DataclassInstance')

_EXTRA_KEYS_WARNING = (
    "This may (unlikely) be an error in the cargo manifest, or may be a missing "
    "implementation in Meson. If this issue can be reproduced with the latest "
    "version of Meson, please help us by opening an issue at "
    "https://github.com/mesonbuild/meson/issues. Please include the crate and "
    "version that is generating this warning if possible."
)


def fixup_meson_varname(name: str) -> str:
    """Fixup a meson variable name

    :param name: The name to fix
    :return: the fixed name
    """
    return name.replace('-', '_')


def _raw_to_dataclass(raw: T.Mapping[str, object], cls: T.Type[_DI],
                      msg: str, **kwargs: T.Callable[[T.Any], object]) -> _DI:
    """Fixup raw cargo mappings to ones more suitable for python to consume as dataclass.

    * Replaces any `-` with `_` in the keys.
    * Optionally pass values through the functions in kwargs, in order to do
      recursive conversions.
    * Remove and warn on keys that are coming from cargo, but are unknown to
      our representations.

    This is intended to give users the possibility of things proceeding when a
    new key is added to Cargo.toml that we don't yet handle, but to still warn
    them that things might not work.

    :param data: The raw data to look at
    :param cls: The Dataclass derived type that will be created
    :param msg: the header for the error message. Usually something like "In N structure".
    :param convert_version: whether to convert the version field to a Meson compatible one.
    :return: The original data structure, but with all unknown keys removed.
    """
    new_dict = {}
    unexpected = set()
    fields = {x.name for x in dataclasses.fields(cls)}
    for orig_k, v in raw.items():
        k = fixup_meson_varname(orig_k)
        if k not in fields:
            unexpected.add(orig_k)
            continue
        if k in kwargs:
            v = kwargs[k](v)
        new_dict[k] = v

    if unexpected:
        mlog.warning(msg, 'has unexpected keys', '"{}".'.format(', '.join(sorted(unexpected))),
                     _EXTRA_KEYS_WARNING)
    return cls(**new_dict)


@dataclasses.dataclass
class CargoLockPackage:

    """A description of a package in the Cargo.lock file format."""

    name: str
    version: str
    source: T.Optional[str] = None
    checksum: T.Optional[str] = None
    dependencies: T.List[str] = dataclasses.field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: raw.CargoLockPackage) -> CargoLockPackage:
        return _raw_to_dataclass(raw, cls, 'Cargo.lock package')


@dataclasses.dataclass
class CargoLock:

    """A description of the Cargo.lock file format."""

    version: int = 1
    package: T.List[CargoLockPackage] = dataclasses.field(default_factory=list)
    metadata: T.Dict[str, str] = dataclasses.field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: raw.CargoLock) -> CargoLock:
        return _raw_to_dataclass(raw, cls, 'Cargo.lock',
                                 package=lambda x: [CargoLockPackage.from_raw(p) for p in x])
