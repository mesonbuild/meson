# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Red Hat, Inc

from __future__ import annotations

import typing as T
import argparse
import os
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('command')
parser.add_argument('--build-dir', default='')
parser.add_argument('-i', '--input', nargs='+', default=[])
parser.add_argument('-o', '--output', default='')

def all_ifaces(build_dir: str, inputs: T.List[str], output: str) -> int:
    output = os.path.join(build_dir, output)
    with open(output, 'w', encoding='utf-8') as out_file:
        with tempfile.NamedTemporaryFile(mode='w+t', delete=True, prefix="selinux-m4-iferror", encoding='utf-8') as tmp_file:
            tmp_file.write("ifdef(`__if_error',`m4exit(1)')\n")
            m4_cmd = ['m4'] + inputs + [tmp_file.name]
            try:
                result = subprocess.run(m4_cmd, check=True, stdout=subprocess.PIPE, encoding='utf-8')
                out_file.write('divert(-1)\n')
                out_file.write(result.stdout)
                out_file.write('divert\n')
            except subprocess.CalledProcessError as e:
                print(f"Error executing m4: {e}")
                return 1
    return 0

def run(args: T.List[str]) -> int:
    options = parser.parse_args(args)
    command = options.command
    build_dir = os.environ.get('MESON_BUILD_ROOT', os.getcwd())
    if options.build_dir:
        build_dir = options.build_dir

    if command == 'all-ifaces':
        return all_ifaces(build_dir, options.input, options.output)
    else:
        print('Unknown subcommand.')
        return 1
