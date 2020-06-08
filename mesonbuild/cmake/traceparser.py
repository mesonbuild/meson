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
from .generator import parse_generator_expressions
from .. import mlog
from ..mesonlib import version_compare

import typing as T
from pathlib import Path
import re
import os
import json
import textwrap

class CMakeTraceLine:
    def __init__(self, file, line, func, args):
        self.file = file
        self.line = line
        self.func = func.lower()
        self.args = args

    def __repr__(self):
        s = 'CMake TRACE: {0}:{1} {2}({3})'
        return s.format(self.file, self.line, self.func, self.args)

class CMakeTarget:
    def __init__(self, name, target_type, properties=None, imported: bool = False, tline: T.Optional[CMakeTraceLine] = None):
        if properties is None:
            properties = {}
        self.name = name
        self.type = target_type
        self.properties = properties
        self.imported = imported
        self.tline = tline
        self.depends = []
        self.current_bin_dir = None
        self.current_src_dir = None

    def __repr__(self):
        s = 'CMake TARGET:\n  -- name:      {}\n  -- type:      {}\n  -- imported:  {}\n  -- properties: {{\n{}     }}\n  -- tline: {}'
        propSTR = ''
        for i in self.properties:
            propSTR += "      '{}': {}\n".format(i, self.properties[i])
        return s.format(self.name, self.type, self.imported, propSTR, self.tline)

    def strip_properties(self) -> None:
        # Strip the strings in the properties
        if not self.properties:
            return
        for key, val in self.properties.items():
            self.properties[key] = [x.strip() for x in val]
            assert all([';' not in x for x in self.properties[key]])

class CMakeGeneratorTarget(CMakeTarget):
    def __init__(self, name):
        super().__init__(name, 'CUSTOM', {})
        self.outputs = []        # type: T.List[str]
        self.command = []        # type: T.List[T.List[str]]
        self.working_dir = None  # type: T.Optional[str]

class CMakeTraceParser:
    def __init__(self, cmake_version: str, build_dir: str, permissive: bool = False):
        self.vars = {}     # type: T.Dict[str, T.List[str]]
        self.targets = {}  # type: T.Dict[str, CMakeTarget]

        self.explicit_headers = set()  # type: T.Set[Path]

        # T.List of targes that were added with add_custom_command to generate files
        self.custom_targets = []  # type: T.List[CMakeGeneratorTarget]

        self.permissive = permissive  # type: bool
        self.cmake_version = cmake_version  # type: str
        self.trace_file = 'cmake_trace.txt'
        self.trace_file_path = Path(build_dir) / self.trace_file
        self.trace_format = 'json-v1' if version_compare(cmake_version, '>=3.17') else 'human'

        # State for delayed command execution. Delayed command execution is realised
        # with a custom CMake file that overrides some functions and adds some
        # introspection information to the trace.
        self.delayed_commands = []  # type: T.List[str]
        self.stored_commands = []   # type: T.List[CMakeTraceLine]

        # All supported functions
        self.functions = {
            'set': self._cmake_set,
            'unset': self._cmake_unset,
            'add_executable': self._cmake_add_executable,
            'add_library': self._cmake_add_library,
            'add_custom_command': self._cmake_add_custom_command,
            'add_custom_target': self._cmake_add_custom_target,
            'set_property': self._cmake_set_property,
            'set_target_properties': self._cmake_set_target_properties,
            'target_compile_definitions': self._cmake_target_compile_definitions,
            'target_compile_options': self._cmake_target_compile_options,
            'target_include_directories': self._cmake_target_include_directories,
            'target_link_libraries': self._cmake_target_link_libraries,
            'target_link_options': self._cmake_target_link_options,
            'add_dependencies': self._cmake_add_dependencies,

            # Special functions defined in the preload script.
            # These functions do nothing in the CMake code, but have special
            # meaning here in the trace parser.
            'meson_ps_execute_delayed_calls': self._meson_ps_execute_delayed_calls,
            'meson_ps_reload_vars': self._meson_ps_reload_vars,
        }

    def trace_args(self) -> T.List[str]:
        arg_map = {
            'human': ['--trace', '--trace-expand'],
            'json-v1': ['--trace-expand', '--trace-format=json-v1'],
        }

        base_args = ['--no-warn-unused-cli']
        if not self.requires_stderr():
            base_args += ['--trace-redirect={}'.format(self.trace_file)]

        return arg_map[self.trace_format] + base_args

    def requires_stderr(self) -> bool:
        return version_compare(self.cmake_version, '<3.16')

    def parse(self, trace: T.Optional[str] = None) -> None:
        # First load the trace (if required)
        if not self.requires_stderr():
            if not self.trace_file_path.exists and not self.trace_file_path.is_file():
                raise CMakeException('CMake: Trace file "{}" not found'.format(str(self.trace_file_path)))
            trace = self.trace_file_path.read_text(errors='ignore')
        if not trace:
            raise CMakeException('CMake: The CMake trace was not provided or is empty')

        # Second parse the trace
        lexer1 = None
        if self.trace_format == 'human':
            lexer1 = self._lex_trace_human(trace)
        elif self.trace_format == 'json-v1':
            lexer1 = self._lex_trace_json(trace)
        else:
            raise CMakeException('CMake: Internal error: Invalid trace format {}. Expected [human, json-v1]'.format(self.trace_format))

        # Primary pass -- parse everything
        for l in lexer1:
            # store the function if its execution should be delayed
            if l.func in self.delayed_commands:
                self.stored_commands += [l]
                continue

            # "Execute" the CMake function if supported
            fn = self.functions.get(l.func, None)
            if(fn):
                fn(l)

        # Postprocess
        for tgt in self.targets.values():
            tgt.strip_properties()

    def get_first_cmake_var_of(self, var_list: T.List[str]) -> T.List[str]:
        # Return the first found CMake variable in list var_list
        for i in var_list:
            if i in self.vars:
                return self.vars[i]

        return []

    def get_cmake_var(self, var: str) -> T.List[str]:
        # Return the value of the CMake variable var or an empty list if var does not exist
        if var in self.vars:
            return self.vars[var]

        return []

    def var_to_str(self, var: str) -> T.Optional[str]:
        if var in self.vars and self.vars[var]:
            return self.vars[var][0]

        return None

    def _str_to_bool(self, expr: T.Union[str, T.List[str]]) -> bool:
        if not expr:
            return False
        if isinstance(expr, list):
            expr_str = expr[0]
        else:
            expr_str = expr
        expr_str = expr_str.upper()
        return expr_str not in ['0', 'OFF', 'NO', 'FALSE', 'N', 'IGNORE'] and not expr_str.endswith('NOTFOUND')

    def var_to_bool(self, var: str) -> bool:
        return self._str_to_bool(self.vars.get(var, []))

    def _gen_exception(self, function: str, error: str, tline: CMakeTraceLine) -> None:
        # Generate an exception if the parser is not in permissive mode

        if self.permissive:
            mlog.debug('CMake trace warning: {}() {}\n{}'.format(function, error, tline))
            return None
        raise CMakeException('CMake: {}() {}\n{}'.format(function, error, tline))

    def _cmake_set(self, tline: CMakeTraceLine) -> None:
        """Handler for the CMake set() function in all variaties.

        comes in three flavors:
        set(<var> <value> [PARENT_SCOPE])
        set(<var> <value> CACHE <type> <docstring> [FORCE])
        set(ENV{<var>} <value>)

        We don't support the ENV variant, and any uses of it will be ignored
        silently. the other two variates are supported, with some caveats:
        - we don't properly handle scoping, so calls to set() inside a
          function without PARENT_SCOPE set could incorrectly shadow the
          outer scope.
        - We don't honor the type of CACHE arguments
        """
        # DOC: https://cmake.org/cmake/help/latest/command/set.html

        # 1st remove PARENT_SCOPE and CACHE from args
        args = []
        for i in tline.args:
            if not i or i == 'PARENT_SCOPE':
                continue

            # Discard everything after the CACHE keyword
            if i == 'CACHE':
                break

            args.append(i)

        if len(args) < 1:
            return self._gen_exception('set', 'requires at least one argument', tline)

        # Now that we've removed extra arguments all that should be left is the
        # variable identifier and the value, join the value back together to
        # ensure spaces in the value are correctly handled. This assumes that
        # variable names don't have spaces. Please don't do that...
        identifier = args.pop(0)
        value = ' '.join(args)

        if not value:
            # Same as unset
            if identifier in self.vars:
                del self.vars[identifier]
        else:
            self.vars[identifier] = value.split(';')

    def _cmake_unset(self, tline: CMakeTraceLine):
        # DOC: https://cmake.org/cmake/help/latest/command/unset.html
        if len(tline.args) < 1:
            return self._gen_exception('unset', 'requires at least one argument', tline)

        if tline.args[0] in self.vars:
            del self.vars[tline.args[0]]

    def _cmake_add_executable(self, tline: CMakeTraceLine):
        # DOC: https://cmake.org/cmake/help/latest/command/add_executable.html
        args = list(tline.args) # Make a working copy

        # Make sure the exe is imported
        if 'IMPORTED' not in args:
            return self._gen_exception('add_executable', 'non imported executables are not supported', tline)

        args.remove('IMPORTED')

        if len(args) < 1:
            return self._gen_exception('add_executable', 'requires at least 1 argument', tline)

        self.targets[args[0]] = CMakeTarget(args[0], 'EXECUTABLE', {})

    def _cmake_add_library(self, tline: CMakeTraceLine):
        # DOC: https://cmake.org/cmake/help/latest/command/add_library.html
        args = list(tline.args) # Make a working copy

        # Make sure the lib is imported
        if 'INTERFACE' in args:
            args.remove('INTERFACE')

            if len(args) < 1:
                return self._gen_exception('add_library', 'interface library name not specified', tline)

            self.targets[args[0]] = CMakeTarget(args[0], 'INTERFACE', {}, tline=tline, imported='IMPORTED' in args)
        elif 'IMPORTED' in args:
            args.remove('IMPORTED')

            # Now, only look at the first two arguments (target_name and target_type) and ignore the rest
            if len(args) < 2:
                return self._gen_exception('add_library', 'requires at least 2 arguments', tline)

            self.targets[args[0]] = CMakeTarget(args[0], args[1], {}, tline=tline, imported=True)
        elif 'ALIAS' in args:
            args.remove('ALIAS')

            # Now, only look at the first two arguments (target_name and target_ref) and ignore the rest
            if len(args) < 2:
                return self._gen_exception('add_library', 'requires at least 2 arguments', tline)

            # Simulate the ALIAS with INTERFACE_LINK_LIBRARIES
            self.targets[args[0]] = CMakeTarget(args[0], 'ALIAS', {'INTERFACE_LINK_LIBRARIES': [args[1]]}, tline=tline)
        elif 'OBJECT' in args:
            return self._gen_exception('add_library', 'OBJECT libraries are not supported', tline)
        else:
            self.targets[args[0]] = CMakeTarget(args[0], 'NORMAL', {}, tline=tline)

    def _cmake_add_custom_command(self, tline: CMakeTraceLine, name=None):
        # DOC: https://cmake.org/cmake/help/latest/command/add_custom_command.html
        args = self._flatten_args(list(tline.args))  # Commands can be passed as ';' seperated lists

        if not args:
            return self._gen_exception('add_custom_command', 'requires at least 1 argument', tline)

        # Skip the second function signature
        if args[0] == 'TARGET':
            return self._gen_exception('add_custom_command', 'TARGET syntax is currently not supported', tline)

        magic_keys = ['OUTPUT', 'COMMAND', 'MAIN_DEPENDENCY', 'DEPENDS', 'BYPRODUCTS',
                      'IMPLICIT_DEPENDS', 'WORKING_DIRECTORY', 'COMMENT', 'DEPFILE',
                      'JOB_POOL', 'VERBATIM', 'APPEND', 'USES_TERMINAL', 'COMMAND_EXPAND_LISTS']

        target = CMakeGeneratorTarget(name)

        def handle_output(key: str, target: CMakeGeneratorTarget) -> None:
            target.outputs += [key]

        def handle_command(key: str, target: CMakeGeneratorTarget) -> None:
            if key == 'ARGS':
                return
            target.command[-1] += [key]

        def handle_depends(key: str, target: CMakeGeneratorTarget) -> None:
            target.depends += [key]

        def handle_working_dir(key: str, target: CMakeGeneratorTarget) -> None:
            if target.working_dir is None:
                target.working_dir = key
            else:
                target.working_dir += ' '
                target.working_dir += key

        fn = None

        for i in args:
            if i in magic_keys:
                if i == 'OUTPUT':
                    fn = handle_output
                elif i == 'DEPENDS':
                    fn = handle_depends
                elif i == 'WORKING_DIRECTORY':
                    fn = handle_working_dir
                elif i == 'COMMAND':
                    fn = handle_command
                    target.command += [[]]
                else:
                    fn = None
                continue

            if fn is not None:
                fn(i, target)

        target.current_bin_dir = self.var_to_str('MESON_PS_CMAKE_CURRENT_BINARY_DIR')
        target.current_src_dir = self.var_to_str('MESON_PS_CMAKE_CURRENT_SOURCE_DIR')
        target.outputs = self._guess_files(target.outputs)
        target.depends = self._guess_files(target.depends)
        target.command = [self._guess_files(x) for x in target.command]

        self.custom_targets += [target]
        if name:
            self.targets[name] = target

    def _cmake_add_custom_target(self, tline: CMakeTraceLine):
        # DOC: https://cmake.org/cmake/help/latest/command/add_custom_target.html
        # We only the first parameter (the target name) is interesting
        if len(tline.args) < 1:
            return self._gen_exception('add_custom_target', 'requires at least one argument', tline)

        # It's pretty much the same as a custom command
        self._cmake_add_custom_command(tline, tline.args[0])

    def _cmake_set_property(self, tline: CMakeTraceLine) -> None:
        # DOC: https://cmake.org/cmake/help/latest/command/set_property.html
        args = list(tline.args)

        scope = args.pop(0)

        append = False
        targets = []
        while args:
            curr = args.pop(0)
            # XXX: APPEND_STRING is specifically *not* supposed to create a
            # list, is treating them as aliases really okay?
            if curr == 'APPEND' or curr == 'APPEND_STRING':
                append = True
                continue

            if curr == 'PROPERTY':
                break

            targets += curr.split(';')

        if not args:
            return self._gen_exception('set_property', 'faild to parse argument list', tline)

        if len(args) == 1:
            # Tries to set property to nothing so nothing has to be done
            return

        identifier = args.pop(0)
        if self.trace_format == 'human':
            value = ' '.join(args).split(';')
        else:
            value = [y for x in args for y in x.split(';')]
        if not value:
            return

        def do_target(tgt: str) -> None:
            if i not in self.targets:
                return self._gen_exception('set_property', 'TARGET {} not found'.format(i), tline)

            if identifier not in self.targets[i].properties:
                self.targets[i].properties[identifier] = []

            if append:
                self.targets[i].properties[identifier] += value
            else:
                self.targets[i].properties[identifier] = value

        def do_source(src: str) -> None:
            if identifier != 'HEADER_FILE_ONLY' or not self._str_to_bool(value):
                return

            current_src_dir = self.var_to_str('MESON_PS_CMAKE_CURRENT_SOURCE_DIR')
            if not current_src_dir:
                mlog.warning(textwrap.dedent('''\
                    CMake trace: set_property(SOURCE) called before the preload script was loaded.
                    Unable to determine CMAKE_CURRENT_SOURCE_DIR. This can lead to build errors.
                '''))
                current_src_dir = '.'

            cur_p = Path(current_src_dir)
            src_p = Path(src)

            if not src_p.is_absolute():
                src_p = cur_p / src_p
            self.explicit_headers.add(src_p)

        if scope == 'TARGET':
            for i in targets:
                do_target(i)
        elif scope == 'SOURCE':
            files = self._guess_files(targets)
            for i in files:
                do_source(i)

    def _cmake_set_target_properties(self, tline: CMakeTraceLine) -> None:
        # DOC: https://cmake.org/cmake/help/latest/command/set_target_properties.html
        args = list(tline.args)

        targets = []
        while args:
            curr = args.pop(0)
            if curr == 'PROPERTIES':
                break

            targets.append(curr)

        # Now we need to try to reconsitute the original quoted format of the
        # arguments, as a property value could have spaces in it. Unlike
        # set_property() this is not context free. There are two approaches I
        # can think of, both have drawbacks:
        #
        #   1. Assume that the property will be capitalized ([A-Z_]), this is
        #      convention but cmake doesn't require it.
        #   2. Maintain a copy of the list here: https://cmake.org/cmake/help/latest/manual/cmake-properties.7.html#target-properties
        #
        # Neither of these is awesome for obvious reasons. I'm going to try
        # option 1 first and fall back to 2, as 1 requires less code and less
        # synchroniztion for cmake changes.
        #
        # With the JSON output format, introduced in CMake 3.17, spaces are
        # handled properly and we don't have to do either options

        arglist = []  # type: T.List[T.Tuple[str, T.List[str]]]
        if self.trace_format == 'human':
            name = args.pop(0)
            values = []
            prop_regex = re.compile(r'^[A-Z_]+$')
            for a in args:
                if prop_regex.match(a):
                    if values:
                        arglist.append((name, ' '.join(values).split(';')))
                    name = a
                    values = []
                else:
                    values.append(a)
            if values:
                arglist.append((name, ' '.join(values).split(';')))
        else:
            arglist = [(x[0], x[1].split(';')) for x in zip(args[::2], args[1::2])]

        for name, value in arglist:
            for i in targets:
                if i not in self.targets:
                    return self._gen_exception('set_target_properties', 'TARGET {} not found'.format(i), tline)

                self.targets[i].properties[name] = value

    def _cmake_add_dependencies(self, tline: CMakeTraceLine) -> None:
        # DOC: https://cmake.org/cmake/help/latest/command/add_dependencies.html
        args = list(tline.args)

        if len(args) < 2:
            return self._gen_exception('add_dependencies', 'takes at least 2 arguments', tline)

        target = self.targets.get(args[0])
        if not target:
            return self._gen_exception('add_dependencies', 'target not found', tline)

        for i in args[1:]:
            target.depends += i.split(';')

    def _cmake_target_compile_definitions(self, tline: CMakeTraceLine) -> None:
        # DOC: https://cmake.org/cmake/help/latest/command/target_compile_definitions.html
        self._parse_common_target_options('target_compile_definitions', 'COMPILE_DEFINITIONS', 'INTERFACE_COMPILE_DEFINITIONS', tline)

    def _cmake_target_compile_options(self, tline: CMakeTraceLine) -> None:
        # DOC: https://cmake.org/cmake/help/latest/command/target_compile_options.html
        self._parse_common_target_options('target_compile_options', 'COMPILE_OPTIONS', 'INTERFACE_COMPILE_OPTIONS', tline)

    def _cmake_target_include_directories(self, tline: CMakeTraceLine) -> None:
        # DOC: https://cmake.org/cmake/help/latest/command/target_include_directories.html
        self._parse_common_target_options('target_include_directories', 'INCLUDE_DIRECTORIES', 'INTERFACE_INCLUDE_DIRECTORIES', tline, ignore=['SYSTEM', 'BEFORE'], paths=True)

    def _cmake_target_link_options(self, tline: CMakeTraceLine) -> None:
        # DOC: https://cmake.org/cmake/help/latest/command/target_link_options.html
        self._parse_common_target_options('target_link_options', 'LINK_OPTIONS', 'INTERFACE_LINK_OPTIONS', tline)

    def _cmake_target_link_libraries(self, tline: CMakeTraceLine) -> None:
        # DOC: https://cmake.org/cmake/help/latest/command/target_link_libraries.html
        self._parse_common_target_options('target_link_options', 'LINK_LIBRARIES', 'INTERFACE_LINK_LIBRARIES', tline)

    def _parse_common_target_options(self, func: str, private_prop: str, interface_prop: str, tline: CMakeTraceLine, ignore: T.Optional[T.List[str]] = None, paths: bool = False):
        if ignore is None:
            ignore = ['BEFORE']

        args = list(tline.args)

        if len(args) < 1:
            return self._gen_exception(func, 'requires at least one argument', tline)

        target = args[0]
        if target not in self.targets:
            return self._gen_exception(func, 'TARGET {} not found'.format(target), tline)

        interface = []
        private = []

        mode = 'PUBLIC'
        for i in args[1:]:
            if i in ignore:
                continue

            if i in ['INTERFACE', 'LINK_INTERFACE_LIBRARIES', 'PUBLIC', 'PRIVATE', 'LINK_PUBLIC', 'LINK_PRIVATE']:
                mode = i
                continue

            if mode in ['INTERFACE', 'LINK_INTERFACE_LIBRARIES', 'PUBLIC', 'LINK_PUBLIC']:
                interface += i.split(';')

            if mode in ['PUBLIC', 'PRIVATE', 'LINK_PRIVATE']:
                private += i.split(';')

        if paths:
            interface = self._guess_files(interface)
            private = self._guess_files(private)

        interface = [x for x in interface if x]
        private = [x for x in private if x]

        for i in [(private_prop, private), (interface_prop, interface)]:
            if not i[0] in self.targets[target].properties:
                self.targets[target].properties[i[0]] = []

            self.targets[target].properties[i[0]] += i[1]

    def _meson_ps_execute_delayed_calls(self, tline: CMakeTraceLine) -> None:
        for l in self.stored_commands:
            fn = self.functions.get(l.func, None)
            if(fn):
                fn(l)

        # clear the stored commands
        self.stored_commands = []

    def _meson_ps_reload_vars(self, tline: CMakeTraceLine) -> None:
        self.delayed_commands = self.get_cmake_var('MESON_PS_DELAYED_CALLS')

    def _lex_trace_human(self, trace):
        # The trace format is: '<file>(<line>):  <func>(<args -- can contain \n> )\n'
        reg_tline = re.compile(r'\s*(.*\.(cmake|txt))\(([0-9]+)\):\s*(\w+)\(([\s\S]*?) ?\)\s*\n', re.MULTILINE)
        reg_other = re.compile(r'[^\n]*\n')
        loc = 0
        while loc < len(trace):
            mo_file_line = reg_tline.match(trace, loc)
            if not mo_file_line:
                skip_match = reg_other.match(trace, loc)
                if not skip_match:
                    print(trace[loc:])
                    raise CMakeException('Failed to parse CMake trace')

                loc = skip_match.end()
                continue

            loc = mo_file_line.end()

            file = mo_file_line.group(1)
            line = mo_file_line.group(3)
            func = mo_file_line.group(4)
            args = mo_file_line.group(5)
            args = parse_generator_expressions(args)
            args = args.split(' ')
            args = list(map(lambda x: x.strip(), args))

            yield CMakeTraceLine(file, line, func, args)

    def _lex_trace_json(self, trace: str):
        lines = trace.splitlines(keepends=False)
        lines.pop(0)  # The first line is the version
        for i in lines:
            data = json.loads(i)
            args = data['args']
            args = [parse_generator_expressions(x) for x in args]
            yield CMakeTraceLine(data['file'], data['line'], data['cmd'], args)

    def _flatten_args(self, args: T.List[str]) -> T.List[str]:
        # Split lists in arguments
        res = []  # type: T.List[str]
        for i in args:
            res += i.split(';')
        return res

    def _guess_files(self, broken_list: T.List[str]) -> T.List[str]:
        # Nothing has to be done for newer formats
        if self.trace_format != 'human':
            return broken_list

        # Try joining file paths that contain spaces

        reg_start = re.compile(r'^([A-Za-z]:)?/(.*/)*[^./]+$')
        reg_end = re.compile(r'^.*\.[a-zA-Z]+$')

        fixed_list = []  # type: T.List[str]
        curr_str = None  # type: T.Optional[str]
        path_found = False # type: bool

        for i in broken_list:
            if curr_str is None:
                curr_str = i
                path_found = False
            elif os.path.isfile(curr_str):
                # Abort concatenation if curr_str is an existing file
                fixed_list += [curr_str]
                curr_str = i
                path_found = False
            elif not reg_start.match(curr_str):
                # Abort concatenation if curr_str no longer matches the regex
                fixed_list += [curr_str]
                curr_str = i
                path_found = False
            elif reg_end.match(i):
                # File detected
                curr_str = '{} {}'.format(curr_str, i)
                fixed_list += [curr_str]
                curr_str = None
                path_found = False
            elif os.path.exists('{} {}'.format(curr_str, i)):
                # Path detected
                curr_str = '{} {}'.format(curr_str, i)
                path_found = True
            elif path_found:
                # Add path to fixed_list after ensuring the whole path is in curr_str
                fixed_list += [curr_str]
                curr_str = i
                path_found = False
            else:
                curr_str = '{} {}'.format(curr_str, i)
                path_found = False

        if curr_str:
            fixed_list += [curr_str]
        return fixed_list
