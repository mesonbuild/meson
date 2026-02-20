#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T
import os
from collections import defaultdict

from mesonbuild import build
from mesonbuild.mesonlib import File
from mesonbuild.dependencies import base as dependency_base
from mesonbuild.options import OptionKey
from enum import Enum, IntFlag

from mesonbuild.convert.instance.convert_instance_utils import (
    ConvertInstanceFlag,
    ConvertInstanceIncludeDirectory,
    ConvertInstanceFileGroup,
)
from mesonbuild.convert.convert_project_instance import ConvertProjectInstance
from mesonbuild.convert.convert_project_config import ConvertProjectConfig


class RustABI(Enum):
    RUST = 'rust'
    C = 'c'
    NONE = None


class GeneratedFilesType(IntFlag):
    UNKNOWN = 0
    HEADERS = 1
    IMPL = 2
    HEADERS_AND_IMPL = 3  # pylint: disable=implicit-flag-alias


def _determine_name(original_name: str, project_config: ConvertProjectConfig,
                    rust_abi: RustABI) -> str:
    # Soong has a separation of module name and crate_name.  If the crate_name is 'serde', then
    # the module_name must be 'libserde'.  Rust binaries are ignored for now by this tool.
    if rust_abi != RustABI.NONE:
        if not original_name.startswith('lib'):
            return 'lib' + original_name
        return original_name
    else:
        return project_config.sanitize_target_name(original_name)


def _determine_rust_abi(build_target: build.BuildTarget) -> RustABI:
    rust_abi = build_target.original_kwargs.get('rust_abi')
    if rust_abi:
        return RustABI(rust_abi)

    return RustABI.NONE


def _determine_files_type(outputs: T.List[str]) -> GeneratedFilesType:
    files_type: GeneratedFilesType = GeneratedFilesType.UNKNOWN
    for output in outputs:
        if output.endswith('.h') or output.endswith('.hpp'):
            files_type |= GeneratedFilesType.HEADERS
        else:
            files_type |= GeneratedFilesType.IMPL

    return files_type


class ConvertInstanceBuildTarget:
    """A representation of build.BuildTarget, but optimized for the convert tool"""

    def __init__(
        self,
        build_info: build.Build,
        build_target: build.BuildTarget,
        project_instance: ConvertProjectInstance,
        project_config: ConvertProjectConfig,
    ):
        self.name: str = ''

        self.static_libs: T.List[str] = []
        self.rust_abi: RustABI = RustABI.NONE
        self.crate_root: str = ''
        self.crate_name: str = ''
        self.src_subdirs: T.Set[str] = set()
        self.rust_edition: T.Optional[str] = None
        self.proc_macros: T.List[str] = []

        self.srcs: T.List[str] = []
        self.header_libs: T.List[str] = []
        self.shared_libs: T.List[str] = []
        self.whole_static_libs: T.List[str] = []
        self.generated_headers: T.List[str] = []
        self.generated_sources: T.List[str] = []
        self.c_std: T.Optional[str] = None
        self.cpp_std: T.Optional[str] = None

        self.compile_args_deps: T.List[str] = []
        self.link_args_deps: T.List[str] = []
        self.linker_version_script_name: T.Optional[str] = None

        self.generated_filegroups: T.Dict[str, ConvertInstanceFileGroup] = {}
        self.generated_include_dirs: T.Dict[str, ConvertInstanceIncludeDirectory] = {}
        self.generated_flags: T.Dict[str, ConvertInstanceFlag] = {}
        self.generated_linker_flags: T.Dict[str, ConvertInstanceFlag] = {}

        self.subdir = build_target.subdir
        self.machine_choice = build_target.for_machine
        self.install = build_target.install
        self._parse_build_target(build_info, build_target, project_instance, project_config)

    def _parse_build_target(
        self,
        build_info: build.Build,
        build_target: build.BuildTarget,
        project_instance: ConvertProjectInstance,
        project_config: ConvertProjectConfig,
    ) -> None:
        """
        Main entry point for processing a `build.BuildTarget`.

        This method serves as a dispatcher that orchestrates the parsing of a raw
        `build.BuildTarget` from Meson. It calls various specialized `_handle_*`
        methods to translate all relevant properties of the target—such as its
        name, sources, dependencies (both internal and external), include
        directories, and compiler/linker flags—into the build-system-agnostic
        representation used by the converter.
        """
        self._handle_naming(build_target, project_config)
        self._handle_sources(build_target, project_instance)
        self._handle_generated_sources(build_target, project_config)
        self._handle_external_dependencies(build_target, project_config)
        self._handle_internal_dependencies(build_target, project_config)
        self._handle_include_dirs(build_target, project_instance)
        self._handle_compile_args(build_info, build_target, project_instance, project_config)
        self._handle_linker_args(build_info, build_target, project_instance, project_config)
        self._handle_language_standards(build_target)

    def _handle_naming(
        self,
        build_target: build.BuildTarget,
        project_config: ConvertProjectConfig,
    ) -> None:
        self.rust_abi = _determine_rust_abi(build_target)
        if self.rust_abi != RustABI.NONE:
            self.crate_name = build_target.get_basename()
        self.name = _determine_name(build_target.get_basename(), project_config, self.rust_abi)

    def _handle_sources(
        self,
        build_target: build.BuildTarget,
        project_instance: ConvertProjectInstance,
    ) -> None:
        for file in build_target.sources:
            if not isinstance(file, File):
                continue
            fg_name = project_instance.interpreter_info.lookup_assignment(file)
            if fg_name is not None and file.subdir != self.subdir:
                if file.fname.endswith('.h'):
                    fg_name = fg_name + '_headers'
                    if fg_name in self.generated_include_dirs:
                        self.generated_include_dirs[fg_name].add_header_file(file, project_instance)
                    else:
                        directory = ConvertInstanceIncludeDirectory(fg_name)
                        directory.add_header_file(file, project_instance)
                        self.generated_include_dirs[directory.name] = directory
                else:
                    fg_name = fg_name + '_impl'
                    if fg_name in self.generated_filegroups:
                        self.generated_filegroups[fg_name].add_source_file(file, project_instance)
                    else:
                        filegroup = ConvertInstanceFileGroup(name=fg_name)
                        filegroup.add_source_file(file, project_instance)
                        self.generated_filegroups[fg_name] = filegroup
                        self.srcs.append(':' + filegroup.name)
            else:
                if not file.fname.endswith('.h') and not file.fname.endswith('.hpp'):
                    self.srcs.append(file.fname)

        if self.rust_abi != RustABI.NONE:
            for s in self.srcs:
                if os.path.basename(s) == 'lib.rs':
                    self.crate_root = s
                    break
            if not self.crate_root and self.srcs:
                self.crate_root = self.srcs[0]

            for s in self.srcs:
                self.src_subdirs.add(os.path.dirname(s))

    def _handle_external_dependencies(
        self,
        build_target: build.BuildTarget,
        project_config: ConvertProjectConfig,
    ) -> None:
        for d in build_target.external_deps:
            if d.found() and isinstance(d, dependency_base.ExternalDependency):
                dep_info = (project_config.dependencies.shared_libraries.get(d.name)
                            or project_config.dependencies.static_libraries.get(d.name)
                            or project_config.dependencies.header_libraries.get(d.name))

                if not project_config.is_dependency_necessary(d.name):
                    continue

                assert dep_info is not None
                target_name = dep_info[0].get('target_name')
                is_proc_macro = dep_info[0].get('proc_macro', False)

                if d.name in project_config.dependencies.header_libraries:
                    self.header_libs.append(target_name)
                elif d.name in project_config.dependencies.static_libraries:
                    if is_proc_macro:
                        self.proc_macros.append(target_name)
                    else:
                        self.static_libs.append(target_name)
                else:
                    if project_config.is_dependency_necessary(target_name):
                        self.shared_libs.append(target_name)
            elif isinstance(d, dependency_base.InternalDependency):
                # meson likes to put link + compile args as internal dependencies
                # for some reason
                self.compile_args_deps.extend(d.get_compile_args())
                self.link_args_deps.extend(d.get_link_args())

    def _handle_include_dirs(
        self,
        build_target: build.BuildTarget,
        project_instance: ConvertProjectInstance,
    ) -> None:
        for include_dir in build_target.include_dirs:
            directory_name = project_instance.interpreter_info.lookup_assignment(include_dir)
            if directory_name is not None:
                if directory_name in self.generated_include_dirs:
                    self.generated_include_dirs[directory_name].add_include_dir(
                        include_dir, project_instance)
                else:
                    directory = ConvertInstanceIncludeDirectory(directory_name)
                    directory.add_include_dir(include_dir, project_instance)
                    self.generated_include_dirs[directory.name] = directory
            else:
                directory = ConvertInstanceIncludeDirectory()
                directory.add_include_dir(include_dir, project_instance)
                if directory.name not in self.generated_include_dirs:
                    self.generated_include_dirs[directory.name] = directory
                else:
                    self.generated_include_dirs[directory.name].add_include_dir(
                        include_dir, project_instance)

    def _handle_generated_sources(
        self,
        build_target: build.BuildTarget,
        project_config: ConvertProjectConfig,
    ) -> None:
        target_mapping: T.Dict[str,
                               GeneratedFilesType] = defaultdict(lambda: GeneratedFilesType.UNKNOWN)
        for obj in build_target.get_generated_sources():
            if isinstance(obj, build.CustomTarget):
                # Is there a better way to do this?
                for dep in obj.extra_depends:
                    if isinstance(dep, build.CustomTarget):
                        target_mapping[dep.name] |= _determine_files_type(
                            T.cast(T.List[str], dep.outputs))

                target_mapping[obj.name] |= _determine_files_type(T.cast(T.List[str], obj.outputs))
            elif isinstance(obj, build.CustomTargetIndex):
                custom_target = obj.target
                index = custom_target.outputs.index(obj.output)
                output = custom_target.outputs[index]
                target_mapping[custom_target.name] |= _determine_files_type([T.cast(str, output)])

        for target_name, files_type in target_mapping.items():
            sanitized_name = _determine_name(target_name, project_config, self.rust_abi)
            if files_type & GeneratedFilesType.HEADERS != 0:
                self.generated_headers.append(sanitized_name)
            if files_type & GeneratedFilesType.IMPL != 0:
                self.generated_sources.append(sanitized_name)

    def _handle_internal_dependencies(
        self,
        build_target: build.BuildTarget,
        project_config: ConvertProjectConfig,
    ) -> None:
        for target in build_target.link_whole_targets:
            if not isinstance(target, build.BuildTarget):
                continue
            target_rust_abi = _determine_rust_abi(target)
            if (self.rust_abi == RustABI.NONE and target_rust_abi == RustABI.RUST):
                continue

            sanitized_name = _determine_name(target.name, project_config, target_rust_abi)
            if isinstance(target, build.BuildTarget):
                self.whole_static_libs.append(sanitized_name)

        for linked_target in build_target.get_all_linked_targets():
            if not isinstance(linked_target, build.BuildTarget):
                continue
            target_rust_abi = _determine_rust_abi(linked_target)
            if (self.rust_abi == RustABI.NONE and target_rust_abi == RustABI.RUST):
                continue

            sanitized_name = _determine_name(linked_target.name, project_config, target_rust_abi)
            if isinstance(linked_target, build.StaticLibrary):
                if (sanitized_name not in self.static_libs or self.whole_static_libs):
                    self.static_libs.append(sanitized_name)
            elif isinstance(linked_target, build.SharedLibrary):
                if sanitized_name not in self.shared_libs:
                    self.shared_libs.append(sanitized_name)

    def _handle_linker_args(
        self,
        build_info: build.Build,
        build_target: build.BuildTarget,
        project_instance: ConvertProjectInstance,
        project_config: ConvertProjectConfig,
    ) -> None:
        for language in build_target.compilers.keys():
            compiler = build_target.compilers[language]
            project_link_args = build_info.get_project_link_args(compiler, build_target.subproject,
                                                                 build_target.for_machine)

            if project_link_args:
                name = f'{project_config.project_name}_{language}_link_args'
                flag = ConvertInstanceFlag(name, '', language)
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
                    if (normalized_string is not None
                            and normalized_string.startswith('@@PROJECT_DIR@@/')):
                        normalized_string = normalized_string.replace('@@PROJECT_DIR@@/', '')
                    elif normalized_string is not None:
                        normalized_string = normalized_string.replace('@@PROJECT_DIR@@', '')
                    else:
                        continue

                    subdir, filename = os.path.split(normalized_string)
                    file = File.from_source_file(project_instance.project_dir, subdir, filename)

                    filegroup = ConvertInstanceFileGroup()
                    filegroup.add_source_file(file, project_instance)
                    self.generated_filegroups[filegroup.name] = filegroup
                    self.linker_version_script_name = ':' + filegroup.name
                    continue

                filtered_link_args.append(arg)

            for arg in filtered_link_args:
                if arg in project_link_args:
                    continue

                assignment = project_instance.interpreter_info.lookup_full_assignment(arg)
                if assignment is not None:
                    name, subdir = assignment
                    if name in self.generated_flags:
                        self.generated_flags[name].add_link_arg(arg)
                    else:
                        flag = ConvertInstanceFlag(name, subdir, language)
                        flag.add_link_arg(arg)
                        self.generated_flags[name] = flag

    def _handle_compile_args(
        self,
        build_info: build.Build,
        build_target: build.BuildTarget,
        project_instance: ConvertProjectInstance,
        project_config: ConvertProjectConfig,
    ) -> None:
        for language in build_target.compilers.keys():
            compiler = build_target.compilers[language]
            project_args = build_info.get_project_args(compiler, build_target.subproject,
                                                       build_target.for_machine)

            if project_args:
                name = f'{project_config.project_name}_{language}_project_args'
                flag = ConvertInstanceFlag(name, '', language)
                if language in {'c', 'cpp'}:
                    flag.project_native_args = True

                for arg in project_args:
                    flag.add_compile_arg(arg)

                self.generated_flags[name] = flag

            extra_args = build_target.get_extra_args(language) + self.compile_args_deps
            if extra_args:
                for arg in extra_args:
                    if arg in project_args:
                        continue

                    assignment = project_instance.interpreter_info.lookup_full_assignment(arg)
                    if assignment is not None:
                        name, subdir = assignment
                    else:
                        name = f'{build_target.name}_{language}_flags'
                        subdir = self.subdir

                    if name in self.generated_flags:
                        self.generated_flags[name].add_compile_arg(arg)
                    else:
                        flag = ConvertInstanceFlag(name, subdir, language)
                        flag.add_compile_arg(arg)
                        self.generated_flags[name] = flag

    def _handle_language_standards(self, build_target: build.BuildTarget) -> None:
        if 'c' in build_target.compilers:
            c_std = build_target.environment.coredata.get_option_for_target(
                build_target, OptionKey('c_std'))
            if c_std and c_std != 'none':
                self.c_std = str(c_std)

        if 'cpp' in build_target.compilers:
            cpp_std = build_target.environment.coredata.get_option_for_target(
                build_target, OptionKey('cpp_std'))
            if cpp_std and cpp_std != 'none':
                self.cpp_std = str(cpp_std)

        if self.rust_abi != RustABI.NONE:
            edition = build_target.environment.coredata.get_option_for_target(
                build_target, OptionKey('rust_std'))
            if edition:
                self.rust_edition = str(edition)


class ConvertInstanceStaticLibrary(ConvertInstanceBuildTarget):

    def __str__(self) -> str:
        return f'@StaticLibrary({self.name})'


class ConvertInstanceSharedLibrary(ConvertInstanceBuildTarget):

    def __str__(self) -> str:
        return f'@SharedLibrary({self.name})'


class ConvertInstanceExecutable(ConvertInstanceBuildTarget):

    def __str__(self) -> str:
        return f'@Executable({self.name})'
