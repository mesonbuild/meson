#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import tempfile
import typing as T
from typing import Protocol
import os

from mesonbuild import build, environment, mlog
from mesonbuild.options import OptionKey
from mesonbuild.mesonlib import MachineChoice

from mesonbuild.hermetic.hermetic_dependencies import HermeticDependencies
from mesonbuild.hermetic.hermetic_platform import HermeticPlatform, HermeticPlatformInstance
from mesonbuild.convert.build_systems.bazel.emitter import BazelEmitterBackend
from mesonbuild.convert.build_systems.bazel.state import BazelBackend
from mesonbuild.convert.build_systems.common import ConvertStateTracker
from mesonbuild.convert.build_systems.emitter import CommonEmitter
from mesonbuild.convert.build_systems.soong.emitter import SoongEmitterBackend
from mesonbuild.convert.build_systems.soong.state import SoongBackend
from mesonbuild.convert.common_defs import ConvertUnimplementedException, SelectInstance
from mesonbuild.convert.convert_project_config import ProjectConfigToml
from mesonbuild.hermetic.common_compiler import PlatformsToml
from mesonbuild.hermetic.hermetic_dependencies import DependenciesToml
from mesonbuild.convert.convert_project_config import ConvertProjectConfig
from mesonbuild.convert.convert_interpreter import ConvertInterpreter
from mesonbuild.convert.instance.convert_instance_build_target import (
    ConvertInstanceBuildTargetType,
    ConvertInstanceExecutable,
    ConvertInstanceStaticLibrary,
    ConvertInstanceSharedLibrary,
)
from mesonbuild.convert.instance.convert_instance_custom_target import ConvertInstanceCustomTarget
from mesonbuild.convert.convert_project_instance import ConvertProjectInstance

if T.TYPE_CHECKING:
    from mesonbuild.cmdline import SharedCMDOptions

    class ConvertOptions(SharedCMDOptions, Protocol):
        project_dir: str
        output_dir: T.Optional[str]
        config: str
        platforms: T.Optional[str]
        dependencies: T.Optional[str]
        hermetic_project: T.Optional[str]
        git_project: T.Optional[str]


def _sanitize_options(args: ConvertOptions) -> ConvertOptions:
    # default SharedCMDOptions: workaround Protocol
    args.cmd_line_options = {}
    args.builtin_keys = set()
    args.d_keys = set()
    args.cross_file = []
    args.native_file = []
    return args


def generate(project_instance: ConvertProjectInstance, options: ConvertOptions,
             platform: HermeticPlatformInstance, env: environment.Environment,

             state_tracker: ConvertStateTracker,
             custom_select_instances: T.Set[SelectInstance]) -> None:  # fmt: skip
    """
    Sets up and runs the Meson interpreter for a single project configuration.

    This function configures the environment with the hermetic platform, runs the
    custom `ConvertInterpreter` to analyze the `meson.build` files, and then
    iterates through the results.

    It processes all discovered targets (custom, build, etc.), converting them into
    build-system-agnostic representations and adding them to the state tracker for
    later emission.
    """
    build_info = build.Build(env)
    intr = ConvertInterpreter(
        build_info,
        project_instance,
        state_tracker.project_config,
        platform,
        user_defined_options=options,
    )

    try:
        intr.run()
    except Exception as e:
        raise e

    for custom_target in build_info.get_custom_targets().values():
        convert_ct = ConvertInstanceCustomTarget(
            custom_target, project_instance, state_tracker.project_config
        )

        if convert_ct.skip_custom_target:
            continue

        state_tracker.add_custom_target(convert_ct)

    for target in build_info.get_build_targets().values():
        build_target: T.Optional[ConvertInstanceBuildTargetType] = None

        if isinstance(target, build.StaticLibrary):
            build_target = ConvertInstanceStaticLibrary(
                build_info, target, project_instance, state_tracker.project_config
            )
            state_tracker.add_static_library(build_target)
        elif isinstance(target, build.SharedLibrary):
            build_target = ConvertInstanceSharedLibrary(
                build_info, target, project_instance, state_tracker.project_config
            )
            state_tracker.add_shared_library(build_target)
        elif isinstance(target, build.Executable):
            build_target = ConvertInstanceExecutable(
                build_info, target, project_instance, state_tracker.project_config
            )
            state_tracker.add_executable(build_target)

        # Need to handle build.Executable here
        if not build_target:
            continue

        for flag in build_target.generated_flags.values():
            state_tracker.add_flag(flag)

    for bindgen_instance in project_instance.rust_bindgens.values():
        state_tracker.add_rust_bindgen(bindgen_instance)

    for include_dir in project_instance.shared_include_dirs.values():
        state_tracker.add_include_directory(include_dir)
    for filegroup in project_instance.shared_filegroups.values():
        state_tracker.add_file_group(filegroup)
    for py_binary in project_instance.python_binaries.values():
        state_tracker.add_python_binary(py_binary)


def choose_build_system(project_config: ConvertProjectConfig,
                        output_dir: str) -> T.Tuple[ConvertStateTracker, CommonEmitter]:  # fmt: skip
    if project_config.build_system == 'soong':
        state_tracker: ConvertStateTracker = ConvertStateTracker(
            project_config, SoongBackend(project_config.soong_properties)
        )
        emitter: CommonEmitter = CommonEmitter(output_dir, SoongEmitterBackend())
    elif project_config.build_system == 'bazel':
        state_tracker = ConvertStateTracker(project_config, BazelBackend())
        emitter = CommonEmitter(output_dir, BazelEmitterBackend())
    else:
        raise ConvertUnimplementedException(f'Build system {project_config.build_system}')

    return (state_tracker, emitter)


def convert_build_system(config_toml: ProjectConfigToml, platform_toml: PlatformsToml,
                         dependencies_toml: DependenciesToml,
                         options: ConvertOptions) -> int:  # fmt: skip
    """
    Converts a Meson project to a different build system based on the provided configuration.

    This tool operates by parsing three main TOML configuration files:
       - project.toml: a project's structure and build options,
       - platforms.toml: platforms + sysroots for a hermetic project
       - dependency.toml: mappings to external dependencies needed by the project

    The main logic iterates through each build configuration specified in the project's TOML file.

    For each configuration, it simulates a Meson build environment using a "hermetic" platform
    that mimics a real one without actually invoking any compilers.

    A custom version of the Meson interpreter runs on the project's `meson.build` files.
    Instead of generating build commands, this interpreter gathers detailed information about all
    targets, sources, dependencies, and compiler flags.

    This information is collected into a build-system-agnostic state tracker. After processing all
    configurations, this tracker consolidates the data, resolving any conditional logic. Finally, a
    build system-specific "emitter" (e.g., for Soong or Bazel) takes this consolidated state and
    generates the corresponding build files (e.g., `BUILD.bazel` or `Android.bp`).
    """
    dependencies = HermeticDependencies(dependencies_toml)
    platform = HermeticPlatform(platform_toml)
    options.project_dir = os.path.abspath(options.project_dir)
    output_dir = os.path.abspath(options.output_dir) if options.output_dir else options.project_dir

    project_config = ConvertProjectConfig(
        config_toml, dependencies, os.path.dirname(options.config)
    )
    state_tracker, emitter = choose_build_system(project_config, output_dir)
    state_tracker.project_dir = options.project_dir

    mlog.warning(mlog.bold('The convert API is unstable and subject to change'))
    # Iterate over ConvertProjectInstance objects
    for project_instance in project_config.get_project_instances():
        sourcedir = options.project_dir
        sanitized_options = _sanitize_options(options)
        sanitized_options.cmd_line_options = {
            OptionKey.from_string(k): str(v)
            for k, v in project_instance.option_instance.meson_options.items()
        }
        custom_select_instances = set(project_instance.option_instance.select_instances)
        mlog.set_verbose()
        project_instance.emit()
        mlog.set_quiet()
        with tempfile.TemporaryDirectory() as builddir:
            env = environment.Environment(sourcedir, builddir, sanitized_options)

            platform_info = platform.create_platform_info(
                project_instance.host_platform, project_instance.build_platform, env
            )
            env.machines.host = platform_info.machine_info[MachineChoice.HOST]
            env.machines.build = platform_info.machine_info[MachineChoice.BUILD]
            state_tracker.set_current_config(platform_info, custom_select_instances)
            generate(
                project_instance,
                sanitized_options,
                platform_info,
                env,
                state_tracker,
                custom_select_instances,
            )
            state_tracker.finish_current_config()

    state_tracker.finish()
    emitter.emit(state_tracker)
    return 0
