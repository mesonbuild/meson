# Copyright 2012-2016 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys, stat, traceback, pickle, argparse
import time, datetime
import os.path
from . import environment, interpreter, mesonlib
from . import build
import platform
from . import mlog, coredata
from .mesonlib import MesonException
from .wrap import WrapMode


parser = argparse.ArgumentParser()

default_warning = '1'

def add_builtin_argument(name, **kwargs):
    k = kwargs.get('dest', name.replace('-', '_'))
    c = coredata.get_builtin_option_choices(k)
    b = True if kwargs.get('action', None) in ['store_true', 'store_false'] else False
    h = coredata.get_builtin_option_description(k)
    if not b:
        h = h.rstrip('.') + ' (default: %s).' % coredata.get_builtin_option_default(k)
    if c and not b:
        kwargs['choices'] = c
    parser.add_argument('--' + name, default=coredata.get_builtin_option_default(k), help=h, **kwargs)

add_builtin_argument('prefix')
add_builtin_argument('libdir')
add_builtin_argument('libexecdir')
add_builtin_argument('bindir')
add_builtin_argument('sbindir')
add_builtin_argument('includedir')
add_builtin_argument('datadir')
add_builtin_argument('mandir')
add_builtin_argument('infodir')
add_builtin_argument('localedir')
add_builtin_argument('sysconfdir')
add_builtin_argument('localstatedir')
add_builtin_argument('sharedstatedir')
add_builtin_argument('backend')
add_builtin_argument('buildtype')
add_builtin_argument('strip', action='store_true')
add_builtin_argument('unity')
add_builtin_argument('werror', action='store_true')
add_builtin_argument('layout')
add_builtin_argument('default-library')
add_builtin_argument('warnlevel', dest='warning_level')
add_builtin_argument('stdsplit', action='store_false')
add_builtin_argument('errorlogs', action='store_false')

parser.add_argument('--cross-file', default=None,
                    help='File describing cross compilation environment.')
parser.add_argument('-D', action='append', dest='projectoptions', default=[], metavar="option",
                    help='Set the value of an option, can be used several times to set multiple options.')
parser.add_argument('-v', '--version', action='version',
                    version=coredata.version)
# See the mesonlib.WrapMode enum for documentation
parser.add_argument('--wrap-mode', default=WrapMode.default,
                    type=lambda t: getattr(WrapMode, t), choices=WrapMode,
                    help='Special wrap mode to use')
parser.add_argument('directories', nargs='*')

class MesonApp:

    def __init__(self, dir1, dir2, script_launcher, handshake, options, original_cmd_line_args):
        (self.source_dir, self.build_dir) = self.validate_dirs(dir1, dir2, handshake)
        self.meson_script_launcher = script_launcher
        self.options = options
        self.original_cmd_line_args = original_cmd_line_args

    def has_build_file(self, dirname):
        fname = os.path.join(dirname, environment.build_filename)
        return os.path.exists(fname)

    def validate_core_dirs(self, dir1, dir2):
        ndir1 = os.path.abspath(os.path.realpath(dir1))
        ndir2 = os.path.abspath(os.path.realpath(dir2))
        if not os.path.exists(ndir1):
            os.makedirs(ndir1)
        if not os.path.exists(ndir2):
            os.makedirs(ndir2)
        if not stat.S_ISDIR(os.stat(ndir1).st_mode):
            raise RuntimeError('%s is not a directory' % dir1)
        if not stat.S_ISDIR(os.stat(ndir2).st_mode):
            raise RuntimeError('%s is not a directory' % dir2)
        if os.path.samefile(dir1, dir2):
            raise RuntimeError('Source and build directories must not be the same. Create a pristine build directory.')
        if self.has_build_file(ndir1):
            if self.has_build_file(ndir2):
                raise RuntimeError('Both directories contain a build file %s.' % environment.build_filename)
            return ndir1, ndir2
        if self.has_build_file(ndir2):
            return ndir2, ndir1
        raise RuntimeError('Neither directory contains a build file %s.' % environment.build_filename)

    def validate_dirs(self, dir1, dir2, handshake):
        (src_dir, build_dir) = self.validate_core_dirs(dir1, dir2)
        priv_dir = os.path.join(build_dir, 'meson-private/coredata.dat')
        if os.path.exists(priv_dir):
            if not handshake:
                msg = '''Trying to run Meson on a build directory that has already been configured.
If you want to build it, just run your build command (e.g. ninja) inside the
build directory. Meson will autodetect any changes in your setup and regenerate
itself as required.

If you want to change option values, use the mesonconf tool instead.'''
                raise RuntimeError(msg)
        else:
            if handshake:
                raise RuntimeError('Something went terribly wrong. Please file a bug.')
        return src_dir, build_dir

    def check_pkgconfig_envvar(self, env):
        curvar = os.environ.get('PKG_CONFIG_PATH', '')
        if curvar != env.coredata.pkgconf_envvar:
            mlog.warning('PKG_CONFIG_PATH has changed between invocations from "%s" to "%s".' %
                         (env.coredata.pkgconf_envvar, curvar))
            env.coredata.pkgconf_envvar = curvar

    def generate(self):
        env = environment.Environment(self.source_dir, self.build_dir, self.meson_script_launcher, self.options, self.original_cmd_line_args)
        mlog.initialize(env.get_log_dir())
        mlog.debug('Build started at', datetime.datetime.now().isoformat())
        mlog.debug('Python binary:', sys.executable)
        mlog.debug('Python system:', platform.system())
        mlog.log(mlog.bold('The Meson build system'))
        self.check_pkgconfig_envvar(env)
        mlog.log('Version:', coredata.version)
        mlog.log('Source dir:', mlog.bold(self.source_dir))
        mlog.log('Build dir:', mlog.bold(self.build_dir))
        if env.is_cross_build():
            mlog.log('Build type:', mlog.bold('cross build'))
        else:
            mlog.log('Build type:', mlog.bold('native build'))
        b = build.Build(env)
        if self.options.backend == 'ninja':
            from .backend import ninjabackend
            g = ninjabackend.NinjaBackend(b)
        elif self.options.backend == 'vs':
            from .backend import vs2010backend
            g = vs2010backend.autodetect_vs_version(b)
            mlog.log('Auto detected Visual Studio backend:', mlog.bold(g.name))
        elif self.options.backend == 'vs2010':
            from .backend import vs2010backend
            g = vs2010backend.Vs2010Backend(b)
        elif self.options.backend == 'vs2015':
            from .backend import vs2015backend
            g = vs2015backend.Vs2015Backend(b)
        elif self.options.backend == 'vs2017':
            from .backend import vs2017backend
            g = vs2017backend.Vs2017Backend(b)
        elif self.options.backend == 'xcode':
            from .backend import xcodebackend
            g = xcodebackend.XCodeBackend(b)
        else:
            raise RuntimeError('Unknown backend "%s".' % self.options.backend)

        intr = interpreter.Interpreter(b, g)
        if env.is_cross_build():
            mlog.log('Host machine cpu family:', mlog.bold(intr.builtin['host_machine'].cpu_family_method([], {})))
            mlog.log('Host machine cpu:', mlog.bold(intr.builtin['host_machine'].cpu_method([], {})))
            mlog.log('Target machine cpu family:', mlog.bold(intr.builtin['target_machine'].cpu_family_method([], {})))
            mlog.log('Target machine cpu:', mlog.bold(intr.builtin['target_machine'].cpu_method([], {})))
        mlog.log('Build machine cpu family:', mlog.bold(intr.builtin['build_machine'].cpu_family_method([], {})))
        mlog.log('Build machine cpu:', mlog.bold(intr.builtin['build_machine'].cpu_method([], {})))
        intr.run()
        coredata_mtime = time.time()
        g.generate(intr)
        g.run_postconf_scripts()
        dumpfile = os.path.join(env.get_scratch_dir(), 'build.dat')
        with open(dumpfile, 'wb') as f:
            pickle.dump(b, f)
        # Write this last since we use the existence of this file to check if
        # we generated the build file successfully, so we don't want an error
        # that pops up during generation, post-conf scripts, etc to cause us to
        # incorrectly signal a successful meson run which will cause an error
        # about an already-configured build directory when the user tries again.
        #
        # However, we set the mtime to an earlier value to ensure that doing an
        # mtime comparison between the coredata dump and other build files
        # shows the build files to be newer, not older.
        env.dump_coredata(coredata_mtime)

def run_script_command(args):
    cmdname = args[0]
    cmdargs = args[1:]
    if cmdname == 'exe':
        import mesonbuild.scripts.meson_exe as abc
        cmdfunc = abc.run
    elif cmdname == 'cleantrees':
        import mesonbuild.scripts.cleantrees as abc
        cmdfunc = abc.run
    elif cmdname == 'install':
        import mesonbuild.scripts.meson_install as abc
        cmdfunc = abc.run
    elif cmdname == 'commandrunner':
        import mesonbuild.scripts.commandrunner as abc
        cmdfunc = abc.run
    elif cmdname == 'delsuffix':
        import mesonbuild.scripts.delwithsuffix as abc
        cmdfunc = abc.run
    elif cmdname == 'depfixer':
        import mesonbuild.scripts.depfixer as abc
        cmdfunc = abc.run
    elif cmdname == 'dirchanger':
        import mesonbuild.scripts.dirchanger as abc
        cmdfunc = abc.run
    elif cmdname == 'gtkdoc':
        import mesonbuild.scripts.gtkdochelper as abc
        cmdfunc = abc.run
    elif cmdname == 'msgfmthelper':
        import mesonbuild.scripts.msgfmthelper as abc
        cmdfunc = abc.run
    elif cmdname == 'regencheck':
        import mesonbuild.scripts.regen_checker as abc
        cmdfunc = abc.run
    elif cmdname == 'symbolextractor':
        import mesonbuild.scripts.symbolextractor as abc
        cmdfunc = abc.run
    elif cmdname == 'scanbuild':
        import mesonbuild.scripts.scanbuild as abc
        cmdfunc = abc.run
    elif cmdname == 'vcstagger':
        import mesonbuild.scripts.vcstagger as abc
        cmdfunc = abc.run
    elif cmdname == 'gettext':
        import mesonbuild.scripts.gettext as abc
        cmdfunc = abc.run
    elif cmdname == 'yelphelper':
        import mesonbuild.scripts.yelphelper as abc
        cmdfunc = abc.run
    elif cmdname == 'uninstall':
        import mesonbuild.scripts.uninstall as abc
        cmdfunc = abc.run
    elif cmdname == 'dist':
        import mesonbuild.scripts.dist as abc
        cmdfunc = abc.run
    elif cmdname == 'coverage':
        import mesonbuild.scripts.coverage as abc
        cmdfunc = abc.run
    else:
        raise MesonException('Unknown internal command {}.'.format(cmdname))
    return cmdfunc(cmdargs)

def run(mainfile, args):
    if sys.version_info < (3, 3):
        print('Meson works correctly only with python 3.3+.')
        print('You have python %s.' % sys.version)
        print('Please update your environment')
        return 1
    if len(args) >= 2 and args[0] == '--internal':
        if args[1] != 'regenerate':
            script = args[1]
            try:
                sys.exit(run_script_command(args[1:]))
            except MesonException as e:
                mlog.log(mlog.red('\nError in {} helper script:'.format(script)))
                mlog.log(e)
                sys.exit(1)
        args = args[2:]
        handshake = True
    else:
        handshake = False
    args = mesonlib.expand_arguments(args)
    options = parser.parse_args(args)
    args = options.directories
    if not args or len(args) > 2:
        # if there's a meson.build in the dir above, and not in the current
        # directory, assume we're in the build directory
        if not args and not os.path.exists('meson.build') and os.path.exists('../meson.build'):
            dir1 = '..'
            dir2 = '.'
        else:
            print('{} <source directory> <build directory>'.format(sys.argv[0]))
            print('If you omit either directory, the current directory is substituted.')
            print('Run {} --help for more information.'.format(sys.argv[0]))
            return 1
    else:
        dir1 = args[0]
        if len(args) > 1:
            dir2 = args[1]
        else:
            dir2 = '.'
    try:
        app = MesonApp(dir1, dir2, mainfile, handshake, options, sys.argv)
    except Exception as e:
        # Log directory does not exist, so just print
        # to stdout.
        print('Error during basic setup:\n')
        print(e)
        return 1
    try:
        app.generate()
    except Exception as e:
        if isinstance(e, MesonException):
            if hasattr(e, 'file') and hasattr(e, 'lineno') and hasattr(e, 'colno'):
                mlog.log(mlog.red('\nMeson encountered an error in file %s, line %d, column %d:' % (e.file, e.lineno, e.colno)))
            else:
                mlog.log(mlog.red('\nMeson encountered an error:'))
            mlog.log(e)
            if os.environ.get('MESON_FORCE_BACKTRACE'):
                raise
        else:
            if os.environ.get('MESON_FORCE_BACKTRACE'):
                raise
            traceback.print_exc()
        return 1
    return 0
