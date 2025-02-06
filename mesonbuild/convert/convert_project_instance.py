#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T
from pathlib import Path
import os
import sys
from collections import defaultdict

from mesonbuild import build, mlog
from mesonbuild.mesonlib import File
from mesonbuild.convert.common_defs import ProjectOptionsInstance
from mesonbuild.convert.convert_interpreter_info import ConvertInterpreterInfo

from mesonbuild.convert.instance.convert_instance_utils import (
    ConvertInstanceFileGroup,
    ConvertInstanceIncludeDirectory,
    ConvertInstancePythonBinary,
    ConvertId,
    include_dir_name,
)


def _python_script_to_binary(name: str) -> str:
    if name.endswith('gen.py'):
        return name[:-6] + 'py_binary'
    if name.endswith('gen_py'):
        return name[:-6] + 'py_binary'
    if name.endswith('.py'):
        return name[:-3] + '_py_binary'
    if name.endswith('_py'):
        return name[:-3] + '_py_binary'
    return name + '_py_binary'


class ConvertProjectInstance:
    """A single meson project configuration.  A meson convert invocation can have multiple
    meson configurations"""

    def __init__(self, name: str, host_platform: str, build_platform: str,
                 option_instance: ProjectOptionsInstance,
                 python_libraries: T.List[str]):  # fmt: skip
        self.name = name
        self.host_platform = host_platform
        self.build_platform = build_platform
        self.option_instance = option_instance
        self.global_python_libs = python_libraries

        self.project_dir: str = ''
        self.install_dir: str = ''
        self.build_dir: str = ''

        self.shared_filegroups: T.Dict[str, ConvertInstanceFileGroup] = {}
        self.filegroup_variants: T.Dict[str, T.List[str]] = defaultdict(list)
        self.shared_include_dirs: T.Dict[str, ConvertInstanceIncludeDirectory] = {}
        self.python_binaries: T.Dict[ConvertId, ConvertInstancePythonBinary] = {}

        self.interpreter_info: ConvertInterpreterInfo = ConvertInterpreterInfo()

    def set_directories(self, project_dir: str, build_dir: str,
                        install_dir: str) -> None:  # fmt: skip
        self.project_dir = project_dir
        self.build_dir = build_dir
        self.install_dir = install_dir

    def emit(self) -> None:
        mlog.log(mlog.bold(f'Processing config: {self.name}'))
        mlog.log(mlog.normal_red(f'  Host platform: {self.host_platform}'))
        mlog.log(mlog.normal_blue(f'  Build platform: {self.build_platform}'))
        if self.option_instance.select_instances:
            vars_str = ', '.join([str(v) for v in self.option_instance.select_instances])
            mlog.log(mlog.normal_green(f'  Custom variables: [{vars_str}]'))

    def normalize_path(self, path: str, current_subdir: str) -> str:
        """
        Calculates path relative to the project root.


        Example input:
          path: "../..".
          current_subdir: "src/code/functions"

        Example output:
          "src/"
        """

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

    def normalize_string(self, input_string: str,
                         current_subdir: str) -> T.Optional[str]:  # fmt: skip
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

    def determine_include_dir(self, inc: build.IncludeDirs) -> str:
        inc_name = self.interpreter_info.lookup_assignment(inc)

        if not inc_name:
            inc_name = include_dir_name(inc.curdir)

        if inc_name not in self.shared_include_dirs:
            self.shared_include_dirs[inc_name] = ConvertInstanceIncludeDirectory(inc_name)

        new_paths: T.Set[str] = set()
        for directory in inc.incdirs:
            new_paths.add(self.normalize_path(directory, inc.curdir))

        self.shared_include_dirs[inc_name].add_new_paths(new_paths)

        return inc_name

    def determine_include_dir_from_file(self, file: File) -> str:
        subdir = self.normalize_file_path(file.fname, file.subdir)
        inc_name = include_dir_name(subdir)
        if inc_name not in self.shared_include_dirs:
            self.shared_include_dirs[inc_name] = ConvertInstanceIncludeDirectory.from_subdir(subdir)

        return inc_name

    def determine_filegroup(self, file: File,
                            target_name: T.Optional[str] = None) -> T.Tuple[str, str]:  # fmt: skip
        assigned_name = self.interpreter_info.lookup_assignment(file)
        subdir = self.normalize_file_path(file.fname, file.subdir)

        if assigned_name:
            fg_variant_key = assigned_name
        elif target_name:
            fg_variant_key = target_name + '_fg'
        else:
            root, ext = os.path.splitext(file.fname)
            fg_variant_key = os.path.basename(root) + '_' + ext[1:]

        if subdir not in self.filegroup_variants[fg_variant_key]:
            self.filegroup_variants[fg_variant_key].append(subdir)

        fg_name = fg_variant_key
        for index in range(len(self.filegroup_variants[fg_variant_key])):
            if subdir == self.filegroup_variants[fg_variant_key][index] and index != 0:
                fg_name += f'_{index}'
                break

        if fg_name not in self.shared_filegroups:
            self.shared_filegroups[fg_name] = ConvertInstanceFileGroup(fg_name, subdir)

        self.shared_filegroups[fg_name].add_source_file(file)
        return (fg_name, subdir)

    def _determine_python_info(self, python_file: File) -> T.Tuple[str, str]:
        assigned_name = self.interpreter_info.lookup_assignment(python_file)
        subdir = self.normalize_file_path(python_file.fname, python_file.subdir)

        needs_filegroup_or_lib = subdir != python_file.subdir
        if needs_filegroup_or_lib:
            if assigned_name:
                name = assigned_name
            else:
                root, ext = os.path.split(python_file.fname)
                name = os.path.basename(root) + '_' + ext[1:]
        else:
            name = python_file.fname

        return (name, subdir)

    def handle_python_depends(self, python_depend_file: File, binary_src: ConvertId) -> None:  # fmt: skip
        (name, subdir) = self._determine_python_info(python_depend_file)
        python_binary = self.python_binaries[binary_src]

        if os.path.basename(python_depend_file.fname) == python_binary.main:
            return

        # This is technically incorrect for Bazel.  For example, imagine:
        #   src/project/cool.py
        #   src/project/cool/cool_dep.py
        #
        # This only works if there's not a subpackage present in 'src/project/cool',
        # which would block the Python binary from accessing cool_dep.py.  In practice,
        # cases like this have actually yet to be encountered.
        if os.path.commonpath([subdir, python_binary.subdir]) != python_binary.subdir:
            if name not in self.shared_filegroups:
                self.shared_filegroups[name] = ConvertInstanceFileGroup(name, subdir)

            self.shared_filegroups[name].add_source_file(python_depend_file)
            python_binary.add_source(ConvertId(name, subdir))
        else:
            python_binary.add_source(ConvertId.from_local_file(python_depend_file))

    def python_binary_from_file(self, file: File) -> ConvertId:  # fmt: skip
        (src_target_name, subdir) = self._determine_python_info(file)
        python_main = os.path.basename(file.fname)
        target = _python_script_to_binary(python_main)
        target_src = ConvertId(target, subdir)
        if target_src not in self.python_binaries:
            self.python_binaries[target_src] = ConvertInstancePythonBinary(
                target, subdir, python_main
            )

            for lib in self.global_python_libs:
                self.python_binaries[target_src].add_libs(ConvertId(lib))

        self.python_binaries[target_src].add_source(ConvertId.from_local_name(python_main, subdir))
        return target_src

    def python_binary_from_program(self, program: str, subdir: str) -> ConvertId:  # fmt: skip
        python_main = os.path.basename(program)
        target = _python_script_to_binary(python_main)
        target_src = ConvertId(target, subdir)

        if target_src not in self.python_binaries:
            self.python_binaries[target_src] = ConvertInstancePythonBinary(target, subdir, program)

            for lib in self.global_python_libs:
                self.python_binaries[target_src].add_libs(ConvertId(lib))

        self.python_binaries[target_src].add_source(ConvertId.from_local_name(program, subdir))
        return target_src
