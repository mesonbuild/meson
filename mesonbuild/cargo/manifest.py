# SPDX-License-Identifier: Apache-2.0
# Copyright © 2022-2024 Intel Corporation

"""Type definitions for cargo manifest files."""

from __future__ import annotations

import dataclasses
import os
import typing as T

from . import version
from .. import mlog
from ..mesonlib import MesonException

if T.TYPE_CHECKING:
    from typing_extensions import Protocol, Self

    from . import raw
    from .raw import EDITION, CRATE_TYPE

    # Copied from typeshed. Blarg that they don't expose this
    class DataclassInstance(Protocol):
        __dataclass_fields__: T.ClassVar[dict[str, dataclasses.Field[T.Any]]]

_DI = T.TypeVar('_DI', bound='DataclassInstance')
_R = T.TypeVar('_R', bound='raw._BaseBuildTarget')

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


def _depv_to_dep(depv: raw.DependencyV) -> raw.Dependency:
    return {'version': depv} if isinstance(depv, str) else depv


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
class Package:

    """Representation of a Cargo Package entry, with defaults filled in."""

    name: str
    version: str
    description: T.Optional[str] = None
    resolver: T.Optional[str] = None
    authors: T.List[str] = dataclasses.field(default_factory=list)
    edition: EDITION = '2015'
    rust_version: T.Optional[str] = None
    documentation: T.Optional[str] = None
    readme: T.Optional[str] = None
    homepage: T.Optional[str] = None
    repository: T.Optional[str] = None
    license: T.Optional[str] = None
    license_file: T.Optional[str] = None
    keywords: T.List[str] = dataclasses.field(default_factory=list)
    categories: T.List[str] = dataclasses.field(default_factory=list)
    workspace: T.Optional[str] = None
    build: T.Optional[str] = None
    links: T.Optional[str] = None
    exclude: T.List[str] = dataclasses.field(default_factory=list)
    include: T.List[str] = dataclasses.field(default_factory=list)
    publish: bool = True
    metadata: T.Dict[str, T.Any] = dataclasses.field(default_factory=dict)
    default_run: T.Optional[str] = None
    autolib: bool = True
    autobins: bool = True
    autoexamples: bool = True
    autotests: bool = True
    autobenches: bool = True

    api: str = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        self.api = version.api(self.version)

    @classmethod
    def from_raw(cls, raw_pkg: raw.Package) -> Self:
        return _raw_to_dataclass(raw_pkg, cls, f'Package entry {raw_pkg["name"]}')

@dataclasses.dataclass
class SystemDependency:

    """ Representation of a Cargo system-deps entry
        https://docs.rs/system-deps/latest/system_deps
    """

    name: str
    version: T.List[str]
    optional: bool = False
    feature: T.Optional[str] = None
    # TODO: convert values to dataclass
    feature_overrides: T.Dict[str, T.Dict[str, str]] = dataclasses.field(default_factory=dict)

    @classmethod
    def from_raw(cls, name: str, raw: T.Union[T.Dict[str, T.Any], str]) -> SystemDependency:
        if isinstance(raw, str):
            return cls(name, SystemDependency.convert_version(raw))
        name = raw.get('name', name)
        version = SystemDependency.convert_version(raw.get('version', ''))
        optional = raw.get('optional', False)
        feature = raw.get('feature')
        # Everything else are overrides when certain features are enabled.
        feature_overrides = {k: v for k, v in raw.items() if k not in {'name', 'version', 'optional', 'feature'}}
        return cls(name, version, optional, feature, feature_overrides)

    @staticmethod
    def convert_version(version: T.Optional[str]) -> T.List[str]:
        vers = version.split(',') if version else []
        result: T.List[str] = []
        for v in vers:
            v = v.strip()
            if v[0] not in '><=':
                v = f'>={v}'
            result.append(v)
        return result

    def enabled(self, features: T.Set[str]) -> bool:
        return self.feature is None or self.feature in features

@dataclasses.dataclass
class Dependency:

    """Representation of a Cargo Dependency Entry."""

    package: str
    version: T.List[str]
    registry: T.Optional[str] = None
    git: T.Optional[str] = None
    branch: T.Optional[str] = None
    rev: T.Optional[str] = None
    path: T.Optional[str] = None
    optional: bool = False
    default_features: bool = True
    features: T.List[str] = dataclasses.field(default_factory=list)

    api: str = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        # Extract wanted API version from version constraints.
        api = set()
        for v in self.version:
            if v.startswith(('>=', '==')):
                api.add(version.api(v[2:].strip()))
            elif v.startswith('='):
                api.add(version.api(v[1:].strip()))
        if not api:
            self.api = '0'
        elif len(api) == 1:
            self.api = api.pop()
        else:
            raise MesonException(f'Cannot determine minimum API version from {self.version}.')

    @classmethod
    def from_raw_dict(cls, name: str, raw_dep: raw.Dependency) -> Dependency:
        raw_dep.setdefault('package', name)
        return _raw_to_dataclass(raw_dep, cls, f'Dependency entry {name}',
                                 version=version.convert)

    @classmethod
    def from_raw(cls, name: str, raw_depv: raw.DependencyV) -> Dependency:
        """Create a dependency from a raw cargo dictionary or string"""
        raw_dep = _depv_to_dep(raw_depv)
        return cls.from_raw_dict(name, raw_dep)


@dataclasses.dataclass
class BuildTarget(T.Generic[_R]):

    name: str
    path: str
    crate_type: T.List[CRATE_TYPE] = dataclasses.field(default_factory=lambda: ['lib'])

    # https://doc.rust-lang.org/cargo/reference/cargo-targets.html#the-test-field
    # True for lib, bin, test
    test: bool = True

    # https://doc.rust-lang.org/cargo/reference/cargo-targets.html#the-doctest-field
    # True for lib
    doctest: bool = False

    # https://doc.rust-lang.org/cargo/reference/cargo-targets.html#the-bench-field
    # True for lib, bin, benchmark
    bench: bool = True

    # https://doc.rust-lang.org/cargo/reference/cargo-targets.html#the-doc-field
    # True for libraries and binaries
    doc: bool = False

    harness: bool = True
    edition: EDITION = '2015'
    required_features: T.List[str] = dataclasses.field(default_factory=list)
    plugin: bool = False

    @classmethod
    def from_raw(cls, raw: _R) -> Self:
        name = raw.get('name', '<anonymous>')
        return _raw_to_dataclass(raw, cls, f'Binary entry {name}')

@dataclasses.dataclass
class Library(BuildTarget['raw.LibTarget']):

    """Representation of a Cargo Library Entry."""

    doctest: bool = True
    doc: bool = True
    path: str = os.path.join('src', 'lib.rs')
    proc_macro: bool = False
    crate_type: T.List[CRATE_TYPE] = dataclasses.field(default_factory=lambda: ['lib'])
    doc_scrape_examples: bool = True

    @classmethod
    def from_raw(cls, raw: raw.LibTarget, fallback_name: str) -> Self:  # type: ignore[override]
        # We need to set the name field if it's not set manually, including if
        # other fields are set in the lib section
        raw.setdefault('name', fallback_name)
        return _raw_to_dataclass(raw, cls, f'Library entry {raw["name"]}')


@dataclasses.dataclass
class Binary(BuildTarget['raw.BuildTarget']):

    """Representation of a Cargo Bin Entry."""

    doc: bool = True


@dataclasses.dataclass
class Test(BuildTarget['raw.BuildTarget']):

    """Representation of a Cargo Test Entry."""

    bench: bool = True

@dataclasses.dataclass
class Benchmark(BuildTarget['raw.BuildTarget']):

    """Representation of a Cargo Benchmark Entry."""

    test: bool = True


@dataclasses.dataclass
class Example(BuildTarget['raw.BuildTarget']):

    """Representation of a Cargo Example Entry."""


@dataclasses.dataclass
class Manifest:

    """Cargo Manifest definition.

    Most of these values map up to the Cargo Manifest, but with default values
    if not provided.

    Cargo subprojects can contain what Meson wants to treat as multiple,
    interdependent, subprojects.

    :param path: the path within the cargo subproject.
    """

    package: Package
    dependencies: T.Dict[str, Dependency]
    dev_dependencies: T.Dict[str, Dependency]
    build_dependencies: T.Dict[str, Dependency]
    system_dependencies: T.Dict[str, SystemDependency] = dataclasses.field(init=False)
    lib: Library
    bin: T.List[Binary]
    test: T.List[Test]
    bench: T.List[Benchmark]
    example: T.List[Example]
    features: T.Dict[str, T.List[str]]
    target: T.Dict[str, T.Dict[str, Dependency]]

    path: str = ''

    def __post_init__(self) -> None:
        self.features.setdefault('default', [])
        self.system_dependencies = {k: SystemDependency.from_raw(k, v) for k, v in self.package.metadata.get('system-deps', {}).items()}

    @classmethod
    def from_raw(cls, raw: raw.Manifest, path: str = '') -> Self:
        return cls(
            package=Package.from_raw(raw['package']),
            dependencies={k: Dependency.from_raw(k, v) for k, v in raw.get('dependencies', {}).items()},
            dev_dependencies={k: Dependency.from_raw(k, v) for k, v in raw.get('dev-dependencies', {}).items()},
            build_dependencies={k: Dependency.from_raw(k, v) for k, v in raw.get('build-dependencies', {}).items()},
            lib=Library.from_raw(raw.get('lib', {}), raw['package']['name']),
            bin=[Binary.from_raw(b) for b in raw.get('bin', {})],
            test=[Test.from_raw(b) for b in raw.get('test', {})],
            bench=[Benchmark.from_raw(b) for b in raw.get('bench', {})],
            example=[Example.from_raw(b) for b in raw.get('example', {})],
            features=raw.get('features', {}),
            target={k: {k2: Dependency.from_raw(k2, v2) for k2, v2 in v.get('dependencies', {}).items()}
                    for k, v in raw.get('target', {}).items()},
            path=path,
        )


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
