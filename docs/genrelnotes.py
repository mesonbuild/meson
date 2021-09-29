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
'''
  Generates release notes for new releases of Meson build system
'''
import subprocess
import sys
import os
from glob import glob

RELNOTE_TEMPLATE = '''---
title: Release {}
short-description: Release notes for {}
...

# New features

'''


def add_to_sitemap(from_version, to_version):
    '''
       Adds release note entry to sitemap.txt.
    '''
    sitemapfile = '../sitemap.txt'
    s_f = open(sitemapfile, encoding='utf-8')
    lines = s_f.readlines()
    s_f.close()
    with open(sitemapfile, 'w', encoding='utf-8') as s_f:
        for line in lines:
            if 'Release-notes' in line and from_version in line:
                new_line = line.replace(from_version, to_version)
                s_f.write(new_line)
            s_f.write(line)

def generate(from_version, to_version):
    '''
       Generate notes for Meson build next release.
    '''
    ofilename = f'Release-notes-for-{to_version}.md'
    with open(ofilename, 'w', encoding='utf-8') as ofile:
        ofile.write(RELNOTE_TEMPLATE.format(to_version, to_version))
        for snippetfile in glob('snippets/*.md'):
            snippet = open(snippetfile, encoding='utf-8').read()
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
    FROM_VERSION = sys.argv[1]
    TO_VERSION = sys.argv[2]
    os.chdir('markdown')
    generate(FROM_VERSION, TO_VERSION)
