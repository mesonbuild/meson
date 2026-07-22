#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Authors

from __future__ import annotations
import typing as T
import operator
import json

from mesonbuild.hermetic.common_compiler import PlatformsToml

if T.TYPE_CHECKING:
    from mesonbuild.checkplatforms.checker import CheckPlatformOptions


MAX_LINE_LENGTH = 80
INDENT_STRING = '    '


def _sanitize_cmd(options: CheckPlatformOptions) -> str:
    pdir = (options.project_dir or '').rstrip('/')

    def _clean_path(path: str) -> str:
        if pdir and pdir in path:
            return path.replace(pdir, '${PROJECT_DIR}')
        return path

    parts = ['check-platforms']
    if options.config:
        parts.append(f'--config={_clean_path(options.config)}')
    if options.platforms:
        parts.append(f'--platforms={_clean_path(options.platforms)}')
    if options.dependencies:
        parts.append(f'--dependencies={_clean_path(options.dependencies)}')
    if options.project_dir:
        parts.append('--project-dir=${PROJECT_DIR}')

    return ' '.join(parts)


def _emit_array(name: str, values: T.List[str]) -> T.List[str]:
    lines = [f'{name} = [']
    current_line_items: T.List[str] = []
    for value in values:
        item_str = f'{json.dumps(value)},'
        if not current_line_items:
            current_line_items.append(item_str)
        else:
            candidate = f'{INDENT_STRING}{" ".join(current_line_items)} {item_str}'
            if len(candidate) > MAX_LINE_LENGTH:
                lines.append(f'{INDENT_STRING}{" ".join(current_line_items)}')
                current_line_items = [item_str]
            else:
                current_line_items.append(item_str)

    if current_line_items:
        lines.append(f'{INDENT_STRING}{" ".join(current_line_items)}')

    lines.append(']')
    return lines


class PlatformEmitter:
    def __init__(self, platforms_toml: PlatformsToml, args: CheckPlatformOptions):
        self.platforms_toml = platforms_toml
        self.args = args

    def emit(self, output_filename: str) -> None:
        """
        Serializes the collected platform data into a TOML file.
        """
        output = []
        output.append('# Copyright 2026 The Magma GPU Project')
        output.append('# SPDX-License-Identifier: MIT')
        output.append(f'\n# Generated via meson {_sanitize_cmd(self.args)}\n')

        all_wraps = {w['name']: w for w in self.platforms_toml.get('wrap', []) if 'name' in w}
        all_toolchains = {
            tc['name']: tc for tc in self.platforms_toml.get('toolchain', []) if 'name' in tc
        }
        all_platforms = self.platforms_toml.get('platform', [])

        for name, wrap in sorted(all_wraps.items(), key=operator.itemgetter(0)):
            output.append('[[wrap]]')
            output.append(f'name = "{wrap["name"]}"')
            output.append(f'source_url = "{wrap.get("source_url", "")}"')
            output.append(f'source_filename = "{wrap.get("source_filename", "")}"')
            output.append(f'source_hash = "{wrap.get("source_hash", "")}"')
            output.append('')

        for name, toolchain in sorted(all_toolchains.items(), key=operator.itemgetter(0)):
            output.append('[[toolchain]]')
            output.append(f'name = "{toolchain["name"]}"')
            output.append(f'wrap_name = "{toolchain.get("wrap_name", "")}"')
            for b_name, b_val in sorted(toolchain.items()):
                if b_name in {'name', 'wrap_name'}:
                    continue
                else:
                    output.append(f'{b_name} = {json.dumps(b_val)}')
            output.append('')

        for i, plat in enumerate(all_platforms):
            output.append('[[platform]]')
            output.append(f'name = "{plat["name"]}"')

            machine_info = plat.get('machine_info')
            if machine_info:
                output.append('\n[platform.machine_info]')
                output.append(f'cpu_family = "{machine_info["cpu_family"]}"')
                output.append(f'cpu = "{machine_info["cpu"]}"')
                output.append(f'system = "{machine_info["system"]}"')
                output.append(f'endian = "{machine_info["endian"]}"')

            for lang in ['c', 'cpp', 'rust']:
                compiler = T.cast(T.Dict[str, T.Any], plat.get(lang))
                if compiler:
                    output.append(f'\n[platform.{lang}]')
                    output.append(f'compiler_id = "{compiler.get("compiler_id", "")}"')
                    output.append(f'linker_id = "{compiler.get("linker_id", "")}"')
                    output.append(f'version = "{compiler.get("version", "")}"')
                    if compiler.get('standards'):
                        output.extend(_emit_array('standards', compiler['standards']))
                    if compiler.get('base_options'):
                        output.extend(_emit_array('base_options', sorted(compiler['base_options'])))
                    if compiler.get('toolchain'):
                        output.append(f'toolchain = "{compiler["toolchain"]}"')
                    if compiler.get('sysroot'):
                        sr = compiler['sysroot']
                        output.append(
                            f'sysroot = {{ wrap_name = {json.dumps(sr["wrap_name"])}, path = {json.dumps(sr["path"])} }}'
                        )

                    if compiler.get('compiles', {}).get('fails'):
                        output.append(f'\n[platform.{lang}.compiles.fails]')
                        for item in sorted(compiler['compiles']['fails'].keys()):
                            output.append(f'{json.dumps(item)} = true')

                    if compiler.get('links', {}).get('fails'):
                        output.append(f'\n[platform.{lang}.links.fails]')
                        for item in sorted(compiler['links']['fails'].keys()):
                            output.append(f'{json.dumps(item)} = true')

                    if compiler.get('check_header', {}).get('fails'):
                        output.append(f'\n[platform.{lang}.check_header.fails]')
                        for item in sorted(compiler['check_header']['fails'].keys()):
                            output.append(f'{json.dumps(item)} = true')

                    if compiler.get('has_header_symbol', {}).get('fails'):
                        output.append(f'\n[platform.{lang}.has_header_symbol.fails]')
                        for header, symbols in sorted(compiler['has_header_symbol']['fails'].items()):  # fmt: skip
                            symbol_list = (
                                sorted(symbols.keys())
                                if isinstance(symbols, dict)
                                else sorted(symbols)
                            )
                            symbol_str = ', '.join([f'{s} = true' for s in symbol_list])
                            output.append(f'{json.dumps(header)} = {{ {symbol_str} }}')

                    if compiler.get('has_function', {}).get('fails'):
                        output.append(f'\n[platform.{lang}.has_function.fails]')
                        for func in sorted(compiler['has_function']['fails'].keys()):
                            output.append(f'{func} = true')

                    if compiler.get('has_function_attribute', {}).get('fails'):
                        output.append(f'\n[platform.{lang}.has_function_attribute.fails]')
                        for attr in sorted(compiler['has_function_attribute']['fails'].keys()):
                            output.append(f'{json.dumps(attr)} = true')

                    if compiler.get('has_member', {}).get('fails'):
                        output.append(f'\n[platform.{lang}.has_member.fails]')
                        for struct, members in sorted(compiler['has_member']['fails'].items()):
                            member_list = (
                                sorted(members.keys())
                                if isinstance(members, dict)
                                else sorted(members)
                            )
                            member_str = ', '.join([f'{m} = true' for m in member_list])
                            output.append(f'{json.dumps(struct)} = {{ {member_str} }}')

                    if compiler.get('supported_arguments', {}).get('fails', {}).get('args'):
                        output.append(f'\n[platform.{lang}.supported_arguments.fails]')
                        output.extend(
                            _emit_array(
                                'args', sorted(compiler['supported_arguments']['fails']['args'])
                            )
                        )

                    if compiler.get('supported_link_arguments', {}).get('fails', {}).get('args'):
                        output.append(f'\n[platform.{lang}.supported_link_arguments.fails]')
                        output.extend(
                            _emit_array(
                                'args',
                                sorted(compiler['supported_link_arguments']['fails']['args']),
                            )
                        )

                    if compiler.get('sizeof', {}).get('sizes'):
                        output.append(f'\n[platform.{lang}.sizeof.sizes]')
                        for typename, size in sorted(compiler['sizeof']['sizes'].items()):
                            output.append(f'{json.dumps(typename)} = {size}')

                    if compiler.get('alignment', {}).get('aligns'):
                        output.append(f'\n[platform.{lang}.alignment.aligns]')
                        for typename, align in sorted(compiler['alignment']['aligns'].items()):
                            output.append(f'{json.dumps(typename)} = {align}')

            if i < len(all_platforms) - 1:
                output.append('')

        with open(output_filename, 'w', encoding='utf-8') as f:
            for line in output:
                f.write(line)
                f.write('\n')
