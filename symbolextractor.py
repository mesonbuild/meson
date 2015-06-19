#!/usr/bin/env python3

# Copyright 2013-2015 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This script extracts the symbols of a given shared library
# into a file. If the symbols have not changed, the file is not
# touched. This information is used to skip link steps if the
# ABI has not changed.

# This file is basically a reimplementation of
# http://cgit.freedesktop.org/libreoffice/core/commit/?id=3213cd54b76bc80a6f0516aac75a48ff3b2ad67c

import sys, subprocess, platform
import argparse

parser = argparse.ArgumentParser()

parser.add_argument('--cross-host', default=None, dest='cross_host',
                    help='cross compilation host platform')
parser.add_argument('args', nargs='+')

def dummy_syms(outfilename):
    """Just touch it so relinking happens always."""
    open(outfilename, 'w').close()

def write_if_changed(text, outfilename):
    try:
        oldtext = open(outfilename, 'r').read()
        if text == oldtext:
            return
    except FileNotFoundError:
        pass
    open(outfilename, 'w').write(text)

def linux_syms(libfilename, outfilename):
    pe = subprocess.Popen(['readelf', '-d', libfilename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = pe.communicate()[0].decode()
    if pe.returncode != 0:
        raise RuntimeError('Readelf does not work')
    result = [x for x in output.split('\n') if 'SONAME' in x]
    assert(len(result) <= 1)
    pnm = subprocess.Popen(['nm', '--dynamic', '--extern-only', '--defined-only', '--format=posix', libfilename],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = pnm.communicate()[0].decode()
    if pnm.returncode != 0:
        raise RuntimeError('nm does not work.')
    result += [' '.join(x.split()[0:2]) for x in output.split('\n') if len(x) > 0]
    write_if_changed('\n'.join(result) + '\n', outfilename)

def osx_syms(libfilename, outfilename):
    pe = subprocess.Popen(['otool', '-l', libfilename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = pe.communicate()[0].decode()
    if pe.returncode != 0:
        raise RuntimeError('Otool does not work.')
    arr = output.split('\n')
    for (i, val) in enumerate(arr):
        if 'LC_ID_DYLIB' in val:
            match = i
            break
    result = [arr[match+2], arr[match+5]] # Libreoffice stores all 5 lines but the others seem irrelevant.
    pnm = subprocess.Popen(['nm', '-g', '-P', libfilename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = pnm.communicate()[0].decode()
    if pnm.returncode != 0:
        raise RuntimeError('nm does not work.')
    result += [' '.join(x.split()[0:2]) for x in output.split('\n') if len(x) > 0 and not x.endswith('U')]
    write_if_changed('\n'.join(result) + '\n', outfilename)

def gen_symbols(libfilename, outfilename, cross_host):
    if cross_host is not None:
        # In case of cross builds just always relink.
        # In theory we could determine the correct
        # toolset but there are more important things
        # to do.
        dummy_syms(outfilename)
    elif platform.system() == 'Linux':
        linux_syms(libfilename, outfilename)
    elif platform.system() == 'Darwin':
        osx_syms(libfilename, outfilename)
    else:
        dummy_syms(outfilename)

if __name__ == '__main__':
    options = parser.parse_args()
    if len(options.args) != 2:
        print(sys.argv[0], '<shared library file> <output file>')
        sys.exit(1)
    libfile = options.args[0]
    outfile = options.args[1]
    gen_symbols(libfile, outfile, options.cross_host)
