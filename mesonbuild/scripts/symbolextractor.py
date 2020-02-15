# Copyright 2013-2016 The Meson development team

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

import os, sys
from .. import mesonlib
from .. import mlog
from ..mesonlib import Popen_safe
import argparse

parser = argparse.ArgumentParser()

parser.add_argument('--cross-host', default=None, dest='cross_host',
                    help='cross compilation host platform')
parser.add_argument('args', nargs='+')

TOOL_WARNING_FILE = None
RELINKING_WARNING = 'Relinking will always happen on source changes.'

def dummy_syms(outfilename):
    """Just touch it so relinking happens always."""
    with open(outfilename, 'w'):
        pass

def write_if_changed(text, outfilename):
    try:
        with open(outfilename, 'r') as f:
            oldtext = f.read()
        if text == oldtext:
            return
    except FileNotFoundError:
        pass
    with open(outfilename, 'w') as f:
        f.write(text)

def linux_syms(libfilename, outfilename):
    evar = 'READELF'
    if evar in os.environ:
        readelfbin = os.environ[evar].strip()
    else:
        readelfbin = 'readelf'
    evar = 'NM'
    if evar in os.environ:
        nmbin = os.environ[evar].strip()
    else:
        nmbin = 'nm'
    pe, output = Popen_safe([readelfbin, '-d', libfilename])[0:2]
    if pe.returncode != 0:
        raise RuntimeError('Readelf does not work')
    result = [x for x in output.split('\n') if 'SONAME' in x]
    assert(len(result) <= 1)
    pnm, output = Popen_safe([nmbin, '--dynamic', '--extern-only',
                              '--defined-only', '--format=posix',
                              libfilename])[0:2]
    if pnm.returncode != 0:
        raise RuntimeError('nm does not work.')
    for line in output.split('\n'):
        if not line:
            continue
        line_split = line.split()
        entry = line_split[0:2]
        if len(line_split) >= 4:
            entry += [line_split[3]]
        result += [' '.join(entry)]
    write_if_changed('\n'.join(result) + '\n', outfilename)

def osx_syms(libfilename, outfilename):
    pe, output = Popen_safe(['otool', '-l', libfilename])[0:2]
    if pe.returncode != 0:
        raise RuntimeError('Otool does not work.')
    arr = output.split('\n')
    for (i, val) in enumerate(arr):
        if 'LC_ID_DYLIB' in val:
            match = i
            break
    result = [arr[match + 2], arr[match + 5]] # Libreoffice stores all 5 lines but the others seem irrelevant.
    pnm, output = Popen_safe(['nm', '-g', '-P', libfilename])[0:2]
    if pnm.returncode != 0:
        raise RuntimeError('nm does not work.')
    result += [' '.join(x.split()[0:2]) for x in output.split('\n') if x and not x.endswith('U')]
    write_if_changed('\n'.join(result) + '\n', outfilename)

def gen_symbols(libfilename, outfilename, cross_host):
    if cross_host is not None:
        # In case of cross builds just always relink. In theory we could
        # determine the correct toolset, but we would need to use the correct
        # `nm`, `readelf`, etc, from the cross info which requires refactoring.
        dummy_syms(outfilename)
    elif mesonlib.is_linux():
        linux_syms(libfilename, outfilename)
    elif mesonlib.is_osx():
        osx_syms(libfilename, outfilename)
    else:
        if not os.path.exists(TOOL_WARNING_FILE):
            mlog.warning('Symbol extracting has not been implemented for this '
                         'platform. ' + RELINKING_WARNING)
            # Write it out so we don't warn again
            with open(TOOL_WARNING_FILE, 'w'):
                pass
        dummy_syms(outfilename)

def run(args):
    global TOOL_WARNING_FILE
    options = parser.parse_args(args)
    if len(options.args) != 3:
        print('symbolextractor.py <shared library file> <output file>')
        sys.exit(1)
    privdir = os.path.join(options.args[0], 'meson-private')
    TOOL_WARNING_FILE = os.path.join(privdir, 'symbolextractor_tool_warning_printed')
    libfile = options.args[1]
    outfile = options.args[2]
    gen_symbols(libfile, outfile, options.cross_host)
    return 0

if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
