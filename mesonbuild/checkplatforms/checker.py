#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Authors

from __future__ import annotations
from dataclasses import dataclass
import os
import tempfile
import typing as T

from mesonbuild import environment, build, mlog
from mesonbuild.options import OptionKey
from mesonbuild.hermetic.hermetic_interpreter import HermeticInterpreter
from mesonbuild.hermetic.hermetic_dependencies import DependenciesToml, HermeticDependencies
from mesonbuild.hermetic.common_compiler import PlatformsToml
from mesonbuild.hermetic.hermetic_platform import HermeticPlatform
from mesonbuild.convert.convert_project_config import ProjectConfigToml
from mesonbuild.checkplatforms.emitter import PlatformEmitter

if T.TYPE_CHECKING:
    from typing_extensions import Protocol
    from mesonbuild.cmdline import SharedCMDOptions

    class CheckPlatformOptions(SharedCMDOptions, Protocol):
        project_dir: T.Optional[str]
        config: T.Optional[str]
        dependencies: T.Optional[str]
        platforms: T.Optional[str]
        output: T.Optional[str]
        hermetic_project: T.Optional[str]
        git_project: T.Optional[str]


def _sanitize_options(args: CheckPlatformOptions) -> CheckPlatformOptions:
    # default SharedCMDOptions: workaround Protocol
    args.cmd_line_options = {}
    args.builtin_keys = set()
    args.d_keys = set()
    args.cross_file = []
    args.native_file = []
    return args


@dataclass
class CheckPlatformsInstance:
    host_platform: str
    build_platform: str
    meson_options: T.Dict[str, T.Union[str, bool]]


def _determine_platforms_to_run(project_toml: ProjectConfigToml, platforms_toml: PlatformsToml,
                                options: CheckPlatformOptions) -> T.List[CheckPlatformsInstance]:  # fmt: skip
    instances: T.List[CheckPlatformsInstance] = []
    configs = project_toml.get('config', [])

    for config in configs:
        platforms_data = config.get('platforms', {})
        host_platforms = platforms_data.get('host_platforms', [])
        build_platforms = platforms_data.get('build_platforms', [])
        static_options = config.get('static_options', {}).copy()

        for host_platform in host_platforms:
            for build_platform in build_platforms:
                instances.append(
                    CheckPlatformsInstance(host_platform, build_platform, static_options)
                )

    return instances


def do_checkplatforms(project_toml: ProjectConfigToml, platforms_toml: PlatformsToml,
                      dependencies_toml: DependenciesToml, options: CheckPlatformOptions) -> int:  # fmt: skip

    instances = _determine_platforms_to_run(project_toml, platforms_toml, options)
    hermetic_platform = HermeticPlatform(platforms_toml)
    dependencies = HermeticDependencies(dependencies_toml)

    for instance in instances:
        sanitized_options = _sanitize_options(options)
        sanitized_options.cmd_line_options = {
            OptionKey.from_string(k): str(v) for k, v in instance.meson_options.items()
        }

        mlog.set_quiet()
        with tempfile.TemporaryDirectory() as builddir:
            env = environment.Environment(options.project_dir, builddir, sanitized_options)
            platform_instance = hermetic_platform.create_platform_info(
                instance.host_platform, instance.build_platform, env, download=True
            )
            b = build.Build(env)
            intr = HermeticInterpreter(
                b,
                dependencies=dependencies,
                hermetic_platform=platform_instance,
                user_defined_options=sanitized_options,
            )

            try:
                intr.run()
            except Exception as e:
                mlog.warning(
                    f'Interpreter failed during checks for platform {instance.host_platform}: {e}'
                )

    emitter = PlatformEmitter(hermetic_platform.platforms_toml, options)
    emitter.emit(options.output)
    mlog.set_verbose()
    mlog.log('Platform information written to', mlog.bold(os.path.abspath(options.output)))
    return 0
