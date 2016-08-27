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

def split_options(user_options, suboptions):
    main_options = {}
    main_suboptions = {}
    subproject_options = {}
    subproject_suboptions = {} 
    for k in user_options.keys():
        if ':' in k:
            subproject_options[k] = user_options[k]
        else:
            main_options[k] = user_options[k]
    for k in suboptions.keys():
        if ':' in k:
            subproject_suboptions[k] = suboptions[k]
        else:
            main_suboptions[k] = suboptions[k]
    return (main_options, main_suboptions, subproject_options, subproject_suboptions)

def list_buildoptions(coredata, builddata):
    (main_options, main_suboptions, subproject_options, subproject_suboptions) = split_options(coredata.user_options, coredata.suboptions)
    all_opt = [{'name' : 'builtin',
                'description': 'Meson builtin options',
                'type': 'suboption',
                'value': get_keys(coredata.builtins),
                }]
    all_opt.append({'name': 'base',
                    'description' : 'Base options',
                    'type' : 'suboption',
                    'value' : get_keys(coredata.base_options),
                    })
    all_opt.append({'name' : 'compilers',
                    'description' : 'Options for compilers',
                    'type' : 'suboption',
                    'value' : get_keys(coredata.compiler_options),
                    })
    all_opt.append({'name': 'user',
                    'description' : 'User options',
                    'type' : 'suboption',
                    'value' : build_usertree(main_options, main_suboptions),
                    })
    all_opt += build_subprojecttree(subproject_options, subproject_suboptions)
    print(json.dumps(all_opt, indent=2))

def build_subprojecttree(options, suboptions):
    result = []
    sp_names = {}
    for n in options.keys():
        sp_names[n.split(':')[0]] = True
    for n in suboptions.keys():
        sp_names[n.split(':')[0]] = True
    for subproject in sorted(sp_names.keys()):
        prefix = subproject + ':'
        cur_opt = {x.name : x for x in options.values() if x.name.startswith(prefix)}
        cur_subopt = {x.name : x for x in suboptions.values() if x.name.startswith(prefix)}
        result.append({'name' : subproject,
                      'description' : 'Options of subproject: %s' % subproject,
                      'type' : 'suboption',
                      'value' :  build_usertree(cur_opt, cur_subopt)
                      })
    return result

def build_usertree(user_options, suboptions, subbranch=None):
    current = []
    current_suboptions = [x for x in suboptions.values() if x.parent == subbranch]
    current_options = [x for x in user_options.values() if x.parent == subbranch]
    for so in current_suboptions:
        subentry = {'type' : 'subobject',
                    'value' : build_usertree(user_options, suboptions, so.name),
                    'description' : so.description,
                    'name' : so.name
                    }
        current.append(subentry)
    for opt in current_options:
        current.append(opt2dict(opt.name, opt))
    return current

def opt2dict(key, opt):
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
    return optdict

def get_keys(options):
    optlist = []
    keys = list(options.keys())
    keys.sort()
    for key in keys:
        if key == 'backend': # The backend can never be changed.
            continue
        opt = options[key]
        optlist.append(opt2dict(key, opt))
    return optlist

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
    coredata = pickle.load(open(corefile, 'rb'))
    builddata = pickle.load(open(buildfile, 'rb'))
    testdata = pickle.load(open(testfile, 'rb'))
    benchmarkdata = pickle.load(open(benchmarkfile, 'rb'))
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
