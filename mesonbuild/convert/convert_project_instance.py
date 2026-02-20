#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T
from pathlib import Path
import os
import sys

from mesonbuild import mlog
from mesonbuild.convert.common_defs import ProjectOptionsInstance
from mesonbuild.convert.convert_interpreter_info import ConvertInterpreterInfo


class ConvertProjectInstance:
    """A single meson project configuration.  A meson convert invocation can have multiple meson configurations"""

    def __init__(
        self,
        name: str,
        host_toolchain: str,
        build_toolchain: str,
        option_instance: ProjectOptionsInstance,
    ):
        self.name = name
        self.host_toolchain = host_toolchain
        self.build_toolchain = build_toolchain
        self.option_instance = option_instance

        self.project_dir: str = ''
        self.install_dir: str = ''
        self.build_dir: str = ''

        self.interpreter_info: ConvertInterpreterInfo = ConvertInterpreterInfo()

    def set_directories(self, project_dir: str, build_dir: str, install_dir: str) -> None:
        self.project_dir = project_dir
        self.build_dir = build_dir
        self.install_dir = install_dir

    def emit(self) -> None:
        mlog.set_verbose()
        mlog.log(f'Processing config: {self.name}')
        mlog.log(f"""  Processing -- host toolchain: {self.host_toolchain}, build toolchain:
            {self.build_toolchain}, custom variables {self.option_instance.select_instances}""")
        mlog.set_quiet()

    def normalize_path(self, path: str, current_subdir: str) -> str:
        prospective_path = Path(self.project_dir) / current_subdir / path
        abs_path = os.path.normpath(str(prospective_path))

        if os.path.exists(abs_path):
            relative_path = os.path.relpath(abs_path, self.project_dir)
            return relative_path
        else:
            sys.exit(f'Unknown path: {abs_path}')

    def normalize_file_path(self, file_path: str, current_subdir: str) -> str:
        path = self.normalize_path(file_path, current_subdir)
        return os.path.dirname(path)

    def normalize_string(self, input_string: str, current_subdir: str) -> T.Optional[str]:
        gen_dir = self.build_dir + '/' + current_subdir
        if gen_dir in input_string:
            sanitized = input_string.replace(gen_dir, '@@GEN_DIR@@')
            return sanitized

        if self.install_dir in input_string:
            sanitized = input_string.replace(self.install_dir, '@@INSTALL_DIR@@')
            return sanitized

        if self.build_dir in input_string:
            sanitized = input_string.replace(self.build_dir, '@@BUILD_DIR@@')
            return sanitized

        if self.project_dir in input_string:
            sanitized = input_string.replace(self.project_dir, '@@PROJECT_DIR@@')
            return sanitized

        return input_string
