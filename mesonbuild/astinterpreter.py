# Copyright 2016 The Meson development team

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

from . import interpreterbase, mlog, mparser, mesonlib
from . import environment

from .interpreterbase import InterpreterException

import os

class DontCareObject(interpreterbase.InterpreterObject):
    pass

class MockExecutable(interpreterbase.InterpreterObject):
    pass

class MockStaticLibrary(interpreterbase.InterpreterObject):
    pass

class MockSharedLibrary(interpreterbase.InterpreterObject):
    pass

class MockCustomTarget(interpreterbase.InterpreterObject):
    pass

class MockRunTarget(interpreterbase.InterpreterObject):
    pass

class AstInterpreter(interpreterbase.InterpreterBase):
    def __init__(self, source_root, subdir):
        super().__init__(source_root, subdir)
        self.funcs.update({'project' : self.func_do_nothing,
                           'test' : self.func_do_nothing,
                           'benchmark' : self.func_do_nothing,
                           'install_headers' : self.func_do_nothing,
                           'install_man' : self.func_do_nothing,
                           'install_data' : self.func_do_nothing,
                           'install_subdir' : self.func_do_nothing,
                           'configuration_data' : self.func_do_nothing,
                           'configure_file' : self.func_do_nothing,
                           'find_program' : self.func_do_nothing,
                           'include_directories' : self.func_do_nothing,
                           'add_global_arguments' : self.func_do_nothing,
                           'add_global_link_arguments' : self.func_do_nothing,
                           'add_project_arguments' : self.func_do_nothing,
                           'add_project_link_arguments' : self.func_do_nothing,
                           'message' : self.func_do_nothing,
                           'generator' : self.func_do_nothing,
                           'error' : self.func_do_nothing,
                           'run_command' : self.func_do_nothing,
                           'assert' : self.func_do_nothing,
                           'subproject' : self.func_do_nothing,
                           'dependency' : self.func_do_nothing,
                           'get_option' : self.func_do_nothing,
                           'join_paths' : self.func_do_nothing,
                           'environment' : self.func_do_nothing,
                           'import' : self.func_do_nothing,
                           'vcs_tag' : self.func_do_nothing,
                           'add_languages' : self.func_do_nothing,
                           'declare_dependency' : self.func_do_nothing,
                           'files' : self.func_files,
                           'executable': self.func_executable,
                           'static_library' : self.func_static_lib,
                           'shared_library' : self.func_shared_lib,
                           'library' : self.func_library,
                           'build_target' : self.func_build_target,
                           'custom_target' : self.func_custom_target,
                           'run_target' : self.func_run_target,
                           'subdir' : self.func_subdir,
                           'set_variable' : self.func_set_variable,
                           'get_variable' : self.func_get_variable,
                           'is_variable' : self.func_is_variable,
                           })

    def func_do_nothing(self, *args, **kwargs):
        return True

    def method_call(self, node):
        return True

    def func_executable(self, *args, **kwargs):
        return MockExecutable()

    def func_static_lib(self, *args, **kwargs):
        return MockStaticLibrary()

    def func_shared_lib(self, *args, **kwargs):
        return MockSharedLibrary()

    def func_library(self, *args, **kwargs):
        return self.func_shared_lib(*args, **kwargs)

    def func_custom_target(self, *args, **kwargs):
        return MockCustomTarget()

    def func_run_target(self, *args, **kwargs):
        return MockRunTarget()

    def func_subdir(self, node, args, kwargs):
        prev_subdir = self.subdir
        subdir = os.path.join(prev_subdir, args[0])
        self.subdir = subdir
        buildfilename = os.path.join(self.subdir, environment.build_filename)
        absname = os.path.join(self.source_root, buildfilename)
        if not os.path.isfile(absname):
            self.subdir = prev_subdir
            raise InterpreterException('Nonexistant build def file %s.' % buildfilename)
        with open(absname, encoding='utf8') as f:
            code = f.read()
        assert(isinstance(code, str))
        try:
            codeblock = mparser.Parser(code).parse()
        except mesonlib.MesonException as me:
            me.file = buildfilename
            raise me
        self.evaluate_codeblock(codeblock)
        self.subdir = prev_subdir

    def func_files(self, node, args, kwargs):
        if not isinstance(args, list):
            return [args]
        return args

    def evaluate_arithmeticstatement(self, cur):
        return 0

    def evaluate_plusassign(self, node):
        return 0

    def evaluate_indexing(self, node):
        return 0

    def dump(self):
        self.load_root_meson_file()
        self.sanity_check_ast()
        self.parse_project()
        self.run()
        print('AST here')

    def unknown_function_called(self, func_name):
        mlog.warning('Unknown function called: ' + func_name)
