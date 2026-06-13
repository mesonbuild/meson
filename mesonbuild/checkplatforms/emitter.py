#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Authors

from __future__ import annotations
import typing as T
import argparse
import sys
import operator

from .defs import Platform


class PlatformEmitter:
    def __init__(self, platforms: T.List[Platform], args: argparse.Namespace):
        self.platforms = platforms
        self.args = args

    def emit(self, output_filename: str) -> None:
        """
        Serializes the collected platform data into a TOML file.
        """
        output = []
        cmd_args = sys.argv[1:]
        output.append('# Copyright 2026 The Meson Development Team')
        output.append('# SPDX-License-Identifier-Apache-2.0')
        output.append(f'\n# Generated via meson {" ".join(cmd_args)}\n')

        if not self.platforms:
            return

        # Collect all wraps and toolchains
        all_wraps = {}
        all_toolchains = {}
        for p in self.platforms:
            all_wraps.update(p.wraps)
            all_toolchains.update(p.toolchains)

        for name, wrap in sorted(all_wraps.items(), key=operator.itemgetter(0)):
            output.append('[[wrap]]')
            output.append(f'name = "{wrap.name}"')
            output.append(f'source_url = "{wrap.source_url}"')
            output.append(f'source_filename = "{wrap.source_filename}"')
            output.append(f'source_hash = "{wrap.source_hash}"')
            output.append('')

        for name, toolchain in sorted(all_toolchains.items(), key=operator.itemgetter(0)):  # fmt: skip
            output.append('[[toolchain]]')
            output.append(f'name = "{toolchain.name}"')
            output.append(f'wrap_name = "{toolchain.wrap_name}"')
            for b_name, b_path in sorted(toolchain.binaries.items()):
                output.append(f'{b_name} = "{b_path}"')
            output.append('')

        for i, platform in enumerate(self.platforms):
            output.append('[[platform]]')
            output.append(f'name = "{platform.name}"')
            if platform.toolchain:
                output.append(f'toolchain = "{platform.toolchain}"')
            if platform.sysroot:
                output.append('\n[platform.sysroot]')
                output.append(f'wrap_name = "{platform.sysroot.wrap_name}"')
                output.append(f'path = "{platform.sysroot.path}"')

            output.append('\n[platform.host_machine]')
            output.append(f'cpu_family = "{platform.host_machine.cpu_family}"')
            output.append(f'cpu = "{platform.host_machine.cpu}"')
            output.append(f'system = "{platform.host_machine.system}"')
            output.append(f'endian = "{platform.host_machine.endian}"')

            output.append('\n[platform.c]')
            output.append(f'compiler_id = "{platform.c.compiler_id}"')
            output.append(f'linker_id = "{platform.c.linker_id}"')
            output.append(f'version = "{platform.c.version}"')

            output.append('\n[platform.cpp]')
            output.append(f'compiler_id = "{platform.cpp.compiler_id}"')
            output.append(f'linker_id = "{platform.cpp.linker_id}"')
            output.append(f'version = "{platform.cpp.version}"')

            if platform.rust:
                output.append('\n[platform.rust]')
                output.append(f'compiler_id = "{platform.rust.compiler_id}"')
                output.append(f'linker_id = "{platform.rust.linker_id}"')
                output.append(f'version = "{platform.rust.version}"')

            if platform.c_compiles_fails:
                output.append('\n[platform.c.compiles.fails]')
                for item in platform.c_compiles_fails:
                    output.append(f'"{item}" = true')

            if platform.c_links_fails:
                output.append('\n[platform.c.links.fails]')
                for item in platform.c_links_fails:
                    output.append(f'"{item}" = true')

            if platform.c_headers_fails:
                output.append('\n[platform.c.check_header.fails]')
                for item in platform.c_headers_fails:
                    output.append(f'"{item}" = true')

            if platform.c_header_symbols_fails:
                output.append('\n[platform.c.has_header_symbol.fails]')
                for header, symbols in platform.c_header_symbols_fails.items():
                    symbol_str = ', '.join([f'{s} = true' for s in symbols])
                    output.append(f'"{header}" = {{ {symbol_str} }}')

            if platform.c_functions_fails:
                output.append('\n[platform.c.has_function.fails]')
                for func in platform.c_functions_fails:
                    output.append(f'{func} = true')

            if platform.c_function_attributes_fails:
                output.append('\n[platform.c.has_function_attribute.fails]')
                for attr in platform.c_function_attributes_fails:
                    output.append(f'"{attr}" = true')
            if platform.c_members_fails:
                output.append('\n[platform.c.has_member.fails]')
                for struct, members in platform.c_members_fails.items():
                    member_str = ', '.join([f'{m} = true' for m in members])
                    output.append(f'"{struct}" = {{ {member_str} }}')

            if platform.c_supported_arguments_fails:
                output.append('\n[platform.c.supported_arguments.fails]')
                output.append('args = [')
                for arg in platform.c_supported_arguments_fails:
                    output.append(f'    "{arg}",')
                output.append(']')

            if platform.c_supported_link_arguments_fails:
                output.append('\n[platform.c.supported_link_arguments.fails]')
                output.append('args = [')
                for arg in platform.c_supported_link_arguments_fails:
                    output.append(f'    "{arg}",')
                output.append(']')
            if platform.cpp_links_fails:
                output.append('\n[platform.cpp.links.fails]')
                for item in sorted(platform.cpp_links_fails):
                    output.append(f'"{item}" = true')
            if platform.cpp_supported_arguments_fails:
                output.append('\n[platform.cpp.supported_arguments.fails]')
                output.append('args = [')
                for arg in platform.cpp_supported_arguments_fails:
                    output.append(f'    "{arg}",')
                output.append(']')

            if i < len(self.platforms) - 1:
                output.append('')

        with open(output_filename, 'w', encoding='utf-8') as f:
            for line in output:
                f.write(line)
                f.write('\n')
