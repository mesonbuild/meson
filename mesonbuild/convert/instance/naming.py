#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import os
import re
import typing as T

from mesonbuild import build
from mesonbuild.modules.rust import RustBindgenTarget
from mesonbuild.convert.convert_project_config import ConvertProjectConfig


def sanitize_target_name(target_name: str, project_config: ConvertProjectConfig) -> str:
    if target_name in project_config.target_renames:
        return project_config.target_renames[target_name]
    return target_name.translate(str.maketrans('', '', '[]'))


def include_dir_name(subdir: str) -> str:
    return 'inc_' + subdir.replace('/', '_')


def resolve_include_dir_name(subdir: str, project_config: ConvertProjectConfig,
                             assigned_name: T.Optional[str] = None) -> str:  # fmt: skip
    name = assigned_name or include_dir_name(subdir)
    return sanitize_target_name(name, project_config)


def python_binary_name(name: str, project_config: ConvertProjectConfig) -> str:
    if name.endswith(('gen.py', 'gen_py')):
        binary_name = name[:-6] + 'py_binary'
    elif name.endswith(('.py', '_py')):
        binary_name = name[:-3] + '_py_binary'
    else:
        binary_name = name + '_py_binary'
    return sanitize_target_name(binary_name, project_config)


def filegroup_name(fname: str, assigned_name: T.Optional[str],
                   target_name: T.Optional[str]) -> str:  # fmt: skip
    if assigned_name:
        return assigned_name
    if target_name:
        return target_name + '_fg'
    root, ext = os.path.splitext(fname)
    return os.path.basename(root) + '_' + ext[1:]


def is_bindgen_inline_wrapper(src: build.GeneratedTypes) -> bool:
    if not (isinstance(src, build.CustomTargetIndex) and isinstance(src.target, RustBindgenTarget)):
        return False
    inline_wrapper = src.target.original_kwargs['output_inline_wrapper']
    return bool(inline_wrapper) and src.output == inline_wrapper


def _needs_lib_prefix(target: build.BuildTarget) -> bool:
    # - [Soong rule] Rust library modules (rlib, FFI, proc-macro) must start with 'lib<crate_name>'.
    if target.uses_rust():
        return target.original_kwargs.get('rust_crate_type') in {
            'rlib',
            'cdylib',
            'staticlib',
            'proc-macro',
        }
    # Is target a StaticLibrary, and does it compile the static_inline wrapper of a RustBindgenTarget?
    # C static_inline_library modules for rust_bindgen are linked via rustc's
    #   '-lstatic:+whole-archive=<name>', which requires a 'lib*.a' output filename.
    return isinstance(target, build.StaticLibrary) and any(
        is_bindgen_inline_wrapper(src) for src in target.get_generated_sources()
    )


def bindgen_crate_name(target: RustBindgenTarget) -> str:
    return re.sub(r'[^a-zA-Z0-9_]', '_', target.name)


def resolve_target_name(target: build.Target, project_config: ConvertProjectConfig) -> str:
    if isinstance(target, RustBindgenTarget):
        crate_name = bindgen_crate_name(target)
        return sanitize_target_name(f'lib{crate_name}', project_config)
    if isinstance(target, build.BuildTarget):
        sanitized_name = sanitize_target_name(target.get_basename(), project_config)
        if _needs_lib_prefix(target) and not sanitized_name.startswith('lib'):
            return 'lib' + sanitized_name
        return sanitized_name
    return sanitize_target_name(target.name, project_config)


def structured_sources_name(owner: build.BuildTarget,
                            project_config: ConvertProjectConfig) -> str:  # fmt: skip
    return f'{resolve_target_name(owner, project_config)}_structured_srcs'
