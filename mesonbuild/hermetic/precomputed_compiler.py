#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import contextlib
import functools
import typing as T

from mesonbuild.arglist import CompilerArgs
from mesonbuild.environment import Environment
from mesonbuild.mesonlib import File, LibType, MachineChoice, version_compare
from mesonbuild.dependencies.base import Dependency
from mesonbuild.compilers.compilers import (
    Compiler,
    CompileCheckMode,
    CompileResult,
    clike_optimization_args,
)
from mesonbuild.compilers.rust import rust_optimization_args
from mesonbuild.linkers.linkers import DynamicLinker, GnuBFDDynamicLinker
from mesonbuild import options
from mesonbuild.options import OptionKey
from mesonbuild.hermetic.common_compiler import CompilerConfig

if T.TYPE_CHECKING:
    from mesonbuild.compilers.compilers import Language
    from mesonbuild.compilers.rust import RustdocTestCompiler


class PrecomputedHermeticCompiler(Compiler):
    """Base class for precomputed compilers used by the convert tool."""

    language: Language

    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice,
                 env: Environment, conf: CompilerConfig, linker: T.Optional[DynamicLinker] = None,
                 full_version: T.Optional[str] = None):  # fmt: skip
        self.conf = conf
        self.id = conf.get('compiler_id', 'unknown')
        super().__init__(
            [], exelist, version, for_machine, env, linker=linker, full_version=full_version
        )

    def has_multi_arguments(self, args: T.List[str]) -> T.Tuple[bool, bool]:
        fails = self.conf.get('supported_arguments', {}).get('fails', {}).get('args', [])
        return (all(a not in fails for a in args), True)

    def has_multi_link_arguments(self, args: T.List[str],
                                 to_host_args: bool = True) -> T.Tuple[bool, bool]:  # fmt: skip
        fails = self.conf.get('supported_link_arguments', {}).get('fails', {}).get('args', [])
        return (all(a not in fails for a in args), True)

    def compiles(self, code: T.Union[File, str], *,
                 extra_args: T.Union[T.List[str], CompilerArgs, T.Callable[[CompileCheckMode], T.List[str]], None] = None,
                 dependencies: T.Optional[T.List[Dependency]] = None,
                 mode: CompileCheckMode = CompileCheckMode.COMPILE,
                 disable_cache: bool = False,
                 name: str = '') -> T.Tuple[bool, bool]:  # fmt: skip
        fails = self.conf.get('compiles', {}).get('fails', {})
        if name and name in fails:
            return (False, True)
        if isinstance(code, list):
            snippet_str = '\n'.join(code)
        elif not isinstance(code, str):
            return (True, True)
        else:
            snippet_str = code
        for failure_marker in fails:
            if failure_marker in snippet_str:
                return (False, True)
        return (True, True)

    def links(self, code: T.Union[str, File], *, compiler: T.Optional[Compiler] = None,
              extra_args: T.Union[None, T.List[str], CompilerArgs, T.Callable[[CompileCheckMode], T.List[str]]] = None,
              dependencies: T.Optional[T.List[Dependency]] = None,
              disable_cache: bool = False,
              name: str = '') -> T.Tuple[bool, bool]:  # fmt: skip
        fails = self.conf.get('links', {}).get('fails', {})
        if name and name in fails:
            return (False, True)
        if not isinstance(code, str):
            return (True, True)
        for failure_marker in fails:
            if failure_marker in code:
                return (False, True)
        return (True, True)

    @contextlib.contextmanager
    def compile(self, code: T.Union[File, str],
                extra_args: T.Union[None, CompilerArgs, T.List[str]] = None,
                *, mode: CompileCheckMode = CompileCheckMode.LINK, want_output: bool = False,
                temp_dir: T.Optional[str] = None) -> T.Iterator[CompileResult]:  # fmt: skip
        yield CompileResult('', '', [], 0, '')

    def sanity_check(self, work_dir: str) -> None:
        pass

    def get_options(self) -> options.MutableKeyedOptionDictType:
        opts = super().get_options()
        key = self.form_compileropt_key('args')
        opts[key] = options.UserStringArrayOption(
            self.make_option_name(key), 'Extra arguments passed to the compiler', []
        )
        key = self.form_compileropt_key('link_args')
        opts[key] = options.UserStringArrayOption(
            self.make_option_name(key), 'Extra arguments passed to the linker', []
        )
        return opts


class PrecomputedHermeticCLikeCompiler(PrecomputedHermeticCompiler):
    """Abstract C/C++ Compiler for hermetic tools"""

    def __init__(self, for_machine: MachineChoice, env: Environment, conf: CompilerConfig):
        version = conf.get('version', 'unknown')
        linker_id = conf.get('linker_id')
        exelist = ['/usr/bin/true']
        linker = None
        if linker_id:
            linker = GnuBFDDynamicLinker([f'/dev/null/{linker_id}'], env, for_machine, None, [])

        super().__init__(exelist, version, for_machine, env, conf, linker, full_version=version)
        base_opts = conf.get('base_options')
        self.base_options.update({OptionKey(o) for o in base_opts})
        self.can_compile_suffixes.update({'s', 'sx'})

    def needs_static_linker(self) -> bool:
        return True

    def sizeof(self, typename: str, prefix: str, *,
               extra_args: T.Union[None, T.List[str], T.Callable[[CompileCheckMode], T.List[str]], None] = None,
               dependencies: T.Optional[T.List[Dependency]] = None) -> T.Tuple[int, bool]:  # fmt: skip
        sizeof_conf = self.conf.get('sizeof', {})
        sizes = sizeof_conf.get('sizes', {})
        if typename in sizes:
            return (sizes[typename], True)

        return (8, True)

    def alignment(self, typename: str, prefix: str, *,
                  extra_args: T.Optional[T.List[str]] = None,
                  dependencies: T.Optional[T.List[Dependency]] = None) -> T.Tuple[int, bool]:  # fmt: skip
        alignment_conf = self.conf.get('alignment', {})
        aligns = alignment_conf.get('aligns', {})
        if typename in aligns:
            return (aligns[typename], True)

        size, _ = self.sizeof(typename, prefix, extra_args=extra_args, dependencies=dependencies)
        return (size, True)

    def get_output_args(self, outputname: str) -> T.List[str]:
        return ['-o', outputname]

    def _sanity_check_source_code(self) -> str:
        return 'int main(void) { return 0; }'

    def get_optimization_args(self, optimization_level: str) -> T.List[str]:
        return clike_optimization_args.get(optimization_level, [])

    def find_library(self, libname: str, extra_dirs: T.List[str],
                     libtype: LibType = LibType.PREFER_SHARED,
                     lib_prefix_warning: bool = True,
                     ignore_system_dirs: bool = False,
                     skip_link_check: bool = False) -> T.Optional[T.List[str]]:  # fmt: skip
        if libname == 'rt':
            return ['']
        return None

    def has_header_symbol(self, hname: str, symbol: str, prefix: str, *,
                          extra_args: T.Union[T.List[str], T.Callable[[CompileCheckMode], T.List[str]], None] = None,
                          dependencies: T.Optional[T.List[Dependency]] = None) -> T.Tuple[bool, bool]:  # fmt: skip
        fails = self.conf.get('has_header_symbol', {}).get('fails', {})
        header_symbols_fails = fails.get(hname, {})
        return (symbol not in header_symbols_fails, True)

    def get_supported_function_attributes(self, attributes: T.List[str]) -> T.List[str]:
        fails = self.conf.get('has_function_attribute', {}).get('fails', {})
        return [a for a in attributes if a not in fails]

    def has_func_attribute(self, name: str) -> T.Tuple[bool, bool]:
        fails = self.conf.get('has_function_attribute', {}).get('fails', {})
        return name not in fails, True

    def has_function(self, funcname: str, prefix: str, *,
                     extra_args: T.Optional[T.List[str]] = None,
                     dependencies: T.Optional[T.List[Dependency]] = None) -> T.Tuple[bool, bool]:  # fmt: skip
        fails = self.conf.get('has_function', {}).get('fails', {})
        return (funcname not in fails, True)

    def cross_compute_int(self, expression: str, low: T.Optional[int],
                          high: T.Optional[int], upper: T.Optional[int]) -> int:  # fmt: skip
        return 0

    def get_default_include_dirs(self) -> T.List[str]:
        return []

    def get_define(self, dname: str, prefix: str,
                   extra_args: T.Union[T.List[str], T.Callable[[CompileCheckMode], T.List[str]]],
                   dependencies: T.List[Dependency], disable_cache: bool = False) -> T.Tuple[str, bool]:  # fmt: skip
        return ('', False)

    def thread_flags(self) -> T.List[str]:
        return []

    def thread_link_flags(self) -> T.List[str]:
        return []

    def check_header(self, hname: str, prefix: str, *,
                     extra_args: T.Union[None, T.List[str], T.Callable[[CompileCheckMode], T.List[str]]] = None,
                     dependencies: T.Optional[T.List[Dependency]] = None) -> T.Tuple[bool, bool]:  # fmt: skip
        fails = self.conf.get('check_header', {}).get('fails', {})
        return (hname not in fails, True)

    def has_header(self, hname: str, prefix: str, *,
                   extra_args: T.Union[None, T.List[str], T.Callable[[CompileCheckMode], T.List[str]]] = None,
                   dependencies: T.Optional[T.List[Dependency]] = None, disable_cache: bool = False) -> T.Tuple[bool, bool]:  # fmt: skip
        fails = self.conf.get('check_header', {}).get('fails', {})
        return (hname not in fails, True)

    def has_members(self, typename: str, membernames: T.List[str], prefix: str, *,
                    extra_args: T.Union[None, T.List[str], T.Callable[[CompileCheckMode], T.List[str]]] = None,
                    dependencies: T.Optional[T.List[Dependency]] = None) -> T.Tuple[bool, bool]:  # fmt: skip
        fails = self.conf.get('has_member', {}).get('fails', {})
        type_members_fails = fails.get(typename, {})
        return (all(m not in type_members_fails for m in membernames), True)


class PrecomputedHermeticCCompiler(PrecomputedHermeticCLikeCompiler):
    language = 'c'

    def get_options(self) -> options.MutableKeyedOptionDictType:
        opts = super().get_options()
        key = self.form_compileropt_key('std')
        choices = self.conf.get('standards')
        opts[key] = options.UserComboOption(
            self.make_option_name(key), 'C language standard to use', 'none', choices=choices
        )
        return opts


class PrecomputedHermeticCppCompiler(PrecomputedHermeticCLikeCompiler):
    language = 'cpp'

    def get_options(self) -> options.MutableKeyedOptionDictType:
        opts = super().get_options()
        key = self.form_compileropt_key('std')
        choices = self.conf.get('standards')
        opts[key] = options.UserComboOption(
            self.make_option_name(key), 'C++ language standard to use', 'none', choices=choices
        )

        key = self.form_compileropt_key('eh')
        opts[key] = options.UserComboOption(
            self.make_option_name(key),
            'C++ exception handling type.',
            'default',
            choices=['none', 'default', 'a', 's', 'sc'],
        )

        key = self.form_compileropt_key('rtti')
        opts[key] = options.UserBooleanOption(self.make_option_name(key), 'Enable RTTI', True)

        key = self.form_compileropt_key('debugstl')
        opts[key] = options.UserBooleanOption(self.make_option_name(key), 'STL debug mode', False)

        return opts


class PrecomputedHermeticRustCompiler(PrecomputedHermeticCompiler):
    """Abstract Rust Compiler for convert tool using pure inheritance."""

    language = 'rust'

    def __init__(self, for_machine: MachineChoice, env: Environment, conf: CompilerConfig):
        if 'compiler_id' not in conf:
            conf['compiler_id'] = 'rustc'
        if 'linker_id' not in conf:
            conf['linker_id'] = 'rustc'
        version = conf.get('version', '1.90.0')
        exelist = ['/usr/bin/true']
        self.is_nightly = False
        self.native_static_libs = []

        super().__init__(exelist, version, for_machine, env, conf, full_version=version)

    def needs_static_linker(self) -> bool:
        return False

    def get_crt_static(self) -> bool:
        return False

    def get_rustdoc(self) -> T.Optional[RustdocTestCompiler]:
        return None

    def get_output_args(self, outputname: str) -> T.List[str]:
        return ['--emit', f'link={outputname}']

    def _sanity_check_source_code(self) -> str:
        return 'fn main() {}'

    def get_optimization_args(self, optimization_level: str) -> T.List[str]:
        return rust_optimization_args.get(optimization_level, [])

    def get_options(self) -> options.MutableKeyedOptionDictType:
        opts = super().get_options()

        key = self.form_compileropt_key('std')
        opts[key] = options.UserComboOption(
            self.make_option_name(key),
            'Rust edition to use',
            'none',
            choices=['none', '2015', '2018', '2021', '2024'],
        )

        key = self.form_compileropt_key('dynamic_std')
        opts[key] = options.UserBooleanOption(
            self.make_option_name(key),
            'Whether to link Rust build targets to a dynamic libstd',
            False,
        )

        key = self.form_compileropt_key('nightly')
        opts[key] = options.UserFeatureOption(
            self.make_option_name(key),
            "Nightly Rust compiler (enabled=required, disabled=don't use nightly feature, auto=use nightly feature if available)",
            'auto',
        )

        return opts

    @functools.lru_cache(maxsize=None)
    def get_cfgs(self) -> T.List[str]:
        return []
