#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T
from dataclasses import dataclass
from enum import Enum, IntEnum, IntFlag
from collections import defaultdict

from mesonbuild.convert.common_defs import SelectInstance, SelectId, SelectKind
from mesonbuild.convert.instance.convert_instance_custom_target import ConvertInstanceCustomTarget
from mesonbuild.convert.instance.convert_instance_build_target import RustABI


class ConvertAttr(Enum):
    # Common attributes (1-100)
    INCLUDES = 1
    LDFLAGS = 2  # LinkOpts in Bazel
    NAME = 3
    OUT = 4
    PYTHON_MAIN = 5
    RUSTFLAGS = 6
    RUST_CRATE_NAME = 7
    RUST_CRATE_ROOT = 8
    RUST_EDITION = 9
    RUST_PROC_MACROS = 10
    SRCS = 11
    TOOLS = 12

    # Soong-specific attributes (101-200)
    SOONG_APEX_AVAILABLE = 101
    SOONG_BINDGEN_FLAGS = 102
    SOONG_CFLAGS = 103
    SOONG_CPPFLAGS = 104
    SOONG_CPP_STD = 105
    SOONG_C_STD = 106
    SOONG_DEFAULTS = 107
    SOONG_ENABLED = 108
    SOONG_GENERATED_HEADERS = 109
    SOONG_HEADER_LIBS = 110
    SOONG_HOST_SUPPORTED = 111
    SOONG_LINKER_VERSION_SCRIPT = 112
    SOONG_PYTHON_LIBS = 113
    SOONG_RUST_CFGS = 114
    SOONG_RUST_LIBS = 115
    SOONG_SHARED_LIBRARIES = 116
    SOONG_SOURCE_STEM = 117
    SOONG_STATIC_LIBRARIES = 118
    SOONG_VENDOR = 119
    SOONG_VENDOR_AVAILABLE = 120
    SOONG_WHOLE_STATIC_LIBRARIES = 121
    SOONG_WRAPPER_SRC = 122

    # Bazel-specific attributes (201-300)
    BAZEL_DEPS = 201
    BAZEL_FLAGS = 202
    BAZEL_HDRS = 203


@dataclass
class SelectNode:
    select_ids: T.List[SelectId]
    select_tuples: T.List[T.Tuple[T.List[str], T.List[str]]]


class ConvertAttrNode:
    """Representation of target attributes.

    For example:

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

    The conditionality is provided the platform-generated SelectInstances
    as well as the user-provided SelectInstances.
    """

    def __init__(self, attribute: ConvertAttr):
        self.attribute = attribute
        # Bindgen is a sensitive to ordering and duplicates. For example, one may have
        # bindgen command like:
        #
        #      ["--allowlist-var", "ARM",
        #       "--allowlist-var", "AMD"]
        #
        # A set removes duplicates and changes ordering, so use a list in that instance.
        if attribute is ConvertAttr.SOONG_BINDGEN_FLAGS:
            self.common_values: T.Union[T.List[str], T.Set[str]] = []
        else:
            self.common_values = set()
        self.grouped_select_instances: T.Dict[str, T.List[T.Set[SelectInstance]]] = defaultdict(
            list
        )
        self.all_select_instances: T.Dict[str, T.Set[SelectInstance]] = defaultdict(set)
        self.common_custom_instances: T.Optional[T.Set[SelectInstance]] = None
        self.select_nodes: T.List[SelectNode] = []

    def add_common_values(self, values: T.List[str]) -> None:
        if isinstance(self.common_values, list):
            if not self.common_values:
                self.common_values.extend(values)
        else:
            self.common_values.update(values)

    def add_conditional_values(self, label: T.Set[SelectInstance],
                               values: T.List[str]) -> None:  # fmt: skip
        for select_instance in label:
            if select_instance.select_id.select_kind is SelectKind.CUSTOM:
                if self.common_custom_instances is None:
                    self.common_custom_instances = {select_instance}
                else:
                    self.common_custom_instances &= {select_instance}

        for value in values:
            self.grouped_select_instances[value].append(label)
            for select_instance in label:
                self.all_select_instances[value].add(select_instance)

    def consolidate_conditionals(self, select_instance_groups: T.List[T.Set[SelectInstance]],
                                 all_custom_defaults: T.Set[SelectInstance]) -> None:  # fmt: skip
        """
        Simplifies and organizes conditional attribute values after all project
        configurations have been processed.

        This method iterates through each attribute value and its associated
        conditional labels (`SelectInstance` objects). It intelligently determines
        if a value is truly conditional or if it's common to all configurations by
        checking against groups of conditions (e.g., al possible OSes,
        all architectures).

        For example, if a source file 'linux.c' is present in configurations for
        `{os:linux, arch:x86_64}` and `{os:linux, arch:aarch64}`, and the project
        is only configured for these two architectures, this method will deduce
        that 'linux.c' is only conditional on the OS. The redundant architecture
        conditions are removed.

        The final simplified condition is then stored in a `SelectNode`. If a value
        is found to be present in all possible configurations (i.e., it has no
        remaining unique conditions), it's moved from being conditional to the
        `common_values` set. This process ensures that the final build file output is
        as clean and minimal as possible.
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
                if isinstance(self.common_values, list):
                    if value not in self.common_values:
                        self.common_values.append(value)
                else:
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
                            for existing_values, attribute_values in select_node.select_tuples:
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
                            SelectNode(select_ids, [(current_select_values, [value])])
                        )

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


# Determines the order in which ConvertTargets are emitted
class ConvertTargetType(IntEnum):
    FILEGROUP = 0
    PYTHON_BINARY = 1
    PYTHON_LIBRARY = 2
    CUSTOM_TARGET = 3
    INCLUDE_DIRECTORY = 4
    FLAG = 5
    RUST_FLAG = 6
    STATIC_LIBRARY = 8
    SHARED_LIBRARY = 9
    EXECUTABLE = 10
    RUST_BINDGEN = 11
    RUST_LIBRARY = 12
    RUST_EXECUTABLE = 13
    RUST_FFI_STATIC = 14
    RUST_FFI_SHARED = 15
    UNKNOWN = 16


class SoongTargetBlock(IntFlag):
    NONE = 0
    HOST_MULTILIB = 1
    ANDROID_MULTILIB = 2
    ANDROID_32_BIT = 4
    ANDROID_INSTALL = 8


class ConvertTarget:
    """Base class for all converted build targets"""

    def __init__(self, name: str, subdir: str):
        self.name = name
        self.subdir = subdir
        self.single_attributes: T.Dict[ConvertAttr, str] = {}
        self.attribute_nodes: T.Dict[ConvertAttr, ConvertAttrNode] = {}
        self.single_attributes[ConvertAttr.NAME] = f'"{name}"'
        self.target_type = ConvertTargetType.UNKNOWN

    def get_attribute_node(self, attribute: ConvertAttr) -> ConvertAttrNode:
        if attribute not in self.attribute_nodes:
            self.attribute_nodes[attribute] = ConvertAttrNode(attribute)

        return self.attribute_nodes[attribute]

    def is_active_for_label(self, attribute: ConvertAttr,
                            label: T.Set[SelectInstance]) -> bool:  # fmt: skip
        """Checks if a target has any values defined for the specific label."""
        attr_node = self.attribute_nodes.get(attribute)
        if not attr_node:
            return False

        # If it has common values, it's active for all labels
        if attr_node.common_values:
            return True

        # Check if the exact current label was used to add values
        for labels_list in attr_node.grouped_select_instances.values():
            if label in labels_list:
                return True
        return False

    def finish(self, all_select_instance_groups: T.List[T.Set[SelectInstance]],
               all_custom_defaults: T.Set[SelectInstance]) -> None:  # fmt: skip
        for node in self.attribute_nodes.values():
            node.consolidate_conditionals(all_select_instance_groups, all_custom_defaults)

    def __lt__(self, other: ConvertTarget) -> bool:
        if not isinstance(other, ConvertTarget):
            return NotImplemented

        if self.target_type is not other.target_type:
            return self.target_type < other.target_type
        return self.name < other.name

    def emit(self) -> str:
        return ''


class ConvertFileGroup(ConvertTarget):
    def __init__(self, name: str, subdir: str):
        super().__init__(name, subdir)
        self.target_type = ConvertTargetType.FILEGROUP


class ConvertPythonBinary(ConvertTarget):
    def __init__(self, name: str, subdir: str):
        super().__init__(name, subdir)
        self.target_type = ConvertTargetType.PYTHON_BINARY


class ConvertCustomTarget(ConvertTarget):
    def __init__(self, name: str, subdir: str,
                 custom_target_instance: ConvertInstanceCustomTarget):  # fmt: skip
        super().__init__(name, subdir)
        self.cmd: str = ''
        self.instance = custom_target_instance
        self.target_type = ConvertTargetType.CUSTOM_TARGET


class ConvertFlag(ConvertTarget):
    def __init__(self, name: str, subdir: str, language: str):
        super().__init__(name, subdir)
        self.language = language
        self.host_supported: bool = False
        self.project_native_args: bool = False
        if language == 'rust':
            self.target_type = ConvertTargetType.RUST_FLAG
        else:
            self.target_type = ConvertTargetType.FLAG


class ConvertIncludeDirectory(ConvertTarget):
    def __init__(self, name: str, subdir: str):
        super().__init__(name, subdir)
        self.target_type = ConvertTargetType.INCLUDE_DIRECTORY


class ConvertBuildTarget(ConvertTarget):
    def __init__(self, name: str, subdir: str, rust_abi: RustABI):
        super().__init__(name, subdir)
        self.rust_abi = rust_abi
        self.project_native_args: bool = False
        self.soong_target_block: SoongTargetBlock = SoongTargetBlock.NONE


class ConvertStaticLibrary(ConvertBuildTarget):
    def __init__(self, name: str, subdir: str, rust_abi: RustABI):
        super().__init__(name, subdir, rust_abi)
        if rust_abi is RustABI.RUST:
            self.target_type = ConvertTargetType.RUST_LIBRARY
        elif rust_abi is RustABI.C:
            self.target_type = ConvertTargetType.RUST_FFI_STATIC
        else:
            self.target_type = ConvertTargetType.STATIC_LIBRARY


class ConvertSharedLibrary(ConvertBuildTarget):
    def __init__(self, name: str, subdir: str, rust_abi: RustABI):
        super().__init__(name, subdir, rust_abi)
        if rust_abi is RustABI.C:
            self.target_type = ConvertTargetType.RUST_FFI_SHARED
        else:
            self.target_type = ConvertTargetType.SHARED_LIBRARY


class ConvertExecutable(ConvertBuildTarget):
    def __init__(self, name: str, subdir: str, rust_abi: RustABI):
        super().__init__(name, subdir, rust_abi)
        if rust_abi is RustABI.BINARY:
            self.target_type = ConvertTargetType.RUST_EXECUTABLE
        else:
            self.target_type = ConvertTargetType.EXECUTABLE


class ConvertRustBindgen(ConvertTarget):
    def __init__(self, name: str, subdir: str):
        super().__init__(name, subdir)
        self.target_type = ConvertTargetType.RUST_BINDGEN
