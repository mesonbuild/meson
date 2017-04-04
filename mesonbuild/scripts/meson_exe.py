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

from ..mesonlib import Popen_safe

options = None

parser = argparse.ArgumentParser()
parser.add_argument('args', nargs='+')

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
                raise AssertionError('BUG: Trying to run cross-compiled exes with no wrapper')
            else:
                cmd = [exe.exe_runner] + exe.fname
        else:
            cmd = exe.fname
    child_env = os.environ.copy()
    child_env.update(exe.env)
    if len(exe.extra_paths) > 0:
        child_env['PATH'] = (os.pathsep.join(exe.extra_paths + ['']) +
                             child_env['PATH'])
    p, stdout, stderr = Popen_safe(cmd + exe.cmd_args, env=child_env, cwd=exe.workdir)
    if exe.capture and p.returncode == 0:
        with open(exe.capture, 'w') as output:
            output.write(stdout)
    if stderr:
        sys.stderr.write(stderr)
    return p.returncode

def run(args):
    global options
    options = parser.parse_args(args)
    if len(options.args) != 1:
        print('Test runner for Meson. Do not run on your own, mmm\'kay?')
        print(sys.argv[0] + ' [data file]')
    exe_data_file = options.args[0]
    with open(exe_data_file, 'rb') as f:
        exe = pickle.load(f)
    return run_exe(exe)

if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
