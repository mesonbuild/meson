#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T
from pathlib import Path

from mesonbuild import mlog
from mesonbuild.mesonlib import MachineChoice
from mesonbuild.hermetic.hermetic_platform import HermeticPlatformInstance

from mesonbuild.convert.common_defs import SelectInstance, SelectId, SelectKind, GeneratedFilesType

from mesonbuild.convert.instance.convert_instance_utils import (
    ConvertId,
    ConvertInstanceFlag,
    ConvertInstanceIncludeDirectory,
    ConvertInstanceFileGroup,
    ConvertInstancePythonBinary,
    ConvertInstanceRustBindgen,
)

from mesonbuild.convert.build_systems.common import (
    ConvertBackend,
    ConvertTreeNode,
    ConvertStateTracker,
)
from mesonbuild.convert.build_systems.target import (
    ConvertAttr,
    ConvertFileGroup,
    ConvertIncludeDirectory,
    ConvertPythonBinary,
    ConvertFlag,
    ConvertBuildTarget,
    ConvertStaticLibrary,
    ConvertSharedLibrary,
    ConvertTarget,
    ConvertCustomTarget,
    ConvertRustBindgen,
)
from mesonbuild.convert.instance.convert_instance_build_target import ConvertInstanceBuildTargetType
from mesonbuild.convert.instance.convert_instance_custom_target import (
    ConvertInstanceCustomTarget,
    ConvertCustomTargetCmdPart,
    ConvertCustomTargetCmdPartType,
)
from mesonbuild.convert.build_systems.utils import (
    substitute_inputs_into_string,
    substitute_indexed_inputs_into_string,
    substitute_outputs_into_string,
    substitute_indexed_outputs_into_string,
)

GLOB_HEADERS: str = """glob(["**/*.h", "**/*.hpp", "**/*.inl", "**/*.inc"], allow_empty = True)"""


class BazelBackend(ConvertBackend):
    """Bazel backend for build system conversion."""

    def __init__(self) -> None:
        self.converted_custom_targets: T.Dict[str, T.Tuple[str, str]] = {}
        self.external_deps: T.Set[ConvertId] = set()

    def get_os_info(self, platform: HermeticPlatformInstance,
                    choice: MachineChoice) -> SelectInstance:  # fmt: skip
        machine_info = platform.machine_info[choice]
        os_string = machine_info.system
        os_select = SelectInstance(SelectId(SelectKind.OS, '', 'os'), os_string)
        return os_select

    def get_arch_info(self, platform: HermeticPlatformInstance,
                      choice: MachineChoice) -> SelectInstance:  # fmt: skip
        machine_info = platform.machine_info[choice]
        select_id = SelectId(SelectKind.ARCH, '', 'arch')
        arch_select = SelectInstance(select_id, machine_info.cpu_family)
        return arch_select

    def add_python_binary_config(self, target: ConvertPythonBinary,
                                 instance: ConvertInstancePythonBinary) -> None:  # fmt: skip
        id_ = ConvertId.from_local_name(instance.main)
        bazel_main = self._get_bazel_sources([id_])[0]
        target.single_attributes[ConvertAttr.PYTHON_MAIN] = f'"{bazel_main}"'
        target.get_attribute_node(ConvertAttr.SRCS).add_common_values(
            self._get_bazel_sources(list(instance.srcs))
        )
        target.get_attribute_node(ConvertAttr.BAZEL_DEPS).add_common_values(
            self._get_bazel_targets(list(instance.libs))
        )

    def add_flag_config(self, target: ConvertFlag, instance: ConvertInstanceFlag,
                        platform: HermeticPlatformInstance,
                        custom_instances: T.Set[SelectInstance]) -> None:  # fmt: skip
        os_select = self.get_os_info(platform, MachineChoice.HOST)
        arch_select = self.get_arch_info(platform, MachineChoice.HOST)
        label = {arch_select, os_select} | custom_instances

        target.get_attribute_node(ConvertAttr.BAZEL_FLAGS).add_conditional_values(
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
        os_select = self.get_os_info(platform, MachineChoice.HOST)
        arch_select = self.get_arch_info(platform, MachineChoice.HOST)
        label = {arch_select, os_select} | custom_instances

        target.get_attribute_node(ConvertAttr.INCLUDES).add_conditional_values(
            label, list(instance.paths)
        )

        target.single_attributes[ConvertAttr.BAZEL_HDRS] = GLOB_HEADERS

    def add_file_group_config(self, target: ConvertFileGroup, instance: ConvertInstanceFileGroup,
                              platform: HermeticPlatformInstance,
                              custom_instances: T.Set[SelectInstance]) -> None:  # fmt: skip
        label = self.get_label(platform, custom_instances)
        target.get_attribute_node(ConvertAttr.SRCS).add_conditional_values(
            label, list(instance.srcs)
        )

    def _get_custom_target_cmd(self, convert_instance_cmds: T.List[ConvertCustomTargetCmdPart],
                               ct: ConvertInstanceCustomTarget) -> str:  # fmt: skip
        final_cmd = []
        bazel_srcs = self._get_bazel_sources(ct.command_list_srcs)
        substitution_inputs = [f'$(location {i})' for i in bazel_srcs]
        substitution_outputs = [
            f'$(location {Path(o).name})'
            for o in ct.get_outputs_by_type(GeneratedFilesType.HEADERS_AND_IMPL)
        ]

        for cmd in convert_instance_cmds:
            res = ''
            if cmd.cmd_type is ConvertCustomTargetCmdPartType.TOOL:
                bazel_src = self._get_bazel_sources([cmd.src])[0]
                res = f'$(location {bazel_src})'
            elif cmd.cmd_type is ConvertCustomTargetCmdPartType.PYTHON_BINARY:
                bazel_src = self._get_bazel_sources([cmd.src])[0]
                res = f'$(location {bazel_src})'
            elif cmd.cmd_type is ConvertCustomTargetCmdPartType.INPUT:
                res = substitute_inputs_into_string(cmd.cmd, substitution_inputs[: cmd.idx + 1])
            elif cmd.cmd_type is ConvertCustomTargetCmdPartType.INPUT_INDEX:
                res = substitute_indexed_inputs_into_string(cmd.cmd, substitution_inputs)
            elif cmd.cmd_type is ConvertCustomTargetCmdPartType.OUTPUT:
                res = substitute_outputs_into_string(cmd.cmd, substitution_outputs)
            elif cmd.cmd_type is ConvertCustomTargetCmdPartType.OUTPUT_INDEX:
                res = substitute_indexed_outputs_into_string(cmd.cmd, substitution_outputs)
            elif cmd.cmd_type is ConvertCustomTargetCmdPartType.STRING:
                res = cmd.cmd.replace('@@GEN_DIR@@', '$(GENDIR)')
            elif cmd.cmd_type is ConvertCustomTargetCmdPartType.M4_WORKAROUND:
                res = 'M4=$(location m4)'
            elif cmd.cmd_type is ConvertCustomTargetCmdPartType.COPY_SRCS:
                bazel_src = self._get_bazel_sources([cmd.src])[0]
                target_subdir = cmd.src.subdir
                res = f'cp $(location {bazel_src}) $(GENDIR)/{target_subdir} &&'
            elif cmd.cmd_type is ConvertCustomTargetCmdPartType.MKDIR:
                res = f'mkdir -p $(GENDIR)/{cmd.cmd} &&'

            if res.strip():
                final_cmd.append(res.strip())

        return ' '.join(final_cmd)

    def add_custom_target(self, state_tracker: ConvertStateTracker,
                          ct: ConvertInstanceCustomTarget) -> None:  # fmt: skip
        if ct.name not in state_tracker.targets:
            state_tracker.targets[ct.name] = ConvertCustomTarget(ct.name, ct.subdir, ct)

        target = T.cast(ConvertCustomTarget, state_tracker.targets[ct.name])
        if target.instance != ct:
            state_tracker.targets.pop(ct.name)
            mlog.warning('Dropped custom target that differed across configs')
            return

        # Bazel outputs must be relative to the package directory.
        # Mostly happens with export_include_dirs workaround
        out = []
        for o in ct.get_outputs_by_type(GeneratedFilesType.HEADERS_AND_IMPL):
            out.append(Path(o).name)

        target.get_attribute_node(ConvertAttr.OUT).add_common_values(out)
        target.get_attribute_node(ConvertAttr.SRCS).add_common_values(
            self._get_bazel_sources(ct.command_list_srcs + ct.depend_srcs)
        )
        target.get_attribute_node(ConvertAttr.TOOLS).add_common_values(
            self._get_bazel_sources(ct.tools)
        )
        target.get_attribute_node(ConvertAttr.INCLUDES).add_common_values(ct.export_include_dirs)
        target.cmd = self._get_custom_target_cmd(ct.convert_instance_cmds, ct)

    def add_rust_bindgen(self, target: ConvertRustBindgen,
                         instance: ConvertInstanceRustBindgen) -> None:  # fmt: skip
        pass

    def add_build_target_config(self, target: ConvertBuildTarget,
                                instance: ConvertInstanceBuildTargetType,
                                platform: HermeticPlatformInstance,
                                custom_instances: T.Set[SelectInstance]) -> None:  # fmt: skip
        os_select = self.get_os_info(platform, instance.machine_choice)
        arch_select = self.get_arch_info(platform, instance.machine_choice)
        label = {arch_select, os_select} | custom_instances

        bazel_generated_flags: T.List[ConvertId] = []
        for generated_flag in instance.generated_flags.values():
            bazel_generated_flags.append(ConvertId(generated_flag.name, generated_flag.subdir))

        bazel_generated_includes: T.List[ConvertId] = []
        for generated_dir in instance.generated_include_dirs.values():
            bazel_generated_includes.append(ConvertId(generated_dir.name, generated_dir.subdir))

        all_deps = (
            self._get_bazel_targets(bazel_generated_flags)
            + self._get_bazel_targets(bazel_generated_includes)
            + self._get_bazel_targets(instance.header_libs)
            + self._get_bazel_targets(instance.rust_libs)
            + self._get_bazel_targets(instance.static_libs)
            + self._get_bazel_targets(instance.shared_libs)
            + self._get_bazel_targets(instance.whole_static_libs)
            + self._get_bazel_targets(instance.generated_sources)
            + self._get_bazel_targets(instance.generated_headers)
        )

        bazel_srcs = self._get_bazel_sources(instance.srcs)
        if instance.crate_root:
            bazel_srcs.append(instance.crate_root)

        target.get_attribute_node(ConvertAttr.SRCS).add_conditional_values(label, bazel_srcs)
        target.get_attribute_node(ConvertAttr.BAZEL_DEPS).add_conditional_values(label, all_deps)

    def _process_include_dependencies(self, state_tracker: ConvertStateTracker,
                                      node: ConvertTreeNode,
                                      label: T.Set[SelectInstance]) -> T.List[ConvertTarget]:  # fmt: skip
        """
        Recursively discovers and links include targets.  Returns a list of header providers
        for this node's subtree that are active in 'label'.

        This is needed for Bazel because it handles include_directories weirdly.  Say I have
        a directory structure like this:

            include/
                -- BUILD.bazel
                -- clang/
                     BUILD.bazel

        If the include/BUILD.bazel has:
              meson_include_directories(
                 name = "inc_include",
                 hdrs = glob[**/*.h],
                 include = ["."]
              )

        Build targets that depend on inc_include will not be able to access include/clang.  That's because
        the include/clang/BUILD.bazel 'blocks' visibility into the package.  This is quite annoying.

        We utilize tree structure to add dependencies on child packages.

              meson_include_directories(
                 name = "inc_include",
                 hdrs = glob[**/*.h],
                 include = ["."]
                 deps = [//include/clang:inc_clang]
              )

        The above works as expected.  The below code also considers "labels", since you only want to
        depend on child include dirs with the same label as the current.  It could be a bit of
        over-engineering here.
        """
        child_providers: T.List[ConvertTarget] = []
        for child_key in sorted(node.child_nodes.keys()):
            child_providers.extend(
                self._process_include_dependencies(
                    state_tracker, node.child_nodes[child_key], label
                )
            )

        # Identify or create local header providers
        local_providers = [t for t in node.targets if isinstance(t, ConvertIncludeDirectory)]

        if not local_providers and node.targets:
            abs_subdir = Path(state_tracker.project_dir) / node.subdir
            if abs_subdir.is_dir():
                has_headers = any(
                    f.suffix in {'.h', '.hpp'} for f in abs_subdir.iterdir() if f.is_file()
                )
                if has_headers:
                    name = 'inc_' + (node.subdir.replace('/', '_') or 'root')
                    name = state_tracker.project_config.sanitize_target_name(name)
                    inc = ConvertIncludeDirectory(name, node.subdir)
                    inc.single_attributes[ConvertAttr.BAZEL_HDRS] = GLOB_HEADERS
                    node.add_target(inc)
                    local_providers = [inc]

        # Ensure auto-generated providers are marked active for the current label
        for provider in local_providers:
            if provider.name.startswith('inc_'):
                provider.get_attribute_node(ConvertAttr.INCLUDES).add_conditional_values(
                    label, ['.']
                )

        # Establish links for this configuration
        # We only care about providers that are active for the current label
        # fmt: off
        active_local_providers: T.List[ConvertTarget] = [
            p for p in local_providers
            if p.is_active_for_label(ConvertAttr.INCLUDES, label)
        ]
        # fmt: on
        if active_local_providers:
            inc_labels = [
                f'//{p.subdir}:{p.name}' if p.subdir else f'//:{p.name}'
                for p in active_local_providers
            ]

            # All build targets in this node depend on its active header providers
            for t in node.targets:
                if isinstance(t, (ConvertStaticLibrary, ConvertSharedLibrary)):
                    t.get_attribute_node(ConvertAttr.BAZEL_DEPS).add_conditional_values(
                        label, inc_labels
                    )

            # Local header providers depend on child header providers (bubbling up)
            if child_providers:
                child_labels = [
                    f'//{p.subdir}:{p.name}' if p.subdir else f'//:{p.name}'
                    for p in child_providers
                ]
                for p in active_local_providers:
                    p.get_attribute_node(ConvertAttr.BAZEL_DEPS).add_conditional_values(
                        label, child_labels
                    )

            return active_local_providers

        # No active local provider, propagate children's providers to the parent
        return child_providers

    def finish_current_config(self, state_tracker: ConvertStateTracker) -> None:
        os_select = self.get_os_info(state_tracker.current_platform, MachineChoice.HOST)
        arch_select = self.get_arch_info(state_tracker.current_platform, MachineChoice.HOST)
        label = {arch_select, os_select} | state_tracker.current_custom_select_instances

        self._process_include_dependencies(state_tracker, state_tracker.targets.root, label)

    def _get_bazel_targets(self, convert_deps: T.List[ConvertId]) -> T.List[str]:
        bazel_targets: T.List[str] = []
        for dep in convert_deps:
            if dep.repo:
                if dep.subdir:
                    bazel_target = f'@{dep.repo}//{dep.subdir}:{dep.name}'
                else:
                    bazel_target = f'@{dep.repo}//:{dep.name}'
                if dep.source_url:
                    self.external_deps.add(dep)
            else:
                bazel_target = f'//{dep.subdir}:{dep.name}'

            bazel_targets.append(bazel_target)

        return bazel_targets

    def _get_bazel_sources(self, convert_srcs: T.List[ConvertId]) -> T.List[str]:  # fmt: skip
        bazel_srcs: T.List[str] = []
        for src in convert_srcs:
            if src.local:
                bazel_srcs.append(src.name)
            else:
                bazel_srcs.extend(self._get_bazel_targets([src]))

        return bazel_srcs
