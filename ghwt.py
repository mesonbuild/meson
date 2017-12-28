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
import configparser, hashlib, zipfile

private_repos = {'meson', 'wrapweb', 'meson-ci'}

def gh_get(url):
    r = urllib.request.urlopen(url)
    jd = json.loads(r.read().decode('utf-8'))
    return jd

def list_projects(org):
    try:
        jd = gh_get('https://api.github.com/orgs/%s/repos' % org)
    except urllib.error.HTTPError:
        jd = gh_get('https://api.github.com/users/%s/repos' % org)
    entries = [entry['name'] for entry in jd]
    entries = [e for e in entries if e not in private_repos]
    entries.sort()
    print('Meson Build projects of https://github.com/%s:\n' % org)
    for i in entries:
        print(i)
    return 0

def unpack(sproj, branch, outdir, org):
    subprocess.check_call(['git', 'clone', '-b', branch, 'https://github.com/%s/%s.git' % (org, sproj), outdir])
    upstream_file = os.path.join(outdir, 'upstream.wrap')
    upstream_content = open(upstream_file).read()
    try:
        revision_str = subprocess.check_output(['git', 'describe'], cwd=outdir).decode('utf-8')
        revision_id = int(revision_str.split('-')[1])
    except Exception:
        # no revision
        revision_id = None
    config = configparser.ConfigParser()
    config.read(upstream_file)
    wrap_def = config['wrap-file']
    shutil.rmtree(os.path.join(outdir, '.git'))
    os.unlink(os.path.join(outdir, 'readme.txt'))
    os.unlink(upstream_file)
    try:
        os.unlink(os.path.join(outdir, '.gitignore'))
    except Exception:
        pass
    base_name = sproj + '-' + branch
    if revision_id is not None:
        base_name += '-' + str(revision_id)
    base_name += '-wrap'
    zip_name = base_name + '.zip'
    wrap_name = sproj + '.wrap'
    zip_file = os.path.join(outdir, '..', zip_name)
    with zipfile.ZipFile(zip_file, 'w', compression=zipfile.ZIP_DEFLATED) as zip:
        for root, dirs, files in os.walk(outdir):
            for f in files:
                abspath = os.path.join(root, f)
                relpath = abspath[len(outdir) + 1:]
                zip.write(abspath, os.path.join(wrap_def['directory'], relpath))

    source_hash = hashlib.sha256(open(zip_file, 'rb').read()).hexdigest()
    shutil.rmtree(outdir) # delete git branch checkout
    # write .wrap file
    wrap_file = os.path.normpath(os.path.join(outdir, '..', wrap_name))
    with open(wrap_file, 'w') as wrap:
        url = 'file://' + os.path.abspath(zip_file)
        wrap.write(upstream_content.rstrip())
        wrap.write('\n\n')
        wrap.write('patch_url = %s\n' % url)
        wrap.write('patch_filename = %s\n' % zip_name)
        wrap.write('patch_hash = %s\n' % source_hash)

def install(sproj, org = 'mesonbuild'):
    sproj_dir = os.path.join('subprojects', sproj)
    if not os.path.isdir('subprojects'):
        print('Run this in your source root and make sure there is a subprojects directory in it.')
        return 1
    if os.path.isdir(sproj_dir):
        print('Subproject is already there. To update, nuke the dir and reinstall.')
        return 1
    blist = gh_get('https://api.github.com/repos/%s/%s/branches' % (org, sproj))
    blist = [b['name'] for b in blist]
    blist = [b for b in blist if b != 'master']
    blist.sort()
    branch = blist[-1]
    print('Using branch', branch)
    return unpack(sproj, branch, sproj_dir, org)

def run(args):
    if not args or args[0] == '-h' or args[0] == '--help':
        print('Usage:')
        print('   ', sys.argv[0], 'list [user/oranisation]')
        print('   ', sys.argv[0], 'install [user/]package_name')
        return 1
    command = args[0]
    args = args[1:]
    org = 'mesonbuild' # default organisation to take wrap packages from
    if command == 'list':
        if len(args) == 1:
            org = args[0]
        elif len(args) > 1:
            print('List can have only one optional argument (github organisation).')
            return 1
        list_projects(org)
        return 0
    elif command == 'install':
        if len(args) != 1:
            print('Install requires exactly one argument (wrap package name).')
            return 1
        chunks = args[0].split('/')
        if len(chunks) == 1:
            sproj = args[0]
        elif len(chunks) == 2:
            org, sproj = chunks
        else:
            print('Incorrect package name format.')
            return 1

        return install(sproj, org)
    else:
        print('Unknown command')
        return 1

if __name__ == '__main__':
    print('This is an emergency wrap downloader. Use only when wrapdb is down.')
    sys.exit(run(sys.argv[1:]))
