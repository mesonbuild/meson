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

import os, sys, argparse, re
from glob import glob

hello_c_template  = '''#include <stdio.h>

#define PROJECT_NAME "{project_name}"

int main(int argc, char **argv) {{
    printf("This is project %s.", PROJECT_NAME);
    return 0;
}}
'''

hello_c_meson_template = '''project('{project_name}', 'c')

executable('{exe_name}', '{source_name}',
  install : true)
'''

info_message = '''Sample project created. To build it run the
following commands:

meson builddir
ninja -C builddir
'''

def create_exe_c_sample(project_name):
    lowercase_token = re.sub(r'[^a-z0-9]', '_', project_name.lower())
    uppercase_token = lowercase_token.upper()
    source_name = lowercase_token + '.c'
    open(source_name, 'w').write(hello_c_template.format(project_name=project_name))
    open('meson.build', 'w').write(hello_c_meson_template.format(project_name=project_name,
                                                                 exe_name=lowercase_token,
                                                                 source_name=source_name))

def create_sample(options):
    create_exe_c_sample(options.name)
    print(info_message)

def run(args):
    parser = argparse.ArgumentParser(prog='meson')
    parser.add_argument('--name', default = 'mesonsample')
    #parser.add_argument('--type', default_value='executable')
    options = parser.parse_args(args)
    if len(glob('*')) != 0:
        sys.exit('This command must be run in an empty directory.')
    create_sample(options)
    return 0
