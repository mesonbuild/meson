#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T
import os

from mesonbuild.convert.build_systems.target import (
    ConvertAttr,
    ConvertTarget,
    ConvertTargetType,
    ConvertAttrNode,
)

COMMON_INDENT = 4
COMMON_MAX_LINE_LENGTH = 70

if T.TYPE_CHECKING:
    from mesonbuild.convert.build_systems.common import ConvertStateTracker


class ConvertEmitterBackend:
    """Interface for build system emitter backends."""

    def emit_begin(self, output_dir: str, state_tracker: ConvertStateTracker) -> None:
        pass

    def get_attr_map(self) -> T.Dict[ConvertAttr, str]:
        raise NotImplementedError

    def get_module_map(self) -> T.Dict[ConvertTargetType, str]:
        raise NotImplementedError

    def get_attr_separator(self) -> str:
        raise NotImplementedError

    def get_opening_brace(self) -> str:
        raise NotImplementedError

    def get_closing_brace(self) -> str:
        raise NotImplementedError

    def get_list_brackets(self) -> T.Tuple[str, str]:
        return ("[", "]")

    def get_build_file_name(self) -> str:
        raise NotImplementedError

    def get_copyright_header(self, copyright_info: T.Dict[str, T.Any]) -> str:
        raise NotImplementedError

    def get_license_block(
        self, copyright_info: T.Dict[str, T.Any], is_root: bool
    ) -> str:
        raise NotImplementedError

    def emit_extra_root_info(self, state_tracker: ConvertStateTracker) -> str:
        return ""

    def emit_module_load_info(
        self, targets: T.List[ConvertTarget], is_root: bool
    ) -> str:
        return ""

    def emit_special_target_info(self, target: ConvertTarget) -> str:
        return ""

    def format_conditionals(self, indent: int, node: ConvertAttrNode) -> str:
        raise NotImplementedError


def generic_emit_attribute_values(
        current_indent: int,
        attribute_values: T.List[str],
        brackets: T.Tuple[str, str] = ("[", "]"),
        leading_space: bool = False) -> str:  # fmt: skip
    if not attribute_values:
        return (" " if leading_space else "") + f"{brackets[0]}{brackets[1]}"

    default_indent = " " * current_indent
    list_indent = " " * (current_indent + COMMON_INDENT)
    content_str = (" " if leading_space else "") + f"{brackets[0]}\n"
    for value in attribute_values:
        content_str += f'{list_indent}"{value}",\n'

    content_str += f"{default_indent}{brackets[1]}"
    return content_str


class CommonModuleEmitter:
    """Shared module emitter that delegates backend-specific syntax to a backend."""

    def __init__(self, target: ConvertTarget, backend: ConvertEmitterBackend):
        self.target = target
        self.backend = backend

    def emit(self) -> str:
        content = "\n\n"
        module_type = self.backend.get_module_map().get(
            self.target.target_type, "unknown"
        )
        content += f"{module_type}{self.backend.get_opening_brace()}\n"
        content += self.emit_single_attributes()
        content += self.emit_attribute_nodes()

        special_info = self.backend.emit_special_target_info(self.target)
        if special_info:
            content += special_info

        content += self.backend.get_closing_brace()
        return content

    def emit_single_attributes(self) -> str:
        content_str = ""
        attr_indent = COMMON_INDENT * " "
        attr_map = self.backend.get_attr_map()
        separator = self.backend.get_attr_separator()

        for attr, value in self.target.single_attributes.items():
            attr_name = attr_map.get(attr)
            if attr_name:
                content_str += f"{attr_indent}{attr_name}{separator} {value},\n"
        return content_str

    def emit_attribute_nodes(self) -> str:
        attr_indent = COMMON_INDENT * " "
        attr_map = self.backend.get_attr_map()
        separator = self.backend.get_attr_separator()

        content_str = ""
        for attr, node in self.target.attribute_nodes.items():
            if node.empty():
                continue

            attr_name = attr_map.get(attr)
            if not attr_name:
                continue

            content_str += f"{attr_indent}{attr_name}{separator}"
            common_values = list(node.common_values)
            common_values.sort()

            if node.common_values:
                content_str += generic_emit_attribute_values(
                    COMMON_INDENT,
                    common_values,
                    self.backend.get_list_brackets(),
                    leading_space=(separator == ":"),
                )

            if node.select_nodes:
                if node.common_values:
                    content_str += " + "
                elif separator == ":":
                    content_str += " "
                content_str += self.backend.format_conditionals(COMMON_INDENT, node)
            content_str += ",\n"
        return content_str


class CommonEmitter:
    """Base class for all build system emitters, handling high-level emission logic."""

    def __init__(self, output_dir: str, backend: ConvertEmitterBackend):
        self.output_dir = output_dir
        self.backend = backend

    def emit(self, state_tracker: ConvertStateTracker) -> None:
        self.backend.emit_begin(self.output_dir, state_tracker)

        copyright_info = state_tracker.project_config.copyright.copy()
        copyright_header = self.backend.get_copyright_header(copyright_info).strip()

        for node in state_tracker.targets.walk():
            subdir = node.subdir
            targets = node.targets
            if not targets and not node.is_root:
                continue

            is_root = node.is_root
            blocks = []

            load_info = self.backend.emit_module_load_info(targets, is_root).strip()
            if load_info:
                # Place load info immediately after copyright header
                blocks.append(copyright_header + "\n\n" + load_info)
            else:
                blocks.append(copyright_header)

            license_block = self.backend.get_license_block(
                copyright_info, is_root
            ).strip()
            if license_block:
                blocks.append(license_block)

            for target in targets:
                module_text = CommonModuleEmitter(target, self.backend).emit().strip()
                blocks.append(module_text)

            if is_root:
                extra_info = self.backend.emit_extra_root_info(state_tracker).strip()
                if extra_info:
                    blocks.append(extra_info)

            content = "\n\n".join(blocks) + "\n"

            output_path = (
                os.path.join(self.output_dir, subdir) if subdir else self.output_dir
            )
            os.makedirs(output_path, exist_ok=True)
            with open(
                os.path.join(output_path, self.backend.get_build_file_name()),
                "w",
                encoding="utf-8",
            ) as f:
                f.write(content)
