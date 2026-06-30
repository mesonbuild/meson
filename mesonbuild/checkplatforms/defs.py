#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Authors

from __future__ import annotations
import typing as T
from dataclasses import dataclass, field
import hashlib
import zipfile
import os


def compute_sha256(filename: str) -> str:
    sha256 = hashlib.sha256()
    with open(filename, 'rb') as f:
        while chunk := f.read(4096):
            sha256.update(chunk)
    return sha256.hexdigest()


def extract_zip(zip_path: str, extract_path: str) -> None:
    with zipfile.ZipFile(zip_path, 'r') as z:
        for info in z.infolist():
            mode = info.external_attr >> 16
            # Check if it's a symlink (0o120000)
            if (mode & 0o170000) == 0o120000:
                target = z.read(info).decode('utf-8')
                dest = os.path.join(extract_path, info.filename)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                if os.path.lexists(dest):
                    os.remove(dest)
                os.symlink(target, dest)
            else:
                extracted_path = z.extract(info, extract_path)
                if mode & 0o7777:
                    os.chmod(extracted_path, mode & 0o7777)


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
class WrapInfo:
    name: str
    source_url: str
    source_filename: str
    source_hash: str


@dataclass
class ToolchainInfo:
    name: str
    wrap_name: str
    binaries: T.Dict[str, str]


@dataclass
class PlatformSysroot:
    wrap_name: str
    path: str


@dataclass
class Platform:
    name: str
    host_machine: HostMachine
    c: CompilerInfo
    cpp: CompilerInfo
    rust: T.Optional[CompilerInfo] = None
    toolchain: str = ''
    sysroot: T.Optional[PlatformSysroot] = None
    wraps: T.Dict[str, WrapInfo] = field(default_factory=dict)
    toolchains: T.Dict[str, ToolchainInfo] = field(default_factory=dict)
    c_compiles_fails: T.List[str] = field(default_factory=list)
    c_links_fails: T.List[str] = field(default_factory=list)
    c_headers_fails: T.List[str] = field(default_factory=list)
    c_header_symbols_fails: T.Dict[str, T.List[str]] = field(default_factory=dict)
    c_functions_fails: T.List[str] = field(default_factory=list)
    c_function_attributes_fails: T.List[str] = field(default_factory=list)
    c_members_fails: T.Dict[str, T.List[str]] = field(default_factory=dict)
    c_supported_arguments_fails: T.List[str] = field(default_factory=list)
    c_supported_link_arguments_fails: T.List[str] = field(default_factory=list)
    cpp_links_fails: T.Set[str] = field(default_factory=set)
    cpp_supported_arguments_fails: T.List[str] = field(default_factory=list)
