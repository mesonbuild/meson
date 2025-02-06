#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

from mesonbuild.convert.common_defs import (
    SelectInstance,
    SelectId,
    SelectKind,
)
from mesonbuild.convert.convert_project_config import (
    ConvertProjectConfig, )
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
    AbstractToolchainInfo, )
from mesonbuild.convert.instance.convert_instance_build_target import (
    ConvertInstanceStaticLibrary,
    ConvertInstanceSharedLibrary,
)

COMMON_INDENT = 4
COMMON_MAX_LINE_LENGTH = 70


class ConvertAttr(Enum):
    # Common attributes (1-100)
    NAME = 1
    SRCS = 2
    INCLUDES = 3
    LDFLAGS = 4  # LinkOpts in Bazel
    PYTHON_MAIN = 5
    RUST_CRATE_NAME = 6
    RUST_CRATE_ROOT = 7
    RUST_EDITION = 8
    RUST_PROC_MACROS = 9
    RUSTFLAGS = 10
    TOOLS = 11
    OUT = 12
    # Soong-specific attributes (101-200)
    SOONG_VENDOR = 101
    SOONG_HOST_SUPPORTED = 102
    SOONG_DEFAULTS = 103
    SOONG_GENERATED_HEADERS = 104
    SOONG_GENERATED_SOURCES = 105
    SOONG_HEADER_LIBS = 106
    SOONG_STATIC_LIBRARIES = 108
    SOONG_SHARED_LIBRARIES = 109
    SOONG_WHOLE_STATIC_LIBRARIES = 110
    SOONG_CFLAGS = 111
    SOONG_CPPFLAGS = 112
    SOONG_C_STD = 113
    SOONG_CPP_STD = 114
    SOONG_RUST_LIBS = 115
    SOONG_LINKER_VERSION_SCRIPT = 116
    SOONG_PYTHON_LIBS = 117
    # Bazel-specific attributes (200-300)
    BAZEL_DEPS = 201
    BAZEL_DEFINES = 202


@dataclass
class SelectNode:
    select_ids: T.List[SelectId]
    select_tuples: T.List[T.Tuple[T.List[str], T.List[str]]]


class ConvertAttrNode:
    """Representation of target attributes.
    For example,
          inc = include_directories('common')
          srcs = files('common.c');
          if host_machine.system() == 'linux':
             inc += include_directories('linux')
             srcs += files('linux.c')
          elif host_machine.system == 'windows'
             inc += include_directories('windows')
             srcs += files('windows.c')
         If a build target uses both 'inc' and 'srcs', then it would
         have the 'inc'/'srcs' attributes.  These attributes would
         have a set of common values and conditional values.

         The conditionality is provided the toolchain-generated SelectInstances
         as well as the user-provided SelectInstances.
    """

    def __init__(self, attribute: ConvertAttr):
        self.attribute = attribute
        self.common_values: T.Set[str] = set()
        self.grouped_select_instances: T.Dict[str,
                                              T.List[T.Set[SelectInstance]]] = defaultdict(list)
        self.all_select_instances: T.Dict[str, T.Set[SelectInstance]] = defaultdict(set)
        self.common_custom_instances: T.Optional[T.Set[SelectInstance]] = None
        self.select_nodes: T.List[SelectNode] = []

    def add_common_values(self, values: T.List[str]) -> None:
        if not values:
            return

        self.common_values.update(values)

    def add_conditional_values(self, label: T.Set[SelectInstance], values: T.List[str]) -> None:
        for select_instance in label:
            if select_instance.select_id.select_kind == SelectKind.CUSTOM:
                if self.common_custom_instances is None:
                    self.common_custom_instances = {select_instance}
                else:
                    self.common_custom_instances &= {select_instance}

        if not values:
            return

        for value in values:
            self.grouped_select_instances[value].append(label)
            for select_instance in label:
                self.all_select_instances[value].add(select_instance)

    def consolidate_conditionals(
        self,
        select_instance_groups: T.List[T.Set[SelectInstance]],
        all_custom_defaults: T.Set[SelectInstance],
    ) -> None:
        """
        Simplifies and organizes conditional attribute values after all project
        configurations have been processed. This method iterates through each attribute
        value and its associated conditional labels (`SelectInstance` objects). It
        intelligently determines if a value is truly conditional or if it's common
        to all configurations by checking against groups of conditions (e.g., all
        possible OSes, all architectures).

        For example, if a source file 'linux.c' is present in configurations for
        `{os:linux, arch:x86_64}` and `{os:linux, arch:aarch64}`, and the project
        is only configured for these two architectures, this method will deduce
        that 'linux.c' is only conditional on the OS. The redundant architecture
        conditions are removed. The final simplified condition is then stored in
        a `SelectNode`. If a value is found to be present in all possible
        configurations (i.e., it has no remaining unique conditions), it's moved
        from being conditional to the `common_values` set. This process ensures
        that the final build file output is as clean and minimal as possible.
        """
        for value, labels_list in self.grouped_select_instances.items():
            processed_labels: T.List[T.Set[SelectInstance]] = []
            for label in labels_list:
                current_label = label.copy()
                # Remove any full group matches from the label
                for group in select_instance_groups:
                    if group.issubset(self.all_select_instances[value]):
                        current_label -= group

                # Remove common custom instances
                if self.common_custom_instances is not None:
                    for instance in self.common_custom_instances:
                        if instance in all_custom_defaults:
                            current_label -= {instance}

                if current_label:
                    processed_labels.append(current_label)

            if not processed_labels:
                self.common_values.add(value)
            else:
                self.grouped_select_instances[value] = processed_labels
                for new_label in processed_labels:
                    select_ids: T.List[SelectId] = []
                    for select_instance in new_label:
                        select_ids.append(select_instance.select_id)

                    select_ids.sort()
                    current_select_values = []
                    for select_id in select_ids:
                        for select_instance in new_label:
                            if select_id == select_instance.select_id:
                                current_select_values.append(select_instance.value)

                    found = False
                    for select_node in self.select_nodes:
                        if select_ids == select_node.select_ids:
                            for (
                                    existing_values,
                                    attribute_values,
                            ) in select_node.select_tuples:
                                if existing_values == current_select_values:
                                    if value not in attribute_values:
                                        attribute_values.append(value)
                                    found = True
                                    break
                            if not found:
                                select_node.select_tuples.append((current_select_values, [value]))
                                found = True
                            break

                    if not found:
                        self.select_nodes.append(
                            SelectNode(select_ids, [(current_select_values, [value])]))

    def get_select_nodes(self) -> T.List[SelectNode]:
        if not self.common_values and not self.select_nodes:
            return []

        for select_node in self.select_nodes:
            default_strings: T.List[str] = []
            for select_id in select_node.select_ids:
                default_strings.append('default')

            select_node.select_tuples.append((default_strings, []))

            for values, attribute_values in select_node.select_tuples:
                attribute_values.sort()

        return self.select_nodes

    def empty(self) -> bool:
        return bool(not self.common_values and not self.select_nodes)


class ConvertTarget:
    """Base class for all converted build targets"""

    def __init__(self, name: str, subdir: str):
        self.module_type: str = ''
        self.name = name
        self.subdir = subdir
        self.single_attributes: T.Dict[ConvertAttr, str] = {}
        self.attribute_nodes: T.Dict[ConvertAttr, ConvertAttrNode] = {}
        self.single_attributes[ConvertAttr.NAME] = f'"{name}"'

    def get_attribute_node(self, attribute: ConvertAttr) -> ConvertAttrNode:
        if attribute not in self.attribute_nodes:
            self.attribute_nodes[attribute] = ConvertAttrNode(attribute)

        return self.attribute_nodes[attribute]

    def finish(
        self,
        all_select_instance_groups: T.List[T.Set[SelectInstance]],
        all_custom_defaults: T.Set[SelectInstance],
    ) -> None:
        for node in self.attribute_nodes.values():
            node.consolidate_conditionals(all_select_instance_groups, all_custom_defaults)

    def emit(self) -> str:
        return ''


class CommonStateTracker:
    """Base class for all build system state trackers"""

    def __init__(self, project_config: ConvertProjectConfig):
        self.project_config = project_config
        self.current_toolchain: T.Optional[AbstractToolchainInfo] = None
        self.current_custom_select_instances: T.Optional[T.Set[SelectInstance]] = None
        self.all_toolchains: T.Set[AbstractToolchainInfo] = set()
        self.output_dir: str = ''

    def set_current_config(
        self,
        toolchain_info: AbstractToolchainInfo,
        custom_select_instances: T.Set[SelectInstance],
    ) -> None:
        self.current_toolchain = toolchain_info
        self.current_custom_select_instances = custom_select_instances
        self.all_toolchains.add(toolchain_info)

    def add_python_target(self, target: ConvertInstancePythonTarget) -> None:
        raise NotImplementedError

    def add_flag(self, flag: ConvertInstanceFlag) -> None:
        raise NotImplementedError

    def add_include_directory(self, inc: ConvertInstanceIncludeDirectory) -> None:
        raise NotImplementedError

    def add_file_group(self, grp: ConvertInstanceFileGroup) -> None:
        raise NotImplementedError

    def add_custom_target(self, custom_target: ConvertInstanceCustomTarget) -> None:
        raise NotImplementedError

    def add_static_library(self, lib: ConvertInstanceStaticLibrary) -> None:
        raise NotImplementedError

    def add_shared_library(self, lib: ConvertInstanceSharedLibrary) -> None:
        raise NotImplementedError

    def finish(self) -> None:
        raise NotImplementedError


class CommonEmitter:
    """Base class for all build system emitters"""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def emit(self, state_tracker: CommonStateTracker) -> None:
        pass
