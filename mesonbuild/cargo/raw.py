# SPDX-License-Identifier: Apache-2.0
# Copyright © 2022-2024 Intel Corporation

"""Type definitions for cargo manifest files."""

from __future__ import annotations

import typing as T
from typing import Literal

from typing_extensions import Required, TypedDict

EDITION = Literal['2015', '2018', '2021']
CRATE_TYPE = Literal['bin', 'lib', 'dylib', 'staticlib', 'cdylib', 'rlib', 'proc-macro']
LINT_LEVEL = Literal['allow', 'deny', 'forbid', 'warn']


class FromWorkspace(TypedDict):

    """An entry or section that is copied from the workspace."""

    workspace: bool


Package = TypedDict(
    'Package',
    {
        'name': Required[str],
        'version': Required[FromWorkspace | str],
        'authors': FromWorkspace | list[str],
        'edition': FromWorkspace | EDITION,
        'rust-version': FromWorkspace | str,
        'description': FromWorkspace | str,
        'readme': FromWorkspace | str,
        'license': FromWorkspace | str,
        'license-file': FromWorkspace | str,
        'keywords': FromWorkspace | list[str],
        'categories': FromWorkspace | list[str],
        'homepage': FromWorkspace | str,
        'repository': FromWorkspace | str,
        'documentation': FromWorkspace | str,
        'workspace': str,
        'build': str,
        'links': str,
        'include': FromWorkspace | list[str],
        'exclude': FromWorkspace | list[str],
        'publish': FromWorkspace | bool,
        'metadata': dict[str, dict[str, str]],
        'default-run': str,
        'autolib': bool,
        'autobins': bool,
        'autoexamples': bool,
        'autotests': bool,
        'autobenches': bool,
    },
    total=False,
)
"""A description of the Package Dictionary."""

class Badge(TypedDict):

    """An entry in the badge section."""

    status: Literal['actively-developed', 'passively-developed', 'as-is', 'experimental', 'deprecated', 'none']
    repository: str


Dependency = TypedDict(
    'Dependency',
    {
        'version': str,
        'registry': str,
        'git': str,
        'branch': str,
        'rev': str,
        'path': str,
        'optional': bool,
        'package': str,
        'default-features': bool,
        'features': list[str],
    },
    total=False,
)
"""An entry in the *dependencies sections."""


DependencyV = T.Union[Dependency, str]
"""A Dependency entry, either a string or a Dependency Dict."""


_BaseBuildTarget = TypedDict(
    '_BaseBuildTarget',
    {
        'path': str,
        'test': bool,
        'doctest': bool,
        'bench': bool,
        'doc': bool,
        'plugin': bool,
        'proc-macro': bool,
        'harness': bool,
        'edition': EDITION,
        'crate-type': list[CRATE_TYPE],
        'required-features': list[str],
    },
    total=False,
)


class BuildTarget(_BaseBuildTarget, total=False):

    name: Required[str]


class LibTarget(_BaseBuildTarget, total=False):

    name: str


class Target(TypedDict):

    """Target entry in the Manifest File."""

    dependencies: dict[str, FromWorkspace | DependencyV]


Lint = TypedDict(
    'Lint',
    {
        'level': Required[LINT_LEVEL],
        'priority': int,
        'check-cfg': list[str],
    },
    total=True,
)
"""The representation of a linter setting.

This does not include the name or tool, since those are the keys of the
dictionaries that point to Lint.
"""


LintV = T.Union[Lint, str]
"""A Lint entry, either a string or a Lint Dict."""


class Workspace(TypedDict):

    """The representation of a workspace.

    In a vritual manifest the :attribute:`members` is always present, but in a
    project manifest, an empty workspace may be provided, in which case the
    workspace is implicitly filled in by values from the path based dependencies.

    the :attribute:`exclude` is always optional
    """

    members: list[str]
    exclude: list[str]
    package: Package
    dependencies: dict[str, DependencyV]


Profile = TypedDict(
    'Profile',
    {
        'opt-level': int | str,
        'debug': bool | int | str,
        'split-debuginfo': str,
        'strip': bool | str,
        'debug-assertions': bool,
        'overflow-checks': bool,
        'lto': bool | str,
        'panic': str,
        'incremental': bool,
        'codegen-units': int,
        'rpath': bool,
        'inherits': str,
        'package': dict[str, 'Profile'],
        'build-override': 'Profile',
    },
    total=False,
)
"""An entry in the [profile] section.

See https://doc.rust-lang.org/cargo/reference/profiles.html
"""


Manifest = TypedDict(
    'Manifest',
    {
        'package': Package,
        'badges': dict[str, Badge],
        'dependencies': dict[str, FromWorkspace | DependencyV],
        'dev-dependencies': dict[str, FromWorkspace | DependencyV],
        'build-dependencies': dict[str, FromWorkspace | DependencyV],
        'lib': LibTarget,
        'bin': list[BuildTarget],
        'test': list[BuildTarget],
        'bench': list[BuildTarget],
        'example': list[BuildTarget],
        'features': dict[str, list[str]],
        'target': dict[str, Target],
        'workspace': Workspace,
        'lints': FromWorkspace | dict[str, dict[str, LintV]],
        'patch': dict[str, object],
        'profile': dict[str, Profile],

        # TODO: replace?
    },
    total=False,
)
"""The Cargo Manifest format."""


class CargoLockPackage(TypedDict, total=False):

    """A description of a package in the Cargo.lock file format."""

    name: str
    version: str
    source: str
    checksum: str


class CargoLock(TypedDict, total=False):

    """A description of the Cargo.lock file format."""

    version: int
    package: list[CargoLockPackage]
    metadata: dict[str, str]
