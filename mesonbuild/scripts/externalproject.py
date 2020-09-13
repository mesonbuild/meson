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

import os
import argparse
import multiprocessing
import subprocess
from pathlib import Path
import typing as T

from ..mesonlib import Popen_safe

class ExternalProject:
    def __init__(self, options: argparse.Namespace):
        self.name = options.name
        self.src_dir = options.srcdir
        self.build_dir = options.builddir
        self.install_dir = options.installdir
        self.verbose = options.verbose
        self.stampfile = options.stampfile
        self.depfile = options.depfile
        self.make = options.make

    def write_depfile(self) -> None:
        with open(self.depfile, 'w') as f:
            f.write('{}: \\\n'.format(self.stampfile))
            for dirpath, dirnames, filenames in os.walk(self.src_dir):
                dirnames[:] = [d for d in dirnames if not d.startswith('.')]
                for fname in filenames:
                    if fname.startswith('.'):
                        continue
                    path = Path(dirpath, fname)
                    f.write('  {} \\\n'.format(path.as_posix().replace(' ', '\\ ')))

    def write_stampfile(self) -> None:
        with open(self.stampfile, 'w') as f:
            pass

    def gnu_make(self) -> bool:
        p, o, e = Popen_safe([self.make, '--version'])
        if p.returncode == 0 and 'GNU Make' in o:
            return True
        return False

    def build(self) -> int:
        make_cmd = [self.make]
        if not self.verbose:
            make_cmd.append('--quiet')
        if self.gnu_make():
            make_cmd.append('-j' + str(multiprocessing.cpu_count()))

        rc = self._run(make_cmd)
        if rc != 0:
            return rc

        install_cmd = make_cmd + ['DESTDIR= ' + self.install_dir, 'install']
        rc = self._run(install_cmd)
        if rc != 0:
            return rc

        self.write_depfile()
        self.write_stampfile()

        return 0

    def _run(self, command: T.List[str]) -> int:
        output = None if self.verbose else subprocess.DEVNULL
        p, o, e = Popen_safe(command, stderr=subprocess.STDOUT, stdout=output,
                             cwd=self.build_dir)
        return p.returncode

def run(args: T.List[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--name')
    parser.add_argument('--srcdir')
    parser.add_argument('--builddir')
    parser.add_argument('--installdir')
    parser.add_argument('--make')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('stampfile')
    parser.add_argument('depfile')

    options = parser.parse_args(args)
    ep = ExternalProject(options)
    return ep.build()
