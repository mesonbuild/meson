# SPDX-License-Identifier: Apache-2.0
# Copyright © 2023-2025 Intel Corporation

"""Abstractions for the Elbrus family of compilers."""

from __future__ import annotations

import functools
import os
import re
import subprocess
import typing as T

from ...mesonlib import Popen_safe
from ...options import OptionKey
from .gnu import GnuLikeCompiler, gnu_optimization_args

if T.TYPE_CHECKING:
    from ...build import BuildTarget


class ElbrusCompiler(GnuLikeCompiler):
    # Elbrus compiler is nearly like GCC, but does not support
    # PCH, LTO, sanitizers and color output as of version 1.21.x.

    id = 'lcc'

    def __init__(self) -> None:
        super().__init__()
        self.base_options = {OptionKey(o) for o in ['b_pgo', 'b_coverage', 'b_ndebug', 'b_staticpic', 'b_lundef', 'b_asneeded']}
        default_warn_args = ['-Wall']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic'],
                          'everything': default_warn_args + ['-Wextra', '-Wpedantic']}

    # FIXME: use _build_wrapper to call this so that linker flags from the env
    # get applied
    def get_library_dirs(self, elf_class: int | None = None) -> list[str]:
        os_env = os.environ.copy()
        os_env['LC_ALL'] = 'C'
        stdo = Popen_safe(self.get_exelist(ccache=False) + ['--print-search-dirs'], env=os_env)[1]
        for line in stdo.split('\n'):
            if line.startswith('libraries:'):
                # lcc does not include '=' in --print-search-dirs output. Also it could show nonexistent dirs.
                libstr = line.split(' ', 1)[1]
                return [os.path.realpath(p) for p in libstr.split(':') if os.path.exists(p)]
        return []

    def get_program_dirs(self) -> list[str]:
        os_env = os.environ.copy()
        os_env['LC_ALL'] = 'C'
        stdo = Popen_safe(self.get_exelist(ccache=False) + ['--print-search-dirs'], env=os_env)[1]
        for line in stdo.split('\n'):
            if line.startswith('programs:'):
                # lcc does not include '=' in --print-search-dirs output.
                libstr = line.split(' ', 1)[1]
                return [os.path.realpath(p) for p in libstr.split(':')]
        return []

    @functools.cache
    def get_default_include_dirs(self) -> list[str]:
        os_env = os.environ.copy()
        os_env['LC_ALL'] = 'C'
        p = subprocess.Popen(self.get_exelist(ccache=False) + ['-xc', '-E', '-v', '-'], env=os_env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stderr = p.stderr.read().decode('utf-8', errors='replace')
        includes: list[str] = []
        for line in stderr.split('\n'):
            if line.lstrip().startswith('--sys_include'):
                includes.append(re.sub(r'\s*\\$', '', re.sub(r'^\s*--sys_include\s*', '', line)))
        return includes

    def get_optimization_args(self, optimization_level: str) -> list[str]:
        return gnu_optimization_args[optimization_level]

    def get_prelink_args(self, prelink_name: str, obj_list: list[str]) -> tuple[list[str], list[str]]:
        return [prelink_name], ['-r', '-nodefaultlibs', '-nostartfiles', '-o', prelink_name] + obj_list

    def get_pch_suffix(self) -> str:
        # Actually it's not supported for now, but probably will be supported in future
        return 'pch'

    def get_option_std_args(self, target: BuildTarget, subproject: str | None = None) -> list[str]:
        args: list[str] = []
        key = OptionKey(f'{self.language}_std', subproject=subproject, machine=self.for_machine)
        if target:
            std = self.environment.coredata.get_option_for_target(target, key)
        else:
            std = self.environment.coredata.optstore.get_value_for(key)
        assert isinstance(std, str)
        if std != 'none':
            args.append('-std=' + std)
        return args

    def openmp_flags(self) -> list[str]:
        return ['-fopenmp']

    @classmethod
    def use_linker_args(cls, linker: str, version: str) -> list[str]:
        return []
