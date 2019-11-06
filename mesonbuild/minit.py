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

from pathlib import Path
import re, shutil, subprocess
from glob import glob
from mesonbuild import mesonlib
from mesonbuild.environment import detect_ninja

from mesonbuild.templates.ctemplates import (create_exe_c_sample, create_lib_c_sample)
from mesonbuild.templates.cpptemplates import (create_exe_cpp_sample, create_lib_cpp_sample)
from mesonbuild.templates.objctemplates import (create_exe_objc_sample, create_lib_objc_sample)
from mesonbuild.templates.dlangtemplates import (create_exe_d_sample, create_lib_d_sample)
from mesonbuild.templates.fortrantemplates import (create_exe_fortran_sample, create_lib_fortran_sample)
from mesonbuild.templates.rusttemplates import (create_exe_rust_sample, create_lib_rust_sample)

FORTRAN_SUFFIXES = ['.f', '.for', '.F', '.f90', '.F90']

info_message = '''Sample project created. To build it run the
following commands:

meson builddir
ninja -C builddir
'''

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
    elif options.language == 'd':
        if options.type == 'executable':
            create_exe_d_sample(options.name, options.version)
        elif options.type == 'library':
            create_lib_d_sample(options.name, options.version)
        else:
            raise RuntimeError('Unreachable code')
    elif options.language == 'fortran':
        if options.type == 'executable':
            create_exe_fortran_sample(options.name, options.version)
        elif options.type == 'library':
            create_lib_fortran_sample(options.name, options.version)
        else:
            raise RuntimeError('Unreachable code')
    elif options.language == 'rust':
        if options.type == 'executable':
            create_exe_rust_sample(options.name, options.version)
        elif options.type == 'library':
            create_lib_rust_sample(options.name, options.version)
        else:
            raise RuntimeError('Unreachable code')
    elif options.language == 'objc':
        if options.type == 'executable':
            create_exe_objc_sample(options.name, options.version)
        elif options.type == 'library':
            create_lib_objc_sample(options.name, options.version)
        else:
            raise RuntimeError('Unreachable code')
    else:
        raise RuntimeError('Unreachable code')
    print(info_message)

def autodetect_options(options, sample: bool = False):
    if not options.name:
        options.name = Path().resolve().stem
        if not re.match('[a-zA-Z_][a-zA-Z0-9]*', options.name) and sample:
            raise SystemExit('Name of current directory "{}" is not usable as a sample project name.\n'
                             'Specify a project name with --name.'.format(options.name))
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
        for f in (f for f in Path().iterdir() if f.is_file()):
            if f.suffix in (['.cc', '.cpp', '.c', '.d', '.m', '.rs'] + FORTRAN_SUFFIXES):
                srcfiles.append(f)
        if not srcfiles:
            raise SystemExit('No recognizable source files found.\n'
                             'Run meson init in an empty directory to create a sample project.')
        options.srcfiles = srcfiles
        print("Detected source files: " + ' '.join(map(str, srcfiles)))
    options.srcfiles = [Path(f) for f in options.srcfiles]
    if not options.language:
        for f in options.srcfiles:
            if f.suffix in ('.cc', '.cpp'):
                options.language = 'cpp'
                break
            if f.suffix == '.c':
                options.language = 'c'
                break
            if f.suffix == '.d':
                options.language = 'd'
                break
            if f.suffix in FORTRAN_SUFFIXES:
                options.language = 'fortran'
                break
            if f.suffix == '.rs':
                options.language = 'rust'
                break
            if f.suffix == '.m':
                options.language = 'objc'
                break
        if not options.language:
            raise SystemExit("Can't autodetect language, please specify it with -l.")
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
        raise SystemExit('\nGenerating a meson.build file from existing sources is\n'
                         'supported only for project type "executable".\n'
                         'Run meson init in an empty directory to create a sample project.')
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

def add_arguments(parser):
    parser.add_argument("srcfiles", metavar="sourcefile", nargs="*",
                        help="source files. default: all recognized files in current directory")
    parser.add_argument("-n", "--name", help="project name. default: name of current directory")
    parser.add_argument("-e", "--executable", help="executable name. default: project name")
    parser.add_argument("-d", "--deps", help="dependencies, comma-separated")
    parser.add_argument("-l", "--language", choices=['c', 'cpp', 'd', 'fortran', 'rust', 'objc'],
                        help="project language. default: autodetected based on source files")
    parser.add_argument("-b", "--build", help="build after generation", action='store_true')
    parser.add_argument("--builddir", help="directory for build", default='build')
    parser.add_argument("-f", "--force", action="store_true",
                        help="force overwrite of existing files and directories.")
    parser.add_argument('--type', default='executable',
                        choices=['executable', 'library'])
    parser.add_argument('--version', default='0.1')

def run(options) -> int:
    if not glob('*'):
        autodetect_options(options, sample=True)
        if not options.language:
            print('Defaulting to generating a C language project.')
            options.language = 'c'
        create_sample(options)
    else:
        autodetect_options(options)
        if Path('meson.build').is_file() and not options.force:
            raise SystemExit('meson.build already exists. Use --force to overwrite.')
        create_meson_build(options)
    if options.build:
        if Path(options.builddir).is_dir() and options.force:
            print('Build directory already exists, deleting it.')
            shutil.rmtree(options.builddir)
        print('Building...')
        cmd = mesonlib.meson_command + [options.builddir]
        ret = subprocess.run(cmd)
        if ret.returncode:
            raise SystemExit
        cmd = [detect_ninja(), '-C', options.builddir]
        ret = subprocess.run(cmd)
        if ret.returncode:
            raise SystemExit
    return 0
