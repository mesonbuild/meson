#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T
import os
import copy

from mesonbuild import mlog
from mesonbuild.mesonlib import MachineChoice
from mesonbuild.convert.abstract.abstract_toolchain import (
    AbstractToolchainInfo,
)

from mesonbuild.convert.common_defs import (
    SelectInstance,
    SelectId,
    SelectKind,
)

from mesonbuild.convert.instance.convert_instance_utils import (
    ConvertDep,
    ConvertSrc,
    ConvertInstanceFlag,
    ConvertInstanceIncludeDirectory,
    ConvertInstanceFileGroup,
)
from mesonbuild.convert.build_systems.common import (
    ConvertBackend,
    ConvertStateTracker,
)
from mesonbuild.convert.build_systems.target import (
    ConvertAttr,
    ConvertFileGroup,
    ConvertIncludeDirectory,
    ConvertPythonTarget,
    ConvertFlag,
    ConvertBuildTarget,
    ConvertCustomTarget,
)
from mesonbuild.convert.instance.convert_instance_build_target import (
    ConvertInstanceStaticLibrary,
    ConvertInstanceSharedLibrary,
    GeneratedFilesType,
    RustABI,
)
from mesonbuild.convert.instance.convert_instance_custom_target import (
    ConvertInstanceCustomTarget,
    ConvertInstancePythonTarget,
    ConvertCustomTargetCmdPart,
    ConvertCustomTargetCmdPartType,
)


def _get_soong_targets(convert_deps: T.List[ConvertDep]) -> T.List[str]:
    soong_targets: T.List[str] = []
    for dep in convert_deps:
        soong_targets.append(dep.target)

    return soong_targets


def _get_soong_sources(convert_srcs: T.List[ConvertSrc]) -> T.List[str]:
    soong_srcs: T.List[str] = []
    for src in convert_srcs:
        if src.target_dep:
            soong_srcs.append(":" + src.target_dep.target)
        else:
            soong_srcs.append(src.source)

    return soong_srcs


def _custom_target_convert(custom_target: ConvertInstanceCustomTarget,
                           custom_target_type: GeneratedFilesType) -> ConvertInstanceCustomTarget:  # fmt: skip
    new_target = copy.deepcopy(custom_target)
    filter_target: T.List[str] = []
    if custom_target_type == GeneratedFilesType.HEADERS:
        new_target.name = f"{custom_target.name}_headers"
        new_target.generated_sources = []
        filter_target = custom_target.generated_sources
    elif custom_target_type == GeneratedFilesType.IMPL:
        new_target.name = f"{custom_target.name}_impl"
        new_target.generated_headers = []
        new_target.export_include_dirs = []
        filter_target = custom_target.generated_headers

    filtered_cmds: T.List[ConvertCustomTargetCmdPart] = []
    for cmd_part in custom_target.convert_instance_cmds:
        if (
            cmd_part.cmd_type == ConvertCustomTargetCmdPartType.OUTPUT
            and cmd_part.cmd in filter_target
        ):
            filtered_cmds.append(
                ConvertCustomTargetCmdPart(
                    f"@@GEN_DIR@@/{os.path.basename(cmd_part.cmd)}",
                    ConvertCustomTargetCmdPartType.STRING,
                )
            )
        else:
            filtered_cmds.append(cmd_part)

    new_target.convert_instance_cmds = filtered_cmds
    return new_target


class SoongBackend(ConvertBackend):
    """Soong backend for build system conversion."""

    def __init__(self) -> None:
        self.converted_custom_targets: T.Dict[str, T.Tuple[str, str]] = {}

    def get_os_info(
        self, toolchain: AbstractToolchainInfo, choice: MachineChoice
    ) -> SelectInstance:
        machine_info = toolchain.machine_info[choice]
        toolchain_str = toolchain.toolchains[choice]

        os_string: str
        if machine_info.system == "linux":
            if toolchain_str.startswith("linux_glibc"):
                os_string = "linux_glibc"
            else:
                os_string = "linux_musl"
        else:
            os_string = machine_info.system

        os_select = SelectInstance(SelectId(SelectKind.OS, "", "os"), os_string)
        return os_select

    def get_arch_info(
        self, toolchain: AbstractToolchainInfo, choice: MachineChoice
    ) -> SelectInstance:
        machine_info = toolchain.machine_info[choice]
        select_id = SelectId(SelectKind.ARCH, "", "arch")
        arch = machine_info.cpu_family

        # meson CPU families' don't seem to accept "arm64"
        if arch == "aarch64":
            arch = "arm64"

        arch_select = SelectInstance(select_id, arch)
        return arch_select

    def add_python_config(
        self, target: ConvertPythonTarget, instance: ConvertInstancePythonTarget
    ) -> None:
        target.single_attributes[ConvertAttr.PYTHON_MAIN] = (
            f'"{instance.main.target_only()}"'
        )
        target.get_attribute_node(ConvertAttr.SRCS).add_common_values(
            _get_soong_sources(instance.srcs)
        )
        target.get_attribute_node(ConvertAttr.SOONG_PYTHON_LIBS).add_common_values(
            instance.libs
        )

    def add_flag_config(
            self,
            target: ConvertFlag,
            instance: ConvertInstanceFlag,
            toolchain: AbstractToolchainInfo,
            custom_instances: T.Set[SelectInstance]) -> None:  # fmt: skip
        if not hasattr(target, "project_native_args"):
            target.project_native_args = False
        if not hasattr(target, "host_supported"):
            target.host_supported = False

        os_select = self.get_os_info(toolchain, MachineChoice.HOST)
        arch_select = self.get_arch_info(toolchain, MachineChoice.HOST)

        label = {arch_select} | {os_select} | custom_instances
        target.single_attributes[ConvertAttr.SOONG_VENDOR] = "true"
        if toolchain.host_supported():
            target.single_attributes[ConvertAttr.SOONG_HOST_SUPPORTED] = "true"
            target.host_supported = True

        if instance.project_native_args:
            target.project_native_args = True

        if instance.language == "c":
            target.get_attribute_node(ConvertAttr.SOONG_CFLAGS).add_conditional_values(
                label, instance.compile_args
            )
        elif instance.language == "cpp":
            target.get_attribute_node(
                ConvertAttr.SOONG_CPPFLAGS
            ).add_conditional_values(label, instance.compile_args)
        elif instance.language == "rust":
            target.get_attribute_node(ConvertAttr.RUSTFLAGS).add_conditional_values(
                label, instance.compile_args
            )

        if instance.link_args:
            target.get_attribute_node(ConvertAttr.LDFLAGS).add_conditional_values(
                label, instance.link_args
            )

    def add_include_dir_config(
            self,
            target: ConvertIncludeDirectory,
            instance: ConvertInstanceIncludeDirectory,
            toolchain: AbstractToolchainInfo,
            custom_instances: T.Set[SelectInstance]) -> None:  # fmt: skip
        os_select = self.get_os_info(toolchain, MachineChoice.HOST)
        arch_select = self.get_arch_info(toolchain, MachineChoice.HOST)

        label = {arch_select} | {os_select} | custom_instances
        target.single_attributes[ConvertAttr.SOONG_VENDOR] = "true"
        if toolchain.host_supported():
            target.single_attributes[ConvertAttr.SOONG_HOST_SUPPORTED] = "true"

        target.get_attribute_node(ConvertAttr.INCLUDES).add_conditional_values(
            label, list(instance.paths)
        )

    def add_file_group_config(
        self, target: ConvertFileGroup, instance: ConvertInstanceFileGroup
    ) -> None:
        target.get_attribute_node(ConvertAttr.SRCS).add_common_values(instance.srcs)

    def _get_custom_target_cmd(
        self, convert_instance_cmds: T.List[ConvertCustomTargetCmdPart]
    ) -> str:
        final_cmd = []
        for p in convert_instance_cmds:
            if isinstance(p, ConvertCustomTargetCmdPart):
                if p.cmd_type == ConvertCustomTargetCmdPartType.TOOL:
                    final_cmd.append(f"$(location {p.src.target_only()})")
                elif p.cmd_type == ConvertCustomTargetCmdPartType.PYTHON_BINARY:
                    final_cmd.append(f"$(location {p.src.target_only()})")
                elif p.cmd_type == ConvertCustomTargetCmdPartType.INPUT:
                    soong_src = _get_soong_sources([p.src])[0]
                    final_cmd.append(f"$(location {soong_src})")
                elif p.cmd_type == ConvertCustomTargetCmdPartType.OUTPUT:
                    final_cmd.append(f"$(location {p.cmd})")
                elif p.cmd_type == ConvertCustomTargetCmdPartType.STRING:
                    processed_cmd = p.cmd.replace("@@GEN_DIR@@", "$(genDir)")
                    final_cmd.append(processed_cmd)
        return " ".join(final_cmd)

    def add_custom_target(
        self, state_tracker: ConvertStateTracker, instance: ConvertInstanceCustomTarget
    ) -> None:
        modified_targets: T.List[ConvertInstanceCustomTarget] = []
        if instance.generated_headers and instance.generated_sources:
            modified_targets.append(
                _custom_target_convert(instance, GeneratedFilesType.HEADERS)
            )
            modified_targets.append(
                _custom_target_convert(instance, GeneratedFilesType.IMPL)
            )
            self.converted_custom_targets[instance.name] = (
                modified_targets[0].name,
                modified_targets[1].name,
            )
        else:
            modified_targets.append(instance)

        for ct in modified_targets:
            if ct.name not in state_tracker.targets:
                state_tracker.targets[ct.name] = ConvertCustomTarget(
                    ct.name, ct.subdir, instance
                )

            target = T.cast(ConvertCustomTarget, state_tracker.targets[ct.name])
            if target.instance != instance:
                state_tracker.targets.pop(ct.name)
                mlog.warning("Dropped custom target that differed across configs")
                return

            out = ct.generated_headers + ct.generated_sources
            target.get_attribute_node(ConvertAttr.OUT).add_common_values(out)
            target.get_attribute_node(ConvertAttr.SRCS).add_common_values(
                _get_soong_sources(ct.srcs)
            )
            target.get_attribute_node(ConvertAttr.TOOLS).add_common_values(
                [t.target_only() for t in ct.tools]
            )
            target.get_attribute_node(ConvertAttr.INCLUDES).add_common_values(
                ct.export_include_dirs
            )
            target.cmd = self._get_custom_target_cmd(ct.convert_instance_cmds)

    def add_build_target_config(
            self,
            target: ConvertBuildTarget,
            instance: T.Union[ConvertInstanceStaticLibrary, ConvertInstanceSharedLibrary],
            toolchain: AbstractToolchainInfo,
            custom_instances: T.Set[SelectInstance]) -> None:  # fmt: skip
        if not hasattr(target, "install"):
            target.install = False

        os_select = self.get_os_info(toolchain, instance.machine_choice)
        arch_select = self.get_arch_info(toolchain, instance.machine_choice)
        label = {arch_select} | {os_select} | custom_instances

        target.install |= instance.install
        header_libs = list(instance.generated_include_dirs) + _get_soong_targets(
            instance.header_libs
        )

        target.single_attributes[ConvertAttr.SOONG_VENDOR] = "true"
        if toolchain.host_supported():
            target.single_attributes[ConvertAttr.SOONG_HOST_SUPPORTED] = "true"

        target.get_attribute_node(ConvertAttr.SOONG_DEFAULTS).add_common_values(
            list(instance.generated_flags)
        )

        if target.rust_abi == RustABI.NONE:
            if instance.c_std:
                target.single_attributes[ConvertAttr.SOONG_C_STD] = (
                    f'"{instance.c_std}"'
                )
            if instance.cpp_std:
                target.single_attributes[ConvertAttr.SOONG_CPP_STD] = (
                    f'"{instance.cpp_std}"'
                )
            target.get_attribute_node(
                ConvertAttr.SOONG_HEADER_LIBS
            ).add_conditional_values(label, header_libs)

            modified_gen_headers: T.List[str] = []
            modified_gen_sources: T.List[str] = []
            for header in instance.generated_headers:
                if header.target in self.converted_custom_targets:
                    modified_gen_headers.append(
                        self.converted_custom_targets[header.target][0]
                    )
                else:
                    modified_gen_headers.append(header.target)

            for source in instance.generated_sources:
                if source.target in self.converted_custom_targets:
                    modified_gen_sources.append(
                        self.converted_custom_targets[source.target][1]
                    )
                else:
                    modified_gen_sources.append(source.target)

            target.get_attribute_node(
                ConvertAttr.SOONG_GENERATED_HEADERS
            ).add_conditional_values(label, modified_gen_headers)
            target.get_attribute_node(
                ConvertAttr.SOONG_GENERATED_SOURCES
            ).add_conditional_values(label, modified_gen_sources)
            target.get_attribute_node(ConvertAttr.SRCS).add_conditional_values(
                label, _get_soong_sources(instance.srcs)
            )
            target.get_attribute_node(
                ConvertAttr.SOONG_STATIC_LIBRARIES
            ).add_conditional_values(label, _get_soong_targets(instance.static_libs))
            target.get_attribute_node(
                ConvertAttr.SOONG_SHARED_LIBRARIES
            ).add_conditional_values(label, _get_soong_targets(instance.shared_libs))
            target.get_attribute_node(
                ConvertAttr.SOONG_WHOLE_STATIC_LIBRARIES
            ).add_conditional_values(
                label, _get_soong_targets(instance.whole_static_libs)
            )
        else:
            if instance.rust_edition:
                target.single_attributes[ConvertAttr.RUST_EDITION] = (
                    f'"{instance.rust_edition}"'
                )
            target.single_attributes[ConvertAttr.RUST_CRATE_ROOT] = (
                f'"{instance.crate_root}"'
            )
            target.single_attributes[ConvertAttr.RUST_CRATE_NAME] = (
                f'"{instance.crate_name}"'
            )
            target.get_attribute_node(ConvertAttr.SOONG_RUST_LIBS).add_common_values(
                _get_soong_targets(instance.static_libs)
            )
            target.get_attribute_node(ConvertAttr.RUST_PROC_MACROS).add_common_values(
                _get_soong_targets(instance.proc_macros)
            )
