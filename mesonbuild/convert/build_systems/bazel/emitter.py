#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T
import datetime
import os
from collections import defaultdict

from mesonbuild.convert.build_systems.bazel.state import (
    BazelStateTracker,
    BazelFileGroup,
    BazelPythonTarget,
    BazelCustomTarget,
    BazelIncludeDirectory,
    BazelFlag,
    BazelTargetType,
    BazelStaticLibrary,
    BazelSharedLibrary,
)
from mesonbuild.convert.build_systems.common import (
    ConvertAttr,
    ConvertAttrNode,
    ConvertTarget,
    CommonEmitter,
    CommonStateTracker,
    SelectNode,
    COMMON_INDENT,
)

COPYRIGHT_HEADER_TEMPLATE = """\
# Copyright {year} The Meson Development Team
# SPDX-License-Identifier: Apache-2.0
#
# Generated via meson2hermetic.  Do not hand-edit.
#
"""

LICENSE_BLOCK_TEMPLATE = """\
load("//tools/build_defs/license:license.bzl", "license")

package(
    default_applicable_licenses = [
{license_kinds}
    ],
    default_visibility = ["//visibility:public"],
)
"""

BAZEL_ATTR_MAP = {
    ConvertAttr.NAME: 'name',
    ConvertAttr.SRCS: 'srcs',
    ConvertAttr.INCLUDES: 'includes',
    ConvertAttr.BAZEL_DEPS: 'deps',
    ConvertAttr.BAZEL_DEFINES: 'defines',
    ConvertAttr.RUSTFLAGS: 'rustc_flags',
    ConvertAttr.OUT: 'outs',
    ConvertAttr.TOOLS: 'tools',
    ConvertAttr.PYTHON_MAIN: 'main',
    ConvertAttr.RUST_CRATE_NAME: 'crate_name',
    ConvertAttr.RUST_EDITION: 'edition',
    ConvertAttr.LDFLAGS: 'linkopts',
}


def _format_select_value(value: T.Union[str, bool]) -> str:
    # This needs to map to a config_setting label
    # For now, just return the string
    return f'"//{value}"'


def _emit_attribute_values(current_indent: int, attribute_values: T.List[str]) -> str:
    if not attribute_values:
        return '[]'

    default_indent = ' ' * current_indent
    list_indent = ' ' * (current_indent + COMMON_INDENT)
    content_str = '[\n'
    for value in attribute_values:
        content_str += f'{list_indent}"{value}",\n'
    content_str += f'{default_indent}]'
    return content_str


def _emit_select_values(indent: int, select_node: SelectNode) -> str:
    content_str = ''
    value_indent = indent + COMMON_INDENT
    indent_str = ' ' * value_indent
    for select_values, attribute_values in select_node.select_tuples:
        # This is a simplification. Real Bazel select needs a proper mapping
        # from select_values to a config_setting label.
        key = ':'.join(select_values)
        if key == 'default':
            key = '//conditions:default'
        content_str += f'{indent_str}"{key}": {_emit_attribute_values(value_indent, attribute_values)},\n'
    return content_str


def _emit_conditionals(indent: int, node: ConvertAttrNode) -> str:
    content_str = ''
    select_nodes = node.get_select_nodes()
    if not select_nodes:
        return content_str

    # Bazel's select() is a dictionary, so we can't just add them up like in Soong
    # This implementation is a simplification and might need to be more sophisticated
    # for complex cases. We take the first select node.
    select_node = select_nodes[0]

    content_str += ' select({\n'
    content_str += _emit_select_values(indent, select_node)
    content_str += ' ' * indent + '})'
    return content_str


class BazelModuleEmitter:
    """Emits a Bazel module definition."""

    def __init__(self, target: ConvertTarget):
        self.target = target

    def emit(self) -> str:
        content = '\n\n'
        content += f'{self.target.module_type}(\n'
        content += self.emit_single_attributes()
        content += self.emit_attribute_nodes()
        if isinstance(self.target, BazelCustomTarget):
            content += f'    cmd = "{self.target.cmd}",\n'
        content += ')'
        return content

    def emit_single_attributes(self) -> str:
        content_str = ''
        attr_indent = COMMON_INDENT * ' '
        for attr, value in self.target.single_attributes.items():
            attr_name = BAZEL_ATTR_MAP.get(attr)
            if attr_name:
                content_str += f'{attr_indent}{attr_name} = {value},\n'
        return content_str

    def emit_attribute_nodes(self) -> str:
        attr_indent = COMMON_INDENT * ' '
        content_str = ''
        for attr, node in self.target.attribute_nodes.items():
            if node.empty():
                continue

            attr_name = BAZEL_ATTR_MAP.get(attr)
            if not attr_name:
                continue

            content_str += f'{attr_indent}{attr_name} = '
            common_values = list(node.common_values)
            common_values.sort()

            if node.common_values:
                content_str += _emit_attribute_values(COMMON_INDENT, common_values)

            if node.select_nodes:
                if node.common_values:
                    content_str += ' + '
                content_str += _emit_conditionals(COMMON_INDENT, node)
            content_str += ',\n'
        return content_str


def _get_target_sort_key(t: BazelTargetType) -> T.Tuple[int, str]:
    type_map = {
        BazelFileGroup: 0,
        BazelPythonTarget: 1,
        BazelCustomTarget: 2,
        BazelIncludeDirectory: 3,
        BazelFlag: 4,
        BazelStaticLibrary: 5,
        BazelSharedLibrary: 6,
    }
    priority = type_map.get(type(t), 7)
    return (priority, t.name)


class BazelEmitter(CommonEmitter):
    """Emits the Bazel build files."""

    def emit(self, state_tracker: CommonStateTracker) -> None:
        state_tracker = T.cast(BazelStateTracker, state_tracker)
        copyright_info = state_tracker.project_config.copyright.copy()
        copyright_info.setdefault('year', datetime.date.today().year)
        copyright_string = COPYRIGHT_HEADER_TEMPLATE.format(year=copyright_info['year'])

        license_string = ''
        if 'license_name' in copyright_info:
            license_kinds = '\n'.join(
                [f'        "{lic}",' for lic in copyright_info.get('licenses', [])])
            license_string = LICENSE_BLOCK_TEMPLATE.format(
                license_name=copyright_info['license_name'],
                license_kinds=license_kinds,
                license_text=copyright_info.get('license_text', 'LICENSE'),
            )

        targets_by_subdir: T.DefaultDict[str, T.List[BazelTargetType]] = defaultdict(list)
        for t in state_tracker.targets.values():
            targets_by_subdir[t.subdir].append(t)

        for subdir, targets in targets_by_subdir.items():
            targets.sort(key=_get_target_sort_key)
            content = copyright_string
            if license_string:
                content += '\n\n' + license_string

            for target in targets:
                module = BazelModuleEmitter(target)
                content += module.emit()

            content += '\n'
            output_path = (os.path.join(self.output_dir, subdir) if subdir else self.output_dir)
            os.makedirs(output_path, exist_ok=True)
            with open(os.path.join(output_path, 'BUILD.bazel'), 'w', encoding='utf-8') as f:
                f.write(content)
