#!/usr/bin/env python3

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

from glob import glob

from .wrap import API_ROOT, open_wrapdburl

help_templ = '''This program allows you to manage your Wrap dependencies
using the online wrap database http://wrapdb.mesonbuild.com.

Run this command in your top level source directory.

Usage:

%s <command> [options]

Commands:

 list - show all available projects
 search - search the db by name
 install - install the specified project
 update - update the project to its newest available release
 info - show available versions of a project
 status - show installed and available versions of your projects

'''


def print_help():
    print(help_templ % sys.argv[0])

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

def list_projects():
    projects = get_projectlist()
    for p in projects:
        print(p)

def search(name):
    jd = get_result(API_ROOT + 'query/byname/' + name)
    for p in jd['projects']:
        print(p)

def get_latest_version(name):
    jd = get_result(API_ROOT + 'query/get_latest/' + name)
    branch = jd['branch']
    revision = jd['revision']
    return (branch, revision)

def install(name):
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
    return (branch, revision, cp['directory'], cp['source_filename'], cp['patch_filename'])

def update(name):
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

def info(name):
    jd = get_result(API_ROOT + 'projects/' + name)
    versions = jd['versions']
    if len(versions) == 0:
        print('No available versions of', name)
        sys.exit(0)
    print('Available versions of %s:' % name)
    for v in versions:
        print(' ', v['branch'], v['revision'])

def status():
    print('Subproject status')
    for w in glob('subprojects/*.wrap'):
        name = os.path.split(w)[1][:-5]
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
    if len(args) == 0 or args[0] == '-h' or args[0] == '--help':
        print_help()
        return 0
    command = args[0]
    args = args[1:]
    if command == 'list':
        list_projects()
    elif command == 'search':
        if len(args) != 1:
            print('Search requires exactly one argument.')
            return 1
        search(args[0])
    elif command == 'install':
        if len(args) != 1:
            print('Install requires exactly one argument.')
            return 1
        install(args[0])
    elif command == 'update':
        if len(args) != 1:
            print('update requires exactly one argument.')
            return 1
        update(args[0])
    elif command == 'info':
        if len(args) != 1:
            print('info requires exactly one argument.')
            return 1
        info(args[0])
    elif command == 'status':
        status()
    else:
        print('Unknown command', command)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
