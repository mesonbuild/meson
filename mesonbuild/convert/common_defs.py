#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T

from mesonbuild.mesonlib import MesonException
from dataclasses import dataclass
from enum import IntEnum


class SelectKind(IntEnum):
    ARCH = 1
    OS = 2
    CUSTOM = 3
    TOOLCHAIN = 4


@dataclass(frozen=True, eq=True, order=True)
class SelectId:
    select_kind: SelectKind
    namespace: str
    variable: str


@dataclass(frozen=True, eq=True)
class SelectInstance:
    select_id: SelectId
    value: str

    @staticmethod
    def parse_from_string(custom_select: str) -> 'SelectInstance':
        if ':' in custom_select:
            namespace, rest = custom_select.split(':', 1)
        else:
            namespace = ''
            rest = custom_select
        if '=' in rest:
            variable, value = rest.split('=', 1)
        else:
            raise MesonException(f'Invalid custom variable format: {custom_select}')
        return SelectInstance(SelectId(SelectKind.CUSTOM, namespace, variable), value)

    def __repr__(self) -> str:
        return f'{self.select_id.namespace}:{self.select_id.variable}={self.value}'


@dataclass(frozen=True, eq=True)
class CustomSelect:
    select_id: SelectId
    possible_values: T.List[str]
    default_value: str

    def __hash__(self) -> int:
        return hash(self.select_id)

    def get_select_instances(self) -> T.Set[SelectInstance]:
        instances = set()
        for value in self.possible_values:
            instances.add(SelectInstance(self.select_id, value))
        return instances

    def get_default_instance(self) -> SelectInstance:
        return SelectInstance(self.select_id, self.default_value)


@dataclass
class MesonOptionInstance:
    meson_option: str
    meson_value: str
    select_instance: SelectInstance


@dataclass
class ProjectOptionsInstance:
    meson_options: T.Dict[str, T.Any]
    select_instances: T.List[SelectInstance]

    def __repr__(self) -> str:
        return f"'{self.select_instances}'"
