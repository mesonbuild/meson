# Copyright 2017 The Meson development team

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

import os, sys, argparse, re, shutil, subprocess
from glob import glob
from mesonbuild import mesonlib
from mesonbuild.environment import detect_ninja

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

shlib = shared_library('{lib_name}', '{source_file}',
  install : true,
  c_args : lib_args,
  gnu_symbol_visibility : 'hidden',
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

hello_c_meson_template = '''project('{project_name}', 'c',
  version : '{version}',
  default_options : ['warning_level=3'])

exe = executable('{exe_name}', '{source_name}',
  install : true)

test('basic', exe)
'''

hello_cpp_template = '''#include <iostream>

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
  default_options : ['warning_level=3',
                     'cpp_std=c++14'])

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

shlib = shared_library('{lib_name}', '{source_file}',
  install : true,
  cpp_args : lib_args,
  gnu_symbol_visibility : 'hidden',
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

def autodetect_options(options, sample=False):
    if not options.name:
        options.name = os.path.basename(os.getcwd())
        if not re.match('[a-zA-Z_][a-zA-Z0-9]*', options.name) and sample:
            print('Name of current directory "{}" is not usable as a sample project name.\n'
                  'Specify a project name with --name.'.format(options.name))
            sys.exit(1)
        print('Using "{}" (name of current directory) as project name.'
              .format(options.name))
    if not options.executable:
        options.executable = options.name
        print('Using "{}" (project name) as name of executable to build.'
              .format(options.executable))
    if sample:
        # The rest of the autodetection is not applicable to generating sample projects.
        return
    if not options.srcfiles:
        srcfiles = []
        for f in os.listdir():
            if f.endswith('.cc') or f.endswith('.cpp') or f.endswith('.c'):
                srcfiles.append(f)
        if not srcfiles:
            print("No recognizable source files found.\n"
                  "Run me in an empty directory to create a sample project.")
            sys.exit(1)
        options.srcfiles = srcfiles
        print("Detected source files: " + ' '.join(srcfiles))
    if not options.language:
        for f in options.srcfiles:
            if f.endswith('.cc') or f.endswith('.cpp'):
                options.language = 'cpp'
                break
            if f.endswith('.c'):
                options.language = 'c'
                break
        if not options.language:
            print("Can't autodetect language, please specify it with -l.")
            sys.exit(1)
        print("Detected language: " + options.language)

meson_executable_template = '''project('{project_name}', '{language}',
  version : '{version}',
  default_options : [{default_options}])

executable('{executable}',
           {sourcespec},{depspec}
           install : true)
'''

def create_meson_build(options):
    if options.type != 'executable':
        print('\nGenerating a meson.build file from existing sources is\n'
              'supported only for project type "executable".\n'
              'Run me in an empty directory to create a sample project.')
        sys.exit(1)
    default_options = ['warning_level=3']
    if options.language == 'cpp':
        # This shows how to set this very common option.
        default_options += ['cpp_std=c++14']
    # If we get a meson.build autoformatter one day, this code could
    # be simplified quite a bit.
    formatted_default_options = ', '.join("'{}'".format(x) for x in default_options)
    sourcespec = ',\n           '.join("'{}'".format(x) for x in options.srcfiles)
    depspec = ''
    if options.deps:
        depspec = '\n           dependencies : [\n              '
        depspec += ',\n              '.join("dependency('{}')".format(x)
                                            for x in options.deps.split(','))
        depspec += '],'
    content = meson_executable_template.format(project_name=options.name,
                                               language=options.language,
                                               version=options.version,
                                               executable=options.executable,
                                               sourcespec=sourcespec,
                                               depspec=depspec,
                                               default_options=formatted_default_options)
    open('meson.build', 'w').write(content)
    print('Generated meson.build file:\n\n' + content)

def run(args):
    parser = argparse.ArgumentParser(prog='meson')
    parser.add_argument("srcfiles", metavar="sourcefile", nargs="*",
                        help="source files. default: all recognized files in current directory")
    parser.add_argument("-n", "--name", help="project name. default: name of current directory")
    parser.add_argument("-e", "--executable", help="executable name. default: project name")
    parser.add_argument("-d", "--deps", help="dependencies, comma-separated")
    parser.add_argument("-l", "--language", choices=['c', 'cpp'],
                        help="project language. default: autodetected based on source files")
    parser.add_argument("-b", "--build", help="build after generation", action='store_true')
    parser.add_argument("--builddir", help="directory for build", default='build')
    parser.add_argument("-f", "--force", action="store_true",
                        help="force overwrite of existing files and directories.")
    parser.add_argument('--type', default='executable',
                        choices=['executable', 'library'])
    parser.add_argument('--version', default='0.1')
    options = parser.parse_args(args)
    if len(glob('*')) == 0:
        autodetect_options(options, sample=True)
        if not options.language:
            print('Defaulting to generating a C language project.')
            options.language = 'c'
        create_sample(options)
    else:
        autodetect_options(options)
        if os.path.isfile('meson.build') and not options.force:
            print('meson.build already exists. Use --force to overwrite.')
            sys.exit(1)
        create_meson_build(options)
    if options.build:
        if os.path.isdir(options.builddir) and options.force:
            print('Build directory already exists, deleting it.')
            shutil.rmtree(options.builddir)
        print('Building...')
        cmd = mesonlib.meson_command + [options.builddir]
        err = subprocess.call(cmd)
        if err:
            sys.exit(1)
        cmd = [detect_ninja(), '-C', options.builddir]
        err = subprocess.call(cmd)
        if err:
            sys.exit(1)
    return 0
