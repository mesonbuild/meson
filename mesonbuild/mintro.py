#!/usr/bin/env python3

# Copyright 2014-2016 The Meson development team

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
from . import coredata, build, mesonlib
import argparse
import sys, os

parser = argparse.ArgumentParser()
parser.add_argument('--targets', action='store_true', dest='list_targets', default=False,
                    help='List top level targets.')
parser.add_argument('--target-files', action='store', dest='target_files', default=None,
                    help='List source files for a given target.')
parser.add_argument('--buildsystem-files', action='store_true', dest='buildsystem_files', default=False,
                    help='List files that make up the build system.')
parser.add_argument('--buildoptions', action='store_true', dest='buildoptions', default=False,
                    help='List all build options.')
parser.add_argument('--tests', action='store_true', dest='tests', default=False,
                    help='List all unit tests.')
parser.add_argument('--benchmarks', action='store_true', dest='benchmarks', default=False,
                    help='List all benchmarks.')
parser.add_argument('--dependencies', action='store_true', dest='dependencies', default=False,
                    help='list external dependencies.')
parser.add_argument('args', nargs='+')

def list_targets(coredata, builddata):
    tlist = []
    for (idname, target) in builddata.get_targets().items():
        t = {}
        t['name'] = target.get_basename()
        t['id'] = idname
        fname = target.get_filename()
        if isinstance(fname, list):
            fname = [os.path.join(target.subdir, x) for x in fname]
        else:
            fname = os.path.join(target.subdir, fname)
        t['filename'] = fname
        if isinstance(target, build.Executable):
            typename = 'executable'
        elif isinstance(target, build.SharedLibrary):
            typename = 'shared library'
        elif isinstance(target, build.StaticLibrary):
            typename = 'static library'
        elif isinstance(target, build.CustomTarget):
            typename = 'custom'
        elif isinstance(target, build.RunTarget):
            typename = 'run'
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
    except KeyError:
        print("Unknown target %s." % target_name)
        sys.exit(1)
    sources = [os.path.join(i.subdir, i.fname) for i in sources]
    print(json.dumps(sources))

def list_buildoptions(coredata, builddata):
    buildtype= {'choices': ['plain', 'debug', 'debugoptimized', 'release', 'minsize'],
                'type' : 'combo',
                'value' : coredata.get_builtin_option('buildtype'),
                'description' : 'Build type',
                'name' : 'type'}
    strip = {'value' : coredata.get_builtin_option('strip'),
             'type' : 'boolean',
             'description' : 'Strip on install',
             'name' : 'strip'}
    unity = {'value' : coredata.get_builtin_option('unity'),
             'type' : 'boolean',
             'description' : 'Unity build',
             'name' : 'unity'}
    optlist = [buildtype, strip, unity]
    add_keys(optlist, coredata.user_options)
    add_keys(optlist, coredata.compiler_options)
    add_keys(optlist, coredata.base_options)
    print(json.dumps(optlist))

def add_keys(optlist, options):
    keys = list(options.keys())
    keys.sort()
    for key in keys:
        opt = options[key]
        optdict = {}
        optdict['name'] = key
        optdict['value'] = opt.value
        if isinstance(opt, coredata.UserStringOption):
            typestr = 'string'
        elif isinstance(opt, coredata.UserBooleanOption):
            typestr = 'boolean'
        elif isinstance(opt, coredata.UserComboOption):
            optdict['choices'] = opt.choices
            typestr = 'combo'
        elif isinstance(opt, coredata.UserStringArrayOption):
            typestr = 'stringarray'
        else:
            raise RuntimeError("Unknown option type")
        optdict['type'] = typestr
        optdict['description'] = opt.description
        optlist.append(optdict)

def list_buildsystem_files(coredata, builddata):
    src_dir = builddata.environment.get_source_dir()
    # I feel dirty about this. But only slightly.
    filelist = []
    for root, _, files in os.walk(src_dir):
        for f in files:
            if f == 'meson.build' or f == 'meson_options.txt':
                filelist.append(os.path.relpath(os.path.join(root, f), src_dir))
    print(json.dumps(filelist))

def list_deps(coredata):
    result = {}
    for d in coredata.deps.values():
        if d.found():
            args = {'compile_args': d.get_compile_args(),
                    'link_args': d.get_link_args()}
            result[d.name] = args
    print(json.dumps(result))

def list_tests(testdata):
    result = []
    for t in testdata:
        to = {}
        if isinstance(t.fname, str):
            fname = [t.fname]
        else:
            fname = t.fname
        to['cmd'] = fname + t.cmd_args
        to['env'] = t.env
        to['name'] = t.name
        to['workdir'] = t.workdir
        to['timeout'] = t.timeout
        to['suite'] = t.suite
        result.append(to)
    print(json.dumps(result))

def run(args):
    options = parser.parse_args(args)
    if len(options.args) > 1:
        print('Too many arguments')
        return 1
    elif len(options.args) == 1:
        bdir = options.args[0]
    else:
        bdir = ''
    corefile = os.path.join(bdir, 'meson-private/coredata.dat')
    buildfile = os.path.join(bdir, 'meson-private/build.dat')
    testfile = os.path.join(bdir, 'meson-private/meson_test_setup.dat')
    benchmarkfile = os.path.join(bdir, 'meson-private/meson_benchmark_setup.dat')
    with open(corefile, 'rb') as f:
        coredata = pickle.load(f)
    with open(buildfile, 'rb') as f:
        builddata = pickle.load(f)
    with open(testfile, 'rb') as f:
       testdata = pickle.load(f)
    with open(benchmarkfile, 'rb') as f:
       benchmarkdata = pickle.load(f)
    if options.list_targets:
        list_targets(coredata, builddata)
    elif options.target_files is not None:
        list_target_files(options.target_files, coredata, builddata)
    elif options.buildsystem_files:
        list_buildsystem_files(coredata, builddata)
    elif options.buildoptions:
        list_buildoptions(coredata, builddata)
    elif options.tests:
        list_tests(testdata)
    elif options.benchmarks:
        list_tests(benchmarkdata)
    elif options.dependencies:
        list_deps(coredata)
    else:
        print('No command specified')
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
