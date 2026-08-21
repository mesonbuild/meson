# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import sys
import os
import typing as T

from mesonbuild.interpreterbase import InterpreterObject
from mesonbuild.interpreterbase.decorators import noKwargs
from mesonbuild.interpreter import Interpreter
from mesonbuild.interpreter.interpreterobjects import RunProcess
from mesonbuild.compilers import Compiler
from mesonbuild.interpreterbase import Feature, noArgsFlattening
from mesonbuild.mesonlib import File, MachineChoice, MesonException, ROOT_SUBPROJECT
from mesonbuild import programs, mparser
from mesonbuild.dependencies import base as dependency_base
from mesonbuild.dependencies.base import DependencyTypeName
from mesonbuild.dependencies.misc import ThreadDependency

if T.TYPE_CHECKING:
    from mesonbuild.build import Build, Executable
    from mesonbuild.cmdline import SharedCMDOptions
    from mesonbuild.compilers.compilers import Language
    from mesonbuild.envconfig import MachineInfo
    from mesonbuild.hermetic.hermetic_dependencies import HermeticDependencies
    from mesonbuild.hermetic.hermetic_platform import HermeticPlatformInstance
    from mesonbuild.interpreter import kwargs
    from mesonbuild.interpreterbase import TYPE_var, TYPE_kwargs

    RunCommandArg = T.Union[Executable, programs.Program, Compiler, File, str]


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


class HermeticInterpreter(Interpreter):
    """A base interpreter for hermetic tools (check-platforms, convert) that uses
    hermetic dependencies and platforms rather than probing the host system."""

    def __init__(self, build_info: Build,
                 dependencies: HermeticDependencies,
                 hermetic_platform: HermeticPlatformInstance,
                 user_defined_options: SharedCMDOptions) -> None:  # fmt: skip
        self.dependencies = dependencies
        self.hermetic_platform = hermetic_platform
        build_info.environment.machines.host = hermetic_platform.machine_info.host
        build_info.environment.machines.build = hermetic_platform.machine_info.build
        build_info.environment.machines.target = hermetic_platform.machine_info.host
        super().__init__(
            build_info,
            backend=None,
            subproject=ROOT_SUBPROJECT,
            subdir='',
            user_defined_options=user_defined_options,
        )

        self.variables['host_machine'] = MachineHolder(self.build.environment.machines.host)
        self.variables['build_machine'] = MachineHolder(self.build.environment.machines.build)
        self.variables['target_machine'] = MachineHolder(self.build.environment.machines.target)
        self.builtin['host_machine'] = self.variables['host_machine']
        self.builtin['build_machine'] = self.variables['build_machine']
        self.builtin['target_machine'] = self.variables['target_machine']

    def _redetect_machines(self) -> None:
        pass

    def print_extra_warnings(self) -> None:
        pass

    def _print_summary(self) -> None:
        pass

    def add_languages_for(self, args: T.List[Language], required: bool,
                          for_machine: MachineChoice) -> bool:  # fmt: skip
        for lang in args:
            if lang not in self.coredata.compilers[for_machine]:
                compiler = self.hermetic_platform.create_compiler(lang, for_machine)
                if compiler:
                    self.coredata.compilers[for_machine][lang] = compiler
        return super().add_languages_for(args, required, for_machine)

    @noArgsFlattening
    def func_find_program(self, node: mparser.BaseNode, args: T.List[T.Union[str, T.List[str]]],
                          kwargs: kwargs.FindProgram) -> programs.ExternalProgram:  # fmt: skip
        prog_names = args[0]
        if not isinstance(prog_names, list):
            prog_names = [prog_names]

        for prog_name in prog_names:
            script_path = os.path.join(self.environment.source_dir, self.subdir, prog_name)
            is_file = os.path.isfile(script_path)
            if is_file:
                if prog_name.endswith('.py'):
                    return programs.ExternalProgram(
                        prog_name, command=[sys.executable, script_path]
                    )
                return programs.ExternalProgram(prog_name, command=[script_path])

            prog_info = self.dependencies.programs.get(prog_name)
            if prog_info:
                prog = programs.ExternalProgram(prog_name, command=[prog_name])
                prog.found = lambda: True  # type: ignore[method-assign]
                version = prog_info.get('version')
                if version:
                    prog.version = version  # type: ignore[attr-defined]
                return prog

        return programs.NonExistingExternalProgram(prog_names[0])

    def func_dependency(self, node: mparser.BaseNode, args: T.List[str],
                        kwargs: kwargs.FuncDependency) -> dependency_base.Dependency:  # fmt: skip
        if args:
            arg0 = args[0]
            if isinstance(arg0, (list, tuple)):
                desired_dep_name = str(arg0[0]) if arg0 else 'unnamed'
            else:
                desired_dep_name = str(arg0)
        else:
            desired_dep_name = T.cast(str, kwargs.get('name', 'unnamed'))

        if T.TYPE_CHECKING:
            typed_kwargs = T.cast(dependency_base.DependencyObjectKWs, kwargs)
        else:
            typed_kwargs = kwargs

        if desired_dep_name == 'threads':
            kwargs['native'] = MachineChoice.HOST
            return ThreadDependency('threads', self.environment, typed_kwargs)

        dep_info = (
            self.dependencies.shared_libraries.get(desired_dep_name)
            or self.dependencies.static_libraries.get(desired_dep_name)
            or self.dependencies.rust_libraries.get(desired_dep_name)
            or self.dependencies.header_libraries.get(desired_dep_name)
        )

        if dep_info:
            kwargs['native'] = MachineChoice.HOST
            dep = dependency_base.ExternalDependency('system', self.environment, typed_kwargs)
            dep.type_name = T.cast(DependencyTypeName, 'library')
            dep.is_found = True
            dep.version = dep_info[0].get('version', '')

            configtool_checks = T.cast(T.Dict[str, str], dep_info[0].get('configtool', {}))
            pkgconfig_checks = T.cast(T.Dict[str, str], dep_info[0].get('pkgconfig', {}))

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

            if self.dependencies.static_libraries.get(
                desired_dep_name
            ) or self.dependencies.rust_libraries.get(desired_dep_name):
                dep.static = True

            return dep

        required = kwargs.get('required', True)
        if isinstance(required, Feature):
            required = required.is_enabled()

        if required:
            raise MesonException(f"Dependency '{desired_dep_name}' not found and is required.")

        return dependency_base.NotFoundDependency(desired_dep_name, self.environment)

    def run_command_impl(self, args: T.Tuple[T.Union[RunCommandArg, T.List[RunCommandArg]],
                         T.List[RunCommandArg]], kwargs: kwargs.RunCommand, in_builddir: bool = False) -> RunProcess:  # fmt: skip
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

        prog_info = self.dependencies.programs.get(cmd_name)
        if '--version' in cmd_args:
            if prog_info and 'version' in prog_info:
                emulated_process.stdout = str(prog_info['version'])
                emulated_process.stderr = ''

        emulated_process.subproject = self.subproject
        return emulated_process
