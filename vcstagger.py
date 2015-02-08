#!/usr/bin/env python3

# Copyright 2015 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys, os, subprocess

def tag(infile, outfile, fallback):
    tagid = get_string(infile, fallback)
    newdata = open(infile).read().replace('@VCS_TAG@', tagid)
    try:
        olddata = open(outfile).read()
        if olddata == newdata:
            return
    except Exception:
        pass
    open(outfile, 'w').write(newdata)

def get_string(infile, fallback):
    absfile = os.path.join(os.getcwd(), infile)
    directory = os.path.split(absfile)[0]
    segs = directory.replace('\\', '/').split('/')
    for i in range(len(segs), -1, -1):
        curdir = '/'.join(segs[:i])
        if os.path.isdir(os.path.join(curdir, '.git')):
            output = subprocess.check_output(['git', 'describe'],
                                             cwd = directory)
            return output.decode().strip()
        elif os.path.isdir(os.path.join(curdir, '.hg')):
            output = subprocess.check_output(['hg', 'identify'],
                                             cwd=directory)
            return output.decode().strip()
        elif os.path.isdir(os.path.join(curdir, '.bzr')):
            output = subprocess.check_output(['bzr', 'revno'],
                                             cwd=directory)
            return output.decode().strip()
        elif os.path.isdir(os.path.join(curdir, '.svn')):
            output = subprocess.check_output(['svn', 'info'],
                                             cwd=directory)
            for line in output.decode().split('\n'):
                (k, v) = line.split(':', 1)
                if k.strip() == 'Revision':
                    return v.strip()
            raise RuntimeError('Svn output malformed.')
    return fallback

if __name__ == '__main__':
    infile = sys.argv[1]
    outfile = sys.argv[2]
    fallback = sys.argv[3]
    tag(infile, outfile, fallback)
