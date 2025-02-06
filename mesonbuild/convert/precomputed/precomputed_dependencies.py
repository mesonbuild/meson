#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T


class DependencyWrapInfo(T.TypedDict, total=False):
    """Wrap info for a dependency."""

    source_url: str
    source_filename: str
    source_hash: str


class CommonDependencyInfo(T.TypedDict, total=False):
    """Common information for a dependency."""

    target_name: str
    repo_name: str
    subdir: str
    version: str


class NativeLibsInfo(T.TypedDict, total=False):
    """Native library specific information."""

    pkgconfig: T.Dict[str, str]
    configtool: T.Dict[str, str]


class RustLibsInfo(T.TypedDict, total=False):
    """Rust library specific information."""

    proc_macro: bool


class NativeDependencyInfo(CommonDependencyInfo, NativeLibsInfo, DependencyWrapInfo, total=False):
    """Full information for a native dependency."""


class RustDependencyInfo(CommonDependencyInfo, RustLibsInfo, DependencyWrapInfo, total=False):
    """Full information for a rust dependency."""


class ExternalProgramInfo(T.TypedDict, total=False):
    """Information for an external program."""

    version: str
    subdir: str
    repo: str


class DependenciesToml(T.TypedDict, total=False):
    shared_libraries: T.Dict[str, T.List[NativeDependencyInfo]]
    static_libraries: T.Dict[str, T.List[NativeDependencyInfo]]
    rust_libraries: T.Dict[str, T.List[RustDependencyInfo]]
    header_libraries: T.Dict[str, T.List[NativeDependencyInfo]]
    python_libraries: T.Dict[str, str]
    programs: T.Dict[str, ExternalProgramInfo]


class PrecomputedDependencies:
    """Wrapper around the dependencies TOML data"""

    def __init__(self, dependencies_data: DependenciesToml):
        self._data = dependencies_data

    @property
    def shared_libraries(self) -> T.Dict[str, T.List[NativeDependencyInfo]]:
        return self._data.get('shared_libraries', {})

    @property
    def static_libraries(self) -> T.Dict[str, T.List[NativeDependencyInfo]]:
        return self._data.get('static_libraries', {})

    @property
    def rust_libraries(self) -> T.Dict[str, T.List[RustDependencyInfo]]:
        return self._data.get('rust_libraries', {})

    @property
    def header_libraries(self) -> T.Dict[str, T.List[NativeDependencyInfo]]:
        return self._data.get('header_libraries', {})

    @property
    def programs(self) -> T.Dict[str, ExternalProgramInfo]:
        return self._data.get('programs', {})

    @property
    def python_libraries(self) -> T.Dict[str, str]:
        return self._data.get('python_libraries', {})
