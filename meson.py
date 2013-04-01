#!/usr/bin/env python3

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
import sys, stat, traceback
import os.path
import environment, interpreter
import backends, build

from coredata import version, MesonException

usage_info = '%prog [options] source_dir build_dir'

parser = OptionParser(usage=usage_info, version=version)

build_types = ['plain', 'debug', 'optimized']
buildtype_help = 'build type, one of: %s' % ', '.join(build_types)
buildtype_help += ' (default: %default)'

if environment.is_windows():
    def_prefix = 'c:/'
else:
    def_prefix = '/usr/local'

parser.add_option('--prefix', default=def_prefix, dest='prefix',
                  help='the installation prefix (default: %default)')
parser.add_option('--libdir', default='lib', dest='libdir',
                  help='the installation subdir of libraries (default: %default)')
parser.add_option('--bindir', default='bin', dest='bindir',
                  help='the installation subdir of executables (default: %default)')
parser.add_option('--includedir', default='include', dest='includedir',
                  help='relative path of installed headers (default: %default)')
parser.add_option('--datadir', default='share', dest='datadir',
                  help='relative path to the top of data file subdirectory (default: %default)')
parser.add_option('--mandir' , default='share/man', dest='mandir',
                  help='relatie path of man files (default: %default)')
parser.add_option('--backend', default='ninja', dest='backend',
                  help='the backend to use (default: %default)')
parser.add_option('--buildtype', default='debug', type='choice', choices=build_types, dest='buildtype',
                  help=buildtype_help)
parser.add_option('--strip', action='store_true', dest='strip', default=False,\
                  help='strip targets on install (default: %default)')
parser.add_option('--enable-gcov', action='store_true', dest='coverage', default=False,\
                  help='measure test coverage')

class MesonApp():

    def __init__(self, dir1, dir2, script_file, options):
        (self.source_dir, self.build_dir) = self.validate_dirs(dir1, dir2)
        if not os.path.isabs(options.prefix):
            raise RuntimeError('--prefix must be an absolute path.')
        self.meson_script_file = script_file
        self.options = options
    
    def has_build_file(self, dirname):
        fname = os.path.join(dirname, environment.build_filename)
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
        if self.has_build_file(ndir1):
            if self.has_build_file(ndir2):
                raise RuntimeError('Both directories contain a build file %s.' % environment.build_filename)
            return (ndir1, ndir2)
        if self.has_build_file(ndir2):
            return (ndir2, ndir1)
        raise RuntimeError('Neither directory contains a build file %s.' % environment.build_filename)
    
    def generate(self):
        env = environment.Environment(self.source_dir, self.build_dir, self.meson_script_file, options)
        b = build.Build(env)
        intr = interpreter.Interpreter(b)
        intr.run()
        if options.backend == 'ninja':
            g = backends.NinjaBackend(b, intr)
        else:
            raise RuntimeError('Unknown backend "%s".' % options.backend)
        g.generate()
        env.generating_finished()

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
    this_file = os.path.abspath(__file__)
    while os.path.islink(this_file):
        resolved = os.readlink(this_file)
        if resolved[0] != '/':
            this_file = os.path.join(os.path.dirname(this_file), resolved)
        else:
            this_file = resolved 
    app = MesonApp(dir1, dir2, this_file, options)
    print ('Source dir: ' + app.source_dir)
    print ('Build dir: ' + app.build_dir)
    try:
        app.generate()
    except Exception as e:
        if isinstance(e, MesonException):
            print('\nMeson encountered an error:')
            print(e)
            sys.exit(1)
        else:
            traceback.print_exc()

