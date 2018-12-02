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

import sys
import os.path
import importlib
import traceback
import argparse

from . import mesonlib
from . import mlog
from . import mconf, minit, minstall, mintro, msetup, mtest, rewriter, msubprojects
from .mesonlib import MesonException
from .environment import detect_msys2_arch
from .wrap import wraptool


class CommandLineParser:
    def __init__(self):
        self.commands = {}
        self.hidden_commands = []
        self.parser = argparse.ArgumentParser(prog='meson')
        self.subparsers = self.parser.add_subparsers(title='Commands',
                                                     description='If no command is specified it defaults to setup command.')
        self.add_command('setup', msetup.add_arguments, msetup.run,
                         help='Configure the project')
        self.add_command('configure', mconf.add_arguments, mconf.run,
                         help='Change project options',)
        self.add_command('install', minstall.add_arguments, minstall.run,
                         help='Install the project')
        self.add_command('introspect', mintro.add_arguments, mintro.run,
                         help='Introspect project')
        self.add_command('init', minit.add_arguments, minit.run,
                         help='Create a new project')
        self.add_command('test', mtest.add_arguments, mtest.run,
                         help='Run tests')
        self.add_command('wrap', wraptool.add_arguments, wraptool.run,
                         help='Wrap tools')
        self.add_command('subprojects', msubprojects.add_arguments, msubprojects.run,
                         help='Manage subprojects')
        self.add_command('help', self.add_help_arguments, self.run_help_command,
                         help='Print help of a subcommand')

        # Hidden commands
        self.add_command('rewrite', rewriter.add_arguments, rewriter.run,
                         help=argparse.SUPPRESS)
        self.add_command('runpython', self.add_runpython_arguments, self.run_runpython_command,
                         help=argparse.SUPPRESS)

    def add_command(self, name, add_arguments_func, run_func, help):
        # FIXME: Cannot have hidden subparser:
        # https://bugs.python.org/issue22848
        if help == argparse.SUPPRESS:
            p = argparse.ArgumentParser(prog='meson ' + name)
            self.hidden_commands.append(name)
        else:
            p = self.subparsers.add_parser(name, help=help)
        add_arguments_func(p)
        p.set_defaults(run_func=run_func)
        self.commands[name] = p

    def add_runpython_arguments(self, parser):
        parser.add_argument('script_file')
        parser.add_argument('script_args', nargs=argparse.REMAINDER)

    def run_runpython_command(self, options):
        import runpy
        sys.argv[1:] = options.script_args
        runpy.run_path(options.script_file, run_name='__main__')
        return 0

    def add_help_arguments(self, parser):
        parser.add_argument('command', nargs='?')

    def run_help_command(self, options):
        if options.command:
            self.commands[options.command].print_help()
        else:
            self.parser.print_help()
        return 0

    def run(self, args):
        # If first arg is not a known command, assume user wants to run the setup
        # command.
        known_commands = list(self.commands.keys()) + ['-h', '--help']
        if len(args) == 0 or args[0] not in known_commands:
            args = ['setup'] + args

        # Hidden commands have their own parser instead of using the global one
        if args[0] in self.hidden_commands:
            parser = self.commands[args[0]]
            args = args[1:]
        else:
            parser = self.parser

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

def run_script_command(script_name, script_args):
    # Map script name to module name for those that doesn't match
    script_map = {'exe': 'meson_exe',
                  'install': 'meson_install',
                  'delsuffix': 'delwithsuffix',
                  'gtkdoc': 'gtkdochelper',
                  'hotdoc': 'hotdochelper',
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
    mesonlib.set_meson_command(mainfile)

    args = original_args[:]

    # Special handling of internal commands called from backends, they don't
    # need to go through argparse.
    if len(args) >= 2 and args[0] == '--internal':
        if args[1] == 'regenerate':
            # Rewrite "meson --internal regenerate" command line to
            # "meson --reconfigure"
            args = ['--reconfigure'] + args[2:]
        else:
            return run_script_command(args[1], args[2:])

    return CommandLineParser().run(args)

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
