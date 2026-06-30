#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T
import copy

from mesonbuild import mlog
from mesonbuild.mesonlib import MachineChoice
from mesonbuild.convert.precomputed.precomputed_platform import PrecomputedPlatformInfo

from mesonbuild.convert.common_defs import SelectInstance, SelectId, SelectKind, GeneratedFilesType

from mesonbuild.convert.instance.convert_instance_utils import (
    ConvertId,
    ConvertInstanceFlag,
    ConvertInstanceIncludeDirectory,
    ConvertInstanceFileGroup,
    ConvertInstancePythonBinary,
)
from mesonbuild.convert.build_systems.common import ConvertBackend, ConvertStateTracker
from mesonbuild.convert.build_systems.target import (
    ConvertAttr,
    ConvertFileGroup,
    ConvertIncludeDirectory,
    ConvertPythonBinary,
    ConvertFlag,
    ConvertBuildTarget,
    ConvertCustomTarget,
)
from mesonbuild.convert.instance.convert_instance_build_target import (
    ConvertInstanceStaticLibrary,
    ConvertInstanceSharedLibrary,
    RustABI,
)
from mesonbuild.convert.instance.convert_instance_custom_target import (
    ConvertInstanceCustomTarget,
    ConvertCustomTargetCmdPart,
    ConvertCustomTargetCmdPartType,
    GeneratedOutput,
)
from mesonbuild.convert.build_systems.utils import (
    substitute_inputs_into_string,
    substitute_indexed_inputs_into_string,
    substitute_outputs_into_string,
    substitute_indexed_outputs_into_string,
)


def _get_soong_targets(convert_deps: T.List[ConvertId]) -> T.List[str]:
    return [d.name for d in convert_deps]


def _get_soong_sources(convert_srcs: T.List[ConvertId]) -> T.List[str]:
    soong_srcs: T.List[str] = []
    for src in convert_srcs:
        if src.local:
            soong_srcs.append(src.name)
        else:
            soong_srcs.append(':' + src.name)

    return soong_srcs


def _custom_target_convert(custom_target: ConvertInstanceCustomTarget,
                           custom_target_type: GeneratedFilesType) -> ConvertInstanceCustomTarget:  # fmt: skip
    new_target = copy.deepcopy(custom_target)
    new_target.custom_target_type = custom_target_type

    if custom_target_type is GeneratedFilesType.HEADERS:
        new_target.name = f'{custom_target.name}_headers'
    elif custom_target_type is GeneratedFilesType.IMPL:
        new_target.name = f'{custom_target.name}_impl'
        new_target.export_include_dirs = []

    current_outputs = custom_target.get_outputs_by_type(custom_target_type)
    new_target.generated_outputs = [
        GeneratedOutput(
            f'$(location {o.output})' if o.output in current_outputs else f'$(genDir)/{o.output}',
            o.file_type,
        )
        for o in custom_target.generated_outputs
    ]

    return new_target


class SoongBackend(ConvertBackend):
    """Soong backend for build system conversion."""

    def __init__(self) -> None:
        self.converted_custom_targets: T.Dict[str, T.Tuple[str, str]] = {}

    def get_os_info(self, platform: PrecomputedPlatformInfo,
                    choice: MachineChoice) -> SelectInstance:  # fmt: skip
        machine_info = platform.machine_info[choice]
        platform_str = platform.platforms[choice]

        os_string: str
        if machine_info.system == 'linux':
            if platform_str.startswith('linux_glibc'):
                os_string = 'linux_glibc'
            else:
                os_string = 'linux_musl'
        else:
            os_string = machine_info.system

        os_select = SelectInstance(SelectId(SelectKind.OS, '', 'os'), os_string)
        return os_select

    def get_arch_info(self, platform: PrecomputedPlatformInfo,
                      choice: MachineChoice) -> SelectInstance:  # fmt: skip
        machine_info = platform.machine_info[choice]
        select_id = SelectId(SelectKind.ARCH, '', 'arch')
        arch = machine_info.cpu_family

        # meson CPU families' don't seem to accept "arm64"
        if arch == 'aarch64':
            arch = 'arm64'

        arch_select = SelectInstance(select_id, arch)
        return arch_select

    def add_python_binary_config(self, target: ConvertPythonBinary,
                                 instance: ConvertInstancePythonBinary) -> None:  # fmt: skip
        target.single_attributes[ConvertAttr.PYTHON_MAIN] = f'"{instance.main}"'
        target.get_attribute_node(ConvertAttr.SRCS).add_common_values(
            _get_soong_sources(list(instance.srcs))
        )
        target.get_attribute_node(ConvertAttr.SOONG_PYTHON_LIBS).add_common_values(
            _get_soong_targets(list(instance.libs))
        )

    def add_flag_config(self, target: ConvertFlag, instance: ConvertInstanceFlag,
                        platform: PrecomputedPlatformInfo,
                        custom_instances: T.Set[SelectInstance]) -> None:  # fmt: skip
        label = self.get_label(platform, custom_instances)
        target.single_attributes[ConvertAttr.SOONG_VENDOR] = 'true'
        if platform.is_native():
            target.single_attributes[ConvertAttr.SOONG_HOST_SUPPORTED] = 'true'
            target.host_supported = True

        if instance.project_native_args:
            target.project_native_args = True

        if instance.language == 'c':
            target.get_attribute_node(ConvertAttr.SOONG_CFLAGS).add_conditional_values(
                label, instance.compile_args
            )
        elif instance.language == 'cpp':
            target.get_attribute_node(ConvertAttr.SOONG_CPPFLAGS).add_conditional_values(
                label, instance.compile_args
            )
        elif instance.language == 'rust':
            target.get_attribute_node(ConvertAttr.RUSTFLAGS).add_conditional_values(
                label, instance.compile_args
            )

        if instance.link_args:
            target.get_attribute_node(ConvertAttr.LDFLAGS).add_conditional_values(
                label, instance.link_args
            )

    def add_include_dir_config(self, target: ConvertIncludeDirectory,
                               instance: ConvertInstanceIncludeDirectory,
                               platform: PrecomputedPlatformInfo,
                               custom_instances: T.Set[SelectInstance]) -> None:  # fmt: skip
        label = self.get_label(platform, custom_instances)
        target.single_attributes[ConvertAttr.SOONG_VENDOR] = 'true'
        if platform.is_native():
            target.single_attributes[ConvertAttr.SOONG_HOST_SUPPORTED] = 'true'

        target.get_attribute_node(ConvertAttr.INCLUDES).add_conditional_values(
            label, list(instance.paths)
        )

    def add_file_group_config(self, target: ConvertFileGroup, instance: ConvertInstanceFileGroup,
                              platform: PrecomputedPlatformInfo,
                              custom_instances: T.Set[SelectInstance]) -> None:  # fmt: skip
        # Soong doesn't support OS mutators on filegroups
        label = custom_instances
        target.get_attribute_node(ConvertAttr.SRCS).add_conditional_values(
            label, list(instance.srcs)
        )

    def _get_custom_target_cmd(self,
                               convert_instance_cmds: T.List[ConvertCustomTargetCmdPart],
                               ct: ConvertInstanceCustomTarget) -> str:  # fmt: skip
        final_cmd = []
        soong_srcs = _get_soong_sources(ct.command_list_srcs)
        substitution_inputs = [f'$(location {i})' for i in soong_srcs]
        substitution_outputs = [o.output for o in ct.generated_outputs]

        for cmd in convert_instance_cmds:
            res = ''
            if cmd.cmd_type is ConvertCustomTargetCmdPartType.TOOL:
                res = f'$(location {cmd.src.name})'
            elif cmd.cmd_type is ConvertCustomTargetCmdPartType.PYTHON_BINARY:
                res = f'$(location {cmd.src.name})'
            if cmd.cmd_type is ConvertCustomTargetCmdPartType.INPUT:
                res = substitute_inputs_into_string(cmd.cmd, substitution_inputs[: cmd.idx + 1])
            elif cmd.cmd_type is ConvertCustomTargetCmdPartType.INPUT_INDEX:
                res = substitute_indexed_inputs_into_string(cmd.cmd, substitution_inputs)
            elif cmd.cmd_type is ConvertCustomTargetCmdPartType.OUTPUT:
                res = substitute_outputs_into_string(cmd.cmd, substitution_outputs)
            elif cmd.cmd_type is ConvertCustomTargetCmdPartType.OUTPUT_INDEX:
                res = substitute_indexed_outputs_into_string(cmd.cmd, substitution_outputs)
            elif cmd.cmd_type is ConvertCustomTargetCmdPartType.STRING:
                res = cmd.cmd.replace('@@GEN_DIR@@', '$(genDir)')
            elif cmd.cmd_type is ConvertCustomTargetCmdPartType.M4_WORKAROUND:
                res = 'M4=$(location m4)'
            elif cmd.cmd_type is ConvertCustomTargetCmdPartType.COPY_SRCS:
                soong_src = _get_soong_sources([cmd.src])[0]
                target_subdir = cmd.src.subdir
                res = f'cp $(locations {soong_src}) $(genDir)/{target_subdir} &&'
            elif cmd.cmd_type is ConvertCustomTargetCmdPartType.MKDIR:
                res = f'mkdir -p $(genDir)/{cmd.cmd} &&'

            if res.strip():
                final_cmd.append(res.strip())

        return ' '.join(final_cmd)

    def add_custom_target(self, state_tracker: ConvertStateTracker,
                          instance: ConvertInstanceCustomTarget) -> None:  # fmt: skip
        modified_targets: T.List[ConvertInstanceCustomTarget] = []
        if instance.get_outputs_by_type(
            GeneratedFilesType.HEADERS
        ) and instance.get_outputs_by_type(GeneratedFilesType.IMPL):
            # Soong can't generate headers and implementation files at the same time, so
            # two separate genrules are required
            modified_targets.append(_custom_target_convert(instance, GeneratedFilesType.HEADERS))
            modified_targets.append(_custom_target_convert(instance, GeneratedFilesType.IMPL))
            self.converted_custom_targets[instance.name] = (
                modified_targets[0].name,
                modified_targets[1].name,
            )
        else:
            modified_targets.append(
                _custom_target_convert(instance, GeneratedFilesType.HEADERS_AND_IMPL)
            )

        for ct in modified_targets:
            if ct.name not in state_tracker.targets:
                state_tracker.targets[ct.name] = ConvertCustomTarget(ct.name, ct.subdir, instance)

            target = T.cast(ConvertCustomTarget, state_tracker.targets[ct.name])
            if target.instance != instance:
                state_tracker.targets.pop(ct.name)
                mlog.warning('Dropped custom target that differed across configs')
                return

            out = instance.get_outputs_by_type(ct.custom_target_type)
            target.get_attribute_node(ConvertAttr.OUT).add_common_values(out)
            target.get_attribute_node(ConvertAttr.SRCS).add_common_values(
                _get_soong_sources(ct.command_list_srcs + ct.depend_srcs)
            )

            tool_targets: T.List[str] = []
            for tool in ct.tools:
                tool_targets.append(tool.name)

            target.get_attribute_node(ConvertAttr.TOOLS).add_common_values(tool_targets)
            target.get_attribute_node(ConvertAttr.INCLUDES).add_common_values(
                ct.export_include_dirs
            )
            target.cmd = self._get_custom_target_cmd(ct.convert_instance_cmds, ct)

    def add_build_target_config(self, target: ConvertBuildTarget,
                                instance: T.Union[ConvertInstanceStaticLibrary, ConvertInstanceSharedLibrary],
                                platform: PrecomputedPlatformInfo,
                                custom_instances: T.Set[SelectInstance]) -> None:  # fmt: skip
        label = self.get_label(platform, custom_instances)
        target.install |= instance.install
        header_libs = list(instance.generated_include_dirs.keys()) + _get_soong_targets(
            instance.header_libs
        )

        target.single_attributes[ConvertAttr.SOONG_VENDOR] = 'true'
        if platform.is_native():
            target.single_attributes[ConvertAttr.SOONG_HOST_SUPPORTED] = 'true'

        target.get_attribute_node(ConvertAttr.SOONG_DEFAULTS).add_common_values(
            list(instance.generated_flags)
        )

        if target.rust_abi is RustABI.NONE:
            if instance.c_std:
                target.single_attributes[ConvertAttr.SOONG_C_STD] = f'"{instance.c_std}"'
            if instance.cpp_std:
                target.single_attributes[ConvertAttr.SOONG_CPP_STD] = f'"{instance.cpp_std}"'
            target.get_attribute_node(ConvertAttr.SOONG_HEADER_LIBS).add_conditional_values(
                label, header_libs
            )

            modified_gen_headers: T.List[str] = []
            modified_gen_sources: T.List[ConvertId] = []
            for header in instance.generated_headers:
                if header.name in self.converted_custom_targets:
                    modified_gen_headers.append(self.converted_custom_targets[header.name][0])
                else:
                    modified_gen_headers.append(header.name)

            for source in instance.generated_sources:
                if source.name in self.converted_custom_targets:
                    modified_gen_sources.append(
                        ConvertId(self.converted_custom_targets[source.name][1], '')
                    )
                else:
                    modified_gen_sources.append(ConvertId(source.name, source.subdir))

            target.get_attribute_node(ConvertAttr.SOONG_GENERATED_HEADERS).add_common_values(
                modified_gen_headers
            )
            target.get_attribute_node(ConvertAttr.SRCS).add_conditional_values(
                label, _get_soong_sources(instance.srcs + modified_gen_sources)
            )
            target.get_attribute_node(ConvertAttr.SOONG_STATIC_LIBRARIES).add_conditional_values(
                label, _get_soong_targets(instance.static_libs)
            )
            target.get_attribute_node(ConvertAttr.SOONG_SHARED_LIBRARIES).add_conditional_values(
                label, _get_soong_targets(instance.shared_libs)
            )
            target.get_attribute_node(
                ConvertAttr.SOONG_WHOLE_STATIC_LIBRARIES
            ).add_conditional_values(label, _get_soong_targets(instance.whole_static_libs))
        else:
            if instance.rust_edition:
                target.single_attributes[ConvertAttr.RUST_EDITION] = f'"{instance.rust_edition}"'
            target.single_attributes[ConvertAttr.RUST_CRATE_ROOT] = f'"{instance.crate_root}"'
            target.single_attributes[ConvertAttr.RUST_CRATE_NAME] = f'"{instance.crate_name}"'
            target.get_attribute_node(ConvertAttr.SOONG_RUST_LIBS).add_common_values(
                _get_soong_targets(instance.static_libs)
            )
            target.get_attribute_node(ConvertAttr.RUST_PROC_MACROS).add_common_values(
                _get_soong_targets(instance.proc_macros)
            )
