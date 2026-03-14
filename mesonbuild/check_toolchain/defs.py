#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Authors

from __future__ import annotations
import typing as T
from dataclasses import dataclass, field


@dataclass
class HostMachine:
    cpu_family: str
    cpu: str
    system: str
    endian: str


@dataclass
class CompilerInfo:
    compiler_id: str
    linker_id: str
    version: str


@dataclass
class Toolchain:
    name: str
    host_machine: HostMachine
    c: CompilerInfo
    cpp: CompilerInfo
    rust: T.Optional[CompilerInfo] = None
    c_compiles_fails: T.List[str] = field(default_factory=list)
    c_links_fails: T.List[str] = field(default_factory=list)
    c_headers_fails: T.List[str] = field(default_factory=list)
    c_header_symbols_fails: T.Dict[str, T.List[str]] = field(default_factory=dict)
    c_functions_fails: T.List[str] = field(default_factory=list)
    c_function_attributes_fails: T.List[str] = field(default_factory=list)
    c_members_fails: T.Dict[str, T.List[str]] = field(default_factory=dict)
    c_supported_arguments_fails: T.List[str] = field(default_factory=list)
    c_supported_link_arguments_fails: T.List[str] = field(default_factory=list)
    cpp_supported_arguments_fails: T.List[str] = field(default_factory=list)
