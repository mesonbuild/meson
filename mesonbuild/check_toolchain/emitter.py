#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Authors

from __future__ import annotations
import typing as T
import argparse

from .defs import Toolchain


class ToolchainEmitter:

    def __init__(self, toolchains: T.List[Toolchain], args: argparse.Namespace):
        self.toolchains = toolchains
        self.args = args

    def emit(self, output_filename: str) -> None:
        """
        Serializes the collected toolchain data into a TOML file.

        This method takes the final list of `Toolchain` objects, each populated
        with data from the compiler checks, and writes them to a specified
        output file in TOML format. It handles the structured serialization of
        all toolchain properties, including host machine details, compiler
        versions, and the various lists of detected failures (e.g., unsupported
        functions, arguments, or headers), ensuring the output is well-formed
        and readable.
        """
        output = []
        output.append("# Copyright 2026 The Meson Development Team")
        output.append("# SPDX-License-Identifier-Apache-2.0\n")

        for i, toolchain in enumerate(self.toolchains):
            output.append("[[toolchain]]")
            output.append(f'name = "{toolchain.name}"')

            output.append("\n[toolchain.host_machine]")
            output.append(f'cpu_family = "{toolchain.host_machine.cpu_family}"')
            output.append(f'cpu = "{toolchain.host_machine.cpu}"')
            output.append(f'system = "{toolchain.host_machine.system}"')
            output.append(f'endian = "{toolchain.host_machine.endian}"')

            output.append("\n[toolchain.c]")
            output.append(f'compiler_id = "{toolchain.c.compiler_id}"')
            output.append(f'linker_id = "{toolchain.c.linker_id}"')
            output.append(f'version = "{toolchain.c.version}"')

            output.append("\n[toolchain.cpp]")
            output.append(f'compiler_id = "{toolchain.cpp.compiler_id}"')
            output.append(f'linker_id = "{toolchain.cpp.linker_id}"')
            output.append(f'version = "{toolchain.cpp.version}"')

            if toolchain.rust:
                output.append("\n[toolchain.rust]")
                output.append(f'compiler_id = "{toolchain.rust.compiler_id}"')
                output.append(f'linker_id = "{toolchain.rust.linker_id}"')
                output.append(f'version = "{toolchain.rust.version}"')

            if toolchain.c_compiles_fails:
                output.append("\n[toolchain.c.compiles.fails]")
                for item in toolchain.c_compiles_fails:
                    output.append(f'"{item}" = true')

            if toolchain.c_links_fails:
                output.append("\n[toolchain.c.links.fails]")
                for item in toolchain.c_links_fails:
                    output.append(f'"{item}" = true')

            if toolchain.c_headers_fails:
                output.append("\n[toolchain.c.check_header.fails]")
                for item in toolchain.c_headers_fails:
                    output.append(f'"{item}" = true')

            if toolchain.c_header_symbols_fails:
                output.append("\n[toolchain.c.has_header_symbol.fails]")
                for header, symbols in toolchain.c_header_symbols_fails.items():
                    symbol_str = ", ".join([f"{s} = true" for s in symbols])
                    output.append(f'"{header}" = {{ {symbol_str} }}')

            if toolchain.c_functions_fails:
                output.append("\n[toolchain.c.has_function.fails]")
                for func in toolchain.c_functions_fails:
                    output.append(f"{func} = true")

            if toolchain.c_function_attributes_fails:
                output.append("\n[toolchain.c.has_function_attribute.fails]")
                for attr in toolchain.c_function_attributes_fails:
                    output.append(f'"{attr}" = true')
            if toolchain.c_members_fails:
                output.append("\n[toolchain.c.has_member.fails]")
                for struct, members in toolchain.c_members_fails.items():
                    member_str = ", ".join([f"{m} = true" for m in members])
                    output.append(f'"{struct}" = {{ {member_str} }}')

            if toolchain.c_supported_arguments_fails:
                output.append("\n[toolchain.c.supported_arguments.fails]")
                output.append("args = [")
                for arg in toolchain.c_supported_arguments_fails:
                    output.append(f'    "{arg}",')
                output.append("]")

            if toolchain.c_supported_link_arguments_fails:
                output.append("\n[toolchain.c.supported_link_arguments.fails]")
                output.append("args = [")
                for arg in toolchain.c_supported_link_arguments_fails:
                    output.append(f'    "{arg}",')
                output.append("]")
            if toolchain.cpp_supported_arguments_fails:
                output.append("\n[toolchain.cpp.supported_arguments.fails]")
                output.append("args = [")
                for arg in toolchain.cpp_supported_arguments_fails:
                    output.append(f'    "{arg}",')
                output.append("]")

            if i < len(self.toolchains) - 1:
                output.append("")

        output_content = "\n".join(output)

        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(output_content)
