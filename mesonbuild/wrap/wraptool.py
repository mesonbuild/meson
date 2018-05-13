# Copyright 2015-2016 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import sys, os
import configparser
import shutil
import argparse

from glob import glob

from .wrap import API_ROOT, open_wrapdburl

from .. import mesonlib

def add_arguments(parser):
    subparsers = parser.add_subparsers(title='Commands', dest='command')
    subparsers.required = True

    p = subparsers.add_parser('list', help='show all available projects')
    p.set_defaults(wrap_func=list_projects)

    p = subparsers.add_parser('search', help='search the db by name')
    p.add_argument('name')
    p.set_defaults(wrap_func=search)

    p = subparsers.add_parser('install', help='install the specified project')
    p.add_argument('name')
    p.set_defaults(wrap_func=install)

    p = subparsers.add_parser('update', help='update the project to its newest available release')
    p.add_argument('name')
    p.set_defaults(wrap_func=update)

    p = subparsers.add_parser('info', help='show available versions of a project')
    p.add_argument('name')
    p.set_defaults(wrap_func=info)

    p = subparsers.add_parser('status', help='show installed and available versions of your projects')
    p.set_defaults(wrap_func=status)

    p = subparsers.add_parser('promote', help='bring a subsubproject up to the master project')
    p.add_argument('project_path')
    p.set_defaults(wrap_func=promote)

def get_result(urlstring):
    u = open_wrapdburl(urlstring)
    data = u.read().decode('utf-8')
    jd = json.loads(data)
    if jd['output'] != 'ok':
        print('Got bad output from server.')
        print(data)
        sys.exit(1)
    return jd

def get_projectlist():
    jd = get_result(API_ROOT + 'projects')
    projects = jd['projects']
    return projects

def list_projects(options):
    projects = get_projectlist()
    for p in projects:
        print(p)

def search(options):
    name = options.name
    jd = get_result(API_ROOT + 'query/byname/' + name)
    for p in jd['projects']:
        print(p)

def get_latest_version(name):
    jd = get_result(API_ROOT + 'query/get_latest/' + name)
    branch = jd['branch']
    revision = jd['revision']
    return branch, revision

def install(options):
    name = options.name
    if not os.path.isdir('subprojects'):
        print('Subprojects dir not found. Run this script in your source root directory.')
        sys.exit(1)
    if os.path.isdir(os.path.join('subprojects', name)):
        print('Subproject directory for this project already exists.')
        sys.exit(1)
    wrapfile = os.path.join('subprojects', name + '.wrap')
    if os.path.exists(wrapfile):
        print('Wrap file already exists.')
        sys.exit(1)
    (branch, revision) = get_latest_version(name)
    u = open_wrapdburl(API_ROOT + 'projects/%s/%s/%s/get_wrap' % (name, branch, revision))
    data = u.read()
    with open(wrapfile, 'wb') as f:
        f.write(data)
    print('Installed', name, 'branch', branch, 'revision', revision)

def get_current_version(wrapfile):
    cp = configparser.ConfigParser()
    cp.read(wrapfile)
    cp = cp['wrap-file']
    patch_url = cp['patch_url']
    arr = patch_url.split('/')
    branch = arr[-3]
    revision = int(arr[-2])
    return branch, revision, cp['directory'], cp['source_filename'], cp['patch_filename']

def update(options):
    name = options.name
    if not os.path.isdir('subprojects'):
        print('Subprojects dir not found. Run this command in your source root directory.')
        sys.exit(1)
    wrapfile = os.path.join('subprojects', name + '.wrap')
    if not os.path.exists(wrapfile):
        print('Project', name, 'is not in use.')
        sys.exit(1)
    (branch, revision, subdir, src_file, patch_file) = get_current_version(wrapfile)
    (new_branch, new_revision) = get_latest_version(name)
    if new_branch == branch and new_revision == revision:
        print('Project', name, 'is already up to date.')
        sys.exit(0)
    u = open_wrapdburl(API_ROOT + 'projects/%s/%s/%d/get_wrap' % (name, new_branch, new_revision))
    data = u.read()
    shutil.rmtree(os.path.join('subprojects', subdir), ignore_errors=True)
    try:
        os.unlink(os.path.join('subprojects/packagecache', src_file))
    except FileNotFoundError:
        pass
    try:
        os.unlink(os.path.join('subprojects/packagecache', patch_file))
    except FileNotFoundError:
        pass
    with open(wrapfile, 'wb') as f:
        f.write(data)
    print('Updated', name, 'to branch', new_branch, 'revision', new_revision)

def info(options):
    name = options.name
    jd = get_result(API_ROOT + 'projects/' + name)
    versions = jd['versions']
    if not versions:
        print('No available versions of', name)
        sys.exit(0)
    print('Available versions of %s:' % name)
    for v in versions:
        print(' ', v['branch'], v['revision'])

def do_promotion(from_path, spdir_name):
    if os.path.isfile(from_path):
        assert(from_path.endswith('.wrap'))
        shutil.copy(from_path, spdir_name)
    elif os.path.isdir(from_path):
        sproj_name = os.path.basename(from_path)
        outputdir = os.path.join(spdir_name, sproj_name)
        if os.path.exists(outputdir):
            sys.exit('Output dir %s already exists. Will not overwrite.' % outputdir)
        shutil.copytree(from_path, outputdir, ignore=shutil.ignore_patterns('subprojects'))

def promote(options):
    argument = options.project_path
    spdir_name = 'subprojects'
    sprojs = mesonlib.detect_subprojects(spdir_name)

    # check if the argument is a full path to a subproject directory or wrap file
    system_native_path_argument = argument.replace('/', os.sep)
    for _, matches in sprojs.items():
        if system_native_path_argument in matches:
            do_promotion(system_native_path_argument, spdir_name)
            return

    # otherwise the argument is just a subproject basename which must be unambiguous
    if argument not in sprojs:
        sys.exit('Subproject %s not found in directory tree.' % argument)
    matches = sprojs[argument]
    if len(matches) > 1:
        print('There is more than one version of %s in tree. Please specify which one to promote:\n' % argument)
        for s in matches:
            print(s)
        sys.exit(1)
    do_promotion(matches[0], spdir_name)

def status(options):
    print('Subproject status')
    for w in glob('subprojects/*.wrap'):
        name = os.path.basename(w)[:-5]
        try:
            (latest_branch, latest_revision) = get_latest_version(name)
        except Exception:
            print('', name, 'not available in wrapdb.')
            continue
        try:
            (current_branch, current_revision, _, _, _) = get_current_version(w)
        except Exception:
            print('Wrap file not from wrapdb.')
            continue
        if current_branch == latest_branch and current_revision == latest_revision:
            print('', name, 'up to date. Branch %s, revision %d.' % (current_branch, current_revision))
        else:
            print('', name, 'not up to date. Have %s %d, but %s %d is available.' % (current_branch, current_revision, latest_branch, latest_revision))

def run(args):
    parser = argparse.ArgumentParser(prog='wraptool')
    add_arguments(parser)
    options = parser.parse_args(args)
    options.wrap_func(options)
    return 0
