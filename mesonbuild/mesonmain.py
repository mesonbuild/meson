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

import sys, stat, traceback, argparse
import datetime
import os.path
import platform
import cProfile as profile
import importlib

from . import environment, interpreter, mesonlib
from . import build
from . import mconf, mintro, mtest, rewriter, minit
from . import mlog, coredata
from .mesonlib import MesonException
from .environment import detect_msys2_arch
from .wrap import WrapMode, wraptool

def add_setup_arguments(p):
    coredata.register_builtin_arguments(p)
    p.add_argument('--cross-file', default=None,
                   help='File describing cross compilation environment.')
    p.add_argument('-v', '--version', action='version',
                   version=coredata.version)
    # See the mesonlib.WrapMode enum for documentation
    p.add_argument('--wrap-mode', default=WrapMode.default,
                   type=wrapmodetype, choices=WrapMode,
                   help='Special wrap mode to use')
    p.add_argument('--profile-self', action='store_true', dest='profile',
                   help=argparse.SUPPRESS)
    p.add_argument('--reconfigure', action='store_true',
                   help='Reconfigure the project using the same options.')
    p.add_argument('builddir', nargs='?', default='..')
    p.add_argument('sourcedir', nargs='?', default='.')

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
                      'If ninja fails, run "ninja reconfigure" or "meson setup --reconfigure"\n'
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
        mlog.initialize(env.get_log_dir())
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

def set_meson_command(mainfile):
    if mainfile.endswith('.exe'):
        mesonlib.meson_command = [mainfile]
    elif os.path.isabs(mainfile) and mainfile.endswith('mesonmain.py'):
        # Can't actually run meson with an absolute path to mesonmain.py, it must be run as -m mesonbuild.mesonmain
        mesonlib.meson_command = mesonlib.python_command + ['-m', 'mesonbuild.mesonmain']
    else:
        mesonlib.meson_command = mesonlib.python_command + [mainfile]
    # This won't go into the log file because it's not initialized yet, and we
    # need this value for unit tests.
    if 'MESON_COMMAND_TESTS' in os.environ:
        mlog.log('meson_command is {!r}'.format(mesonlib.meson_command))

def run_setup_command(options):
    coredata.parse_cmd_line_options(options)
    app = MesonApp(options)
    app.generate()
    return 0

def add_runpython_arguments(parser):
    parser.add_argument('script_file')
    parser.add_argument('script_args', nargs=argparse.REMAINDER)

def run_runpython_command(options):
    import runpy
    sys.argv[1:] = options.script_args
    runpy.run_path(options.script_file, run_name='__main__')
    return 0

def add_help_arguments(parser):
    parser.add_argument('command', nargs='?')

def run_help_command(options):
    args = ['--help']
    if options.command:
        args.insert(0, options.command)
    return run(args)

def run_script_command(script_name, script_args):
    # Map script name to module name for those that doesn't match
    script_map = {'exe': 'meson_exe',
                  'install': 'meson_install',
                  'delsuffix': 'delwithsuffix',
                  'gtkdoc': 'gtkdochelper',
                  'regencheck': 'regen_checker'}
    module_name = script_map.get(script_name, script_name)

    try:
        module = importlib.import_module('mesonbuild.scripts.' + module_name)
    except ModuleNotFoundError as e:
        mlog.exception(e)
        return 1

    try:
        return module.run(script_args)
    except MesonException as e:
        mlog.error('Error in {} helper script:'.format(script_name))
        mlog.exception(e)
        return 1

class CommandInfo:
    def __init__(self, name, add_arguments_func, run_func, help):
        self.name = name
        self.add_arguments_func = add_arguments_func
        self.run_func = run_func
        self.help = help

def run(args, mainfile):
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

    commands = [
        CommandInfo('setup', add_setup_arguments, run_setup_command,
                    help='Configure the project'),
        CommandInfo('configure', mconf.add_arguments, mconf.run,
                    help='Change project options',),
        CommandInfo('introspect', mintro.add_arguments, mintro.run,
                    help='Introspect project'),
        CommandInfo('init', minit.add_arguments, minit.run,
                    help='Create a new project'),
        CommandInfo('test', mtest.add_arguments, mtest.run,
                    help='Run tests'),
        CommandInfo('rewrite', rewriter.add_arguments, rewriter.run,
                    help='Edit project files'),
        CommandInfo('wrap', wraptool.add_arguments, wraptool.run,
                    help='Wrap tools'),
        CommandInfo('help', add_help_arguments, run_help_command,
                    help='Print help of a subcommand'),
        CommandInfo('runpython', add_runpython_arguments, run_runpython_command,
                    help='Run a python script'),
    ]

    # Special handling of args before passing them to argparse, mostly for
    # backward compatibility.
    if len(args) >= 2 and args[0] == '--internal':
        if args[1] == 'regenerate':
            args = ['setup', '--reconfigure'] + args[2:]
        else:
            return run_script_command(args[1], args[2:])

    # If first arg is not a known command, assume user wants to run the setup
    # command.
    known_commands = [cmd.name for cmd in commands] + ['-h', '--help']
    if len(args) == 0 or args[0] not in known_commands:
        args = ['setup'] + args

    parser = argparse.ArgumentParser(prog='meson')
    subparsers = parser.add_subparsers(title='Commands',
                                       description='If no command is specified it defaults to setup command.')
    for cmd in commands:
        p = subparsers.add_parser(cmd.name, help=cmd.help)
        p.set_defaults(run_func=cmd.run_func)
        cmd.add_arguments_func(p)

    args = mesonlib.expand_arguments(args)
    options = parser.parse_args(args)

    try:
        return options.run_func(options)
    except MesonException as e:
        mlog.exception(e)
        logfile = mlog.shutdown()
        if logfile is not None:
            mlog.log("\nA full log can be found at", mlog.bold(logfile))
        if os.environ.get('MESON_FORCE_BACKTRACE'):
            raise
        return 1
    except Exception as e:
        if os.environ.get('MESON_FORCE_BACKTRACE'):
            raise
        traceback.print_exc()
        return 2
    finally:
        mlog.shutdown()

    return 0

def main():
    # Always resolve the command path so Ninja can find it for regen, tests, etc.
    launcher = os.path.realpath(sys.argv[0])
    return run(sys.argv[1:], launcher)

if __name__ == '__main__':
    sys.exit(main())
