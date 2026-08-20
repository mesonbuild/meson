# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson development team

from __future__ import annotations

import os
import typing as T

from .run_tool import run_tool_on_targets, run_with_buffered_output
from .. import build, mlog
from ..mesonlib import MachineChoice

# Languages for which syntax-only checking is supported.
SYNTAX_CHECK_LANGS = frozenset({'c', 'cpp', 'objc', 'objcpp'})

# Compile-only flags that should be stripped when doing syntax-only checks,
# since -fsyntax-only / /Zs replace them.
COMPILE_ONLY_FLAGS = {'-c', '/c'}


class SyntaxChecker:
    def __init__(self, build_data: build.Build) -> None:
        self.syntax_args: T.Dict[T.Tuple[str, str], T.List[str]] = {}
        self.warned: T.Set[T.Tuple[str, str]] = set()

        for machine in MachineChoice:
            compilers = build_data.environment.coredata.compilers[machine]
            machine_name = machine.get_lower_case_name()
            for lang, compiler in compilers.items():
                if lang not in SYNTAX_CHECK_LANGS:
                    continue
                syntax_args = compiler.get_syntax_only_args()
                if syntax_args is not None:
                    self.syntax_args[(machine_name, lang)] = syntax_args

    def __call__(self, target: T.Dict[str, T.Any]) -> T.Iterable[T.Coroutine[None, None, int]]:
        for src_block in target['target_sources']:
            if 'compiler' not in src_block:
                continue
            lang = src_block['language']
            if lang not in SYNTAX_CHECK_LANGS:
                continue

            machine = src_block['machine']
            key = (machine, lang)
            syntax_args = self.syntax_args.get(key)
            if syntax_args is None:
                if key not in self.warned:
                    self.warned.add(key)
                    mlog.warning(f'No syntax-only support for {lang} on {machine} machine; skipping')
                continue

            compiler_exe = src_block['compiler']
            parameters = [p for p in src_block['parameters'] if p not in COMPILE_ONLY_FLAGS]

            sources = src_block['sources'] + src_block.get('generated_sources', [])
            for source in sources:
                cmdlist = list(compiler_exe) + parameters + list(syntax_args) + [source]
                yield run_with_buffered_output(cmdlist)


def run(args: T.List[str]) -> int:
    os.chdir(args[0])
    build_data = build.load(os.getcwd())
    return run_tool_on_targets(SyntaxChecker(build_data))
