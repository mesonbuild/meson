# SPDX-License-Identifier: Apache-2.0
# Copyright 2024 The Meson development team

from __future__ import annotations

from mesonbuild.templates.sampleimpl import FileImpl
import typing as T

class CythonProject(FileImpl):
    """
    Template generator for Cython projects.
    """
    
    source_ext = 'pyx'  # Cython source file extension
    
    # Template for the Cython source file
    lib_template = '''# This is a sample Cython file.
def cython_function():
    return "Hello from Cython!"
'''
    
    # Template for the test file
    lib_test_template = '''# This is a sample test file for the Cython module.
import module_name

def test_cython_function():
    assert module_name.cython_function() == "Hello from Cython!"
'''
    
    # Template for the Meson build file
    lib_meson_template = '''project('{project_name}', 'cython',
  version : '{version}',
  default_options : ['warning_level=3'])

cython_module = cython_shared_module('{lib_name}', '{source_file}',
  install : true,
)

test_exe = executable('{test_exe_name}', '{test_source_file}',
  link_with : cython_module)
test('{test_name}', test_exe)

# Make this module usable as a Meson subproject.
{ltoken}_dep = declare_dependency(
  include_directories: include_directories('.'),
  link_with : cython_module)
'''
    
    def lib_kwargs(self) -> T.Dict[str, str]:
        """
        Returns the keyword arguments for the template.
        """
        kwargs = super().lib_kwargs()
        kwargs['module_name'] = self.lowercase_token
        return kwargs
