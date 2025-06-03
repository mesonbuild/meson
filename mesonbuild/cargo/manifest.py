# SPDX-License-Identifier: Apache-2.0
# Copyright © 2022-2024 Intel Corporation

"""Type definitions for cargo manifest files."""

from __future__ import annotations
import typing as T

from typing_extensions import TypedDict, Required

from .raw import EDITION, CRATE_TYPE

class FixedPackage(TypedDict, total=False):

    """A description of the Package Dictionary, fixed up."""

    name: Required[str]
    version: Required[str]
    authors: T.List[str]
    edition: EDITION
    rust_version: str
    description: str
    readme: str
    license: str
    license_file: str
    keywords: T.List[str]
    categories: T.List[str]
    workspace: str
    build: str
    links: str
    include: T.List[str]
    exclude: T.List[str]
    publish: bool
    metadata: T.Dict[str, T.Dict[str, str]]
    default_run: str
    autolib: bool
    autobins: bool
    autoexamples: bool
    autotests: bool
    autobenches: bool


class FixedDependency(TypedDict, total=False):

    """An entry in the *dependencies sections, fixed up."""

    version: T.List[str]
    registry: str
    git: str
    branch: str
    rev: str
    path: str
    optional: bool
    package: str
    default_features: bool
    features: T.List[str]


class _BaseFixedBuildTarget(TypedDict, total=False):
    path: str
    test: bool
    doctest: bool
    bench: bool
    doc: bool
    plugin: bool
    harness: bool
    edition: EDITION
    crate_type: T.List[CRATE_TYPE]
    required_features: T.List[str]


class FixedBuildTarget(_BaseFixedBuildTarget, total=False):

    name: Required[str]


class FixedLibTarget(_BaseFixedBuildTarget, total=False):

    name: str
    proc_macro: bool
