# SPDX-License-Identifier: Apache-2.0
# Copyright 2019 The Meson development team
# Copyright © 2023-2025 Intel Corporation

from __future__ import annotations

from mesonbuild.templates.sampleimpl import FileHeaderImpl


lib_h_template = '''#pragma once
#if defined _WIN32 || defined __CYGWIN__
  #ifdef BUILDING_{utoken}
    #define {utoken}_PUBLIC __declspec(dllexport)
  #else
    #define {utoken}_PUBLIC __declspec(dllimport)
  #endif
#else
  #ifdef BUILDING_{utoken}
      #define {utoken}_PUBLIC __attribute__ ((visibility ("default")))
  #else
      #define {utoken}_PUBLIC
  #endif
#endif

int {utoken}_PUBLIC {function_name}();

'''

lib_c_template = '''#include <{header_file}>

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

lib_c_test_template = '''#include <{header_file}>
#include <stdio.h>

int main(int argc, char **argv) {{
    if(argc != 1) {{
        printf("%s takes no arguments.\\n", argv[0]);
        return 1;
    }}
    return {function_name}();
}}
'''

lib_c_meson_template = '''project(
  '{project_name}',
  'c',
  version : '{version}',
  meson_version : '>= {meson_version}',
  default_options : ['warning_level=3'],
)

# These arguments are only used to build the shared library
# not the executables that use the library.
lib_args = ['-DBUILDING_{utoken}']

dependencies = [{dependencies}
]

shlib = shared_library(
  '{lib_name}',
  '{source_file}',
  install : true,
  c_args : lib_args,
  gnu_symbol_visibility : 'hidden',
  dependencies : dependencies,
)

test_exe = executable(
  '{test_exe_name}',
  '{test_source_file}',
  dependencies : dependencies,
  link_with : shlib,
)
test('{test_name}', test_exe)

# Make this library usable as a Meson subproject.
{ltoken}_dep = declare_dependency(
  include_directories : include_directories('.'),
  dependencies : dependencies,
  link_with : shlib,
)
meson.override_dependency('{project_name}', {ltoken}_dep)

# Make this library usable from the system's
# package manager.
install_headers('{header_file}', subdir : '{header_dir}')

pkg_mod = import('pkgconfig')
pkg_mod.generate(
  shlib,
  description : 'Meson sample project.',
  subdirs : '{header_dir}',
)
'''

hello_c_template = '''#include <stdio.h>

#define PROJECT_NAME "{project_name}"

int main(int argc, char **argv) {{
    if(argc != 1) {{
        printf("%s takes no arguments.\\n", argv[0]);
        return 1;
    }}
    printf("This is project %s.\\n", PROJECT_NAME);
    return 0;
}}
'''

hello_c_meson_template = '''project(
  '{project_name}',
  'c',
  meson_version : '>= {meson_version}',
  version : '{version}',
  default_options : ['warning_level=3'],
)

dependencies = [{dependencies}
]

exe = executable(
  '{exe_name}',
  '{source_name}',
  dependencies : dependencies,
  install : true,
)

test('basic', exe)
'''


class CProject(FileHeaderImpl):

    source_ext = 'c'
    header_ext = 'h'
    exe_template = hello_c_template
    exe_meson_template = hello_c_meson_template
    lib_template = lib_c_template
    lib_header_template = lib_h_template
    lib_test_template = lib_c_test_template
    lib_meson_template = lib_c_meson_template
