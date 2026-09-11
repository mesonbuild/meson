#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T
import os

if T.TYPE_CHECKING:
    from mesonbuild.cmdline import SharedCMDOptions
    from mesonbuild.interpreter import kwargs as kwtypes

from mesonbuild import mparser
from mesonbuild.build import Build
from mesonbuild.interpreter.interpreterobjects import GeneratedListHolder
from mesonbuild.convert.instance.convert_instance_utils import ConvertInstanceRustBindgen
from mesonbuild.convert.convert_project_instance import ConvertProjectInstance
from mesonbuild.convert.modules.rust import ConvertRustModule
from mesonbuild.convert.convert_project_config import ConvertProjectConfig
from mesonbuild.hermetic.hermetic_interpreter import HermeticInterpreter
from mesonbuild.hermetic.hermetic_platform import HermeticPlatformInstance
from mesonbuild.interpreterbase import ObjectHolder
from mesonbuild.modules import ExtensionModule, NewExtensionModule, NotFoundExtensionModule

ModuleImportResult: T.TypeAlias = T.Union[
    ExtensionModule, NewExtensionModule, NotFoundExtensionModule
]


class ConvertInterpreter(HermeticInterpreter):
    """Custom Meson interpreter for the convert tool.

    It tracks name assignments and overrides the behavior of dependencies and `run_command`
    from the base `Interpreter` class.
    """

    def __init__(self, build_info: Build, project_instance: ConvertProjectInstance,
                 project_config: ConvertProjectConfig, platform: HermeticPlatformInstance,
                 user_defined_options: SharedCMDOptions):  # fmt: skip
        self.platform = platform
        self.project_instance = project_instance
        self.project_config = project_config
        super().__init__(
            build_info,
            dependencies=project_config.dependencies,
            hermetic_platform=platform,
            user_defined_options=user_defined_options,
        )

        prefix = self.environment.get_prefix()
        libdir = self.environment.get_libdir()
        install_dir = libdir
        if not os.path.isabs(libdir):
            install_dir = os.path.join(prefix, libdir)

        self.project_instance.set_directories(
            self.environment.get_source_dir(), self.environment.get_build_dir(), install_dir
        )
        self.holder_map[ConvertInstanceRustBindgen] = GeneratedListHolder

    def func_import(self, node: mparser.BaseNode, args: T.Tuple[str],
                    kwargs: 'kwtypes.FuncImportModule') -> ModuleImportResult:  # fmt: skip
        modname = args[0]
        if modname == 'rust':
            if 'rust' not in self.modules:
                self.modules['rust'] = ConvertRustModule(self, self.project_instance)
                self.build.modules.add('rust')

            return T.cast(ExtensionModule, self.modules['rust'])

        return T.cast(ModuleImportResult, super().func_import(node, args, kwargs))

    def track_assignment(self, name: str) -> None:
        variable = self.variables.get(name)
        if not variable:
            return

        if isinstance(variable, ObjectHolder):
            variable = variable.held_object

        if isinstance(variable, list):
            self.project_instance.interpreter_info.assign(name, self.subdir, variable)
            for obj in variable:
                self.project_instance.interpreter_info.assign(name, self.subdir, obj)
        else:
            self.project_instance.interpreter_info.assign(name, self.subdir, variable)

    def assignment(self, node: mparser.AssignmentNode) -> None:
        name = node.var_name.value
        super().assignment(node)
        self.track_assignment(name)

    def evaluate_plusassign(self, node: mparser.PlusAssignmentNode) -> None:
        name = node.var_name.value
        super().evaluate_plusassign(node)
        self.track_assignment(name)
