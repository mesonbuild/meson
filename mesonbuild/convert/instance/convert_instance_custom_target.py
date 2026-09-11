#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import os
import re
import typing as T
from enum import Enum
from dataclasses import dataclass
from pathlib import PurePosixPath

from mesonbuild import build, programs
from mesonbuild.mesonlib import File, MesonException

from mesonbuild.convert.instance.convert_instance_utils import ConvertId
from mesonbuild.convert.convert_project_instance import ConvertProjectInstance
from mesonbuild.convert.convert_project_config import ConvertProjectConfig
from mesonbuild.convert.common_defs import ConvertUnimplementedException, GeneratedFilesType

CustomTargetCommandElement = T.Union[
    programs.Program, str, File, build.BuildTarget, build.CustomTarget
]
CustomTargetSource = T.Union[
    File,
    build.CustomTarget,
    build.CustomTargetIndex,
    build.GeneratedList,
    build.BuildTarget,
    build.ExtractedObjects,
    programs.Program,
]


class ConvertCustomTargetCmdPartType(Enum):
    TOOL = 1
    PYTHON_BINARY = 2
    INPUT = 3
    INPUT_INDEX = 4
    OUTPUT = 5
    OUTPUT_INDEX = 6
    STRING = 7
    M4_WORKAROUND = 8
    COPY_SRCS = 9
    MKDIR = 10


@dataclass(eq=True, unsafe_hash=True)
class ConvertCustomTargetCmdPart:
    cmd: str
    cmd_type: ConvertCustomTargetCmdPartType
    src: T.Optional[ConvertId] = None
    idx: int = 0

    @staticmethod
    def from_convert_src(source: ConvertId) -> ConvertCustomTargetCmdPart:
        return ConvertCustomTargetCmdPart('', ConvertCustomTargetCmdPartType.INPUT, source)

    @staticmethod
    def from_external_tool(src: ConvertId) -> ConvertCustomTargetCmdPart:
        return ConvertCustomTargetCmdPart('', ConvertCustomTargetCmdPartType.TOOL, src)

    @staticmethod
    def from_copy_src(source: ConvertId) -> ConvertCustomTargetCmdPart:
        return ConvertCustomTargetCmdPart('', ConvertCustomTargetCmdPartType.COPY_SRCS, source)

    @staticmethod
    def from_mkdir(directory: str) -> ConvertCustomTargetCmdPart:
        return ConvertCustomTargetCmdPart(directory, ConvertCustomTargetCmdPartType.MKDIR)

    @staticmethod
    def from_input_idx(cmd: str, idx: int) -> ConvertCustomTargetCmdPart:
        return ConvertCustomTargetCmdPart(cmd, ConvertCustomTargetCmdPartType.INPUT_INDEX, idx=idx)

    @staticmethod
    def from_input(cmd: str, idx: int = 0) -> ConvertCustomTargetCmdPart:
        return ConvertCustomTargetCmdPart(cmd, ConvertCustomTargetCmdPartType.INPUT, idx=idx)

    @staticmethod
    def from_output_idx(cmd: str, idx: int) -> ConvertCustomTargetCmdPart:
        return ConvertCustomTargetCmdPart(cmd, ConvertCustomTargetCmdPartType.OUTPUT_INDEX, idx=idx)

    @staticmethod
    def from_output(cmd: str) -> ConvertCustomTargetCmdPart:
        return ConvertCustomTargetCmdPart(cmd, ConvertCustomTargetCmdPartType.OUTPUT)

    @staticmethod
    def from_workaround(workaround_kind: ConvertCustomTargetCmdPartType) -> ConvertCustomTargetCmdPart:  # fmt: skip
        return ConvertCustomTargetCmdPart('', workaround_kind)


def get_component_dirs(subdir: str) -> T.List[str]:
    parts = subdir.split('/')
    components: T.List[str] = []
    current_path: T.List[str] = []
    for part in parts:
        current_path.append(part)
        components.append('/'.join(current_path))
    return components


def index_from_string(input_str: str) -> int:
    match = re.search(r'@(?:INPUT|OUTPUT)(\d+)', input_str)
    return int(match.group(1)) if match else 0


def is_python_script(input_str: str) -> bool:
    return input_str.endswith(('.py', '_py'))


@dataclass(frozen=True, eq=True)
class GeneratedOutput:
    output: str
    file_type: GeneratedFilesType


class ConvertInstanceCustomTarget:
    """A representation of build.CustomTarget, but optimized for the convert tool"""

    def __init__(self, custom_target: build.CustomTarget,
                 project_instance: ConvertProjectInstance,
                 project_config: ConvertProjectConfig) -> None:  # fmt: skip

        self.has_python_cmd = False
        self.tools: T.List[ConvertId] = []
        self.command_list_srcs: T.List[ConvertId] = []
        self.depend_srcs: T.List[ConvertId] = []

        self.generated_outputs: T.List[GeneratedOutput] = []
        self.custom_target_type = GeneratedFilesType.HEADERS_AND_IMPL
        self.export_include_dirs: T.List[str] = []

        self.skip_custom_target: bool = False

        self.need_ancillary_cmds: bool = False
        self.convert_instance_cmds: T.List[ConvertCustomTargetCmdPart] = []

        self.name = project_config.sanitize_target_name(custom_target.name)
        self.subdir = custom_target.subdir
        self.project_instance = project_instance
        self.project_config = project_config

        self.found_executable = False
        self.python_tool: T.Optional[ConvertId] = None

        self._parse_custom_target(custom_target, self.project_instance)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ConvertInstanceCustomTarget):
            return NotImplemented
        return (
            self.command_list_srcs == other.command_list_srcs
            and self.depend_srcs == other.depend_srcs
            and self.tools == other.tools
            and self.generated_outputs == other.generated_outputs
            and set(self.convert_instance_cmds) == set(other.convert_instance_cmds)
        )

    def _parse_custom_target(self, custom_target: build.CustomTarget,
                             project_instance: ConvertProjectInstance) -> None:  # fmt: skip
        """
        Main entry point for processing a `build.CustomTarget`.

        This method orchestrates the parsing of a raw `build.CustomTarget` from
        Meson. It delegates the analysis of the target's command, outputs, and
        dependencies to various `_handle_*` methods.

        These methods are responsible for translating the different parts of the
        custom target into a build-system-agnostic representation..
        """
        self._handle_environment(custom_target)

        for command in custom_target.command:
            self._handle_command_element(command, custom_target)

        # This is unnecessary for 99% of custom_targets, as the above code handles inputs and stores
        # them.  There are some arguably incorrect custom targets that use inputs as "depend" file,
        # and that needs to be accounted for here.
        for src in custom_target.sources:
            if isinstance(src, File) and is_python_script(src.fname):
                self.project_instance.handle_python_depends(src, self.python_tool)
            elif isinstance(src, File) and not is_python_script(src.fname):
                self._add_depend_file(src, custom_target)

        for output in custom_target.outputs:
            # this only works for one output, but that's the case we see in practice
            if custom_target.capture:
                self.convert_instance_cmds.append(
                    ConvertCustomTargetCmdPart('>', ConvertCustomTargetCmdPartType.STRING)
                )
                self.convert_instance_cmds.append(
                    ConvertCustomTargetCmdPart.from_output('@OUTPUT@')
                )

            if output.endswith('.h'):
                self.generated_outputs.append(GeneratedOutput(output, GeneratedFilesType.HEADERS))
            else:
                self.generated_outputs.append(GeneratedOutput(output, GeneratedFilesType.IMPL))

        for file in custom_target.depend_files:
            if isinstance(file, File):
                if is_python_script(file.fname) and self.has_python_cmd:
                    self.project_instance.handle_python_depends(file, self.python_tool)
                else:
                    self._add_depend_file(file, custom_target)
            elif isinstance(file, str):
                new_file = File.from_source_file(
                    self.project_instance.project_dir, self.subdir, file
                )
                self._add_depend_file(new_file, custom_target)

        for depend in custom_target.extra_depends:
            if isinstance(depend, build.CustomTarget):
                target_name = self.project_config.sanitize_target_name(depend.name)
                id_ = ConvertId(target_name, depend.subdir)
                if id_ not in self.command_list_srcs and id_ not in self.depend_srcs:
                    self.depend_srcs.append(id_)
            else:
                raise ConvertUnimplementedException(f'Type: {type(depend)}')

        self._add_ancillary_cmds()
        self._apply_workarounds(custom_target)

    def _handle_environment(self, custom_target: build.CustomTarget) -> None:
        if custom_target.env:
            for key, val in custom_target.env.get_env({}).items():
                sanitized_val = self.project_instance.normalize_string(val, self.subdir)
                env_cmd = f'{key}={sanitized_val}'
                self.convert_instance_cmds.append(
                    ConvertCustomTargetCmdPart(env_cmd, ConvertCustomTargetCmdPartType.STRING)
                )

    def _handle_command_element(self, element: CustomTargetCommandElement,
                                custom_target: build.CustomTarget) -> None:  # fmt: skip
        if isinstance(element, programs.ExternalProgram):
            self._handle_program(element)
        elif isinstance(element, str):
            self._handle_string(element, custom_target)
        elif isinstance(element, File):
            idx = self._handle_command_list_file(element, custom_target)
            if idx is None:
                return

            self.convert_instance_cmds.append(
                ConvertCustomTargetCmdPart.from_input_idx(f'@INPUT{idx}@', idx)
            )
        else:
            raise ConvertUnimplementedException(f'Type: {type(element)}')

    def _handle_program(self, program: programs.ExternalProgram) -> None:  # fmt: skip
        prog_name = program.get_name()
        prog_path = program.get_path()

        # This means the actual Python script is file, and needs to be be handled by
        # the the NEXT command element.
        if prog_name in {'python', 'python3'}:
            return

        if is_python_script(prog_name):
            # Actual python script is an ExternalProgram
            if prog_path:
                bin_subdir = self.project_instance.normalize_path(os.path.dirname(prog_path), '.')
            else:
                bin_subdir = self.subdir

            python_src = self.project_instance.python_binary_from_program(prog_name, bin_subdir)
            self._handle_python_binary(python_src)
        else:
            # Flex depends on m4, but many usages of flex neglect to even think about m4.
            # Workaround that here
            if prog_name in {'flex', 'bison'}:
                self._handle_external_program('m4')
                self.convert_instance_cmds.append(
                    ConvertCustomTargetCmdPart.from_workaround(
                        ConvertCustomTargetCmdPartType.M4_WORKAROUND
                    )
                )

            tool_src = self._handle_external_program(prog_name)
            self.convert_instance_cmds.append(
                ConvertCustomTargetCmdPart.from_external_tool(tool_src)
            )

        self.found_executable = True

    def _handle_python_binary(self, python_src: ConvertId) -> None:
        self.convert_instance_cmds.append(
            ConvertCustomTargetCmdPart(
                python_src.name, ConvertCustomTargetCmdPartType.PYTHON_BINARY, python_src
            )
        )
        self.tools.append(python_src)
        self.has_python_cmd = True
        self.python_tool = python_src

    def _handle_external_program(self, prog_name: str) -> ConvertId:
        prog_config = self.project_config.dependencies.programs.get(prog_name)
        if prog_config is None:
            raise MesonException(f'Type: {prog_name} not present, exiting...')

        tool_name = prog_name
        subdir: str = prog_config.get('subdir', '')
        repo: str = prog_config.get('repo', '')

        tool_src = ConvertId(tool_name, subdir, repo)
        self.tools.append(tool_src)
        return tool_src

    def _handle_source(self, src: CustomTargetSource,
                       custom_target: build.CustomTarget) -> T.Optional[int]:  # fmt: skip

        if isinstance(src, File):
            return self._handle_command_list_file(src, custom_target)
        else:
            raise ConvertUnimplementedException(f'Type: {type(src)}')

    def _handle_command_list_file(self, src: File,
                                  custom_target: build.CustomTarget) -> T.Optional[int]:  # fmt: skip

        # We need to add exectuable scripts to [tools], not [srcs]
        if is_python_script(src.fname) and not self.found_executable:
            python_src = self.project_instance.python_binary_from_file(src)
            self._handle_python_binary(python_src)
            self.found_executable = True
            return None

        src_id = self._handle_file(src, custom_target)
        if src_id not in self.command_list_srcs:
            self.command_list_srcs.append(src_id)

        return self.command_list_srcs.index(src_id)

    def _add_depend_file(self, file: File, custom_target: build.CustomTarget) -> None:  # fmt: skip
        src = self._handle_file(file, custom_target)
        if src not in self.command_list_srcs and src not in self.depend_srcs:
            self.depend_srcs.append(src)

    def _handle_file(self, file: File, custom_target: build.CustomTarget) -> ConvertId:  # fmt: skip
        needs_filegroup = file.fname != os.path.basename(file.fname) or file.subdir != self.subdir
        if needs_filegroup:
            (fg_name, subdir) = self.project_instance.determine_filegroup(file)
            src = ConvertId(fg_name, subdir)
        else:
            src = ConvertId.from_local_file(file)

        return src

    def _handle_string(self, command_string: str, custom_target: build.CustomTarget) -> None:  # fmt: skip
        if command_string.count('@INPUT@'):
            idx: T.Optional[int] = None
            for src in custom_target.sources:
                idx = self._handle_source(src, custom_target)

            if idx is None:
                return

            self.convert_instance_cmds.append(
                ConvertCustomTargetCmdPart.from_input(command_string, idx)
            )
        elif command_string.count('@INPUT'):
            meson_idx = index_from_string(command_string)
            src = custom_target.sources[meson_idx]
            idx = self._handle_source(src, custom_target)
            if idx is None:
                return

            # Map index in string to internal index
            input_str = command_string.replace(f'@INPUT{meson_idx}@', f'@INPUT{idx}@')
            self.convert_instance_cmds.append(
                ConvertCustomTargetCmdPart.from_input_idx(input_str, idx)
            )
        elif command_string.count('@OUTPUT@'):
            self.convert_instance_cmds.append(
                ConvertCustomTargetCmdPart.from_output(command_string)
            )
        elif command_string.count('@OUTPUT'):
            idx = index_from_string(command_string)
            self.convert_instance_cmds.append(
                ConvertCustomTargetCmdPart.from_output_idx(command_string, idx)
            )
        else:
            normalized_string = self.project_instance.normalize_string(command_string, self.subdir)
            processed_string = self._handle_normalized_string(normalized_string, custom_target)
            self.convert_instance_cmds.append(
                ConvertCustomTargetCmdPart(processed_string, ConvertCustomTargetCmdPartType.STRING)
            )

    def _handle_normalized_string(self, normalized_str: str,
                                  custom_target: build.CustomTarget) -> str:  # fmt: skip
        sanitized_parts = []
        string_parts = normalized_str.split()

        for part in string_parts:
            if part.startswith('-I'):
                if self.project_config.project_path:
                    sanitized = part.replace('@@PROJECT_DIR@@', self.project_config.project_path)
                else:
                    sanitized = part.replace('@@PROJECT_DIR@@', '')
                sanitized_parts.append(sanitized)
            elif part.startswith('@@PROJECT_DIR@@'):
                # The custom target wants to reference other source files (hopefully, explicitly
                # declared depend_srcs, but not always).  Right now, we copy the depend_srcs to
                # @@GEN_DIR@@, but in theory can copy the entire directory that is desired by the
                # custom target.
                sanitized = part.replace('@@PROJECT_DIR@@', '@@GEN_DIR@@')
                sanitized_parts.append(sanitized)
                self.need_ancillary_cmds = True
            elif part.startswith('@@BUILD_DIR@@'):
                # The custom target wants to reference other generated outputs.  The generated
                # outputs which are sources to this custom target will be placed at location
                # under @@GEN_DIR@@.
                sanitized = part.replace('@@BUILD_DIR@@', '@@GEN_DIR@@')
                sanitized_parts.append(sanitized)
                self.need_ancillary_cmds = True
            elif part.startswith('@@INSTALL_DIR@@'):
                # Install dir undefined for hermetic builds for now
                self.skip_custom_target = True
            elif '@DEPFILE@' in part:
                depfile = custom_target.get_dep_outname(self.command_list_srcs[0].name)  # type: ignore
                sanitized_parts.append(part.replace('@DEPFILE@', depfile))
            elif part.count('<') and part.count('>'):
                # This handles a part like '<A7XX>'.  They can't be passed directly to Soong genrule
                # since that considers them as shell re-direct commands
                sanitized_parts.append(f"'{part}'")
            else:
                sanitized_parts.append(part)

        if not sanitized_parts:
            return ''
        elif len(sanitized_parts) == 1:
            return sanitized_parts[0]
        else:
            joined_string = ' '.join(sanitized_parts)
            return f"'{joined_string}'"

    def _apply_workarounds(self, custom_target: build.CustomTarget) -> None:
        workarounds = self.project_config.custom_target.get('workarounds', {})
        if workarounds:
            skip_export_includes = workarounds.get('skip_export_include_dirs', [])
            if custom_target.name in skip_export_includes:
                return

        if not self.get_outputs_by_type(GeneratedFilesType.HEADERS):
            return

        # This is related to the handling header includes.  In hermetic systems,
        # code is generated in the root of a sandbox, and '#include "generated_header.h"'
        # is the ideal way to access it.  "#include "src/generated_header.h"" will not
        # work, unless the code is generated in the "src" directory (in the sandbox).
        # This logic adds the correct subdirectory prefixes.
        prefixed_outputs: T.List[GeneratedOutput] = []

        for o in self.generated_outputs:
            path = str(PurePosixPath(self.subdir) / o.output)
            prefixed_outputs.append(GeneratedOutput(path, o.file_type))

        self.generated_outputs = prefixed_outputs
        self.export_include_dirs = get_component_dirs(self.subdir)

    def get_outputs_by_type(self, file_type: GeneratedFilesType) -> T.List[str]:
        return [o.output for o in self.generated_outputs if o.file_type & file_type]

    def _add_ancillary_cmds(self) -> None:
        if not self.need_ancillary_cmds:
            return

        extra_directories: T.Set[str] = set()
        copy_cmds: T.List[ConvertCustomTargetCmdPart] = []
        mkdir_cmds: T.List[ConvertCustomTargetCmdPart] = []
        for src in self.depend_srcs:
            if src.subdir not in extra_directories:
                mkdir_cmds.append(ConvertCustomTargetCmdPart.from_mkdir(src.subdir))
                extra_directories.add(src.subdir)

            copy_cmds.append(ConvertCustomTargetCmdPart.from_copy_src(src))

        self.convert_instance_cmds = mkdir_cmds + copy_cmds + self.convert_instance_cmds
