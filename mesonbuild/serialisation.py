# Copyright 2013-2021 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import typing as T
from . import programs

if T.TYPE_CHECKING:
    from . import build
    from .backend.backends import TestProtocol

class ExecutableSerialisation:

    # XXX: should capture and feed default to False, instead of None?

    def __init__(self, cmd_args: T.List[str],
                 env: T.Optional['build.EnvironmentVariables'] = None,
                 exe_wrapper: T.Optional[programs.ExternalProgram] = None,
                 workdir: T.Optional[str] = None,
                 extra_paths: T.Optional[T.List] = None,
                 capture: T.Optional[bool] = None,
                 feed: T.Optional[bool] = None,
                 tag: T.Optional[str] = None,
                 verbose: bool = False,
                 ) -> None:
        self.cmd_args = cmd_args
        self.env = env
        if exe_wrapper is not None:
            assert isinstance(exe_wrapper, programs.ExternalProgram)
        self.exe_runner = exe_wrapper
        self.workdir = workdir
        self.extra_paths = extra_paths
        self.capture = capture
        self.feed = feed
        self.pickled = False
        self.skip_if_destdir = False
        self.verbose = verbose
        self.subproject = ''
        self.tag = tag

class TestSerialisation:
    def __init__(self, name: str, project: str, suite: T.List[str], fname: T.List[str],
                 is_cross_built: bool, exe_wrapper: T.Optional[programs.ExternalProgram],
                 needs_exe_wrapper: bool, is_parallel: bool, cmd_args: T.List[str],
                 env: 'build.EnvironmentVariables', should_fail: bool,
                 timeout: T.Optional[int], workdir: T.Optional[str],
                 extra_paths: T.List[str], protocol: 'TestProtocol', priority: int,
                 cmd_is_built: bool, depends: T.List[str], version: str):
        self.name = name
        self.project_name = project
        self.suite = suite
        self.fname = fname
        self.is_cross_built = is_cross_built
        if exe_wrapper is not None:
            assert isinstance(exe_wrapper, programs.ExternalProgram)
        self.exe_runner = exe_wrapper
        self.is_parallel = is_parallel
        self.cmd_args = cmd_args
        self.env = env
        self.should_fail = should_fail
        self.timeout = timeout
        self.workdir = workdir
        self.extra_paths = extra_paths
        self.protocol = protocol
        self.priority = priority
        self.needs_exe_wrapper = needs_exe_wrapper
        self.cmd_is_built = cmd_is_built
        self.depends = depends
        self.version = version
