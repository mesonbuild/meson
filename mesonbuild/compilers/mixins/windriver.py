# SPDX-License-Identifier: Apache-2.0
# Copyright 2012-2023 The Meson development team
from __future__ import annotations

"""Representations specific to the TASKING embedded C/C++ compiler family."""

import os
import typing as T
import functools
import enum

from ...mesonlib import EnvironmentException
from ...options import OptionKey
from ... import options

if T.TYPE_CHECKING:
    from ...compilers.compilers import Compiler
    from ...mesonlib import File, FileOrString
else:
    # This is a bit clever, for mypy we pretend that these mixins descend from
    # Compiler, so we get all of the methods and attributes defined for us, but
    # for runtime we make them descend from object (which all classes normally
    # do). This gives us DRYer type checking, with no runtime impact
    Compiler = object

class DiabCompilerMixin(Compiler):
    """The Wind River Diab compiler suite for bare-metal PowerPC

    The suite entry program _dplus_ handles c++, c and assembler sources, and linking.

    This object should have a DiabLinker instance in its `linker` member.

    Archiving can be done with DiabArchiver.
    """
    id = "diab"

    # Target processor
    processor = [
        "PPC", # Generic PowerPC
        "MGT5200",
        "PPC401",
        "PPC403",
        "PPC405",
        "PPC440",
        "PPC440GX",
        "PPC505",
        "PPC509",
        "PPC553",
        "PPC555",
        "PPC561",
        "PPC565",
        "PPC601",
        "PPC602",
        "PPC603",
        "PPC603e",
        "PPC604",
        "PPC740",
        "PPC745",
        "PPC750",
        "PPC755",
        "PPC801",
        "PPC821",
        "PPC823",
        "PPC850",
        "PPC852",
        "PPC855",
        "PPC857",
        "PPC859",
        "PPC860",
        "PPC862",
        "PPC866",
        "PPC970",
        "PPCE500",
        "PPC5500",
        "PPC5534",
        "PPC5534V",
        "PPC5534N",
        "PPC5553",
        "PPC5554",
        "PPC7400",
        "PPC7410",
        "PPC7440",
        "PPC7441",
        "PPC7445",
        "PPC7447",
        "PPC7450",
        "PPC7451",
        "PPC7455",
        "PPC7457",
        "PPC8240",
        "PPC8241",
        "PPC8245",
        "PPC8250",
        "PPC8255",
        "PPC8260",
        "PPC8264",
        "PPC8265",
        "PPC8266",
        "PPC8270",
        "PPC8275",
        "PPC8280",
        "PPC8540",
        "PPC8541",
        "PPC8543",
        "PPC8545",
        "PPC8547",
        "PPC8548",
        "PPC8560",
        "POWER",
    ]

    # Object format
    object_format = {
        'EABI': 'E', # ELF using EABI conventions
        'Motorola': 'C', # Motorola compressible ELF
        'no-small-section': 'F', # global and static scalar variables may be placed in a local data area
        'little-endian': 'L', # little-endian
        'COFF': 'D' # COFF using AIX conventions
    }

    # Floating point support
    floating_point = {
        'Hard': 'H', # Hardware floating point
        'HardSingle': 'F', # Single precision uses hardware, double precision uses software emulation
        'HardSingleOnly': 'G', # Single precision uses hardware, double precision is mapped to single precision
        'Vector': 'V', # Vector floating point for AltiVec with the PPC7400 or PPC970 processor only
        'Soft': 'S', # Software floating point emulation provided with the compiler
        'None': 'N' # No floating point support
    }

    # Basic operating system functions
    os_impl = {
        'stdinout': 'simple', # Simple character input/output for stdin and stdout only
        'ramdisk': 'cross' # Ram-disk file input/output
    }

    optimization_args: T.Dict[str, T.List[str]] = {
        "plain": [],
        "0": [],
        "g": ["-O", "-Xno-optimized-debug"],
        "1": ["-O"],
        "2": ["-O", "-Xinline=40"],
        "3": ["XO"],
        "s": ["-Xsize-opt"],
    }

    class Prefix(enum.Enum):
        CPP = "cpp"
        CXX = "c++"
        C = "c"
        AS = "as"
        LD = "ld"

    def __init__(self) -> None:
        self.base_options = {
            OptionKey(o) for o in ['b_pch', 'b_lto', 'b_pgo', 'b_coverage',
                                   'b_ndebug', 'b_staticpic', 'b_pie']}
        if not (self.info.is_windows() or self.info.is_cygwin() or self.info.is_openbsd()):
            self.base_options.add(OptionKey('b_lundef'))
        if not self.info.is_windows() or self.info.is_cygwin():
            self.base_options.add(OptionKey('b_asneeded'))
        if not self.info.is_hurd():
            self.base_options.add(OptionKey('b_sanitize'))

        self.can_compile_suffixes.add('s')

    def _apply_prefix(self, prefix: Prefix, arg: T.Union[str, T.List[str]]) -> T.List[str]:
        """Prefix commands to redirect to compiler suite sub programs"""
        args = [arg] if isinstance(arg, str) else arg
        return [f"-W:{prefix.value}:,{arg}" for arg in args]

    def get_include_args(self, path: str, is_system: bool) -> T.List[str]:
        return super().get_include_args(path, is_system) + self._apply_prefix(self.Prefix.AS, f"-I{path}")

    def get_warn_args(self, level: str) -> T.List[str]:
        """No such levels"""
        return []

    def get_werror_args(self) -> T.List[str]:
        return ["-Xstop-on-warning"]

    def get_optimization_args(self, optimization_level: str) -> T.List[str]:
        return self.optimization_args[optimization_level]

    def get_debug_args(self, is_debug: bool) -> T.List[str]:
        return ['-g'] if is_debug else []

    def _create_string_option(self, key: str, description: str) -> T.Tuple[options.OptionKey, options.UserStringArrayOption]:
        return self.form_compileropt_key(key), options.UserStringArrayOption(key, description, [])

    def _create_boolean_option(self, key: str, description: str, default: bool) -> T.Tuple[options.OptionKey, options.UserBooleanOption]:
        return self.form_compileropt_key(key), options.UserBooleanOption(key, description, default)

    def _create_combo_option(self, key: str, description: str, choices: T.Iterable[str]) -> T.Tuple[options.OptionKey, options.UserComboOption]:
        choices = list(choices)
        return self.form_compileropt_key(key), options.UserComboOption(key, description, choices[0], choices=choices)

    def get_options(self) -> 'MutableKeyedOptionDictType':
        opts = super().get_options()
        key = self.form_compileropt_key("std")
        std_opt = opts[key]
        assert isinstance(std_opt, options.UserStdOption), "for mypy"
        std_opt.set_versions(["c++98"])
        opts.update([
            self._create_boolean_option('eh', 'C++ exception handling', True),
            self._create_boolean_option('rtti', 'RTTI enabled', True),
            self._create_boolean_option('lic_wait', 'Enable waiting for available license', False),
            self._create_boolean_option('subprog_cmd', 'Print subprogram cmd lines with args as they are executed', False),
            self._create_boolean_option('map', 'Save linker memory map', False),
            self._create_combo_option('tgt_proc', "Target processor", self.processor),
            self._create_combo_option('tgt_fmt', "Target object format", self.object_format),
            self._create_combo_option('tgt_fp', "Target floating point processing", self.floating_point),
            self._create_combo_option('os_impl', "Basic operating system functions", self.os_impl),
        ])
        return opts

    def _get_option_common_args(self, target: 'BuildTarget', env: 'Environment', subproject: T.Optional[str] = None) -> T.List[str]:
        args: T.List[str] = []

        if self.get_compileropt_value('lic_wait', env, target, subproject):
            args.append('-Xlicense-wait')
        if self.get_compileropt_value('subprog_cmd', env, target, subproject):
            args.append('-#')

        tgt_fmt = self.get_compileropt_value("tgt_fmt", env, target, subproject)
        assert isinstance(tgt_fmt, str)
        tgt_fp = self.get_compileropt_value("tgt_fp", env, target, subproject)
        assert isinstance(tgt_fp, str)

        args.append(
            "-t{0}{1}{2}:simple".format(
                self.get_compileropt_value("tgt_proc", env, target, subproject),
                self.object_format[tgt_fmt],
                self.floating_point[tgt_fp],
            )
        )

        return args

    def get_option_compile_args(self, target: 'BuildTarget', env: 'Environment', subproject: T.Optional[str] = None) -> T.List[str]:
        args = self._get_option_common_args(target, env, subproject)

        if not self.get_compileropt_value('eh', env, target, subproject):
            args += self._apply_prefix(self.Prefix.CXX, '-Xexceptions-off')
        if not self.get_compileropt_value('rtti', env, target, subproject):
            args += self._apply_prefix(self.Prefix.CXX, '-Xrtti-off')

        return args

    def get_option_std_args(self, target: BuildTarget, env: Environment, subproject: T.Optional[str] = None) -> T.List[str]:
        std = self.get_compileropt_value('std', env, target, subproject)
        assert isinstance(std, str)
        if std == 'c++98':
            return self._apply_prefix(self.Prefix.CXX, '-Xstrict-ansi')
        else:
            return []

    def get_option_link_args(self, target: 'BuildTarget', env: 'Environment', subproject: T.Optional[str] = None) -> T.List[str]:
        args = self._get_option_common_args(target, env, subproject)

        if self.get_compileropt_value('map', env, target, subproject):
            args += self.linker._apply_prefix(['-m2', '-Xunused-sections-list', '-Xcheck-overlapping', f'-@O={target.filename}.map'])

        return args

    def compute_parameters_with_absolute_paths(self, parameter_list: T.List[str], build_dir: str) -> T.List[str]:
        for idx, i in enumerate(parameter_list):
            if i[:2] == '-I' or i[:2] == '-L':
                parameter_list[idx] = i[:2] + os.path.normpath(os.path.join(build_dir, i[2:]))

        return parameter_list

    def get_always_args(self) -> T.List[str]:
        """Disable super's large-file-support"""
        return []

    def get_compiler_check_args(self, mode: CompileCheckMode) -> T.List[str]:
        return super(CPPCompiler, self).get_compiler_check_args(mode)
