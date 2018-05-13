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

import time
import sys, stat, traceback, argparse
import datetime
import os.path
import platform
import cProfile as profile

from . import environment, interpreter, mesonlib
from . import build
from . import mlog, coredata
from .mesonlib import MesonException
from .environment import detect_msys2_arch
from .wrap import WrapMode

default_warning = '1'

def create_parser():
    p = argparse.ArgumentParser(prog='meson')
    coredata.register_builtin_arguments(p)
    p.add_argument('--cross-file', default=None,
                   help='File describing cross compilation environment.')
    p.add_argument('-v', '--version', action='version',
                   version=coredata.version)
    # See the mesonlib.WrapMode enum for documentation
    p.add_argument('--wrap-mode', default=None,
                   type=wrapmodetype, choices=WrapMode,
                   help='Special wrap mode to use')
    p.add_argument('--profile-self', action='store_true', dest='profile',
                   help=argparse.SUPPRESS)
    p.add_argument('--fatal-meson-warnings', action='store_true', dest='fatal_warnings',
                   help='Make all Meson warnings fatal')
    p.add_argument('--reconfigure', action='store_true',
                   help='Set options and reconfigure the project. Useful when new ' +
                        'options have been added to the project and the default value ' +
                        'is not working.')
    p.add_argument('builddir', nargs='?', default=None)
    p.add_argument('sourcedir', nargs='?', default=None)
    return p

def wrapmodetype(string):
    try:
        return getattr(WrapMode, string)
    except AttributeError:
        msg = ', '.join([t.name.lower() for t in WrapMode])
        msg = 'invalid argument {!r}, use one of {}'.format(string, msg)
        raise argparse.ArgumentTypeError(msg)

class MesonApp:

    def __init__(self, options):
        (self.source_dir, self.build_dir) = self.validate_dirs(options.builddir,
                                                               options.sourcedir,
                                                               options.reconfigure)
        self.options = options

    def has_build_file(self, dirname):
        fname = os.path.join(dirname, environment.build_filename)
        return os.path.exists(fname)

    def validate_core_dirs(self, dir1, dir2):
        if dir1 is None:
            if dir2 is None:
                if not os.path.exists('meson.build') and os.path.exists('../meson.build'):
                    dir2 = '..'
                else:
                    raise MesonException('Must specify at least one directory name.')
            dir1 = os.getcwd()
        if dir2 is None:
            dir2 = os.getcwd()
        ndir1 = os.path.abspath(os.path.realpath(dir1))
        ndir2 = os.path.abspath(os.path.realpath(dir2))
        if not os.path.exists(ndir1):
            os.makedirs(ndir1)
        if not os.path.exists(ndir2):
            os.makedirs(ndir2)
        if not stat.S_ISDIR(os.stat(ndir1).st_mode):
            raise MesonException('%s is not a directory' % dir1)
        if not stat.S_ISDIR(os.stat(ndir2).st_mode):
            raise MesonException('%s is not a directory' % dir2)
        if os.path.samefile(dir1, dir2):
            raise MesonException('Source and build directories must not be the same. Create a pristine build directory.')
        if self.has_build_file(ndir1):
            if self.has_build_file(ndir2):
                raise MesonException('Both directories contain a build file %s.' % environment.build_filename)
            return ndir1, ndir2
        if self.has_build_file(ndir2):
            return ndir2, ndir1
        raise MesonException('Neither directory contains a build file %s.' % environment.build_filename)

    def validate_dirs(self, dir1, dir2, reconfigure):
        (src_dir, build_dir) = self.validate_core_dirs(dir1, dir2)
        priv_dir = os.path.join(build_dir, 'meson-private/coredata.dat')
        if os.path.exists(priv_dir):
            if not reconfigure:
                print('Directory already configured.\n'
                      '\nJust run your build command (e.g. ninja) and Meson will regenerate as necessary.\n'
                      'If ninja fails, run "ninja reconfigure" or "meson --reconfigure"\n'
                      'to force Meson to regenerate.\n'
                      '\nIf build failures persist, manually wipe your build directory to clear any\n'
                      'stored system data.\n'
                      '\nTo change option values, run "meson configure" instead.')
                sys.exit(1)
        else:
            if reconfigure:
                print('Directory does not contain a valid build tree:\n{}'.format(build_dir))
                sys.exit(1)
        return src_dir, build_dir

    def check_pkgconfig_envvar(self, env):
        curvar = os.environ.get('PKG_CONFIG_PATH', '')
        if curvar != env.coredata.pkgconf_envvar:
            mlog.warning('PKG_CONFIG_PATH has changed between invocations from "%s" to "%s".' %
                         (env.coredata.pkgconf_envvar, curvar))
            env.coredata.pkgconf_envvar = curvar

    def generate(self):
        env = environment.Environment(self.source_dir, self.build_dir, self.options)
        mlog.initialize(env.get_log_dir(), self.options.fatal_warnings)
        if self.options.profile:
            mlog.set_timestamp_start(time.monotonic())
        with mesonlib.BuildDirLock(self.build_dir):
            self._generate(env)

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

        intr = interpreter.Interpreter(b)
        if env.is_cross_build():
            mlog.log('Host machine cpu family:', mlog.bold(intr.builtin['host_machine'].cpu_family_method([], {})))
            mlog.log('Host machine cpu:', mlog.bold(intr.builtin['host_machine'].cpu_method([], {})))
            mlog.log('Target machine cpu family:', mlog.bold(intr.builtin['target_machine'].cpu_family_method([], {})))
            mlog.log('Target machine cpu:', mlog.bold(intr.builtin['target_machine'].cpu_method([], {})))
        mlog.log('Build machine cpu family:', mlog.bold(intr.builtin['build_machine'].cpu_family_method([], {})))
        mlog.log('Build machine cpu:', mlog.bold(intr.builtin['build_machine'].cpu_method([], {})))
        if self.options.profile:
            fname = os.path.join(self.build_dir, 'meson-private', 'profile-interpreter.log')
            profile.runctx('intr.run()', globals(), locals(), filename=fname)
        else:
            intr.run()
        # Print all default option values that don't match the current value
        for def_opt_name, def_opt_value, cur_opt_value in intr.get_non_matching_default_options():
            mlog.log('Option', mlog.bold(def_opt_name), 'is:',
                     mlog.bold(str(cur_opt_value)),
                     '[default: {}]'.format(str(def_opt_value)))
        try:
            dumpfile = os.path.join(env.get_scratch_dir(), 'build.dat')
            # We would like to write coredata as late as possible since we use the existence of
            # this file to check if we generated the build file successfully. Since coredata
            # includes settings, the build files must depend on it and appear newer. However, due
            # to various kernel caches, we cannot guarantee that any time in Python is exactly in
            # sync with the time that gets applied to any files. Thus, we dump this file as late as
            # possible, but before build files, and if any error occurs, delete it.
            cdf = env.dump_coredata()
            if self.options.profile:
                fname = 'profile-{}-backend.log'.format(intr.backend.name)
                fname = os.path.join(self.build_dir, 'meson-private', fname)
                profile.runctx('intr.backend.generate(intr)', globals(), locals(), filename=fname)
            else:
                intr.backend.generate(intr)
            build.save(b, dumpfile)
            # Post-conf scripts must be run after writing coredata or else introspection fails.
            intr.backend.run_postconf_scripts()
        except:
            if 'cdf' in locals():
                old_cdf = cdf + '.prev'
                if os.path.exists(old_cdf):
                    os.replace(old_cdf, cdf)
                else:
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
    elif cmdname == 'commandrunner':
        import mesonbuild.scripts.commandrunner as abc
        cmdfunc = abc.run
    elif cmdname == 'delsuffix':
        import mesonbuild.scripts.delwithsuffix as abc
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
    elif cmdname == 'hotdoc':
        import mesonbuild.scripts.hotdochelper as abc
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

def set_meson_command(mainfile):
    # On UNIX-like systems `meson` is a Python script
    # On Windows `meson` and `meson.exe` are wrapper exes
    if not mainfile.endswith('.py'):
        mesonlib.meson_command = [mainfile]
    elif os.path.isabs(mainfile) and mainfile.endswith('mesonmain.py'):
        # Can't actually run meson with an absolute path to mesonmain.py, it must be run as -m mesonbuild.mesonmain
        mesonlib.meson_command = mesonlib.python_command + ['-m', 'mesonbuild.mesonmain']
    else:
        # Either run uninstalled, or full path to meson-script.py
        mesonlib.meson_command = mesonlib.python_command + [mainfile]
    # We print this value for unit tests.
    if 'MESON_COMMAND_TESTS' in os.environ:
        mlog.log('meson_command is {!r}'.format(mesonlib.meson_command))

def run(original_args, mainfile):
    if sys.version_info < (3, 5):
        print('Meson works correctly only with python 3.5+.')
        print('You have python %s.' % sys.version)
        print('Please update your environment')
        return 1
    # https://github.com/mesonbuild/meson/issues/3653
    if sys.platform.lower() == 'msys':
        mlog.error('This python3 seems to be msys/python on MSYS2 Windows, which is known to have path semantics incompatible with Meson')
        msys2_arch = detect_msys2_arch()
        if msys2_arch:
            mlog.error('Please install and use mingw-w64-i686-python3 and/or mingw-w64-x86_64-python3 with Pacman')
        else:
            mlog.error('Please download and use Python as detailed at: https://mesonbuild.com/Getting-meson.html')
        return 2
    # Set the meson command that will be used to run scripts and so on
    set_meson_command(mainfile)
    args = original_args[:]
    if len(args) > 0:
        # First check if we want to run a subcommand.
        cmd_name = args[0]
        remaining_args = args[1:]
        # "help" is a special case: Since printing of the help may be
        # delegated to a subcommand, we edit cmd_name before executing
        # the rest of the logic here.
        if cmd_name == 'help':
            remaining_args += ['--help']
            args = remaining_args
            cmd_name = args[0]
        if cmd_name == 'test':
            from . import mtest
            return mtest.run(remaining_args)
        elif cmd_name == 'setup':
            args = remaining_args
            # FALLTHROUGH like it's 1972.
        elif cmd_name == 'install':
            from . import minstall
            return minstall.run(remaining_args)
        elif cmd_name == 'introspect':
            from . import mintro
            return mintro.run(remaining_args)
        elif cmd_name == 'rewrite':
            from . import rewriter
            return rewriter.run(remaining_args)
        elif cmd_name == 'configure':
            try:
                from . import mconf
                return mconf.run(remaining_args)
            except MesonException as e:
                mlog.exception(e)
                sys.exit(1)
        elif cmd_name == 'wrap':
            from .wrap import wraptool
            return wraptool.run(remaining_args)
        elif cmd_name == 'init':
            from . import minit
            return minit.run(remaining_args)
        elif cmd_name == 'runpython':
            import runpy
            script_file = remaining_args[0]
            sys.argv[1:] = remaining_args[1:]
            runpy.run_path(script_file, run_name='__main__')
            sys.exit(0)

    # No special command? Do the basic setup/reconf.
    if len(args) >= 2 and args[0] == '--internal':
        if args[1] == 'regenerate':
            # Rewrite "meson --internal regenerate" command line to
            # "meson --reconfigure"
            args = ['--reconfigure'] + args[2:]
        else:
            script = args[1]
            try:
                sys.exit(run_script_command(args[1:]))
            except MesonException as e:
                mlog.error('\nError in {} helper script:'.format(script))
                mlog.exception(e)
                sys.exit(1)

    parser = create_parser()

    args = mesonlib.expand_arguments(args)
    options = parser.parse_args(args)
    coredata.parse_cmd_line_options(options)
    try:
        app = MesonApp(options)
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
            mlog.exception(e)
            # Path to log file
            mlog.shutdown()
            logfile = os.path.join(app.build_dir, environment.Environment.log_dir, mlog.log_fname)
            mlog.log("\nA full log can be found at", mlog.bold(logfile))
            if os.environ.get('MESON_FORCE_BACKTRACE'):
                raise
            return 1
        else:
            if os.environ.get('MESON_FORCE_BACKTRACE'):
                raise
            traceback.print_exc()
            return 2
    finally:
        mlog.shutdown()

    return 0

def main():
    # Always resolve the command path so Ninja can find it for regen, tests, etc.
    if 'meson.exe' in sys.executable:
        assert(os.path.isabs(sys.executable))
        launcher = sys.executable
    else:
        launcher = os.path.realpath(sys.argv[0])
    return run(sys.argv[1:], launcher)

if __name__ == '__main__':
    sys.exit(main())
