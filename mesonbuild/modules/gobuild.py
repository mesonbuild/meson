# SPDX-License-Identifier: Apache-2.0
# Copyright 2025 The Meson development team

from __future__ import annotations

import itertools
import typing as T
from dataclasses import asdict, dataclass
from os import path

from .. import build, mesonlib
from ..interpreter.type_checking import CT_INPUT_KW
from ..interpreterbase import ContainerTypeInfo, KwargInfo
from ..interpreterbase.decorators import typed_kwargs, typed_pos_args
from . import ExtensionModule, ModuleInfo, ModuleReturnValue

if T.TYPE_CHECKING:
    from typing_extensions import TypedDict

    from ..interpreter import Interpreter
    from ..programs import ExternalProgram
    from . import ModuleState

    class ProjectKwargs(TypedDict):
        sources: T.List[T.Union[mesonlib.FileOrString, build.GeneratedTypes]]
        include_directories: T.List[T.Union[str, build.IncludeDirs]]
        link_with: T.List[T.Union[build.SharedLibrary, build.StaticLibrary]]
        tags: T.List[str]
        native: bool
        gomod_tidy: bool


@dataclass
class CGOToolchain:
    GOOS: str
    GOARCH: str
    CC: str
    CXX: str
    CGO_ENABLED: str = "1"


class GoBuildModule(ExtensionModule):
    INFO = ModuleInfo("Go build", "1.6.0", unstable=True)

    def __init__(self, interpreter: Interpreter) -> None:
        super().__init__(interpreter)
        self.go_exe: T.Union[ExternalProgram, build.Executable, None] = None
        self.methods.update(
            {
                "project": self.project,
            }
        )

    def detect_tools(self, state: ModuleState, is_cross_build: bool) -> CGOToolchain:
        if self.go_exe is None:
            self.go_exe = state.find_program("go")

        HOST = mesonlib.MachineChoice.HOST
        compilers = state.environment.coredata.compilers[HOST]

        if "c" not in compilers:
            raise mesonlib.MesonException(
                "Cross-compiler for language 'c' not found. "
                "Did we forget to add_languages()?"
            )

        if "cpp" not in compilers:
            raise mesonlib.MesonException(
                "Cross-compiler for language 'cpp' not found. "
                "Did we forget to add_languages()?"
            )

        # CGO for windows target assumes MinGW toolchain.
        # https://gcc.gnu.org/onlinedocs/gcc/Cygwin-and-MinGW-Options.html#index-mthreads
        system = state.environment.machines[HOST].system
        if "windows" in system and not compilers["c"].has_multi_arguments(
            ["-mthreads"], state.environment
        ):
            raise mesonlib.MesonException(
                f"Cross-compiler {compilers['c']} does not support "
                "`-mthreads`. Likely a clang compiler?"
            )

        return CGOToolchain(
            GOOS=system,
            GOARCH=state.environment.machines[HOST].cpu_family.replace(
                "x86_64", "amd64"
            ),
            CC=" ".join(
                compilers["c"].get_exelist(ccache=True)
                + ["-Wno-unused-command-line-argument"]
            ),
            CXX=" ".join(compilers["cpp"].get_exelist(ccache=True)),
        )

    @typed_pos_args(
        "gobuild.project",
        str,
        varargs=(
            str,
            mesonlib.File,
            build.CustomTarget,
            build.CustomTargetIndex,
            build.GeneratedList,
        ),
    )
    @typed_kwargs(
        "gobuild.project",
        CT_INPUT_KW.evolve(name="sources"),
        KwargInfo(
            "include_directories",
            ContainerTypeInfo(list, (str, build.IncludeDirs)),
            default=[],
            listify=True,
        ),
        KwargInfo(
            "link_with",
            ContainerTypeInfo(list, (build.SharedLibrary, build.StaticLibrary)),
            default=[],
            listify=True,
        ),
        KwargInfo(
            "tags",
            ContainerTypeInfo(list, (str)),
            default=[],
            listify=True,
        ),
        KwargInfo(
            "native",
            bool,
            default=False,
        ),
        KwargInfo(
            "gomod_tidy",
            bool,
            default=True,
        ),
    )
    def project(
        self,
        state: ModuleState,
        args: T.Tuple[
            str, T.List[T.Union[mesonlib.FileOrString, build.GeneratedTypes]]
        ],
        kwargs: ProjectKwargs,
    ) -> ModuleReturnValue:
        is_cross_build = state.environment.is_cross_build(
            mesonlib.MachineChoice.BUILD
            if kwargs["native"]
            else mesonlib.MachineChoice.HOST
        )

        cross_compilers = self.detect_tools(state, is_cross_build)

        proj_name, arg_sources = args
        all_sources = self.interpreter.source_strings_to_files(
            list(itertools.chain(arg_sources, kwargs["sources"]))
        )
        go_sum_target = build.CustomTarget(
            f"{proj_name}: go mod tidy",
            state.subdir,
            state.subproject,
            state.environment,
            [
                self.go_exe,
                "-C",
                "@CURRENT_SOURCE_DIR@",
                "mod",
                "tidy" if kwargs["gomod_tidy"] else "verify",
            ],
            self.interpreter.source_strings_to_files(["go.mod"]),
            [f"go-mod-tidy-{proj_name}.log"],
            capture=True,
            build_always_stale=True,
        )

        build_dir_abs = path.abspath(state.environment.get_build_dir())
        target_dir_abs = path.join(
            build_dir_abs, state.backend.get_target_dir(go_sum_target)
        )

        link_dirs = {
            "-L" + path.join(build_dir_abs, state.backend.get_target_dir(lib))
            for lib in kwargs["link_with"]
        }
        link_targets = {"-l" + lib.name for lib in kwargs["link_with"]}

        if not is_cross_build:
            # TODO: always override environment variables CC and CXX for native builds.
            extra_env = {}
        else:
            extra_env = asdict(cross_compilers)

        exe_target = build.CustomTarget(
            f"{proj_name}: go build",
            state.subdir,
            state.subproject,
            state.environment,
            [
                self.go_exe,
                "-C",
                "@CURRENT_SOURCE_DIR@",
                "build",
                "-tags",
                ",".join(kwargs["tags"]),
                "-o",
                f"{target_dir_abs}/@OUTPUT0@",
            ],
            all_sources + [go_sum_target],
            [
                proj_name
                + (
                    ".exe"
                    if ("windows" in cross_compilers.GOOS) and (not kwargs["native"])
                    else ""
                )
            ],
            extra_depends=kwargs["link_with"],
            env=mesonlib.EnvironmentVariables(
                extra_env
                | {
                    "CGO_CFLAGS": " ".join(
                        state.get_include_args(kwargs["include_directories"])
                    ),
                    "CGO_LDFLAGS": " ".join(list(link_dirs) + list(link_targets)),
                }
            ),
            build_by_default=True,
            install=True,
            install_dir=[T.cast(str, state.get_option("bindir"))],
        )

        # TODO: Write a custom python function to convert the output to TAP protocol.
        self.interpreter.add_test(
            self.interpreter.current_node,
            (
                f"{proj_name}_go test",
                self.go_exe,
            ),
            kwargs={
                "args": ["test", "./..."],
                "is_parallel": False,
                # TODO: Expose the timeout argument.
                "timeout": 30,
                "priority": 0,
                "should_fail": False,
                "workdir": (path.abspath(state.environment.get_source_dir())),
                "protocol": "exitcode",
                "verbose": True,
                "suite": ["go test"],
                "depends": go_sum_target,
            },
            is_base_test=True,
        )

        return ModuleReturnValue(exe_target, [go_sum_target, exe_target])


def initialize(interp: Interpreter) -> GoBuildModule:
    return GoBuildModule(interp)
