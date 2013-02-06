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
import environment, interpreter
import generators, build

parser = OptionParser()

parser.add_option('--prefix', default='/usr/local', dest='prefix')
parser.add_option('--libdir', default='lib', dest='libdir')
parser.add_option('--bindir', default='bin', dest='bindir')
parser.add_option('--includedir', default='include', dest='includedir')
parser.add_option('--datadir', default='share', dest='datadir')
parser.add_option('--mandir' , default='share/man', dest='mandir')

class BuilderApp():

    def __init__(self, dir1, dir2, options):
        (self.source_dir, self.build_dir) = self.validate_dirs(dir1, dir2)
        if options.prefix[0] != '/':
            raise RuntimeError('--prefix must be an absolute path.')
        self.options = options
    
    def has_builder_file(self, dirname):
        fname = os.path.join(dirname, environment.builder_filename)
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
        if os.path.samefile(dir1, dir2):
            raise RuntimeError('Source and build directories must not be the same. Create a pristine build directory.')
        if self.has_builder_file(ndir1):
            if self.has_builder_file(ndir2):
                raise RuntimeError('Both directories contain a builder file %s.' % environment.builder_filename)
            return (ndir1, ndir2)
        if self.has_builder_file(ndir2):
            return (ndir2, ndir1)
        raise RuntimeError('Neither directory contains a builder file %s.' % environment.builder_filename)
    
    def generate(self):
        code = open(os.path.join(self.source_dir, environment.builder_filename)).read()
        if len(code.strip()) == 0:
            raise interpreter.InvalidCode('Builder file is empty.')
        assert(isinstance(code, str))
        env = environment.Environment(self.source_dir, self.build_dir, options)
        b = build.Build(env)
        intr = interpreter.Interpreter(code, b)
        intr.run()
        g = generators.ShellGenerator(b, intr)
        g.generate()

if __name__ == '__main__':
    (options, args) = parser.parse_args(sys.argv)
    if len(args) == 1 or len(args) > 3:
        print('%s <source directory> <build directory>' % sys.argv[0])
        print('If you omit either directory, the current directory is substituted.')
        sys.exit(1)
    dir1 = args[1]
    if len(args) > 2:
        dir2 = args[2]
    else:
        dir2 = '.'
    builder = BuilderApp(dir1, dir2, options)
    print ('Source dir: ' + builder.source_dir)
    print ('Build dir: ' + builder.build_dir)
    builder.generate()

