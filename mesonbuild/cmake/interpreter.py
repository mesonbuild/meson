# Copyright 2019 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This class contains the basic functionality needed to run any interpreter
# or an interpreter-based tool.

from .common import CMakeException
from .client import CMakeClient, RequestCMakeInputs, RequestConfigure, RequestCompute, RequestCodeModel
from .. import mlog
from ..build import Build
from ..environment import Environment
from ..backend.backends import Backend
from ..dependencies.base import CMakeDependency, ExternalProgram
from subprocess import Popen, PIPE, STDOUT
import os

CMAKE_BACKEND_GENERATOR_MAP = {
    'ninja': 'Ninja',
    'xcode': 'Xcode',
    'vs2010': 'Visual Studio 10 2010',
    'vs2015': 'Visual Studio 15 2017',
    'vs2017': 'Visual Studio 15 2017',
}

CMAKE_LANGUAGE_MAP = {
    'c': 'C',
    'cpp': 'CXX',
    'cuda': 'CUDA',
    'cs': 'CSharp',
    'java': 'Java',
    'fortran': 'Fortran',
    'swift': 'Swift',
}

class CMakeInterpreter:
    def __init__(self, build: Build, src_dir: str, build_dir: str, env: Environment, backend: Backend):
        assert(hasattr(backend, 'name'))
        self.build = build
        self.src_dir = src_dir
        self.build_dir = build_dir
        self.env = env
        self.backend_name = backend.name
        self.client = CMakeClient(self.env)
        os.makedirs(self.build_dir, exist_ok=True)

    def configure(self) -> None:
        # Find CMake
        cmake_exe, cmake_vers, _ = CMakeDependency.find_cmake_binary(self.env)
        if cmake_exe is None or cmake_exe is False:
            raise CMakeException('Unable to find CMake')
        assert(isinstance(cmake_exe, ExternalProgram))
        if not cmake_exe.found():
            raise CMakeException('Unable to find CMake')

        generator = CMAKE_BACKEND_GENERATOR_MAP[self.backend_name]
        cmake_args = cmake_exe.get_command()

        # Map meson compiler to CMake variables
        for lang, comp in self.build.compilers.items():
            if lang not in CMAKE_LANGUAGE_MAP:
                continue
            cmake_lang = CMAKE_LANGUAGE_MAP[lang]
            exelist = comp.get_exelist()
            if len(exelist) == 1:
                cmake_args += ['-DCMAKE_{}_COMPILER={}'.format(cmake_lang, exelist[0])]
            elif len(exelist) == 2:
                cmake_args += ['-DCMAKE_{}_COMPILER_LAUNCHER={}'.format(cmake_lang, exelist[0]),
                               '-DCMAKE_{}_COMPILER={}'.format(cmake_lang, exelist[1])]
        cmake_args += ['-G', generator]

        # Run CMake
        mlog.log('Configuring the build directory with', mlog.bold('CMake'), 'version', mlog.cyan(cmake_vers))
        with mlog.nested():
            mlog.log(mlog.bold('Running:'), ' '.join(cmake_args))
            proc = Popen(cmake_args + [self.src_dir], stdout=PIPE, stderr=STDOUT, cwd=self.build_dir)

            # Print CMake log in realtime
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                mlog.log(line.decode('utf-8').strip('\n'))

            # Wait for CMake to finish
            proc.communicate()

        h = mlog.green('SUCCEEDED') if proc.returncode == 0 else mlog.red('FAILED')
        mlog.log('CMake configuration:', h)
        if proc.returncode != 0:
            raise CMakeException('Failed to configure the CMake subproject')

    def run(self) -> None:
        # Run configure the old way becuse doing it
        # with the server doesn't work for some reason
        self.configure()

        with self.client.connect():
            generator = CMAKE_BACKEND_GENERATOR_MAP[self.backend_name]
            self.client.do_handshake(self.src_dir, self.build_dir, generator, 1)

            # Do a second configure to initialise the server
            self.client.query_checked(RequestConfigure(), 'CMake server configure')

            # Generate the build system files
            self.client.query_checked(RequestCompute(), 'Generating build system files')

            # Get CMake build system files
            bs_reply = self.client.query_checked(RequestCMakeInputs(), 'Querying build system files')

            # Now get the CMake code model
            cm_reply = self.client.query_checked(RequestCodeModel(), 'Querying the CMake code model')
            cm_reply.log()
