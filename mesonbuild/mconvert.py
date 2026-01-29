#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

import argparse
import os
import sys
import typing as T

if sys.version_info >= (3, 11):
    import tomllib
else:
    tomllib: T.Optional[T.Any] = None

from mesonbuild.convert.convertmain import convert_build_system


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "hermetic_project",
        nargs="?",
        default=None,
        help="The hermetic project to convert (e.g., android, fuchsia).",
    )
    parser.add_argument(
        "git_project",
        nargs="?",
        default=None,
        help="The git project to convert (e.g., aosp_mesa3d, mesa3d).",
    )
    parser.add_argument("--config", help="The path to a valid project config file (toml).")
    parser.add_argument("--toolchain", help="The path to a valid toolchain config file (toml).")
    parser.add_argument("--dependencies", help="The path to a valid dependencies file (toml).")
    parser.add_argument("--project-dir",
                        default=os.getcwd(),
                        help="The path to the project directory.")
    parser.add_argument(
        "--output-dir",
        help=
        "The path to the output directory for generated files. Defaults to the project directory.",
    )


def run(options: argparse.Namespace) -> int:
    if tomllib is None:
        sys.exit("The convert feature requires Python 3.11 or newer.")

    if options.hermetic_project and options.git_project:
        base_path = os.path.join(os.path.dirname(__file__), "convert", "reference",
                                 options.hermetic_project)
        options.config = os.path.join(base_path, f"{options.git_project}.toml")
        options.toolchain = os.path.join(base_path, "toolchain.toml")
        options.dependencies = os.path.join(base_path, "dependencies.toml")
    elif not all([options.config, options.toolchain]):
        sys.exit(
            "Error: You must specify either a hermetic project and git project, or --config and --toolchain paths."
        )

    # Load all toml files
    try:
        with open(options.config, "rb") as f:
            config_toml = tomllib.load(f)
        with open(options.toolchain, "rb") as f:
            toolchain_toml = tomllib.load(f)
        dependencies_toml = {}
        if options.dependencies and os.path.exists(options.dependencies):
            with open(options.dependencies, "rb") as f:
                dependencies_toml = tomllib.load(f)
    except Exception as e:
        sys.exit(f"Error trying to open config file: {e}")

    return convert_build_system(config_toml, toolchain_toml, dependencies_toml, options)
