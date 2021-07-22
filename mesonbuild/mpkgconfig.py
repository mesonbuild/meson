# Copyright 2021 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import shlex
from .environment import Environment

def add_arguments(parser: 'argparse.ArgumentParser') -> None:
    parser.add_argument("--list-all", action='store_true')
    parser.add_argument("--path", action='store_true')
    parser.add_argument("--cflags", action='store_true')
    parser.add_argument("--libs", action='store_true')
    parser.add_argument("--static", action='store_true')
    parser.add_argument("--modversion", action='store_true')
    parser.add_argument("--variable")
    parser.add_argument("--define-variable")
    parser.add_argument("modules", nargs="*")

def run(options: 'argparse.Namespace') -> int:
    repo = Environment.create_pkgconfig_repo()
    allow_system_cflags = os.environ.get('PKG_CONFIG_ALLOW_SYSTEM_CFLAGS') is not None
    allow_system_libs = os.environ.get('PKG_CONFIG_ALLOW_SYSTEM_LIBS') is not None

    overrides = {}
    if options.define_variable:
        varname, value = options.define_variable.split('=', 1)
        overrides[varname] = value

    if options.list_all:
        packages = repo.get_all()
        max_len = max(len(pkg.pkgname) for pkg in packages)
        for pkg in packages:
            align = ' ' * (max_len - len(pkg.pkgname))
            print(pkg.pkgname + align, pkg.name, '-', pkg.description)

    all_cflags = []
    all_libs = []
    for module in options.modules:
        pkg = repo.lookup(module)
        if options.path:
            print(pkg.filename)
        if options.modversion:
            print(pkg.version)
        if options.variable:
            print(pkg.get_variable(options.variable, overrides=overrides))
        if options.cflags:
            all_cflags += pkg.get_cflags(allow_system_cflags)
        if options.libs:
            all_libs += pkg.get_libs(options.static, allow_system_libs)
    all_args = all_cflags + all_libs
    if all_args:
        print(' '.join([shlex.quote(a) for a in all_args]))
    return 0
