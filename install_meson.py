#!/usr/bin/python3 -tt

# Copyright 2013 Jussi Pakkanen

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os, sys, glob, shutil
from optparse import OptionParser
from meson import version

usage_info = '%prog [--prefix PREFIX] [--destdir DESTDIR]'

parser = OptionParser(usage=usage_info)

build_types = ['plain', 'debug', 'optimized']
buildtype_help = 'build type, one of: %s' % ', '.join(build_types)
buildtype_help += ' (default: %default)'

parser.add_option('--prefix', default='/usr/local', dest='prefix',
                  help='the installation prefix (default: %default)')
parser.add_option('--destdir', default='', dest='destdir',
                  help='the destdir (default: %default)')

try:
    open('parsetab.py', 'r').close()
except IOError:
    print('Parsetab.py not found, run compile_meson.py first.')
    sys.exit(1)

(options, args) = parser.parse_args(sys.argv)
if options.prefix[0] != '/':
    print('Error, prefix must be an absolute path.')
    sys.exit(1)

if options.destdir == '':
    install_root = options.prefix
else:
    install_root = os.path.join(options.destdir, options.prefix[1:])

script_dir = os.path.join(install_root, 'share/meson-' + version)
bin_dir = os.path.join(install_root, 'bin')
bin_script = os.path.join(script_dir, 'meson.py')
bin_name = os.path.join(bin_dir, 'meson')

symlink_value = os.path.relpath(bin_script, os.path.dirname(bin_name))

files = glob.glob('*.py')

noinstall = ['compile_meson.py', 'install_meson.py', 'run_tests.py']

files = [x for x in files if x not in noinstall]

os.makedirs(script_dir, exist_ok=True)
os.makedirs(bin_dir, exist_ok=True)

for f in files:
    print('Installing %s to %s' %(f, script_dir))
    outfilename = os.path.join(script_dir, f)
    shutil.copyfile(f, outfilename)
    shutil.copystat(f, outfilename)

os.symlink(symlink_value, bin_name)
