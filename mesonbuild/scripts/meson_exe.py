# Copyright 2013-2016 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import argparse
import pickle
import platform
import subprocess

from .. import mesonlib
from ..backend.backends import ExecutableSerialisation

options = None

def buildparser():
    parser = argparse.ArgumentParser(description='Custom executable wrapper for Meson. Do not run on your own, mmm\'kay?')
    parser.add_argument('--unpickle')
    parser.add_argument('--capture')
    return parser

def is_windows():
    platname = platform.system().lower()
    return platname == 'windows' or 'mingw' in platname

def is_cygwin():
    platname = platform.system().lower()
    return 'cygwin' in platname

def run_exe(exe):
    if exe.exe_runner:
        if not exe.exe_runner.found():
            raise AssertionError('BUG: Can\'t run cross-compiled exe {!r} with not-found '
                                 'wrapper {!r}'.format(exe.cmd_args[0], exe.exe_runner.get_path()))
        cmd_args = exe.exe_runner.get_command() + exe.cmd_args
    else:
        cmd_args = exe.cmd_args
    child_env = os.environ.copy()
    child_env.update(exe.env)
    if exe.extra_paths:
        child_env['PATH'] = (os.pathsep.join(exe.extra_paths + ['']) +
                             child_env['PATH'])
        if exe.exe_runner and mesonlib.substring_is_in_list('wine', exe.exe_runner.get_command()):
            child_env['WINEPATH'] = mesonlib.get_wine_shortpath(
                exe.exe_runner.get_command(),
                ['Z:' + p for p in exe.extra_paths] + child_env.get('WINEPATH', '').split(';')
            )

    p = subprocess.Popen(cmd_args, env=child_env, cwd=exe.workdir,
                         close_fds=False,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()

    if p.returncode == 0xc0000135:
        # STATUS_DLL_NOT_FOUND on Windows indicating a common problem that is otherwise hard to diagnose
        raise FileNotFoundError('Missing DLLs on calling {!r}'.format(exe.name))

    if exe.capture and p.returncode == 0:
        skip_write = False
        try:
            with open(exe.capture, 'rb') as cur:
                skip_write = cur.read() == stdout
        except IOError:
            pass
        if not skip_write:
            with open(exe.capture, 'wb') as output:
                output.write(stdout)
    else:
        sys.stdout.buffer.write(stdout)
    if stderr:
        sys.stderr.buffer.write(stderr)
    return p.returncode

def run(args):
    global options
    parser = buildparser()
    options, cmd_args = parser.parse_known_args(args)
    # argparse supports double dash to separate options and positional arguments,
    # but the user has to remove it manually.
    if cmd_args and cmd_args[0] == '--':
        cmd_args = cmd_args[1:]
    if not options.unpickle and not cmd_args:
        parser.error('either --unpickle or executable and arguments are required')
    if options.unpickle:
        if cmd_args or options.capture:
            parser.error('no other arguments can be used with --unpickle')
        with open(options.unpickle, 'rb') as f:
            exe = pickle.load(f)
    else:
        exe = ExecutableSerialisation(cmd_args, capture=options.capture)

    return run_exe(exe)

if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
