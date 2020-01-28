#!/usr/bin/env python3

# Copyright 2016 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# ghwt - GitHub WrapTool
#
# An emergency wraptool(1) replacement downloader that downloads
# directly from GitHub in case wrapdb.mesonbuild.com is down.

import urllib.request, json, sys, os, shutil, subprocess
import configparser, hashlib

req_timeout = 600.0
private_repos = {'meson', 'wrapweb', 'meson-ci'}
spdir = 'subprojects'

def gh_get(url):
    r = urllib.request.urlopen(url, timeout=req_timeout)
    jd = json.loads(r.read().decode('utf-8'))
    return jd

def list_projects():
    jd = gh_get('https://api.github.com/orgs/mesonbuild/repos')
    entries = [entry['name'] for entry in jd]
    entries = [e for e in entries if e not in private_repos]
    entries.sort()
    for i in entries:
        print(i)
    return 0

def unpack(sproj, branch):
    tmpdir = os.path.join(spdir, sproj + '_ghwt')
    shutil.rmtree(tmpdir, ignore_errors=True)
    subprocess.check_call(['git', 'clone', '-b', branch, 'https://github.com/mesonbuild/{}.git'.format(sproj), tmpdir])
    usfile = os.path.join(tmpdir, 'upstream.wrap')
    assert(os.path.isfile(usfile))
    config = configparser.ConfigParser(interpolation=None)
    config.read(usfile)
    outdir = os.path.join(spdir, sproj)
    if 'directory' in config['wrap-file']:
        outdir = os.path.join(spdir, config['wrap-file']['directory'])
    if os.path.isdir(outdir):
        print('Subproject is already there. To update, nuke the {} dir and reinstall.'.format(outdir))
        shutil.rmtree(tmpdir)
        return 1
    us_url = config['wrap-file']['source_url']
    us = urllib.request.urlopen(us_url, timeout=req_timeout).read()
    h = hashlib.sha256()
    h.update(us)
    dig = h.hexdigest()
    should = config['wrap-file']['source_hash']
    if dig != should:
        print('Incorrect hash on download.')
        print(' expected:', should)
        print(' obtained:', dig)
        return 1
    ofilename = os.path.join(spdir, config['wrap-file']['source_filename'])
    with open(ofilename, 'wb') as ofile:
        ofile.write(us)
    if 'lead_directory_missing' in config['wrap-file']:
        os.mkdir(outdir)
        shutil.unpack_archive(ofilename, outdir)
    else:
        shutil.unpack_archive(ofilename, spdir)
        assert(os.path.isdir(outdir))
    shutil.move(os.path.join(tmpdir, '.git'), outdir)
    subprocess.check_call(['git', 'reset', '--hard'], cwd=outdir)
    shutil.rmtree(tmpdir)
    shutil.rmtree(os.path.join(outdir, '.git'))
    os.unlink(ofilename)

def install(sproj, requested_branch=None):
    if not os.path.isdir(spdir):
        print('Run this in your source root and make sure there is a subprojects directory in it.')
        return 1
    blist = gh_get('https://api.github.com/repos/mesonbuild/{}/branches'.format(sproj))
    blist = [b['name'] for b in blist]
    blist = [b for b in blist if b != 'master']
    blist.sort()
    branch = blist[-1]
    if requested_branch is not None:
        if requested_branch in blist:
            branch = requested_branch
        else:
            print('Could not find user-requested branch', requested_branch)
            print('Available branches for', sproj, ':')
            print(blist)
            return 1
    print('Using branch', branch)
    return unpack(sproj, branch)

def print_help():
    print('Usage:')
    print(sys.argv[0], 'list')
    print(sys.argv[0], 'install', 'package_name', '[branch_name]')

def run(args):
    if not args or args[0] == '-h' or args[0] == '--help':
        print_help()
        return 1
    command = args[0]
    args = args[1:]
    if command == 'list':
        list_projects()
        return 0
    elif command == 'install':
        if len(args) == 1:
            return install(args[0])
        elif len(args) == 2:
            return install(args[0], args[1])
        else:
            print_help()
            return 1
    else:
        print('Unknown command')
        return 1

if __name__ == '__main__':
    print('This is an emergency wrap downloader. Use only when wrapdb is down.')
    sys.exit(run(sys.argv[1:]))
