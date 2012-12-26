#!/usr/bin/python3 -tt

# Copyright 2012 Jussi Pakkanen

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from optparse import OptionParser
import sys, stat
import os.path

parser = OptionParser()

parser.add_option('--prefix', default='/usr/local', dest='prefix')
parser.add_option('--libdir', default='lib', dest='libdir')
parser.add_option('--includedir', default='include', dest='includedir')
parser.add_option('--datadir', default='share', dest='datadir')

class Builder():
    builder_filename = 'builder.txt'
    
    def __init__(self, dir1, dir2, options):
        (self.source_dir, self.build_dir) = self.validate_dirs(dir1, dir2)
    
    def has_builder_file(self, dirname):
        fname = os.path.join(dirname, Builder.builder_filename)
        try:
            ifile = open(fname, 'r')
            ifile.close()
            return True
        except IOError:
            return False

    def validate_dirs(self, dir1, dir2):
        ndir1 = os.path.abspath(dir1)
        ndir2 = os.path.abspath(dir2)
        if not stat.S_ISDIR(os.stat(ndir1).st_mode):
            raise RuntimeError('%s is not a directory' % dir1)
        if not stat.S_ISDIR(os.stat(ndir2).st_mode):
            raise RuntimeError('%s is not a directory' % dir2)
        self.options = options
        if ndir1 == ndir2:
            raise RuntimeError('Source and build directories must not be the same. Create a pristine build directory.')
        if self.has_builder_file(ndir1):
            if self.has_builder_file(ndir2):
                raise RuntimeError('Both directories contain a builder file %s.' % Builder.builder_filename)
            return (ndir1, ndir2)
        if self.has_builder_file(ndir2):
            return (ndir2, ndir1)
        raise RuntimeError('Neither directory contains a builder file %s.' % Builder.builder_filename)

if __name__ == '__main__':
    (options, args) = parser.parse_args(sys.argv)
    if len(args) == 1 or len(args) > 3:
        print('Invalid number of arguments')
        sys.exit(1)
    dir1 = args[1]
    if len(args) > 2:
        dir2 = args[2]
    else:
        dir2 = '.'
    builder = Builder(dir1, dir2, options)
    print ('Source dir: ' + builder.source_dir)
    print ('Build dir: ' + builder.build_dir)
