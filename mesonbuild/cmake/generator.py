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

from .. import mesonlib
import typing as T

def parse_generator_expressions(raw: str) -> str:
    '''Parse CMake generator expressions

    Most generator expressions are simply ignored for
    simplicety, however some are required for some common
    use cases.
    '''

    out = ''  # type: str
    i = 0     # type: int

    def equal(arg: str) -> str:
        col_pos = arg.find(',')
        if col_pos < 0:
            return '0'
        else:
            return '1' if arg[:col_pos] == arg[col_pos + 1:] else '0'

    def vers_comp(op: str, arg: str) -> str:
        col_pos = arg.find(',')
        if col_pos < 0:
            return '0'
        else:
            return '1' if mesonlib.version_compare(arg[:col_pos], '{}{}'.format(op, arg[col_pos + 1:])) else '0'

    supported = {
        # Boolean functions
        'BOOL': lambda x: '0' if x.upper() in ['0', 'FALSE', 'OFF', 'N', 'NO', 'IGNORE', 'NOTFOUND'] or x.endswith('-NOTFOUND') else '1',
        'AND': lambda x: '1' if all([y == '1' for y in x.split(',')]) else '0',
        'OR': lambda x: '1' if any([y == '1' for y in x.split(',')]) else '0',
        'NOT': lambda x: '0' if x == '1' else '1',

        '0': lambda x: '',
        '1': lambda x: x,

        # String operations
        'STREQUAL': equal,
        'EQUAL': equal,
        'VERSION_LESS': lambda x: vers_comp('<', x),
        'VERSION_GREATER': lambda x: vers_comp('>', x),
        'VERSION_EQUAL': lambda x: vers_comp('=', x),
        'VERSION_LESS_EQUAL': lambda x: vers_comp('<=', x),
        'VERSION_GREATER_EQUAL': lambda x: vers_comp('>=', x),

        # String modification
        'LOWER_CASE': lambda x: x.lower(),
        'UPPER_CASE': lambda x: x.upper(),

        # Always assume the BUILD_INTERFACE is valid.
        # INSTALL_INTERFACE is always invalid for subprojects and
        # it should also never appear in CMake config files, used
        # for dependencies
        'INSTALL_INTERFACE': lambda x: '',
        'BUILD_INTERFACE': lambda x: x,

        # Constants
        'ANGLE-R': lambda x: '>',
        'COMMA': lambda x: ',',
        'SEMICOLON': lambda x: ';',
    }  # type: T.Dict[str, T.Callable[[str], str]]

    # Recursively evaluate generator expressions
    def eval_generator_expressions() -> str:
        nonlocal i
        i += 2

        func = ''  # type: str
        args = ''  # type: str
        res = ''   # type: str
        exp = ''   # type: str

        # Determine the body of the expression
        while i < len(raw):
            if raw[i] == '>':
                # End of the generator expression
                break
            elif i < len(raw) - 1 and raw[i] == '$' and raw[i + 1] == '<':
                # Nested generator expression
                exp += eval_generator_expressions()
            else:
                # Generator expression body
                exp += raw[i]

            i += 1

        # Split the expression into a function and arguments part
        col_pos = exp.find(':')
        if col_pos < 0:
            func = exp
        else:
            func = exp[:col_pos]
            args = exp[col_pos + 1:]

        func = func.strip()
        args = args.strip()

        # Evaluate the function
        if func in supported:
            res = supported[func](args)

        return res

    while i < len(raw):
        if i < len(raw) - 1 and raw[i] == '$' and raw[i + 1] == '<':
            # Generator expression detected --> try resolving it
            out += eval_generator_expressions()
        else:
            # Normal string, leave unchanged
            out += raw[i]

        i += 1

    return out
