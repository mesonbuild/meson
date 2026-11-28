#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T

from mesonbuild import build
from mesonbuild.dependencies import base as dependency_base
from mesonbuild.mesonlib import File, MesonException
from mesonbuild.options import OptionKey
from mesonbuild.modules.rust import RustBindgenTarget

from mesonbuild.convert.common_defs import ExternalDepKind, FlagScope
from mesonbuild.convert.convert_project_config import ConvertProjectConfig
from mesonbuild.convert.convert_project_instance import ConvertProjectInstance
from mesonbuild.convert.instance.convert_instance_utils import ConvertId, ConvertInstanceFlag
from mesonbuild.convert.instance.naming import bindgen_crate_name, resolve_target_name


def _scrub_bindgen_args(raw_args: T.List[str]) -> T.List[str]:
    # Strip --clang-macro-fallback-build-dir (typically paired with Meson's
    # @PRIVATE_DIR@ placeholder to avoid temp-file races across parallel Ninja
    # jobs sharing one build directory). Hermetic build systems (Soong/Bazel)
    # isolate each bindgen action in its own sandbox/working directory and do
    # not expand Meson placeholders.
    scrubbed: T.List[str] = []
    idx = 0
    while idx < len(raw_args):
        if raw_args[idx] == '--clang-macro-fallback-build-dir':
            idx += 2
            continue
        scrubbed.append(raw_args[idx])
        idx += 1
    return scrubbed


class ConvertInstanceRustBindgen:
    """A representation of RustBindgenTarget, optimized for the convert tool"""

    def __init__(self, bindgen_target: RustBindgenTarget,
                 project_instance: ConvertProjectInstance,
                 project_config: ConvertProjectConfig) -> None:  # fmt: skip
        self.subdir = bindgen_target.subdir
        self.target_name: str = ''
        self.crate_name: str = ''
        self.header: ConvertId = ConvertId('', '')
        self.output: str = bindgen_target.outputs[0]

        self.args: T.List[str] = []
        self.c_args: T.List[str] = []
        self.include_dirs: T.List[str] = []
        self.rust_libs: T.List[ConvertId] = []
        self.generated_headers: T.List[ConvertId] = []
        self.generated_flags: T.Dict[str, ConvertInstanceFlag] = {}

        self.c_std: T.Optional[str] = None
        self.rust_edition: T.Optional[str] = None

        self._project_args: T.List[str] = []
        self._parse_bindgen_target(bindgen_target, project_instance, project_config)

    def _parse_bindgen_target(self, bindgen_target: RustBindgenTarget,
                              project_instance: ConvertProjectInstance,
                              project_config: ConvertProjectConfig) -> None:  # fmt: skip
        self._handle_naming(bindgen_target, project_config)
        self._handle_header(bindgen_target, project_instance)
        self._handle_include_dirs(bindgen_target, project_instance)
        self._handle_bindgen_args(bindgen_target)
        self._handle_project_flags(bindgen_target, project_config)
        self._handle_dependencies(bindgen_target, project_instance, project_config)
        self._handle_language_standards(bindgen_target)

    def _handle_naming(self, bindgen_target: RustBindgenTarget,
                       project_config: ConvertProjectConfig) -> None:  # fmt: skip
        self.crate_name = bindgen_crate_name(bindgen_target)
        self.target_name = resolve_target_name(bindgen_target, project_config)

    def _handle_header(self, bindgen_target: RustBindgenTarget,
                       project_instance: ConvertProjectInstance) -> None:  # fmt: skip
        header_src = bindgen_target.sources[0]
        if not isinstance(header_src, File):
            raise MesonException(f'Unsupported bindgen header type: {type(header_src).__name__}')
        fg_name, fg_subdir = project_instance.determine_filegroup(header_src)
        self.header = ConvertId(fg_name, fg_subdir)

    def _handle_include_dirs(self, bindgen_target: RustBindgenTarget,
                             project_instance: ConvertProjectInstance) -> None:  # fmt: skip
        for inc in bindgen_target.original_kwargs['include_directories']:
            if isinstance(inc, build.IncludeDirs):
                inc_name = project_instance.determine_include_dir(inc)
                if inc_name not in self.include_dirs:
                    self.include_dirs.append(inc_name)

    def _handle_bindgen_args(self, bindgen_target: RustBindgenTarget) -> None:
        raw_args = list(bindgen_target.original_kwargs['args'])
        self.args = [arg.replace('"', '\\"') for arg in _scrub_bindgen_args(raw_args)]

    def _handle_project_flags(self, bindgen_target: RustBindgenTarget,
                              project_config: ConvertProjectConfig) -> None:  # fmt: skip
        self._project_args = bindgen_target.build_project.project_args.host.get('c', [])
        if not self._project_args:
            return

        flag_name = f'{project_config.project_name}_c_project_args'
        flag = ConvertInstanceFlag(flag_name, '', 'c', FlagScope.PROJECT)
        for arg in self._project_args:
            flag.add_compile_arg(arg, False)
        self.generated_flags[flag_name] = flag

    def _add_external_dep(self, dep: dependency_base.ExternalDependency,
                          project_config: ConvertProjectConfig) -> None:  # fmt: skip
        if not dep.found():
            return

        found = project_config.lookup_external_dependency(dep.name)
        if not found:
            return

        ext_dep, kind = found
        if kind is ExternalDepKind.RUST and ext_dep not in self.rust_libs:
            self.rust_libs.append(ext_dep)

    def _add_internal_dep(self, dep: dependency_base.InternalDependency,
                          project_instance: ConvertProjectInstance,
                          project_config: ConvertProjectConfig) -> None:  # fmt: skip
        for inc in dep.get_include_dirs():
            inc_name = project_instance.determine_include_dir(inc)
            if inc_name not in self.include_dirs:
                self.include_dirs.append(inc_name)

        for arg in dep.get_all_compile_args():
            if arg not in self._project_args:
                escaped = arg.replace('"', '\\"')
                if escaped not in self.c_args:
                    self.c_args.append(escaped)

        for src in dep.get_sources():
            if (isinstance(src, build.CustomTarget)
                    and any(o.endswith(('.h', '.hpp')) for o in src.outputs)):  # fmt: skip
                gen_dep = ConvertId(resolve_target_name(src, project_config), src.subdir)
                if gen_dep not in self.generated_headers:
                    self.generated_headers.append(gen_dep)

    def _handle_dependencies(self, bindgen_target: RustBindgenTarget,
                             project_instance: ConvertProjectInstance,
                             project_config: ConvertProjectConfig) -> None:  # fmt: skip
        for dep in bindgen_target.original_kwargs['dependencies']:
            if isinstance(dep, dependency_base.ExternalDependency):
                self._add_external_dep(dep, project_config)
            elif isinstance(dep, dependency_base.InternalDependency):
                self._add_internal_dep(dep, project_instance, project_config)

    def _handle_language_standards(self, bindgen_target: RustBindgenTarget) -> None:
        optstore = bindgen_target.environment.coredata.optstore
        c_std = optstore.get_value_for(OptionKey('c_std', bindgen_target.subproject))
        if isinstance(c_std, str) and c_std != 'none':
            self.c_std = c_std

        rust_std = optstore.get_value_for(OptionKey('rust_std', bindgen_target.subproject))
        if isinstance(rust_std, str) and rust_std != 'none':
            self.rust_edition = rust_std
