# SPDX-License-Identifier: Apache-2.0
# Copyright 2019 The Meson development team

from __future__ import annotations

from mesonbuild.templates.sampleimpl import FileImpl

import typing as T


hello_pyx_template = '''print("This is project {project_name}.")'''

hello_pyx_meson_template = '''project('{project_name}', 'python',
    version : '{version}',
    default_options: ['warning_level=3'])

exe = executable('{exe_name}', '{source_name}',
  install : true)

test('basic', exe)
'''

lib_pyx_template = '''def internal_function():
    return 0

def {function_name}():
    return internal_function()
'''

lib_pyx_test_template = '''import {module_file}


def test_{function_name}():
    assert {function_name}() == 0
'''

lib_pyx_meson_template = '''project('{project_name}', 'python',
  version : '{version}',
  default_options : ['warning_level=3'])

stlib = static_library('{lib_name}', '{source_file}',
  install : true,
)

test_exe = executable('{test_exe_name}', '{test_source_file}',
  link_with : stlib)
test('{test_name}', test_exe)

# Make this library usable as a Meson subproject.
{ltoken}_dep = declare_dependency(
  include_directories: include_directories('.'),
  link_with : stlib)
'''

class CythonProject(FileImpl):

    source_ext = 'pyx'
    exe_template = hello_pyx_template
    exe_meson_template = hello_pyx_meson_template
    lib_template = lib_pyx_template
    lib_test_template = lib_pyx_test_template
    lib_meson_template = lib_pyx_meson_template

    def lib_kwargs(self) -> T.Dict[str, str]:
        kwargs = super().lib_kwargs()
        kwargs['module_file'] = self.lowercase_token
        return kwargs
