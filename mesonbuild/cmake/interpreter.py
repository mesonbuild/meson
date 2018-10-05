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
from .. import mlog
from ..build import Build
from ..environment import Environment
from ..mesonlib import MachineChoice
from ..mparser import Token, BaseNode, CodeBlockNode, FunctionNode, ArrayNode, ArgumentNode, AssignmentNode, BooleanNode, StringNode, IdNode, MethodNode
from ..backend.backends import Backend
from ..compilers.compilers import lang_suffixes, header_suffixes, obj_suffixes
from ..dependencies.base import CMakeDependency, ExternalProgram
from subprocess import Popen, PIPE, STDOUT
from typing import List, Dict, Optional
import os, re

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
}

skip_targets = ['UTILITY']

blacklist_compiler_flags = [
    '/W1', '/W2', '/W3', '/W4', '/Wall',
    '/O1', '/O2', '/Ob', '/Od', '/Og', '/Oi', '/Os', '/Ot', '/Ox', '/Oy', '/Ob0',
    '/RTC1', '/RTCc', '/RTCs', '/RTCu'
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

class ConverterTarget:
    lang_cmake_to_meson = {val.lower(): key for key, val in language_map.items()}

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

    def postprocess(self, output_target_map: dict, root_src_dir: str, subdir: str, install_prefix: str) -> None:
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

        # Fix link libraries
        temp = []
        for i in self.link_libraries:
            # Let meson handle this arcane magic
            if ',-rpath,' in i:
                continue
            if not os.path.isabs(i):
                basename = os.path.basename(i)
                if basename in output_target_map:
                    self.link_with += [output_target_map[basename]]
                    continue

            temp += [i]
        self.link_libraries = temp

        # Make paths relative
        def rel_path(x: str, is_header: bool) -> Optional[str]:
            if not os.path.isabs(x):
                x = os.path.normpath(os.path.join(self.src_dir, x))
            if not os.path.exists(x) and not any([x.endswith(y) for y in obj_suffixes]):
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

        build_dir_rel = os.path.relpath(self.build_dir, os.path.join(self.env.get_build_dir(), subdir))
        self.includes = list(set([rel_path(x, True) for x in set(self.includes)] + [build_dir_rel]))
        self.sources = [rel_path(x, False) for x in self.sources]
        self.generated = [rel_path(x, False) for x in self.generated]

        self.includes = [x for x in self.includes if x is not None]
        self.sources = [x for x in self.sources if x is not None]
        self.generated = [x for x in self.generated if x is not None]

        # Filter out files that are not supported by the language
        supported = list(header_suffixes) + list(obj_suffixes)
        for i in self.languages:
            supported += list(lang_suffixes[i])
        supported = ['.{}'.format(x) for x in supported]
        self.sources = [x for x in self.sources if any([x.endswith(y) for y in supported])]
        self.generated = [x for x in self.generated if any([x.endswith(y) for y in supported])]

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
        temp = [os.path.basename(x) for x in self.generated]
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
        self.generated = [x for x in self.generated if not any([x.endswith('.' + y) for y in obj_suffixes])]

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

class CMakeInterpreter:
    def __init__(self, build: Build, subdir: str, src_dir: str, install_prefix: str, env: Environment, backend: Backend):
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

        # Analysed data
        self.project_name = ''
        self.languages = []
        self.targets = []

        # Generated meson data
        self.generated_targets = {}

    def configure(self, extra_cmake_options: List[str]) -> None:
        for_machine = MachineChoice.HOST # TODO make parameter
        # Find CMake
        cmake_exe, cmake_vers, _ = CMakeDependency.find_cmake_binary(self.env, for_machine)
        if cmake_exe is None or cmake_exe is False:
            raise CMakeException('Unable to find CMake')
        assert(isinstance(cmake_exe, ExternalProgram))
        if not cmake_exe.found():
            raise CMakeException('Unable to find CMake')

        generator = backend_generator_map[self.backend_name]
        cmake_args = cmake_exe.get_command()

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
            mlog.log('Configuring the build directory with', mlog.bold('CMake'), 'version', mlog.cyan(cmake_vers))
            mlog.log(mlog.bold('Running:'), ' '.join(cmake_args))
            mlog.log()
            os.makedirs(self.build_dir, exist_ok=True)
            os_env = os.environ.copy()
            os_env['LC_ALL'] = 'C'
            proc = Popen(cmake_args + [self.src_dir], stdout=PIPE, stderr=STDOUT, cwd=self.build_dir, env=os_env)

            # Print CMake log in realtime
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                mlog.log(line.decode('utf-8').strip('\n'))

            # Wait for CMake to finish
            proc.communicate()

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

        # Find all targets
        for i in self.codemodel.configs:
            for j in i.projects:
                if not self.project_name:
                    self.project_name = j.name
                for k in j.targets:
                    if k.type not in skip_targets:
                        self.targets += [ConverterTarget(k, self.env)]

        output_target_map = {x.full_name: x for x in self.targets}
        for i in self.targets:
            for j in i.artifacts:
                output_target_map[os.path.basename(j)] = i
        object_libs = []

        # First pass: Basic target cleanup
        for i in self.targets:
            i.postprocess(output_target_map, self.src_dir, self.subdir, self.install_prefix)
            if i.type == 'OBJECT_LIBRARY':
                object_libs += [i]
            self.languages += [x for x in i.languages if x not in self.languages]

        # Second pass: Detect object library dependencies
        for i in self.targets:
            i.process_object_libs(object_libs)

        mlog.log('CMake project', mlog.bold(self.project_name), 'has', mlog.bold(str(len(self.targets))), 'build targets.')

    def pretend_to_be_meson(self) -> CodeBlockNode:
        if not self.project_name:
            raise CMakeException('CMakeInterpreter was not analysed')

        def token(tid: str = 'string', val='') -> Token:
            return Token(tid, self.subdir, 0, 0, 0, None, val)

        def string(value: str) -> StringNode:
            return StringNode(token(val=value))

        def id_node(value: str) -> IdNode:
            return IdNode(token(val=value))

        def nodeify(value):
            if isinstance(value, str):
                return string(value)
            elif isinstance(value, bool):
                return BooleanNode(token(), value)
            elif isinstance(value, list):
                return array(value)
            return value

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
        processed = {}

        def process_target(tgt: ConverterTarget):
            # First handle inter target dependencies
            link_with = []
            objec_libs = []
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
                'include_directories': id_node(inc_var),
            }

            # Generate the function nodes
            inc_node = assign(inc_var, function('include_directories', tgt.includes))
            src_node = assign(src_var, function('files', tgt.sources + tgt.generated))
            tgt_node = assign(tgt_var, function(tgt_func, [base_name, id_node(src_var)], tgt_kwargs))
            dep_node = assign(dep_var, function('declare_dependency', kwargs=dep_kwargs))

            # Add the nodes to the ast
            root_cb.lines += [inc_node, src_node, tgt_node, dep_node]
            processed[tgt.name] = {'inc': inc_var, 'src': src_var, 'dep': dep_var, 'tgt': tgt_var, 'func': tgt_func}

        # Now generate the target function calls
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
