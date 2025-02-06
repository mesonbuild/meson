#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T
from collections import defaultdict

from mesonbuild.convert.build_systems.target import (
    ConvertAttr,
    ConvertTarget,
    ConvertTargetType,
    ConvertAttrNode,
)
from mesonbuild.convert.build_systems.emitter import (
    ConvertEmitterBackend,
    generic_emit_attribute_values,
    COMMON_INDENT,
)
from mesonbuild.convert.build_systems.bazel.bzlmod_emitter import _emit_module_bazel

if T.TYPE_CHECKING:
    from mesonbuild.convert.build_systems.common import ConvertStateTracker

COPYRIGHT_HEADER_TEMPLATE = """\
# Copyright (C) 2025-2026 The Magma GPU Project
# SPDX-License-Identifier: Apache-2.0
#
# Generated via:
#   https://github.com/mesonbuild/meson/tree/master/mesonbuild/convert
#
# Submit patches, do not hand-edit."""

LICENSE_BLOCK_TEMPLATE = """\
package(
    default_applicable_licenses = ["//:{root_license_name}"],
    default_visibility = ["//visibility:public"],
)"""

ROOT_LICENSE_TEMPLATE = """\
license(
    name = "{license_name}",
    license_kinds = [
{license_kinds}
    ],
)"""

BAZEL_ATTR_MAP = {
    ConvertAttr.NAME: "name",
    ConvertAttr.SRCS: "srcs",
    ConvertAttr.INCLUDES: "export_include_dirs",
    ConvertAttr.RUSTFLAGS: "rustc_flags",
    ConvertAttr.OUT: "outs",
    ConvertAttr.TOOLS: "tools",
    ConvertAttr.PYTHON_MAIN: "main",
    ConvertAttr.RUST_CRATE_NAME: "crate_name",
    ConvertAttr.RUST_EDITION: "edition",
    ConvertAttr.LDFLAGS: "linkopts",
    ConvertAttr.BAZEL_DEPS: "deps",
    ConvertAttr.BAZEL_FLAGS: "flags",
    ConvertAttr.BAZEL_HDRS: "hdrs",
}


BAZEL_MODULE_MAP = {
    ConvertTargetType.FILEGROUP: "filegroup",
    ConvertTargetType.PYTHON_TARGET: "py_binary",
    ConvertTargetType.CUSTOM_TARGET: "meson_genrule",
    ConvertTargetType.INCLUDE_DIRECTORY: "meson_cc_headers",
    ConvertTargetType.FLAG: "meson_cc_flags",
    ConvertTargetType.RUST_FLAG: "meson_rust_flags",
    ConvertTargetType.STATIC_LIBRARY: "meson_cc_library",
    ConvertTargetType.SHARED_LIBRARY: "meson_cc_library",
    ConvertTargetType.RUST_LIBRARY: "rust_library",
    ConvertTargetType.RUST_FFI_STATIC: "rust_static_library",
    ConvertTargetType.RUST_FFI_SHARED: "rust_shared_library",
}


BAZEL_LOAD_MAP = {
    ConvertTargetType.PYTHON_TARGET: (
        "@rules_python//python:py_binary.bzl",
        "py_binary",
    ),
    ConvertTargetType.CUSTOM_TARGET: ("//bazel:meson_rules.bzl", "meson_genrule"),
    ConvertTargetType.STATIC_LIBRARY: ("//bazel:meson_rules.bzl", "meson_cc_library"),
    ConvertTargetType.SHARED_LIBRARY: ("//bazel:meson_rules.bzl", "meson_cc_library"),
    ConvertTargetType.RUST_LIBRARY: ("@rules_rust//rust:defs.bzl", "rust_library"),
    ConvertTargetType.RUST_FFI_STATIC: (
        "@rules_rust//rust:defs.bzl",
        "rust_static_library",
    ),
    ConvertTargetType.RUST_FFI_SHARED: (
        "@rules_rust//rust:defs.bzl",
        "rust_shared_library",
    ),
    ConvertTargetType.INCLUDE_DIRECTORY: (
        "//bazel:meson_rules.bzl",
        "meson_cc_headers",
    ),
    ConvertTargetType.FLAG: ("//bazel:meson_rules.bzl", "meson_cc_flags"),
    ConvertTargetType.RUST_FLAG: ("//bazel:rust_rules.bzl", "meson_rust_flags"),
}


def _emit_python_aliases(python_libs: T.Dict[str, str]) -> str:
    content = ""
    for dep in sorted(list(python_libs)):
        content += "alias(\n"
        content += f'    name = "{dep}",\n'
        content += f'    actual = "@meson_python_deps//{dep}",\n'
        content += '    visibility = ["//visibility:public"],\n'
        content += ")\n\n"
    return content


class BazelEmitterBackend(ConvertEmitterBackend):
    def emit_begin(self, output_dir: str, state_tracker: ConvertStateTracker) -> None:
        _emit_module_bazel(output_dir, state_tracker, self.get_copyright_header({}))

    def get_attr_map(self) -> T.Dict[ConvertAttr, str]:
        return BAZEL_ATTR_MAP

    def get_module_map(self) -> T.Dict[ConvertTargetType, str]:
        return BAZEL_MODULE_MAP

    def get_attr_separator(self) -> str:
        return " ="

    def get_opening_brace(self) -> str:
        return "("

    def get_closing_brace(self) -> str:
        return ")"

    def get_build_file_name(self) -> str:
        return "BUILD.bazel"

    def get_copyright_header(self, copyright_info: T.Dict[str, T.Any]) -> str:
        return COPYRIGHT_HEADER_TEMPLATE

    def get_license_block(
        self, copyright_info: T.Dict[str, T.Any], is_root: bool
    ) -> str:
        if "license_name" in copyright_info:
            root_license_name = copyright_info["license_name"]
            content = ""
            if is_root:
                license_kinds = "\n".join(
                    [
                        f'        "@rules_license//licenses/spdx:{lic}",'
                        for lic in copyright_info.get("licenses", [])
                    ]
                )
                content += "\n\n" + ROOT_LICENSE_TEMPLATE.format(
                    license_name=root_license_name,
                    license_kinds=license_kinds,
                )
            content += "\n\n" + LICENSE_BLOCK_TEMPLATE.format(
                root_license_name=root_license_name
            )
            return content
        return ""

    def emit_extra_root_info(self, state_tracker: ConvertStateTracker) -> str:
        content = ""
        python_libs = state_tracker.project_config.dependencies.python_libraries
        if python_libs:
            content += _emit_python_aliases(python_libs)
        return content

    def emit_module_load_info(
        self, targets: T.List[ConvertTarget], is_root: bool
    ) -> str:
        file_to_rules = defaultdict(set)
        if is_root:
            file_to_rules["@rules_license//rules:license.bzl"].add("license")

        for t in targets:
            if t.target_type in BAZEL_LOAD_MAP:
                load_file, rule = BAZEL_LOAD_MAP[t.target_type]
                file_to_rules[load_file].add(rule)

        if not file_to_rules:
            return ""

        load_lines = []
        for load_file in sorted(file_to_rules.keys()):
            rules = sorted(list(file_to_rules[load_file]))
            rules_str = ", ".join([f'"{r}"' for r in rules])
            load_lines.append(f'load("{load_file}", {rules_str})')

        return "\n".join(load_lines) + "\n\n"

    def emit_special_target_info(self, target: ConvertTarget) -> str:
        from mesonbuild.convert.build_systems.target import ConvertCustomTarget

        if isinstance(target, ConvertCustomTarget):
            return f'    cmd = "{getattr(target, "cmd", "")}",\n'
        return ""

    def format_conditionals(self, indent: int, node: ConvertAttrNode) -> str:
        content_str = ""
        select_nodes = node.get_select_nodes()
        if not select_nodes:
            return content_str

        select_node = select_nodes[0]
        content_str += "select({\n"

        value_indent = indent + COMMON_INDENT
        indent_str = " " * value_indent
        for select_values, attribute_values in select_node.select_tuples:
            key = ":".join(select_values)
            if key == "default":
                key = "//conditions:default"
            content_str += f'{indent_str}"{key}": {generic_emit_attribute_values(value_indent, attribute_values)},\n'

        content_str += " " * indent + "})"
        return content_str
