# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Authors

from __future__ import annotations
import argparse
import os
import typing as T
import sys

if sys.version_info >= (3, 11):
    import tomllib
else:
    tomllib: T.Optional[T.Any] = None

from mesonbuild import mlog
from mesonbuild.checkplatforms.checker import do_checkplatforms
from mesonbuild.convert.convert_project_config import ProjectConfigToml
from mesonbuild.hermetic.common_compiler import PlatformsToml
from mesonbuild.hermetic.hermetic_dependencies import DependenciesToml
from mesonbuild.hermetic.hermetic_projects import get_known_toml_files

if T.TYPE_CHECKING:
    from mesonbuild.checkplatforms.checker import CheckPlatformOptions


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        'hermetic_project',
        nargs='?',
        default=None,
        help='The hermetic project to check (e.g., android, fuchsia).',
    )
    parser.add_argument(
        'git_project',
        nargs='?',
        default=None,
        help='The git project to check (e.g., aosp_mesa3d, mesa3d).',
    )
    parser.add_argument(
        '--project-dir', default=os.getcwd(), help='The path to the project directory.'
    )
    parser.add_argument('--config', default=None, help='Path to project config file (toml).')
    parser.add_argument('--dependencies', default=None, help='Path to dependencies.toml')
    parser.add_argument(
        '--platforms',
        default=None,
        help='Path to existing platforms TOML file.',
    )
    parser.add_argument(
        '--output',
        default=None,
        help='[Optional] Location of output platforms TOML file.',
    )


def run(options: CheckPlatformOptions) -> int:
    mlog.warning(mlog.bold('The check-platforms API is unstable and subject to change'))

    if tomllib is None:
        sys.exit('The check-platforms API requires Python 3.11 or newer.')

    if options.project_dir:
        options.project_dir = os.path.abspath(options.project_dir)

    if options.hermetic_project and options.git_project:
        res = get_known_toml_files(
            options.hermetic_project, options.git_project, options.project_dir
        )
        if res is not None:
            options.config, options.platforms, options.dependencies = res
        else:
            sys.exit('Error looking up check-platforms fast path')

    project_dir = options.project_dir
    platforms = options.platforms
    config = options.config
    dependencies = options.dependencies

    if config and not os.path.exists(config):
        if os.path.exists(os.path.join(project_dir, config)):
            config = os.path.join(project_dir, config)

    if config and os.path.exists(config):
        config_dir = os.path.dirname(os.path.abspath(config))
        if not dependencies and os.path.exists(os.path.join(config_dir, 'dependencies.toml')):
            dependencies = os.path.join(config_dir, 'dependencies.toml')
        if not platforms and os.path.exists(os.path.join(config_dir, 'platforms.toml')):
            platforms = os.path.join(config_dir, 'platforms.toml')

    if dependencies and not os.path.exists(dependencies):
        if os.path.exists(os.path.join(project_dir, dependencies)):
            dependencies = os.path.join(project_dir, dependencies)

    if platforms and not os.path.exists(platforms):
        if os.path.exists(os.path.join(project_dir, platforms)):
            platforms = os.path.join(project_dir, platforms)

    if not options.output:
        options.output = options.platforms

    project_toml: ProjectConfigToml = {}
    platforms_toml: PlatformsToml = {}
    dependencies_toml: DependenciesToml = {}

    try:
        if config and os.path.exists(config):
            with open(config, 'rb') as f:
                project_toml = T.cast('ProjectConfigToml', tomllib.load(f))

        if dependencies and os.path.exists(dependencies):
            with open(dependencies, 'rb') as f:
                dependencies_toml = T.cast('DependenciesToml', tomllib.load(f))

        if platforms and os.path.exists(platforms):
            with open(platforms, 'rb') as f:
                platforms_toml = T.cast('PlatformsToml', tomllib.load(f))
    except Exception as e:
        sys.exit(f'Error trying to open config file: {e}')

    return do_checkplatforms(project_toml, platforms_toml, dependencies_toml, options)
