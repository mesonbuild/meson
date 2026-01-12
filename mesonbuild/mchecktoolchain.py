# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Authors

from __future__ import annotations
import argparse
import os
import typing as T

from . import mlog
from .check_toolchain.android import generate_android_toolchains
from .check_toolchain.defs import Toolchain
from .check_toolchain.emitter import ToolchainEmitter
from .check_toolchain.checker import run_compiler_checks


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--name", default=None)
    parser.add_argument("-o", "--output", default=None, help="Output file name.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--cross-file")
    group.add_argument("--android-ndk-path")


def run(options: argparse.Namespace) -> int:
    toolchains: T.List[Toolchain] = []
    output_filename = options.output

    if options.cross_file and options.android_ndk_path:
        mlog.error("Cannot use --cross-file and --android-ndk-path options at the same time.")
        return 1

    if options.cross_file:
        if not options.name:
            mlog.error("Must specify --name when using --cross-file.")
            return 1
        toolchains.append(run_compiler_checks(options.cross_file, options.name, [], []))
        if output_filename is None:
            output_filename = "check-toolchain-output.toml"
    elif options.android_ndk_path:
        options.android_ndk_path = os.path.abspath(options.android_ndk_path)
        if output_filename is None:
            output_filename = "aosp.toolchain.toml"
        toolchains = generate_android_toolchains(options.android_ndk_path, run_compiler_checks)
    else:
        name = options.name or "native"
        toolchains.append(run_compiler_checks(None, name, [], []))
        if output_filename is None:
            output_filename = "check-toolchain-output.toml"

    emitter = ToolchainEmitter(toolchains, options)
    emitter.emit(output_filename)

    mlog.log("Toolchain information written to", mlog.bold(os.path.abspath(output_filename)))
    return 0
