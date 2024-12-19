# SPDX-License-Identifier: Apache-2.0
# Copyright 2024 The Meson development team

from __future__ import annotations
import argparse
import os
import sys
import typing as T

from .run_tool import run_tool_on_targets, run_with_buffered_output
from .. import build, mlog
from ..mesonlib import MachineChoice

if T.TYPE_CHECKING:
    from ..compilers.rust import RustCompiler

class Rustfmt:
    def __init__(self, rustfmt: T.List[str], args: T.List[str]):
        self.args = rustfmt + args
        self.done: T.Set[str] = set()

    def __call__(self, target: T.Dict[str, T.Any]) -> T.Iterable[T.Coroutine[T.Any, T.Any, int]]:
        for src_block in target['target_sources']:
            if src_block['language'] == 'rust':
                file = src_block['sources'][0]
                if file in self.done:
                    continue
                self.done.add(file)

                cmdlist = list(self.args)
                for arg in src_block['parameters']:
                    if arg.startswith('--color=') or arg.startswith('--edition='):
                        cmdlist.append(arg)

                cmdlist.append(src_block['sources'][0])
                yield run_with_buffered_output(cmdlist)

def run(args: T.List[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('builddir')
    options = parser.parse_args(args)

    os.chdir(options.builddir)
    build_data = build.load(os.getcwd())

    rustfmt: T.Optional[T.List[str]] = None
    for machine in MachineChoice:
        compilers = build_data.environment.coredata.compilers[machine]
        if 'rust' in compilers:
            compiler = T.cast('RustCompiler', compilers['rust'])
            rustfmt = compiler.get_rust_tool('rustfmt', build_data.environment, False)
            if rustfmt:
                break
    else:
        mlog.error('rustfmt not found')
        sys.exit(1)

    return run_tool_on_targets(Rustfmt(rustfmt, ['--check'] if options.check else []))
