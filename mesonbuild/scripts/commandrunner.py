# Copyright 2014 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This program is a wrapper to run external commands. It determines
what to run, sets up the environment and executes the command."""

import sys, os, subprocess, shutil, shlex
import re
import typing as T

def run_command(source_dir: str, build_dir: str, subdir: str, meson_command: T.List[str], command: str, arguments: T.List[str]) -> subprocess.Popen:
    env = {'MESON_SOURCE_ROOT': source_dir,
           'MESON_BUILD_ROOT': build_dir,
           'MESON_SUBDIR': subdir,
           'MESONINTROSPECT': ' '.join([shlex.quote(x) for x in meson_command + ['introspect']]),
           }
    cwd = os.path.join(source_dir, subdir)
    child_env = os.environ.copy()
    child_env.update(env)

    # Is the command an executable in path?
    exe = shutil.which(command)
    if exe is not None:
        command_array = [exe] + arguments
    else:# No? Maybe it is a script in the source tree.
        fullpath = os.path.join(source_dir, subdir, command)
        command_array = [fullpath] + arguments
    try:
        return subprocess.Popen(command_array, env=child_env, cwd=cwd)
    except FileNotFoundError:
        print('Could not execute command "%s". File not found.' % command)
        sys.exit(1)
    except PermissionError:
        print('Could not execute command "%s". File not executable.' % command)
        sys.exit(1)
    except OSError as err:
        print('Could not execute command "{}": {}'.format(command, err))
        sys.exit(1)
    except subprocess.SubprocessError as err:
        print('Could not execute command "{}": {}'.format(command, err))
        sys.exit(1)

def is_python_command(cmdname: str) -> bool:
    end_py_regex = r'python(3|3\.\d+)?(\.exe)?$'
    return re.search(end_py_regex, cmdname) is not None

def run(args: T.List[str]) -> int:
    if len(args) < 4:
        print('commandrunner.py <source dir> <build dir> <subdir> <command> [arguments]')
        return 1
    src_dir = args[0]
    build_dir = args[1]
    subdir = args[2]
    meson_bin = args[3]
    if is_python_command(meson_bin):
        meson_command = [meson_bin, args[4]]
        command = args[5]
        arguments = args[6:]
    else:
        meson_command = [meson_bin]
        command = args[4]
        arguments = args[5:]
    pc = run_command(src_dir, build_dir, subdir, meson_command, command, arguments)
    while True:
        try:
            pc.wait()
            break
        except KeyboardInterrupt:
            pass
    return pc.returncode

if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
