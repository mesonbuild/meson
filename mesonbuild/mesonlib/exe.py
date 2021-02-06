# Copyright 2012-2020 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os, subprocess
import typing as T

__all__ = [
    'EnvironmentVariables',
    'ExecutableSerialisation',
]

class EnvironmentVariables:
    def __init__(self):
        self.envvars = []
        # The set of all env vars we have operations for. Only used for self.has_name()
        self.varnames = set()

    def __repr__(self):
        repr_str = "<{0}: {1}>"
        return repr_str.format(self.__class__.__name__, self.envvars)

    def add_var(self, method, name, args, kwargs):
        self.varnames.add(name)
        self.envvars.append((method, name, args, kwargs))

    def has_name(self, name):
        return name in self.varnames

    def get_value(self, values, kwargs):
        separator = kwargs.get('separator', os.pathsep)

        value = ''
        for var in values:
            value += separator + var
        return separator, value.strip(separator)

    def set(self, env, name, values, kwargs):
        return self.get_value(values, kwargs)[1]

    def append(self, env, name, values, kwargs):
        sep, value = self.get_value(values, kwargs)
        if name in env:
            return env[name] + sep + value
        return value

    def prepend(self, env, name, values, kwargs):
        sep, value = self.get_value(values, kwargs)
        if name in env:
            return value + sep + env[name]

        return value

    def get_env(self, full_env: T.Dict[str, str]) -> T.Dict[str, str]:
        env = full_env.copy()
        for method, name, values, kwargs in self.envvars:
            env[name] = method(full_env, name, values, kwargs)
        return env

class ExecutableSerialisation:
    def __init__(self, cmd_args, env: T.Optional[EnvironmentVariables] = None, exe_wrapper=None,
                 workdir=None, extra_paths=None, capture=None) -> None:
        self.cmd_args = cmd_args
        self.env = env
        self.exe_runner = exe_wrapper
        self.workdir = workdir
        self.extra_paths = extra_paths
        self.capture = capture
        self.pickled = False
        self.skip_if_destdir = False

    def run(extra_env: T.Optional[dict] = None) -> int:
        if self.exe_runner:
            if not self.exe_runner.found():
                raise AssertionError('BUG: Can\'t run cross-compiled exe {!r} with not-found '
                                     'wrapper {!r}'.format(self.cmd_args[0], self.exe_runner.get_path()))
            cmd_args = self.exe_runner.get_command() + self.cmd_args
        else:
            cmd_args = self.cmd_args
        child_env = os.environ.copy()
        if extra_env:
            child_env.update(extra_env)
        if self.env:
            child_env = self.env.get_env(child_env)
        if self.extra_paths:
            child_env['PATH'] = (os.pathsep.join(self.extra_paths + ['']) +
                                 child_env['PATH'])
            if self.exe_runner and mesonlib.substring_is_in_list('wine', self.exe_runner.get_command()):
                child_env['WINEPATH'] = mesonlib.get_wine_shortpath(
                    self.exe_runner.get_command(),
                    ['Z:' + p for p in self.extra_paths] + child_env.get('WINEPATH', '').split(';')
                )

        p = subprocess.Popen(cmd_args, env=child_env, cwd=self.workdir,
                             close_fds=False,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()

        if p.returncode == 0xc0000135:
            # STATUS_DLL_NOT_FOUND on Windows indicating a common problem that is otherwise hard to diagnose
            raise FileNotFoundError('due to missing DLLs')

        if p.returncode != 0:
            if self.pickled:
                print('while executing {!r}'.format(cmd_args))
            if not self.capture:
                print('--- stdout ---')
                print(stdout.decode())
            print('--- stderr ---')
            print(stderr.decode())
            return p.returncode

        if self.capture:
            skip_write = False
            try:
                with open(self.capture, 'rb') as cur:
                    skip_write = cur.read() == stdout
            except IOError:
                pass
            if not skip_write:
                with open(self.capture, 'wb') as output:
                    output.write(stdout)

        return 0
