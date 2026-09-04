# SPDX-License-Identifier: Apache-2.0
# Copyright © 2021-2025 Intel Corporation
# Copyright © 2021-2025 Intel Corporation

"""Keyword Argument type annotations."""

from __future__ import annotations

import typing as T
from typing import Literal

from typing_extensions import NotRequired, Protocol, TypedDict

from .. import build, options
from ..compilers import Compiler
from ..compilers.compilers import Language
from ..dependencies.base import Dependency, DependencyMethods, IncludeType
from ..interpreterbase import Feature
from ..mesonlib import EnvironmentVariables, File, FileMode, FileOrString, MachineChoice
from ..modules.cmake import CMakeSubprojectOptions
from ..options import OptionKey
from ..programs import ExternalProgram, Program
from .type_checking import PkgConfigDefineType, SourcesVarargsType

TargetDepends = T.Union[build.CustomTarget, build.CustomTargetIndex, build.BuildTarget, build.GeneratedList, Program]
CustomTargetInputs = T.Union[str, build.BuildTarget, build.GeneratedTypes,
                             build.ExtractedObjects, Program, File]
BuildTargetObjects = T.Union[str, File, build.ExtractedObjects, build.GeneratedTypes]
RustAbi = Literal['rust', 'c']

class NativeKW(TypedDict):

    native: MachineChoice


class FuncAddProjectArgs(TypedDict):

    """Keyword Arguments for the add_*_arguments family of arguments.

    including `add_global_arguments`, `add_project_arguments`, and their
    link variants

    Because of the use of a convertor function, we get the native keyword as
    a MachineChoice instance already.
    """

    native: MachineChoice
    language: list[Language]


class BaseTest(TypedDict):

    """Shared base for the Rust module."""

    should_fail: bool | None
    expected_fail: bool | None
    expected_exitcode: int | None
    timeout: int
    workdir: str | None
    priority: int
    env: EnvironmentVariables
    depends: list[TargetDepends]
    suite: list[str]
    verbose: bool


class FuncBenchmark(BaseTest):

    """Keyword arguments used by `benchmark` and `test`, but not Rust"""

    # Needs complex refactor for rust test to go in BaseTest
    args: list[build.CommandTypes]
    protocol: Literal['exitcode', 'tap', 'gtest', 'rust']

class FuncTest(FuncBenchmark):

    """Keyword Arguments for `test` but not `benchmark`"""

    is_parallel: bool


class ExtractRequired(TypedDict):

    """Keyword Arguments consumed by the `extract_required_kwargs` function.

    Any function that uses the `required` keyword argument which accepts either
    a boolean or a feature option should inherit its arguments from this class.
    """

    required: bool | Feature


class ExtractSearchDirs(TypedDict):

    """Keyword arguments consumed by the `extract_search_dirs` function.

    See the not in `ExtractRequired`
    """

    dirs: list[str]


class FuncGenerator(TypedDict):

    """Keyword rguments for the generator function."""

    arguments: list[str]
    output: list[str]
    depfile: str | None
    capture:  bool
    depends: list[TargetDepends]


class GeneratorProcess(TypedDict):

    """Keyword Arguments for generator.process."""

    preserve_path_from: str | None
    extra_args: list[str]
    env: EnvironmentVariables
    depends: list[build.GeneratedTypes]

class DependencyMethodPartialDependency(TypedDict):

    """ Keyword Arguments for the dep.partial_dependency methods """

    compile_args: bool
    link_args: bool
    links: bool
    includes: bool
    sources: bool

class BuildTargeMethodExtractAllObjects(TypedDict):
    recursive: bool

class FuncInstallSubdir(TypedDict):

    install_dir: str
    install_tag: str | None
    strip_directory: bool
    exclude_files: list[str]
    exclude_directories: list[str]
    install_mode: FileMode
    follow_symlinks: bool | None


class FuncInstallData(TypedDict):

    install_dir: str
    sources: list[FileOrString]
    rename: list[str]
    install_mode: FileMode
    install_tag: str | None
    follow_symlinks: bool | None
    preserve_path: bool


class FuncInstallEmptyDir(TypedDict):

    install_mode: FileMode
    install_tag: str | None


class FuncInstallHeaders(TypedDict):

    install_dir: str | None
    install_mode: FileMode
    subdir: str | None
    follow_symlinks: bool | None
    install_tag: str | None
    preserve_path: bool


class FuncInstallMan(TypedDict):

    install_dir: str | None
    install_mode: FileMode
    install_tag: str | None
    locale: str | None


class FuncInstallSymlink(TypedDict):

    install_dir: str | None
    install_tag: str | None
    pointing_to: str


class FuncImportModule(ExtractRequired):

    disabler: bool


class FuncIncludeDirectories(TypedDict):

    is_system: bool

class FuncAddLanguages(ExtractRequired):

    native: MachineChoice | None

class RunTarget(TypedDict):

    command: list[build.CommandTypes]
    depends: list[TargetDepends]
    env: EnvironmentVariables


class CustomTarget(TypedDict):

    build_always: bool
    build_always_stale: bool | None
    build_by_default: bool | None
    build_subdir: str
    capture: bool
    command: list[build.CommandTypes]
    console: bool
    depend_files: list[FileOrString]
    depends: list[TargetDepends]
    depfile: str | None
    env: EnvironmentVariables
    feed: bool
    input: list[CustomTargetInputs]
    install: bool
    install_dir: list[str | T.Literal[False]]
    install_mode: FileMode
    install_tag: list[str | None]
    output: list[str]

class AddTestSetup(TypedDict):

    exe_wrapper: list[str | ExternalProgram]
    gdb: bool
    timeout_multiplier: int
    is_default: bool
    exclude_suites: list[str]
    env: EnvironmentVariables


class Project(TypedDict):

    version: FileOrString
    meson_version: str | None
    default_options: options.OptionDict
    license: list[str]
    license_files: list[str]
    subproject_dir: str


class _FoundProto(Protocol):

    """Protocol for subdir arguments.

    This allows us to define any object that has a found(self) -> bool method
    """

    def found(self) -> bool: ...


class Subdir(TypedDict):

    if_found: list[_FoundProto]


class Summary(TypedDict):

    section: str
    bool_yn: bool
    list_sep: str | None


class FindProgram(ExtractRequired, ExtractSearchDirs):

    default_options: dict[OptionKey, options.ElementaryOptionValues]
    native: MachineChoice
    version: list[str]
    version_argument: str


class RunCommand(TypedDict):

    check: bool
    capture: bool | None
    console: bool | None
    env: EnvironmentVariables


class FeatureOptionRequire(TypedDict):

    error_message: str | None


class DependencyPkgConfigVar(TypedDict):

    default: str | None
    define_variable: PkgConfigDefineType


class DependencyGetVariable(TypedDict):

    cmake: str | None
    pkgconfig: str | None
    configtool: str | None
    internal: str | None
    system: str | None
    default_value: str | None
    pkgconfig_define: PkgConfigDefineType


class ConfigurationDataSet(TypedDict):

    description: str | None

class VcsTag(TypedDict):

    command: list[build.CommandTypes]
    fallback: str | None
    input: list[CustomTargetInputs]
    output: list[str]
    replace_string: str
    install: bool
    install_tag: str | None
    install_dir: str | None
    install_mode: FileMode


class ConfigureFile(TypedDict):

    output: str
    capture: bool
    format: T.Literal['meson', 'cmake', 'cmake@']
    output_format: T.Literal['c', 'json', 'nasm']
    depfile: str | None
    install: bool | None
    install_dir: str | T.Literal[False]
    install_mode: FileMode
    install_tag: str | None
    encoding: str
    command: list[build.Executable | Program | Compiler | File | str] | None
    input: list[FileOrString]
    configuration: dict[str, str | int | bool] | build.ConfigurationData | None
    macro_name: str | None
    build_subdir: str
    copy: bool


class Subproject(ExtractRequired):

    default_options: dict[OptionKey, options.ElementaryOptionValues]
    version: list[str]
    native: MachineChoice


class DoSubproject(ExtractRequired):

    default_options: dict[OptionKey, options.ElementaryOptionValues]
    version: list[str]
    cmake_options: list[str]
    options: CMakeSubprojectOptions | None
    for_machine: MachineChoice


class BaseBuildTarget(TypedDict):

    """Arguments used by all BuildTarget like functions.

    This really exists because Jar is so different than all of the other
    BuildTarget functions.
    """

    build_by_default: bool
    build_rpath: str
    build_subdir: str
    dependencies: list[Dependency]
    extra_files: list[FileOrString]
    gnu_symbol_visibility: str
    include_directories: list[str | build.IncludeDirs]
    install: bool
    install_mode: FileMode
    install_tag: str | None
    install_rpath: str
    implicit_include_directories: bool
    link_depends: list[str | File | build.BuildTargetTypes]
    link_language: Language | None
    link_whole: list[build.StaticTargetTypes]
    link_with: list[build.LinkableTargetTypes]
    name_prefix: str | None
    name_suffix: str | None
    native: MachineChoice
    objects: list[BuildTargetObjects]
    override_options: dict[str, options.ElementaryOptionValues]
    depend_files: NotRequired[list[File]]
    resources: list[str]
    vala_header: str | None
    vala_vapi: str | None
    vala_gir: str | None


class BuildTarget(BaseBuildTarget):

    """Arguments shared by non-JAR functions"""

    d_debug: list[str | int]
    d_import_dirs: list[str | build.IncludeDirs]
    d_module_versions: list[str | int]
    d_unittest: bool
    install_dir: list[str | bool]
    install_vala_header: str | bool | None
    install_vala_vapi: str | bool | None
    install_vala_gir: str | bool | None
    rust_crate_type: Literal['bin', 'lib', 'rlib', 'dylib', 'cdylib', 'staticlib', 'proc-macro'] | None
    rust_dependency_map: dict[str, str]
    swift_interoperability_mode: Literal['c', 'cpp']
    swift_module_name: str
    sources: SourcesVarargsType
    link_args: list[str]
    link_early_args: list[str]
    c_pch: tuple[str, str | None] | None
    cpp_pch: tuple[str, str | None] | None
    c_args: list[str]
    cpp_args: list[str]
    cuda_args: list[str]
    fortran_args: list[str]
    d_args: list[str]
    objc_args: list[str]
    objcpp_args: list[str]
    rust_args: list[str]
    vala_args: list[str | File]  # Yes, Vala is really special
    cs_args: list[str]
    swift_args: list[str]
    cython_args: list[str]
    nasm_args: list[str]
    masm_args: list[str]


class _LibraryMixin(TypedDict):

    rust_abi: RustAbi | None


class _LinkableTargetMixin(TypedDict):

    vs_module_defs: str | File | build.CustomTarget | build.CustomTargetIndex | None
    win_subsystem: str | None


class _ExecutableMixin(TypedDict):

    export_dynamic: bool | None
    gui_app: bool | None
    implib: str | bool | None
    pie: bool | None
    android_exe_type: Literal['application', 'executable'] | None


class Executable(BuildTarget, _ExecutableMixin, _LinkableTargetMixin):
    pass


class _StaticLibMixin(TypedDict):

    prelink: bool
    pic: bool | None


class StaticLibrary(BuildTarget, _StaticLibMixin, _LibraryMixin):
    pass


class _SharedLibMixin(TypedDict):

    darwin_versions: tuple[str, str] | None
    soversion: str | None
    version: str | None
    shortname: str


class SharedLibrary(BuildTarget, _SharedLibMixin, _LibraryMixin, _LinkableTargetMixin):
    pass


class SharedModule(BuildTarget, _LibraryMixin, _LinkableTargetMixin):
    pass


class Library(BuildTarget, _SharedLibMixin, _StaticLibMixin, _LibraryMixin, _LinkableTargetMixin):

    """For library, both_library, and as a base for build_target"""

    c_static_args: NotRequired[list[str]]
    c_shared_args: NotRequired[list[str]]
    cpp_static_args: NotRequired[list[str]]
    cpp_shared_args: NotRequired[list[str]]
    cuda_static_args: NotRequired[list[str]]
    cuda_shared_args: NotRequired[list[str]]
    fortran_static_args: NotRequired[list[str]]
    fortran_shared_args: NotRequired[list[str]]
    d_static_args: NotRequired[list[str]]
    d_shared_args: NotRequired[list[str]]
    objc_static_args: NotRequired[list[str]]
    objc_shared_args: NotRequired[list[str]]
    objcpp_static_args: NotRequired[list[str]]
    objcpp_shared_args: NotRequired[list[str]]
    rust_static_args: NotRequired[list[str]]
    rust_shared_args: NotRequired[list[str]]
    vala_static_args: NotRequired[list[str | File]]  # Yes, Vala is really special
    vala_shared_args: NotRequired[list[str | File]]  # Yes, Vala is really special
    cs_static_args: NotRequired[list[str]]
    cs_shared_args: NotRequired[list[str]]
    swift_static_args: NotRequired[list[str]]
    swift_shared_args: NotRequired[list[str]]
    cython_static_args: NotRequired[list[str]]
    cython_shared_args: NotRequired[list[str]]
    nasm_static_args: NotRequired[list[str]]
    nasm_shared_args: NotRequired[list[str]]
    masm_static_args: NotRequired[list[str]]
    masm_shared_args: NotRequired[list[str]]


class _JarMixin(TypedDict):

    main_class: str
    java_resources: build.StructuredSources | None
    java_args: list[str]


class Jar(BaseBuildTarget, _JarMixin):

    sources: str | build.TargetSources | build.ExtractedObjects | build.BuildTarget


class BuildTargetFunc(Library, _ExecutableMixin, _JarMixin):

    target_type: Literal['executable', 'shared_library', 'static_library',
                         'shared_module', 'both_libraries', 'library', 'jar']


class FuncDeclareDependency(TypedDict):

    compile_args: list[str]
    d_import_dirs: list[build.IncludeDirs | str]
    d_module_versions: list[str | int]
    dependencies: list[Dependency]
    extra_files: list[FileOrString]
    include_directories: list[build.IncludeDirs | str]
    link_args: list[str]
    link_whole: list[build.StaticTargetTypes]
    link_with: list[build.LinkableTargetTypes]
    objects: list[build.ExtractedObjects]
    sources: list[str | build.TargetSources]
    variables: dict[str, str]
    version: str | None


class FuncDependency(ExtractRequired):

    allow_fallback: bool | None
    cmake_args: list[str]
    cmake_module_path: list[str]
    cmake_package_version: str
    components: list[str]
    default_options: dict[OptionKey, options.ElementaryOptionValues]
    fallback: str | list[str] | None
    include_type: IncludeType
    language: Language | None
    main: bool
    method: DependencyMethods
    modules: list[str]
    native: MachineChoice
    not_found_message: str
    optional_modules: list[str]
    private_headers: bool
    static: bool | None
    version: list[str]


class FuncExpectError(TypedDict):

    how: str


class FuncEnvironment(TypedDict):

    method: Literal['set', 'prepend', 'append']
    separator: str


class MachineMapArgs(TypedDict):

    native: NotRequired[MachineChoice]
    install: NotRequired[bool]
