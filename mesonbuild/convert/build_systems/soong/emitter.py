#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T
import datetime
import os
import textwrap
from collections import defaultdict

from mesonbuild.convert.common_defs import (
    SelectId,
    SelectKind,
)

from mesonbuild.convert.build_systems.soong.state import (
    SoongStateTracker,
    SoongBuildTarget,
    SoongFileGroup,
    SoongPythonTarget,
    SoongCustomTarget,
    SoongIncludeDirectory,
    SoongFlag,
    SoongTargetType,
    SoongStaticLibrary,
    SoongSharedLibrary,
)
from mesonbuild.convert.build_systems.common import (
    ConvertAttr,
    ConvertTarget,
    ConvertAttrNode,
    CommonEmitter,
    CommonStateTracker,
    SelectNode,
    COMMON_INDENT,
    COMMON_MAX_LINE_LENGTH,
)

MULTILIB_TARGET_BLOCK = """\
    target: {
        host: {
            compile_multilib: "64",
        },
    },
"""

INSTALL_TARGET_BLOCK = """\
    target: {
        android: {
            relative_install_path: "hw",
        },
    },
"""

COPYRIGHT_HEADER_TEMPLATE = """\
/*
 * Copyright (C) {year} The Meson Development Team
 * SPDX-License-Identifier: Apache-2.0
 *
 * Generated via meson2hermetic.  Do not hand-edit.
 *
 */

package {{
    // See: http://go/android-license-faq
    default_applicable_licenses: ["{license_name}"],
}}"""

LICENSE_BLOCK_TEMPLATE = """\
license {{
    name: "{license_name}",
    visibility: [":__subpackages__"],
    license_kinds: [
{license_kinds}
    ],
    license_text: [
{license_texts}
    ],
}}"""

SOONG_ATTR_MAP = {
    ConvertAttr.NAME: 'name',
    ConvertAttr.SRCS: 'srcs',
    ConvertAttr.SOONG_DEFAULTS: 'defaults',
    ConvertAttr.SOONG_STATIC_LIBRARIES: 'static_libs',
    ConvertAttr.SOONG_SHARED_LIBRARIES: 'shared_libs',
    ConvertAttr.SOONG_WHOLE_STATIC_LIBRARIES: 'whole_static_libs',
    ConvertAttr.SOONG_HEADER_LIBS: 'header_libs',
    ConvertAttr.SOONG_GENERATED_HEADERS: 'generated_headers',
    ConvertAttr.SOONG_GENERATED_SOURCES: 'generated_sources',
    ConvertAttr.SOONG_CFLAGS: 'cflags',
    ConvertAttr.SOONG_CPPFLAGS: 'cppflags',
    ConvertAttr.RUSTFLAGS: 'flags',
    ConvertAttr.SOONG_HOST_SUPPORTED: 'host_supported',
    ConvertAttr.SOONG_VENDOR: 'vendor',
    ConvertAttr.OUT: 'out',
    ConvertAttr.TOOLS: 'tools',
    ConvertAttr.INCLUDES: 'export_include_dirs',
    ConvertAttr.PYTHON_MAIN: 'main',
    ConvertAttr.SOONG_PYTHON_LIBS: 'libs',
    ConvertAttr.RUST_CRATE_NAME: 'crate_name',
    ConvertAttr.RUST_CRATE_ROOT: 'crate_root',
    ConvertAttr.SOONG_RUST_LIBS: 'rustlibs',
    ConvertAttr.RUST_PROC_MACROS: 'proc_macros',
    ConvertAttr.RUST_EDITION: 'edition',
    ConvertAttr.SOONG_C_STD: 'c_std',
    ConvertAttr.SOONG_CPP_STD: 'cpp_std',
    ConvertAttr.LDFLAGS: 'ldflags',
    ConvertAttr.SOONG_LINKER_VERSION_SCRIPT: 'version_script',
}


def _format_select_value(value: T.Union[str, bool]) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if value == 'default':
        return value
    return f'"{value}"'


def _format_select_id(select_id: SelectId) -> str:
    if select_id.select_kind == SelectKind.ARCH:
        return 'arch()'
    if select_id.select_kind == SelectKind.OS:
        return 'os()'
    if select_id.select_kind == SelectKind.CUSTOM:
        return f'soong_config_variable("{select_id.namespace}", "{select_id.variable}")'
    return ''


def _emit_list_parens(strings: T.List[str]) -> str:
    content_str = ''
    for i, string in enumerate(strings):
        content_str += string
        if i != len(strings) - 1:
            content_str += ', '

    if len(strings) > 1:
        content_str = '(' + content_str + ')'

    return content_str


def _emit_attribute_values(current_indent: int, attribute_values: T.List[str]) -> str:
    if not attribute_values:
        return ' []'

    default_indent = ' ' * current_indent
    list_indent = ' ' * (current_indent + COMMON_INDENT)
    content_str = ' [\n'
    for value in attribute_values:
        content_str += f'{list_indent}"{value}",\n'

    content_str += f'{default_indent}]'
    return content_str


def _emit_select_ids(select_node: SelectNode) -> str:
    formatted_select_ids: T.List[str] = []
    for select_id in select_node.select_ids:
        formatted_select_ids.append(_format_select_id(select_id))

    return _emit_list_parens(formatted_select_ids)


def _emit_select_values(indent: int, select_node: SelectNode) -> str:
    content_str = ''
    value_indent = indent + COMMON_INDENT
    indent_str = ' ' * value_indent
    for select_values, attribute_values in select_node.select_tuples:
        formatted_values: T.List[str] = []
        for select_value in select_values:
            formatted_values.append(_format_select_value(select_value))

        content_str += indent_str + _emit_list_parens(formatted_values) + ':'
        content_str += (_emit_attribute_values(value_indent, attribute_values) + ',\n')

    return content_str


def _emit_conditionals(indent: int, node: ConvertAttrNode) -> str:
    content_str = ''
    current_indent = ' ' * indent
    select_nodes = node.get_select_nodes()
    if not select_nodes:
        return content_str

    need_addition = False
    if node.common_values:
        need_addition = True

    for i, select_node in enumerate(select_nodes):
        if need_addition:
            content_str += ' + '
        else:
            content_str += ' '

        content_str += 'select('
        content_str += _emit_select_ids(select_node)
        content_str += ', {\n'
        content_str += _emit_select_values(indent, select_node)
        content_str += f'{current_indent}}})'
        need_addition = True

    return content_str


def _custom_target_emit(custom_target: SoongCustomTarget) -> str:
    wrapper = textwrap.TextWrapper(width=COMMON_MAX_LINE_LENGTH, break_on_hyphens=False)
    lines = wrapper.wrap(text=custom_target.cmd)
    cmd_str = COMMON_INDENT * ' ' + 'cmd: '
    subsequent_indent = 2 * COMMON_INDENT

    for i, line in enumerate(lines):
        first_line = False
        last_line = False
        if i == 0:
            first_line = True
        if i == len(lines) - 1:
            last_line = True

        if last_line:
            line = f'"{line}",'
        else:
            if not line.endswith(' '):
                line = line + ' '
            line = f'"{line}" +'

        if not first_line:
            cmd_str += ' ' * subsequent_indent

        cmd_str += line
        cmd_str += '\n'

    return cmd_str


def _flag_target_emit(flag: SoongFlag) -> str:
    content_str = ''
    if flag.project_native_args and flag.host_supported:
        content_str += MULTILIB_TARGET_BLOCK
    return content_str


def _build_target_emit(build_target: SoongBuildTarget) -> str:
    content_str = ''
    if build_target.install:
        content_str += INSTALL_TARGET_BLOCK
    return content_str


class SoongModuleEmitter:
    """Emits a Soong module definition."""

    def __init__(self, target: ConvertTarget):
        self.target = target
        self.special_emit: T.Optional[T.Callable[[T.Any], str]] = None
        if isinstance(target, SoongCustomTarget):
            self.special_emit = _custom_target_emit
        elif isinstance(target, SoongFlag):
            self.special_emit = _flag_target_emit
        elif isinstance(target, SoongBuildTarget):
            self.special_emit = _build_target_emit

    def emit(self) -> str:
        content = '\n\n'
        content += f'{self.target.module_type} {{\n'
        content += self.emit_single_attributes()
        content += self.emit_attribute_nodes()

        if self.special_emit is not None:
            content += self.special_emit(self.target)

        content += '}'

        return content

    def emit_single_attributes(self) -> str:
        content_str = ''
        attr_indent = COMMON_INDENT * ' '
        for attr, value in self.target.single_attributes.items():
            attr_name = SOONG_ATTR_MAP.get(attr)
            if attr_name:
                content_str += f'{attr_indent}{attr_name}: {value},\n'

        return content_str

    def emit_attribute_nodes(self) -> str:
        attr_indent = COMMON_INDENT * ' '

        content_str = ''
        for attr, node in self.target.attribute_nodes.items():
            if node.empty():
                continue

            attr_name = SOONG_ATTR_MAP.get(attr)
            if not attr_name:
                continue

            content_str += f'{attr_indent}{attr_name}:'
            common_values = list(node.common_values)
            common_values.sort()

            if node.common_values:
                content_str += _emit_attribute_values(COMMON_INDENT, common_values)
            content_str += _emit_conditionals(COMMON_INDENT, node)
            content_str += ',\n'

        return content_str


def _get_target_sort_key(t: SoongTargetType) -> T.Tuple[int, str]:
    type_map = {
        SoongFileGroup: 0,
        SoongPythonTarget: 1,
        SoongCustomTarget: 2,
        SoongIncludeDirectory: 3,
        SoongFlag: 4,
        SoongStaticLibrary: 5,
        SoongSharedLibrary: 6,
    }
    priority = type_map.get(type(t), 7)
    return (priority, t.name)


class SoongEmitter(CommonEmitter):
    """Emits the Soong build files."""

    def emit(self, state_tracker: CommonStateTracker) -> None:
        state_tracker = T.cast(SoongStateTracker, state_tracker)
        copyright_info = state_tracker.project_config.copyright.copy()
        copyright_info.setdefault('year', datetime.date.today().year)

        copyright_string = COPYRIGHT_HEADER_TEMPLATE.format(
            year=copyright_info['year'],
            license_name=copyright_info['license_name'],
        )

        license_kinds = '\n'.join([
            f'        "SPDX-license-identifier-{lic}",'
            for lic in copyright_info.get('licenses', [])
        ])
        license_texts = '\n'.join(
            [f'        "{txt}",' for txt in copyright_info.get('license_texts', [])])
        license_string = LICENSE_BLOCK_TEMPLATE.format(
            license_name=copyright_info['license_name'],
            license_kinds=license_kinds,
            license_texts=license_texts,
        )

        targets_by_subdir = defaultdict(list)
        for t in state_tracker.targets.values():
            targets_by_subdir[t.subdir].append(t)

        for subdir, targets in targets_by_subdir.items():
            targets.sort(key=_get_target_sort_key)

            content = copyright_string
            if not subdir:
                content += '\n\n' + license_string

            for target in targets:
                module = SoongModuleEmitter(target)
                content += module.emit()

            content += '\n'
            output_path = (os.path.join(self.output_dir, subdir) if subdir else self.output_dir)
            os.makedirs(output_path, exist_ok=True)
            with open(os.path.join(output_path, 'Android.bp'), 'w', encoding='utf-8') as f:
                f.write(content)
