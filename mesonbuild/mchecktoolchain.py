# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Authors

from __future__ import annotations
import argparse
import os
import typing as T

from . import mlog
from .check_toolchain.android import generate_android_toolchains
from .check_toolchain.fuchsia import generate_fuchsia_toolchains
from .check_toolchain.defs import Toolchain
from .check_toolchain.emitter import ToolchainEmitter
from .check_toolchain.checker import run_compiler_checks


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--name", default=None)
    parser.add_argument("-o", "--output", default=None, help="Output file name.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--cross-file")
    group.add_argument("--android-ndk-version")
    group.add_argument("--fuchsia-clang-instance-id")
    parser.add_argument("--fuchsia-core-sdk-instance-id")
    parser.add_argument("--android-ndk-platform", default="linux")


def run(options: argparse.Namespace) -> int:
    toolchains: T.List[Toolchain] = []
    output_filename = options.output

    if options.cross_file:
        if not options.name:
            mlog.error("Must specify --name when using --cross-file.")
            return 1
        toolchains.append(run_compiler_checks(options.cross_file, options.name, [], []))
        if output_filename is None:
            output_filename = "check-toolchain-output.toml"
    elif options.android_ndk_version:
        if output_filename is None:
            output_filename = "aosp.toolchain.toml"
        toolchains = generate_android_toolchains(
            run_compiler_checks,
            ndk_version=options.android_ndk_version,
            ndk_platform=options.android_ndk_platform,
        )
    elif options.fuchsia_clang_instance_id:
        if not options.fuchsia_core_sdk_instance_id:
            mlog.error(
                "Must specify --fuchsia-core-sdk-instance-id when using --fuchsia-clang-instance-id."
            )
            return 1
        if output_filename is None:
            output_filename = "fuchsia.toolchain.toml"
        toolchains = generate_fuchsia_toolchains(
            options.fuchsia_clang_instance_id,
            options.fuchsia_core_sdk_instance_id,
            run_compiler_checks,
        )
    else:
        name = options.name or "native"
        toolchains.append(run_compiler_checks(None, name, [], []))
        if output_filename is None:
            output_filename = "check-toolchain-output.toml"

    emitter = ToolchainEmitter(toolchains, options)
    emitter.emit(output_filename)

    mlog.log(
        "Toolchain information written to", mlog.bold(os.path.abspath(output_filename))
    )
    return 0
