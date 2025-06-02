# SPDX-License-Identifier: Apache-2.0
# Copyright © 2022-2024 Intel Corporation

"""Type definitions for cargo manifest files."""

from __future__ import annotations
import dataclasses
import os
import typing as T

from . import version
from ..mesonlib import MesonException
from .. import mlog

if T.TYPE_CHECKING:
    from typing_extensions import Literal, Protocol, Self

    # Copied from typeshed. Blarg that they don't expose this
    class DataclassInstance(Protocol):
        __dataclass_fields__: T.ClassVar[dict[str, dataclasses.Field[T.Any]]]

    EDITION = Literal['2015', '2018', '2021']
    CRATE_TYPE = Literal['bin', 'lib', 'dylib', 'staticlib', 'cdylib', 'rlib', 'proc-macro']

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


def _raw_mapping_to_attributes(raw: T.Dict[str, T.Any], cls: T.Union[DataclassInstance, T.Type[DataclassInstance]],
                               msg: str, convert_version: bool = False) -> T.Dict[str, T.Any]:
    """Fixup raw cargo mappings to ones more suitable for python to consume as dataclass.

    * Replaces any `-` with `_` in the keys.
    * Convert Dependency versions from the cargo format to something meson
      understands.
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
    raw = {fixup_meson_varname(k): v for k, v in raw.items()}
    unexpected = set(raw) - {x.name for x in dataclasses.fields(cls)}
    if unexpected:
        mlog.warning(msg, 'has unexpected keys', '"{}".'.format(', '.join(sorted(unexpected))),
                     _EXTRA_KEYS_WARNING)
        for k in unexpected:
            del raw[k]
    if convert_version:
        raw['version'] = version.convert(raw['version'])
    return raw


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
    def from_raw(cls, raw: T.Dict[str, T.Any]) -> Self:
        fixed = _raw_mapping_to_attributes(raw, cls, f'Package entry {raw["name"]}')
        return cls(**fixed)

@dataclasses.dataclass
class SystemDependency:

    """ Representation of a Cargo system-deps entry
        https://docs.rs/system-deps/latest/system_deps
    """

    name: str
    version: T.List[str]
    optional: bool = False
    feature: T.Optional[str] = None
    feature_overrides: T.Dict[str, T.Dict[str, str]] = dataclasses.field(default_factory=dict)

    @classmethod
    def from_raw(cls, name: str, raw: T.Union[T.Dict[str, T.Any], str]) -> SystemDependency:
        if isinstance(raw, str):
            return cls(name, SystemDependency.convert_version(raw))
        name = raw.get('name', name)
        version = SystemDependency.convert_version(raw.get('version'))
        optional = raw.get('optional', False)
        feature = raw.get('feature')
        # Everything else are overrides when certain features are enabled.
        feature_overrides = {k: v for k, v in raw.items() if k not in {'name', 'version', 'optional', 'feature'}}
        return cls(name, version, optional, feature, feature_overrides)

    @staticmethod
    def convert_version(version: T.Optional[str]) -> T.List[str]:
        vers = version.split(',') if version is not None else []
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

    name: dataclasses.InitVar[str]
    version: T.List[str]
    registry: T.Optional[str] = None
    git: T.Optional[str] = None
    branch: T.Optional[str] = None
    rev: T.Optional[str] = None
    path: T.Optional[str] = None
    optional: bool = False
    package: str = ''
    default_features: bool = True
    features: T.List[str] = dataclasses.field(default_factory=list)

    api: str = dataclasses.field(init=False)

    def __post_init__(self, name: str) -> None:
        self.package = self.package or name
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
    def from_raw(cls, name: str, raw: T.Union[T.Dict[str, T.Any], str]) -> Dependency:
        """Create a dependency from a raw cargo dictionary"""
        if isinstance(raw, str):
            return cls(name, version.convert(raw))
        fixed = _raw_mapping_to_attributes(raw, cls, f'Dependency entry {name}', convert_version=True)
        return cls(name, **fixed)


@dataclasses.dataclass
class BuildTarget:

    name: str
    crate_type: T.List[CRATE_TYPE] = dataclasses.field(default_factory=lambda: ['lib'])
    path: dataclasses.InitVar[T.Optional[str]] = None

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
    def from_raw(cls, raw: T.Dict[str, T.Any]) -> Self:
        name = raw.get('name', '<anonymous>')
        build = _raw_mapping_to_attributes(raw, cls, f'Binary entry {name}')
        return cls(**build)

@dataclasses.dataclass
class Library(BuildTarget):

    """Representation of a Cargo Library Entry."""

    doctest: bool = True
    doc: bool = True
    path: str = os.path.join('src', 'lib.rs')
    proc_macro: bool = False
    crate_type: T.List[CRATE_TYPE] = dataclasses.field(default_factory=lambda: ['lib'])
    doc_scrape_examples: bool = True

    @classmethod
    def from_raw(cls, raw: T.Dict[str, T.Any], fallback_name: str) -> Self:  # type: ignore[override]
        # We need to set the name field if it's not set manually, including if
        # other fields are set in the lib section
        raw.setdefault('name', fallback_name)
        fixed = _raw_mapping_to_attributes(raw, cls, f'Library entry {raw["name"]}')
        return cls(**fixed)


@dataclasses.dataclass
class Binary(BuildTarget):

    """Representation of a Cargo Bin Entry."""

    doc: bool = True


@dataclasses.dataclass
class Test(BuildTarget):

    """Representation of a Cargo Test Entry."""

    bench: bool = True


@dataclasses.dataclass
class Benchmark(BuildTarget):

    """Representation of a Cargo Benchmark Entry."""

    test: bool = True


@dataclasses.dataclass
class Example(BuildTarget):

    """Representation of a Cargo Example Entry."""

    crate_type: T.List[CRATE_TYPE] = dataclasses.field(default_factory=lambda: ['bin'])


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
    def from_raw(cls, raw: T.Dict[str, T.Any], path: str = '') -> Manifest:
        return cls(
            Package.from_raw(raw['package']),
            {k: Dependency.from_raw(k, v) for k, v in raw.get('dependencies', {}).items()},
            {k: Dependency.from_raw(k, v) for k, v in raw.get('dev-dependencies', {}).items()},
            {k: Dependency.from_raw(k, v) for k, v in raw.get('build-dependencies', {}).items()},
            Library.from_raw(raw.get('lib', {}), raw['package']['name']),
            [Binary.from_raw(b) for b in raw.get('bin', {})],
            [Test.from_raw(b) for b in raw.get('test', {})],
            [Benchmark.from_raw(b) for b in raw.get('bench', {})],
            [Example.from_raw(b) for b in raw.get('example', {})],
            raw.get('features', {}),
            {k: {k2: Dependency.from_raw(k2, v2) for k2, v2 in v.get('dependencies', {}).items()}
                for k, v in raw.get('target', {}).items()},
            path,
        )


@dataclasses.dataclass
class CargoLockPackage:

    """A description of a package in the Cargo.lock file format."""

    name: str
    version: str
    source: T.Optional[str] = None
    checksum: T.Optional[str] = None

    @classmethod
    def from_raw(cls, raw: T.Dict[str, T.Any]) -> CargoLockPackage:
        fixed = _raw_mapping_to_attributes(raw, cls, 'Cargo.lock package')
        return cls(**fixed)


@dataclasses.dataclass
class CargoLock:

    """A description of the Cargo.lock file format."""

    version: str
    package: T.List[CargoLockPackage]
    metadata: T.Dict[str, str]

    @classmethod
    def from_raw(cls, raw: T.Dict[str, T.Any]) -> CargoLock:
        fixed = _raw_mapping_to_attributes(raw, cls, 'Cargo.lock')
        return cls(
            fixed['version'],
            [CargoLockPackage.from_raw(i) for i in fixed['package']],
            fixed.get('metadata', {}),
        )
