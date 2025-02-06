#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import argparse
import os
import sys
import typing as T

if T.TYPE_CHECKING:
    from mesonbuild.convert.convert_project_config import ProjectConfigToml
    from mesonbuild.hermetic.common_compiler import PlatformsToml
    from mesonbuild.hermetic.hermetic_dependencies import DependenciesToml
    from mesonbuild.convert.convertmain import ConvertOptions

if sys.version_info >= (3, 11):
    import tomllib
else:
    tomllib: T.Optional[T.Any] = None

from mesonbuild.convert.convertmain import convert_build_system
from mesonbuild.hermetic.hermetic_projects import get_known_toml_files


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        'hermetic_project',
        nargs='?',
        default=None,
        help='The hermetic project to convert (e.g., android, fuchsia).',
    )
    parser.add_argument(
        'git_project',
        nargs='?',
        default=None,
        help='The git project to convert (e.g., aosp_mesa3d, mesa3d).',
    )
    parser.add_argument('--config', help='The path to a valid project config file (toml).')
    parser.add_argument('--platforms', help='The path to a valid platform config file (toml).')
    parser.add_argument('--dependencies', help='The path to a valid dependencies file (toml).')
    parser.add_argument(
        '--project-dir', default=os.getcwd(), help='The path to the project directory.'
    )
    parser.add_argument(
        '--output-dir',
        help='The path to the output directory for generated files. Defaults to the project directory.',
    )


def run(options: ConvertOptions) -> int:
    if tomllib is None:
        sys.exit('The convert feature requires Python 3.11 or newer.')

    if options.hermetic_project and options.git_project:
        res = get_known_toml_files(
            options.hermetic_project, options.git_project, options.project_dir
        )
        if res is not None:
            options.config, options.platforms, options.dependencies = res
        else:
            sys.exit('Error looking up convert fast path')
    elif not all([options.config, options.platform]):
        sys.exit(
            'Error: You must specify either a hermetic project and git project, or --config and --platform paths.'
        )

    # Load all toml files
    try:
        with open(options.config, 'rb') as f:
            config_toml = T.cast('ProjectConfigToml', tomllib.load(f))
        with open(options.platforms, 'rb') as f:
            platform_toml = T.cast('PlatformsToml', tomllib.load(f))
        dependencies_toml = T.cast('DependenciesToml', {})
        if options.dependencies and os.path.exists(options.dependencies):
            with open(options.dependencies, 'rb') as f:
                dependencies_toml = T.cast('DependenciesToml', tomllib.load(f))
    except Exception as e:
        sys.exit(f'Error trying to open config file: {e}')

    return convert_build_system(config_toml, platform_toml, dependencies_toml, options)
