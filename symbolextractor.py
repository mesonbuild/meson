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

# This script extracts the symbols of a given shared library
# into a file. If the symbols have not changed, the file is not
# touched. This information is used to skip link steps if the
# ABI has not changed.

# This file is basically a reimplementation of
# http://cgit.freedesktop.org/libreoffice/core/commit/?id=3213cd54b76bc80a6f0516aac75a48ff3b2ad67c

import sys, subprocess, platform

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
    assert(len(result) == 1)
    pnm = subprocess.Popen(['nm', '--dynamic', '--extern-only', '--defined-only', '--format=posix', libfilename],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = pnm.communicate()[0].decode()
    if pnm.returncode != 0:
        raise RuntimeError('nm does not work.')
    result += [x.split()[0] for x in output.split('\n') if len(x) > 0]
    write_if_changed('\n'.join(result), outfilename)

def gen_symbols(libfilename, outfilename):
    if platform.system() == 'Linux':
        linux_syms(libfilename, outfilename)
    else:
        dummy_syms(outfilename)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(sys.argv[0], '<shared library file> <output file>')
        sys.exit(1)
    libfile = sys.argv[1]
    outfile = sys.argv[2]
    gen_symbols(libfile, outfile)
