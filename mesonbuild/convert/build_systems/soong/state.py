#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T
import copy
import os

from mesonbuild import mlog
from mesonbuild.mesonlib import MachineChoice
from mesonbuild.hermetic.hermetic_platform import HermeticPlatformInstance
from mesonbuild.convert.convert_project_config import SoongPropertiesSection
from mesonbuild.convert.common_defs import (
    ConvertUnimplementedException,
    FlagScope,
    SelectInstance,
    SelectId,
    SelectKind,
    GeneratedFilesType,
)

from mesonbuild.convert.instance.convert_instance_rust_bindgen import ConvertInstanceRustBindgen
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
    ConvertTarget,
    ConvertTargetType,
    ConvertFileGroup,
    ConvertIncludeDirectory,
    ConvertPythonBinary,
    ConvertFlag,
    ConvertBuildTarget,
    ConvertCustomTarget,
    ConvertRustBindgen,
    SoongTargetBlock,
)

from mesonbuild.convert.instance.convert_instance_build_target import (
    ConvertInstanceBuildTargetType,
    ConvertInstanceExecutable,
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
    return [src.name if src.local else f':{src.name}' for src in convert_srcs]


def _get_soong_bindgen_wrapper(bindgen_id: ConvertId, wrapper_output: str) -> str:
    # Soong's rust_bindgen only generates a .c static-inline wrapper and exposes it via
    # the hardcoded ".c" output tag (build/soong/rust/bindgen.go).
    ext = os.path.splitext(wrapper_output)[1]
    if ext != '.c':
        raise ConvertUnimplementedException(
            f'Soong rust_bindgen static inline wrapper with extension {ext!r}'
        )
    return f':{bindgen_id.name}{{{ext}}}'


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


SOONG_APEX_TARGET_TYPES = frozenset(
    {
        ConvertTargetType.CC_CUSTOM_TARGET,
        ConvertTargetType.STATIC_LIBRARY,
        ConvertTargetType.SHARED_LIBRARY,
        ConvertTargetType.EXECUTABLE,
        ConvertTargetType.RUST_BINDGEN,
        ConvertTargetType.RUST_LIBRARY,
        ConvertTargetType.RUST_EXECUTABLE,
        ConvertTargetType.RUST_FFI_STATIC,
        ConvertTargetType.RUST_FFI_SHARED,
    }
)

SOONG_PARTITION_TARGET_TYPES = SOONG_APEX_TARGET_TYPES | frozenset(
    {ConvertTargetType.FLAG, ConvertTargetType.RUST_FLAG, ConvertTargetType.INCLUDE_DIRECTORY}
)

SOONG_PARTITION_ATTRS = {
    'vendor': ConvertAttr.SOONG_VENDOR,
    'vendor_available': ConvertAttr.SOONG_VENDOR_AVAILABLE,
}


def _is_android_32bit(platform: HermeticPlatformInstance) -> bool:
    host = platform.machine_info[MachineChoice.HOST]
    return host.system == 'android' and host.cpu_family in {'arm', 'x86'}


class SoongBackend(ConvertBackend):
    """Soong backend for build system conversion."""

    def __init__(self, soong_props: SoongPropertiesSection) -> None:
        self.converted_custom_targets: T.Dict[str, T.Tuple[str, str]] = {}
        self.rust_multilib_targets: T.Set[str] = set()
        self.bindgen_static_inline_libs: T.Dict[str, str] = {}
        self.soong_props = soong_props

    def _resolve_custom_target_header(self, header: ConvertId) -> str:
        if header.name in self.converted_custom_targets:
            return self.converted_custom_targets[header.name][0]
        return header.name

    def _resolve_custom_target_impl(self, source: ConvertId) -> ConvertId:
        if not source.local and source.name in self.converted_custom_targets:
            return ConvertId(self.converted_custom_targets[source.name][1], '')
        return source

    def get_os_info(self, platform: HermeticPlatformInstance,
                    choice: MachineChoice) -> SelectInstance:  # fmt: skip
        machine_info = platform.machine_info[choice]
        platform_str = platform.platforms[choice].name

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

    def get_arch_info(self, platform: HermeticPlatformInstance,
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
        if not instance.strict_deps:
            target.single_attributes[ConvertAttr.SOONG_STRICT_DEPS] = 'false'
        target.get_attribute_node(ConvertAttr.SRCS).add_common_values(
            _get_soong_sources(list(instance.srcs))
        )
        target.get_attribute_node(ConvertAttr.SOONG_PYTHON_LIBS).add_common_values(
            _get_soong_targets(list(instance.libs))
        )

    def add_flag_config(self, target: ConvertFlag, instance: ConvertInstanceFlag,
                        platform: HermeticPlatformInstance,
                        custom_instances: T.Set[SelectInstance]) -> None:  # fmt: skip
        label = self.get_label(platform, custom_instances)

        if instance.language == 'c':
            target.get_attribute_node(ConvertAttr.SOONG_CFLAGS).add_conditional_values(
                label, instance.compile_args
            )
        elif instance.language == 'cpp':
            target.get_attribute_node(ConvertAttr.SOONG_CPPFLAGS).add_conditional_values(
                label, instance.compile_args
            )
        elif instance.language == 'rust':
            target.get_attribute_node(ConvertAttr.SOONG_RUST_CFGS).add_conditional_values(
                label, instance.rust_cfgs
            )
            target.get_attribute_node(ConvertAttr.RUSTFLAGS).add_conditional_values(
                label, instance.compile_args
            )

        if instance.link_args:
            target.get_attribute_node(ConvertAttr.LDFLAGS).add_conditional_values(
                label, instance.link_args
            )

    def add_include_dir_config(self, target: ConvertIncludeDirectory,
                               instance: ConvertInstanceIncludeDirectory,
                               platform: HermeticPlatformInstance,
                               custom_instances: T.Set[SelectInstance]) -> None:  # fmt: skip
        label = self.get_label(platform, custom_instances)

        target.get_attribute_node(ConvertAttr.INCLUDES).add_conditional_values(
            label, list(instance.paths)
        )

    def add_file_group_config(self, target: ConvertFileGroup, instance: ConvertInstanceFileGroup,
                              platform: HermeticPlatformInstance,
                              custom_instances: T.Set[SelectInstance]) -> None:  # fmt: skip
        # Soong doesn't support arch + OS mutators on filegroups
        # Soong team seems open to adding it, but who has the time?
        label = custom_instances

        # As a consequence of the above issue, we can't effectively fix the case where
        # the subdirectories of a filegroup instance vary. This can be solved in various
        # ways. However, things work without it, so just note the issue.
        if instance.subdir != target.subdir:
            mlog.warning(f'Filegroup {target.name} differed across configs: dropping some files.')
            return

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

        for i, cmd in enumerate(convert_instance_cmds):
            res = ''
            if cmd.cmd_type is ConvertCustomTargetCmdPartType.TOOL and cmd.src:
                res = f'$(location {cmd.src.name})'
            elif cmd.cmd_type is ConvertCustomTargetCmdPartType.PYTHON_BINARY and cmd.src:
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
            elif cmd.cmd_type is ConvertCustomTargetCmdPartType.COPY_SRCS and cmd.src:
                soong_src = _get_soong_sources([cmd.src])[0]
                target_dest = cmd.cmd or cmd.src.subdir
                suffix = ' &&' if i < len(convert_instance_cmds) - 1 else ''
                res = f'cp $(locations {soong_src}) $(genDir)/{target_dest}{suffix}'
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
                state_tracker.targets[ct.name] = ConvertCustomTarget(
                    ct.name, ct.subdir, instance, arch_variant=ct.arch_variant
                )

            target = T.cast(ConvertCustomTarget, state_tracker.targets[ct.name])
            if target.instance != instance:
                state_tracker.targets.pop(ct.name)
                mlog.warning(f'Dropped custom target {ct.name} that differed across configs')
                return

            platform, _ = state_tracker.get_current_config()
            target.platforms.add(platform)

            ct.command_list_srcs = [
                self._resolve_custom_target_impl(s) for s in ct.command_list_srcs
            ]

            out = instance.get_outputs_by_type(ct.custom_target_type)
            target.get_attribute_node(ConvertAttr.OUT).add_common_values(out)
            target.get_attribute_node(ConvertAttr.SRCS).add_common_values(
                _get_soong_sources(ct.command_list_srcs + ct.depend_srcs)
            )

            tool_targets: T.List[str] = [tool.name for tool in ct.tools]

            target.get_attribute_node(ConvertAttr.TOOLS).add_common_values(tool_targets)
            target.get_attribute_node(ConvertAttr.INCLUDES).add_common_values(
                ct.export_include_dirs
            )
            target.cmd = self._get_custom_target_cmd(ct.convert_instance_cmds, ct)

    def add_rust_bindgen(self, state_tracker: ConvertStateTracker,
                         instance: ConvertInstanceRustBindgen) -> None:  # fmt: skip
        if instance.target_name not in state_tracker.targets:
            state_tracker.targets[instance.target_name] = ConvertRustBindgen(
                instance.target_name, instance.subdir
            )

        target = T.cast(ConvertRustBindgen, state_tracker.targets[instance.target_name])
        platform, custom_instances = state_tracker.get_current_config()
        label = self.get_label(platform, custom_instances)

        target.single_attributes[ConvertAttr.RUST_CRATE_NAME] = f'"{instance.crate_name}"'
        if instance.rust_edition:
            target.single_attributes[ConvertAttr.RUST_EDITION] = f'"{instance.rust_edition}"'
        if instance.c_std:
            target.single_attributes[ConvertAttr.SOONG_C_STD] = f'"{instance.c_std}"'

        wrapper_source = _get_soong_sources([instance.header])[0]
        stem = os.path.splitext(os.path.basename(instance.output))[0]
        target.single_attributes[ConvertAttr.SOONG_WRAPPER_SRC] = f'"{wrapper_source}"'
        target.single_attributes[ConvertAttr.SOONG_SOURCE_STEM] = f'"{stem}"'
        # Reserve defaults slot before other attributes; populated in finish().
        target.get_attribute_node(ConvertAttr.SOONG_DEFAULTS, no_sort=True)
        header_libs = list(instance.include_dirs)
        resolved_gen_headers = [
            self._resolve_custom_target_header(h)
            for h in instance.generated_headers
            if h.name in state_tracker.targets or h.name in self.converted_custom_targets
        ]
        if resolved_gen_headers:
            # Soong's rust_bindgen does not support generated_headers directly; wrap them
            # in an ancillary cc_library_headers module.
            gen_inc_name = f'{instance.target_name}_generated_headers'
            if gen_inc_name not in state_tracker.targets:
                state_tracker.targets[gen_inc_name] = ConvertIncludeDirectory(
                    gen_inc_name, instance.subdir
                )
            gen_inc_target = T.cast(ConvertIncludeDirectory, state_tracker.targets[gen_inc_name])
            gen_inc_target.platforms.add(platform)
            gen_inc_target.get_attribute_node(
                ConvertAttr.SOONG_GENERATED_HEADERS
            ).add_common_values(resolved_gen_headers)
            gen_inc_target.get_attribute_node(
                ConvertAttr.SOONG_EXPORT_GENERATED_HEADERS
            ).add_common_values(resolved_gen_headers)
            header_libs.append(gen_inc_name)

        if header_libs:
            target.get_attribute_node(ConvertAttr.SOONG_HEADER_LIBS).add_conditional_values(
                label, header_libs
            )
        # Bindgen flags are sensitive to ordering and duplicates (e.g. repeated --allowlist-var).
        target.get_attribute_node(ConvertAttr.SOONG_BINDGEN_FLAGS, no_sort=True).add_common_values(
            instance.args
        )
        if instance.c_args:
            target.get_attribute_node(ConvertAttr.SOONG_CFLAGS).add_conditional_values(
                label, instance.c_args
            )
        if instance.rust_libs:
            target.get_attribute_node(ConvertAttr.SOONG_RUST_LIBS).add_conditional_values(
                label, _get_soong_targets(instance.rust_libs)
            )

    def add_build_target_config(self, target: ConvertBuildTarget,
                                instance: ConvertInstanceBuildTargetType,
                                platform: HermeticPlatformInstance,
                                custom_instances: T.Set[SelectInstance]) -> None:  # fmt: skip
        label = self.get_label(platform, custom_instances)
        if instance.install:
            target.soong_target_block |= SoongTargetBlock.ANDROID_INSTALL
        header_libs = list(instance.generated_include_dirs.keys()) + _get_soong_targets(
            instance.header_libs
        )

        # Reserve defaults slot before other attributes; populated in finish().
        target.get_attribute_node(ConvertAttr.SOONG_DEFAULTS, no_sort=True)

        structured_srcs: T.List[str] = []
        if instance.structured_sources:
            gen_name = instance.structured_sources.name
            structured_srcs = [
                f':{gen_name}{{{o.output}}}' for o in instance.structured_sources.generated_outputs
            ]

        if target.rust_abi is RustABI.NONE:
            if instance.c_std:
                target.single_attributes[ConvertAttr.SOONG_C_STD] = f'"{instance.c_std}"'
            if instance.cpp_std:
                target.single_attributes[ConvertAttr.SOONG_CPP_STD] = f'"{instance.cpp_std}"'
            target.get_attribute_node(ConvertAttr.SOONG_HEADER_LIBS).add_conditional_values(
                label, header_libs
            )

            modified_gen_headers = [
                self._resolve_custom_target_header(h) for h in instance.generated_headers
            ]
            modified_gen_sources = [
                self._resolve_custom_target_impl(s) for s in instance.generated_sources
            ]
            bindgen_srcs: T.List[str] = []
            for bindgen_id, wrapper_output in instance.bindgen_inline_wrappers:
                self.bindgen_static_inline_libs[bindgen_id.name] = target.name
                bindgen_srcs.append(_get_soong_bindgen_wrapper(bindgen_id, wrapper_output))

            # HACK: For executables, Soong complains about missing main functions if we have a
            # structure like this:
            #
            # srcs: select((os(), soong_config_variable("", "my_var")), {
            #     ("android", "true"): [
            #        "datasource.cc",
            #        "producer.cc",
            #     ],
            #     (default, default): [],
            # }),
            #
            # To get properly deal with this, we need to conditional single attributes too:
            #
            # enabled: select((os(), soong_config_variable("", "my_var")), {
            #     ("android", "true"): "true"
            #     (default, default): false,
            # }),
            #
            # Workaround this just by disabling on native binaries for now.
            if isinstance(instance, ConvertInstanceExecutable):
                target.single_attributes[ConvertAttr.SOONG_ENABLED] = 'false'

            target.get_attribute_node(ConvertAttr.SOONG_GENERATED_HEADERS).add_common_values(
                modified_gen_headers
            )
            target.get_attribute_node(ConvertAttr.SRCS).add_conditional_values(
                label,
                _get_soong_sources(instance.srcs + modified_gen_sources)
                + bindgen_srcs
                + structured_srcs,
            )
            target.get_attribute_node(
                ConvertAttr.SOONG_EXTRA_INCLUDE_DIR_DEPS
            ).add_conditional_values(label, _get_soong_sources(instance.extra_include_dir_deps))
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
            if (
                instance.static_libs
                or instance.shared_libs
                or instance.whole_static_libs
                or (instance.structured_sources and instance.structured_sources.arch_variant)
            ):
                self.rust_multilib_targets.add(target.name)

            if instance.rust_edition:
                target.single_attributes[ConvertAttr.RUST_EDITION] = f'"{instance.rust_edition}"'

            crate_root: T.Optional[str] = None
            if instance.crate_root:
                crate_root = _get_soong_sources([instance.crate_root])[0]
            elif instance.structured_sources:
                structured_root = instance.structured_crate_root()
                if structured_root:
                    crate_root = f':{instance.structured_sources.name}{{{structured_root}}}'

            if crate_root:
                target.single_attributes[ConvertAttr.RUST_CRATE_ROOT] = f'"{crate_root}"'

            rust_srcs = _get_soong_sources(instance.generated_sources) + structured_srcs
            if rust_srcs:
                target.get_attribute_node(ConvertAttr.SRCS).add_conditional_values(label, rust_srcs)

            target.single_attributes[ConvertAttr.RUST_CRATE_NAME] = f'"{instance.crate_name}"'
            target.get_attribute_node(ConvertAttr.SOONG_RUST_LIBS).add_conditional_values(
                label, _get_soong_targets(instance.rust_libs)
            )
            target.get_attribute_node(ConvertAttr.SOONG_STATIC_LIBRARIES).add_conditional_values(
                label, _get_soong_targets(instance.static_libs)
            )
            target.get_attribute_node(ConvertAttr.SOONG_SHARED_LIBRARIES).add_conditional_values(
                label, _get_soong_targets(instance.shared_libs)
            )
            target.get_attribute_node(ConvertAttr.RUST_PROC_MACROS).add_common_values(
                _get_soong_targets(instance.proc_macros)
            )

    def _apply_soong_props(self, target: ConvertTarget) -> None:
        if target.target_type not in SOONG_PARTITION_TARGET_TYPES:
            return

        attrs = target.single_attributes
        partition_attr = SOONG_PARTITION_ATTRS.get(self.soong_props.get('partition_type', 'vendor'))
        if partition_attr is not None:
            attrs[partition_attr] = 'true'

        apex_available = self.soong_props.get('apex_available', '')
        if apex_available and target.target_type in SOONG_APEX_TARGET_TYPES:
            attrs[ConvertAttr.SOONG_APEX_AVAILABLE] = f'["{apex_available}"]'

        if any(p.is_native() for p in target.platforms):
            attrs[ConvertAttr.SOONG_HOST_SUPPORTED] = 'true'

    def _apply_multilib_block(self, target: ConvertTarget) -> None:
        has_native = any(p.is_native() for p in target.platforms)
        needs_rust_multilib = (
            target.target_type is ConvertTargetType.CC_CUSTOM_TARGET
            or target.name in self.rust_multilib_targets
        )
        if needs_rust_multilib:
            block = SoongTargetBlock.ANDROID_MULTILIB
            if has_native:
                block |= SoongTargetBlock.HOST_MULTILIB
            if any(_is_android_32bit(p) for p in target.platforms):
                block |= SoongTargetBlock.ANDROID_32_BIT
            target.soong_target_block |= block
            return

        is_project_c_flag = (
            isinstance(target, ConvertFlag)
            and target.scope is FlagScope.PROJECT
            and target.language in {'c', 'cpp'}
        )
        if is_project_c_flag and has_native:
            target.soong_target_block |= SoongTargetBlock.HOST_MULTILIB

    def finish(self, state_tracker: ConvertStateTracker) -> None:
        for target in state_tracker.targets.values():
            self._apply_soong_props(target)
            self._apply_multilib_block(target)
            if target.flags:
                # Soong prepends each defaults module in order, so emit highest-precedence
                # scopes first (TARGET, SHARED, PROJECT) so target flags appear last on the
                # compiler command line.
                ordered_flags = sorted(target.flags.values(), key=lambda f: (f.scope, f.name))
                target.get_attribute_node(
                    ConvertAttr.SOONG_DEFAULTS, no_sort=True
                ).add_common_values([f.name for f in ordered_flags])

        for bindgen_name, static_lib in self.bindgen_static_inline_libs.items():
            if bindgen_name not in state_tracker.targets:
                continue
            bindgen_target = state_tracker.targets[bindgen_name]
            if not isinstance(bindgen_target, ConvertRustBindgen):
                continue
            bindgen_target.single_attributes[ConvertAttr.SOONG_HANDLE_STATIC_INLINE] = 'true'
            bindgen_target.single_attributes[ConvertAttr.SOONG_STATIC_INLINE_LIBRARY] = (
                f'"{static_lib}"'
            )
