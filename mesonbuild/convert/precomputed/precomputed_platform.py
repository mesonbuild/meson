#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import contextlib
import functools
import typing as T
from typing import TypeAlias

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

if T.TYPE_CHECKING:
    from mesonbuild.compilers.compilers import Language

# FIXME(used variant in mesonbuild.options) eventually
ElementaryOptionValues: TypeAlias = T.Union[str, int, bool, T.List[str]]


class WrapInfo(T.TypedDict, total=False):
    name: str
    source_url: str
    source_filename: str
    source_hash: str
    binaries: T.Dict[str, str]


class ToolchainInfo(T.TypedDict, total=False):
    name: str
    wrap_name: str
    ar: str
    cc: str
    cpp: str
    strip: str


class SysrootInfo(T.TypedDict, total=False):
    wrap_name: str
    path: str


class HostMachineInfo(T.TypedDict, total=False):
    cpu_family: str
    cpu: str
    system: str
    endian: str


class CheckHeaderConfig(T.TypedDict, total=False):
    fails: T.Dict[str, bool]


class HasHeaderSymbolConfig(T.TypedDict, total=False):
    fails: T.Dict[str, T.Dict[str, bool]]


class HasFunctionConfig(T.TypedDict, total=False):
    fails: T.Dict[str, bool]


class SupportedArgumentsFails(T.TypedDict, total=False):
    args: T.List[str]


class SupportedArgumentsConfig(T.TypedDict, total=False):
    fails: SupportedArgumentsFails


class CompilesConfig(T.TypedDict, total=False):
    fails: T.Dict[str, bool]


class LinksConfig(T.TypedDict, total=False):
    fails: T.Dict[str, bool]


class HasMemberConfig(T.TypedDict, total=False):
    fails: T.Dict[str, T.Dict[str, bool]]


class HasFunctionAttributeConfig(T.TypedDict, total=False):
    fails: T.Dict[str, bool]


class CompilerConfig(T.TypedDict, total=False):
    compiler_id: str
    linker_id: str
    version: str
    check_header: CheckHeaderConfig
    has_header_symbol: HasHeaderSymbolConfig
    has_function: HasFunctionConfig
    supported_arguments: SupportedArgumentsConfig
    supported_link_arguments: SupportedArgumentsConfig
    compiles: CompilesConfig
    links: LinksConfig
    has_member: HasMemberConfig
    has_function_attribute: HasFunctionAttributeConfig


class PlatformInfo(T.TypedDict, total=False):
    name: str
    toolchain: str
    sysroot: SysrootInfo
    host_machine: HostMachineInfo
    c: CompilerConfig
    cpp: CompilerConfig
    rust: CompilerConfig


class PlatformsToml(T.TypedDict, total=False):
    wrap: T.List[WrapInfo]
    toolchain: T.List[ToolchainInfo]
    platform: T.List[PlatformInfo]


class PrecomputedCLikeCompiler(Compiler):
    """Abstract C/C++ Compiler for convert tool using composition."""

    def __init__(self, compiler: Compiler, conf: CompilerConfig, language: Language):
        self.compiler: Compiler = compiler
        self.conf: CompilerConfig = conf
        self.language = language
        super().__init__(
            [],
            compiler.exelist_no_ccache,
            compiler.version,
            compiler.for_machine,
            compiler.environment,
            linker=compiler.linker,
            full_version=compiler.full_version,
        )

    def __getattribute__(self, name: str) -> T.Any:
        # We use a custom __getattribute__ hook to implement a selective proxy pattern.
        # This allows us to mock specific compiler checks (like `has_header`) for the
        # convert tool, while delegating all other compiler behavior to the
        # self.compiler.

        # Prevent infinite recursion by directly returning the wrapper's own
        # core attributes using the base object class.
        if name in {'compiler', 'conf', 'language', '__class__', '__dict__'}:
            return object.__getattribute__(self, name)

        # Check if the attribute/method is explicitly overridden (mocked) on this
        # wrapper class.
        if name in PrecomputedCLikeCompiler.__dict__ or name in type(self).__dict__:
            return object.__getattribute__(self, name)

        # Delegate everything else to the wrapped compiler instance.
        # We do not re-bind delegated methods to this wrapper (`self`). We return
        # them bound to `self.compiler` (the real compiler instance).
        compiler = object.__getattribute__(self, 'compiler')
        return getattr(compiler, name)

    def get_output_args(self, outputname: str) -> T.List[str]:
        return self.compiler.get_output_args(outputname)

    def _sanity_check_source_code(self) -> str:
        return self.compiler._sanity_check_source_code()

    def get_optimization_args(self, optimization_level: str) -> T.List[str]:
        return self.compiler.get_optimization_args(optimization_level)

    def get_options(self) -> options.MutableKeyedOptionDictType:
        opts = self.compiler.get_options()
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
                 disable_cache: bool = False) -> T.Tuple[bool, bool]:  # fmt: skip
        fails = self.conf.get('compiles', {}).get('fails', {})
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
              disable_cache: bool = False) -> T.Tuple[bool, bool]:  # fmt: skip
        fails = self.conf.get('links', {}).get('fails', {})
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

    def has_member(self, typename: str, membername: str, prefix: str, *,
                   extra_args: T.Union[None, T.List[str], T.Callable[[CompileCheckMode], T.List[str]]] = None,
                   dependencies: T.Optional[T.List[Dependency]] = None) -> T.Tuple[bool, bool]:  # fmt: skip
        fails = self.conf.get('has_member', {}).get('fails', {})
        type_members_fails = fails.get(typename, {})
        return (membername not in type_members_fails, True)


class PrecomputedRustCompiler(RustCompiler):
    """Abstract Rust Compiler for convert tool using inheritance."""

    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice,
                 env: Environment, conf: CompilerConfig, full_version: T.Optional[str] = None):  # fmt: skip
        super().__init__(exelist, version, for_machine, env, full_version=full_version)
        self.conf = conf
        self.native_static_libs: T.List[str] = []

    @functools.lru_cache(maxsize=None)
    def get_cfgs(self) -> T.List[str]:
        return []

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


class PrecomputedPlatformWrap:
    """Holds information about the platform archive and its contents.
    Able to be downloaded from internet, like a normal wrap file"""

    def __init__(self, wrap_config: WrapInfo):
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


class PrecomputedPlatformInfo:
    """Holds information about the build and host machines for a platform."""

    def __init__(self, build_machine: str, host_machine: str,
                 platform_config: T.Dict[str, PlatformInfo],
                 global_config: T.Optional[PlatformsToml] = None):  # fmt: skip
        self.name = host_machine
        self.platforms = PerMachine(build_machine, host_machine)
        # Note: Getting the host_machine of the build_machine is completely intentional
        # for now.
        # TODO: Change the platforms.toml to be [platform.machine_info] in next revision.
        build_machine_info = T.cast(
            T.Dict[str, ElementaryOptionValues],
            platform_config.get(build_machine, {}).get('host_machine', {}),
        )
        host_machine_info = T.cast(
            T.Dict[str, ElementaryOptionValues],
            platform_config.get(host_machine, {}).get('host_machine', {}),
        )
        self.machine_info = PerMachine(
            MachineInfo.from_literal(build_machine_info),
            MachineInfo.from_literal(host_machine_info),
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
                    self.compilers_wrap = PrecomputedPlatformWrap(wraps[wrap_name])
                    # Copy binaries from toolchain info
                    self.compilers_wrap.binaries = {
                        k: T.cast(str, v)
                        for k, v in tc_info.items()
                        if k not in ['name', 'wrap_name']
                    }

            sysroot_info = host_config.get('sysroot')
            if sysroot_info:
                wrap_name = sysroot_info.get('wrap_name')
                if wrap_name in wraps:
                    self.sysroot_wrap = PrecomputedPlatformWrap(wraps[wrap_name])
                    self.sysroot_path = sysroot_info.get('path')

    def is_native(self) -> bool:
        return self.platforms[MachineChoice.HOST] == self.platforms[MachineChoice.BUILD]


class PrecomputedPlatform:
    """Represents a platform configuration for the convert tool."""

    def __init__(self, env: Environment, host_machine_platform: str,
                 build_machine_platform: str, platform_config: T.Dict[str, PlatformInfo],
                 global_config: T.Optional[PlatformsToml] = None):  # fmt: skip
        self.env = env
        self.platforms: T.Dict[MachineChoice, PlatformInfo] = {}
        self.platform_info = PrecomputedPlatformInfo(
            build_machine_platform, host_machine_platform, platform_config, global_config
        )
        self.platforms[MachineChoice.HOST] = platform_config[host_machine_platform]
        self.platforms[MachineChoice.BUILD] = platform_config[build_machine_platform]

    def create_c_compiler(self, choice: MachineChoice) -> T.Optional[PrecomputedCLikeCompiler]:
        c_info = self.platforms[choice].get('c')
        if not c_info:
            return None
        version = c_info.get('version')
        linker_id = c_info.get('linker_id')
        exelist = ['/usr/bin/true']
        linker = None
        if linker_id:
            linker = GnuBFDDynamicLinker([f'/dev/null/{linker_id}'], self.env, choice, None, [])
        compiler = ClangCCompiler(
            [], exelist, version, choice, self.env, linker=linker, full_version=version
        )
        return PrecomputedCLikeCompiler(compiler, c_info, 'c')

    def create_cpp_compiler(self, choice: MachineChoice) -> T.Optional[PrecomputedCLikeCompiler]:
        cpp_info = self.platforms[choice].get('cpp')
        if not cpp_info:
            return None
        version = cpp_info.get('version')
        linker_id = cpp_info.get('linker_id')
        exelist = ['/usr/bin/true']
        linker = None
        if linker_id:
            linker = GnuBFDDynamicLinker([f'/dev/null/{linker_id}'], self.env, choice, None, [])
        compiler = ClangCPPCompiler(
            [], exelist, version, choice, self.env, linker=linker, full_version=version
        )
        return PrecomputedCLikeCompiler(compiler, cpp_info, 'cpp')

    def create_rust_compiler(self, choice: MachineChoice) -> T.Optional[PrecomputedRustCompiler]:
        rs_info = self.platforms[choice].get('rust')
        if not rs_info:
            return None
        version = rs_info.get('version')
        exelist = ['/usr/bin/true']
        return PrecomputedRustCompiler(
            exelist, version, choice, self.env, rs_info, full_version=version
        )

    def create_compiler(self, lang: str, choice: MachineChoice) -> T.Optional[Compiler]:
        if lang == 'c':
            return self.create_c_compiler(choice)
        elif lang == 'cpp':
            return self.create_cpp_compiler(choice)
        elif lang == 'rust':
            return self.create_rust_compiler(choice)
        return None
