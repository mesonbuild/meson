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

options = None

def buildparser():
    parser = argparse.ArgumentParser()
    parser.add_argument('args', nargs='+')
    return parser

def is_windows():
    platname = platform.system().lower()
    return platname == 'windows' or 'mingw' in platname

def is_cygwin():
    platname = platform.system().lower()
    return 'cygwin' in platname

def run_with_mono(fname):
    if fname.endswith('.exe') and not (is_windows() or is_cygwin()):
        return True
    return False

def run_exe(exe):
    if exe.fname[0].endswith('.jar'):
        cmd = ['java', '-jar'] + exe.fname
    elif not exe.is_cross and run_with_mono(exe.fname[0]):
        cmd = ['mono'] + exe.fname
    else:
        if exe.is_cross:
            if exe.exe_runner is None:
                raise AssertionError('BUG: Can\'t run cross-compiled exe {!r}'
                                     'with no wrapper'.format(exe.name))
            elif not exe.exe_runner.found():
                raise AssertionError('BUG: Can\'t run cross-compiled exe {!r} with not-found'
                                     'wrapper {!r}'.format(exe.name, exe.exe_runner.get_path()))
            else:
                cmd = exe.exe_runner.get_command() + exe.fname
        else:
            cmd = exe.fname
    child_env = os.environ.copy()
    child_env.update(exe.env)
    if len(exe.extra_paths) > 0:
        child_env['PATH'] = (os.pathsep.join(exe.extra_paths + ['']) +
                             child_env['PATH'])
        if exe.exe_runner and mesonlib.substring_is_in_list('wine', exe.exe_runner.get_command()):
            wine_paths = ['Z:' + p for p in exe.extra_paths]
            wine_path = ';'.join(wine_paths)
            # Don't accidentally end with an `;` because that will add the
            # current directory and might cause unexpected behaviour
            if 'WINEPATH' in child_env:
                child_env['WINEPATH'] = wine_path + ';' + child_env['WINEPATH']
            else:
                child_env['WINEPATH'] = wine_path

    p = subprocess.Popen(cmd + exe.cmd_args, env=child_env, cwd=exe.workdir,
                         close_fds=False,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if exe.capture and p.returncode == 0:
        with open(exe.capture, 'wb') as output:
            output.write(stdout)
    if stderr:
        sys.stderr.buffer.write(stderr)
    return p.returncode

def run(args):
    global options
    options = buildparser().parse_args(args)
    if len(options.args) != 1:
        print('Test runner for Meson. Do not run on your own, mmm\'kay?')
        print(sys.argv[0] + ' [data file]')
    exe_data_file = options.args[0]
    with open(exe_data_file, 'rb') as f:
        exe = pickle.load(f)
    return run_exe(exe)

if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
