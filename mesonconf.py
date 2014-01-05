#!/usr/bin/env python3

# Copyright 2014 Jussi Pakkanen

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys, os
from optparse import OptionParser
import coredata

usage_info = '%prog [build dir]'

parser = OptionParser(usage=usage_info, version=coredata.version)

class ConfException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class Conf:
    def __init__(self, build_dir):
        self.build_dir = build_dir
        self.coredata_file = os.path.join(build_dir, 'meson-private/coredata.dat')
        self.build_file = os.path.join(build_dir, 'meson-private/build.dat')
        if not os.path.isfile(self.coredata_file) or not os.path.isfile(self.build_file):
            raise ConfException('Directory %s does not seem to be a Meson build directory.' % build_dir)

if __name__ == '__main__':
    (options, args) = parser.parse_args(sys.argv)
    if len(args) > 2:
        print(args)
        print('%s <build directory>' % sys.argv[0])
        print('If you omit build directory, the current directory is substituted.')
        sys.exit(1)
    if len(args) == 1:
        builddir = os.getcwd()
    else:
        builddir = args[-1]
    try:
        c = Conf(builddir)
    except ConfException as e:
        print('Meson configurator encountered an error:\n')
        print(e)

