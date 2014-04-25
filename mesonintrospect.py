#!/usr/bin/env python3

# Copyright 2014 Jussi Pakkanen

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This is a helper script for IDE developers. It allows you to
extract information such as list of targets, files, compiler flags,
tests and so on. All output is in JSON for simple parsing.

Currently only works for the Ninja backend. Others use generated
project files and don't need this info."""

import json, pickle
import coredata, build
from optparse import OptionParser
import sys, os

parser = OptionParser()
parser.add_option('--list-targets', action='store_true', dest='list_targets', default=False)
parser.add_option('--target-files', action='store', dest='target_files', default=None)

def list_targets(coredata, builddata):
    tlist = []
    for target in builddata.get_targets().values():
        t = {}
        t['name'] = target.get_basename()
        t['filename'] = os.path.join(target.subdir, target.get_filename())
        if isinstance(target, build.Executable):
            typename = 'executable'
        elif isinstance(target, build.SharedLibrary):
            typename = 'shared library'
        elif isinstance(target, build.StaticLibrary):
            typename = 'static library'
        else:
            typename = 'unknown'
        t['type'] = typename
        if target.should_install():
            t['installed'] = True
        else:
            t['installed'] = False
        tlist.append(t)
    print(json.dumps(tlist))

def list_target_files(target_name, coredata, builddata):
    try:
        t = builddata.targets[target_name]
        sources = t.sources + t.extra_files
        subdir = t.subdir
    except KeyError:
        print("Unknown target %s." % target_name)
        sys.exit(1)
    sources = [os.path.join(subdir, i) for i in sources]
    print(json.dumps(sources))

if __name__ == '__main__':
    (options, args) = parser.parse_args()
    if len(args) > 1:
        print('Too many arguments')
        sys.exit(1)
    elif len(args) == 1:
        bdir = args[0]
    else:
        bdir == ''
    corefile = os.path.join(bdir, 'meson-private/coredata.dat')
    buildfile = os.path.join(bdir, 'meson-private/build.dat')
    coredata = pickle.load(open(corefile, 'rb'))
    builddata = pickle.load(open(buildfile, 'rb'))
    if options.list_targets:
        list_targets(coredata, builddata)
    elif options.target_files is not None:
        list_target_files(options.target_files, coredata, builddata)
    else:
        print('No command specified')
        sys.exit(1)
