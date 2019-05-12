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

from .visitor import AstVisitor
from .. import interpreterbase, mparser, mesonlib
from .. import environment

from ..interpreterbase import InvalidArguments, BreakRequest, ContinueRequest
from ..mparser import (
    ArgumentNode,
    ArithmeticNode,
    ArrayNode,
    AssignmentNode,
    BaseNode,
    ElementaryNode,
    EmptyNode,
    IdNode,
    MethodNode,
    PlusAssignmentNode,
    TernaryNode,
)

import os, sys
from typing import List, Any, Optional

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
    def __init__(self, source_root: str, subdir: str, visitors: Optional[List[AstVisitor]] = None):
        super().__init__(source_root, subdir)
        self.visitors = visitors if visitors is not None else []
        self.visited_subdirs = {}
        self.assignments = {}
        self.assign_vals = {}
        self.reverse_assignment = {}
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
                           'files': self.func_do_nothing,
                           'executable': self.func_do_nothing,
                           'static_library': self.func_do_nothing,
                           'shared_library': self.func_do_nothing,
                           'library': self.func_do_nothing,
                           'build_target': self.func_do_nothing,
                           'custom_target': self.func_do_nothing,
                           'run_target': self.func_do_nothing,
                           'subdir': self.func_subdir,
                           'set_variable': self.func_do_nothing,
                           'get_variable': self.func_do_nothing,
                           'is_variable': self.func_do_nothing,
                           'disabler': self.func_do_nothing,
                           'gettext': self.func_do_nothing,
                           'jar': self.func_do_nothing,
                           'warning': self.func_do_nothing,
                           'shared_module': self.func_do_nothing,
                           'option': self.func_do_nothing,
                           'both_libraries': self.func_do_nothing,
                           'add_test_setup': self.func_do_nothing,
                           'find_library': self.func_do_nothing,
                           'subdir_done': self.func_do_nothing,
                           })

    def func_do_nothing(self, node, args, kwargs):
        return True

    def load_root_meson_file(self):
        super().load_root_meson_file()
        for i in self.visitors:
            self.ast.accept(i)

    def func_subdir(self, node, args, kwargs):
        args = self.flatten_args(args)
        if len(args) != 1 or not isinstance(args[0], str):
            sys.stderr.write('Unable to evaluate subdir({}) in AstInterpreter --> Skipping\n'.format(args))
            return

        prev_subdir = self.subdir
        subdir = os.path.join(prev_subdir, args[0])
        absdir = os.path.join(self.source_root, subdir)
        buildfilename = os.path.join(subdir, environment.build_filename)
        absname = os.path.join(self.source_root, buildfilename)
        symlinkless_dir = os.path.realpath(absdir)
        if symlinkless_dir in self.visited_subdirs:
            sys.stderr.write('Trying to enter {} which has already been visited --> Skipping\n'.format(args[0]))
            return
        self.visited_subdirs[symlinkless_dir] = True

        if not os.path.isfile(absname):
            sys.stderr.write('Unable to find build file {} --> Skipping\n'.format(buildfilename))
            return
        with open(absname, encoding='utf8') as f:
            code = f.read()
        assert(isinstance(code, str))
        try:
            codeblock = mparser.Parser(code, subdir).parse()
        except mesonlib.MesonException as me:
            me.file = buildfilename
            raise me

        self.subdir = subdir
        for i in self.visitors:
            codeblock.accept(i)
        self.evaluate_codeblock(codeblock)
        self.subdir = prev_subdir

    def method_call(self, node):
        return True

    def evaluate_arithmeticstatement(self, cur):
        self.evaluate_statement(cur.left)
        self.evaluate_statement(cur.right)
        return 0

    def evaluate_uminusstatement(self, cur):
        self.evaluate_statement(cur.value)
        return 0

    def evaluate_ternary(self, node):
        assert(isinstance(node, TernaryNode))
        self.evaluate_statement(node.condition)
        self.evaluate_statement(node.trueblock)
        self.evaluate_statement(node.falseblock)

    def evaluate_plusassign(self, node):
        assert(isinstance(node, PlusAssignmentNode))
        if node.var_name not in self.assignments:
            self.assignments[node.var_name] = []
            self.assign_vals[node.var_name] = []
        self.assignments[node.var_name] += [node.value] # Save a reference to the value node
        if hasattr(node.value, 'ast_id'):
            self.reverse_assignment[node.value.ast_id] = node
        self.assign_vals[node.var_name] += [self.evaluate_statement(node.value)]

    def evaluate_indexing(self, node):
        return 0

    def unknown_function_called(self, func_name):
        pass

    def reduce_arguments(self, args):
        if isinstance(args, ArgumentNode):
            if args.incorrect_order():
                raise InvalidArguments('All keyword arguments must be after positional arguments.')
            return self.flatten_args(args.arguments), args.kwargs
        else:
            return self.flatten_args(args), {}

    def evaluate_comparison(self, node):
        self.evaluate_statement(node.left)
        self.evaluate_statement(node.right)
        return False

    def evaluate_andstatement(self, cur):
        self.evaluate_statement(cur.left)
        self.evaluate_statement(cur.right)
        return False

    def evaluate_orstatement(self, cur):
        self.evaluate_statement(cur.left)
        self.evaluate_statement(cur.right)
        return False

    def evaluate_foreach(self, node):
        try:
            self.evaluate_codeblock(node.block)
        except ContinueRequest:
            pass
        except BreakRequest:
            pass

    def evaluate_if(self, node):
        for i in node.ifs:
            self.evaluate_codeblock(i.block)
        if not isinstance(node.elseblock, EmptyNode):
            self.evaluate_codeblock(node.elseblock)

    def get_variable(self, varname):
        return 0

    def assignment(self, node):
        assert(isinstance(node, AssignmentNode))
        self.assignments[node.var_name] = [node.value] # Save a reference to the value node
        if hasattr(node.value, 'ast_id'):
            self.reverse_assignment[node.value.ast_id] = node
        self.assign_vals[node.var_name] = [self.evaluate_statement(node.value)] # Evaluate the value just in case

    def flatten_args(self, args: Any, include_unknown_args: bool = False, id_loop_detect: Optional[List[str]] = None) -> List[str]:
        def quick_resolve(n: BaseNode, loop_detect: Optional[List[str]] = None) -> Any:
            if loop_detect is None:
                loop_detect = []
            if isinstance(n, IdNode):
                if n.value in loop_detect or n.value not in self.assignments:
                    return []
                return quick_resolve(self.assignments[n.value][0], loop_detect = loop_detect + [n.value])
            elif isinstance(n, ElementaryNode):
                return n.value
            else:
                return n

        if id_loop_detect is None:
            id_loop_detect = []
        flattend_args = []

        if isinstance(args, BaseNode):
            assert(hasattr(args, 'ast_id'))
            if args.ast_id in id_loop_detect:
                return [] # Loop detected
            id_loop_detect += [args.ast_id]

        if isinstance(args, ArrayNode):
            args = [x for x in args.args.arguments]

        elif isinstance(args, ArgumentNode):
            args = [x for x in args.arguments]

        elif isinstance(args, ArithmeticNode):
            if args.operation != 'add':
                return [] # Only handle string and array concats
            l = quick_resolve(args.left)
            r = quick_resolve(args.right)
            if isinstance(l, str) and isinstance(r, str):
                args = [l + r] # String concatination detected
            else:
                args = self.flatten_args(l, include_unknown_args, id_loop_detect) + self.flatten_args(r, include_unknown_args, id_loop_detect)

        elif isinstance(args, MethodNode):
            src = quick_resolve(args.source_object)
            margs = self.flatten_args(args.args, include_unknown_args, id_loop_detect)
            try:
                if isinstance(src, str):
                    args = [self.string_method_call(src, args.name, margs)]
                elif isinstance(src, bool):
                    args = [self.bool_method_call(src, args.name, margs)]
                elif isinstance(src, int):
                    args = [self.int_method_call(src, args.name, margs)]
                elif isinstance(src, list):
                    args = [self.array_method_call(src, args.name, margs)]
                elif isinstance(src, dict):
                    args = [self.dict_method_call(src, args.name, margs)]
                else:
                    return []
            except mesonlib.MesonException:
                return []

        # Make sure we are always dealing with lists
        if not isinstance(args, list):
            args = [args]

        # Resolve the contents of args
        for i in args:
            if isinstance(i, IdNode):
                flattend_args += self.flatten_args(quick_resolve(i), include_unknown_args, id_loop_detect)
            elif isinstance(i, (ArrayNode, ArgumentNode, ArithmeticNode, MethodNode)):
                flattend_args += self.flatten_args(i, include_unknown_args, id_loop_detect)
            elif isinstance(i, mparser.ElementaryNode):
                flattend_args += [i.value]
            elif isinstance(i, (str, bool, int, float)):
                flattend_args += [i]
            elif include_unknown_args:
                flattend_args += [i]
        return flattend_args

    def flatten_kwargs(self, kwargs: object, include_unknown_args: bool = False):
        flattend_kwargs = {}
        for key, val in kwargs.items():
            if isinstance(val, ElementaryNode):
                flattend_kwargs[key] = val.value
            elif isinstance(val, (ArrayNode, ArgumentNode)):
                flattend_kwargs[key] = self.flatten_args(val, include_unknown_args)
            elif isinstance(val, (str, bool, int, float)) or include_unknown_args:
                flattend_kwargs[key] = val
        return flattend_kwargs
