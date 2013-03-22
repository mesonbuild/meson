#!/usr/bin/env python3 -tt

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

import sys, subprocess
from optparse import OptionParser

parser = OptionParser()
parser.add_option('--wrapper', default=None, dest='wrapper',
                  help='wrapper to run tests (e.g. valgrind')


def run_tests(options, datafilename):
    if options.wrapper is None:
        wrap = []
    else:
        wrap = [options.wrapper]
    for line in open(datafilename, 'r'):
        line = line.strip()
        if line == '':
            continue
        cmd = wrap + [line]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdo, stde) = p.communicate()
        if p.returncode != 0:
            print('Error running test.')
            print('Stdout:\n' + stdo.decode())
            print('Stderr:\n' + stde.decode())
            sys.exit(1)
        print('Test "%s": OK' % line)

if __name__ == '__main__':
    (options, args) = parser.parse_args(sys.argv)
    if len(args) != 2:
        print('Test runner for Meson. Do not run on your own, mmm\'kay?')
        print('%s [data file]' % sys.argv[0])
    datafile = args[1]
    run_tests(options, datafile)
