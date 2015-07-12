#!/usr/bin/env python3

# Copyright 2013-2014 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This script installs Meson. We can't use Meson to install itself
# because of the bootstrap problem. We can't use any other build system
# either becaust that would be just silly.

import os, sys, glob, shutil, gzip
import argparse

parser = argparse.ArgumentParser()

parser.add_argument('--prefix', default='/usr/local', dest='prefix',
                    help='the installation prefix (default: %(default)s)')
parser.add_argument('--destdir', default='', dest='destdir',
                    help='the destdir (default: %(default)s)')

options = parser.parse_args()
if options.prefix[0] != '/':
    print('Error, prefix must be an absolute path.')
    sys.exit(1)

if options.destdir == '':
    install_root = options.prefix
else:
    install_root = os.path.join(options.destdir, options.prefix[1:])

script_dir = os.path.join(install_root, 'share/meson')
module_dir = os.path.join(script_dir, 'modules')
bin_dir = os.path.join(install_root, 'bin')
bin_script = os.path.join(script_dir, 'meson.py')
gui_script = os.path.join(script_dir, 'mesongui.py')
conf_script = os.path.join(script_dir, 'mesonconf.py')
intro_script = os.path.join(script_dir, 'mesonintrospect.py')
wraptool_script = os.path.join(script_dir, 'wraptool.py')
bin_name = os.path.join(bin_dir, 'meson')
gui_name = os.path.join(bin_dir, 'mesongui')
conf_name = os.path.join(bin_dir, 'mesonconf')
intro_name = os.path.join(bin_dir, 'mesonintrospect')
wraptool_name = os.path.join(bin_dir, 'wraptool')
man_dir = os.path.join(install_root, 'share/man/man1')
in_manfile = 'man/meson.1'
out_manfile = os.path.join(man_dir, 'meson.1.gz')
in_guimanfile = 'man/mesongui.1'
out_guimanfile = os.path.join(man_dir, 'mesongui.1.gz')
in_confmanfile = 'man/mesonconf.1'
out_confmanfile = os.path.join(man_dir, 'mesonconf.1.gz')
in_intromanfile = 'man/mesonintrospect.1'
out_intromanfile = os.path.join(man_dir, 'mesonintrospect.1.gz')
in_wrapmanfile = 'man/wraptool.1'
out_wrapmanfile = os.path.join(man_dir, 'wraptool.1.gz')
rpmmacros_dir = os.path.join(install_root, 'lib/rpm/macros.d')

symlink_value = os.path.relpath(bin_script, os.path.dirname(bin_name))
guisymlink_value = os.path.relpath(gui_script, os.path.dirname(gui_name))
confsymlink_value = os.path.relpath(conf_script, os.path.dirname(conf_name))
introsymlink_value = os.path.relpath(intro_script, os.path.dirname(intro_name))
wrapsymlink_value = os.path.relpath(wraptool_script, os.path.dirname(wraptool_name))

files = glob.glob('*.py')
files += glob.glob('*.ui')

noinstall = ['compile_meson.py', 'install_meson.py', 'run_tests.py', 'run_cross_test.py']

files = [x for x in files if x not in noinstall]

os.makedirs(script_dir, exist_ok=True)
os.makedirs(bin_dir, exist_ok=True)
os.makedirs(man_dir, exist_ok=True)

for f in files:
    print('Installing %s to %s.' %(f, script_dir))
    outfilename = os.path.join(script_dir, f)
    shutil.copyfile(f, outfilename)
    shutil.copystat(f, outfilename)
try:
    os.remove(bin_name)
except OSError:
    pass
print('Creating symlinks.')
try:
    os.unlink(bin_name)
except FileNotFoundError:
    pass
try:
    os.unlink(gui_name)
except FileNotFoundError:
    pass
try:
    os.unlink(conf_name)
except FileNotFoundError:
    pass
try:
    os.unlink(intro_name)
except FileNotFoundError:
    pass
try:
    os.unlink(wraptool_name)
except FileNotFoundError:
    pass
os.symlink(symlink_value, bin_name)
os.symlink(guisymlink_value, gui_name)
os.symlink(confsymlink_value, conf_name)
os.symlink(introsymlink_value, intro_name)
os.symlink(wrapsymlink_value, wraptool_name)
print('Installing manfiles to %s.' % man_dir)
open(out_manfile, 'wb').write(gzip.compress(open(in_manfile, 'rb').read()))
open(out_confmanfile, 'wb').write(gzip.compress(open(in_confmanfile, 'rb').read()))
open(out_guimanfile, 'wb').write(gzip.compress(open(in_guimanfile, 'rb').read()))
open(out_intromanfile, 'wb').write(gzip.compress(open(in_intromanfile, 'rb').read()))
open(out_wrapmanfile, 'wb').write(gzip.compress(open(in_wrapmanfile, 'rb').read()))

print('Installing modules to %s.' % module_dir)
if os.path.exists('modules/__pycache__'):
    shutil.rmtree('modules/__pycache__')
if os.path.exists(module_dir):
    shutil.rmtree(module_dir)
shutil.copytree('modules', module_dir)

if os.path.exists('/usr/bin/rpm'):
    print('Installing RPM macros to %s.' % rpmmacros_dir)
    outfilename = os.path.join(rpmmacros_dir, 'macros.meson')
    os.makedirs(rpmmacros_dir, exist_ok=True)
    shutil.copyfile('data/macros.meson', outfilename)
    shutil.copystat('data/macros.meson', outfilename)
