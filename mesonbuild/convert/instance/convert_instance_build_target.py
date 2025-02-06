#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T
import os
from collections import defaultdict
from dataclasses import dataclass

from mesonbuild import build
from mesonbuild.backend.backends import Backend
from mesonbuild.mesonlib import File
from mesonbuild.dependencies import base as dependency_base
from mesonbuild.options import OptionKey
from enum import Enum

from mesonbuild.convert.common_defs import ExternalDepKind, FlagScope, GeneratedFilesType
from mesonbuild.convert.instance.convert_instance_custom_target import ConvertInstanceCustomTarget
from mesonbuild.convert.instance.convert_instance_utils import (
    ConvertId,
    ConvertInstanceFlag,
    ConvertInstanceIncludeDirectory,
)
from mesonbuild.convert.instance.naming import (
    is_bindgen_inline_wrapper,
    resolve_target_name,
    sanitize_target_name,
    structured_sources_name,
)
from mesonbuild.convert.convert_project_instance import ConvertProjectInstance
from mesonbuild.convert.convert_project_config import ConvertProjectConfig
from mesonbuild.modules.rust import RustBindgenTarget


class RustABI(Enum):
    RUST = 'rust'
    C = 'c'
    BINARY = 'rust_binary'
    PROC_MACRO = 'proc-macro'
    NONE = None


@dataclass
class CustomTargetInfo:
    subdir: str = ''
    files_type: GeneratedFilesType = GeneratedFilesType.UNKNOWN


def _determine_rust_abi(build_target: build.BuildTarget) -> RustABI:

    if build_target.uses_rust():
        kwarg_crate_type = build_target.original_kwargs.get('rust_crate_type')
        if kwarg_crate_type in {'bin'}:
            return RustABI.BINARY
        if kwarg_crate_type in {'proc-macro'}:
            return RustABI.PROC_MACRO
        if kwarg_crate_type in {'rlib'}:
            return RustABI.RUST
        if kwarg_crate_type in {'cdylib', 'staticlib'}:
            return RustABI.C

    return RustABI.NONE


def _rust_dependency_mismatch(build_target_abi: RustABI, dependency_abi: RustABI) -> bool:
    if dependency_abi in {RustABI.RUST, RustABI.PROC_MACRO} and build_target_abi is RustABI.NONE:
        return True

    return False


def _determine_files_type(outputs: T.List[str]) -> GeneratedFilesType:
    files_type: GeneratedFilesType = GeneratedFilesType.UNKNOWN
    for output in outputs:
        if output.endswith(('.h', '.hpp')):
            files_type |= GeneratedFilesType.HEADERS
        elif output.endswith(('.c', '.cpp', '.cc')):
            files_type |= GeneratedFilesType.IMPL

    return files_type


class ConvertInstanceBuildTarget:
    """A representation of build.BuildTarget, but optimized for the convert tool"""

    def __init__(self, build_info: build.Build, backend: Backend, build_target: build.BuildTarget,
                 project_instance: ConvertProjectInstance, project_config: ConvertProjectConfig):  # fmt: skip
        self.name: str = ''

        self.rust_abi: RustABI = RustABI.NONE
        self.crate_root: T.Optional[ConvertId] = None
        self.crate_name: str = ''
        self.rust_edition: T.Optional[str] = None
        self.proc_macros: T.List[ConvertId] = []

        self.srcs: T.List[ConvertId] = []
        self.structured_sources: T.Optional[ConvertInstanceCustomTarget] = None
        self.bindgen_inline_wrappers: T.List[T.Tuple[ConvertId, str]] = []
        self.extra_include_dir_deps: T.List[ConvertId] = []
        self.rust_libs: T.List[ConvertId] = []
        self.static_libs: T.List[ConvertId] = []
        self.header_libs: T.List[ConvertId] = []
        self.shared_libs: T.List[ConvertId] = []
        self.whole_static_libs: T.List[ConvertId] = []
        self.generated_headers: T.List[ConvertId] = []
        self.generated_sources: T.List[ConvertId] = []
        self.install_dir: T.List[str] = []
        self.generated_include_dirs: T.Dict[str, ConvertInstanceIncludeDirectory] = {}

        self.c_std: T.Optional[str] = None
        self.cpp_std: T.Optional[str] = None

        self.compile_args_deps: T.List[str] = []
        self.link_args_deps: T.List[str] = []
        self.linker_version_script: T.Optional[ConvertId] = None

        self.generated_flags: T.Dict[str, ConvertInstanceFlag] = {}
        self.generated_linker_flags: T.Dict[str, ConvertInstanceFlag] = {}

        self.subdir = build_target.subdir
        self.machine_choice = build_target.for_machine
        self.install = build_target.install
        self._parse_build_target(
            build_info, backend, build_target, project_instance, project_config
        )

    def _parse_build_target(self, build_info: build.Build, backend: Backend, build_target: build.BuildTarget,
                            project_instance: ConvertProjectInstance,
                            project_config: ConvertProjectConfig) -> None:  # fmt: skip
        """
        Main entry point for processing a `build.BuildTarget`.

        This method serves as a dispatcher that orchestrates the parsing of a raw
        `build.BuildTarget` from Meson.

        It calls various specialized `_handle_*` methods to translate all relevant
        properties of the target—such as its name, sources, dependencies, etc.
        """
        self._handle_naming(build_target, project_config)
        self._handle_structured_sources(build_target, project_instance, project_config)
        self._handle_sources(build_target, project_instance)

        self._handle_generated_sources(build_target, project_config)
        self._handle_extra_include_dir_deps(project_config)
        self._handle_external_dependencies(build_target, project_config)
        self._handle_internal_dependencies(backend, build_target, project_config)

        self._handle_include_dirs(build_target, project_instance)
        self._handle_compile_args(build_info, build_target, project_instance, project_config)
        self._handle_linker_args(build_info, build_target, project_instance, project_config)
        self._handle_language_standards(build_target)

    def _handle_naming(self, build_target: build.BuildTarget,
                       project_config: ConvertProjectConfig) -> None:  # fmt: skip
        self.rust_abi = _determine_rust_abi(build_target)
        if self.rust_abi is not RustABI.NONE:
            self.crate_name = build_target.get_basename()
        self.name = resolve_target_name(build_target, project_config)

    def structured_crate_root(self) -> T.Optional[str]:
        if not self.structured_sources or self.rust_abi is RustABI.NONE:
            return None
        for generated in self.structured_sources.generated_outputs:
            if os.path.basename(generated.output) in {'lib.rs', 'main.rs'}:
                return generated.output
        return None

    def _handle_structured_sources(self, build_target: build.BuildTarget,
                                   project_instance: ConvertProjectInstance,
                                   project_config: ConvertProjectConfig) -> None:  # fmt: skip
        if not build_target.structured_sources:
            return

        gen_name = structured_sources_name(build_target, project_config)
        self.structured_sources = ConvertInstanceCustomTarget.from_structured_sources(
            gen_name, self.subdir, build_target.structured_sources, project_instance, project_config
        )

    def _handle_sources(self, build_target: build.BuildTarget,
                        project_instance: ConvertProjectInstance) -> None:  # fmt: skip
        for file in build_target.sources:
            basename = os.path.basename(file.fname)
            if self.rust_abi is not RustABI.NONE and basename in {'lib.rs', 'main.rs'}:
                self.crate_root = ConvertId.from_local_file(file)
                continue

            filegroup_or_include_dir = file.subdir != self.subdir or file.fname != basename
            if filegroup_or_include_dir:
                if file.fname.endswith(('.h', '.hpp')):
                    # Headers must be represented by ConvertInstanceIncludeDirectory
                    inc_name = project_instance.determine_include_dir_from_file(file)
                    self.generated_include_dirs[inc_name] = project_instance.shared_include_dirs[
                        inc_name
                    ]
                else:
                    (fg_name, subdir) = project_instance.determine_filegroup(file, self.name)
                    src = ConvertId(fg_name, subdir)
                    if src not in self.srcs:
                        self.srcs.append(src)
            else:
                if not file.fname.endswith('.h') and not file.fname.endswith('.hpp'):
                    self.srcs.append(ConvertId.from_local_file(file))

    def _handle_extra_include_dir_deps(self, project_config: ConvertProjectConfig) -> None:
        for dep in project_config.extra_include_dir_deps.get(self.name, []):
            self.extra_include_dir_deps.append(ConvertId.from_local_name(dep, self.subdir))

    def _add_external_dep(self, d: dependency_base.ExternalDependency,
                          project_config: ConvertProjectConfig,
                          shared_only: bool = False) -> None:  # fmt: skip
        """Classify and register a single external dependency.

        When ``shared_only`` is True (used when propagating external deps from
        statically linked targets into a SharedLibrary or Executable), only
        shared-library-kind deps are added. Header, static, and Rust library
        deps are intentionally left out because they were already pulled in via
        the static-library link edge.
        """
        found = project_config.lookup_external_dependency(d.name)
        if not found:
            return

        dep, kind = found
        if shared_only and kind is not ExternalDepKind.SHARED:
            return

        target_lists = {
            ExternalDepKind.HEADER: self.header_libs,
            ExternalDepKind.PROC_MACRO: self.proc_macros,
            ExternalDepKind.RUST: self.rust_libs,
            ExternalDepKind.STATIC: self.static_libs,
            ExternalDepKind.SHARED: self.shared_libs,
        }
        target_list = target_lists[kind]
        if dep not in target_list:
            target_list.append(dep)

    def _handle_external_dependencies(self, build_target: build.BuildTarget,
                                      project_config: ConvertProjectConfig) -> None:  # fmt: skip
        for d in build_target.external_deps:
            if d.found() and isinstance(d, dependency_base.ExternalDependency):
                self._add_external_dep(d, project_config)
            elif isinstance(d, dependency_base.InternalDependency):
                # meson likes to put link + compile args as internal dependencies
                # for some reason
                self.compile_args_deps.extend(d.get_compile_args())
                self.link_args_deps.extend(d.get_link_args())

    def _handle_include_dirs(self, build_target: build.BuildTarget,
                             project_instance: ConvertProjectInstance) -> None:  # fmt: skip
        for include_dir in build_target.include_dirs:
            inc_name = project_instance.determine_include_dir(include_dir)
            self.generated_include_dirs[inc_name] = project_instance.shared_include_dirs[inc_name]

    def _handle_generated_sources(self, build_target: build.BuildTarget,
                                  project_config: ConvertProjectConfig) -> None:  # fmt: skip
        targets_to_process: T.List[T.Tuple[build.Target, T.List[str]]] = []
        target_mapping: T.Dict[str, CustomTargetInfo] = defaultdict(CustomTargetInfo)
        for obj in build_target.get_generated_sources():
            if isinstance(obj, RustBindgenTarget):
                target_name = resolve_target_name(obj, project_config)
                dep = ConvertId(target_name, obj.subdir)
                if dep not in self.generated_sources:
                    self.generated_sources.append(dep)
                continue
            elif isinstance(obj, build.CustomTargetIndex) and isinstance(
                obj.target, RustBindgenTarget
            ):
                target_name = resolve_target_name(obj.target, project_config)
                dep = ConvertId(target_name, obj.target.subdir)
                if self.rust_abi is RustABI.NONE and is_bindgen_inline_wrapper(obj):
                    wrapper = (dep, obj.output)
                    if wrapper not in self.bindgen_inline_wrappers:
                        self.bindgen_inline_wrappers.append(wrapper)
                elif dep not in self.generated_sources:
                    self.generated_sources.append(dep)
                continue
            elif isinstance(obj, build.CustomTarget):
                targets_to_process.append((obj, obj.outputs))
                targets_to_process.extend(
                    (extra_dep, extra_dep.outputs)
                    for extra_dep in obj.extra_depends
                    if isinstance(extra_dep, build.CustomTarget)
                )
            elif isinstance(obj, build.CustomTargetIndex):
                targets_to_process.append((obj.target, [obj.output]))

            for target, outputs in targets_to_process:
                sanitized_name = resolve_target_name(target, project_config)
                info = target_mapping[sanitized_name]
                info.subdir = target.subdir
                info.files_type |= _determine_files_type(outputs)

        for sanitized_name, info in target_mapping.items():
            dep = ConvertId(sanitized_name, info.subdir)

            if info.files_type & GeneratedFilesType.HEADERS:
                self.generated_headers.append(dep)
            if info.files_type & GeneratedFilesType.IMPL:
                self.generated_sources.append(dep)

    def _handle_internal_dependencies(self, backend: Backend, build_target: build.BuildTarget,
                                      project_config: ConvertProjectConfig) -> None:  # fmt: skip
        for target in build_target.link_whole_targets:
            if not isinstance(target, build.BuildTarget):
                continue
            dep_rust_abi = _determine_rust_abi(target)
            if _rust_dependency_mismatch(self.rust_abi, dep_rust_abi):
                continue

            sanitized_name = resolve_target_name(target, project_config)
            if isinstance(target, build.BuildTarget):
                self.whole_static_libs.append(ConvertId(sanitized_name, target.subdir))

        for linked_target in backend.get_all_linked_targets(build_target):
            if not isinstance(linked_target, build.BuildTarget):
                continue
            dep_rust_abi = _determine_rust_abi(linked_target)
            if _rust_dependency_mismatch(self.rust_abi, dep_rust_abi):
                continue

            sanitized_name = resolve_target_name(linked_target, project_config)
            dep = ConvertId(sanitized_name, linked_target.subdir)
            if isinstance(linked_target, build.StaticLibrary):
                if self.rust_abi is not RustABI.NONE and dep_rust_abi is not RustABI.NONE:
                    self.rust_libs.append(dep)
                elif dep not in self.static_libs or self.whole_static_libs:
                    self.static_libs.append(dep)

                if isinstance(build_target, (build.SharedLibrary, build.Executable)):
                    for d in linked_target.external_deps:
                        if d.found() and isinstance(d, dependency_base.ExternalDependency):
                            self._add_external_dep(d, project_config, shared_only=True)
            elif isinstance(linked_target, build.SharedLibrary):
                if dep_rust_abi is RustABI.PROC_MACRO:
                    if dep not in self.proc_macros:
                        self.proc_macros.append(dep)
                elif dep not in self.shared_libs:
                    self.shared_libs.append(dep)

    def _handle_linker_args(self, build_info: build.Build, build_target: build.BuildTarget,
                            project_instance: ConvertProjectInstance,
                            project_config: ConvertProjectConfig) -> None:  # fmt: skip
        for language in build_target.compilers.keys():
            if self.rust_abi is not RustABI.NONE and language != 'rust':
                continue
            compiler = build_target.compilers[language]
            project_link_args = build_info.get_project_link_args(compiler, build_target)

            if project_link_args:
                name = f'{project_config.project_name}_{language}_link_args'
                flag = ConvertInstanceFlag(name, '', language, FlagScope.PROJECT)
                for arg in project_link_args:
                    flag.add_link_arg(arg)
                self.generated_flags[name] = flag

            filtered_link_args = []
            for arg in build_target.link_args:
                # Meson should really support version scripts to avoid special cases, such as here.
                # https://github.com/mesonbuild/meson/issues/3047
                if arg == '-Wl,--version-script':
                    continue

                normalized_string = project_instance.normalize_string(arg, self.subdir)
                if normalized_string != arg:
                    # Version script detected
                    if normalized_string.startswith('@@PROJECT_DIR@@/'):
                        normalized_string = normalized_string.replace('@@PROJECT_DIR@@/', '')
                    else:
                        normalized_string = normalized_string.replace('@@PROJECT_DIR@@', '')

                    subdir, filename = os.path.split(normalized_string)

                    file = File.from_source_file(project_instance.project_dir, subdir, filename)  # noqa #fmt: skip
                    # FIXME: Things work fine without linker scripts on Soong, but we should
                    # use them when available.
                    # (fg_name, subdir) = project_instance.determine_filegroup(file)
                    # self.linker_version_script = ConvertId(fg_name, subdir)
                    continue

                filtered_link_args.append(arg)

            for arg in filtered_link_args:
                if arg in project_link_args:
                    continue

                assignment = project_instance.interpreter_info.lookup_full_assignment(arg)
                if assignment is not None:
                    name, subdir = assignment
                    name = sanitize_target_name(name, project_config)
                    if name in self.generated_flags:
                        self.generated_flags[name].add_link_arg(arg)
                    else:
                        flag = ConvertInstanceFlag(name, subdir, language, FlagScope.SHARED)
                        flag.add_link_arg(arg)
                        self.generated_flags[name] = flag

    def _sanitize_rust_cfgs(self, arg_idx: int, args: T.List[str]) -> T.Tuple[int, bool]:
        # Multiple Rust cfgs such as:
        #
        #    cfg1 = ["--cfg", "my_cfg1"]
        #    cfg2 = ["--cfg", "my_cfg2"]
        #    cfg3 = ["--cfg=my_cfg2"]
        #
        # confuses our name tracking method.  For example, does the "--cfg" string belong to
        # cfg1 or cfg2?
        rs_cfg = False
        if self.rust_abi is not RustABI.NONE:
            if args[arg_idx] == '--cfg':
                # The next arg will be the cfg
                arg_idx += 1
                rs_cfg = True
            elif args[arg_idx].startswith('--cfg='):
                args[arg_idx] = args[arg_idx].removeprefix('--cfg=')
                rs_cfg = True

        return (arg_idx, rs_cfg)

    def _handle_compile_args(self, build_info: build.Build, build_target: build.BuildTarget,
                             project_instance: ConvertProjectInstance,
                             project_config: ConvertProjectConfig) -> None:  # fmt: skip
        for language in build_target.compilers.keys():
            if self.rust_abi is not RustABI.NONE and language != 'rust':
                continue
            compiler = build_target.compilers[language]
            project_args = build_info.get_project_args(compiler, build_target)
            if project_args:
                name = f'{project_config.project_name}_{language}_project_args'
                flag = ConvertInstanceFlag(name, '', language, FlagScope.PROJECT)

                for arg in project_args:
                    # Assume Rust cfgs are never in global project args.  This may be a bad
                    # assumption
                    flag.add_compile_arg(arg, False)

                self.generated_flags[name] = flag

            extra_args = build_target.get_extra_args(language) + self.compile_args_deps

            if build_target.gnu_symbol_visibility == 'hidden' and self.rust_abi is RustABI.NONE:  # fmt: skip
                extra_args += ['-fvisibility=hidden']

            arg_idx = 0
            if extra_args:
                while arg_idx < len(extra_args):
                    if extra_args[arg_idx] in project_args:
                        arg_idx += 1
                        continue

                    if self.rust_abi is RustABI.PROC_MACRO:
                        end = arg_idx + 2
                        if extra_args[arg_idx:end] == ['--extern', 'proc_macro']:
                            arg_idx = end
                            continue

                    arg_idx, rs_cfg = self._sanitize_rust_cfgs(arg_idx, extra_args)

                    arg = extra_args[arg_idx]
                    assignment = project_instance.interpreter_info.lookup_full_assignment(arg)
                    if assignment is not None:
                        name, subdir = assignment
                        name = sanitize_target_name(name, project_config)
                        scope = FlagScope.SHARED
                    else:
                        name = f'{build_target.name}_{language}_flags'
                        subdir = self.subdir
                        scope = FlagScope.TARGET

                    if name in self.generated_flags:
                        self.generated_flags[name].add_compile_arg(arg, rs_cfg)
                    else:
                        flag = ConvertInstanceFlag(name, subdir, language, scope)
                        flag.add_compile_arg(arg, rs_cfg)
                        self.generated_flags[name] = flag

                    arg_idx += 1

    def _handle_language_standards(self, build_target: build.BuildTarget) -> None:
        # This **may** need to handle build_target.for_machine.  However, differing
        # language standards given machine targets are rare in actual meson.build files,
        # so ignore for now.
        if 'c' in build_target.compilers:
            c_std = build_target.environment.coredata.get_option_for_target(
                build_target, OptionKey('c_std')
            )
            if c_std and c_std != 'none':
                self.c_std = str(c_std)

        if 'cpp' in build_target.compilers:
            cpp_std = build_target.environment.coredata.get_option_for_target(
                build_target, OptionKey('cpp_std')
            )
            if cpp_std and cpp_std != 'none':
                self.cpp_std = str(cpp_std)

        if self.rust_abi is not RustABI.NONE:
            edition = build_target.environment.coredata.get_option_for_target(
                build_target, OptionKey('rust_std')
            )
            if edition:
                self.rust_edition = str(edition)


class ConvertInstanceStaticLibrary(ConvertInstanceBuildTarget):
    pass


class ConvertInstanceSharedLibrary(ConvertInstanceBuildTarget):
    pass


class ConvertInstanceExecutable(ConvertInstanceBuildTarget):
    pass


ConvertInstanceBuildTargetType: T.TypeAlias = T.Union[
    ConvertInstanceExecutable, ConvertInstanceStaticLibrary, ConvertInstanceSharedLibrary
]
