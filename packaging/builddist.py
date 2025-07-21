#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright 2025 The Meson development team

# This script must be run from the source root.

import pathlib, shutil, subprocess

gendir = pathlib.Path('distgendir')
distdir = pathlib.Path('dist')
gitdir = pathlib.Path('.git')

if distdir.is_dir():
    shutil.rmtree(distdir)
distdir.mkdir()

if gendir.is_dir():
    shutil.rmtree(gendir)
gendir.mkdir()

shutil.copytree(gitdir, gendir / '.git')

subprocess.check_call(['git', 'reset', '--hard'],
                      cwd=gendir)
subprocess.check_call(['python3', 'setup.py', 'sdist', 'bdist_wheel'],
                       cwd=gendir)
for f in (gendir / 'dist').glob('*'):
    shutil.copy(f, distdir)

shutil.rmtree(gendir)

