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


def soong_get_os_info(toolchain: AbstractToolchainInfo, choice: MachineChoice) -> SelectInstance:
    machine_info = toolchain.machine_info[choice]
    toolchain_str = toolchain.toolchains[choice]

    os_string: str
    if machine_info.system == 'linux':
        if toolchain_str.startswith('linux_glibc'):
            os_string = 'linux_glibc'
        else:
            os_string = 'linux_musl'
    else:
        os_string = machine_info.system

    os_select = SelectInstance(SelectId(SelectKind.OS, '', 'os'), os_string)
    return os_select


def soong_get_arch_info(toolchain: AbstractToolchainInfo, choice: MachineChoice) -> SelectInstance:
    machine_info = toolchain.machine_info[choice]
    select_id = SelectId(SelectKind.ARCH, '', 'arch')
    arch = machine_info.cpu_family

    # meson CPU families' don't seem to accept "arm64"
    if arch == 'aarch64':
        arch = 'arm64'

    arch_select = SelectInstance(select_id, arch)
    return arch_select


def _custom_target_convert(
    custom_target: ConvertInstanceCustomTarget,
    custom_target_type: GeneratedFilesType,
) -> ConvertInstanceCustomTarget:
    new_target = copy.deepcopy(custom_target)
    filter_target: T.List[str] = []
    if custom_target_type == GeneratedFilesType.HEADERS:
        new_target.name = f'{custom_target.name}_headers'
        new_target.generated_sources = []
        filter_target = custom_target.generated_sources
    elif custom_target_type == GeneratedFilesType.IMPL:
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
                    f'@@GEN_DIR@@/{os.path.basename(cmd_part.cmd)}',
                    ConvertCustomTargetCmdPartType.STRING,
                ))
        else:
            filtered_cmds.append(cmd_part)

    new_target.convert_instance_cmds = filtered_cmds
    return new_target


class SoongCustomTarget(ConvertTarget):
    """Representation of a Soong custom target."""

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
                    processed_cmd = p.cmd.replace('@@GEN_DIR@@', '$(genDir)')
                    final_cmd.append(processed_cmd)
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
        self.get_attribute_node(ConvertAttr.INCLUDES).add_common_values(ct.export_include_dirs)
        self.cmd = self._get_cmd(ct.convert_instance_cmds)
        self.convert_instance_target = ct
        return True


class SoongIncludeDirectory(ConvertTarget):
    """Representation of a Soong include directory."""

    def __init__(self, name: str, subdir: str):
        super().__init__(name, subdir)
        self.module_type = 'cc_library_headers'

    def add_config(
        self,
        inc: ConvertInstanceIncludeDirectory,
        current_toolchain: AbstractToolchainInfo,
        custom_select_instances: T.Set[SelectInstance],
    ) -> None:
        os_select = soong_get_os_info(current_toolchain, MachineChoice.HOST)
        arch_select = soong_get_arch_info(current_toolchain, MachineChoice.HOST)

        label = {arch_select} | {os_select} | custom_select_instances
        self.single_attributes[ConvertAttr.SOONG_VENDOR] = 'true'
        if current_toolchain.host_supported():
            self.single_attributes[ConvertAttr.SOONG_HOST_SUPPORTED] = 'true'

        self.get_attribute_node(ConvertAttr.INCLUDES).add_conditional_values(label, list(inc.paths))


class SoongFileGroup(ConvertTarget):
    """Representation of a Soong file group."""

    def __init__(self, name: str, subdir: str):
        super().__init__(name, subdir)
        self.module_type = 'filegroup'

    def add_config(self, grp: ConvertInstanceFileGroup) -> None:
        self.get_attribute_node(ConvertAttr.SRCS).add_common_values(grp.srcs)


class SoongPythonTarget(ConvertTarget):
    """Representation of a Soong Python target."""

    def __init__(self, name: str, subdir: str):
        super().__init__(name, subdir)
        self.module_type = 'python_binary_host'

    def add_config(self, target: ConvertInstancePythonTarget) -> None:
        self.single_attributes[ConvertAttr.PYTHON_MAIN] = f'"{target.main}"'
        self.get_attribute_node(ConvertAttr.SRCS).add_common_values(target.srcs)
        self.get_attribute_node(ConvertAttr.SOONG_PYTHON_LIBS).add_common_values(target.libs)


class SoongFlag(ConvertTarget):
    """Representation of a Soong flag target."""

    def __init__(self, name: str, subdir: str, language: str):
        super().__init__(name, subdir)
        if language == 'rust':
            self.module_type = 'rust_defaults'
        else:
            self.module_type = 'cc_defaults'

        self.project_native_args = False
        self.host_supported = False

    def add_config(
        self,
        flag: ConvertInstanceFlag,
        current_toolchain: AbstractToolchainInfo,
        custom_select_instances: T.Set[SelectInstance],
    ) -> None:
        os_select = soong_get_os_info(current_toolchain, MachineChoice.HOST)
        arch_select = soong_get_arch_info(current_toolchain, MachineChoice.HOST)

        label = {arch_select} | {os_select} | custom_select_instances
        self.single_attributes[ConvertAttr.SOONG_VENDOR] = 'true'
        if current_toolchain.host_supported():
            self.single_attributes[ConvertAttr.SOONG_HOST_SUPPORTED] = 'true'
            self.host_supported = True

        if flag.project_native_args:
            self.project_native_args = True

        if flag.language == 'c':
            self.get_attribute_node(ConvertAttr.SOONG_CFLAGS).add_conditional_values(
                label, flag.compile_args)
        elif flag.language == 'cpp':
            self.get_attribute_node(ConvertAttr.SOONG_CPPFLAGS).add_conditional_values(
                label, flag.compile_args)
        elif flag.language == 'rust':
            self.get_attribute_node(ConvertAttr.RUSTFLAGS).add_conditional_values(
                label, flag.compile_args)

        if flag.link_args:
            self.get_attribute_node(ConvertAttr.LDFLAGS).add_conditional_values(
                label, flag.link_args)


class SoongBuildTarget(ConvertTarget):
    """Base class for Soong build targets."""

    def __init__(self, name: str, subdir: str):
        super().__init__(name, subdir)
        self.rust_abi: T.Optional[RustABI] = None
        self.crate_root: str = ''
        self.install = False

    def add_config(
        self,
        build_target: T.Union[ConvertInstanceStaticLibrary, ConvertInstanceSharedLibrary],
        current_toolchain: AbstractToolchainInfo,
        custom_select_instances: T.Set[SelectInstance],
        converted_custom_targets: T.Dict[str, T.Tuple[str, str]],
    ) -> None:
        os_select = soong_get_os_info(current_toolchain, build_target.machine_choice)
        arch_select = soong_get_arch_info(current_toolchain, build_target.machine_choice)
        label = {arch_select} | {os_select} | custom_select_instances

        if build_target.rust_abi:
            self.rust_abi = build_target.rust_abi

        if build_target.crate_root:
            self.crate_root = build_target.crate_root

        self.install |= build_target.install
        header_libs = list(build_target.generated_include_dirs) + build_target.header_libs

        self.single_attributes[ConvertAttr.SOONG_VENDOR] = 'true'
        if current_toolchain.host_supported():
            self.single_attributes[ConvertAttr.SOONG_HOST_SUPPORTED] = 'true'

        self.get_attribute_node(ConvertAttr.SOONG_DEFAULTS).add_common_values(
            list(build_target.generated_flags))

        if build_target.rust_abi == RustABI.NONE:
            if build_target.c_std:
                self.single_attributes[ConvertAttr.SOONG_C_STD] = f'"{build_target.c_std}"'
            if build_target.cpp_std:
                self.single_attributes[ConvertAttr.SOONG_CPP_STD] = f'"{build_target.cpp_std}"'
            self.get_attribute_node(ConvertAttr.SOONG_HEADER_LIBS).add_conditional_values(
                label, header_libs)

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

            self.get_attribute_node(ConvertAttr.SOONG_GENERATED_HEADERS).add_conditional_values(
                label, modified_gen_headers)
            self.get_attribute_node(ConvertAttr.SOONG_GENERATED_SOURCES).add_conditional_values(
                label, modified_gen_sources)
            self.get_attribute_node(ConvertAttr.SRCS).add_conditional_values(
                label, build_target.srcs)
            self.get_attribute_node(ConvertAttr.SOONG_STATIC_LIBRARIES).add_conditional_values(
                label, build_target.static_libs)
            self.get_attribute_node(ConvertAttr.SOONG_SHARED_LIBRARIES).add_conditional_values(
                label, build_target.shared_libs)
            self.get_attribute_node(
                ConvertAttr.SOONG_WHOLE_STATIC_LIBRARIES).add_conditional_values(
                    label, build_target.whole_static_libs)
        else:
            if build_target.rust_edition:
                self.single_attributes[ConvertAttr.RUST_EDITION] = f'"{build_target.rust_edition}"'
            self.single_attributes[ConvertAttr.RUST_CRATE_ROOT] = f'"{build_target.crate_root}"'
            self.single_attributes[ConvertAttr.RUST_CRATE_NAME] = f'"{build_target.crate_name}"'
            self.get_attribute_node(ConvertAttr.SOONG_RUST_LIBS).add_common_values(
                build_target.static_libs)
            self.get_attribute_node(ConvertAttr.RUST_PROC_MACROS).add_common_values(
                build_target.proc_macros)


class SoongStaticLibrary(SoongBuildTarget):
    """Representation of a Soong static library."""

    def __init__(self, name: str, subdir: str, rust_abi: RustABI):
        super().__init__(name, subdir)
        if rust_abi == RustABI.RUST:
            self.module_type = 'rust_library'
        elif rust_abi == RustABI.C:
            self.module_type = 'rust_ffi_static'
        else:
            self.module_type = 'cc_library_static'


class SoongSharedLibrary(SoongBuildTarget):
    """Representation of a Soong shared library."""

    def __init__(self, name: str, subdir: str, rust_abi: RustABI):
        super().__init__(name, subdir)

        if rust_abi == RustABI.C:
            self.module_type = 'rust_ffi_shared'
        else:
            self.module_type = 'cc_library_shared'


SoongTargetType = T.Union[
    SoongCustomTarget,
    SoongIncludeDirectory,
    SoongFileGroup,
    SoongPythonTarget,
    SoongFlag,
    SoongStaticLibrary,
    SoongSharedLibrary,
]


class SoongStateTracker(CommonStateTracker):
    """Tracks state for Soong build system conversion."""

    def __init__(self, project_config: ConvertProjectConfig):
        super().__init__(project_config)
        self.targets: T.Dict[str, SoongTargetType] = {}
        self.converted_custom_targets: T.Dict[str, T.Tuple[str, str]] = {}

    def add_static_library(self, lib: ConvertInstanceStaticLibrary) -> None:
        if lib.name not in self.targets:
            self.targets[lib.name] = SoongStaticLibrary(lib.name, lib.subdir, lib.rust_abi)
        assert self.current_toolchain is not None
        assert self.current_custom_select_instances is not None
        T.cast(SoongBuildTarget, self.targets[lib.name]).add_config(
            lib,
            self.current_toolchain,
            self.current_custom_select_instances,
            self.converted_custom_targets,
        )

    def add_shared_library(self, lib: ConvertInstanceSharedLibrary) -> None:
        if lib.name not in self.targets:
            self.targets[lib.name] = SoongSharedLibrary(lib.name, lib.subdir, lib.rust_abi)
        assert self.current_toolchain is not None
        assert self.current_custom_select_instances is not None
        T.cast(SoongBuildTarget, self.targets[lib.name]).add_config(
            lib,
            self.current_toolchain,
            self.current_custom_select_instances,
            self.converted_custom_targets,
        )

    def add_python_target(self, target: ConvertInstancePythonTarget) -> None:
        if target.name not in self.targets:
            self.targets[target.name] = SoongPythonTarget(target.name, target.subdir)
        T.cast(SoongPythonTarget, self.targets[target.name]).add_config(target)

    def add_flag(self, flag: ConvertInstanceFlag) -> None:
        if flag.name not in self.targets:
            self.targets[flag.name] = SoongFlag(flag.name, flag.subdir, flag.language)

        assert self.current_toolchain is not None
        assert self.current_custom_select_instances is not None
        T.cast(SoongFlag, self.targets[flag.name]).add_config(flag, self.current_toolchain,
                                                              self.current_custom_select_instances)

    def add_include_directory(self, inc: ConvertInstanceIncludeDirectory) -> None:
        if inc.name not in self.targets:
            self.targets[inc.name] = SoongIncludeDirectory(inc.name, inc.subdir)

        assert self.current_toolchain is not None
        assert self.current_custom_select_instances is not None
        T.cast(SoongIncludeDirectory,
               self.targets[inc.name]).add_config(inc, self.current_toolchain,
                                                  self.current_custom_select_instances)

    def add_file_group(self, grp: ConvertInstanceFileGroup) -> None:
        if grp.name not in self.targets:
            self.targets[grp.name] = SoongFileGroup(grp.name, grp.subdir)
        T.cast(SoongFileGroup, self.targets[grp.name]).add_config(grp)

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
                self.targets[ct.name] = SoongCustomTarget(ct.name, ct.subdir)

            assert self.current_toolchain is not None
            assert self.current_custom_select_instances is not None
            success = T.cast(SoongCustomTarget, self.targets[ct.name]).add_config(
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
            all_os_selects.add(soong_get_os_info(toolchain, MachineChoice.HOST))
            all_arch_selects.add(soong_get_arch_info(toolchain, MachineChoice.HOST))

        all_select_instances.append(all_os_selects)
        all_select_instances.append(all_arch_selects)

        for target in self.targets.values():
            target.finish(all_select_instances, all_custom_defaults)
