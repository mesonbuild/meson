#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import os
from dataclasses import dataclass
import typing as T

from mesonbuild.arglist import CompilerArgs
from mesonbuild.environment import Environment
from mesonbuild.mesonlib import File, LibType, MachineChoice, MesonException
from mesonbuild.dependencies.base import Dependency
from mesonbuild import compilers, options
from mesonbuild.compilers.compilers import Compiler, CompileCheckMode
from mesonbuild.hermetic.common_compiler import HermeticPlatformInfo, CompilerConfig

if T.TYPE_CHECKING:
    from mesonbuild.compilers.compilers import Language


@dataclass
class LanguageProperties:
    binary_name: str
    linker_key: str


LANGUAGE_PROPERTIES_TABLE: T.Dict[str, LanguageProperties] = {
    'c': LanguageProperties('cc', 'c_ld'),
    'cpp': LanguageProperties('cpp', 'cpp_ld'),
}


KNOWN_LINKER_IDS: T.Set[str] = {'ld.lld', 'lld'}
KNOWN_LLVM_PLATFORMS: T.Set[str] = {'fuchsia', 'android'}


class HermeticCompiler(Compiler):
    """Real compiler wrapper that probes and records platform check results."""

    language: Language

    def __init__(self, env: Environment, choice: MachineChoice,
                 platform_info: HermeticPlatformInfo):  # fmt: skip

        self.env = env
        self.platform_info = platform_info
        self.choice = choice
        self.compiler_config: CompilerConfig = T.cast(
            CompilerConfig, self.platform_info.platform.get(self.language, {})
        )
        self._clear_compiler_config()

        self.actual_compiler = self._setup_compiler()
        self.id = self.actual_compiler.id
        super().__init__(
            [],
            self.actual_compiler.exelist,
            self.actual_compiler.version,
            choice,
            env,
            linker=self.actual_compiler.linker,
            full_version=self.actual_compiler.full_version,
        )
        self.actual_compiler.is_cross = True
        self.exelist_no_ccache = self.actual_compiler.exelist_no_ccache
        self.base_options.update(self.actual_compiler.base_options)
        if hasattr(self.actual_compiler, 'can_compile_suffixes'):
            self.can_compile_suffixes.update(self.actual_compiler.can_compile_suffixes)

    def _setup_compiler(self) -> Compiler:
        compiler_paths = self.platform_info.compiler_paths.get(self.language)
        props = LANGUAGE_PROPERTIES_TABLE[self.language]

        toolchain_dir = compiler_paths.toolchain_wrap.download()
        rel_bin = T.cast(str, compiler_paths.toolchain_info.get(props.binary_name, ''))
        bin_path = os.path.join(str(toolchain_dir), rel_bin)
        self.env.binaries[self.choice].binaries[self.language] = [bin_path]

        if compiler_paths.sdk_wrap:
            cmd = self.env.binaries[self.choice].binaries.get(self.language)
            sdk_dir = compiler_paths.sdk_wrap.download()
            sysroot_rel = compiler_paths.sysroot_path
            sysroot_dir = os.path.join(str(sdk_dir), sysroot_rel)
            cmd.append(f'--sysroot={sysroot_dir}')
            self.env.properties[self.choice].properties['sys_root'] = sysroot_dir

            machine_info = self.platform_info.platform.get('machine_info', {})
            if machine_info.get('system') == 'fuchsia':
                cpu = machine_info.get('cpu_family', '')
                cmd.append(f'--target={cpu}-fuchsia')

        if self.language in {'c', 'cpp'}:
            c_info = T.cast(CompilerConfig, self.platform_info.platform.get(self.language, {}))
            machine_info = self.platform_info.platform.get('machine_info', {})
            if (
                c_info.get('linker_id') in KNOWN_LINKER_IDS
                or machine_info.get('system') in KNOWN_LLVM_PLATFORMS
            ):
                self.env.binaries[self.choice].binaries[props.linker_key] = ['lld']

        compiler = compilers.detect_compiler_for(self.env, self.language, self.choice, True, '')
        if not compiler:
            raise MesonException(f'Failed to detect real compiler for language {self.language}')

        compiler_config = self.compiler_config
        compiler_config['compiler_id'] = compiler.get_id()
        linker_id = compiler.get_linker_id()
        if linker_id:
            compiler_config['linker_id'] = linker_id

        compiler_config['version'] = compiler.version

        opts = compiler.get_options()
        std_key = compiler.form_compileropt_key('std')
        if std_key in opts:
            opt = opts[std_key]
            if hasattr(opt, 'choices'):
                compiler_config['standards'] = list(T.cast(T.Any, opt).choices)

        if hasattr(compiler, 'base_options'):
            new_options = [option.name for option in compiler.base_options]
            compiler_config['base_options'] = new_options

        if compiler_paths and compiler_paths.toolchain_info:
            compiler_config['toolchain'] = compiler_paths.toolchain_info.get('name', '')
        if compiler_paths and compiler_paths.sdk_wrap:
            compiler_config['sysroot'] = {
                'wrap_name': compiler_paths.sdk_wrap.name,
                'path': compiler_paths.sysroot_path or '',
            }

        return compiler

    def _clear_compiler_config(self) -> None:
        self.compiler_config['supported_arguments'] = {'fails': {'args': []}}
        self.compiler_config['supported_link_arguments'] = {'fails': {'args': []}}
        self.compiler_config['compiles'] = {'fails': {}}
        self.compiler_config['links'] = {'fails': {}}
        self.compiler_config['check_header'] = {'fails': {}}
        self.compiler_config['has_header_symbol'] = {'fails': {}}
        self.compiler_config['has_function'] = {'fails': {}}
        self.compiler_config['has_member'] = {'fails': {}}
        self.compiler_config['sizeof'] = {'sizes': {}}
        self.compiler_config['alignment'] = {'aligns': {}}
        self.compiler_config['has_function_attribute'] = {'fails': {}}

    def _sanity_check_source_code(self) -> str:
        return self.actual_compiler._sanity_check_source_code()

    def get_optimization_args(self, optimization_level: str) -> T.List[str]:
        return self.actual_compiler.get_optimization_args(optimization_level)

    def get_output_args(self, outputname: str) -> T.List[str]:
        return self.actual_compiler.get_output_args(outputname)

    def get_options(self) -> options.MutableKeyedOptionDictType:
        return self.actual_compiler.get_options()


class HermeticCLikeCompiler(HermeticCompiler):
    """C/C++ specific hermetic compiler wrapper"""

    def needs_static_linker(self) -> bool:
        return self.actual_compiler.needs_static_linker()

    def find_library(self, libname: str, extra_dirs: T.List[str],
                     libtype: LibType = LibType.PREFER_SHARED,
                     lib_prefix_warning: bool = True,
                     ignore_system_dirs: bool = False,
                     skip_link_check: bool = False) -> T.Optional[T.List[str]]:  # fmt: skip
        return self.actual_compiler.find_library(
            libname,
            extra_dirs,
            libtype=libtype,
            lib_prefix_warning=lib_prefix_warning,
            ignore_system_dirs=ignore_system_dirs,
            skip_link_check=skip_link_check,
        )

    def get_supported_function_attributes(self, attributes: T.List[str]) -> T.List[str]:
        return [a for a in attributes if self.has_func_attribute(a)[0]]

    def cross_compute_int(self, expression: str, low: T.Optional[int],
                          high: T.Optional[int], upper: T.Optional[int]) -> int:  # fmt: skip
        compute_fn = getattr(self.actual_compiler, '_cross_compute_int', None)

        if callable(compute_fn):
            return T.cast(int, compute_fn(expression, low, high, upper, ''))
        return 0

    def get_default_include_dirs(self) -> T.List[str]:
        return self.actual_compiler.get_default_include_dirs()

    def get_define(self, dname: str, prefix: str,
                   extra_args: T.Union[T.List[str], T.Callable[[CompileCheckMode], T.List[str]]],
                   dependencies: T.List[Dependency], disable_cache: bool = False) -> T.Tuple[str, bool]:  # fmt: skip
        return self.actual_compiler.get_define(
            dname,
            prefix,
            extra_args=extra_args,
            dependencies=dependencies,
            disable_cache=disable_cache,
        )

    def thread_flags(self) -> T.List[str]:
        return self.actual_compiler.thread_flags()

    def thread_link_flags(self) -> T.List[str]:
        return self.actual_compiler.thread_link_flags()

    def has_multi_arguments(self, args: T.List[str]) -> T.Tuple[bool, bool]:
        res = self.actual_compiler.has_multi_arguments(args)
        if not res[0]:
            args_list = self.compiler_config['supported_arguments']['fails']['args']
            for arg in args:
                if arg not in args_list:
                    args_list.append(arg)
        return res

    def has_multi_link_arguments(self, args: T.List[str],
                                 to_host_args: bool = True) -> T.Tuple[bool, bool]:  # fmt: skip
        res = self.actual_compiler.has_multi_link_arguments(args, to_host_args)
        if not res[0]:
            args_list = self.compiler_config['supported_link_arguments']['fails']['args']
            for arg in args:
                if arg not in args_list:
                    args_list.append(arg)
        return res

    def compiles(self, code: T.Union[File, str], *,
                 extra_args: T.Union[T.List[str], CompilerArgs, T.Callable[[CompileCheckMode], T.List[str]], None] = None,
                 dependencies: T.Optional[T.List[Dependency]] = None,
                 mode: CompileCheckMode = CompileCheckMode.COMPILE,
                 disable_cache: bool = False,
                 name: str = '') -> T.Tuple[bool, bool]:  # fmt: skip
        res = self.actual_compiler.compiles(
            code,
            extra_args=extra_args,
            dependencies=dependencies,
            mode=mode,
            disable_cache=disable_cache,
        )
        if not res[0] and isinstance(name, str) and name:
            if mode == CompileCheckMode.LINK:
                self.compiler_config['links']['fails'][name] = True
            else:
                self.compiler_config['compiles']['fails'][name] = True
        return res

    def links(self, code: T.Union[str, File], *, compiler: T.Optional[Compiler] = None,
              extra_args: T.Union[None, T.List[str], CompilerArgs, T.Callable[[CompileCheckMode], T.List[str]]] = None,
              dependencies: T.Optional[T.List[Dependency]] = None,
              disable_cache: bool = False,
              name: str = '') -> T.Tuple[bool, bool]:  # fmt: skip
        res = self.actual_compiler.links(
            code,
            compiler=compiler,
            extra_args=extra_args,
            dependencies=dependencies,
            disable_cache=disable_cache,
        )
        if not res[0] and isinstance(name, str) and name:
            self.compiler_config['links']['fails'][name] = True
        return res

    def check_header(self, hname: str, prefix: str, *,
                     extra_args: T.Union[None, T.List[str], T.Callable[[CompileCheckMode], T.List[str]]] = None,
                     dependencies: T.Optional[T.List[Dependency]] = None) -> T.Tuple[bool, bool]:  # fmt: skip
        res = self.actual_compiler.check_header(
            hname, prefix, extra_args=extra_args, dependencies=dependencies
        )
        if not res[0]:
            self.compiler_config['check_header']['fails'][hname] = True
        return res

    def has_header(self, hname: str, prefix: str, *,
                   extra_args: T.Union[None, T.List[str], T.Callable[[CompileCheckMode], T.List[str]]] = None,
                   dependencies: T.Optional[T.List[Dependency]] = None, disable_cache: bool = False) -> T.Tuple[bool, bool]:  # fmt: skip
        res = self.actual_compiler.has_header(
            hname,
            prefix,
            extra_args=extra_args,
            dependencies=dependencies,
            disable_cache=disable_cache,
        )
        if not res[0]:
            self.compiler_config['check_header']['fails'][hname] = True
        return res

    def has_header_symbol(self, hname: str, symbol: str, prefix: str, *,
                          extra_args: T.Union[T.List[str], T.Callable[[CompileCheckMode], T.List[str]], None] = None,
                          dependencies: T.Optional[T.List[Dependency]] = None) -> T.Tuple[bool, bool]:  # fmt: skip
        res = self.actual_compiler.has_header_symbol(
            hname, symbol, prefix, extra_args=extra_args, dependencies=dependencies
        )
        if not res[0]:
            self.compiler_config['has_header_symbol']['fails'].setdefault(hname, {})[symbol] = True
        return res

    def has_function(self, funcname: str, prefix: str, *,
                     extra_args: T.Optional[T.List[str]] = None,
                     dependencies: T.Optional[T.List[Dependency]] = None) -> T.Tuple[bool, bool]:  # fmt: skip
        res = self.actual_compiler.has_function(
            funcname, prefix, extra_args=extra_args, dependencies=dependencies
        )
        if not res[0]:
            self.compiler_config['has_function']['fails'][funcname] = True
        return res

    def has_members(self, typename: str, membernames: T.List[str], prefix: str, *,
                    extra_args: T.Union[None, T.List[str], T.Callable[[CompileCheckMode], T.List[str]]] = None,
                    dependencies: T.Optional[T.List[Dependency]] = None) -> T.Tuple[bool, bool]:  # fmt: skip
        res = self.actual_compiler.has_members(
            typename, membernames, prefix, extra_args=extra_args, dependencies=dependencies
        )
        if not res[0]:
            self.compiler_config['has_member']['fails'].setdefault(typename, {}).update(
                {m: True for m in membernames if isinstance(m, str)}
            )
        return res

    def sizeof(self, typename: str, prefix: str, *,
               extra_args: T.Union[None, T.List[str], T.Callable[[CompileCheckMode], T.List[str]], None] = None,
               dependencies: T.Optional[T.List[Dependency]] = None) -> T.Tuple[int, bool]:  # fmt: skip
        res = self.actual_compiler.sizeof(
            typename, prefix, extra_args=extra_args, dependencies=dependencies
        )
        self.compiler_config['sizeof']['sizes'][typename] = res[0]
        return res

    def alignment(self, typename: str, prefix: str, *,
                  extra_args: T.Optional[T.List[str]] = None,
                  dependencies: T.Optional[T.List[Dependency]] = None) -> T.Tuple[int, bool]:  # fmt: skip
        res = self.actual_compiler.alignment(
            typename, prefix, extra_args=extra_args, dependencies=dependencies
        )
        self.compiler_config['alignment']['aligns'][typename] = res[0]
        return res

    def has_func_attribute(self, name: str) -> T.Tuple[bool, bool]:
        res = self.actual_compiler.has_func_attribute(name)
        if not res[0]:
            self.compiler_config['has_function_attribute']['fails'][name] = True
        return res


class HermeticCCompiler(HermeticCLikeCompiler):
    language = 'c'


class HermeticCppCompiler(HermeticCLikeCompiler):
    language = 'cpp'
