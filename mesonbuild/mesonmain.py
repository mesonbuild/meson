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

from . import mesonlib
from . import mlog
from .mesonlib import MesonException
from .environment import detect_msys2_arch

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
        else:
            # If cmd_name is not a known command, assume user wants to run the
            # setup command.
            from . import msetup
            if cmd_name != 'setup':
                remaining_args = args
            return msetup.run(remaining_args)

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
