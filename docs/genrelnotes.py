#!/usr/bin/env python3

# Copyright 2019 The Meson development team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys, os, subprocess
from glob import glob

relnote_template = '''---
title: Release %s
short-description: Release notes for %s
...

# New features

'''


def add_to_sitemap(from_version, to_version):
    sitemapfile = '../sitemap.txt'
    sf = open(sitemapfile)
    lines = sf.readlines()
    sf.close()
    with open(sitemapfile, 'w') as sf:
        for line in lines:
            if 'Release-notes' in line and from_version in line:
                new_line = line.replace(from_version, to_version)
                sf.write(new_line)
            sf.write(line)

def generate(from_version, to_version):
    ofilename = 'Release-notes-for-%s.md' % to_version
    with open(ofilename, 'w') as ofile:
        ofile.write(relnote_template % (to_version, to_version))
        for snippetfile in glob('snippets/*.md'):
            snippet = open(snippetfile).read()
            ofile.write(snippet)
            if not snippet.endswith('\n'):
                ofile.write('\n')
            ofile.write('\n')
            subprocess.check_call(['git', 'rm', snippetfile])
    subprocess.check_call(['git', 'add', ofilename])
    add_to_sitemap(from_version, to_version)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(sys.argv[0], 'from_version to_version')
        sys.exit(1)
    from_version = sys.argv[1]
    to_version = sys.argv[2]
    os.chdir('markdown')
    generate(from_version, to_version)
