# Copyright 2019 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This class contains the basic functionality needed to run any interpreter
# or an interpreter-based tool.

import pkg_resources

from .common import CMakeException, CMakeTarget, TargetOptions
from .client import CMakeClient, RequestCMakeInputs, RequestConfigure, RequestCompute, RequestCodeModel
from .fileapi import CMakeFileAPI
from .executor import CMakeExecutor
from .traceparser import CMakeTraceParser, CMakeGeneratorTarget
from .. import mlog, mesonlib
from ..environment import Environment
from ..mesonlib import MachineChoice, OrderedSet, version_compare
from ..compilers.compilers import lang_suffixes, header_suffixes, obj_suffixes, lib_suffixes, is_header
from enum import Enum
from functools import lru_cache
from pathlib import Path
import typing as T
import os, re

from ..mparser import (
    Token,
    BaseNode,
    CodeBlockNode,
    FunctionNode,
    ArrayNode,
    ArgumentNode,
    AssignmentNode,
    BooleanNode,
    StringNode,
    IdNode,
    IndexNode,
    MethodNode,
    NumberNode,
)


if T.TYPE_CHECKING:
    from ..build import Build
    from ..backend.backends import Backend

# Disable all warnings automaticall enabled with --trace and friends
# See https://cmake.org/cmake/help/latest/variable/CMAKE_POLICY_WARNING_CMPNNNN.html
disable_policy_warnings = [
    'CMP0025',
    'CMP0047',
    'CMP0056',
    'CMP0060',
    'CMP0065',
    'CMP0066',
    'CMP0067',
    'CMP0082',
    'CMP0089',
]

backend_generator_map = {
    'ninja': 'Ninja',
    'xcode': 'Xcode',
    'vs2010': 'Visual Studio 10 2010',
    'vs2015': 'Visual Studio 15 2017',
    'vs2017': 'Visual Studio 15 2017',
    'vs2019': 'Visual Studio 16 2019',
}

language_map = {
    'c': 'C',
    'cpp': 'CXX',
    'cuda': 'CUDA',
    'objc': 'OBJC',
    'objcpp': 'OBJCXX',
    'cs': 'CSharp',
    'java': 'Java',
    'fortran': 'Fortran',
    'swift': 'Swift',
}

target_type_map = {
    'STATIC_LIBRARY': 'static_library',
    'MODULE_LIBRARY': 'shared_module',
    'SHARED_LIBRARY': 'shared_library',
    'EXECUTABLE': 'executable',
    'OBJECT_LIBRARY': 'static_library',
    'INTERFACE_LIBRARY': 'header_only'
}

skip_targets = ['UTILITY']

blacklist_compiler_flags = [
    '-Wall', '-Wextra', '-Weverything', '-Werror', '-Wpedantic', '-pedantic', '-w',
    '/W1', '/W2', '/W3', '/W4', '/Wall', '/WX', '/w',
    '/O1', '/O2', '/Ob', '/Od', '/Og', '/Oi', '/Os', '/Ot', '/Ox', '/Oy', '/Ob0',
    '/RTC1', '/RTCc', '/RTCs', '/RTCu',
    '/Z7', '/Zi', '/ZI',
]

blacklist_link_flags = [
    '/machine:x64', '/machine:x86', '/machine:arm', '/machine:ebc',
    '/debug', '/debug:fastlink', '/debug:full', '/debug:none',
    '/incremental',
]

blacklist_clang_cl_link_flags = ['/GR', '/EHsc', '/MDd', '/Zi', '/RTC1']

blacklist_link_libs = [
    'kernel32.lib',
    'user32.lib',
    'gdi32.lib',
    'winspool.lib',
    'shell32.lib',
    'ole32.lib',
    'oleaut32.lib',
    'uuid.lib',
    'comdlg32.lib',
    'advapi32.lib'
]

transfer_dependencies_from = ['header_only']

_cmake_name_regex = re.compile(r'[^_a-zA-Z0-9]')
def _sanitize_cmake_name(name: str) -> str:
    name = _cmake_name_regex.sub('_', name)
    return 'cm_' + name

class OutputTargetMap:
    rm_so_version = re.compile(r'(\.[0-9]+)+$')

    def __init__(self, build_dir: str):
        self.tgt_map = {}
        self.build_dir = build_dir

    def add(self, tgt: T.Union['ConverterTarget', 'ConverterCustomTarget']) -> None:
        def assign_keys(keys: T.List[str]) -> None:
            for i in [x for x in keys if x]:
                self.tgt_map[i] = tgt
        keys = [self._target_key(tgt.cmake_name)]
        if isinstance(tgt, ConverterTarget):
            keys += [tgt.full_name]
            keys += [self._rel_artifact_key(x) for x in tgt.artifacts]
            keys += [self._base_artifact_key(x) for x in tgt.artifacts]
        if isinstance(tgt, ConverterCustomTarget):
            keys += [self._rel_generated_file_key(x) for x in tgt.original_outputs]
            keys += [self._base_generated_file_key(x) for x in tgt.original_outputs]
        assign_keys(keys)

    def _return_first_valid_key(self, keys: T.List[str]) -> T.Optional[T.Union['ConverterTarget', 'ConverterCustomTarget']]:
        for i in keys:
            if i and i in self.tgt_map:
                return self.tgt_map[i]
        return None

    def target(self, name: str) -> T.Optional[T.Union['ConverterTarget', 'ConverterCustomTarget']]:
        return self._return_first_valid_key([self._target_key(name)])

    def executable(self, name: str) -> T.Optional['ConverterTarget']:
        tgt = self.target(name)
        if tgt is None or not isinstance(tgt, ConverterTarget):
            return None
        if tgt.meson_func() != 'executable':
            return None
        return tgt

    def artifact(self, name: str) -> T.Optional[T.Union['ConverterTarget', 'ConverterCustomTarget']]:
        keys = []
        candidates = [name, OutputTargetMap.rm_so_version.sub('', name)]
        for i in lib_suffixes:
            if not name.endswith('.' + i):
                continue
            new_name = name[:-len(i) - 1]
            new_name = OutputTargetMap.rm_so_version.sub('', new_name)
            candidates += ['{}.{}'.format(new_name, i)]
        for i in candidates:
            keys += [self._rel_artifact_key(i), os.path.basename(i), self._base_artifact_key(i)]
        return self._return_first_valid_key(keys)

    def generated(self, name: str) -> T.Optional[T.Union['ConverterTarget', 'ConverterCustomTarget']]:
        return self._return_first_valid_key([self._rel_generated_file_key(name), self._base_generated_file_key(name)])

    # Utility functions to generate local keys
    def _rel_path(self, fname: str) -> T.Optional[str]:
        fname = os.path.normpath(os.path.join(self.build_dir, fname))
        if os.path.commonpath([self.build_dir, fname]) != self.build_dir:
            return None
        return os.path.relpath(fname, self.build_dir)

    def _target_key(self, tgt_name: str) -> str:
        return '__tgt_{}__'.format(tgt_name)

    def _rel_generated_file_key(self, fname: str) -> T.Optional[str]:
        path = self._rel_path(fname)
        return '__relgen_{}__'.format(path) if path else None

    def _base_generated_file_key(self, fname: str) -> str:
        return '__gen_{}__'.format(os.path.basename(fname))

    def _rel_artifact_key(self, fname: str) -> T.Optional[str]:
        path = self._rel_path(fname)
        return '__relart_{}__'.format(path) if path else None

    def _base_artifact_key(self, fname: str) -> str:
        return '__art_{}__'.format(os.path.basename(fname))

class ConverterTarget:
    def __init__(self, target: CMakeTarget, env: Environment):
        self.env = env
        self.artifacts = target.artifacts
        self.src_dir = target.src_dir
        self.build_dir = target.build_dir
        self.name = target.name
        self.cmake_name = target.name
        self.full_name = target.full_name
        self.type = target.type
        self.install = target.install
        self.install_dir = ''
        self.link_libraries = target.link_libraries
        self.link_flags = target.link_flags + target.link_lang_flags
        self.depends_raw = []
        self.depends = []

        if target.install_paths:
            self.install_dir = target.install_paths[0]

        self.languages = []
        self.sources = []
        self.generated = []
        self.includes = []
        self.sys_includes = []
        self.link_with = []
        self.object_libs = []
        self.compile_opts = {}
        self.public_compile_opts = []
        self.pie = False

        # Project default override options (c_std, cpp_std, etc.)
        self.override_options = []

        # Convert the target name to a valid meson target name
        self.name = _sanitize_cmake_name(self.name)

        for i in target.files:
            # Determine the meson language
            lang_cmake_to_meson = {val.lower(): key for key, val in language_map.items()}
            lang = lang_cmake_to_meson.get(i.language.lower(), 'c')
            if lang not in self.languages:
                self.languages += [lang]
            if lang not in self.compile_opts:
                self.compile_opts[lang] = []

            # Add arguments, but avoid duplicates
            args = i.flags
            args += ['-D{}'.format(x) for x in i.defines]
            self.compile_opts[lang] += [x for x in args if x not in self.compile_opts[lang]]

            # Handle include directories
            self.includes += [x['path'] for x in i.includes if x not in self.includes and not x['isSystem']]
            self.sys_includes += [x['path'] for x in i.includes if x not in self.sys_includes and x['isSystem']]

            # Add sources to the right array
            if i.is_generated:
                self.generated += i.sources
            else:
                self.sources += i.sources

    def __repr__(self) -> str:
        return '<{}: {}>'.format(self.__class__.__name__, self.name)

    std_regex = re.compile(r'([-]{1,2}std=|/std:v?|[-]{1,2}std:)(.*)')

    def postprocess(self, output_target_map: OutputTargetMap, root_src_dir: str, subdir: str, install_prefix: str, trace: CMakeTraceParser) -> None:
        # Detect setting the C and C++ standard
        for i in ['c', 'cpp']:
            if i not in self.compile_opts:
                continue

            temp = []
            for j in self.compile_opts[i]:
                m = ConverterTarget.std_regex.match(j)
                if m:
                    std = m.group(2)
                    supported = self._all_lang_stds(i)
                    if std not in supported:
                        mlog.warning(
                            'Unknown {0}_std "{1}" -> Ignoring. Try setting the project-'
                            'level {0}_std if build errors occur. Known '
                            '{0}_stds are: {2}'.format(i, std, ' '.join(supported)),
                            once=True
                        )
                        continue
                    self.override_options += ['{}_std={}'.format(i, std)]
                elif j in ['-fPIC', '-fpic', '-fPIE', '-fpie']:
                    self.pie = True
                elif j in blacklist_compiler_flags:
                    pass
                else:
                    temp += [j]

            self.compile_opts[i] = temp

        # Make sure to force enable -fPIC for OBJECT libraries
        if self.type.upper() == 'OBJECT_LIBRARY':
            self.pie = True

        # Use the CMake trace, if required
        tgt = trace.targets.get(self.cmake_name)
        if tgt:
            self.depends_raw = trace.targets[self.cmake_name].depends

            # TODO refactor this copy paste from CMakeDependency for future releases
            reg_is_lib = re.compile(r'^(-l[a-zA-Z0-9_]+|-l?pthread)$')
            to_process = [self.cmake_name]
            processed = []
            while len(to_process) > 0:
                curr = to_process.pop(0)

                if curr in processed or curr not in trace.targets:
                    continue

                tgt = trace.targets[curr]
                cfgs = []
                cfg = ''
                otherDeps = []
                libraries = []
                mlog.debug(tgt)

                if 'INTERFACE_INCLUDE_DIRECTORIES' in tgt.properties:
                    self.includes += [x for x in tgt.properties['INTERFACE_INCLUDE_DIRECTORIES'] if x]

                if 'INTERFACE_LINK_OPTIONS' in tgt.properties:
                    self.link_flags += [x for x in tgt.properties['INTERFACE_LINK_OPTIONS'] if x]

                if 'INTERFACE_COMPILE_DEFINITIONS' in tgt.properties:
                    self.public_compile_opts += ['-D' + re.sub('^-D', '', x) for x in tgt.properties['INTERFACE_COMPILE_DEFINITIONS'] if x]

                if 'INTERFACE_COMPILE_OPTIONS' in tgt.properties:
                    self.public_compile_opts += [x for x in tgt.properties['INTERFACE_COMPILE_OPTIONS'] if x]

                if 'IMPORTED_CONFIGURATIONS' in tgt.properties:
                    cfgs += [x for x in tgt.properties['IMPORTED_CONFIGURATIONS'] if x]
                    cfg = cfgs[0]

                if 'CONFIGURATIONS' in tgt.properties:
                    cfgs += [x for x in tgt.properties['CONFIGURATIONS'] if x]
                    cfg = cfgs[0]

                is_debug = self.env.coredata.get_builtin_option('debug');
                if is_debug:
                    if 'DEBUG' in cfgs:
                        cfg = 'DEBUG'
                    elif 'RELEASE' in cfgs:
                        cfg = 'RELEASE'
                else:
                    if 'RELEASE' in cfgs:
                        cfg = 'RELEASE'

                if 'IMPORTED_IMPLIB_{}'.format(cfg) in tgt.properties:
                    libraries += [x for x in tgt.properties['IMPORTED_IMPLIB_{}'.format(cfg)] if x]
                elif 'IMPORTED_IMPLIB' in tgt.properties:
                    libraries += [x for x in tgt.properties['IMPORTED_IMPLIB'] if x]
                elif 'IMPORTED_LOCATION_{}'.format(cfg) in tgt.properties:
                    libraries += [x for x in tgt.properties['IMPORTED_LOCATION_{}'.format(cfg)] if x]
                elif 'IMPORTED_LOCATION' in tgt.properties:
                    libraries += [x for x in tgt.properties['IMPORTED_LOCATION'] if x]

                if 'LINK_LIBRARIES' in tgt.properties:
                    otherDeps += [x for x in tgt.properties['LINK_LIBRARIES'] if x]

                if 'INTERFACE_LINK_LIBRARIES' in tgt.properties:
                    otherDeps += [x for x in tgt.properties['INTERFACE_LINK_LIBRARIES'] if x]

                if 'IMPORTED_LINK_DEPENDENT_LIBRARIES_{}'.format(cfg) in tgt.properties:
                    otherDeps += [x for x in tgt.properties['IMPORTED_LINK_DEPENDENT_LIBRARIES_{}'.format(cfg)] if x]
                elif 'IMPORTED_LINK_DEPENDENT_LIBRARIES' in tgt.properties:
                    otherDeps += [x for x in tgt.properties['IMPORTED_LINK_DEPENDENT_LIBRARIES'] if x]

                for j in otherDeps:
                    if j in trace.targets:
                        to_process += [j]
                    elif reg_is_lib.match(j) or os.path.exists(j):
                        libraries += [j]

                for j in libraries:
                    if j not in self.link_libraries:
                        self.link_libraries += [j]

                processed += [curr]
        elif self.type.upper() not in ['EXECUTABLE', 'OBJECT_LIBRARY']:
            mlog.warning('CMake: Target', mlog.bold(self.cmake_name), 'not found in CMake trace. This can lead to build errors')

        temp = []
        for i in self.link_libraries:
            # Let meson handle this arcane magic
            if ',-rpath,' in i:
                continue
            if not os.path.isabs(i):
                link_with = output_target_map.artifact(i)
                if link_with:
                    self.link_with += [link_with]
                    continue

            temp += [i]
        self.link_libraries = temp

        # Filter out files that are not supported by the language
        supported = list(header_suffixes) + list(obj_suffixes)
        for i in self.languages:
            supported += list(lang_suffixes[i])
        supported = ['.{}'.format(x) for x in supported]
        self.sources = [x for x in self.sources if any([x.endswith(y) for y in supported])]
        self.generated = [x for x in self.generated if any([x.endswith(y) for y in supported])]

        # Make paths relative
        def rel_path(x: str, is_header: bool, is_generated: bool) -> T.Optional[str]:
            if not os.path.isabs(x):
                x = os.path.normpath(os.path.join(self.src_dir, x))
            if not os.path.exists(x) and not any([x.endswith(y) for y in obj_suffixes]) and not is_generated:
                mlog.warning('CMake: path', mlog.bold(x), 'does not exist.')
                mlog.warning(' --> Ignoring. This can lead to build errors.')
                return None
            if Path(x) in trace.explicit_headers:
                return None
            if (
                os.path.isabs(x)
                    and os.path.commonpath([x, self.env.get_source_dir()]) == self.env.get_source_dir()
                    and not (
                        os.path.commonpath([x, root_src_dir]) == root_src_dir or
                        os.path.commonpath([x, self.env.get_build_dir()]) == self.env.get_build_dir()
                    )
                ):
                mlog.warning('CMake: path', mlog.bold(x), 'is inside the root project but', mlog.bold('not'), 'inside the subproject.')
                mlog.warning(' --> Ignoring. This can lead to build errors.')
                return None
            if os.path.isabs(x) and os.path.commonpath([x, self.env.get_build_dir()]) == self.env.get_build_dir():
                if is_header:
                    return os.path.relpath(x, os.path.join(self.env.get_build_dir(), subdir))
                else:
                    return os.path.relpath(x, root_src_dir)
            if os.path.isabs(x) and os.path.commonpath([x, root_src_dir]) == root_src_dir:
                return os.path.relpath(x, root_src_dir)
            return x

        def custom_target(x: str):
            ctgt = output_target_map.generated(x)
            if ctgt:
                assert(isinstance(ctgt, ConverterCustomTarget))
                ref = ctgt.get_ref(x)
                assert(isinstance(ref, CustomTargetReference) and ref.valid())
                return ref
            return x

        build_dir_rel = os.path.relpath(self.build_dir, os.path.join(self.env.get_build_dir(), subdir))
        self.includes = list(OrderedSet([rel_path(x, True, False) for x in OrderedSet(self.includes)] + [build_dir_rel]))
        self.sys_includes = list(OrderedSet([rel_path(x, True, False) for x in OrderedSet(self.sys_includes)]))
        self.sources = [rel_path(x, False, False) for x in self.sources]
        self.generated = [rel_path(x, False, True) for x in self.generated]

        # Resolve custom targets
        self.generated = [custom_target(x) for x in self.generated]

        # Remove delete entries
        self.includes = [x for x in self.includes if x is not None]
        self.sys_includes = [x for x in self.sys_includes if x is not None]
        self.sources = [x for x in self.sources if x is not None]
        self.generated = [x for x in self.generated if x is not None]

        # Make sure '.' is always in the include directories
        if '.' not in self.includes:
            self.includes += ['.']

        # make install dir relative to the install prefix
        if self.install_dir and os.path.isabs(self.install_dir):
            if os.path.commonpath([self.install_dir, install_prefix]) == install_prefix:
                self.install_dir = os.path.relpath(self.install_dir, install_prefix)

        # Remove blacklisted options and libs
        def check_flag(flag: str) -> bool:
            if flag.lower() in blacklist_link_flags or flag in blacklist_compiler_flags + blacklist_clang_cl_link_flags:
                return False
            if flag.startswith('/D'):
                return False
            return True

        self.link_libraries = [x for x in self.link_libraries if x.lower() not in blacklist_link_libs]
        self.link_flags = [x for x in self.link_flags if check_flag(x)]

        # Handle explicit CMake add_dependency() calls
        for i in self.depends_raw:
            tgt = output_target_map.target(i)
            if tgt:
                self.depends.append(tgt)

    def process_object_libs(self, obj_target_list: T.List['ConverterTarget'], linker_workaround: bool):
        # Try to detect the object library(s) from the generated input sources
        temp = [x for x in self.generated if isinstance(x, str)]
        temp = [os.path.basename(x) for x in temp]
        temp = [x for x in temp if any([x.endswith('.' + y) for y in obj_suffixes])]
        temp = [os.path.splitext(x)[0] for x in temp]
        exts = self._all_source_suffixes()
        # Temp now stores the source filenames of the object files
        for i in obj_target_list:
            source_files = [x for x in i.sources + i.generated if isinstance(x, str)]
            source_files = [os.path.basename(x) for x in source_files]
            for j in temp:
                # On some platforms (specifically looking at you Windows with vs20xy backend) CMake does
                # not produce object files with the format `foo.cpp.obj`, instead it skipps the language
                # suffix and just produces object files like `foo.obj`. Thus we have to do our best to
                # undo this step and guess the correct language suffix of the object file. This is done
                # by trying all language suffixes meson knows and checking if one of them fits.
                candidates = [j]  # type: T.List[str]
                if not any([j.endswith('.' + x) for x in exts]):
                    mlog.warning('Object files do not contain source file extensions, thus falling back to guessing them.', once=True)
                    candidates += ['{}.{}'.format(j, x) for x in exts]
                if any([x in source_files for x in candidates]):
                    if linker_workaround:
                        self._append_objlib_sources(i)
                    else:
                        self.includes += i.includes
                        self.includes = list(OrderedSet(self.includes))
                        self.object_libs += [i]
                    break

        # Filter out object files from the sources
        self.generated = [x for x in self.generated if not isinstance(x, str) or not any([x.endswith('.' + y) for y in obj_suffixes])]

    def _append_objlib_sources(self, tgt: 'ConverterTarget') -> None:
        self.includes += tgt.includes
        self.sources += tgt.sources
        self.generated += tgt.generated
        self.sources = list(OrderedSet(self.sources))
        self.generated = list(OrderedSet(self.generated))
        self.includes = list(OrderedSet(self.includes))

        # Inherit compiler arguments since they may be required for building
        for lang, opts in tgt.compile_opts.items():
            if lang not in self.compile_opts:
                self.compile_opts[lang] = []
            self.compile_opts[lang] += [x for x in opts if x not in self.compile_opts[lang]]

    @lru_cache(maxsize=None)
    def _all_source_suffixes(self) -> T.List[str]:
        suffixes = []  # type: T.List[str]
        for exts in lang_suffixes.values():
            suffixes += [x for x in exts]
        return suffixes

    @lru_cache(maxsize=None)
    def _all_lang_stds(self, lang: str) -> T.List[str]:
        lang_opts = self.env.coredata.compiler_options.build.get(lang, None)
        if not lang_opts or 'std' not in lang_opts:
            return []
        return lang_opts['std'].choices

    def process_inter_target_dependencies(self):
        # Move the dependencies from all transfer_dependencies_from to the target
        to_process = list(self.depends)
        processed = []
        new_deps = []
        for i in to_process:
            processed += [i]
            if isinstance(i, ConverterTarget) and i.meson_func() in transfer_dependencies_from:
                to_process += [x for x in i.depends if x not in processed]
            else:
                new_deps += [i]
        self.depends = list(OrderedSet(new_deps))

    def cleanup_dependencies(self):
        # Clear the dependencies from targets that where moved from
        if self.meson_func() in transfer_dependencies_from:
            self.depends = []

    def meson_func(self) -> str:
        return target_type_map.get(self.type.upper())

    def log(self) -> None:
        mlog.log('Target', mlog.bold(self.name), '({})'.format(self.cmake_name))
        mlog.log('  -- artifacts:      ', mlog.bold(str(self.artifacts)))
        mlog.log('  -- full_name:      ', mlog.bold(self.full_name))
        mlog.log('  -- type:           ', mlog.bold(self.type))
        mlog.log('  -- install:        ', mlog.bold('true' if self.install else 'false'))
        mlog.log('  -- install_dir:    ', mlog.bold(self.install_dir))
        mlog.log('  -- link_libraries: ', mlog.bold(str(self.link_libraries)))
        mlog.log('  -- link_with:      ', mlog.bold(str(self.link_with)))
        mlog.log('  -- object_libs:    ', mlog.bold(str(self.object_libs)))
        mlog.log('  -- link_flags:     ', mlog.bold(str(self.link_flags)))
        mlog.log('  -- languages:      ', mlog.bold(str(self.languages)))
        mlog.log('  -- includes:       ', mlog.bold(str(self.includes)))
        mlog.log('  -- sys_includes:   ', mlog.bold(str(self.sys_includes)))
        mlog.log('  -- sources:        ', mlog.bold(str(self.sources)))
        mlog.log('  -- generated:      ', mlog.bold(str(self.generated)))
        mlog.log('  -- pie:            ', mlog.bold('true' if self.pie else 'false'))
        mlog.log('  -- override_opts:  ', mlog.bold(str(self.override_options)))
        mlog.log('  -- depends:        ', mlog.bold(str(self.depends)))
        mlog.log('  -- options:')
        for key, val in self.compile_opts.items():
            mlog.log('    -', key, '=', mlog.bold(str(val)))

class CustomTargetReference:
    def __init__(self, ctgt: 'ConverterCustomTarget', index: int):
        self.ctgt = ctgt    # type: ConverterCustomTarget
        self.index = index  # type: int

    def __repr__(self) -> str:
        if self.valid():
            return '<{}: {} [{}]>'.format(self.__class__.__name__, self.ctgt.name, self.ctgt.outputs[self.index])
        else:
            return '<{}: INVALID REFERENCE>'.format(self.__class__.__name__)

    def valid(self) -> bool:
        return self.ctgt is not None and self.index >= 0

    def filename(self) -> str:
        return self.ctgt.outputs[self.index]

class ConverterCustomTarget:
    tgt_counter = 0  # type: int
    out_counter = 0  # type: int

    def __init__(self, target: CMakeGeneratorTarget):
        assert(target.current_bin_dir is not None)
        assert(target.current_src_dir is not None)
        self.name = target.name
        if not self.name:
            self.name = 'custom_tgt_{}'.format(ConverterCustomTarget.tgt_counter)
            ConverterCustomTarget.tgt_counter += 1
        self.cmake_name = str(self.name)
        self.original_outputs = list(target.outputs)
        self.outputs = [os.path.basename(x) for x in self.original_outputs]
        self.conflict_map = {}
        self.command = target.command
        self.working_dir = target.working_dir
        self.depends_raw = target.depends
        self.inputs = []
        self.depends = []
        self.current_bin_dir = Path(target.current_bin_dir)
        self.current_src_dir = Path(target.current_src_dir)

        # Convert the target name to a valid meson target name
        self.name = _sanitize_cmake_name(self.name)

    def __repr__(self) -> str:
        return '<{}: {} {}>'.format(self.__class__.__name__, self.name, self.outputs)

    def postprocess(self, output_target_map: OutputTargetMap, root_src_dir: str, subdir: str, all_outputs: T.List[str]) -> None:
        # Default the working directory to ${CMAKE_CURRENT_BINARY_DIR}
        if not self.working_dir:
            self.working_dir = self.current_bin_dir.as_posix()

        # relative paths in the working directory are always relative
        # to ${CMAKE_CURRENT_BINARY_DIR}
        if not os.path.isabs(self.working_dir):
            self.working_dir = (self.current_bin_dir / self.working_dir).as_posix()

        # Modify the original outputs if they are relative. Again,
        # relative paths are relative to ${CMAKE_CURRENT_BINARY_DIR}
        def ensure_absolute(x: Path) -> Path:
            if x.is_absolute():
                return x
            else:
                return self.current_bin_dir / x
        self.original_outputs = [ensure_absolute(Path(x)).as_posix() for x in self.original_outputs]

        # Ensure that there is no duplicate output in the project so
        # that meson can handle cases where the same filename is
        # generated in multiple directories
        temp_outputs = []  # type: T.List[str]
        for i in self.outputs:
            if i in all_outputs:
                old = str(i)
                i = 'c{}_{}'.format(ConverterCustomTarget.out_counter, i)
                ConverterCustomTarget.out_counter += 1
                self.conflict_map[old] = i
            all_outputs += [i]
            temp_outputs += [i]
        self.outputs = temp_outputs

        # Check if the command is a build target
        commands = []
        for i in self.command:
            assert(isinstance(i, list))
            cmd = []

            for j in i:
                if not j:
                    continue
                target = output_target_map.executable(j)
                cmd += [target] if target else [j]

            commands += [cmd]
        self.command = commands

        # If the custom target does not declare any output, create a dummy
        # one that can be used as dependency.
        if not self.outputs:
            self.outputs = [self.name + '.h']

        # Check dependencies and input files
        root = Path(root_src_dir)
        for i in self.depends_raw:
            if not i:
                continue
            raw = Path(i)
            art = output_target_map.artifact(i)
            tgt = output_target_map.target(i)
            gen = output_target_map.generated(i)

            rel_to_root = None
            try:
                rel_to_root = raw.relative_to(root)
            except ValueError:
                rel_to_root = None

            # First check for existing files. Only then check for existing
            # targets, etc. This reduces the chance of misdetecting input files
            # as outputs from other targets.
            # See https://github.com/mesonbuild/meson/issues/6632
            if not raw.is_absolute() and (self.current_src_dir / raw).exists():
                self.inputs += [(self.current_src_dir / raw).relative_to(root).as_posix()]
            elif raw.is_absolute() and raw.exists() and rel_to_root is not None:
                self.inputs += [rel_to_root.as_posix()]
            elif art:
                self.depends += [art]
            elif tgt:
                self.depends += [tgt]
            elif gen:
                self.inputs += [gen.get_ref(i)]

    def process_inter_target_dependencies(self):
        # Move the dependencies from all transfer_dependencies_from to the target
        to_process = list(self.depends)
        processed = []
        new_deps = []
        for i in to_process:
            processed += [i]
            if isinstance(i, ConverterTarget) and i.meson_func() in transfer_dependencies_from:
                to_process += [x for x in i.depends if x not in processed]
            else:
                new_deps += [i]
        self.depends = list(OrderedSet(new_deps))

    def get_ref(self, fname: str) -> T.Optional[CustomTargetReference]:
        fname = os.path.basename(fname)
        try:
            if fname in self.conflict_map:
                fname = self.conflict_map[fname]
            idx = self.outputs.index(fname)
            return CustomTargetReference(self, idx)
        except ValueError:
            return None

    def log(self) -> None:
        mlog.log('Custom Target', mlog.bold(self.name), '({})'.format(self.cmake_name))
        mlog.log('  -- command:      ', mlog.bold(str(self.command)))
        mlog.log('  -- outputs:      ', mlog.bold(str(self.outputs)))
        mlog.log('  -- conflict_map: ', mlog.bold(str(self.conflict_map)))
        mlog.log('  -- working_dir:  ', mlog.bold(str(self.working_dir)))
        mlog.log('  -- depends_raw:  ', mlog.bold(str(self.depends_raw)))
        mlog.log('  -- inputs:       ', mlog.bold(str(self.inputs)))
        mlog.log('  -- depends:      ', mlog.bold(str(self.depends)))

class CMakeAPI(Enum):
    SERVER = 1
    FILE = 2

class CMakeInterpreter:
    def __init__(self, build: 'Build', subdir: str, src_dir: str, install_prefix: str, env: Environment, backend: 'Backend'):
        assert(hasattr(backend, 'name'))
        self.build = build
        self.subdir = subdir
        self.src_dir = src_dir
        self.build_dir_rel = os.path.join(subdir, '__CMake_build')
        self.build_dir = os.path.join(env.get_build_dir(), self.build_dir_rel)
        self.install_prefix = install_prefix
        self.env = env
        self.backend_name = backend.name
        self.linkers = set()  # type: T.Set[str]
        self.cmake_api = CMakeAPI.SERVER
        self.client = CMakeClient(self.env)
        self.fileapi = CMakeFileAPI(self.build_dir)

        # Raw CMake results
        self.bs_files = []
        self.codemodel_configs = None
        self.raw_trace = None

        # Analysed data
        self.project_name = ''
        self.languages = []
        self.targets = []
        self.custom_targets = []  # type: T.List[ConverterCustomTarget]
        self.trace = CMakeTraceParser('', '')  # Will be replaced in analyse
        self.output_target_map = OutputTargetMap(self.build_dir)

        # Generated meson data
        self.generated_targets = {}
        self.internal_name_map = {}

    def configure(self, extra_cmake_options: T.List[str]) -> None:
        for_machine = MachineChoice.HOST # TODO make parameter
        # Find CMake
        cmake_exe = CMakeExecutor(self.env, '>=3.7', for_machine)
        if not cmake_exe.found():
            raise CMakeException('Unable to find CMake')
        self.trace = CMakeTraceParser(cmake_exe.version(), self.build_dir, permissive=True)

        preload_file = pkg_resources.resource_filename('mesonbuild', 'cmake/data/preload.cmake')

        # Prefere CMAKE_PROJECT_INCLUDE over CMAKE_TOOLCHAIN_FILE if possible,
        # since CMAKE_PROJECT_INCLUDE was actually designed for code injection.
        preload_var = 'CMAKE_PROJECT_INCLUDE'
        if version_compare(cmake_exe.version(), '<3.15'):
            preload_var = 'CMAKE_TOOLCHAIN_FILE'

        generator = backend_generator_map[self.backend_name]
        cmake_args = []
        trace_args = self.trace.trace_args()
        cmcmp_args = ['-DCMAKE_POLICY_WARNING_{}=OFF'.format(x) for x in disable_policy_warnings]
        pload_args = ['-D{}={}'.format(preload_var, str(preload_file))]

        if version_compare(cmake_exe.version(), '>=3.14'):
            self.cmake_api = CMakeAPI.FILE
            self.fileapi.setup_request()

        # Map meson compiler to CMake variables
        for lang, comp in self.env.coredata.compilers[for_machine].items():
            if lang not in language_map:
                continue
            self.linkers.add(comp.get_linker_id())
            cmake_lang = language_map[lang]
            exelist = comp.get_exelist()
            if len(exelist) == 1:
                cmake_args += ['-DCMAKE_{}_COMPILER={}'.format(cmake_lang, exelist[0])]
            elif len(exelist) == 2:
                cmake_args += ['-DCMAKE_{}_COMPILER_LAUNCHER={}'.format(cmake_lang, exelist[0]),
                               '-DCMAKE_{}_COMPILER={}'.format(cmake_lang, exelist[1])]
            if hasattr(comp, 'get_linker_exelist') and comp.get_id() == 'clang-cl':
                cmake_args += ['-DCMAKE_LINKER={}'.format(comp.get_linker_exelist()[0])]
        cmake_args += ['-G', generator]
        cmake_args += ['-DCMAKE_INSTALL_PREFIX={}'.format(self.install_prefix)]
        cmake_args += extra_cmake_options

        # Run CMake
        mlog.log()
        with mlog.nested():
            mlog.log('Configuring the build directory with', mlog.bold('CMake'), 'version', mlog.cyan(cmake_exe.version()))
            mlog.log(mlog.bold('Running:'), ' '.join(cmake_args))
            mlog.log(mlog.bold('  - build directory:         '), self.build_dir)
            mlog.log(mlog.bold('  - source directory:        '), self.src_dir)
            mlog.log(mlog.bold('  - trace args:              '), ' '.join(trace_args))
            mlog.log(mlog.bold('  - preload file:            '), str(preload_file))
            mlog.log(mlog.bold('  - disabled policy warnings:'), '[{}]'.format(', '.join(disable_policy_warnings)))
            mlog.log()
            os.makedirs(self.build_dir, exist_ok=True)
            os_env = os.environ.copy()
            os_env['LC_ALL'] = 'C'
            final_args = cmake_args + trace_args + cmcmp_args + pload_args + [self.src_dir]

            cmake_exe.set_exec_mode(print_cmout=True, always_capture_stderr=self.trace.requires_stderr())
            rc, _, self.raw_trace = cmake_exe.call(final_args, self.build_dir, env=os_env, disable_cache=True)

        mlog.log()
        h = mlog.green('SUCCEEDED') if rc == 0 else mlog.red('FAILED')
        mlog.log('CMake configuration:', h)
        if rc != 0:
            raise CMakeException('Failed to configure the CMake subproject')

    def initialise(self, extra_cmake_options: T.List[str]) -> None:
        # Run configure the old way because doing it
        # with the server doesn't work for some reason
        # Additionally, the File API requires a configure anyway
        self.configure(extra_cmake_options)

        # Continue with the file API If supported
        if self.cmake_api is CMakeAPI.FILE:
            # Parse the result
            self.fileapi.load_reply()

            # Load the buildsystem file list
            cmake_files = self.fileapi.get_cmake_sources()
            self.bs_files = [x.file for x in cmake_files if not x.is_cmake and not x.is_temp]
            self.bs_files = [os.path.relpath(x, self.env.get_source_dir()) for x in self.bs_files]
            self.bs_files = list(OrderedSet(self.bs_files))

            # Load the codemodel configurations
            self.codemodel_configs = self.fileapi.get_cmake_configurations()
            return

        with self.client.connect():
            generator = backend_generator_map[self.backend_name]
            self.client.do_handshake(self.src_dir, self.build_dir, generator, 1)

            # Do a second configure to initialise the server
            self.client.query_checked(RequestConfigure(), 'CMake server configure')

            # Generate the build system files
            self.client.query_checked(RequestCompute(), 'Generating build system files')

            # Get CMake build system files
            bs_reply = self.client.query_checked(RequestCMakeInputs(), 'Querying build system files')

            # Now get the CMake code model
            cm_reply = self.client.query_checked(RequestCodeModel(), 'Querying the CMake code model')

        src_dir = bs_reply.src_dir
        self.bs_files = [x.file for x in bs_reply.build_files if not x.is_cmake and not x.is_temp]
        self.bs_files = [os.path.relpath(os.path.join(src_dir, x), self.env.get_source_dir()) for x in self.bs_files]
        self.bs_files = list(OrderedSet(self.bs_files))
        self.codemodel_configs = cm_reply.configs

    def analyse(self) -> None:
        if self.codemodel_configs is None:
            raise CMakeException('CMakeInterpreter was not initialized')

        # Clear analyser data
        self.project_name = ''
        self.languages = []
        self.targets = []
        self.custom_targets = []

        # Parse the trace
        self.trace.parse(self.raw_trace)

        # Find all targets
        added_target_names = []  # type: T.List[str]
        for i in self.codemodel_configs:
            for j in i.projects:
                if not self.project_name:
                    self.project_name = j.name
                for k in j.targets:
                    # Avoid duplicate targets from different configurations and known
                    # dummy CMake internal target types
                    if k.type not in skip_targets and k.name not in added_target_names:
                        added_target_names += [k.name]
                        self.targets += [ConverterTarget(k, self.env)]

        # Add interface targets from trace, if not already present.
        # This step is required because interface targets were removed from
        # the CMake file API output.
        api_target_name_list = [x.name for x in self.targets]
        for i in self.trace.targets.values():
            if i.type != 'INTERFACE' or i.name in api_target_name_list or i.imported:
                continue
            dummy = CMakeTarget({
                'name': i.name,
                'type': 'INTERFACE_LIBRARY',
                'sourceDirectory': self.src_dir,
                'buildDirectory': self.build_dir,
            })
            self.targets += [ConverterTarget(dummy, self.env)]

        for i in self.trace.custom_targets:
            self.custom_targets += [ConverterCustomTarget(i)]

        # generate the output_target_map
        for i in [*self.targets, *self.custom_targets]:
            self.output_target_map.add(i)

        # First pass: Basic target cleanup
        object_libs = []
        custom_target_outputs = []  # type: T.List[str]
        for i in self.custom_targets:
            i.postprocess(self.output_target_map, self.src_dir, self.subdir, custom_target_outputs)
        for i in self.targets:
            i.postprocess(self.output_target_map, self.src_dir, self.subdir, self.install_prefix, self.trace)
            if i.type == 'OBJECT_LIBRARY':
                object_libs += [i]
            self.languages += [x for x in i.languages if x not in self.languages]

        # Second pass: Detect object library dependencies
        for i in self.targets:
            i.process_object_libs(object_libs, self._object_lib_workaround())

        # Third pass: Reassign dependencies to avoid some loops
        for i in self.targets:
            i.process_inter_target_dependencies()
        for i in self.custom_targets:
            i.process_inter_target_dependencies()

        # Fourth pass: Remove rassigned dependencies
        for i in self.targets:
            i.cleanup_dependencies()

        mlog.log('CMake project', mlog.bold(self.project_name), 'has', mlog.bold(str(len(self.targets) + len(self.custom_targets))), 'build targets.')

    def pretend_to_be_meson(self, options: TargetOptions) -> CodeBlockNode:
        if not self.project_name:
            raise CMakeException('CMakeInterpreter was not analysed')

        def token(tid: str = 'string', val='') -> Token:
            return Token(tid, self.subdir, 0, 0, 0, None, val)

        def string(value: str) -> StringNode:
            return StringNode(token(val=value))

        def id_node(value: str) -> IdNode:
            return IdNode(token(val=value))

        def number(value: int) -> NumberNode:
            return NumberNode(token(val=value))

        def nodeify(value):
            if isinstance(value, str):
                return string(value)
            elif isinstance(value, bool):
                return BooleanNode(token(val=value))
            elif isinstance(value, int):
                return number(value)
            elif isinstance(value, list):
                return array(value)
            return value

        def indexed(node: BaseNode, index: int) -> IndexNode:
            return IndexNode(node, nodeify(index))

        def array(elements) -> ArrayNode:
            args = ArgumentNode(token())
            if not isinstance(elements, list):
                elements = [args]
            args.arguments += [nodeify(x) for x in elements if x is not None]
            return ArrayNode(args, 0, 0, 0, 0)

        def function(name: str, args=None, kwargs=None) -> FunctionNode:
            args = [] if args is None else args
            kwargs = {} if kwargs is None else kwargs
            args_n = ArgumentNode(token())
            if not isinstance(args, list):
                args = [args]
            args_n.arguments = [nodeify(x) for x in args if x is not None]
            args_n.kwargs = {id_node(k): nodeify(v) for k, v in kwargs.items() if v is not None}
            func_n = FunctionNode(self.subdir, 0, 0, 0, 0, name, args_n)
            return func_n

        def method(obj: BaseNode, name: str, args=None, kwargs=None) -> MethodNode:
            args = [] if args is None else args
            kwargs = {} if kwargs is None else kwargs
            args_n = ArgumentNode(token())
            if not isinstance(args, list):
                args = [args]
            args_n.arguments = [nodeify(x) for x in args if x is not None]
            args_n.kwargs = {id_node(k): nodeify(v) for k, v in kwargs.items() if v is not None}
            return MethodNode(self.subdir, 0, 0, obj, name, args_n)

        def assign(var_name: str, value: BaseNode) -> AssignmentNode:
            return AssignmentNode(self.subdir, 0, 0, var_name, value)

        # Generate the root code block and the project function call
        root_cb = CodeBlockNode(token())
        root_cb.lines += [function('project', [self.project_name] + self.languages)]

        # Add the run script for custom commands

        # Add the targets
        processing = []
        processed = {}
        name_map = {}

        def extract_tgt(tgt: T.Union[ConverterTarget, ConverterCustomTarget, CustomTargetReference]) -> IdNode:
            tgt_name = None
            if isinstance(tgt, (ConverterTarget, ConverterCustomTarget)):
                tgt_name = tgt.name
            elif isinstance(tgt, CustomTargetReference):
                tgt_name = tgt.ctgt.name
            assert(tgt_name is not None and tgt_name in processed)
            res_var = processed[tgt_name]['tgt']
            return id_node(res_var) if res_var else None

        def detect_cycle(tgt: T.Union[ConverterTarget, ConverterCustomTarget]) -> None:
            if tgt.name in processing:
                raise CMakeException('Cycle in CMake inputs/dependencies detected')
            processing.append(tgt.name)

        def resolve_ctgt_ref(ref: CustomTargetReference) -> BaseNode:
            tgt_var = extract_tgt(ref)
            if len(ref.ctgt.outputs) == 1:
                return tgt_var
            else:
                return indexed(tgt_var, ref.index)

        def process_target(tgt: ConverterTarget):
            detect_cycle(tgt)

            # First handle inter target dependencies
            link_with = []
            objec_libs = []  # type: T.List[IdNode]
            sources = []
            generated = []
            generated_filenames = []
            custom_targets = []
            dependencies = []
            for i in tgt.link_with:
                assert(isinstance(i, ConverterTarget))
                if i.name not in processed:
                    process_target(i)
                link_with += [extract_tgt(i)]
            for i in tgt.object_libs:
                assert(isinstance(i, ConverterTarget))
                if i.name not in processed:
                    process_target(i)
                objec_libs += [extract_tgt(i)]
            for i in tgt.depends:
                if not isinstance(i, ConverterCustomTarget):
                    continue
                if i.name not in processed:
                    process_custom_target(i)
                dependencies += [extract_tgt(i)]

            # Generate the source list and handle generated sources
            for i in tgt.sources + tgt.generated:
                if isinstance(i, CustomTargetReference):
                    if i.ctgt.name not in processed:
                        process_custom_target(i.ctgt)
                    generated += [resolve_ctgt_ref(i)]
                    generated_filenames += [i.filename()]
                    if i.ctgt not in custom_targets:
                        custom_targets += [i.ctgt]
                else:
                    sources += [i]

            # Add all header files from all used custom targets. This
            # ensures that all custom targets are built before any
            # sources of the current target are compiled and thus all
            # header files are present. This step is necessary because
            # CMake always ensures that a custom target is executed
            # before another target if at least one output is used.
            for i in custom_targets:
                for j in i.outputs:
                    if not is_header(j) or j in generated_filenames:
                        continue

                    generated += [resolve_ctgt_ref(i.get_ref(j))]
                    generated_filenames += [j]

            # Determine the meson function to use for the build target
            tgt_func = tgt.meson_func()
            if not tgt_func:
                raise CMakeException('Unknown target type "{}"'.format(tgt.type))

            # Determine the variable names
            inc_var = '{}_inc'.format(tgt.name)
            dir_var = '{}_dir'.format(tgt.name)
            sys_var = '{}_sys'.format(tgt.name)
            src_var = '{}_src'.format(tgt.name)
            dep_var = '{}_dep'.format(tgt.name)
            tgt_var = tgt.name

            install_tgt = options.get_install(tgt.cmake_name, tgt.install)

            # Generate target kwargs
            tgt_kwargs = {
                'build_by_default': install_tgt,
                'link_args': options.get_link_args(tgt.cmake_name, tgt.link_flags + tgt.link_libraries),
                'link_with': link_with,
                'include_directories': id_node(inc_var),
                'install': install_tgt,
                'override_options': options.get_override_options(tgt.cmake_name, tgt.override_options),
                'objects': [method(x, 'extract_all_objects') for x in objec_libs],
            }

            # Only set if installed and only override if it is set
            if install_tgt and tgt.install_dir:
                tgt_kwargs['install_dir'] = tgt.install_dir

            # Handle compiler args
            for key, val in tgt.compile_opts.items():
                tgt_kwargs['{}_args'.format(key)] = options.get_compile_args(tgt.cmake_name, key, val)

            # Handle -fPCI, etc
            if tgt_func == 'executable':
                tgt_kwargs['pie'] = tgt.pie
            elif tgt_func == 'static_library':
                tgt_kwargs['pic'] = tgt.pie

            # declare_dependency kwargs
            dep_kwargs = {
                'link_args': tgt.link_flags + tgt.link_libraries,
                'link_with': id_node(tgt_var),
                'compile_args': tgt.public_compile_opts,
                'include_directories': id_node(inc_var),
            }

            if dependencies:
                generated += dependencies

            # Generate the function nodes
            dir_node = assign(dir_var, function('include_directories', tgt.includes))
            sys_node = assign(sys_var, function('include_directories', tgt.sys_includes, {'is_system': True}))
            inc_node = assign(inc_var, array([id_node(dir_var), id_node(sys_var)]))
            node_list = [dir_node, sys_node, inc_node]
            if tgt_func == 'header_only':
                del dep_kwargs['link_with']
                dep_node = assign(dep_var, function('declare_dependency', kwargs=dep_kwargs))
                node_list += [dep_node]
                src_var = None
                tgt_var = None
            else:
                src_node = assign(src_var, function('files', sources))
                tgt_node = assign(tgt_var, function(tgt_func, [tgt_var, [id_node(src_var)] + generated], tgt_kwargs))
                node_list += [src_node, tgt_node]
                if tgt_func in ['static_library', 'shared_library']:
                    dep_node = assign(dep_var, function('declare_dependency', kwargs=dep_kwargs))
                    node_list += [dep_node]
                else:
                    dep_var = None

            # Add the nodes to the ast
            root_cb.lines += node_list
            processed[tgt.name] = {'inc': inc_var, 'src': src_var, 'dep': dep_var, 'tgt': tgt_var, 'func': tgt_func}
            name_map[tgt.cmake_name] = tgt.name

        def process_custom_target(tgt: ConverterCustomTarget) -> None:
            # CMake allows to specify multiple commands in a custom target.
            # To map this to meson, a helper script is used to execute all
            # commands in order. This additionally allows setting the working
            # directory.

            detect_cycle(tgt)
            tgt_var = tgt.name  # type: str

            def resolve_source(x: T.Any) -> T.Any:
                if isinstance(x, ConverterTarget):
                    if x.name not in processed:
                        process_target(x)
                    return extract_tgt(x)
                if isinstance(x, ConverterCustomTarget):
                    if x.name not in processed:
                        process_custom_target(x)
                    return extract_tgt(x)
                elif isinstance(x, CustomTargetReference):
                    if x.ctgt.name not in processed:
                        process_custom_target(x.ctgt)
                    return resolve_ctgt_ref(x)
                else:
                    return x

            # Generate the command list
            command = []
            command += mesonlib.meson_command
            command += ['--internal', 'cmake_run_ctgt']
            command += ['-o', '@OUTPUT@']
            if tgt.original_outputs:
                command += ['-O'] + tgt.original_outputs
            command += ['-d', tgt.working_dir]

            # Generate the commands. Subcommands are separated by ';;;'
            for cmd in tgt.command:
                command += [resolve_source(x) for x in cmd] + [';;;']

            tgt_kwargs = {
                'input': [resolve_source(x) for x in tgt.inputs],
                'output': tgt.outputs,
                'command': command,
                'depends': [resolve_source(x) for x in tgt.depends],
            }

            root_cb.lines += [assign(tgt_var, function('custom_target', [tgt.name], tgt_kwargs))]
            processed[tgt.name] = {'inc': None, 'src': None, 'dep': None, 'tgt': tgt_var, 'func': 'custom_target'}
            name_map[tgt.cmake_name] = tgt.name

        # Now generate the target function calls
        for i in self.custom_targets:
            if i.name not in processed:
                process_custom_target(i)
        for i in self.targets:
            if i.name not in processed:
                process_target(i)

        self.generated_targets = processed
        self.internal_name_map = name_map
        return root_cb

    def target_info(self, target: str) -> T.Optional[T.Dict[str, str]]:
        # Try resolving the target name
        # start by checking if there is a 100% match (excluding the name prefix)
        prx_tgt = _sanitize_cmake_name(target)
        if prx_tgt in self.generated_targets:
            return self.generated_targets[prx_tgt]
        # check if there exists a name mapping
        if target in self.internal_name_map:
            target = self.internal_name_map[target]
            assert(target in self.generated_targets)
            return self.generated_targets[target]
        return None

    def target_list(self) -> T.List[str]:
        return list(self.internal_name_map.keys())

    def _object_lib_workaround(self) -> bool:
        return 'link' in self.linkers and self.backend_name.startswith('vs')
