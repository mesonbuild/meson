#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T
import os
import copy

from mesonbuild.mesonlib import MachineChoice
from mesonbuild.convert.abstract.abstract_toolchain import (
    AbstractToolchainInfo, )

from mesonbuild.convert.common_defs import (
    SelectInstance,
    SelectId,
    SelectKind,
)
from mesonbuild.convert.convert_project_config import (
    ConvertProjectConfig, )

from mesonbuild.convert.instance.convert_instance_utils import (
    ConvertInstanceFlag,
    ConvertInstanceIncludeDirectory,
    ConvertInstanceFileGroup,
)
from mesonbuild.convert.build_systems.common import (
    ConvertTarget,
    ConvertAttr,
    CommonStateTracker,
)
from mesonbuild.convert.instance.convert_instance_build_target import (
    RustABI,
    GeneratedFilesType,
    ConvertInstanceStaticLibrary,
    ConvertInstanceSharedLibrary,
)
from mesonbuild.convert.instance.convert_instance_custom_target import (
    ConvertInstanceCustomTarget,
    ConvertInstancePythonTarget,
    ConvertCustomTargetCmdPart,
    ConvertCustomTargetCmdPartType,
)


def bazel_get_os_info(toolchain: AbstractToolchainInfo, choice: MachineChoice) -> SelectInstance:
    machine_info = toolchain.machine_info[choice]
    os_string = machine_info.system
    os_select = SelectInstance(SelectId(SelectKind.OS, '', 'os'), os_string)
    return os_select


def bazel_get_arch_info(toolchain: AbstractToolchainInfo, choice: MachineChoice) -> SelectInstance:
    machine_info = toolchain.machine_info[choice]
    select_id = SelectId(SelectKind.ARCH, '', 'arch')
    arch_select = SelectInstance(select_id, machine_info.cpu_family)
    return arch_select


def _custom_target_convert(
    custom_target: ConvertInstanceCustomTarget,
    custom_target_type: GeneratedFilesType,
) -> ConvertInstanceCustomTarget:
    new_target = copy.deepcopy(custom_target)
    filter_target: T.List[str] = []
    if custom_target_type is GeneratedFilesType.HEADERS:
        new_target.name = f'{custom_target.name}_headers'
        new_target.generated_sources = []
        filter_target = custom_target.generated_sources
    elif custom_target_type is GeneratedFilesType.IMPL:
        new_target.name = f'{custom_target.name}_impl'
        new_target.generated_headers = []
        new_target.export_include_dirs = []
        filter_target = custom_target.generated_headers

    filtered_cmds: T.List[ConvertCustomTargetCmdPart] = []
    for cmd_part in custom_target.convert_instance_cmds:
        if (cmd_part.cmd_type == ConvertCustomTargetCmdPartType.OUTPUT
                and cmd_part.cmd in filter_target):
            filtered_cmds.append(
                ConvertCustomTargetCmdPart(
                    f'$(location {os.path.basename(cmd_part.cmd)})',
                    ConvertCustomTargetCmdPartType.STRING,
                ))
        else:
            filtered_cmds.append(cmd_part)

    new_target.convert_instance_cmds = filtered_cmds
    return new_target


class BazelCustomTarget(ConvertTarget):
    """Representation of a Bazel custom target."""

    def __init__(self, name: str, subdir: str):
        super().__init__(name, subdir)
        self.convert_instance_target: T.Optional[ConvertInstanceCustomTarget] = None
        self.module_type = 'genrule'
        self.cmd: str = ''

    def _get_cmd(self, convert_instance_cmds: T.List[ConvertCustomTargetCmdPart]) -> str:
        final_cmd = []
        for p in convert_instance_cmds:
            if isinstance(p, ConvertCustomTargetCmdPart):
                if p.cmd_type == ConvertCustomTargetCmdPartType.TOOL:
                    final_cmd.append(f'$(location {p.cmd})')
                elif p.cmd_type == ConvertCustomTargetCmdPartType.PYTHON_BINARY:
                    final_cmd.append(f'$(location {p.cmd})')
                elif p.cmd_type == ConvertCustomTargetCmdPartType.INPUT:
                    final_cmd.append(f'$(location {p.cmd})')
                elif p.cmd_type == ConvertCustomTargetCmdPartType.OUTPUT:
                    final_cmd.append(f'$(location {p.cmd})')
                elif p.cmd_type == ConvertCustomTargetCmdPartType.STRING:
                    final_cmd.append(p.cmd)
        return ' '.join(final_cmd)

    def add_config(
        self,
        ct: ConvertInstanceCustomTarget,
        current_toolchain: AbstractToolchainInfo,
        custom_select_instances: T.Set[SelectInstance],
    ) -> bool:
        if self.convert_instance_target is not None:
            return self.convert_instance_target == ct

        out = ct.generated_headers + ct.generated_sources
        self.get_attribute_node(ConvertAttr.OUT).add_common_values(out)
        self.get_attribute_node(ConvertAttr.SRCS).add_common_values(ct.srcs)
        self.get_attribute_node(ConvertAttr.TOOLS).add_common_values(ct.tools)
        self.cmd = self._get_cmd(ct.convert_instance_cmds)
        self.convert_instance_target = ct
        return True


class BazelIncludeDirectory(ConvertTarget):
    """Representation of a Bazel include directory."""

    def __init__(self, name: str, subdir: str):
        super().__init__(name, subdir)
        self.module_type = 'cc_library'

    def add_config(
        self,
        inc: ConvertInstanceIncludeDirectory,
        current_toolchain: AbstractToolchainInfo,
        custom_select_instances: T.Set[SelectInstance],
    ) -> None:
        os_select = bazel_get_os_info(current_toolchain, MachineChoice.HOST)
        arch_select = bazel_get_arch_info(current_toolchain, MachineChoice.HOST)
        label = {arch_select, os_select} | custom_select_instances
        self.get_attribute_node(ConvertAttr.INCLUDES).add_conditional_values(label, list(inc.paths))


class BazelFileGroup(ConvertTarget):
    """Representation of a Bazel file group."""

    def __init__(self, name: str, subdir: str):
        super().__init__(name, subdir)
        self.module_type = 'filegroup'

    def add_config(self, grp: ConvertInstanceFileGroup) -> None:
        self.get_attribute_node(ConvertAttr.SRCS).add_common_values(grp.srcs)


class BazelPythonTarget(ConvertTarget):
    """Representation of a Bazel Python target."""

    def __init__(self, name: str, subdir: str):
        super().__init__(name, subdir)
        self.module_type = 'py_binary'

    def add_config(self, target: ConvertInstancePythonTarget) -> None:
        self.single_attributes[ConvertAttr.PYTHON_MAIN] = f'"{target.main}"'
        self.get_attribute_node(ConvertAttr.SRCS).add_common_values(target.srcs)
        self.get_attribute_node(ConvertAttr.BAZEL_DEPS).add_common_values(target.libs)


class BazelFlag(ConvertTarget):
    """Representation of a Bazel flag target."""

    def __init__(self, name: str, subdir: str, language: str):
        super().__init__(name, subdir)
        self.module_type = 'cc_library'  # Using cc_library to hold flags
        self.language = language

    def add_config(
        self,
        flag: ConvertInstanceFlag,
        current_toolchain: AbstractToolchainInfo,
        custom_select_instances: T.Set[SelectInstance],
    ) -> None:
        os_select = bazel_get_os_info(current_toolchain, MachineChoice.HOST)
        arch_select = bazel_get_arch_info(current_toolchain, MachineChoice.HOST)
        label = {arch_select, os_select} | custom_select_instances

        self.get_attribute_node(ConvertAttr.BAZEL_DEFINES).add_conditional_values(
            label, flag.compile_args)
        if flag.link_args:
            self.get_attribute_node(ConvertAttr.LDFLAGS).add_conditional_values(
                label, flag.link_args)


class BazelBuildTarget(ConvertTarget):
    """Base class for Bazel build targets."""

    def __init__(self, name: str, subdir: str):
        super().__init__(name, subdir)
        self.rust_abi: T.Optional[RustABI] = None

    def add_config(
        self,
        build_target: T.Union[ConvertInstanceStaticLibrary, ConvertInstanceSharedLibrary],
        current_toolchain: AbstractToolchainInfo,
        custom_select_instances: T.Set[SelectInstance],
        converted_custom_targets: T.Dict[str, T.Tuple[str, str]],
    ) -> None:
        os_select = bazel_get_os_info(current_toolchain, build_target.machine_choice)
        arch_select = bazel_get_arch_info(current_toolchain, build_target.machine_choice)
        label = {arch_select, os_select} | custom_select_instances

        if build_target.rust_abi:
            self.rust_abi = build_target.rust_abi

        modified_gen_headers: T.List[str] = []
        modified_gen_sources: T.List[str] = []
        for header in build_target.generated_headers:
            if header in converted_custom_targets:
                modified_gen_headers.append(converted_custom_targets[header][0])
            else:
                modified_gen_headers.append(header)

        for source in build_target.generated_sources:
            if source in converted_custom_targets:
                modified_gen_sources.append(converted_custom_targets[source][1])
            else:
                modified_gen_sources.append(source)

        all_deps = (list(build_target.generated_flags) + list(build_target.generated_include_dirs) +
                    build_target.header_libs + build_target.static_libs + build_target.shared_libs +
                    build_target.whole_static_libs + modified_gen_headers + modified_gen_sources)

        self.get_attribute_node(ConvertAttr.SRCS).add_conditional_values(label, build_target.srcs)
        self.get_attribute_node(ConvertAttr.BAZEL_DEPS).add_conditional_values(label, all_deps)


class BazelStaticLibrary(BazelBuildTarget):
    """Representation of a Bazel static library."""

    def __init__(self, name: str, subdir: str, rust_abi: RustABI):
        super().__init__(name, subdir)
        self.module_type = 'cc_library'


class BazelSharedLibrary(BazelBuildTarget):
    """Representation of a Bazel shared library."""

    def __init__(self, name: str, subdir: str, rust_abi: RustABI):
        super().__init__(name, subdir)
        self.module_type = 'cc_library'


BazelTargetType = T.Union[
    BazelCustomTarget,
    BazelIncludeDirectory,
    BazelFileGroup,
    BazelPythonTarget,
    BazelFlag,
    BazelStaticLibrary,
    BazelSharedLibrary,
]


class BazelStateTracker(CommonStateTracker):
    """Tracks state for Bazel build system conversion."""

    def __init__(self, project_config: ConvertProjectConfig):
        super().__init__(project_config)
        self.targets: T.Dict[str, BazelTargetType] = {}
        self.converted_custom_targets: T.Dict[str, T.Tuple[str, str]] = {}

    def add_static_library(self, lib: ConvertInstanceStaticLibrary) -> None:
        if lib.name not in self.targets:
            self.targets[lib.name] = BazelStaticLibrary(lib.name, lib.subdir, lib.rust_abi)
        assert self.current_toolchain is not None
        assert self.current_custom_select_instances is not None
        T.cast(BazelBuildTarget, self.targets[lib.name]).add_config(
            lib,
            self.current_toolchain,
            self.current_custom_select_instances,
            self.converted_custom_targets,
        )

    def add_shared_library(self, lib: ConvertInstanceSharedLibrary) -> None:
        if lib.name not in self.targets:
            self.targets[lib.name] = BazelSharedLibrary(lib.name, lib.subdir, lib.rust_abi)
        assert self.current_toolchain is not None
        assert self.current_custom_select_instances is not None
        T.cast(BazelBuildTarget, self.targets[lib.name]).add_config(
            lib,
            self.current_toolchain,
            self.current_custom_select_instances,
            self.converted_custom_targets,
        )

    def add_python_target(self, target: ConvertInstancePythonTarget) -> None:
        if target.name not in self.targets:
            self.targets[target.name] = BazelPythonTarget(target.name, target.subdir)
        T.cast(BazelPythonTarget, self.targets[target.name]).add_config(target)

    def add_flag(self, flag: ConvertInstanceFlag) -> None:
        if flag.name not in self.targets:
            self.targets[flag.name] = BazelFlag(flag.name, flag.subdir, flag.language)

        assert self.current_toolchain is not None
        assert self.current_custom_select_instances is not None
        T.cast(BazelFlag, self.targets[flag.name]).add_config(flag, self.current_toolchain,
                                                              self.current_custom_select_instances)

    def add_include_directory(self, inc: ConvertInstanceIncludeDirectory) -> None:
        if inc.name not in self.targets:
            self.targets[inc.name] = BazelIncludeDirectory(inc.name, inc.subdir)

        assert self.current_toolchain is not None
        assert self.current_custom_select_instances is not None
        T.cast(BazelIncludeDirectory,
               self.targets[inc.name]).add_config(inc, self.current_toolchain,
                                                  self.current_custom_select_instances)

    def add_file_group(self, grp: ConvertInstanceFileGroup) -> None:
        if grp.name not in self.targets:
            self.targets[grp.name] = BazelFileGroup(grp.name, grp.subdir)
        T.cast(BazelFileGroup, self.targets[grp.name]).add_config(grp)

    def add_custom_target(self, custom_target: ConvertInstanceCustomTarget) -> None:
        modified_targets: T.List[ConvertInstanceCustomTarget] = []
        if custom_target.generated_headers and custom_target.generated_sources:
            modified_targets.append(
                _custom_target_convert(custom_target, GeneratedFilesType.HEADERS))
            modified_targets.append(_custom_target_convert(custom_target, GeneratedFilesType.IMPL))
            self.converted_custom_targets[custom_target.name] = (
                modified_targets[0].name,
                modified_targets[1].name,
            )
        else:
            modified_targets.append(custom_target)

        for ct in modified_targets:
            if ct.name not in self.targets:
                self.targets[ct.name] = BazelCustomTarget(ct.name, ct.subdir)

            assert self.current_toolchain is not None
            assert self.current_custom_select_instances is not None
            success = T.cast(BazelCustomTarget, self.targets[ct.name]).add_config(
                ct,
                self.current_toolchain,
                self.current_custom_select_instances,
            )
            if not success:
                self.targets.pop(ct.name)
                print('Removed custom target that differed across configs')

    def finish(self) -> None:
        all_os_selects: T.Set[SelectInstance] = set()
        all_arch_selects: T.Set[SelectInstance] = set()
        all_select_instances: T.List[T.Set[SelectInstance]] = []
        all_custom_defaults: T.Set[SelectInstance] = set()

        all_custom_selects = self.project_config.get_all_custom_selects()

        for custom_select in all_custom_selects:
            all_select_instances.append(custom_select.get_select_instances())
            all_custom_defaults.add(custom_select.get_default_instance())

        for toolchain in self.all_toolchains:
            all_os_selects.add(bazel_get_os_info(toolchain, MachineChoice.HOST))
            all_arch_selects.add(bazel_get_arch_info(toolchain, MachineChoice.HOST))

        all_select_instances.append(all_os_selects)
        all_select_instances.append(all_arch_selects)

        for target in self.targets.values():
            target.finish(all_select_instances, all_custom_defaults)
