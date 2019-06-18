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

from typing import List, Tuple
import re

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
    def __init__(self, name, target_type, properies=None):
        if properies is None:
            properies = {}
        self.name = name
        self.type = target_type
        self.properies = properies

    def __repr__(self):
        s = 'CMake TARGET:\n  -- name:      {}\n  -- type:      {}\n  -- properies: {{\n{}     }}'
        propSTR = ''
        for i in self.properies:
            propSTR += "      '{}': {}\n".format(i, self.properies[i])
        return s.format(self.name, self.type, propSTR)

class CMakeTraceParser:
    def __init__(self):
        # Dict of CMake variables: '<var_name>': ['list', 'of', 'values']
        self.vars = {}

        # Dict of CMakeTarget
        self.targets = {}

    def parse(self, trace: str) -> None:
        # First parse the trace
        lexer1 = self._lex_trace(trace)

        # All supported functions
        functions = {
            'set': self._cmake_set,
            'unset': self._cmake_unset,
            'add_executable': self._cmake_add_executable,
            'add_library': self._cmake_add_library,
            'add_custom_target': self._cmake_add_custom_target,
            'set_property': self._cmake_set_property,
            'set_target_properties': self._cmake_set_target_properties
        }

        # Primary pass -- parse everything
        for l in lexer1:
            # "Execute" the CMake function if supported
            fn = functions.get(l.func, None)
            if(fn):
                fn(l)

    def get_first_cmake_var_of(self, var_list: List[str]) -> List[str]:
        # Return the first found CMake variable in list var_list
        for i in var_list:
            if i in self.vars:
                return self.vars[i]

        return []

    def get_cmake_var(self, var: str) -> List[str]:
        # Return the value of the CMake variable var or an empty list if var does not exist
        if var in self.vars:
            return self.vars[var]

        return []

    def var_to_bool(self, var):
        if var not in self.vars:
            return False

        if len(self.vars[var]) < 1:
            return False

        if self.vars[var][0].upper() in ['1', 'ON', 'TRUE']:
            return True
        return False

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
            raise CMakeException('CMake: set() requires at least one argument\n{}'.format(tline))

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
            raise CMakeException('CMake: unset() requires at least one argument\n{}'.format(tline))

        if tline.args[0] in self.vars:
            del self.vars[tline.args[0]]

    def _cmake_add_executable(self, tline: CMakeTraceLine):
        # DOC: https://cmake.org/cmake/help/latest/command/add_executable.html
        args = list(tline.args) # Make a working copy

        # Make sure the exe is imported
        if 'IMPORTED' not in args:
            raise CMakeException('CMake: add_executable() non imported executables are not supported\n{}'.format(tline))

        args.remove('IMPORTED')

        if len(args) < 1:
            raise CMakeException('CMake: add_executable() requires at least 1 argument\n{}'.format(tline))

        self.targets[args[0]] = CMakeTarget(args[0], 'EXECUTABLE', {})

    def _cmake_add_library(self, tline: CMakeTraceLine):
        # DOC: https://cmake.org/cmake/help/latest/command/add_library.html
        args = list(tline.args) # Make a working copy

        # Make sure the lib is imported
        if 'IMPORTED' not in args:
            raise CMakeException('CMake: add_library() non imported libraries are not supported\n{}'.format(tline))

        args.remove('IMPORTED')

        # No only look at the first two arguments (target_name and target_type) and ignore the rest
        if len(args) < 2:
            raise CMakeException('CMake: add_library() requires at least 2 arguments\n{}'.format(tline))

        self.targets[args[0]] = CMakeTarget(args[0], args[1], {})

    def _cmake_add_custom_target(self, tline: CMakeTraceLine):
        # DOC: https://cmake.org/cmake/help/latest/command/add_custom_target.html
        # We only the first parameter (the target name) is interesting
        if len(tline.args) < 1:
            raise CMakeException('CMake: add_custom_target() requires at least one argument\n{}'.format(tline))

        self.targets[tline.args[0]] = CMakeTarget(tline.args[0], 'CUSTOM', {})

    def _cmake_set_property(self, tline: CMakeTraceLine) -> None:
        # DOC: https://cmake.org/cmake/help/latest/command/set_property.html
        args = list(tline.args)

        # We only care for TARGET properties
        if args.pop(0) != 'TARGET':
            return

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

            targets.append(curr)

        if not args:
            raise CMakeException('CMake: set_property() faild to parse argument list\n{}'.format(tline))

        if len(args) == 1:
            # Tries to set property to nothing so nothing has to be done
            return

        identifier = args.pop(0)
        value = ' '.join(args).split(';')
        if not value:
            return

        for i in targets:
            if i not in self.targets:
                raise CMakeException('CMake: set_property() TARGET {} not found\n{}'.format(i, tline))

            if identifier not in self.targets[i].properies:
                self.targets[i].properies[identifier] = []

            if append:
                self.targets[i].properies[identifier] += value
            else:
                self.targets[i].properies[identifier] = value

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
        #   1. Assume that the property will be capitalized, this is convention
        #      but cmake doesn't require it.
        #   2. Maintain a copy of the list here: https://cmake.org/cmake/help/latest/manual/cmake-properties.7.html#target-properties
        #
        # Neither of these is awesome for obvious reasons. I'm going to try
        # option 1 first and fall back to 2, as 1 requires less code and less
        # synchroniztion for cmake changes.

        arglist = []  # type: List[Tuple[str, List[str]]]
        name = args.pop(0)
        values = []
        for a in args:
            if a.isupper():
                if values:
                    arglist.append((name, ' '.join(values).split(';')))
                name = a
                values = []
            else:
                values.append(a)
        if values:
            arglist.append((name, ' '.join(values).split(';')))

        for name, value in arglist:
            for i in targets:
                if i not in self.targets:
                    raise CMakeException('CMake: set_target_properties() TARGET {} not found\n{}'.format(i, tline))

                self.targets[i].properies[name] = value

    def _lex_trace(self, trace):
        # The trace format is: '<file>(<line>):  <func>(<args -- can contain \n> )\n'
        reg_tline = re.compile(r'\s*(.*\.(cmake|txt))\(([0-9]+)\):\s*(\w+)\(([\s\S]*?) ?\)\s*\n', re.MULTILINE)
        reg_other = re.compile(r'[^\n]*\n')
        reg_genexp = re.compile(r'\$<.*>')
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
            args = mo_file_line.group(5).split(' ')
            args = list(map(lambda x: x.strip(), args))
            args = list(map(lambda x: reg_genexp.sub('', x), args)) # Remove generator expressions

            yield CMakeTraceLine(file, line, func, args)
