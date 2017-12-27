# Copyright 2017 The Meson development team
from pyclbr import Function

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Code that creates simple startup projects."""

import os, sys, argparse, re
from glob import glob

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

lib_c_meson_template = '''project('{project_name}', 'c',
  version : '{version}',
  default_options : ['warning_level=3'])

# These arguments are only used to build the shared library
# not the executables that use the library.
lib_args = ['-DBUILDING_{utoken}']

# Hiding symbols that are not explicitly marked as exported
# requires a compiler flag on all compilers except VS.
cc = meson.get_compiler('c')
if cc.get_id() != 'msvc'
  lib_args += ['-fvisibility=hidden']
endif

shlib = shared_library('{lib_name}', '{source_file}',
  install : true,
  c_args : lib_args,
)

test_exe = executable('{test_exe_name}', '{test_source_file}',
  link_with : shlib)
test('{test_name}', test_exe)

# Make this library usable as a Meson subproject.
{ltoken}_dep = declare_dependency(
  include_directories: include_directories('.'),
  link_with : shlib)

# Make this library usable from the system's
# package manager.
install_headers('{header_file}', subdir : '{header_dir}')

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

hello_c_template  = '''#include <stdio.h>

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

hello_c_meson_template = '''project('{project_name}', 'c',
  version : '{version}',
  default_options : ['warning_level=3',
                     'cpp_std=c++14'])

exe = executable('{exe_name}', '{source_name}',
  install : true)
  
test('basic', exe)
'''

hello_cpp_template  = '''#include <iostream>

#define PROJECT_NAME "{project_name}"

int main(int argc, char **argv) {{
    if(argc != 1) {{
        std::cout << argv[0] <<  "takes no arguments.\\n";
        return 1;
    }}
    std::cout << "This is project " << PROJECT_NAME << ".\\n";
    return 0;
}}
'''

hello_cpp_meson_template = '''project('{project_name}', 'cpp',
  version : '{version}',
  default_options : ['warning_level=3'])

exe = executable('{exe_name}', '{source_name}',
  install : true)
  
test('basic', exe)
'''

lib_hpp_template = '''#pragma once
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

namespace {namespace} {{

class {utoken}_PUBLIC {class_name} {{

public:
  {class_name}();
  int get_number() const;
  
private:
  
  int number;

}};

}}

'''

lib_cpp_template = '''#include <{header_file}>

namespace {namespace} {{

{class_name}::{class_name}() {{
    number = 6;
}}

int {class_name}::get_number() const {{
  return number;
}}

}}
'''

lib_cpp_test_template = '''#include <{header_file}>
#include <iostream>

int main(int argc, char **argv) {{
    if(argc != 1) {{
        std::cout << argv[0] << " takes no arguments.\\n";
        return 1;
    }}
    {namespace}::{class_name} c;
    return c.get_number() != 6;
}}
'''

lib_cpp_meson_template = '''project('{project_name}', 'cpp',
  version : '{version}',
  default_options : ['warning_level=3', 'cpp_std=c++14'])

# These arguments are only used to build the shared library
# not the executables that use the library.
lib_args = ['-DBUILDING_{utoken}']

# Hiding symbols that are not explicitly marked as exported
# requires a compiler flag on all compilers except VS.
cpp = meson.get_compiler('cpp')
if cpp.get_id() != 'msvc'
  lib_args += ['-fvisibility=hidden']
endif

shlib = shared_library('{lib_name}', '{source_file}',
  install : true,
  cpp_args : lib_args,
)

test_exe = executable('{test_exe_name}', '{test_source_file}',
  link_with : shlib)
test('{test_name}', test_exe)

# Make this library usable as a Meson subproject.
{ltoken}_dep = declare_dependency(
  include_directories: include_directories('.'),
  link_with : shlib)

# Make this library usable from the system's
# package manager.
install_headers('{header_file}', subdir : '{header_dir}')

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

info_message = '''Sample project created. To build it run the
following commands:

meson builddir
ninja -C builddir
'''

def create_exe_c_sample(project_name, project_version):
    lowercase_token = re.sub(r'[^a-z0-9]', '_', project_name.lower())
    uppercase_token = lowercase_token.upper()
    source_name = lowercase_token + '.c'
    open(source_name, 'w').write(hello_c_template.format(project_name=project_name))
    open('meson.build', 'w').write(hello_c_meson_template.format(project_name=project_name,
                                                                 exe_name=lowercase_token,
                                                                 source_name=source_name,
                                                                 version=project_version))

def create_lib_c_sample(project_name, version):
    lowercase_token = re.sub(r'[^a-z0-9]', '_', project_name.lower())
    uppercase_token = lowercase_token.upper()
    function_name = lowercase_token[0:3] + '_func'
    lib_h_name = lowercase_token + '.h'
    lib_c_name = lowercase_token + '.c'
    test_c_name = lowercase_token + '_test.c'
    kwargs = {'utoken': uppercase_token,
              'ltoken': lowercase_token,
              'header_dir': lowercase_token,
              'function_name': function_name,
              'header_file': lib_h_name,
              'source_file': lib_c_name,
              'test_source_file': test_c_name, 
              'test_exe_name': lowercase_token,
              'project_name': project_name,
              'lib_name': lowercase_token,
              'test_name': lowercase_token,
              'version': version,
              }
    open(lib_h_name, 'w').write(lib_h_template.format(**kwargs))
    open(lib_c_name, 'w').write(lib_c_template.format(**kwargs))
    open(test_c_name, 'w').write(lib_c_test_template.format(**kwargs))
    open('meson.build', 'w').write(lib_c_meson_template.format(**kwargs))

def create_exe_cpp_sample(project_name, project_version):
    lowercase_token = re.sub(r'[^a-z0-9]', '_', project_name.lower())
    uppercase_token = lowercase_token.upper()
    source_name = lowercase_token + '.cpp'
    open(source_name, 'w').write(hello_cpp_template.format(project_name=project_name))
    open('meson.build', 'w').write(hello_cpp_meson_template.format(project_name=project_name,
                                                                 exe_name=lowercase_token,
                                                                 source_name=source_name,
                                                                 version=project_version))

def create_lib_cpp_sample(project_name, version):
    lowercase_token = re.sub(r'[^a-z0-9]', '_', project_name.lower())
    uppercase_token = lowercase_token.upper()
    class_name = uppercase_token[0] + lowercase_token[1:]
    namespace = lowercase_token
    lib_h_name = lowercase_token + '.hpp'
    lib_c_name = lowercase_token + '.cpp'
    test_c_name = lowercase_token + '_test.cpp'
    kwargs = {'utoken': uppercase_token,
              'ltoken': lowercase_token,
              'header_dir': lowercase_token,
              'class_name': class_name,
              'namespace': namespace,
              'header_file': lib_h_name,
              'source_file': lib_c_name,
              'test_source_file': test_c_name, 
              'test_exe_name': lowercase_token,
              'project_name': project_name,
              'lib_name': lowercase_token,
              'test_name': lowercase_token,
              'version': version,
              }
    open(lib_h_name, 'w').write(lib_hpp_template.format(**kwargs))
    open(lib_c_name, 'w').write(lib_cpp_template.format(**kwargs))
    open(test_c_name, 'w').write(lib_cpp_test_template.format(**kwargs))
    open('meson.build', 'w').write(lib_cpp_meson_template.format(**kwargs))

def create_sample(options):
    if options.language == 'c':
        if options.type == 'executable':
            create_exe_c_sample(options.name, options.version)
        elif options.type == 'library':
            create_lib_c_sample(options.name, options.version)
        else:
            raise RuntimeError('Unreachable code')
    elif options.language == 'cpp':
        if options.type == 'executable':
            create_exe_cpp_sample(options.name, options.version)
        elif options.type == 'library':
            create_lib_cpp_sample(options.name, options.version)
        else:
            raise RuntimeError('Unreachable code')
    else:
        raise RuntimeError('Unreachable code')
    print(info_message)

def run(args):
    parser = argparse.ArgumentParser(prog='meson')
    parser.add_argument('--name', default = 'mesonsample')
    parser.add_argument('--type', default='executable',
                        choices=['executable', 'library'])
    parser.add_argument('--language', default='c', choices=['c', 'cpp'])
    parser.add_argument('--version', default='1.0')
    options = parser.parse_args(args)
    if len(glob('*')) != 0:
        sys.exit('This command must be run in an empty directory.')
    create_sample(options)
    return 0
