#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import contextlib
import typing as T

from mesonbuild.arglist import CompilerArgs
from mesonbuild.compilers.compilers import Compiler, CompileCheckMode
from mesonbuild.environment import Environment
from mesonbuild.mesonlib import File, LibType, PerMachine
from mesonbuild.dependencies.base import Dependency

from mesonbuild.envconfig import MachineInfo
from mesonbuild.mesonlib import MachineChoice
from mesonbuild.compilers.c import ClangCCompiler
from mesonbuild.compilers.cpp import ClangCPPCompiler
from mesonbuild.compilers.rust import RustCompiler
from mesonbuild.linkers.linkers import GnuBFDDynamicLinker
from mesonbuild.compilers.compilers import CompileResult
from mesonbuild import options


class AbstractCompiler(Compiler):
    """Base class for compilers in the convert tool, simulating compiler checks."""

    def __init__(self, conf: T.Dict[T.Any, T.Any], *args: T.Any, **kwargs: T.Any):
        self.conf = conf
        super().__init__(*args, **kwargs)

    def get_options(self) -> options.MutableKeyedOptionDictType:
        opts = super().get_options()
        key = self.form_compileropt_key('args')
        opts[key] = options.UserStringArrayOption(
            self.make_option_name(key),
            'Extra arguments passed to the compiler',
            [],
        )
        key = self.form_compileropt_key('link_args')
        opts[key] = options.UserStringArrayOption(
            self.make_option_name(key),
            'Extra arguments passed to the linker',
            [],
        )
        return opts

    def find_library(
        self,
        libname: str,
        extra_dirs: T.List[str],
        libtype: LibType = LibType.PREFER_SHARED,
        lib_prefix_warning: bool = True,
        ignore_system_dirs: bool = False,
    ) -> T.Optional[T.List[str]]:
        if libname == 'rt':
            return ['']
        return None

    def has_header_symbol(
        self,
        hname: str,
        symbol: str,
        prefix: str,
        *,
        extra_args: T.Union[T.List[str], T.Callable[[CompileCheckMode], T.List[str]], None] = None,
        dependencies: T.Optional[T.List[Dependency]] = None,
    ) -> T.Tuple[bool, bool]:
        fails = self.conf.get('has_header_symbol', {}).get('fails', {})
        header_symbols_fails = fails.get(hname, {})
        return (symbol not in header_symbols_fails, True)

    def has_multi_arguments(self, args: T.List[str], *a: T.Any, **kw: T.Any) -> T.Tuple[bool, bool]:
        fails = (self.conf.get('supported_arguments', {}).get('fails', {}).get('args', []))
        return (all(a not in fails for a in args), True)

    def has_multi_link_arguments(self, args: T.List[str], *a: T.Any,
                                 **kw: T.Any) -> T.Tuple[bool, bool]:
        fails = (self.conf.get('supported_link_arguments', {}).get('fails', {}).get('args', []))
        return (all(a not in fails for a in args), True)

    def compiles(
        self,
        code: T.Union[File, str],
        *,
        extra_args: T.Union[
            T.List[str],
            CompilerArgs,
            T.Callable[[CompileCheckMode], T.List[str]],
            None,
        ] = None,
        dependencies: T.Optional[T.List[Dependency]] = None,
        mode: CompileCheckMode = CompileCheckMode.COMPILE,
        disable_cache: bool = False,
    ) -> T.Tuple[bool, bool]:
        fails = self.conf.get('compiles', {}).get('fails', {})
        if isinstance(code, list):
            snippet_str = '\n'.join(code)
        elif not isinstance(code, str):
            # We don't have the file contents, so we assume it compiles
            return (True, True)
        else:
            snippet_str = code
        for f in fails:
            if f in snippet_str:
                return (False, True)
        return (True, True)

    def get_supported_function_attributes(self, attributes: T.List[str]) -> T.List[str]:
        fails = self.conf.get('has_function_attribute', {}).get('fails', {})

        return [a for a in attributes if a not in fails]

    def has_func_attribute(self, name: str) -> T.Tuple[bool, bool]:
        fails = self.conf.get('has_function_attribute', {}).get('fails', {})

        return name not in fails, True

    def has_function(
        self,
        funcname: str,
        prefix: str,
        *,
        extra_args: T.Optional[T.List[str]] = None,
        dependencies: T.Optional[T.List[Dependency]] = None,
    ) -> T.Tuple[bool, bool]:
        fails = self.conf.get('has_function', {}).get('fails', {})
        return (funcname not in fails, True)

    def cross_compute_int(
        self,
        expression: str,
        low: T.Optional[int],
        high: T.Optional[int],
        upper: T.Optional[int],
    ) -> int:
        return 0

    def get_default_include_dirs(self) -> T.List[str]:
        return []

    def get_define(self, *args: T.Any, **kwargs: T.Any) -> T.Tuple[str, bool]:
        return ('', False)

    def thread_flags(self, *args: T.Any, **kwargs: T.Any) -> T.List[str]:
        return []

    def thread_link_flags(self, *args: T.Any, **kwargs: T.Any) -> T.List[str]:
        return []

    def links(
        self,
        code: T.Union[str, File],
        *,
        compiler: T.Optional[Compiler] = None,
        extra_args: T.Union[
            None,
            T.List[str],
            CompilerArgs,
            T.Callable[[CompileCheckMode], T.List[str]],
        ] = None,
        dependencies: T.Optional[T.List[Dependency]] = None,
        disable_cache: bool = False,
    ) -> T.Tuple[bool, bool]:
        fails = self.conf.get('links', {}).get('fails', {})
        if isinstance(code, str):
            return (code not in fails, True)
        return (True, True)

    def check_header(
        self,
        hname: str,
        prefix: str,
        *,
        extra_args: T.Union[None, T.List[str], T.Callable[[CompileCheckMode], T.List[str]]] = None,
        dependencies: T.Optional[T.List[Dependency]] = None,
    ) -> T.Tuple[bool, bool]:
        fails = self.conf.get('check_header', {}).get('fails', {})
        return (hname not in fails, True)

    def has_member(
        self,
        typename: str,
        membername: str,
        prefix: str,
        *,
        extra_args: T.Union[None, T.List[str], T.Callable[[CompileCheckMode], T.List[str]]] = None,
        dependencies: T.Optional[T.List[Dependency]] = None,
    ) -> T.Tuple[bool, bool]:
        fails = self.conf.get('has_member', {}).get('fails', {})
        type_members_fails = fails.get(typename, {})
        return (membername not in type_members_fails, True)

    @contextlib.contextmanager
    def compile(self, *args: T.Any, **kwargs: T.Any) -> T.Generator[CompileResult, None, None]:
        yield CompileResult('', '', [], 0, '')

    def sanity_check(self, work_dir: str) -> None:
        pass


# Only support Clang C Compiler for now
class AbstractClangCCompiler(AbstractCompiler, ClangCCompiler):
    """Abstract Clang C Compiler for convert tool."""

    def __init__(self, conf: T.Dict[str, T.Any], choice: MachineChoice, env: Environment):
        version = conf.get('version')
        linker_id = conf.get('linker_id')
        exelist = ['/usr/bin/true']
        linker = None
        if linker_id:
            linker = GnuBFDDynamicLinker([f'/dev/null/{linker_id}'], env, choice, '', [])
        super().__init__(
            conf,
            [],
            exelist,
            version,
            choice,
            env,
            linker=linker,
            full_version=version,
        )


# Only support Clang C++ Compiler for now
class AbstractClangCppCompiler(AbstractCompiler, ClangCPPCompiler):
    """Abstract Clang C++ Compiler for convert tool."""

    def __init__(self, conf: T.Dict[str, T.Any], choice: MachineChoice, env: Environment):
        version = conf.get('version')
        linker_id = conf.get('linker_id')
        exelist = ['/usr/bin/true']
        linker = None
        if linker_id:
            linker = GnuBFDDynamicLinker([f'/dev/null/{linker_id}'], env, choice, '', [])
        super().__init__(
            conf,
            [],
            exelist,
            version,
            choice,
            env,
            linker=linker,
            full_version=version,
        )


class AbstractRustCompiler(AbstractCompiler, RustCompiler):
    """Abstract Rust Compiler for convert tool."""

    def __init__(self, conf: T.Dict[str, T.Any], choice: MachineChoice, env: Environment):
        version = conf.get('version')
        exelist = ['/usr/bin/true']
        super().__init__(
            conf,
            exelist,
            version,
            choice,
            env,
            full_version=version,
        )
        self.native_static_libs = []


class AbstractToolchainInfo:
    """Holds information about the build and host machines for a toolchain."""

    def __init__(
        self,
        build_machine: str,
        host_machine: str,
        toolchain_config: T.Dict[str, T.Any],
    ):
        self.toolchains = PerMachine(build_machine, host_machine)
        self.machine_info = PerMachine(
            MachineInfo.from_literal(
                toolchain_config.get(build_machine, {}).get('host_machine', {})),
            MachineInfo.from_literal(
                toolchain_config.get(host_machine, {}).get('host_machine', {})),
        )

    def host_supported(self) -> bool:
        return self.toolchains[MachineChoice.HOST] == self.toolchains[MachineChoice.BUILD]


class AbstractToolchain:
    """Represents a toolchain configuration for the convert tool."""

    def __init__(
        self,
        env: T.Any,
        host_machine_toolchain: str,
        build_machine_toolchain: str,
        toolchain_config: T.Dict[str, T.Any],
    ):
        self.env = env
        self.toolchains: T.Dict[MachineChoice, T.Dict[str, T.Any]] = {}
        self.toolchain_info = AbstractToolchainInfo(build_machine_toolchain, host_machine_toolchain,
                                                    toolchain_config)
        self.toolchains[MachineChoice.HOST] = toolchain_config.get(host_machine_toolchain)
        self.toolchains[MachineChoice.BUILD] = toolchain_config.get(build_machine_toolchain)

    def create_c_compiler(self, choice: MachineChoice) -> T.Optional[AbstractClangCCompiler]:
        c_info = self.toolchains[choice].get('c')
        if not c_info:
            return None
        return AbstractClangCCompiler(c_info, choice, self.env)

    def create_cpp_compiler(self, choice: MachineChoice) -> T.Optional[AbstractClangCppCompiler]:
        cpp_info = self.toolchains[choice].get('cpp')
        if not cpp_info:
            return None
        return AbstractClangCppCompiler(cpp_info, choice, self.env)

    def create_rust_compiler(self, choice: MachineChoice) -> T.Optional[AbstractRustCompiler]:
        rs_info = self.toolchains[choice].get('rust')
        if not rs_info:
            return None
        return AbstractRustCompiler(rs_info, choice, self.env)
