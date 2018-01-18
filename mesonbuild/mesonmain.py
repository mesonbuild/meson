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
from . import mconf, mintro, mtest, rewriter, minit
import platform
from . import mlog, coredata
from .mesonlib import MesonException
from .wrap import WrapMode, wraptool

default_warning = '1'

def add_builtin_argument(p, name, **kwargs):
    k = kwargs.get('dest', name.replace('-', '_'))
    c = coredata.get_builtin_option_choices(k)
    b = kwargs.get('action', None) in ['store_true', 'store_false']
    h = coredata.get_builtin_option_description(k)
    if not b:
        h = h.rstrip('.') + ' (default: %s).' % coredata.get_builtin_option_default(k)
    if c and not b:
        kwargs['choices'] = c
    default = coredata.get_builtin_option_default(k, noneIfSuppress=True)
    if default is not None:
        kwargs['default'] = default
    else:
        kwargs['default'] = argparse.SUPPRESS
    p.add_argument('--' + name, help=h, **kwargs)

def create_parser():
    p = argparse.ArgumentParser(prog='meson')
    add_builtin_argument(p, 'prefix')
    add_builtin_argument(p, 'libdir')
    add_builtin_argument(p, 'libexecdir')
    add_builtin_argument(p, 'bindir')
    add_builtin_argument(p, 'sbindir')
    add_builtin_argument(p, 'includedir')
    add_builtin_argument(p, 'datadir')
    add_builtin_argument(p, 'mandir')
    add_builtin_argument(p, 'infodir')
    add_builtin_argument(p, 'localedir')
    add_builtin_argument(p, 'sysconfdir')
    add_builtin_argument(p, 'localstatedir')
    add_builtin_argument(p, 'sharedstatedir')
    add_builtin_argument(p, 'backend')
    add_builtin_argument(p, 'buildtype')
    add_builtin_argument(p, 'strip', action='store_true')
    add_builtin_argument(p, 'unity')
    add_builtin_argument(p, 'werror', action='store_true')
    add_builtin_argument(p, 'layout')
    add_builtin_argument(p, 'default-library')
    add_builtin_argument(p, 'warnlevel', dest='warning_level')
    add_builtin_argument(p, 'stdsplit', action='store_false')
    add_builtin_argument(p, 'errorlogs', action='store_false')
    p.add_argument('--cross-file', default=None,
                   help='File describing cross compilation environment.')
    p.add_argument('-D', action='append', dest='projectoptions', default=[], metavar="option",
                   help='Set the value of an option, can be used several times to set multiple options.')
    p.add_argument('-v', '--version', action='version',
                   version=coredata.version)
    # See the mesonlib.WrapMode enum for documentation
    p.add_argument('--wrap-mode', default=WrapMode.default,
                   type=wrapmodetype, choices=WrapMode,
                   help='Special wrap mode to use')
    p.add_argument('directories', nargs='*')
    return p

def wrapmodetype(string):
    try:
        return getattr(WrapMode, string)
    except AttributeError:
        msg = ', '.join([t.name.lower() for t in WrapMode])
        msg = 'invalid argument {!r}, use one of {}'.format(string, msg)
        raise argparse.ArgumentTypeError(msg)

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
                print('Directory already configured, exiting Meson. Just run your build command\n'
                      '(e.g. ninja) and Meson will regenerate as necessary. If ninja fails, run ninja\n'
                      'reconfigure to force Meson to regenerate.\n'
                      '\nIf build failures persist, manually wipe your build directory to clear any\n'
                      'stored system data.\n'
                      '\nTo change option values, run meson configure instead.')
                sys.exit(0)
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
        try:
            self._generate(env)
        finally:
            mlog.shutdown()

    def _generate(self, env):
        mlog.debug('Build started at', datetime.datetime.now().isoformat())
        mlog.debug('Main binary:', sys.executable)
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
            env.coredata.set_builtin_option('backend', g.name)
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
        try:
            # We would like to write coredata as late as possible since we use the existence of
            # this file to check if we generated the build file successfully. Since coredata
            # includes settings, the build files must depend on it and appear newer. However, due
            # to various kernel caches, we cannot guarantee that any time in Python is exactly in
            # sync with the time that gets applied to any files. Thus, we dump this file as late as
            # possible, but before build files, and if any error occurs, delete it.
            cdf = env.dump_coredata()
            g.generate(intr)
            dumpfile = os.path.join(env.get_scratch_dir(), 'build.dat')
            with open(dumpfile, 'wb') as f:
                pickle.dump(b, f)
            # Post-conf scripts must be run after writing coredata or else introspection fails.
            g.run_postconf_scripts()
        except:
            os.unlink(cdf)
            raise


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

def run(original_args, mainfile=None):
    if sys.version_info < (3, 5):
        print('Meson works correctly only with python 3.5+.')
        print('You have python %s.' % sys.version)
        print('Please update your environment')
        return 1
    args = original_args[:]
    if len(args) > 0:
        # First check if we want to run a subcommand.
        cmd_name = args[0]
        remaining_args = args[1:]
        if cmd_name == 'test':
            return mtest.run(remaining_args)
        elif cmd_name == 'setup':
            args = remaining_args
            # FALLTHROUGH like it's 1972.
        elif cmd_name == 'introspect':
            return mintro.run(remaining_args)
        elif cmd_name == 'rewrite':
            return rewriter.run(remaining_args)
        elif cmd_name == 'configure':
            try:
                return mconf.run(remaining_args)
            except MesonException as e:
                mlog.log(mlog.red('\nError configuring project:'), e)
                sys.exit(1)
        elif cmd_name == 'wrap':
            return wraptool.run(remaining_args)
        elif cmd_name == 'init':
            return minit.run(remaining_args)
        elif cmd_name == 'runpython':
            import runpy
            script_file = remaining_args[0]
            sys.argv[1:] = remaining_args[1:]
            runpy.run_path(script_file, run_name='__main__')
            sys.exit(0)

    # No special command? Do the basic setup/reconf.
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

    parser = create_parser()

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
        if mainfile is None:
            raise AssertionError('I iz broken. Sorry.')
        app = MesonApp(dir1, dir2, mainfile, handshake, options, original_args)
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
            # Error message
            mlog.log(e)
            # Path to log file
            logfile = os.path.join(app.build_dir, environment.Environment.log_dir, mlog.log_fname)
            mlog.log("\nA full log can be found at", mlog.bold(logfile))
            if os.environ.get('MESON_FORCE_BACKTRACE'):
                raise
        else:
            if os.environ.get('MESON_FORCE_BACKTRACE'):
                raise
            traceback.print_exc()
        return 1
    return 0
