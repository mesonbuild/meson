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
            self.make_option_name(key), 'Extra arguments passed to the compiler', []
        )
        key = self.form_compileropt_key('link_args')
        opts[key] = options.UserStringArrayOption(
            self.make_option_name(key), 'Extra arguments passed to the linker', []
        )
        return opts

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

    def has_multi_arguments(self, args: T.List[str], *a: T.Any, **kw: T.Any) -> T.Tuple[bool, bool]:
        fails = self.conf.get('supported_arguments', {}).get('fails', {}).get('args', [])
        return (all(a not in fails for a in args), True)

    def has_multi_link_arguments(
        self, args: T.List[str], *a: T.Any, **kw: T.Any
    ) -> T.Tuple[bool, bool]:
        fails = self.conf.get('supported_link_arguments', {}).get('fails', {}).get('args', [])
        return (all(a not in fails for a in args), True)

    def compiles(self, code: T.Union[File, str], *,
                 extra_args: T.Union[T.List[str], CompilerArgs, T.Callable[[CompileCheckMode], T.List[str]], None] = None,
                 dependencies: T.Optional[T.List[Dependency]] = None,
                 mode: CompileCheckMode = CompileCheckMode.COMPILE,
                 disable_cache: bool = False) -> T.Tuple[bool, bool]:  # fmt: skip
        fails = self.conf.get('compiles', {}).get('fails', {})
        if isinstance(code, list):
            snippet_str = '\n'.join(code)
        elif not isinstance(code, str):
            # We don't have the file contents, so we assume it compiles
            return (True, True)
        else:
            snippet_str = code

        for failure_marker in fails:
            if failure_marker in snippet_str:
                return (False, True)
        return (True, True)

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

    def get_define(self, *args: T.Any, **kwargs: T.Any) -> T.Tuple[str, bool]:
        return ('', False)

    def thread_flags(self, *args: T.Any, **kwargs: T.Any) -> T.List[str]:
        return []

    def thread_link_flags(self, *args: T.Any, **kwargs: T.Any) -> T.List[str]:
        return []

    def links(self, code: T.Union[str, File], *, compiler: T.Optional[Compiler] = None,
              extra_args: T.Union[None, T.List[str], CompilerArgs, T.Callable[[CompileCheckMode], T.List[str]]] = None,
              dependencies: T.Optional[T.List[Dependency]] = None,
              disable_cache: bool = False) -> T.Tuple[bool, bool]:  # fmt: skip
        fails = self.conf.get('links', {}).get('fails', {})
        if not isinstance(code, str):
            return (True, True)

        for failure_marker in fails:
            if failure_marker in code:
                return (False, True)
        return (True, True)

    def check_header(self, hname: str, prefix: str, *,
                     extra_args: T.Union[None, T.List[str], T.Callable[[CompileCheckMode], T.List[str]]] = None,
                     dependencies: T.Optional[T.List[Dependency]] = None) -> T.Tuple[bool, bool]:  # fmt: skip
        fails = self.conf.get('check_header', {}).get('fails', {})
        return (hname not in fails, True)

    def has_member(self, typename: str, membername: str, prefix: str, *,
                   extra_args: T.Union[None, T.List[str], T.Callable[[CompileCheckMode], T.List[str]]] = None,
                   dependencies: T.Optional[T.List[Dependency]] = None) -> T.Tuple[bool, bool]:  # fmt: skip
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

    def __init__(self, conf: T.Dict[str, T.Any], choice: MachineChoice,
                 env: Environment):  # fmt: skip
        version = conf.get('version')
        linker_id = conf.get('linker_id')
        exelist = ['/usr/bin/true']
        linker = None
        if linker_id:
            linker = GnuBFDDynamicLinker([f'/dev/null/{linker_id}'], env, choice, None, [])
        super().__init__(
            conf, [], exelist, version, choice, env, linker=linker, full_version=version
        )


# Only support Clang C++ Compiler for now
class AbstractClangCppCompiler(AbstractCompiler, ClangCPPCompiler):
    """Abstract Clang C++ Compiler for convert tool."""

    def __init__(self, conf: T.Dict[str, T.Any], choice: MachineChoice,
                 env: Environment):  # fmt: skip
        version = conf.get('version')
        linker_id = conf.get('linker_id')
        exelist = ['/usr/bin/true']
        linker = None
        if linker_id:
            linker = GnuBFDDynamicLinker([f'/dev/null/{linker_id}'], env, choice, None, [])
        super().__init__(
            conf, [], exelist, version, choice, env, linker=linker, full_version=version
        )


class AbstractRustCompiler(AbstractCompiler, RustCompiler):
    """Abstract Rust Compiler for convert tool."""

    def __init__(self, conf: T.Dict[str, T.Any], choice: MachineChoice,
                 env: Environment):  # fmt: skip
        version = conf.get('version')
        exelist = ['/usr/bin/true']
        super().__init__(conf, exelist, version, choice, env, full_version=version)
        self.native_static_libs = []


class AbstractPlatformWrap:
    """Holds information about the platform archive and its contents."""

    def __init__(self, wrap_config: T.Dict[str, T.Any]):
        self.url = wrap_config.get('source_url')
        self.sha256 = wrap_config.get('source_hash')
        self.filename = wrap_config.get('source_filename')
        self.binaries = wrap_config.get('binaries', {})
        self.strip_prefix = ''
        if self.filename:
            # Derive strip_prefix from source_filename
            for ext in ['.tar.gz', '.tar.xz', '.zip']:
                if self.filename.endswith(ext):
                    self.strip_prefix = self.filename[: -len(ext)]
                    break
            else:
                self.strip_prefix = self.filename.split('.')[0]


class AbstractPlatformInfo:
    """Holds information about the build and host machines for a platform."""

    def __init__(self, build_machine: str, host_machine: str,
                 platform_config: T.Dict[str, T.Any],
                 global_config: T.Optional[T.Dict[str, T.Any]] = None):  # fmt: skip
        self.name = host_machine
        self.platforms = PerMachine(build_machine, host_machine)
        self.machine_info = PerMachine(
            MachineInfo.from_literal(
                platform_config.get(build_machine, {}).get('host_machine', {})
            ),
            MachineInfo.from_literal(platform_config.get(host_machine, {}).get('host_machine', {})),
        )
        self.compilers_wrap = None
        self.sysroot_wrap = None
        self.sysroot_path = None

        if global_config:
            wraps = {w['name']: w for w in global_config.get('wrap', [])}
            toolchains = {t['name']: t for t in global_config.get('toolchain', [])}

            host_config = platform_config.get(host_machine, {})
            tc_name = host_config.get('toolchain')
            if tc_name in toolchains:
                tc_info = toolchains[tc_name]
                wrap_name = tc_info.get('wrap_name')
                if wrap_name in wraps:
                    self.compilers_wrap = AbstractPlatformWrap(wraps[wrap_name])
                    # Copy binaries from toolchain info
                    self.compilers_wrap.binaries = {
                        k: v for k, v in tc_info.items() if k not in ['name', 'wrap_name']
                    }

            sysroot_info = host_config.get('sysroot')
            if sysroot_info:
                wrap_name = sysroot_info.get('wrap_name')
                if wrap_name in wraps:
                    self.sysroot_wrap = AbstractPlatformWrap(wraps[wrap_name])
                    self.sysroot_path = sysroot_info.get('path')

    def host_supported(self) -> bool:
        return self.platforms[MachineChoice.HOST] == self.platforms[MachineChoice.BUILD]


class AbstractPlatform:
    """Represents a platform configuration for the convert tool."""

    def __init__(self, env: T.Any, host_machine_platform: str,
                 build_machine_platform: str, platform_config: T.Dict[str, T.Any],
                 global_config: T.Optional[T.Dict[str, T.Any]] = None):  # fmt: skip
        self.env = env
        self.platforms: T.Dict[MachineChoice, T.Dict[str, T.Any]] = {}
        self.platform_info = AbstractPlatformInfo(
            build_machine_platform, host_machine_platform, platform_config, global_config
        )
        self.platforms[MachineChoice.HOST] = platform_config.get(host_machine_platform)
        self.platforms[MachineChoice.BUILD] = platform_config.get(build_machine_platform)

    def create_c_compiler(self, choice: MachineChoice) -> T.Optional[AbstractClangCCompiler]:
        c_info = self.platforms[choice].get('c')
        if not c_info:
            return None
        return AbstractClangCCompiler(c_info, choice, self.env)

    def create_cpp_compiler(self, choice: MachineChoice) -> T.Optional[AbstractClangCppCompiler]:
        cpp_info = self.platforms[choice].get('cpp')
        if not cpp_info:
            return None
        return AbstractClangCppCompiler(cpp_info, choice, self.env)

    def create_rust_compiler(self, choice: MachineChoice) -> T.Optional[AbstractRustCompiler]:
        rs_info = self.platforms[choice].get('rust')
        if not rs_info:
            return None
        return AbstractRustCompiler(rs_info, choice, self.env)
