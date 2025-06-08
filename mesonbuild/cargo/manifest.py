# SPDX-License-Identifier: Apache-2.0
# Copyright © 2022-2024 Intel Corporation

"""Type definitions for cargo manifest files."""

from __future__ import annotations

import dataclasses
import os
import typing as T

from . import version
from ..mesonlib import MesonException, lazy_property
from .. import mlog

if T.TYPE_CHECKING:
    from typing_extensions import Literal, Protocol, Self

    # Copied from typeshed. Blarg that they don't expose this
    class DataclassInstance(Protocol):
        __dataclass_fields__: T.ClassVar[dict[str, dataclasses.Field[T.Any]]]

    EDITION = Literal['2015', '2018', '2021']
    CRATE_TYPE = Literal['bin', 'lib', 'dylib', 'staticlib', 'cdylib', 'rlib', 'proc-macro']
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


def _raw_to_dataclass(raw: T.Dict[str, T.Any], cls: T.Type[_DI], msg: str, raw_from_workspace: T.Optional[T.Dict[str, T.Any]] = None, **kwargs: T.Callable[[T.Any], object]) -> _DI:
    """Convert and validate raw cargo mappings to a Python dataclass.

    * Inherit values from the workspace.
    * Replaces any `-` with `_` in the keys.
    * Remove and warn on keys that are coming from cargo, but are unknown to
      our representations.
    * If provided, call the validator function on values to validate and convert.

    :param data: The raw data to look at
    :param cls: The Dataclass derived type that will be created
    :param msg: the header for the error message. Usually something like "In N structure".
    :return: An instance of cls.
    """
    unexpected: T.Set[str] = set()
    known = {x.name for x in dataclasses.fields(cls)}
    result: T.Dict[str, T.Any] = {}
    if raw.get('workspace', False):
        del raw['workspace']
        for k, v in raw_from_workspace.items():
            raw.setdefault(k, v)
    for k, v in raw.items():
        if isinstance(v, dict) and v.get('workspace', False):
            v = raw_from_workspace[k]
        k = fixup_meson_varname(k)
        if k not in known:
            unexpected.add(k)
            continue
        validator = kwargs.get(k)
        if validator:
            v = validator(v)
        result[k] = v
    if unexpected:
        mlog.warning(msg, 'has unexpected keys', '"{}".'.format(', '.join(sorted(unexpected))),
                     _EXTRA_KEYS_WARNING)
    return cls(**result)


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

    @lazy_property
    def api(self) -> str:
        return version.api(self.version)

    @classmethod
    def from_raw(cls, raw: T.Dict[str, T.Any], workspace: T.Optional[Workspace] = None) -> Self:
        raw_from_workspace = workspace.package if workspace else None
        return _raw_to_dataclass(raw, cls, f'Package entry {raw["name"]}', raw_from_workspace)

@dataclasses.dataclass
class SystemDependency:

    """ Representation of a Cargo system-deps entry
        https://docs.rs/system-deps/latest/system_deps
    """

    name: str
    version: str = ''
    optional: bool = False
    feature: T.Optional[str] = None
    feature_overrides: T.Dict[str, T.Dict[str, str]] = dataclasses.field(default_factory=dict)

    @classmethod
    def from_raw(cls, name: str, raw: T.Union[T.Dict[str, T.Any], str]) -> SystemDependency:
        if isinstance(raw, str):
            return cls(name, raw)
        name = raw.get('name', name)
        version = raw.get('version', '')
        optional = raw.get('optional', False)
        feature = raw.get('feature')
        # Everything else are overrides when certain features are enabled.
        feature_overrides = {k: v for k, v in raw.items() if k not in {'name', 'version', 'optional', 'feature'}}
        return cls(name, version, optional, feature, feature_overrides)

    @lazy_property
    def meson_version(self) -> T.List[str]:
        vers = self.version.split(',') if self.version else []
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
    version: str = ''
    registry: T.Optional[str] = None
    git: T.Optional[str] = None
    branch: T.Optional[str] = None
    rev: T.Optional[str] = None
    path: T.Optional[str] = None
    optional: bool = False
    default_features: bool = True
    features: T.List[str] = dataclasses.field(default_factory=list)

    @lazy_property
    def api(self) -> str:
        # Extract wanted API version from version constraints.
        if not self.version:
            return ''
        api = set()
        # FIXME: It is probably overkill to convert to Meson versions.
        for v in self.meson_version:
            if v.startswith(('>=', '==')):
                api.add(version.api(v[2:].strip()))
            elif v.startswith('='):
                api.add(version.api(v[1:].strip()))
        if len(api) == 1:
            return api.pop()
        else:
            raise MesonException(f'Cannot determine minimum API version from {self.version}.')

    @lazy_property
    def meson_version(self) -> T.List[str]:
        """Convert the version to a list of meson compatible versions."""
        return version.convert(self.version) if self.version else []

    @classmethod
    def from_raw(cls, name: str, raw: T.Union[T.Dict[str, T.Any], str], workspace: T.Optional[Workspace] = None, member_path: str = '') -> Dependency:
        """Create a dependency from a raw cargo dictionary"""
        if isinstance(raw, str):
            return cls(name, raw)
        raw_from_workspace = workspace.dependencies.get(name) if workspace else None
        if raw_from_workspace is not None:
            name = raw_from_workspace.get('package', name)
            if 'features' in raw:
                raw['features'] += raw_from_workspace.get('features', [])
            if 'path' in raw_from_workspace:
                raw_from_workspace = raw_from_workspace.copy()
                raw_from_workspace['path'] = os.path.relpath(raw_from_workspace['path'], member_path)
        raw.setdefault('package', name)
        return _raw_to_dataclass(raw, cls, f'Dependency entry {name}', raw_from_workspace)


@dataclasses.dataclass
class BuildTarget:

    name: str
    crate_type: T.List[CRATE_TYPE] = dataclasses.field(default_factory=lambda: ['lib'])
    path: str = ''

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
        return _raw_to_dataclass(raw, cls, f'{cls.__name__} entry {raw["name"]}')


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
    def from_raw(cls, raw: T.Dict[str, T.Any], fallback_name: str) -> Self: # type: ignore[override]
        # We need to set the name field if it's not set manually, including if
        # other fields are set in the lib section
        raw.setdefault('name', fallback_name)
        return _raw_to_dataclass(raw, cls, f'Library entry {raw["name"]}')


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
    lib: Library
    dependencies: T.Dict[str, Dependency] = dataclasses.field(default_factory=dict)
    dev_dependencies: T.Dict[str, Dependency] = dataclasses.field(default_factory=dict)
    build_dependencies: T.Dict[str, Dependency] = dataclasses.field(default_factory=dict)
    bin: T.List[Binary] = dataclasses.field(default_factory=list)
    test: T.List[Test] = dataclasses.field(default_factory=list)
    bench: T.List[Benchmark] = dataclasses.field(default_factory=list)
    example: T.List[Example] = dataclasses.field(default_factory=list)
    features: T.Dict[str, T.List[str]] = dataclasses.field(default_factory=dict)
    target: T.Dict[str, T.Dict[str, Dependency]] = dataclasses.field(default_factory=dict)

    def __post_init__(self) -> None:
        self.features.setdefault('default', [])

    @lazy_property
    def system_dependencies(self) -> T.Dict[str, SystemDependency]:
        return {k: SystemDependency.from_raw(k, v) for k, v in self.package.metadata.get('system-deps', {}).items()}

    @classmethod
    def from_raw(cls, raw: T.Dict[str, T.Any], workspace: T.Optional[Workspace] = None, member_path: str = '') -> Manifest:
        name = raw['package']['name']
        raw.setdefault('lib', {'name': name})

        def dependencies_from_raw(x: T.Dict[str, T.Any]) -> T.Dict[str, Dependency]:
            return {k: Dependency.from_raw(k, v, workspace, member_path) for k, v in x.items()}

        return _raw_to_dataclass(raw, cls, f'Manifest {name}',
                                 package=lambda x: Package.from_raw(x, workspace),
                                 dependencies=dependencies_from_raw,
                                 dev_dependencies=dependencies_from_raw,
                                 build_dependencies=dependencies_from_raw,
                                 lib=lambda x: Library.from_raw(x, name),
                                 bin=lambda x: [Binary.from_raw(b) for b in x],
                                 test=lambda x: [Test.from_raw(t) for t in x],
                                 bench=lambda x: [Benchmark.from_raw(b) for b in x],
                                 example=lambda x: [Example.from_raw(e) for e in x],
                                 target=lambda x: {k: dependencies_from_raw(v.get('dependencies', {})) for k, v in x.items()})


@dataclasses.dataclass
class Workspace:

    """Cargo Workspace definition.
    """

    resolver: str = '2'
    members: T.List[str] = dataclasses.field(default_factory=list)
    exclude: T.List[str] = dataclasses.field(default_factory=list)
    default_members: T.List[str] = dataclasses.field(default_factory=list)
    package: T.Dict[str, T.Any] = dataclasses.field(default_factory=dict)
    dependencies: T.Dict[str, T.Dict[str, T.Any]] = dataclasses.field(default_factory=dict)
    lints: T.Dict[str, T.Any] = dataclasses.field(default_factory=dict)
    metadata: T.Dict[str, T.Any] = dataclasses.field(default_factory=dict)

    root_package: T.Optional[Manifest] = None

    @classmethod
    def from_raw(cls, raw: T.Dict[str, T.Any]) -> Workspace:
        extra_members: T.List[str] = []

        def dependency_from_raw(x: T.Dict[str, T.Any]) -> T.Dict[str, T.Any]:
            if isinstance(x, str):
                return {'version': x}
            path = x.get('path')
            if path:
                extra_members.append(path)
            return x

        ws = _raw_to_dataclass(raw['workspace'], cls, 'Workspace',
                               dependencies=lambda x: {k: dependency_from_raw(v) for k, v in x.items()})
        ws.members.extend(extra_members)

        if 'package' in raw:
            del raw['workspace']
            ws.root_package = Manifest.from_raw(raw, ws, member_path='.')

        return ws


@dataclasses.dataclass
class CargoLockPackage:

    """A description of a package in the Cargo.lock file format."""

    name: str
    version: str
    source: T.Optional[str] = None
    checksum: T.Optional[str] = None
    dependencies: T.List[str] = dataclasses.field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: T.Dict[str, T.Any]) -> CargoLockPackage:
        return _raw_to_dataclass(raw, cls, 'Cargo.lock package')


@dataclasses.dataclass
class CargoLock:

    """A description of the Cargo.lock file format."""

    version: int = 1
    package: T.List[CargoLockPackage] = dataclasses.field(default_factory=list)
    metadata: T.Dict[str, str] = dataclasses.field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: T.Dict[str, T.Any]) -> CargoLock:
        return _raw_to_dataclass(raw, cls, 'Cargo.lock',
                                 package=lambda x: [CargoLockPackage.from_raw(p) for p in x])
