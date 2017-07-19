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

from .interpreterbase import InterpreterException, InvalidArguments

import os, sys

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

ADD_SOURCE = 0
REMOVE_SOURCE = 1

class AstInterpreter(interpreterbase.InterpreterBase):
    def __init__(self, source_root, subdir):
        super().__init__(source_root, subdir)
        self.asts = {}
        self.funcs.update({'project': self.func_do_nothing,
                           'test': self.func_do_nothing,
                           'benchmark': self.func_do_nothing,
                           'install_headers': self.func_do_nothing,
                           'install_man': self.func_do_nothing,
                           'install_data': self.func_do_nothing,
                           'install_subdir': self.func_do_nothing,
                           'configuration_data': self.func_do_nothing,
                           'configure_file': self.func_do_nothing,
                           'find_program': self.func_do_nothing,
                           'include_directories': self.func_do_nothing,
                           'add_global_arguments': self.func_do_nothing,
                           'add_global_link_arguments': self.func_do_nothing,
                           'add_project_arguments': self.func_do_nothing,
                           'add_project_link_arguments': self.func_do_nothing,
                           'message': self.func_do_nothing,
                           'generator': self.func_do_nothing,
                           'error': self.func_do_nothing,
                           'run_command': self.func_do_nothing,
                           'assert': self.func_do_nothing,
                           'subproject': self.func_do_nothing,
                           'dependency': self.func_do_nothing,
                           'get_option': self.func_do_nothing,
                           'join_paths': self.func_do_nothing,
                           'environment': self.func_do_nothing,
                           'import': self.func_do_nothing,
                           'vcs_tag': self.func_do_nothing,
                           'add_languages': self.func_do_nothing,
                           'declare_dependency': self.func_do_nothing,
                           'files': self.func_files,
                           'executable': self.func_executable,
                           'static_library': self.func_static_lib,
                           'shared_library': self.func_shared_lib,
                           'library': self.func_library,
                           'build_target': self.func_build_target,
                           'custom_target': self.func_custom_target,
                           'run_target': self.func_run_target,
                           'subdir': self.func_subdir,
                           'set_variable': self.func_set_variable,
                           'get_variable': self.func_get_variable,
                           'is_variable': self.func_is_variable,
                           })

    def func_do_nothing(self, node, args, kwargs):
        return True

    def method_call(self, node):
        return True

    def func_executable(self, node, args, kwargs):
        if args[0] == self.targetname:
            if self.operation == ADD_SOURCE:
                self.add_source_to_target(node, args, kwargs)
            elif self.operation == REMOVE_SOURCE:
                self.remove_source_from_target(node, args, kwargs)
            else:
                raise NotImplementedError('Bleep bloop')
        return MockExecutable()

    def func_static_lib(self, node, args, kwargs):
        return MockStaticLibrary()

    def func_shared_lib(self, node, args, kwargs):
        return MockSharedLibrary()

    def func_library(self, node, args, kwargs):
        return self.func_shared_lib(node, args, kwargs)

    def func_custom_target(self, node, args, kwargs):
        return MockCustomTarget()

    def func_run_target(self, node, args, kwargs):
        return MockRunTarget()

    def func_subdir(self, node, args, kwargs):
        prev_subdir = self.subdir
        subdir = os.path.join(prev_subdir, args[0])
        self.subdir = subdir
        buildfilename = os.path.join(self.subdir, environment.build_filename)
        absname = os.path.join(self.source_root, buildfilename)
        if not os.path.isfile(absname):
            self.subdir = prev_subdir
            raise InterpreterException('Nonexistent build def file %s.' % buildfilename)
        with open(absname, encoding='utf8') as f:
            code = f.read()
        assert(isinstance(code, str))
        try:
            codeblock = mparser.Parser(code, self.subdir).parse()
            self.asts[subdir] = codeblock
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

    def reduce_arguments(self, args):
        assert(isinstance(args, mparser.ArgumentNode))
        if args.incorrect_order():
            raise InvalidArguments('All keyword arguments must be after positional arguments.')
        return args.arguments, args.kwargs

    def transform(self):
        self.load_root_meson_file()
        self.asts[''] = self.ast
        self.sanity_check_ast()
        self.parse_project()
        self.run()

    def add_source(self, targetname, filename):
        self.operation = ADD_SOURCE
        self.targetname = targetname
        self.filename = filename
        self.transform()

    def remove_source(self, targetname, filename):
        self.operation = REMOVE_SOURCE
        self.targetname = targetname
        self.filename = filename
        self.transform()

    def unknown_function_called(self, func_name):
        mlog.warning('Unknown function called: ' + func_name)

    def add_source_to_target(self, node, args, kwargs):
        namespan = node.args.arguments[0].bytespan
        buildfilename = os.path.join(self.source_root, self.subdir, environment.build_filename)
        raw_data = open(buildfilename, 'r').read()
        updated = raw_data[0:namespan[1]] + (", '%s'" % self.filename) + raw_data[namespan[1]:]
        open(buildfilename, 'w').write(updated)
        sys.exit(0)

    def remove_argument_item(self, args, i):
        assert(isinstance(args, mparser.ArgumentNode))
        namespan = args.arguments[i].bytespan
        # Usually remove the comma after this item but if it is
        # the last argument, we need to remove the one before.
        if i >= len(args.commas):
            i -= 1
        if i < 0:
            commaspan = (0, 0) # Removed every entry in the list.
        else:
            commaspan = args.commas[i].bytespan
        if commaspan[0] < namespan[0]:
            commaspan, namespan = namespan, commaspan
        buildfilename = os.path.join(self.source_root, args.subdir, environment.build_filename)
        raw_data = open(buildfilename, 'r').read()
        intermediary = raw_data[0:commaspan[0]] + raw_data[commaspan[1]:]
        updated = intermediary[0:namespan[0]] + intermediary[namespan[1]:]
        open(buildfilename, 'w').write(updated)
        sys.exit(0)

    def hacky_find_and_remove(self, node_to_remove):
        for a in self.asts[node_to_remove.subdir].lines:
            if a.lineno == node_to_remove.lineno:
                if isinstance(a, mparser.AssignmentNode):
                    v = a.value
                    if not isinstance(v, mparser.ArrayNode):
                        raise NotImplementedError('Not supported yet, bro.')
                    args = v.args
                    for i in range(len(args.arguments)):
                        if isinstance(args.arguments[i], mparser.StringNode) and self.filename == args.arguments[i].value:
                            self.remove_argument_item(args, i)
                raise NotImplementedError('Sukkess')

    def remove_source_from_target(self, node, args, kwargs):
        for i in range(1, len(node.args)):
            # Is file name directly in function call as a string.
            if isinstance(node.args.arguments[i], mparser.StringNode) and self.filename == node.args.arguments[i].value:
                self.remove_argument_item(node.args, i)
            # Is file name in a variable that gets expanded here.
            if isinstance(node.args.arguments[i], mparser.IdNode):
                avar = self.get_variable(node.args.arguments[i].value)
                if not isinstance(avar, list):
                    raise NotImplementedError('Non-arrays not supported yet, sorry.')
                for entry in avar:
                    if isinstance(entry, mparser.StringNode) and entry.value == self.filename:
                        self.hacky_find_and_remove(entry)
        sys.exit('Could not find source %s in target %s.' % (self.filename, args[0]))
