#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import argparse
import tempfile
import typing as T
import sys
import os

from mesonbuild import build, environment, mlog
from mesonbuild.options import OptionKey
from mesonbuild.mesonlib import MachineChoice

from mesonbuild.convert.abstract.abstract_dependencies import (
    AbstractDependencies, )
from mesonbuild.convert.abstract.abstract_toolchain import AbstractToolchain
from mesonbuild.convert.build_systems.bazel.emitter import BazelEmitter
from mesonbuild.convert.build_systems.bazel.state import BazelStateTracker
from mesonbuild.convert.build_systems.common import (
    CommonStateTracker,
    CommonEmitter,
)
from mesonbuild.convert.build_systems.soong.emitter import SoongEmitter
from mesonbuild.convert.build_systems.soong.state import SoongStateTracker
from mesonbuild.convert.common_defs import SelectInstance
from mesonbuild.convert.convert_project_config import (
    ConvertProjectConfig, )
from mesonbuild.convert.convert_interpreter import ConvertInterpreter
from mesonbuild.convert.instance.convert_instance_build_target import (
    ConvertInstanceStaticLibrary,
    ConvertInstanceSharedLibrary,
)
from mesonbuild.convert.instance.convert_instance_custom_target import (
    ConvertInstanceCustomTarget, )
from mesonbuild.convert.convert_project_instance import ConvertProjectInstance


def generate(
    project_instance: ConvertProjectInstance,
    options: argparse.Namespace,
    toolchain: AbstractToolchain,
    env: environment.Environment,
    state_tracker: CommonStateTracker,
    custom_select_instances: T.Set[SelectInstance],
) -> None:
    """
    Sets up and runs the Meson interpreter for a single project configuration.

    This function configures the environment with the abstract toolchain, runs the
    custom `ConvertInterpreter` to analyze the `meson.build` files, and then
    iterates through the results. It processes all discovered targets (custom,
    build, etc.), converting them into build-system-agnostic representations
    and adding them to the state tracker for later emission.
    """
    env.machines.host = toolchain.toolchain_info.machine_info[MachineChoice.HOST]
    env.machines.build = toolchain.toolchain_info.machine_info[MachineChoice.BUILD]
    state_tracker.set_current_config(toolchain.toolchain_info, custom_select_instances)
    c_compiler = toolchain.create_c_compiler(MachineChoice.HOST)
    if c_compiler:
        env.coredata.compilers[MachineChoice.HOST]['c'] = c_compiler
    cpp_compiler = toolchain.create_cpp_compiler(MachineChoice.HOST)
    if cpp_compiler:
        env.coredata.compilers[MachineChoice.HOST]['cpp'] = cpp_compiler
    rust_compiler = toolchain.create_rust_compiler(MachineChoice.HOST)
    if rust_compiler:
        env.coredata.compilers[MachineChoice.HOST]['rust'] = rust_compiler
    c_compiler = toolchain.create_c_compiler(MachineChoice.BUILD)
    if c_compiler:
        env.coredata.compilers[MachineChoice.BUILD]['c'] = c_compiler
    cpp_compiler = toolchain.create_cpp_compiler(MachineChoice.BUILD)
    if cpp_compiler:
        env.coredata.compilers[MachineChoice.BUILD]['cpp'] = cpp_compiler
    rust_compiler = toolchain.create_rust_compiler(MachineChoice.BUILD)
    if rust_compiler:
        env.coredata.compilers[MachineChoice.BUILD]['rust'] = rust_compiler
    build_info = build.Build(env)
    user_defined_options = options
    d: T.Dict[OptionKey, T.Any] = {
        OptionKey.from_string(k): v
        for k, v in project_instance.option_instance.meson_options.items()
    }
    if hasattr(user_defined_options, 'cmd_line_options'):
        cmd_line_opts = {
            OptionKey.from_string(k): v
            for k, v in user_defined_options.cmd_line_options.items()
        }
        d.update(cmd_line_opts)
        user_defined_options.cmd_line_options = d
    intr = ConvertInterpreter(
        build_info,
        project_instance,
        state_tracker.project_config,
        user_defined_options=user_defined_options,
    )
    try:
        intr.run()
    except Exception as e:
        raise e
    processed_python_targets: T.Set[str] = set()
    processed_filegroups: T.Set[str] = set()
    processed_include_dirs: T.Set[str] = set()
    processed_flags: T.Set[str] = set()
    for custom_target in build_info.get_custom_targets().values():
        convert_ct = ConvertInstanceCustomTarget(custom_target, project_instance,
                                                 state_tracker.project_config)
        if convert_ct.skip_custom_target:
            continue
        state_tracker.add_custom_target(convert_ct)
        python_target = convert_ct.get_python_target()
        if python_target:
            if python_target.name not in processed_python_targets:
                state_tracker.add_python_target(python_target)
                processed_python_targets.add(python_target.name)
        for filegroup in convert_ct.get_generated_filegroups():
            if filegroup.name and filegroup.name not in processed_filegroups:
                state_tracker.add_file_group(filegroup)
                processed_filegroups.add(filegroup.name)
    for target in build_info.get_build_targets().values():
        build_target: T.Optional[T.Union[ConvertInstanceStaticLibrary,
                                         ConvertInstanceSharedLibrary]] = None
        if isinstance(target, build.StaticLibrary):
            build_target = ConvertInstanceStaticLibrary(
                build_info,
                target,
                project_instance,
                state_tracker.project_config,
            )
            state_tracker.add_static_library(build_target)
        elif isinstance(target, build.SharedLibrary):
            build_target = ConvertInstanceSharedLibrary(
                build_info,
                target,
                project_instance,
                state_tracker.project_config,
            )
            state_tracker.add_shared_library(build_target)
        if not build_target:
            continue
        for flag in build_target.generated_flags.values():
            if flag.name not in processed_flags:
                processed_flags.add(flag.name)
                state_tracker.add_flag(flag)
        for include_dir in build_target.generated_include_dirs.values():
            if (include_dir.name and include_dir.name not in processed_include_dirs):
                processed_include_dirs.add(include_dir.name)
                state_tracker.add_include_directory(include_dir)
        for filegroup in build_target.generated_filegroups.values():
            if filegroup.name and filegroup.name not in processed_filegroups:
                state_tracker.add_file_group(filegroup)
                processed_filegroups.add(filegroup.name)


def create_default_options(args: argparse.Namespace) -> argparse.Namespace:
    args.sourcedir = args.project_dir
    args.builddir = os.path.join(args.project_dir, 'convert-build')
    args.cross_file = []
    args.backend = 'none'
    args.projectoptions = []
    args.native_file = []
    args.cmd_line_options = {}
    return args


def choose_build_system(project_config: ConvertProjectConfig,
                        output_dir: str) -> T.Tuple[CommonStateTracker, CommonEmitter]:
    if project_config.build_system == 'soong':
        state_tracker: CommonStateTracker = SoongStateTracker(project_config)
        emitter: CommonEmitter = SoongEmitter(output_dir)
    elif project_config.build_system == 'bazel':
        state_tracker = BazelStateTracker(project_config)
        emitter = BazelEmitter(output_dir)
    else:
        sys.exit(f'Build system {project_config.build_system} not supported.')

    return (state_tracker, emitter)


def convert_build_system(
    config_toml: T.Dict[str, T.Any],
    toolchain_toml: T.Dict[str, T.Any],
    dependencies_toml: T.Dict[str, T.Any],
    options: argparse.Namespace,
) -> int:
    """
    Converts a Meson project to a different build system based on the provided configuration.

    This tool operates by parsing three main TOML configuration files: one for the
    project's structure and build options, another for defining the toolchains
    (compilers, linkers, and their capabilities), and a third for mapping external
    dependencies. The main logic iterates through each build configuration specified
    in the project's TOML file. For each configuration, it simulates a Meson build
    environment using an "abstract" toolchain that mimics a real one without
    actually invoking any compilers. A custom version of the Meson interpreter
    runs on the project's `meson.build` files. Instead of generating build
    commands, this interpreter gathers detailed information about all targets,
    sources, dependencies, and compiler flags. This information is collected into
    a build-system-agnostic state tracker. After processing all configurations,
    this tracker consolidates the data, resolving any conditional logic. Finally, a
    build system-specific "emitter" (e.g., for Soong or Bazel) takes this
    consolidated state and generates the corresponding build files (e.g.,
    `BUILD.bazel` or `Android.bp`).
    """
    dependencies = AbstractDependencies(dependencies_toml)
    toolchain_configs = {tc.get('name'): tc for tc in toolchain_toml.get('toolchain', [])}
    output_dir = (options.output_dir if options.output_dir else options.project_dir)

    project_config = ConvertProjectConfig(config_toml, dependencies)
    state_tracker, emitter = choose_build_system(project_config, output_dir)

    mlog.set_quiet()
    # Iterate over ConvertProjectInstance objects
    for project_instance in project_config.get_project_instances():
        default_options = create_default_options(options)
        default_options.cmd_line_options = project_instance.option_instance.meson_options
        custom_select_instances = set(project_instance.option_instance.select_instances)
        project_instance.emit()
        with tempfile.TemporaryDirectory() as build_dir:
            default_options.builddir = build_dir
            env = environment.Environment(
                default_options.sourcedir,
                default_options.builddir,
                default_options,
            )
            toolchain = AbstractToolchain(
                env,
                project_instance.host_toolchain,
                project_instance.build_toolchain,
                toolchain_configs,
            )
            if state_tracker:
                state_tracker.set_current_config(toolchain.toolchain_info, custom_select_instances)
                generate(
                    project_instance,
                    default_options,
                    toolchain,
                    env,
                    state_tracker,
                    custom_select_instances,
                )

    state_tracker.finish()
    emitter.emit(state_tracker)
    return 0
