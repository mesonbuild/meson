#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
from dataclasses import dataclass
import hashlib
import os
import shutil
import tempfile
import typing as T
import urllib.request
import zipfile
from pathlib import Path
from typing import TypeAlias

from mesonbuild.mesonlib import MesonException


# FIXME(used variant in mesonbuild.options) eventually
ElementaryOptionValues: TypeAlias = T.Union[str, int, bool, T.List[str]]


class WrapInfo(T.TypedDict, total=False):
    name: str
    source_url: str
    source_filename: str
    source_hash: str


class ToolchainInfo(T.TypedDict, total=False):
    name: str
    wrap_name: str
    ar: str
    cc: str
    cpp: str
    strip: str


class SysrootInfo(T.TypedDict, total=False):
    wrap_name: str
    path: str


class HostMachineInfo(T.TypedDict, total=False):
    cpu_family: str
    cpu: str
    system: str
    endian: str


class CheckHeaderConfig(T.TypedDict, total=False):
    fails: T.Dict[str, bool]


class HasHeaderSymbolConfig(T.TypedDict, total=False):
    fails: T.Dict[str, T.Dict[str, bool]]


class HasFunctionConfig(T.TypedDict, total=False):
    fails: T.Dict[str, bool]


class SupportedArgumentsFails(T.TypedDict, total=False):
    args: T.List[str]


class SupportedArgumentsConfig(T.TypedDict, total=False):
    fails: SupportedArgumentsFails


class CompilesConfig(T.TypedDict, total=False):
    fails: T.Dict[str, bool]


class LinksConfig(T.TypedDict, total=False):
    fails: T.Dict[str, bool]


class HasMemberConfig(T.TypedDict, total=False):
    fails: T.Dict[str, T.Dict[str, bool]]


class HasFunctionAttributeConfig(T.TypedDict, total=False):
    fails: T.Dict[str, bool]


class SizeofConfig(T.TypedDict, total=False):
    sizes: T.Dict[str, int]


class AlignmentConfig(T.TypedDict, total=False):
    aligns: T.Dict[str, int]


class CompilerConfig(T.TypedDict, total=False):
    toolchain: str
    sysroot: SysrootInfo
    compiler_id: str
    linker_id: str
    version: str
    standards: T.List[str]
    base_options: T.List[str]
    check_header: CheckHeaderConfig
    has_header_symbol: HasHeaderSymbolConfig
    has_function: HasFunctionConfig
    supported_arguments: SupportedArgumentsConfig
    supported_link_arguments: SupportedArgumentsConfig
    compiles: CompilesConfig
    links: LinksConfig
    has_member: HasMemberConfig
    has_function_attribute: HasFunctionAttributeConfig
    sizeof: SizeofConfig
    alignment: AlignmentConfig


class PlatformInfo(T.TypedDict, total=False):
    name: str
    toolchain: str
    sysroot: SysrootInfo
    host_machine: HostMachineInfo
    machine_info: HostMachineInfo
    c: CompilerConfig
    cpp: CompilerConfig
    rust: CompilerConfig


class PlatformsToml(T.TypedDict, total=False):
    wrap: T.List[WrapInfo]
    toolchain: T.List[ToolchainInfo]
    platform: T.List[PlatformInfo]


def _compute_sha256(filename: Path) -> str:
    sha256 = hashlib.sha256()
    with open(filename, 'rb') as f:
        while chunk := f.read(4096):
            sha256.update(chunk)
    return sha256.hexdigest()


def _extract_zip(zip_path: Path, fetch_dir: Path) -> None:
    """ZIP file while preserving Unix file permissions (like executable
    flags) and symbolic links (symlinks)"""
    with zipfile.ZipFile(zip_path, 'r') as z:
        for info in z.infolist():
            mode = info.external_attr >> 16
            if (mode & 0o170000) == 0o120000:
                target = z.read(info).decode('utf-8')
                dest = fetch_dir / info.filename
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists() or dest.is_symlink():
                    dest.unlink()
                os.symlink(target, dest)
            else:
                extracted_path = z.extract(info, fetch_dir)
                if mode & 0o7777:
                    os.chmod(extracted_path, mode & 0o7777)


class HermeticPlatformWrap:
    """Holds information about the platform archive and its contents.
    Able to be downloaded from internet, like a normal wrap file"""

    def __init__(self, wrap_config: WrapInfo):
        self.name = wrap_config.get('name', '')
        self.url = wrap_config.get('source_url', '')
        self.sha256 = self.hash = wrap_config.get('source_hash', '')
        self.filename = wrap_config.get('source_filename', '')
        self.fetch_dir: T.Optional[Path] = None
        if self.filename and not self.filename.endswith('.zip'):
            raise MesonException(f'Unsupported compression type: "{self.filename}"')

    def download(self) -> Path:
        if self.fetch_dir is not None:
            return self.fetch_dir

        # 1) wrap_download_dir: /tmp/custom-sdk
        # 2) fetched_file: /tmp/custom-sdk/sdk-r67.zip
        wrap_download_dir = Path(tempfile.gettempdir()) / self.name
        fetched_file = wrap_download_dir / self.filename
        if wrap_download_dir.exists():
            shutil.rmtree(wrap_download_dir)

        wrap_download_dir.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(self.url, fetched_file)
        if self.hash:
            actual_hash = _compute_sha256(fetched_file)
            if actual_hash != self.hash:
                raise MesonException(f'Expected hash: "{self.hash}", got {actual_hash}')

        _extract_zip(fetched_file, wrap_download_dir)
        fetched_file.unlink()

        # Some Zip files extract to a subfolder:
        #   self.fetch_dir: /tmp/custom-sdk/sdk-r67 (zip deleted)
        # Some skip the subfolder
        #   self.fetch_dir: /tmp/custom-sdk
        prospective_dir = fetched_file.with_suffix('')
        if prospective_dir.is_dir():
            self.fetch_dir = prospective_dir
        else:
            self.fetch_dir = wrap_download_dir

        return self.fetch_dir

    def __eq__(self, other: object) -> bool:
        if isinstance(other, HermeticPlatformWrap):
            return self.name == other.name
        return False

    def __hash__(self) -> int:
        return hash(self.name)


KNOWN_LANGUAGES: T.List[str] = ['c', 'cpp', 'rust']


@dataclass
class CompilerPaths:
    toolchain_wrap: HermeticPlatformWrap
    toolchain_info: ToolchainInfo
    sdk_wrap: T.Optional[HermeticPlatformWrap]
    sysroot_path: T.Optional[str]


class HermeticPlatformInfo:
    """Extended PlatformInfo with additional details"""

    def __init__(self, platform: PlatformInfo, toolchains: T.Dict[str, ToolchainInfo],
                 wraps: T.Dict[str, HermeticPlatformWrap], download: bool):  # fmt: skip
        # Language is the key
        self.compiler_paths: T.Dict[str, CompilerPaths] = {}
        self.platform = platform
        self.name = platform.get('name', '')
        self.download = download
        self._init_compiler_paths(toolchains, wraps)

    def _init_compiler_paths(self, toolchains: T.Dict[str, ToolchainInfo],
                             wraps: T.Dict[str, HermeticPlatformWrap]) -> None:  # fmt: skip
        for lang_name in KNOWN_LANGUAGES:
            language = T.cast(CompilerConfig, self.platform.get(lang_name, {}))
            if language:
                toolchain_name = language.get('toolchain', '')
                if toolchain_name:
                    toolchain = toolchains[toolchain_name]
                    toolchain_wrap_name = toolchain.get('wrap_name', '')
                    toolchain_wrap = wraps[toolchain_wrap_name]

                    # A toolchain is required, but not a SDK/sysroot (Rust)
                    sysroot = language.get('sysroot', {})
                    if sysroot and isinstance(sysroot, dict):
                        sysroot_wrap_name = sysroot.get('wrap_name', '')
                        sysroot_wrap = wraps.get(sysroot_wrap_name) if sysroot_wrap_name else None
                        sysroot_path = sysroot.get('path', '')
                    else:
                        sysroot_wrap = None
                        sysroot_path = None
                    self.compiler_paths[lang_name] = CompilerPaths(
                        toolchain_wrap, toolchain, sysroot_wrap, sysroot_path
                    )

    @property
    def compilers_wrap(self) -> T.Optional[HermeticPlatformWrap]:
        for lang_info in self.compiler_paths.values():
            if lang_info.toolchain_wrap:
                return lang_info.toolchain_wrap
        return None

    @property
    def sysroot_wrap(self) -> T.Optional[HermeticPlatformWrap]:
        for lang_info in self.compiler_paths.values():
            if lang_info.sdk_wrap:
                return lang_info.sdk_wrap
        return None

    @property
    def sysroot_path(self) -> T.Optional[str]:
        for lang_info in self.compiler_paths.values():
            if lang_info.sysroot_path is not None:
                return lang_info.sysroot_path
        return None

    def should_download(self, language: str) -> bool:  # fmt: skip
        return self.download and language in self.compiler_paths

    def __eq__(self, other: object) -> bool:
        if isinstance(other, HermeticPlatformInfo):
            return self.name == other.name
        return False

    def __hash__(self) -> int:
        return hash(self.name)
