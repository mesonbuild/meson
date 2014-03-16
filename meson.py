#!/usr/bin/env python3

# Copyright 2012-2014 Jussi Pakkanen

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
import sys, stat, traceback, pickle
import os.path
import environment, interpreter
import backends, build
import mlog, coredata

from coredata import MesonException

usage_info = '%prog [options] source_dir build_dir'

parser = OptionParser(usage=usage_info, version=coredata.version)

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
                  help='relative path of man files (default: %default)')
parser.add_option('--localedir', default='share/locale', dest='localedir',
                  help='relative path of locale data (default: %default)')
parser.add_option('--backend', default='ninja', dest='backend',
                  help='the backend to use (default: %default)')
parser.add_option('--buildtype', default='debug', type='choice', choices=build_types, dest='buildtype',
                  help=buildtype_help)
parser.add_option('--strip', action='store_true', dest='strip', default=False,\
                  help='strip targets on install (default: %default)')
parser.add_option('--enable-gcov', action='store_true', dest='coverage', default=False,\
                  help='measure test coverage')
parser.add_option('--disable-pch', action='store_false', dest='use_pch', default=True,\
                  help='do not use precompiled headers')
parser.add_option('--unity', action='store_true', dest='unity', default=False,\
                  help='unity build')
parser.add_option('--cross-file', default=None, dest='cross_file',
                  help='file describing cross compilation environment')

class MesonApp():

    def __init__(self, dir1, dir2, script_file, handshake, options):
        (self.source_dir, self.build_dir) = self.validate_dirs(dir1, dir2, handshake)
        if not os.path.isabs(options.prefix):
            raise RuntimeError('--prefix must be an absolute path.')
        self.meson_script_file = script_file
        self.options = options
    
    def has_build_file(self, dirname):
        fname = os.path.join(dirname, environment.build_filename)
        return os.path.exists(fname)

    def validate_core_dirs(self, dir1, dir2):
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

    def validate_dirs(self, dir1, dir2, handshake):
        (src_dir, build_dir) = self.validate_core_dirs(dir1, dir2)
        priv_dir = os.path.join(build_dir, 'meson-private/coredata.dat')
        if os.path.exists(priv_dir):
            if not handshake:
                msg = '''Trying to run Meson on a build directory that has already been configured.
If you want to build it, just run your build command (e.g. ninja) inside the
build directory. Meson will autodetect any changes in your setup and regenerate
itself as required.'''
                raise RuntimeError(msg)
        else:
            if handshake:
                raise RuntimeError('Something went terribly wrong. Please file a bug.')
        return (src_dir, build_dir)

    def generate(self):
        env = environment.Environment(self.source_dir, self.build_dir, self.meson_script_file, options)
        mlog.initialize(env.get_log_dir())
        mlog.log(mlog.bold('The Meson build system'))
        mlog.log(' version:', coredata.version)
        mlog.log('Source dir:', mlog.bold(app.source_dir))
        mlog.log('Build dir:', mlog.bold(app.build_dir))
        if env.is_cross_build():
            mlog.log('Build type:', mlog.bold('cross build'))
        else:
            mlog.log('Build type:', mlog.bold('native build'))
        b = build.Build(env)
        intr = interpreter.Interpreter(b)
        intr.run()
        if options.backend == 'ninja':
            g = backends.NinjaBackend(b, intr)
        else:
            raise RuntimeError('Unknown backend "%s".' % options.backend)
        g.generate()
        env.generating_finished()
        dumpfile = os.path.join(env.get_scratch_dir(), 'build.dat')
        pickle.dump(b, open(dumpfile, 'wb'))

if __name__ == '__main__':
    (options, args) = parser.parse_args(sys.argv)
    if args[-1] == 'secret-handshake':
        args = args[:-1]
        handshake = True
    else:
        handshake = False
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
    try:
        app = MesonApp(dir1, dir2, this_file, handshake, options)
    except Exception as e:
        # Log directory does not exist, so just print
        # to stdout.
        print('Error during basic setup:\n')
        print(e)
        sys.exit(1)
    try:
        app.generate()
    except Exception as e:
        if isinstance(e, MesonException):
            if hasattr(e, 'file') and hasattr(e, 'lineno') and hasattr(e, 'colno'):
                mlog.log(mlog.red('\nMeson encountered an error in %s:%d,%d:' % (e.file, e.lineno, e.colno)))
            else:
                mlog.log(mlog.red('\nMeson encountered an error:'))
            mlog.log(e)
        else:
            traceback.print_exc()
        sys.exit(1)

