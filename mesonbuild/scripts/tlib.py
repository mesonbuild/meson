from __future__ import annotations

import argparse
import subprocess
import typing as T
import os
import tempfile

def _fix_args(args: T.List[str]) -> T.List[str]:
    cmd: T.List[str] = []
    for arg in args:
        if arg[0] == '@':
            with open(arg[1:], 'r', encoding='utf-8') as f:
                cmd += _fix_args([line.strip() for line in f.readlines()])
            continue
        if '/' in arg and arg[0] != '/':
            arg = os.path.normpath(arg)
        if arg.endswith('.res'):
            # Ignore .res objects in static linker
            continue

        cmd.append(arg)

    return cmd

def run(args: T.List[str]) -> int:
    parser = argparse.ArgumentParser()

    args = parser.parse_known_args(args)[1]

    tlib_exe = args[0]
    tlib_cmd = _fix_args(args[1:])

    with tempfile.NamedTemporaryFile('w', delete=False, encoding='utf-8') as rsp_file:
        try:
            rsp_file.writelines(arg + '\n' for arg in tlib_cmd)
            rsp_file.close()

            returncode = subprocess.call([tlib_exe, "/B", f'@{rsp_file.name}'])
        finally:
            os.unlink(rsp_file.name)

    return returncode
