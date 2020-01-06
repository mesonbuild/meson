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

from ..mesonlib import MesonException
from .. import mlog
import typing as T

class CMakeException(MesonException):
    pass

class CMakeBuildFile:
    def __init__(self, file: str, is_cmake: bool, is_temp: bool):
        self.file = file
        self.is_cmake = is_cmake
        self.is_temp = is_temp

    def __repr__(self):
        return '<{}: {}; cmake={}; temp={}>'.format(self.__class__.__name__, self.file, self.is_cmake, self.is_temp)

def _flags_to_list(raw: str) -> T.List[str]:
    # Convert a raw commandline string into a list of strings
    res = []
    curr = ''
    escape = False
    in_string = False
    for i in raw:
        if escape:
            # If the current char is not a quote, the '\' is probably important
            if i not in ['"', "'"]:
                curr += '\\'
            curr += i
            escape = False
        elif i == '\\':
            escape = True
        elif i in ['"', "'"]:
            in_string = not in_string
        elif i in [' ', '\n']:
            if in_string:
                curr += i
            else:
                res += [curr]
                curr = ''
        else:
            curr += i
    res += [curr]
    res = list(filter(lambda x: len(x) > 0, res))
    return res

class CMakeFileGroup:
    def __init__(self, data: dict):
        self.defines = data.get('defines', '')
        self.flags = _flags_to_list(data.get('compileFlags', ''))
        self.includes = data.get('includePath', [])
        self.is_generated = data.get('isGenerated', False)
        self.language = data.get('language', 'C')
        self.sources = data.get('sources', [])

        # Fix the include directories
        tmp = []
        for i in self.includes:
            if isinstance(i, dict) and 'path' in i:
                i['isSystem'] = i.get('isSystem', False)
                tmp += [i]
            elif isinstance(i, str):
                tmp += [{'path': i, 'isSystem': False}]
        self.includes = tmp

    def log(self) -> None:
        mlog.log('flags        =', mlog.bold(', '.join(self.flags)))
        mlog.log('defines      =', mlog.bold(', '.join(self.defines)))
        mlog.log('includes     =', mlog.bold(', '.join(self.includes)))
        mlog.log('is_generated =', mlog.bold('true' if self.is_generated else 'false'))
        mlog.log('language     =', mlog.bold(self.language))
        mlog.log('sources:')
        for i in self.sources:
            with mlog.nested():
                mlog.log(i)

class CMakeTarget:
    def __init__(self, data: dict):
        self.artifacts = data.get('artifacts', [])
        self.src_dir = data.get('sourceDirectory', '')
        self.build_dir = data.get('buildDirectory', '')
        self.name = data.get('name', '')
        self.full_name = data.get('fullName', '')
        self.install = data.get('hasInstallRule', False)
        self.install_paths = list(set(data.get('installPaths', [])))
        self.link_lang = data.get('linkerLanguage', '')
        self.link_libraries = _flags_to_list(data.get('linkLibraries', ''))
        self.link_flags = _flags_to_list(data.get('linkFlags', ''))
        self.link_lang_flags = _flags_to_list(data.get('linkLanguageFlags', ''))
        # self.link_path = data.get('linkPath', '')
        self.type = data.get('type', 'EXECUTABLE')
        # self.is_generator_provided = data.get('isGeneratorProvided', False)
        self.files = []

        for i in data.get('fileGroups', []):
            self.files += [CMakeFileGroup(i)]

    def log(self) -> None:
        mlog.log('artifacts             =', mlog.bold(', '.join(self.artifacts)))
        mlog.log('src_dir               =', mlog.bold(self.src_dir))
        mlog.log('build_dir             =', mlog.bold(self.build_dir))
        mlog.log('name                  =', mlog.bold(self.name))
        mlog.log('full_name             =', mlog.bold(self.full_name))
        mlog.log('install               =', mlog.bold('true' if self.install else 'false'))
        mlog.log('install_paths         =', mlog.bold(', '.join(self.install_paths)))
        mlog.log('link_lang             =', mlog.bold(self.link_lang))
        mlog.log('link_libraries        =', mlog.bold(', '.join(self.link_libraries)))
        mlog.log('link_flags            =', mlog.bold(', '.join(self.link_flags)))
        mlog.log('link_lang_flags       =', mlog.bold(', '.join(self.link_lang_flags)))
        # mlog.log('link_path             =', mlog.bold(self.link_path))
        mlog.log('type                  =', mlog.bold(self.type))
        # mlog.log('is_generator_provided =', mlog.bold('true' if self.is_generator_provided else 'false'))
        for idx, i in enumerate(self.files):
            mlog.log('Files {}:'.format(idx))
            with mlog.nested():
                i.log()

class CMakeProject:
    def __init__(self, data: dict):
        self.src_dir = data.get('sourceDirectory', '')
        self.build_dir = data.get('buildDirectory', '')
        self.name = data.get('name', '')
        self.targets = []

        for i in data.get('targets', []):
            self.targets += [CMakeTarget(i)]

    def log(self) -> None:
        mlog.log('src_dir   =', mlog.bold(self.src_dir))
        mlog.log('build_dir =', mlog.bold(self.build_dir))
        mlog.log('name      =', mlog.bold(self.name))
        for idx, i in enumerate(self.targets):
            mlog.log('Target {}:'.format(idx))
            with mlog.nested():
                i.log()

class CMakeConfiguration:
    def __init__(self, data: dict):
        self.name = data.get('name', '')
        self.projects = []
        for i in data.get('projects', []):
            self.projects += [CMakeProject(i)]

    def log(self) -> None:
        mlog.log('name =', mlog.bold(self.name))
        for idx, i in enumerate(self.projects):
            mlog.log('Project {}:'.format(idx))
            with mlog.nested():
                i.log()
