#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T
import textwrap
from pathlib import Path

from mesonbuild.convert.common_defs import SelectId, SelectKind
from mesonbuild.convert.build_systems.target import (
    ConvertAttr,
    ConvertTarget,
    ConvertTargetType,
    ConvertAttrNode,
    ConvertCustomTarget,
    ConvertFlag,
    ConvertBuildTarget,
    SoongTargetBlock,
)
from mesonbuild.convert.build_systems.emitter import (
    ConvertEmitterBackend,
    generic_emit_attribute_values,
    COMMON_INDENT,
    COMMON_MAX_LINE_LENGTH,
)

from mesonbuild.convert.build_systems.common import ConvertStateTracker
from mesonbuild.convert.convert_project_config import CopyrightSection

TARGET_BLOCK = """\
    target: {
"""


TARGET_BLOCK_HOST = """\
        host: {
"""

TARGET_BLOCK_ANDROID = """\
        android: {
"""

MULTILIB_64 = """\
            compile_multilib: "64",
"""


ANDROID_INSTALL = """\
            relative_install_path: "hw",
"""

COPYRIGHT_HEADER_TEMPLATE = """\
/*
 * Copyright (C) 2025-2026 The Magma GPU Project
 * SPDX-License-Identifier: Apache-2.0
 *
 * Generated via:
 *   https://github.com/mesonbuild/meson/tree/master/mesonbuild/convert
 *
 * Submit patches, do not hand-edit.
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


SOONG_ATTR_MAP: T.Dict[ConvertAttr, str] = {
    # Common attributes
    ConvertAttr.INCLUDES: 'export_include_dirs',
    ConvertAttr.LDFLAGS: 'ldflags',
    ConvertAttr.NAME: 'name',
    ConvertAttr.OUT: 'out',
    ConvertAttr.PYTHON_MAIN: 'main',
    ConvertAttr.RUSTFLAGS: 'flags',
    ConvertAttr.RUST_CRATE_NAME: 'crate_name',
    ConvertAttr.RUST_CRATE_ROOT: 'crate_root',
    ConvertAttr.RUST_EDITION: 'edition',
    ConvertAttr.RUST_PROC_MACROS: 'proc_macros',
    ConvertAttr.SRCS: 'srcs',
    ConvertAttr.TOOLS: 'tools',
    # Soong-specific attributes
    ConvertAttr.SOONG_APEX_AVAILABLE: 'apex_available',
    ConvertAttr.SOONG_BINDGEN_FLAGS: 'bindgen_flags',
    ConvertAttr.SOONG_CFLAGS: 'cflags',
    ConvertAttr.SOONG_CPPFLAGS: 'cppflags',
    ConvertAttr.SOONG_CPP_STD: 'cpp_std',
    ConvertAttr.SOONG_C_STD: 'c_std',
    ConvertAttr.SOONG_DEFAULTS: 'defaults',
    ConvertAttr.SOONG_ENABLED: 'enabled',
    ConvertAttr.SOONG_GENERATED_HEADERS: 'generated_headers',
    ConvertAttr.SOONG_HEADER_LIBS: 'header_libs',
    ConvertAttr.SOONG_HOST_SUPPORTED: 'host_supported',
    ConvertAttr.SOONG_LINKER_VERSION_SCRIPT: 'version_script',
    ConvertAttr.SOONG_PYTHON_LIBS: 'libs',
    ConvertAttr.SOONG_RUST_CFGS: 'cfgs',
    ConvertAttr.SOONG_RUST_LIBS: 'rustlibs',
    ConvertAttr.SOONG_SHARED_LIBRARIES: 'shared_libs',
    ConvertAttr.SOONG_SOURCE_STEM: 'source_stem',
    ConvertAttr.SOONG_STATIC_LIBRARIES: 'static_libs',
    ConvertAttr.SOONG_VENDOR: 'vendor',
    ConvertAttr.SOONG_VENDOR_AVAILABLE: 'vendor_available',
    ConvertAttr.SOONG_WHOLE_STATIC_LIBRARIES: 'whole_static_libs',
    ConvertAttr.SOONG_WRAPPER_SRC: 'wrapper_src',
}


SOONG_MODULE_MAP = {
    ConvertTargetType.CUSTOM_TARGET: 'genrule',
    ConvertTargetType.EXECUTABLE: 'cc_binary',
    ConvertTargetType.FILEGROUP: 'filegroup',
    ConvertTargetType.FLAG: 'cc_defaults',
    ConvertTargetType.INCLUDE_DIRECTORY: 'cc_library_headers',
    ConvertTargetType.PYTHON_BINARY: 'python_binary_host',
    ConvertTargetType.PYTHON_LIBRARY: 'python_library_host',
    ConvertTargetType.RUST_BINDGEN: 'rust_bindgen',
    ConvertTargetType.RUST_EXECUTABLE: 'rust_binary',
    ConvertTargetType.RUST_FFI_SHARED: 'rust_ffi_shared',
    ConvertTargetType.RUST_FFI_STATIC: 'rust_ffi_static',
    ConvertTargetType.RUST_FLAG: 'rust_defaults',
    ConvertTargetType.RUST_LIBRARY: 'rust_library',
    ConvertTargetType.SHARED_LIBRARY: 'cc_library_shared',
    ConvertTargetType.STATIC_LIBRARY: 'cc_library_static',
}


def _format_select_value(value: T.Union[str, bool]) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if value == 'default':
        return value
    return f'"{value}"'


def _format_select_id(select_id: SelectId) -> str:
    if select_id.select_kind is SelectKind.ARCH:
        return 'arch()'
    if select_id.select_kind is SelectKind.OS:
        return 'os()'
    if select_id.select_kind is SelectKind.CUSTOM:
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


def _emit_target_block(soong_target_block: SoongTargetBlock) -> str:
    content_str = ''
    if soong_target_block is SoongTargetBlock.NONE:
        return content_str

    content_str += TARGET_BLOCK
    if soong_target_block & SoongTargetBlock.HOST_MULTILIB:
        content_str += TARGET_BLOCK_HOST
        content_str += MULTILIB_64
        content_str += 2 * COMMON_INDENT * ' ' + '},\n'

    if (soong_target_block & SoongTargetBlock.ANDROID_MULTILIB or soong_target_block & SoongTargetBlock.ANDROID_INSTALL):  # fmt: skip
        content_str += TARGET_BLOCK_ANDROID
        if (soong_target_block & SoongTargetBlock.ANDROID_MULTILIB and not soong_target_block & SoongTargetBlock.ANDROID_32_BIT):  # fmt: skip
            content_str += MULTILIB_64
        if soong_target_block & SoongTargetBlock.ANDROID_INSTALL:
            content_str += ANDROID_INSTALL
        content_str += 2 * COMMON_INDENT * ' ' + '},\n'

    content_str += COMMON_INDENT * ' ' + '},\n'
    return content_str


class SoongEmitterBackend(ConvertEmitterBackend):
    def get_attr_map(self) -> T.Dict[ConvertAttr, str]:
        return SOONG_ATTR_MAP

    def get_module_map(self) -> T.Dict[ConvertTargetType, str]:
        return SOONG_MODULE_MAP

    def get_attr_separator(self) -> str:
        return ': '

    def get_opening_brace(self) -> str:
        return ' {'

    def get_closing_brace(self) -> str:
        return '}'

    def get_build_file_name(self) -> str:
        return 'Android.bp'

    def get_build_file_globs(self) -> T.List[str]:
        return ['*.bp']

    def get_copyright_header(self, copyright_info: CopyrightSection) -> str:
        return COPYRIGHT_HEADER_TEMPLATE.format(
            license_name=copyright_info.get('license_name', 'unnamed')
        )

    def get_license_block(self, copyright_info: CopyrightSection,
                          is_root: bool) -> str:  # fmt: skip
        if is_root:
            license_kinds = '\n'.join(
                [
                    f'        "SPDX-license-identifier-{lic}",'
                    for lic in copyright_info.get('licenses', [])
                ]
            )
            license_texts = '\n'.join(
                [f'        "{txt}",' for txt in copyright_info.get('license_texts', [])]
            )
            return '\n\n' + LICENSE_BLOCK_TEMPLATE.format(
                license_name=copyright_info.get('license_name', 'unnamed'),
                license_kinds=license_kinds,
                license_texts=license_texts,
            )
        return ''

    def emit_extra_root_info(self, state_tracker: ConvertStateTracker) -> str:
        content = ''
        handwritten_modules = state_tracker.project_config.handwritten_modules
        if handwritten_modules:
            handwritten_path = Path(state_tracker.project_config.config_dir) / handwritten_modules
            if handwritten_path.exists():
                with open(handwritten_path, 'r', encoding='utf-8') as f:
                    content += '\n\n' + f.read()
        return content

    def emit_special_target_info(self, target: ConvertTarget) -> str:
        content_str = ''
        if isinstance(target, ConvertCustomTarget):
            # This emits custom_target.cmd with across different lengths and concencatation
            # between lines.
            wrapper = textwrap.TextWrapper(width=COMMON_MAX_LINE_LENGTH, break_on_hyphens=False)
            lines = wrapper.wrap(text=target.cmd)
            content_str += COMMON_INDENT * ' ' + 'cmd: '
            subsequent_indent = 2 * COMMON_INDENT

            for i, line in enumerate(lines):
                first_line = i == 0
                last_line = i == len(lines) - 1

                if last_line:
                    line = f'"{line}",'
                else:
                    if not line.endswith(' '):
                        line = line + ' '
                    line = f'"{line}" +'

                if not first_line:
                    content_str += ' ' * subsequent_indent

                content_str += line + '\n'
        elif isinstance(target, ConvertFlag):
            if target.project_native_args and target.host_supported:
                content_str += _emit_target_block(SoongTargetBlock.HOST_MULTILIB)
        elif isinstance(target, ConvertBuildTarget):
            content_str += _emit_target_block(target.soong_target_block)
        return content_str

    def format_conditionals(self, indent: int, node: ConvertAttrNode) -> str:
        content_str = ''
        current_indent = ' ' * indent
        select_nodes = node.get_select_nodes()
        if not select_nodes:
            return content_str

        for i, select_node in enumerate(select_nodes):
            if i > 0:
                content_str += ' + '

            content_str += 'select('
            formatted_select_ids: T.List[str] = []
            for select_id in select_node.select_ids:
                formatted_select_ids.append(_format_select_id(select_id))
            content_str += _emit_list_parens(formatted_select_ids)
            content_str += ', {\n'

            value_indent = indent + COMMON_INDENT
            indent_str = ' ' * value_indent
            for select_values, attribute_values in select_node.select_tuples:
                formatted_values: T.List[str] = []
                for select_value in select_values:
                    formatted_values.append(_format_select_value(select_value))

                content_str += indent_str + _emit_list_parens(formatted_values) + ':'
                content_str += (
                    generic_emit_attribute_values(
                        value_indent, attribute_values, self.get_list_brackets(), leading_space=True
                    )
                    + ',\n'
                )

            content_str += f'{current_indent}}})'

        return content_str
