#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T


class AbstractDependencies:
    """Wrapper around the dependencies TOML data"""

    def __init__(self, dependencies_data: T.Any):
        self._data = dependencies_data

    @property
    def shared_libraries(self) -> T.Any:
        return self._data.get('shared_libraries', {})

    @property
    def static_libraries(self) -> T.Any:
        return self._data.get('static_libraries', {})

    @property
    def header_libraries(self) -> T.Any:
        return self._data.get('header_libraries', {})

    @property
    def programs(self) -> T.Any:
        return self._data.get('programs', {})
