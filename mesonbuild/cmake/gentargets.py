from configparser import ConfigParser

from importlib.resources import files
import re

from mesonbuild.build import InvalidArguments
from mesonbuild.options import OptionKey
from mesonbuild.utils.universal import SubProject

from heapq import heapify, heappop, heappush
from .. import build

from ..mesonlib import MesonBugException
from dataclasses import dataclass, field
from ..interpreter import Interpreter
import os
import posixpath

from .. import mesonlib
from typing import Any, TypedDict, List
from mesonbuild.utils.universal import FileMode

class CmakeTargetInfoDict(TypedDict):
    interface_include_dirs: List[str]
    interface_compile_defs: List[str]
    interface_compile_opts: List[str]
    interface_link_opts: List[str]
    interface_link_libraries: List[str]
    interface_internal_dependencies: List[str]

@dataclass
class CmakeTargetInfo():
    interface_include_dirs: list[str] = field(default_factory=list)
    interface_compile_defs: list[str] = field(default_factory=list)
    interface_compile_opts: list[str] = field(default_factory=list)
    interface_link_opts: list[str] = field(default_factory=list)
    interface_link_libraries: list[str] = field(default_factory=list)
    interface_internal_dependencies: list[str] = field(default_factory=list)

class CmakeTarget():
    def __init__(self, **kwargs: Any) -> None:
        self.target = kwargs.pop("target")
        self.current_build_dir: str = str(kwargs.pop("current_build_dir"))
        self.subproject: SubProject = kwargs.pop("subproject")
        self.namespace: str = self.normalize_namespace(str(kwargs.pop("namespace")))
        self.target_suffix: str = str(kwargs.pop("target_suffix"))
        self.target_info: CmakeTargetInfo = kwargs.pop("target_info")
        self.validate_namespace()
        self.validate_target_infos()
        self.validate_suffix()

        if isinstance(self.target, build.BothLibraries):
            raise InvalidArguments('You can\'t export both libraries, you must export each lib separated, and you can set a suffix to differ the targets')

    def normalize_namespace(self, namespace: str) -> str:
        if namespace == "":
            return namespace
        if not re.fullmatch(r'^[A-Za-z0-9_.+-]+(?:::[A-Za-z0-9_.+-]+)*(?:::)?$', namespace):
            raise InvalidArguments(
                f'Invalid CMake namespace: {namespace!r}'
            )

        return namespace.removesuffix('::') + '::'

    def validate_namespace(self) -> None:
        CMAKE_RESERVED_NAMESPACES = {
            'install',
            'help',
            'clean',
            'all',
            'test',
            'package',
            'cmake'
        }
        if self.namespace.rstrip(':') in CMAKE_RESERVED_NAMESPACES:
            raise InvalidArguments(
                f'Namespace {self.namespace!r} is reserved.'
            )

    def validate_target_infos(self) -> None:
        if not isinstance(self.target_info, CmakeTargetInfo):
            raise InvalidArguments(
                'CmakeTargetInfo is the only valid argument for targets differents of both libraries'
            )

    def validate_suffix(self) -> None:
        suffix = self.target_suffix
        if not suffix:
            return
        if not re.fullmatch(r'^[A-Za-z0-9_-][A-Za-z0-9_-]*$', suffix):
            raise InvalidArguments(
                'Invalid suffix pattern, must follow ^[A-Za-z0-9_-][A-Za-z0-9_-]*$'
            )

    def get_full_name(self) -> str:
        return str(self.namespace + self.target.name + self.target_suffix)

class CmakeTargets():
    def __init__(self, **kwargs: Any) -> None:
        config_file = files('mesonbuild.cmake').joinpath('cmake.cfg').read_text(encoding='utf-8')
        config = ConfigParser()
        config.read_string(config_file)
        self.COMPILER_FAMILIES = {
            'gcc': 'gcc',
            'g++': 'gcc',
            'clang': 'clang',
            'clang++': 'clang',
            'apple-clang': 'clang',
            'apple-clang++': 'clang',
            'clang-cl': 'msvc',
            'msvc': 'msvc',
            'intel': 'intel',
            'intel-cl': 'msvc',
        }
        self.MESON_2_CMAKE_BUILD_MODES = {
            'debug': 'Debug',
            'release': 'Release',
            'debugoptimized': 'RelWithDebInfo',
            'minsize': 'MinSizeRel',
        }
        self.target_handlers = {
            build.Executable: self.handle_executable_target,
            build.SharedLibrary: self.handle_shared_lib_target,
            build.StaticLibrary: self.handle_static_lib_target,
            build.SharedModule: self.handle_module_target,
        }

        self.targets: dict[str, CmakeTarget] = {}
        self.interpreter: Interpreter = kwargs.pop("interpreter")
        self.os = kwargs.pop("os")
        self.project_name = kwargs.pop("project_name")
        self.install_prefix = kwargs.pop("install_prefix")
        self.files_infix = kwargs.pop("files_infix")
        self.compiler = self.normalize_build_system(kwargs.pop("compiler"))
        self.linker = kwargs.pop("linker")
        self.build_mode = kwargs.pop("build_mode")
        self.min_cmake_version_policy = config.get('options', 'min_policy_version')
        self.validate_version(self.min_cmake_version_policy)
        self.max_cmake_version_policy = config.get('options', 'max_policy_version')
        self.validate_version(self.max_cmake_version_policy)
        self.validate_max_policy_greater_than_min()
        libdir = self.interpreter.environment.coredata.optstore.get_value_for(OptionKey('libdir'))
        assert isinstance(libdir, str), 'for mypy'
        self.target_template = files('mesonbuild.cmake.assets').joinpath('targetFile.cmake.in').read_text(encoding='utf-8')
        self.write_target_static_info()
        self.target_template_build_mode = files('mesonbuild.cmake.assets').joinpath('targetFileBuildMode.cmake.in').read_text(encoding='utf-8')
        self.write_target_build_mode_static_info()
        self.install_dir = posixpath.join('lib', 'cmake', self.project_name)
        self.executable_export_template = files('mesonbuild.cmake.assets').joinpath('executableInfo.cmake.in').read_text(encoding='utf-8')
        self.executable_export_build_mode_template = files('mesonbuild.cmake.assets').joinpath('executableInfoBuildMode.cmake.in').read_text(encoding='utf-8')
        self.library_export_template = files('mesonbuild.cmake.assets').joinpath('libraryInfo.cmake.in').read_text(encoding='utf-8')
        self.shared_library_export_build_mode_template = files('mesonbuild.cmake.assets').joinpath('sharedLibraryInfoBuildMode.cmake.in').read_text(encoding='utf-8')
        self.static_library_export_build_mode_template = files('mesonbuild.cmake.assets').joinpath('staticLibraryInfoBuildMode.cmake.in').read_text(encoding='utf-8')
        self.module_library_export_build_mode_template = files('mesonbuild.cmake.assets').joinpath('moduleLibraryInfoBuildMode.cmake.in').read_text(encoding='utf-8')
        self.policy_set: bool = False

    def normalize_build_system(self, compiler_id: str) -> str:
        unorm_compiler = self.COMPILER_FAMILIES.get(compiler_id, compiler_id)
        if self.os == "windows":
            mingw_envs = ['gcc', 'clang']
            if unorm_compiler in mingw_envs:
                unorm_compiler = f"mingw-{unorm_compiler}"
        return unorm_compiler

    def register_cmake_target(self, target: CmakeTarget) -> None:
        full_target = target.get_full_name()

        if full_target in self.targets:
            raise InvalidArguments(
                f'Duplicate CMake target: {full_target}'
            )

        self.targets[full_target] = target

    def set_policies(self, **kwargs: Any) -> bool:
        if not self.policy_set:
            self.min_cmake_version_policy = kwargs.pop("min_cmake_version_policy")
        return not self.policy_set

    def validate_version(self, version: str) -> None:
        #^[0-9]+[\.][0-9]+[\.][0-9]+$
        if not re.fullmatch(r'^[0-9]+[\.][0-9]+[\.][0-9]+$', version):
            raise MesonBugException(
                'Invalid version format, it must follow the pattern: <major>.<minor>.<patch>'
            )

    def validate_max_policy_greater_than_min(self) -> None:
        min_policy_major, min_policy_minor, min_policy_patch = self.min_cmake_version_policy.split('.')
        max_policy_major, max_policy_minor, max_policy_patch = self.max_cmake_version_policy.split('.')
        num_min_version = (
            int(min_policy_major) * 1_000_000 +
            int(min_policy_minor) * 1_000 +
            int(min_policy_patch)
        )
        num_max_version = (
            int(max_policy_major) * 1_000_000 +
            int(max_policy_minor) * 1_000 +
            int(max_policy_patch)
        )
        if num_min_version > num_max_version:
            raise MesonBugException('CMake max policy must be greater than the min version')

    def write_target_files(self) -> None:
        if not self.targets:
            return
        self.write_merged_targets()

    def write_merged_targets(self) -> None:
        ordered_targets = self.sort_targets_topologically()
        subproject = ordered_targets[0].subproject
        build_dir = ordered_targets[0].current_build_dir
        target_keys: list[str] = []
        merged_targets_info = ""
        merged_targets_info_build_mode = ""
        for target in ordered_targets:
            target_keys.append(target.get_full_name())
            handler = self.target_handlers.get(type(target.target))
            if handler is None:
                raise MesonBugException(f'Unsupported target type: {type(target).__name__}')
            (target_infos, target_infos_build_mode) = handler(target)
            merged_targets_info += target_infos
            merged_targets_info_build_mode += target_infos_build_mode

        merged_targets_info = merged_targets_info[:-2]
        merged_targets_info_build_mode = merged_targets_info_build_mode[:-2]
        self.write_target(merged_targets_info, subproject, build_dir, target_keys)
        self.write_target_config(merged_targets_info_build_mode, subproject, build_dir)

    def write_target_static_info(self) -> None:
        min_policy_major, min_policy_minor, min_policy_patch = self.min_cmake_version_policy.split('.')
        max_policy_major, max_policy_minor, _ = self.max_cmake_version_policy.split('.')
        self.target_template = self.target_template.replace('@CMAKE_MIN_VERSION_MAJ_MIN_PATCH@', f'{min_policy_major}.{min_policy_minor}.{min_policy_patch}')
        self.target_template = self.target_template.replace('@CMAKE_MIN_VERSION_MAJ_MIN@', f'{min_policy_major}.{min_policy_minor}')
        self.target_template = self.target_template.replace('@CMAKE_MAX_VERSION_MAJ_MIN@', f'{max_policy_major}.{max_policy_minor}')
        self.target_template = self.target_template.replace('@MESON_PROJECT_NAME@', self.project_name)

    def write_target_build_mode_static_info(self) -> None:
        cmake_build_mode = self.get_current_cmake_build_mode()
        self.target_template_build_mode = self.target_template_build_mode.replace('@CAPITAL_BUILD_MODE@', cmake_build_mode)

    def get_current_cmake_build_mode(self) -> str:
        cmake_build_mode = self.MESON_2_CMAKE_BUILD_MODES.get(self.build_mode, 'Debug')
        return cmake_build_mode

    def write_target(
        self,
        meson_targets_export: str,
        subproject: SubProject,
        build_dir: str,
        target_keys: list[str]
    ) -> None:
        target_template = self.target_template
        target_template = target_template.replace('@MESON_TARGETS_EXPORT@', meson_targets_export)

        #MESON_TARGETS_EXPORT
        treated_target_names = ""
        treated_target_names = ' '.join(target_keys)
        target_template = target_template.replace('@CMAKE_TARGET_NAMES@', treated_target_names)

        relative_install_dir_count: int = len(self.install_dir.split('/'))
        path_prefix_relative_move_up_text: str = ""
        for _ in range(relative_install_dir_count):
            path_prefix_relative_move_up_text += "get_filename_component(_IMPORT_PREFIX \"${_IMPORT_PREFIX}\" PATH)\n"
        target_template = target_template.replace('@RELATIVE_PREFIX_PATH@', path_prefix_relative_move_up_text)

        outfile_tmp = os.path.join(self.interpreter.environment.build_dir, build_dir, f'{self.project_name}Targets.cmake')
        with open(outfile_tmp, "w", encoding='utf-8') as fout:
            fout.write(target_template)

        (ofile_path, ofile_fname) = os.path.split(os.path.join(build_dir, f'{self.project_name}Targets.cmake'))
        res = build.Data([mesonlib.File(True, ofile_path, ofile_fname)], self.install_dir, self.install_dir, FileMode(), subproject)
        self.interpreter.build.data.append(res)

    def write_target_config(
        self,
        meson_targets_build_mode_export: str,
        subproject: SubProject,
        build_dir: str
    ) -> None:
        target_template_build_mode = self.target_template_build_mode
        target_template_build_mode = target_template_build_mode.replace('@TARGETS_BUILD_MODE@', meson_targets_build_mode_export)

        cmake_build_mode = self.get_current_cmake_build_mode()

        outfile_tmp = os.path.join(self.interpreter.environment.build_dir, build_dir, f'{self.project_name}Targets-{cmake_build_mode.lower()}.cmake')
        with open(outfile_tmp, "w", encoding='utf-8') as fout:
            fout.write(target_template_build_mode)

        (ofile_path, ofile_fname) = os.path.split(os.path.join(build_dir, f'{self.project_name}Targets-{cmake_build_mode.lower()}.cmake'))
        res = build.Data([mesonlib.File(True, ofile_path, ofile_fname)], self.install_dir, self.install_dir, FileMode(), subproject)
        self.interpreter.build.data.append(res)

    def handle_executable_target(self, target: CmakeTarget) -> tuple[str, str]:
        executable_name = target.get_full_name()
        executable_relative_path = self.get_target_relative_path(target)
        target_code = self.executable_export_template
        target_code = target_code.replace('@EXECUTABLE_NAME@', executable_name)

        cmake_build_mode = self.get_current_cmake_build_mode()
        target_build_mode_code = self.executable_export_build_mode_template
        target_build_mode_code = target_build_mode_code.replace('@EXECUTABLE_NAME@', executable_name)
        target_build_mode_code = target_build_mode_code.replace('@EXECUTABLE_RELATIVE_PATH@', executable_relative_path)
        target_build_mode_code = target_build_mode_code.replace('@CMAKE_BUILD_MODE@', cmake_build_mode)
        target_build_mode_code = target_build_mode_code.replace('@UPPER_CMAKE_BUILD_MODE@', cmake_build_mode.upper())
        return (target_code, target_build_mode_code)

    def handle_static_lib_target(self, target: CmakeTarget) -> tuple[str, str]:
        library_name = target.get_full_name()
        library_relative_path = self.get_target_relative_path(target)
        treated_target_infos = self.fill_in_target_info(target)
        target_code = self.replace_lib_target_code(
            library_type="STATIC",
            library_name=library_name,
            treated_target_infos=treated_target_infos
        )

        target_build_mode_code = self.replace_static_lib_build_mode_target_code(
            library_relative_path= library_relative_path,
            target_compile_languages= target.target.compilers.keys(),
            library_name= library_name
        )
        return (target_code, target_build_mode_code)

    def handle_shared_lib_target(self, target: CmakeTarget) -> tuple[str, str]:
        library_name = target.get_full_name()
        library_relative_path = self.get_target_relative_path(target)
        treated_target_infos = self.fill_in_target_info(target)
        target_code = self.replace_lib_target_code(
            library_type="SHARED",
            library_name=library_name,
            treated_target_infos=treated_target_infos
        )

        check_files_impl_lib = ""
        if self.os == 'windows':
            imported_impl_so_lib, check_files_impl_lib = self.gen_import_lib_artifacts(target=target)
        else:
            imported_impl_so_lib = self.gen_so_name(target=target)

        target_build_mode_code = self.replace_shared_lib_build_mode_target_code(
            library_relative_path= library_relative_path,
            check_files_impl_lib= check_files_impl_lib,
            imported_impl_so_lib= imported_impl_so_lib,
            library_name= library_name
        )
        return (target_code, target_build_mode_code)

    def handle_module_target(self, target: CmakeTarget) -> tuple[str, str]:
        library_name = target.get_full_name()
        library_relative_path = self.get_target_relative_path(target)
        treated_target_infos = self.fill_in_target_info(target)
        target_code = self.replace_lib_target_code(
            library_type="MODULE",
            library_name=library_name,
            treated_target_infos=treated_target_infos
        )

        target_build_mode_code = self.replace_module_lib_build_mode_target_code(
            library_relative_path= library_relative_path,
            shared_object_version_arg= self.gen_so_suffix(target),
            common_language_runtime= self.get_common_language_runtime(target),
            library_name= library_name
        )

        return (target_code, target_build_mode_code)

    def replace_lib_target_code(
        self,
        library_type: str,
        library_name: str,
        treated_target_infos: str
    ) -> str:
        library_type = library_type.upper()
        allowed_library_types = ["SHARED", "STATIC", "MODULE"]
        if library_type not in allowed_library_types:
            raise MesonBugException("Libs can be only shared, static or module")
        target_code = self.library_export_template
        target_code = target_code.replace('@LIBRARY_TYPE@', library_type)
        target_code = target_code.replace('@LIBRARY_NAME@', library_name)
        target_code = target_code.replace('@TREATED_TARGET_INFOS@', treated_target_infos)
        return target_code

    def replace_static_lib_build_mode_target_code(
        self,
        library_relative_path: str,
        target_compile_languages: list[str],
        library_name: str
    ) -> str:
        target_compile_languages_merged = ""
        for target_compile_language in target_compile_languages:
            target_compile_language = target_compile_language.upper()
            allowed_library_types = ["C", "CPP"]
            if target_compile_language not in allowed_library_types:
                raise MesonBugException("Only c or cpp are valid compile languages")
            if target_compile_language == "CPP":
                target_compile_language = "CXX"
            target_compile_languages_merged += f"{target_compile_language};"
        target_compile_languages_merged = target_compile_languages_merged[:-1]
        cmake_build_mode = self.get_current_cmake_build_mode()
        target_build_mode_code = self.static_library_export_build_mode_template
        target_build_mode_code = target_build_mode_code.replace('@LIBRARY_NAME@', library_name)
        target_build_mode_code = target_build_mode_code.replace('@LIBRARY_RELATIVE_PATH@', library_relative_path)
        target_build_mode_code = target_build_mode_code.replace('@CMAKE_TARGET_COMPILE_LANGUAGES@', target_compile_languages_merged)
        target_build_mode_code = target_build_mode_code.replace('@UPPER_CMAKE_BUILD_MODE@', cmake_build_mode.upper())
        return target_build_mode_code

    def replace_shared_lib_build_mode_target_code(
        self,
        library_relative_path: str,
        check_files_impl_lib: str,
        imported_impl_so_lib: str,
        library_name: str
    ) -> str:
        cmake_build_mode = self.get_current_cmake_build_mode()
        target_build_mode_code = self.shared_library_export_build_mode_template
        target_build_mode_code = target_build_mode_code.replace('@LIBRARY_NAME@', library_name)
        target_build_mode_code = target_build_mode_code.replace('@LIBRARY_RELATIVE_PATH@', library_relative_path)
        target_build_mode_code = target_build_mode_code.replace('@CHECK_FILES_IMPL_LIB@', check_files_impl_lib)
        target_build_mode_code = target_build_mode_code.replace('@IMPORTED_IMPL_SO_LIB@', imported_impl_so_lib)
        target_build_mode_code = target_build_mode_code.replace('@CMAKE_BUILD_MODE@', cmake_build_mode)
        target_build_mode_code = target_build_mode_code.replace('@UPPER_CMAKE_BUILD_MODE@', cmake_build_mode.upper())
        return target_build_mode_code

    def gen_import_lib_artifacts(self, target: CmakeTarget) -> tuple[str, str]:
        cmake_build_mode = self.get_current_cmake_build_mode()
        impl_lib = ""
        imported_impl_lib = ""
        check_files_impl_lib = ""
        if self.os == 'windows':
            for index, directory in enumerate(target.target.install_dir):
                if (directory == "bin") and (index == len(target.target.install_dir) - 1):
                    directory = 'lib'
                impl_lib = posixpath.join(impl_lib, str(directory))
            impl_lib = posixpath.join(impl_lib, str(target.target.import_filename))
            imported_impl_lib = f"\n  IMPORTED_IMPLIB_{cmake_build_mode.upper()} \"${{_IMPORT_PREFIX}}/{impl_lib}\""
            check_files_impl_lib = f"\"${{_IMPORT_PREFIX}}/{impl_lib}\" "
        return imported_impl_lib, check_files_impl_lib

    def gen_so_name(self, target: CmakeTarget) -> str:
        so_name = ""
        cmake_build_mode = self.get_current_cmake_build_mode()
        if not self.os == 'windows':
            final_filename = target.target.filename
            treated_soversion = ''
            if target.target.soversion:
                treated_soversion = target.target.soversion
            if (target.target.ltversion and target.target.ltversion != ''):
                final_filename = final_filename.replace(target.target.ltversion, '')
            final_filename += treated_soversion
            so_name = f"\n  IMPORTED_SONAME_{cmake_build_mode.upper()} \"{final_filename}\""
        return so_name

    def replace_module_lib_build_mode_target_code(
        self,
        library_relative_path: str,
        library_name: str,
        shared_object_version_arg: str,
        common_language_runtime: str
    ) -> str:
        cmake_build_mode = self.get_current_cmake_build_mode()
        target_build_mode_code = self.module_library_export_build_mode_template
        target_build_mode_code = target_build_mode_code.replace('@LIBRARY_NAME@', library_name)
        target_build_mode_code = target_build_mode_code.replace('@LIBRARY_RELATIVE_PATH@', library_relative_path)
        target_build_mode_code = target_build_mode_code.replace('@SHARED_OBJECT_VERSION_ARG@', shared_object_version_arg)
        target_build_mode_code = target_build_mode_code.replace('@COMMON_LANGUAGE_RUNTIME@', common_language_runtime)
        target_build_mode_code = target_build_mode_code.replace('@CMAKE_BUILD_MODE@', cmake_build_mode)
        target_build_mode_code = target_build_mode_code.replace('@UPPER_CMAKE_BUILD_MODE@', cmake_build_mode.upper())
        return target_build_mode_code

    def gen_so_suffix(self, target: CmakeTarget) -> str:
        if self.os == 'windows':
            return ""
        so_arg = ""
        if self.os != 'darwin':
            #linux|*bsd
            cmake_build_mode = self.get_current_cmake_build_mode().upper()
            no_so_import = "TRUE"
            if target.target.soversion:
                no_so_import = "FALSE"
            so_arg = f"\n  IMPORTED_NO_SONAME_{cmake_build_mode} \"{no_so_import}\""
        return so_arg

    def get_common_language_runtime(self, target: CmakeTarget) -> str:
        return ""

    def get_target_relative_path(self, target: CmakeTarget) -> str:
        target_relative_path = ""
        for directory in target.target.install_dir:
            target_relative_path = posixpath.join(target_relative_path, str(directory))
        target_relative_path = posixpath.join(target_relative_path, target.target.filename)
        return target_relative_path

    def fill_in_target_info(self, target: CmakeTarget) -> str:
        target_treated_info = ""
        target_treated_info_list: list[str] = []
        normalized_definitions: list[str] = [
            self.normalize_definition(definition)
            for definition in target.target_info.interface_compile_defs
        ]
        target_treated_info_list.append(
            self.fill_in_property
            (
                normalized_definitions,
                "INTERFACE_COMPILE_DEFINITIONS"
            )
        )
        target_treated_info_list.append(
            self.fill_in_property(
                target.target_info.interface_compile_opts,
                "INTERFACE_COMPILE_OPTIONS"
            )
        )
        target_treated_info_list.append(
            self.fill_in_property(
                target.target_info.interface_include_dirs,
                "INTERFACE_INCLUDE_DIRECTORIES",
                "${_IMPORT_PREFIX}/"
            )
        )
        target_treated_info_list.append(
            self.fill_in_property(
                target.target_info.interface_link_libraries + target.target_info.interface_internal_dependencies,
                "INTERFACE_LINK_LIBRARIES"
            )
        )
        target_treated_info_list.append(
            self.fill_in_property(
                target.target_info.interface_link_opts,
                "INTERFACE_LINK_OPTIONS"
            )
        )
        for target_treated_info_element in target_treated_info_list:
            if target_treated_info_element:
                target_treated_info += f"{target_treated_info_element}\n"
        target_treated_info = target_treated_info[:-1]
        return target_treated_info

    def fill_in_property(self, property_list: list[str], property_name: str, property_prefix: str = "") -> str:
        filled_in_property: str = ""
        packed_property = ""
        for property in property_list:
            packed_property += f"{property_prefix}{property};"
        if packed_property:
            packed_property = packed_property[:-1]
            filled_in_property = f"  {property_name} \"{packed_property}\""
        return filled_in_property

    def normalize_definition(self, definition: str) -> str:
        if not re.fullmatch(r'^(?:-D)?[A-Za-z_][A-Za-z_0-9]*$', definition):
            raise InvalidArguments(
                'Definitions must follow the expression ^(?:-D)?[A-Za-z_][A-Za-z_0-9]*$'
            )
        if definition.startswith("-D"):
            definition = definition.removeprefix("-D")

        return definition

    def sort_targets_topologically(self) -> list[CmakeTarget]:

        dependents: dict[str, set[str]] = {
            name: set()
            for name in self.targets
        }

        indegree: dict[str, int] = {
            name: 0
            for name in self.targets
        }

        for name, target in self.targets.items():
            dependencies = set(
                target.target_info.interface_internal_dependencies
            )

            for dependency in dependencies:
                if dependency not in self.targets:
                    continue

                if name not in dependents[dependency]:
                    dependents[dependency].add(name)
                    indegree[name] += 1

        ready = [
            name
            for name, degree in indegree.items()
            if degree == 0
        ]

        heapify(ready)

        ordered_names: list[str] = []

        while ready:
            name = heappop(ready)
            ordered_names.append(name)

            for dependent in sorted(dependents[name]):
                indegree[dependent] -= 1

                if indegree[dependent] == 0:
                    heappush(ready, dependent)

        if len(ordered_names) != len(self.targets):
            remaining = [
                name
                for name, degree in indegree.items()
                if degree > 0
            ]

            raise InvalidArguments(
                'Circular dependencies detected between CMake targets: '
                f'{", ".join(remaining)}'
            )

        return [
            self.targets[name]
            for name in ordered_names
        ]
