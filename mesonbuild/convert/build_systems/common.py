#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T
from bisect import insort

from mesonbuild.mesonlib import MachineChoice
from mesonbuild.convert.common_defs import (
    SelectInstance,
)
from mesonbuild.convert.convert_project_config import (
    ConvertProjectConfig,
)
from mesonbuild.convert.instance.convert_instance_custom_target import (
    ConvertInstanceCustomTarget,
    ConvertInstancePythonTarget,
)

from mesonbuild.convert.instance.convert_instance_utils import (
    ConvertInstanceFlag,
    ConvertInstanceIncludeDirectory,
    ConvertInstanceFileGroup,
)
from mesonbuild.convert.abstract.abstract_toolchain import (
    AbstractToolchainInfo,
)
from mesonbuild.convert.instance.convert_instance_build_target import (
    ConvertInstanceStaticLibrary,
    ConvertInstanceSharedLibrary,
)

from mesonbuild.convert.build_systems.target import (
    ConvertTargetType,
    ConvertTarget,
    ConvertFileGroup,
    ConvertPythonTarget,
    ConvertFlag,
    ConvertIncludeDirectory,
    ConvertBuildTarget,
    ConvertStaticLibrary,
    ConvertSharedLibrary,
)


class ConvertBackend:
    """Interface for build system backends."""

    def get_os_info(
        self, toolchain: AbstractToolchainInfo, choice: MachineChoice
    ) -> SelectInstance:
        raise NotImplementedError

    def get_arch_info(
        self, toolchain: AbstractToolchainInfo, choice: MachineChoice
    ) -> SelectInstance:
        raise NotImplementedError

    def add_python_config(
        self, target: ConvertPythonTarget, instance: ConvertInstancePythonTarget
    ) -> None:
        raise NotImplementedError

    def add_flag_config(
        self,
        target: ConvertFlag,
        instance: ConvertInstanceFlag,
        toolchain: AbstractToolchainInfo,
        custom_instances: T.Set[SelectInstance],
    ) -> None:
        raise NotImplementedError

    def add_include_dir_config(
        self,
        target: ConvertIncludeDirectory,
        instance: ConvertInstanceIncludeDirectory,
        toolchain: AbstractToolchainInfo,
        custom_instances: T.Set[SelectInstance],
    ) -> None:
        raise NotImplementedError

    def add_file_group_config(
        self, target: ConvertFileGroup, instance: ConvertInstanceFileGroup
    ) -> None:
        raise NotImplementedError

    def add_custom_target(
        self, state_tracker: ConvertStateTracker, instance: ConvertInstanceCustomTarget
    ) -> None:
        raise NotImplementedError

    def add_build_target_config(
        self,
        target: ConvertBuildTarget,
        instance: T.Union[ConvertInstanceStaticLibrary, ConvertInstanceSharedLibrary],
        toolchain: AbstractToolchainInfo,
        custom_instances: T.Set[SelectInstance],
    ) -> None:
        raise NotImplementedError

    def finish_current_config(self, state_tracker: ConvertStateTracker) -> None:
        pass


class ConvertTreeNode:
    """A single node in an ConvertTree.  Contains subdir, targets, and children"""

    def __init__(self, subdir: str):
        self.subdir: str = subdir
        self.targets: T.List[ConvertTarget] = []
        self.target_types: T.Set[ConvertTargetType] = set()
        self.child_nodes: T.Dict[str, ConvertTreeNode] = {}

    @property
    def is_root(self) -> bool:
        return self.subdir == ""

    def find_target(self, target_name: str) -> T.Optional[ConvertTarget]:
        for target in self.targets:
            if target.name == target_name:
                return target
        for child in self.child_nodes.values():
            target = child.find_target(target_name)
            if target:
                return target
        return None

    def add_target(self, target: ConvertTarget) -> None:
        insort(self.targets, target)
        self.target_types.add(target.target_type)

    def walk(self) -> T.Iterable[ConvertTreeNode]:
        yield self
        for child in sorted(self.child_nodes.keys()):
            yield from self.child_nodes[child].walk()


class ConvertTree:
    """A tree structure where each level tracks the ConvertTargets.  There is a BUILD.bazel or
    Android.bp associated with each node of the tree.
    """

    def __init__(self) -> None:
        self.root = ConvertTreeNode("")
        self._targets_dict: T.Dict[str, ConvertTarget] = {}

    def __contains__(self, name: str) -> bool:
        return name in self._targets_dict

    def __getitem__(self, name: str) -> ConvertTarget:
        return self._targets_dict[name]

    def __setitem__(self, name: str, target: ConvertTarget) -> None:
        self._targets_dict[name] = target
        self._add_to_tree(target)

    def values(self) -> T.ValuesView[ConvertTarget]:
        return self._targets_dict.values()

    def _get_node(self, subdir: str) -> ConvertTreeNode:
        if not subdir:
            return self.root
        parts = subdir.split("/")
        current = self.root
        path_so_far = []
        for part in parts:
            path_so_far.append(part)
            if part not in current.child_nodes:
                current.child_nodes[part] = ConvertTreeNode("/".join(path_so_far))
            current = current.child_nodes[part]
        return current

    def _add_to_tree(self, target: ConvertTarget) -> None:
        node = self._get_node(target.subdir)
        node.add_target(target)

    def pop(self, name: str) -> ConvertTarget:
        target = self._targets_dict.pop(name)
        node = self._get_node(target.subdir)
        node.targets.remove(target)
        return target

    def walk(self) -> T.Iterable[ConvertTreeNode]:
        yield from self.root.walk()


class ConvertStateTracker:
    """Unified state tracker for all build systems."""

    def __init__(self, project_config: ConvertProjectConfig, backend: ConvertBackend):
        self.project_config = project_config
        self.current_toolchain: T.Optional[AbstractToolchainInfo] = None
        self.current_custom_select_instances: T.Optional[T.Set[SelectInstance]] = None
        self.all_toolchains: T.Set[AbstractToolchainInfo] = set()
        self.output_dir: str = ""
        self.project_dir: str = ""
        self.backend = backend
        self.targets = ConvertTree()

    def set_current_config(
        self,
        toolchain_info: AbstractToolchainInfo,
        custom_select_instances: T.Set[SelectInstance],
    ) -> None:
        self.current_toolchain = toolchain_info
        self.current_custom_select_instances = custom_select_instances
        self.all_toolchains.add(toolchain_info)

    def finish_current_config(self) -> None:
        self.backend.finish_current_config(self)

    def add_python_target(self, target: ConvertInstancePythonTarget) -> None:
        if target.name not in self.targets:
            self.targets[target.name] = ConvertPythonTarget(target.name, target.subdir)

        # Ensure all project-defined python libraries are added to the instance
        # before passing it to the backend. This ensures mako, etc. are available.
        python_libs = self.project_config.dependencies.python_libraries
        for lib in python_libs:
            if lib not in target.libs:
                target.libs.append(lib)

        self.backend.add_python_config(
            T.cast(ConvertPythonTarget, self.targets[target.name]), target
        )

    def add_flag(self, flag: ConvertInstanceFlag) -> None:
        if flag.name not in self.targets:
            self.targets[flag.name] = ConvertFlag(flag.name, flag.subdir, flag.language)

        self.backend.add_flag_config(
            T.cast(ConvertFlag, self.targets[flag.name]),
            flag,
            self.current_toolchain,
            self.current_custom_select_instances,
        )

    def add_include_directory(self, inc: ConvertInstanceIncludeDirectory) -> None:
        if inc.name not in self.targets:
            self.targets[inc.name] = ConvertIncludeDirectory(inc.name, inc.subdir)

        self.backend.add_include_dir_config(
            T.cast(ConvertIncludeDirectory, self.targets[inc.name]),
            inc,
            self.current_toolchain,
            self.current_custom_select_instances,
        )

    def add_file_group(self, grp: ConvertInstanceFileGroup) -> None:
        if grp.name not in self.targets:
            self.targets[grp.name] = ConvertFileGroup(grp.name, grp.subdir)
        self.backend.add_file_group_config(
            T.cast(ConvertFileGroup, self.targets[grp.name]), grp
        )

    def add_custom_target(self, custom_target: ConvertInstanceCustomTarget) -> None:
        self.backend.add_custom_target(self, custom_target)

    def add_static_library(self, lib: ConvertInstanceStaticLibrary) -> None:
        if lib.name not in self.targets:
            self.targets[lib.name] = ConvertStaticLibrary(
                lib.name, lib.subdir, lib.rust_abi
            )
        self.backend.add_build_target_config(
            T.cast(ConvertStaticLibrary, self.targets[lib.name]),
            lib,
            self.current_toolchain,
            self.current_custom_select_instances,
        )

    def add_shared_library(self, lib: ConvertInstanceSharedLibrary) -> None:
        if lib.name not in self.targets:
            self.targets[lib.name] = ConvertSharedLibrary(
                lib.name, lib.subdir, lib.rust_abi
            )
        self.backend.add_build_target_config(
            T.cast(ConvertSharedLibrary, self.targets[lib.name]),
            lib,
            self.current_toolchain,
            self.current_custom_select_instances,
        )

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
            all_os_selects.add(self.backend.get_os_info(toolchain, MachineChoice.HOST))
            all_arch_selects.add(
                self.backend.get_arch_info(toolchain, MachineChoice.HOST)
            )

        all_select_instances.append(all_os_selects)
        all_select_instances.append(all_arch_selects)

        for target in self.targets.values():
            target.finish(all_select_instances, all_custom_defaults)
