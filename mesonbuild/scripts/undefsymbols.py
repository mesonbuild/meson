# Copyright 2013-2018 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This script extracts undefined symbols of a given library
# into a file. If the symbols have not changed, the file is not
# touched. This information is used to include functions from static
# libraries into the main program.

import sys
import argparse

parser = argparse.ArgumentParser()

parser.add_argument('--prefix', default='', dest='prefix', nargs=1,
                    help='string to place before the symbol name')
parser.add_argument('args', nargs='+')

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

def dummy_syms(outfilename):
    # Unlike symbolextractor.py, we want write_if_changed here.  That is
    # because if nm is not available, the output file will be unused, but
    # it will still be a dependency of the executable.  Using write_if_changed
    # avoids unnecessary relinking.
    write_if_changed('', outfilename)

def run(args):
    options = parser.parse_args(args)
    if len(options.args) < 2:
        print('undefsymbols.py <shared library file>... <output file> [--prefix <prefix>]')
        sys.exit(1)
    outfile = options.args[-1]
    dummy_syms(outfile)
    return 0

if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
