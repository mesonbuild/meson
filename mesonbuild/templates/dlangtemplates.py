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
from __future__ import annotations

from mesonbuild.templates.sampleimpl import FileImpl

import typing as T


hello_d_template = '''module main;
import std.stdio;

enum PROJECT_NAME = "{project_name}";

int main(string[] args) {{
    if (args.length != 1){{
        writefln("%s takes no arguments.\\n", args[0]);
        return 1;
    }}
    writefln("This is project %s.\\n", PROJECT_NAME);
    return 0;
}}
'''

hello_d_meson_template = '''project('{project_name}', 'd',
    version : '{version}',
    default_options: ['warning_level=3'])

exe = executable('{exe_name}', '{source_name}',
  install : true)

test('basic', exe)
'''

lib_d_template = '''module {module_file};

/* This function will not be exported and is not
 * directly callable by users of this library.
 */
int internal_function() {{
    return 0;
}}

int {function_name}() {{
    return internal_function();
}}
'''

lib_d_test_template = '''module {module_file}_test;
import std.stdio;
import {module_file};


int main(string[] args) {{
    if (args.length != 1){{
        writefln("%s takes no arguments.\\n", args[0]);
        return 1;
    }}
    return {function_name}();
}}
'''

lib_d_meson_template = '''project('{project_name}', 'd',
  version : '{version}',
  default_options : ['warning_level=3'])

stlib = static_library('{lib_name}', '{source_file}',
  install : true,
  gnu_symbol_visibility : 'hidden',
)

test_exe = executable('{test_exe_name}', '{test_source_file}',
  link_with : stlib)
test('{test_name}', test_exe)

# Make this library usable as a Meson subproject.
{ltoken}_dep = declare_dependency(
  include_directories: include_directories('.'),
  link_with : stlib)

# Make this library usable from the Dlang
# build system.
dlang_mod = import('dlang')
if find_program('dub', required: false).found()
  dlang_mod.generate_dub_file(meson.project_name().to_lower(), meson.source_root(),
    name : meson.project_name(),
    license: meson.project_license(),
    sourceFiles : '{source_file}',
    description : 'Meson sample project.',
    version : '{version}',
  )
endif
'''


class DlangProject(FileImpl):

    source_ext = 'd'
    exe_template = hello_d_template
    exe_meson_template = hello_d_meson_template
    lib_template = lib_d_template
    lib_test_template = lib_d_test_template
    lib_meson_template = lib_d_meson_template

    def lib_kwargs(self) -> T.Dict[str, str]:
        kwargs = super().lib_kwargs()
        kwargs['module_file'] = self.lowercase_token
        return kwargs
