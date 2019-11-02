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
import re

lib_fortran_template = '''
! This procedure will not be exported and is not
! directly callable by users of this library.

module modfoo

implicit none
private
public :: {function_name}

contains

integer function internal_function()
    internal_function = 0
end function internal_function

integer function {function_name}()
    {function_name} = internal_function()
end function {function_name}

end module modfoo
'''

lib_fortran_test_template = '''
use modfoo

print *,{function_name}()

end program
'''

lib_fortran_meson_template = '''project('{project_name}', 'fortran',
  version : '{version}',
  default_options : ['warning_level=3'])

# These arguments are only used to build the shared library
# not the executables that use the library.
lib_args = ['-DBUILDING_{utoken}']

shlib = shared_library('{lib_name}', '{source_file}',
  install : true,
  fortran_args : lib_args,
  gnu_symbol_visibility : 'hidden',
)

test_exe = executable('{test_exe_name}', '{test_source_file}',
  link_with : shlib)
test('{test_name}', test_exe)

# Make this library usable as a Meson subproject.
{ltoken}_dep = declare_dependency(
  include_directories: include_directories('.'),
  link_with : shlib)

pkg_mod = import('pkgconfig')
pkg_mod.generate(
  name : '{project_name}',
  filebase : '{ltoken}',
  description : 'Meson sample project.',
  subdirs : '{header_dir}',
  libraries : shlib,
  version : '{version}',
)
'''

hello_fortran_template = '''
implicit none

character(len=*), parameter :: PROJECT_NAME = "{project_name}"

print *,"This is project ", PROJECT_NAME

end program
'''

hello_fortran_meson_template = '''project('{project_name}', 'fortran',
  version : '{version}',
  default_options : ['warning_level=3'])

exe = executable('{exe_name}', '{source_name}',
  install : true)

test('basic', exe)
'''

def create_exe_fortran_sample(project_name, project_version):
    lowercase_token = re.sub(r'[^a-z0-9]', '_', project_name.lower())
    source_name = lowercase_token + '.f90'
    open(source_name, 'w').write(hello_fortran_template.format(project_name=project_name))
    open('meson.build', 'w').write(hello_fortran_meson_template.format(project_name=project_name,
                                                                       exe_name=lowercase_token,
                                                                       source_name=source_name,
                                                                       version=project_version))

def create_lib_fortran_sample(project_name, version):
    lowercase_token = re.sub(r'[^a-z0-9]', '_', project_name.lower())
    uppercase_token = lowercase_token.upper()
    function_name = lowercase_token[0:3] + '_func'
    lib_fortran_name = lowercase_token + '.f90'
    test_fortran_name = lowercase_token + '_test.f90'
    kwargs = {'utoken': uppercase_token,
              'ltoken': lowercase_token,
              'header_dir': lowercase_token,
              'function_name': function_name,
              'source_file': lib_fortran_name,
              'test_source_file': test_fortran_name,
              'test_exe_name': lowercase_token,
              'project_name': project_name,
              'lib_name': lowercase_token,
              'test_name': lowercase_token,
              'version': version,
              }
    open(lib_fortran_name, 'w').write(lib_fortran_template.format(**kwargs))
    open(test_fortran_name, 'w').write(lib_fortran_test_template.format(**kwargs))
    open('meson.build', 'w').write(lib_fortran_meson_template.format(**kwargs))
