#!/usr/bin/env python3

# Copyright 2017 Niklas Claesson

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This is two implementations for how to get module names from the boost
sources.  One relies on json metadata files in the sources, the other relies on
the folder names.

Run the tool in the boost directory and append the stdout to the misc.py:

boost/$ path/to/meson/tools/boost_names.py >> path/to/meson/dependencies/misc.py
"""

import sys
import os
import collections
import pprint
import json
import re

Module = collections.namedtuple('Module', ['dirname', 'name', 'libnames'])
Module.__repr__ = lambda self: str((self.dirname, self.name, self.libnames))

LIBS = 'libs'

manual_map = {
    'callable_traits': 'Call Traits',
    'crc': 'CRC',
    'dll': 'DLL',
    'gil': 'GIL',
    'graph_parallel': 'GraphParallel',
    'icl': 'ICL',
    'io': 'IO State Savers',
    'msm': 'Meta State Machine',
    'mpi': 'MPI',
    'mpl': 'MPL',
    'multi_array': 'Multi-Array',
    'multi_index': 'Multi-Index',
    'numeric': 'Numeric Conversion',
    'ptr_container': 'Pointer Container',
    'poly_collection': 'PolyCollection',
    'qvm': 'QVM',
    'throw_exception': 'ThrowException',
    'tti': 'TTI',
    'vmd': 'VMD',
}

extra = [
    Module('utility', 'Compressed Pair', []),
    Module('core', 'Enable If', []),
    Module('functional', 'Functional/Factory', []),
    Module('functional', 'Functional/Forward', []),
    Module('functional', 'Functional/Hash', []),
    Module('functional', 'Functional/Overloaded Function', []),
    Module('utility', 'Identity Type', []),
    Module('utility', 'In Place Factory, Typed In Place Factory', []),
    Module('numeric', 'Interval', []),
    Module('math', 'Math Common Factor', []),
    Module('math', 'Math Octonion', []),
    Module('math', 'Math Quaternion', []),
    Module('math', 'Math/Special Functions', []),
    Module('math', 'Math/Statistical Distributions', []),
    Module('bind', 'Member Function', []),
    Module('algorithm', 'Min-Max', []),
    Module('numeric', 'Odeint', []),
    Module('utility', 'Operators', []),
    Module('core', 'Ref', []),
    Module('utility', 'Result Of', []),
    Module('algorithm', 'String Algo', []),
    Module('core', 'Swap', []),
    Module('', 'Tribool', []),
    Module('numeric', 'uBLAS', []),
    Module('utility', 'Value Initialized', []),
]

# Cannot find the following modules in the documentation of boost
not_modules = ['beast', 'logic', 'mp11', 'winapi']

def eprint(message):
    print(message, file=sys.stderr)

def get_library_names(jamfile):
    libs = []
    with open(jamfile) as jamfh:
        jam = jamfh.read()
        res = re.finditer(r'^lib[\s]+([A-Za-z0-9_]+)([^;]*);', jam, re.MULTILINE | re.DOTALL)
        for matches in res:
            if ':' in matches.group(2):
                libs.append(matches.group(1))
        res = re.finditer(r'^boost-lib[\s]+([A-Za-z0-9_]+)([^;]*);', jam, re.MULTILINE | re.DOTALL)
        for matches in res:
            if ':' in matches.group(2):
                libs.append('boost_{}'.format(matches.group(1)))
    return libs

def exists(modules, module):
    return len([x for x in modules if x.dirname == module.dirname]) != 0

def get_modules(init=extra):
    modules = init
    for directory in os.listdir(LIBS):
        if not os.path.isdir(os.path.join(LIBS, directory)):
            continue
        if directory in not_modules:
            continue
        jamfile = os.path.join(LIBS, directory, 'build', 'Jamfile.v2')
        if os.path.isfile(jamfile):
            libs = get_library_names(jamfile)
        else:
            libs = []
        if directory in manual_map.keys():
            modname = manual_map[directory]
        else:
            modname = directory.replace('_', ' ').title()
        modules.append(Module(directory, modname, libs))
    return modules

def get_modules_2():
    modules = []
    # The python module uses an older build system format and is not easily parseable.
    # We add the python module libraries manually.
    modules.append(Module('python', 'Python', ['boost_python', 'boost_python3', 'boost_numpy', 'boost_numpy3']))
    for (root, dirs, files) in os.walk(LIBS):
        for f in files:
            if f == "libraries.json":
                projectdir = os.path.dirname(root)

                jamfile = os.path.join(projectdir, 'build', 'Jamfile.v2')
                if os.path.isfile(jamfile):
                    libs = get_library_names(jamfile)
                else:
                    libs = []

                # Get metadata for module
                jsonfile = os.path.join(root, f)
                with open(jsonfile) as jsonfh:
                    boost_modules = json.loads(jsonfh.read())
                    if(isinstance(boost_modules, dict)):
                        boost_modules = [boost_modules]
                    for boost_module in boost_modules:
                        modules.append(Module(boost_module['key'], boost_module['name'], libs))

    # Some subprojects do not have meta directory with json file. Find those
    jsonless_modules = [x for x in get_modules([]) if not exists(modules, x)]
    for module in jsonless_modules:
        eprint("WARNING: {} does not have meta/libraries.json. Will guess pretty name '{}'".format(module.dirname, module.name))
    modules.extend(jsonless_modules)

    return modules

def main(args):
    if not os.path.isdir(LIBS):
        eprint("ERROR: script must be run in boost source directory")

    # It will pick jsonless algorithm if 1 is given as argument
    impl = 0
    if len(args) > 1:
        if args[1] == '1':
            impl = 1

    if impl == 1:
        modules = get_modules()
    else:
        modules = get_modules_2()

    sorted_modules = sorted(modules, key=lambda module: module.name.lower())
    sorted_modules = [x[2] for x in sorted_modules if x[2]]
    sorted_modules = sum(sorted_modules, [])
    sorted_modules = [x for x in sorted_modules if x.startswith('boost')]

    pp = pprint.PrettyPrinter()
    pp.pprint(sorted_modules)

if __name__ == '__main__':
    main(sys.argv)
