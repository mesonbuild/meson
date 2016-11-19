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

from . import interpreterbase, mlog

class MockExecutable(interpreterbase.InterpreterObject):
    pass

class AstInterpreter(interpreterbase.InterpreterBase):
    def __init__(self, source_root, subdir):
        super().__init__(source_root, subdir)
        self.funcs.update({'executable': self.func_executable,
                           })

    def func_executable(self, *args, **kwargs):
        return MockExecutable()

    def dump(self):
        self.load_root_meson_file()
        self.sanity_check_ast()
        self.parse_project()
        self.run()
        print('AST here')

    def unknown_function_called(self, func_name):
        mlog.warning('Unknown function called: ' + func_name)
