#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T
from typing import TypeAlias

from mesonbuild.environment import Environment
from mesonbuild.mesonlib import PerMachine, MachineChoice
from mesonbuild.envconfig import MachineInfo
from mesonbuild.compilers.compilers import Compiler

from mesonbuild.hermetic.common_compiler import (
    PlatformsToml,
    PlatformInfo,
    HermeticPlatformWrap,
    HermeticPlatformInfo,
    ToolchainInfo,
)
from mesonbuild.hermetic.hermetic_compiler import HermeticCCompiler, HermeticCppCompiler
from mesonbuild.hermetic.precomputed_compiler import (
    PrecomputedHermeticCCompiler,
    PrecomputedHermeticCppCompiler,
    PrecomputedHermeticRustCompiler,
)


ElementaryOptionValues: TypeAlias = T.Union[str, int, bool, T.List[str]]


class HermeticPlatformInstance:
    """Holds information about the build and host machines for a platform."""

    def __init__(self, platforms: T.Dict[MachineChoice, HermeticPlatformInfo], env: Environment):
        build_machine_info = T.cast(
            T.Dict[str, ElementaryOptionValues],
            platforms[MachineChoice.BUILD].platform.get('machine_info', {}),
        )
        host_machine_info = T.cast(
            T.Dict[str, ElementaryOptionValues],
            platforms[MachineChoice.HOST].platform.get('machine_info', {}),
        )

        self.platforms = platforms
        self.env = env
        self.machine_info = PerMachine(
            MachineInfo.from_literal(build_machine_info),
            MachineInfo.from_literal(host_machine_info),
        )

    def is_native(self) -> bool:
        return self.platforms[MachineChoice.HOST].name == self.platforms[MachineChoice.BUILD].name

    def create_c_compiler(self, choice: MachineChoice) -> Compiler:
        if self.platforms[choice].should_download('c'):
            return HermeticCCompiler(self.env, choice, self.platforms[choice])
        else:
            c_info = self.platforms[choice].platform.get('c', {})
            return PrecomputedHermeticCCompiler(choice, self.env, c_info)

    def create_cpp_compiler(self, choice: MachineChoice) -> Compiler:
        if self.platforms[choice].should_download('cpp'):
            return HermeticCppCompiler(self.env, choice, self.platforms[choice])
        else:
            cpp_info = self.platforms[choice].platform.get('cpp', {})
            return PrecomputedHermeticCppCompiler(choice, self.env, cpp_info)

    def create_rust_compiler(self, choice: MachineChoice) -> Compiler:
        rs_info = self.platforms[choice].platform.get('rust', {})
        return PrecomputedHermeticRustCompiler(choice, self.env, rs_info)

    def create_compiler(self, lang: str, choice: MachineChoice) -> T.Optional[Compiler]:
        if lang == 'c':
            return self.create_c_compiler(choice)
        elif lang == 'cpp':
            return self.create_cpp_compiler(choice)
        elif lang == 'rust':
            return self.create_rust_compiler(choice)
        return None


class HermeticPlatform:
    """Represents a hermetic platform configuration for the convert/check-platforms tool."""

    def __init__(self, platforms_toml: PlatformsToml):  # fmt: skip
        self.platforms_toml = platforms_toml
        self.platform_configs: T.Dict[str, PlatformInfo] = {}
        self.toolchains: T.Dict[str, ToolchainInfo] = {}
        self.wraps: T.Dict[str, HermeticPlatformWrap] = {}

        for platform in platforms_toml.get('platform', []):
            self.platform_configs[platform['name']] = platform

        for toolchain in platforms_toml.get('toolchain', []):
            self.toolchains[toolchain['name']] = toolchain

        for wrap in platforms_toml.get('wrap', []):
            self.wraps[wrap['name']] = HermeticPlatformWrap(wrap)

    def create_platform_info(self, host_machine: str, build_machine: str,
                             env: Environment, download: bool = False) -> HermeticPlatformInstance:  # fmt: skip
        platforms: T.Dict[MachineChoice, HermeticPlatformInfo] = {}
        host_platform_info = self.platform_configs.get(host_machine, {})
        build_platform_info = self.platform_configs.get(build_machine, {})

        platforms[MachineChoice.HOST] = HermeticPlatformInfo(
            host_platform_info, self.toolchains, self.wraps, download=download
        )
        platforms[MachineChoice.BUILD] = HermeticPlatformInfo(
            build_platform_info, self.toolchains, self.wraps, download=download
        )
        return HermeticPlatformInstance(platforms, env)
