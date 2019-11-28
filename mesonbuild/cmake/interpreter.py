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

from .common import CMakeException
from .client import CMakeClient, RequestCMakeInputs, RequestConfigure, RequestCompute, RequestCodeModel, CMakeTarget
from .executor import CMakeExecutor
from .traceparser import CMakeTraceParser, CMakeGeneratorTarget
from .. import mlog
from ..environment import Environment
from ..mesonlib import MachineChoice
from ..compilers.compilers import lang_suffixes, header_suffixes, obj_suffixes, lib_suffixes, is_header
from subprocess import Popen, PIPE
from typing import Any, List, Dict, Optional, TYPE_CHECKING
from threading import Thread
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


if TYPE_CHECKING:
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

target_type_requires_trace = ['INTERFACE_LIBRARY']

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

# Utility functions to generate local keys
def _target_key(tgt_name: str) -> str:
    return '__tgt_{}__'.format(tgt_name)

def _generated_file_key(fname: str) -> str:
    return '__gen_{}__'.format(os.path.basename(fname))

class ConverterTarget:
    lang_cmake_to_meson = {val.lower(): key for key, val in language_map.items()}
    rm_so_version = re.compile(r'(\.[0-9]+)+$')

    def __init__(self, target: CMakeTarget, env: Environment):
        self.env = env
        self.artifacts = target.artifacts
        self.src_dir = target.src_dir
        self.build_dir = target.build_dir
        self.name = target.name
        self.full_name = target.full_name
        self.type = target.type
        self.install = target.install
        self.install_dir = ''
        self.link_libraries = target.link_libraries
        self.link_flags = target.link_flags + target.link_lang_flags

        if target.install_paths:
            self.install_dir = target.install_paths[0]

        self.languages = []
        self.sources = []
        self.generated = []
        self.includes = []
        self.link_with = []
        self.object_libs = []
        self.compile_opts = {}
        self.public_compile_opts = []
        self.pie = False

        # Project default override options (c_std, cpp_std, etc.)
        self.override_options = []

        for i in target.files:
            # Determine the meson language
            lang = ConverterTarget.lang_cmake_to_meson.get(i.language.lower(), 'c')
            if lang not in self.languages:
                self.languages += [lang]
            if lang not in self.compile_opts:
                self.compile_opts[lang] = []

            # Add arguments, but avoid duplicates
            args = i.flags
            args += ['-D{}'.format(x) for x in i.defines]
            self.compile_opts[lang] += [x for x in args if x not in self.compile_opts[lang]]

            # Handle include directories
            self.includes += [x for x in i.includes if x not in self.includes]

            # Add sources to the right array
            if i.is_generated:
                self.generated += i.sources
            else:
                self.sources += i.sources

    def __repr__(self) -> str:
        return '<{}: {}>'.format(self.__class__.__name__, self.name)

    std_regex = re.compile(r'([-]{1,2}std=|/std:v?|[-]{1,2}std:)(.*)')

    def postprocess(self, output_target_map: dict, root_src_dir: str, subdir: str, install_prefix: str, trace: CMakeTraceParser) -> None:
        # Detect setting the C and C++ standard
        for i in ['c', 'cpp']:
            if i not in self.compile_opts:
                continue

            temp = []
            for j in self.compile_opts[i]:
                m = ConverterTarget.std_regex.match(j)
                if m:
                    self.override_options += ['{}_std={}'.format(i, m.group(2))]
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
        if self.type.upper() in target_type_requires_trace:
            if self.name in trace.targets:
                props = trace.targets[self.name].properties

                self.includes += props.get('INTERFACE_INCLUDE_DIRECTORIES', [])
                self.public_compile_opts += props.get('INTERFACE_COMPILE_DEFINITIONS', [])
                self.public_compile_opts += props.get('INTERFACE_COMPILE_OPTIONS', [])
                self.link_flags += props.get('INTERFACE_LINK_OPTIONS', [])
            else:
                mlog.warning('CMake: Target', mlog.bold(self.name), 'not found in CMake trace. This can lead to build errors')

        # Fix link libraries
        def try_resolve_link_with(path: str) -> Optional[str]:
            basename = os.path.basename(path)
            candidates = [basename, ConverterTarget.rm_so_version.sub('', basename)]
            for i in lib_suffixes:
                if not basename.endswith('.' + i):
                    continue
                new_basename = basename[:-len(i) - 1]
                new_basename = ConverterTarget.rm_so_version.sub('', new_basename)
                new_basename = '{}.{}'.format(new_basename, i)
                candidates += [new_basename]
            for i in candidates:
                if i in output_target_map:
                    return output_target_map[i]
            return None

        temp = []
        for i in self.link_libraries:
            # Let meson handle this arcane magic
            if ',-rpath,' in i:
                continue
            if not os.path.isabs(i):
                link_with = try_resolve_link_with(i)
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
        def rel_path(x: str, is_header: bool, is_generated: bool) -> Optional[str]:
            if not os.path.isabs(x):
                x = os.path.normpath(os.path.join(self.src_dir, x))
            if not os.path.exists(x) and not any([x.endswith(y) for y in obj_suffixes]) and not is_generated:
                mlog.warning('CMake: path', mlog.bold(x), 'does not exist. Ignoring. This can lead to build errors')
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
            key = _generated_file_key(x)
            if key in output_target_map:
                ctgt = output_target_map[key]
                assert(isinstance(ctgt, ConverterCustomTarget))
                ref = ctgt.get_ref(x)
                assert(isinstance(ref, CustomTargetReference) and ref.valid())
                return ref
            return x

        build_dir_rel = os.path.relpath(self.build_dir, os.path.join(self.env.get_build_dir(), subdir))
        self.includes = list(set([rel_path(x, True, False) for x in set(self.includes)] + [build_dir_rel]))
        self.sources = [rel_path(x, False, False) for x in self.sources]
        self.generated = [rel_path(x, False, True) for x in self.generated]

        # Resolve custom targets
        self.generated = [custom_target(x) for x in self.generated]

        # Remove delete entries
        self.includes = [x for x in self.includes if x is not None]
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

    def process_object_libs(self, obj_target_list: List['ConverterTarget']):
        # Try to detect the object library(s) from the generated input sources
        temp = [x for x in self.generated if isinstance(x, str)]
        temp = [os.path.basename(x) for x in temp]
        temp = [x for x in temp if any([x.endswith('.' + y) for y in obj_suffixes])]
        temp = [os.path.splitext(x)[0] for x in temp]
        # Temp now stores the source filenames of the object files
        for i in obj_target_list:
            source_files = [os.path.basename(x) for x in i.sources + i.generated]
            for j in source_files:
                if j in temp:
                    self.object_libs += [i]
                    break

        # Filter out object files from the sources
        self.generated = [x for x in self.generated if not isinstance(x, str) or not any([x.endswith('.' + y) for y in obj_suffixes])]

    def meson_func(self) -> str:
        return target_type_map.get(self.type.upper())

    def log(self) -> None:
        mlog.log('Target', mlog.bold(self.name))
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
        mlog.log('  -- sources:        ', mlog.bold(str(self.sources)))
        mlog.log('  -- generated:      ', mlog.bold(str(self.generated)))
        mlog.log('  -- pie:            ', mlog.bold('true' if self.pie else 'false'))
        mlog.log('  -- override_opts:  ', mlog.bold(str(self.override_options)))
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

    def __init__(self, target: CMakeGeneratorTarget):
        self.name = 'custom_tgt_{}'.format(ConverterCustomTarget.tgt_counter)
        self.original_outputs = list(target.outputs)
        self.outputs = [os.path.basename(x) for x in self.original_outputs]
        self.command = target.command
        self.working_dir = target.working_dir
        self.depends_raw = target.depends
        self.inputs = []
        self.depends = []

        ConverterCustomTarget.tgt_counter += 1

    def __repr__(self) -> str:
        return '<{}: {}>'.format(self.__class__.__name__, self.outputs)

    def postprocess(self, output_target_map: dict, root_src_dir: str, subdir: str, build_dir: str) -> None:
        # Default the working directory to the CMake build dir. This
        # is not 100% correct, since it should be the value of
        # ${CMAKE_CURRENT_BINARY_DIR} when add_custom_command is
        # called. However, keeping track of this variable is not
        # trivial and the current solution should work in most cases.
        if not self.working_dir:
            self.working_dir = build_dir

        # relative paths in the working directory are always relative
        # to ${CMAKE_CURRENT_BINARY_DIR} (see note above)
        if not os.path.isabs(self.working_dir):
            self.working_dir = os.path.normpath(os.path.join(build_dir, self.working_dir))

        # Modify the original outputs if they are relative. Again,
        # relative paths are relative to ${CMAKE_CURRENT_BINARY_DIR}
        # and the first disclaimer is stil in effect
        def ensure_absolute(x: str):
            if os.path.isabs(x):
                return x
            else:
                return os.path.normpath(os.path.join(build_dir, x))
        self.original_outputs = [ensure_absolute(x) for x in self.original_outputs]

        # Check if the command is a build target
        commands = []
        for i in self.command:
            assert(isinstance(i, list))
            cmd = []

            for j in i:
                target_key = _target_key(j)
                if target_key in output_target_map:
                    cmd += [output_target_map[target_key]]
                else:
                    cmd += [j]

            commands += [cmd]
        self.command = commands

        # Check dependencies and input files
        for i in self.depends_raw:
            tgt_key = _target_key(i)
            gen_key = _generated_file_key(i)

            if os.path.basename(i) in output_target_map:
                self.depends += [output_target_map[os.path.basename(i)]]
            elif tgt_key in output_target_map:
                self.depends += [output_target_map[tgt_key]]
            elif gen_key in output_target_map:
                self.inputs += [output_target_map[gen_key].get_ref(i)]
            elif not os.path.isabs(i) and os.path.exists(os.path.join(root_src_dir, i)):
                self.inputs += [i]
            elif os.path.isabs(i) and os.path.exists(i) and os.path.commonpath([i, root_src_dir]) == root_src_dir:
                self.inputs += [os.path.relpath(i, root_src_dir)]

    def get_ref(self, fname: str) -> Optional[CustomTargetReference]:
        try:
            idx = self.outputs.index(os.path.basename(fname))
            return CustomTargetReference(self, idx)
        except ValueError:
            return None

    def log(self) -> None:
        mlog.log('Custom Target', mlog.bold(self.name))
        mlog.log('  -- command:     ', mlog.bold(str(self.command)))
        mlog.log('  -- outputs:     ', mlog.bold(str(self.outputs)))
        mlog.log('  -- working_dir: ', mlog.bold(str(self.working_dir)))
        mlog.log('  -- depends_raw: ', mlog.bold(str(self.depends_raw)))
        mlog.log('  -- inputs:      ', mlog.bold(str(self.inputs)))
        mlog.log('  -- depends:     ', mlog.bold(str(self.depends)))

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
        self.client = CMakeClient(self.env)

        # Raw CMake results
        self.bs_files = []
        self.codemodel = None
        self.raw_trace = None

        # Analysed data
        self.project_name = ''
        self.languages = []
        self.targets = []
        self.custom_targets = []  # type: List[ConverterCustomTarget]
        self.trace = CMakeTraceParser()

        # Generated meson data
        self.generated_targets = {}

    def configure(self, extra_cmake_options: List[str]) -> None:
        for_machine = MachineChoice.HOST # TODO make parameter
        # Find CMake
        cmake_exe = CMakeExecutor(self.env, '>=3.7', for_machine)
        if not cmake_exe.found():
            raise CMakeException('Unable to find CMake')

        generator = backend_generator_map[self.backend_name]
        cmake_args = cmake_exe.get_command()
        trace_args = ['--trace', '--trace-expand', '--no-warn-unused-cli']
        cmcmp_args = ['-DCMAKE_POLICY_WARNING_{}=OFF'.format(x) for x in disable_policy_warnings]

        # Map meson compiler to CMake variables
        for lang, comp in self.env.coredata.compilers[for_machine].items():
            if lang not in language_map:
                continue
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
            mlog.log(mlog.bold('  - disabled policy warnings:'), '[{}]'.format(', '.join(disable_policy_warnings)))
            mlog.log()
            os.makedirs(self.build_dir, exist_ok=True)
            os_env = os.environ.copy()
            os_env['LC_ALL'] = 'C'
            final_command = cmake_args + trace_args + cmcmp_args + [self.src_dir]
            proc = Popen(final_command, stdout=PIPE, stderr=PIPE, cwd=self.build_dir, env=os_env)

            def print_stdout():
                while True:
                    line = proc.stdout.readline()
                    if not line:
                        break
                    mlog.log(line.decode('utf-8').strip('\n'))
                proc.stdout.close()

            t = Thread(target=print_stdout)
            t.start()

            # Read stderr line by line and log non trace lines
            self.raw_trace = ''
            tline_start_reg = re.compile(r'^\s*(.*\.(cmake|txt))\(([0-9]+)\):\s*(\w+)\(.*$')
            inside_multiline_trace = False
            while True:
                line = proc.stderr.readline()
                if not line:
                    break
                line = line.decode('utf-8')
                if tline_start_reg.match(line):
                    self.raw_trace += line
                    inside_multiline_trace = not line.endswith(' )\n')
                elif inside_multiline_trace:
                    self.raw_trace += line
                else:
                    mlog.warning(line.strip('\n'))

            proc.stderr.close()
            proc.wait()

            t.join()

        mlog.log()
        h = mlog.green('SUCCEEDED') if proc.returncode == 0 else mlog.red('FAILED')
        mlog.log('CMake configuration:', h)
        if proc.returncode != 0:
            raise CMakeException('Failed to configure the CMake subproject')

    def initialise(self, extra_cmake_options: List[str]) -> None:
        # Run configure the old way becuse doing it
        # with the server doesn't work for some reason
        self.configure(extra_cmake_options)

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
        self.bs_files = list(set(self.bs_files))
        self.codemodel = cm_reply

    def analyse(self) -> None:
        if self.codemodel is None:
            raise CMakeException('CMakeInterpreter was not initialized')

        # Clear analyser data
        self.project_name = ''
        self.languages = []
        self.targets = []
        self.custom_targets = []
        self.trace = CMakeTraceParser(permissive=True)

        # Parse the trace
        self.trace.parse(self.raw_trace)

        # Find all targets
        for i in self.codemodel.configs:
            for j in i.projects:
                if not self.project_name:
                    self.project_name = j.name
                for k in j.targets:
                    if k.type not in skip_targets:
                        self.targets += [ConverterTarget(k, self.env)]

        for i in self.trace.custom_targets:
            self.custom_targets += [ConverterCustomTarget(i)]

        # generate the output_target_map
        output_target_map = {}
        output_target_map.update({x.full_name: x for x in self.targets})
        output_target_map.update({_target_key(x.name): x for x in self.targets})
        for i in self.targets:
            for j in i.artifacts:
                output_target_map[os.path.basename(j)] = i
        for i in self.custom_targets:
            for j in i.original_outputs:
                output_target_map[_generated_file_key(j)] = i
        object_libs = []

        # First pass: Basic target cleanup
        for i in self.custom_targets:
            i.postprocess(output_target_map, self.src_dir, self.subdir, self.build_dir)
        for i in self.targets:
            i.postprocess(output_target_map, self.src_dir, self.subdir, self.install_prefix, self.trace)
            if i.type == 'OBJECT_LIBRARY':
                object_libs += [i]
            self.languages += [x for x in i.languages if x not in self.languages]

        # Second pass: Detect object library dependencies
        for i in self.targets:
            i.process_object_libs(object_libs)

        mlog.log('CMake project', mlog.bold(self.project_name), 'has', mlog.bold(str(len(self.targets) + len(self.custom_targets))), 'build targets.')

    def pretend_to_be_meson(self) -> CodeBlockNode:
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
                return BooleanNode(token(), value)
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
            args.arguments += [nodeify(x) for x in elements]
            return ArrayNode(args, 0, 0, 0, 0)

        def function(name: str, args=None, kwargs=None) -> FunctionNode:
            if args is None:
                args = []
            if kwargs is None:
                kwargs = {}
            args_n = ArgumentNode(token())
            if not isinstance(args, list):
                args = [args]
            args_n.arguments = [nodeify(x) for x in args]
            args_n.kwargs = {k: nodeify(v) for k, v in kwargs.items()}
            func_n = FunctionNode(self.subdir, 0, 0, 0, 0, name, args_n)
            return func_n

        def method(obj: BaseNode, name: str, args=None, kwargs=None) -> MethodNode:
            if args is None:
                args = []
            if kwargs is None:
                kwargs = {}
            args_n = ArgumentNode(token())
            if not isinstance(args, list):
                args = [args]
            args_n.arguments = [nodeify(x) for x in args]
            args_n.kwargs = {k: nodeify(v) for k, v in kwargs.items()}
            return MethodNode(self.subdir, 0, 0, obj, name, args_n)

        def assign(var_name: str, value: BaseNode) -> AssignmentNode:
            return AssignmentNode(self.subdir, 0, 0, var_name, value)

        # Generate the root code block and the project function call
        root_cb = CodeBlockNode(token())
        root_cb.lines += [function('project', [self.project_name] + self.languages)]

        # Add the run script for custom commands
        run_script = '{}/data/run_ctgt.py'.format(os.path.dirname(os.path.realpath(__file__)))
        run_script_var = 'ctgt_run_script'
        root_cb.lines += [assign(run_script_var, function('find_program', [[run_script]], {'required': True}))]

        # Add the targets
        processed = {}

        def resolve_ctgt_ref(ref: CustomTargetReference) -> BaseNode:
            tgt_var = processed[ref.ctgt.name]['tgt']
            if len(ref.ctgt.outputs) == 1:
                return id_node(tgt_var)
            else:
                return indexed(id_node(tgt_var), ref.index)

        def process_target(tgt: ConverterTarget):
            # First handle inter target dependencies
            link_with = []
            objec_libs = []
            sources = []
            generated = []
            generated_filenames = []
            custom_targets = []
            for i in tgt.link_with:
                assert(isinstance(i, ConverterTarget))
                if i.name not in processed:
                    process_target(i)
                link_with += [id_node(processed[i.name]['tgt'])]
            for i in tgt.object_libs:
                assert(isinstance(i, ConverterTarget))
                if i.name not in processed:
                    process_target(i)
                objec_libs += [processed[i.name]['tgt']]

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
            base_name = str(tgt.name)
            base_name = base_name.replace('-', '_')
            inc_var = '{}_inc'.format(base_name)
            src_var = '{}_src'.format(base_name)
            dep_var = '{}_dep'.format(base_name)
            tgt_var = base_name

            # Generate target kwargs
            tgt_kwargs = {
                'link_args': tgt.link_flags + tgt.link_libraries,
                'link_with': link_with,
                'include_directories': id_node(inc_var),
                'install': tgt.install,
                'install_dir': tgt.install_dir,
                'override_options': tgt.override_options,
                'objects': [method(id_node(x), 'extract_all_objects') for x in objec_libs],
            }

            # Handle compiler args
            for key, val in tgt.compile_opts.items():
                tgt_kwargs['{}_args'.format(key)] = val

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

            # Generate the function nodes
            inc_node = assign(inc_var, function('include_directories', tgt.includes))
            node_list = [inc_node]
            if tgt_func == 'header_only':
                del dep_kwargs['link_with']
                dep_node = assign(dep_var, function('declare_dependency', kwargs=dep_kwargs))
                node_list += [dep_node]
                src_var = ''
                tgt_var = ''
            else:
                src_node = assign(src_var, function('files', sources))
                tgt_node = assign(tgt_var, function(tgt_func, [base_name, [id_node(src_var)] + generated], tgt_kwargs))
                node_list += [src_node, tgt_node]
                if tgt_func in ['static_library', 'shared_library']:
                    dep_node = assign(dep_var, function('declare_dependency', kwargs=dep_kwargs))
                    node_list += [dep_node]
                else:
                    dep_var = ''

            # Add the nodes to the ast
            root_cb.lines += node_list
            processed[tgt.name] = {'inc': inc_var, 'src': src_var, 'dep': dep_var, 'tgt': tgt_var, 'func': tgt_func}

        def process_custom_target(tgt: ConverterCustomTarget) -> None:
            # CMake allows to specify multiple commands in a custom target.
            # To map this to meson, a helper script is used to execute all
            # commands in order. This addtionally allows setting the working
            # directory.

            tgt_var = tgt.name  # type: str

            def resolve_source(x: Any) -> Any:
                if isinstance(x, ConverterTarget):
                    if x.name not in processed:
                        process_target(x)
                    return id_node(x.name)
                elif isinstance(x, CustomTargetReference):
                    if x.ctgt.name not in processed:
                        process_custom_target(x.ctgt)
                    return resolve_ctgt_ref(x)
                else:
                    return x

            # Generate the command list
            command = []
            command += [id_node(run_script_var)]
            command += ['-o', '@OUTPUT@']
            command += ['-O'] + tgt.original_outputs
            command += ['-d', tgt.working_dir]

            # Generate the commands. Subcommands are seperated by ';;;'
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

        # Now generate the target function calls
        for i in self.custom_targets:
            if i.name not in processed:
                process_custom_target(i)
        for i in self.targets:
            if i.name not in processed:
                process_target(i)

        self.generated_targets = processed
        return root_cb

    def target_info(self, target: str) -> Optional[Dict[str, str]]:
        if target in self.generated_targets:
            return self.generated_targets[target]
        return None

    def target_list(self) -> List[str]:
        return list(self.generated_targets.keys())
