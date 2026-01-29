#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import os
import typing as T
from enum import Enum
from dataclasses import dataclass, field

from mesonbuild import build, programs
from mesonbuild.mesonlib import File, MesonException

from mesonbuild.convert.instance.convert_instance_utils import (
    ConvertInstanceFileGroup, )
from mesonbuild.convert.convert_project_instance import ConvertProjectInstance
from mesonbuild.convert.convert_project_config import ConvertProjectConfig


class ConvertCustomTargetCmdPartType(Enum):
    TOOL = 1
    PYTHON_BINARY = 2
    INPUT = 3
    OUTPUT = 4
    STRING = 5


@dataclass(eq=True, unsafe_hash=True)
class ConvertCustomTargetCmdPart:
    cmd: str
    cmd_type: ConvertCustomTargetCmdPartType


def get_component_dirs(subdir: str) -> T.List[str]:
    parts = subdir.split('/')
    components: T.List[str] = []
    current_path: T.List[str] = []
    for part in parts:
        current_path.append(part)
        components.append('/'.join(current_path))
    return components


def index_from_string(input_str: str) -> int:
    valid_prefixes = ('@INPUT', '@OUTPUT')
    if input_str.startswith(valid_prefixes):
        index_as_str = (input_str.replace('@INPUT', '').replace('@OUTPUT', '').rstrip('@'))
        if index_as_str:
            return int(index_as_str)

    return 0


def is_python_script(input_str: str) -> bool:
    return input_str.endswith(('.py', '_py'))


def python_script_to_binary(input_str: str) -> str:
    name = os.path.basename(input_str)
    if name.endswith('gen.py'):
        return name[:-6] + 'py_binary'
    if name.endswith('gen_py'):
        return name[:-6] + 'py_binary'
    if name.endswith('.py'):
        return name[:-3] + '_py_binary'
    if name.endswith('_py'):
        return name[:-3] + '_py_binary'
    return name + '_py_binary'


@dataclass
class ConvertInstancePythonTarget:
    main: str = ''
    subdir: str = ''
    name: str = ''
    srcs: T.List[str] = field(default_factory=list)
    libs: T.List[str] = field(default_factory=list)


class ConvertInstanceCustomTarget:
    """A representation of build.CustomTarget, but optimized for the convert tool"""

    def __init__(
        self,
        custom_target: build.CustomTarget,
        project_instance: ConvertProjectInstance,
        project_config: ConvertProjectConfig,
    ) -> None:
        self.is_python = False
        self.python_depend_files: T.List[str] = []

        self.tools: T.List[str] = []
        self.srcs: T.List[str] = []
        self.python_script: T.Optional[str] = None
        self.generated_headers: T.List[str] = []
        self.generated_sources: T.List[str] = []
        self.export_include_dirs: T.List[str] = []
        self.convert_instance_cmds: T.List[ConvertCustomTargetCmdPart] = []
        self.generated_filegroups: T.Dict[str, ConvertInstanceFileGroup] = {}
        self.skip_custom_target: bool = False

        self.name = project_config.sanitize_target_name(custom_target.name)
        self.subdir = custom_target.subdir
        self.project_instance = project_instance
        self.project_config = project_config
        self._parse_custom_target(custom_target)

    def __repr__(self) -> str:
        return f"(name='{self.name}', subdir='{self.subdir}')"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ConvertInstanceCustomTarget):
            return NotImplemented
        return (self.srcs == other.srcs and self.tools == other.tools
                and self.generated_headers == other.generated_headers
                and self.generated_sources == other.generated_sources
                and set(self.convert_instance_cmds) == set(other.convert_instance_cmds))

    def get_python_target(self) -> T.Optional[ConvertInstancePythonTarget]:
        if self.python_script is None:
            return None

        python_target = ConvertInstancePythonTarget()
        python_target.main = self.python_script
        python_target.name = self.tools[0]
        python_target.subdir = self.subdir
        python_target.srcs = self.python_depend_files
        if self.project_config.dependencies.programs:
            tool_config = (self.project_config.dependencies.programs.get('python3')
                           or self.project_config.dependencies.programs.get('python') or {})
            python_target.libs.extend(tool_config.get('dependencies', []))
        return python_target

    def get_generated_filegroups(self) -> T.List[ConvertInstanceFileGroup]:
        return list(self.generated_filegroups.values())

    def _handle_environment(self, custom_target: build.CustomTarget) -> None:
        if custom_target.env:
            for key, val in custom_target.env.get_env({}).items():
                sanitized_val = self.project_instance.normalize_string(val, custom_target.subdir)
                assert sanitized_val is not None
                env_cmd = f'{key}={sanitized_val}'
                self.convert_instance_cmds.append(
                    ConvertCustomTargetCmdPart(env_cmd, ConvertCustomTargetCmdPartType.STRING))

    def _parse_custom_target(self, custom_target: build.CustomTarget) -> None:
        """
        Main entry point for processing a `build.CustomTarget`.

        This method orchestrates the parsing of a raw `build.CustomTarget` from
        Meson. It delegates the analysis of the target's command, outputs, and
        dependencies to various `_handle_*` methods. These methods are
        responsible for translating the different parts of the custom target into a
        build-system-agnostic representation, including identifying tools, inputs,
        outputs, and applying any necessary workarounds defined in the project's
        configuration.
        """
        self._handle_environment(custom_target)

        for command in custom_target.command:
            if isinstance(command, File):
                self._handle_file(command, custom_target)
            elif isinstance(command, programs.ExternalProgram):
                self._handle_program(command)
            elif isinstance(command, str):
                self._handle_string(command, custom_target)

        for output in custom_target.outputs:
            output_str = T.cast(str, output)
            # this only works for one output, but that's the case we see in practice
            if custom_target.capture:
                self.convert_instance_cmds.append(
                    ConvertCustomTargetCmdPart('>', ConvertCustomTargetCmdPartType.STRING))
                self.convert_instance_cmds.append(
                    ConvertCustomTargetCmdPart(output_str, ConvertCustomTargetCmdPartType.OUTPUT))

            if output_str.endswith('.h'):
                self.generated_headers.append(output_str)
            else:
                self.generated_sources.append(output_str)

        for file in custom_target.depend_files:
            if isinstance(file, File):
                self._handle_file(file, custom_target)

        self._apply_workarounds(custom_target)

    def _handle_input(self, src: T.Any, custom_target: build.CustomTarget) -> None:
        if isinstance(src, File):
            self._handle_file(src, custom_target)
        elif isinstance(src, (build.CustomTarget, build.CustomTargetIndex)):
            output = src.get_outputs()[0]
            self.convert_instance_cmds.append(
                ConvertCustomTargetCmdPart(output, ConvertCustomTargetCmdPartType.INPUT))
            self.srcs.append(output)
        elif isinstance(src, str):
            raise MesonException(f'Type: {type(src)} not handled, exiting...')

    def _handle_file(self, file: File, custom_target: build.CustomTarget) -> None:
        name = file.fname
        needs_filegroup = (file.subdir != custom_target.subdir or name != os.path.basename(name))
        if needs_filegroup:
            fg_name = self.project_instance.interpreter_info.lookup_assignment(file)
            if fg_name is not None:
                if fg_name in self.generated_filegroups:
                    self.generated_filegroups[fg_name].add_source_file(file, self.project_instance)
                else:
                    filegroup = ConvertInstanceFileGroup(name=fg_name)
                    filegroup.add_source_file(file, self.project_instance)
                    self.generated_filegroups[fg_name] = filegroup
            else:
                filegroup = ConvertInstanceFileGroup()
                filegroup.add_source_file(file, self.project_instance)
                fg_name = filegroup.name
                self.generated_filegroups[fg_name] = filegroup

            needs_filegroup = True
            name = ':' + fg_name

        if is_python_script(file.fname) and self.python_script is None:
            self.python_script = os.path.basename(file.fname)
            python_binary = python_script_to_binary(file.fname)
            if python_binary in self.tools:
                return

            self.python_depend_files.append(name)
            self.tools.append(python_binary)
            self.convert_instance_cmds.append(
                ConvertCustomTargetCmdPart(python_binary,
                                           ConvertCustomTargetCmdPartType.PYTHON_BINARY))
        elif name not in self.srcs:
            if file not in custom_target.depend_files:
                self.convert_instance_cmds.append(
                    ConvertCustomTargetCmdPart(name, ConvertCustomTargetCmdPartType.INPUT))
                self.srcs.append(name)
            elif is_python_script(file.fname):
                if name not in self.python_depend_files:
                    self.python_depend_files.append(name)
            else:
                self.srcs.append(name)

    def _handle_program(self, program: programs.ExternalProgram) -> None:
        prog_name = program.get_name()
        if prog_name in {'python', 'python3'}:
            return

        if is_python_script(prog_name):
            self.python_script = prog_name
            python_binary = python_script_to_binary(prog_name)
            self.tools.append(python_binary)
            self.convert_instance_cmds.append(
                ConvertCustomTargetCmdPart(python_binary,
                                           ConvertCustomTargetCmdPartType.PYTHON_BINARY))
        else:
            if self.project_config.dependencies.programs:
                prog_config = self.project_config.dependencies.programs.get(prog_name)
                if prog_config is None:
                    raise MesonException(f'Type: {type(prog_name)} not present, exiting...')

                tool_name = prog_name
                if prog_config and 'path' in prog_config:
                    tool_name = prog_config['path']

                self.tools.append(tool_name)
                self.convert_instance_cmds.append(
                    ConvertCustomTargetCmdPart(tool_name, ConvertCustomTargetCmdPartType.TOOL))

    def _handle_string(self, command_string: str, custom_target: build.CustomTarget) -> None:
        if command_string == '@INPUT@':
            for j, src in enumerate(custom_target.sources):
                self._handle_input(src, custom_target)
        elif command_string.startswith('@INPUT'):
            idx = index_from_string(command_string)
            assert idx is not None
            src = custom_target.sources[idx]
            self._handle_input(src, custom_target)
        elif command_string.startswith('@OUTPUT'):
            value = index_from_string(command_string)
            assert value is not None
            output = custom_target.outputs[value]
            output_str = T.cast(str, output)
            self.convert_instance_cmds.append(
                ConvertCustomTargetCmdPart(output_str, ConvertCustomTargetCmdPartType.OUTPUT))
        else:
            normalized_string = self.project_instance.normalize_string(
                command_string, custom_target.subdir)
            assert normalized_string is not None
            processed_string = self._handle_normalized_string(normalized_string, custom_target)
            self.convert_instance_cmds.append(
                ConvertCustomTargetCmdPart(processed_string, ConvertCustomTargetCmdPartType.STRING))

    def _handle_normalized_string(self, normalized_str: str,
                                  custom_target: build.CustomTarget) -> str:
        sanitized_parts = []
        string_parts = normalized_str.split(' ')

        for part in string_parts:
            if part.startswith('-I'):
                # Ignore for now, maybe do something if desired sources not specified
                # as depend_files or depends
                continue
            elif part.startswith('@@PROJECT_DIR@@'):
                sanitized = part.replace('@@PROJECT_DIR@@', '')
                sanitized_parts.append(sanitized)
            elif part.startswith('@@INSTALL_DIR@@'):
                # Install dir undefined for hermetic builds for now
                self.skip_custom_target = True
            elif '@DEPFILE@' in part:
                depfile = custom_target.get_dep_outname(self.srcs)  # type: ignore
                sanitized_parts.append(part.replace('@DEPFILE@', depfile))
            else:
                sanitized_parts.append(part)

        if len(sanitized_parts) > 1:
            joined_string = ' '.join(sanitized_parts)
            return f"'{joined_string}'"
        else:
            return ' '.join(sanitized_parts)

    def _apply_workarounds(self, custom_target: build.CustomTarget) -> None:
        workarounds = self.project_config.custom_target.get('workarounds', {})
        if not workarounds:
            return

        # Only one workaround now: export_include_dirs
        export_includes = workarounds.get('export_include_dirs', [])
        if not export_includes:
            return

        if custom_target.name not in export_includes:
            return

        prefixed_headers = []
        for header in self.generated_headers:
            prefixed_headers.append(os.path.join(self.subdir, header))

            for cmd_part in self.convert_instance_cmds:
                if header == cmd_part.cmd:
                    cmd_part.cmd = os.path.join(self.subdir, cmd_part.cmd)

        self.generated_headers = prefixed_headers
        self.export_include_dirs = get_component_dirs(custom_target.subdir)
