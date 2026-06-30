#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T
import os
import sys

if T.TYPE_CHECKING:
    from mesonbuild.interpreter import kwargs
    from mesonbuild.interpreterbase import TYPE_var, TYPE_kwargs
    from mesonbuild.cmdline import SharedCMDOptions
    from mesonbuild.compilers.compilers import Language

from mesonbuild import interpreter, programs, mparser
from mesonbuild.build import Build, Executable
from mesonbuild.backend.backends import Backend
from mesonbuild.compilers import Compiler
from mesonbuild.interpreter.interpreterobjects import RunProcess
from mesonbuild.mesonlib import File, MachineChoice, MesonException, SubProject, ROOT_SUBPROJECT
from mesonbuild.dependencies import base as dependency_base
from mesonbuild.dependencies.base import DependencyTypeName
from mesonbuild.dependencies.misc import ThreadDependency
from mesonbuild.envconfig import MachineInfo
from mesonbuild.interpreterbase import InterpreterObject, ObjectHolder, noArgsFlattening, Feature
from mesonbuild.interpreterbase.decorators import noKwargs
from mesonbuild.convert.convert_project_instance import ConvertProjectInstance
from mesonbuild.convert.convert_project_config import ConvertProjectConfig
from mesonbuild.convert.precomputed.precomputed_platform import PrecomputedPlatform


RunCommandArg = T.Union[Executable, 'programs.Program', Compiler, File, str]


class MachineHolder(InterpreterObject):
    """A holder for machine information to make it available in the interpreter"""

    def __init__(self, machine_info: MachineInfo) -> None:
        super().__init__()
        self.holder = machine_info

    @InterpreterObject.method('system')
    @noKwargs
    def system_method(self, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> str:
        return self.holder.system

    @InterpreterObject.method('cpu_family')
    @noKwargs
    def cpu_family_method(self, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> str:
        return self.holder.cpu_family

    @InterpreterObject.method('cpu')
    @noKwargs
    def cpu_method(self, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> str:
        return self.holder.cpu

    @InterpreterObject.method('endian')
    @noKwargs
    def endian_method(self, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> str:
        return self.holder.endian


class ConvertInterpreter(interpreter.Interpreter):
    """Custom Meson interpreter for the convert tool.

    It tracks name assignments and overrides the behavior of dependencies and `run_command`
    from the base `Interpreter` class.
    """

    def __init__(self, build_info: Build, project_instance: ConvertProjectInstance,
                 project_config: ConvertProjectConfig, platform: PrecomputedPlatform,
                 backend: T.Optional[Backend] = None,
                 subproject: SubProject = ROOT_SUBPROJECT, subdir: str = '',
                 user_defined_options: T.Optional[SharedCMDOptions] = None):  # fmt: skip
        self.platform = platform
        self.project_instance = project_instance
        self.project_config = project_config
        super().__init__(
            build_info,
            backend=backend,
            subproject=subproject,
            subdir=subdir,
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
        self.variables['host_machine'] = MachineHolder(self.build.environment.machines.host)
        self.variables['build_machine'] = MachineHolder(self.build.environment.machines.build)
        self.variables['target_machine'] = MachineHolder(self.build.environment.machines.target)
        self.funcs['find_program'] = self.func_find_program  # type: ignore[assignment]

    @noArgsFlattening
    def func_find_program(self, node: mparser.BaseNode, args: T.List[T.Union[str, T.List[str]]],
                          kwargs: kwargs.FindProgram) -> programs.ExternalProgram:  # fmt: skip
        prog_names = args[0]
        if not isinstance(prog_names, list):
            prog_names = [prog_names]

        for prog_name in prog_names:
            # Check if the program is a script in the source tree
            script_path = os.path.join(self.environment.source_dir, self.subdir, prog_name)
            is_file = os.path.isfile(script_path)
            if is_file:
                # If it's a python script, prepend the python executable
                if prog_name.endswith('.py'):
                    return programs.ExternalProgram(
                        prog_name, command=[sys.executable, script_path]
                    )
                return programs.ExternalProgram(prog_name, command=[script_path])

            prog_info = self.project_config.dependencies.programs.get(prog_name)
            if prog_info:
                prog = programs.ExternalProgram(prog_name, command=[prog_name])
                prog.found = lambda: True  # type: ignore[method-assign]
                version = prog_info.get('version')
                if version:
                    prog.version = version  # type: ignore[attr-defined]
                return prog

        return programs.NonExistingExternalProgram(prog_names[0])

    def run_command_impl(self,
                         args: T.Tuple[T.Union[RunCommandArg, T.List[RunCommandArg]], T.List[RunCommandArg]],
                         kwargs: kwargs.RunCommand, in_builddir: bool = False) -> RunProcess:  # fmt: skip
        emulated_process = RunProcess.__new__(RunProcess)
        emulated_process.returncode = 0
        emulated_process.stdout = ''
        emulated_process.stderr = ''

        cmd, raw_args = args

        cmd_args: T.List[RunCommandArg] = []
        for arg in raw_args:
            if isinstance(arg, list):
                cmd_args.extend(arg)
            else:
                cmd_args.append(arg)

        cmd_name = ''
        if isinstance(cmd, programs.ExternalProgram):
            cmd_name = cmd.get_name()
        elif isinstance(cmd, str):
            cmd_name = cmd
        elif isinstance(cmd, list):
            cmd_name = T.cast(str, cmd[0])
            cmd_args = cmd[1:] + cmd_args
        else:
            cmd_name = T.cast(str, cmd)

        prog_info = self.project_config.dependencies.programs.get(cmd_name)
        if '--version' in cmd_args:
            if prog_info and 'version' in prog_info:
                emulated_process.stdout = str(prog_info['version'])
                emulated_process.stderr = ''

        emulated_process.subproject = self.subproject
        return emulated_process

    def _redetect_machines(self) -> None:
        pass

    def add_languages_for(self, args: T.List[Language], required: bool,
                          for_machine: MachineChoice) -> bool:  # fmt: skip
        for lang in args:
            if lang not in self.coredata.compilers[for_machine]:
                compiler = self.platform.create_compiler(lang, for_machine)
                if compiler:
                    self.coredata.compilers[for_machine][lang] = compiler
        return super().add_languages_for(args, required, for_machine)

    def print_extra_warnings(self) -> None:
        pass

    def _print_summary(self) -> None:
        pass

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

    def func_dependency(self, node: mparser.BaseNode, args: T.List[str],
                        kwargs: kwargs.FuncDependency) -> dependency_base.Dependency:  # fmt: skip
        desired_dep_name = args[0] if args else T.cast(str, kwargs.get('name', 'unnamed'))

        if T.TYPE_CHECKING:
            typed_kwargs = T.cast(dependency_base.DependencyObjectKWs, kwargs)
        else:
            typed_kwargs = kwargs

        if desired_dep_name == 'threads':
            kwargs['native'] = MachineChoice.HOST
            return ThreadDependency('threads', self.environment, typed_kwargs)

        dep_info = (
            self.project_config.dependencies.shared_libraries.get(desired_dep_name)
            or self.project_config.dependencies.static_libraries.get(desired_dep_name)
            or self.project_config.dependencies.rust_libraries.get(desired_dep_name)
            or self.project_config.dependencies.header_libraries.get(desired_dep_name)
        )

        if dep_info:
            kwargs['native'] = MachineChoice.HOST
            dep = dependency_base.ExternalDependency('system', self.environment, typed_kwargs)
            dep.type_name = T.cast(DependencyTypeName, 'library')
            dep.is_found = True
            dep.version = (
                dep_info[0].get('version', 'convert_instance') if dep_info else 'convert_instance'
            )

            configtool_checks = (
                T.cast(T.Dict[str, str], dep_info[0].get('configtool', {})) if dep_info else {}
            )
            pkgconfig_checks = (
                T.cast(T.Dict[str, str], dep_info[0].get('pkgconfig', {})) if dep_info else {}
            )

            def get_variable(*, cmake: T.Optional[str] = None, pkgconfig: T.Optional[str] = None,
                             configtool: T.Optional[str] = None, internal: T.Optional[str] = None,
                             system: T.Optional[str] = None, default_value: T.Optional[str] = None,
                             pkgconfig_define: T.Optional[T.Tuple[T.Tuple[str, str], ...]] = None) -> T.Optional[str]:  # fmt: skip
                if configtool and configtool in configtool_checks:
                    return configtool_checks.get(configtool)
                if pkgconfig and pkgconfig in pkgconfig_checks:
                    return pkgconfig_checks.get(pkgconfig)
                return None

            dep.get_variable = get_variable  # type: ignore[method-assign]
            dep.name = desired_dep_name

            if self.project_config.dependencies.static_libraries.get(
                desired_dep_name
            ) or self.project_config.dependencies.rust_libraries.get(desired_dep_name):
                dep.static = True

            return dep

        required = kwargs.get('required', True)
        if isinstance(required, Feature):
            required = required.is_enabled()

        if required:
            raise MesonException(f"Dependency '{desired_dep_name}' not found and is required.")

        return dependency_base.NotFoundDependency(desired_dep_name, self.environment)
