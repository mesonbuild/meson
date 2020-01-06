# Copyright 2013-2019 The Meson development team

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
import os
import re
import subprocess

from .. import mlog
from .. import mesonlib
from ..mesonlib import split_args, listify
from ..environment import detect_cpu_family
from .base import (DependencyException, DependencyMethods, ExternalDependency, ExternalProgram,
                   PkgConfigDependency)


class MPIDependency(ExternalDependency):

    def __init__(self, environment, kwargs: dict):
        language = kwargs.get('language', 'c')
        super().__init__('mpi', environment, language, kwargs)
        kwargs['required'] = False
        kwargs['silent'] = True
        self.is_found = False
        methods = listify(self.methods)

        env_vars = []
        default_wrappers = []
        pkgconfig_files = []
        if language == 'c':
            cid = environment.detect_c_compiler(self.for_machine).get_id()
            if cid in ('intel', 'intel-cl'):
                env_vars.append('I_MPI_CC')
                # IntelMPI doesn't have .pc files
                default_wrappers.append('mpiicc')
            else:
                env_vars.append('MPICC')
                pkgconfig_files.append('ompi-c')
            default_wrappers.append('mpicc')
        elif language == 'cpp':
            cid = environment.detect_cpp_compiler(self.for_machine).get_id()
            if cid in ('intel', 'intel-cl'):
                env_vars.append('I_MPI_CXX')
                # IntelMPI doesn't have .pc files
                default_wrappers.append('mpiicpc')
            else:
                env_vars.append('MPICXX')
                pkgconfig_files.append('ompi-cxx')
                default_wrappers += ['mpic++', 'mpicxx', 'mpiCC']  # these are not for intelmpi
        elif language == 'fortran':
            cid = environment.detect_fortran_compiler(self.for_machine).get_id()
            if cid in ('intel', 'intel-cl'):
                env_vars.append('I_MPI_F90')
                # IntelMPI doesn't have .pc files
                default_wrappers.append('mpiifort')
            else:
                env_vars += ['MPIFC', 'MPIF90', 'MPIF77']
                pkgconfig_files.append('ompi-fort')
            default_wrappers += ['mpifort', 'mpif90', 'mpif77']
        else:
            raise DependencyException('Language {} is not supported with MPI.'.format(language))

        if set([DependencyMethods.AUTO, DependencyMethods.PKGCONFIG]).intersection(methods):
            for pkg in pkgconfig_files:
                pkgdep = PkgConfigDependency(pkg, environment, kwargs, language=self.language)
                if pkgdep.found():
                    self.compile_args = pkgdep.get_compile_args()
                    self.link_args = pkgdep.get_link_args()
                    self.version = pkgdep.get_version()
                    self.is_found = True
                    self.pcdep = pkgdep
                    return

        if DependencyMethods.AUTO in methods:
            for var in env_vars:
                if var in os.environ:
                    wrappers = [os.environ[var]]
                    break
            else:
                # Or search for default wrappers.
                wrappers = default_wrappers

            for prog in wrappers:
                # Note: Some use OpenMPI with Intel compilers on Linux
                result = self._try_openmpi_wrapper(prog, cid)
                if result is not None:
                    self.is_found = True
                    self.version = result[0]
                    self.compile_args = self._filter_compile_args(result[1])
                    self.link_args = self._filter_link_args(result[2], cid)
                    break
                result = self._try_other_wrapper(prog, cid)
                if result is not None:
                    self.is_found = True
                    self.version = result[0]
                    self.compile_args = self._filter_compile_args(result[1])
                    self.link_args = self._filter_link_args(result[2], cid)
                    break

            if not self.is_found and mesonlib.is_windows():
                # only Intel Fortran compiler is compatible with Microsoft MPI at this time.
                if language == 'fortran' and cid != 'intel-cl':
                    return
                result = self._try_msmpi()
                if result is not None:
                    self.is_found = True
                    self.version, self.compile_args, self.link_args = result
            return

    def _filter_compile_args(self, args: T.Sequence[str]) -> T.List[str]:
        """
        MPI wrappers return a bunch of garbage args.
        Drop -O2 and everything that is not needed.
        """
        result = []
        multi_args = ('-I', )
        if self.language == 'fortran':
            fc = self.env.coredata.compilers[self.for_machine]['fortran']
            multi_args += fc.get_module_incdir_args()

        include_next = False
        for f in args:
            if f.startswith(('-D', '-f') + multi_args) or f == '-pthread' \
                    or (f.startswith('-W') and f != '-Wall' and not f.startswith('-Werror')):
                result.append(f)
                if f in multi_args:
                    # Path is a separate argument.
                    include_next = True
            elif include_next:
                include_next = False
                result.append(f)
        return result

    def _filter_link_args(self, args: T.Sequence[str], cid: str) -> T.List[str]:
        """
        MPI wrappers return a bunch of garbage args.
        Drop -O2 and everything that is not needed.
        """
        result = []
        include_next = False
        for f in args:
            if self._is_link_arg(f, cid):
                result.append(f)
                if f in ('-L', '-Xlinker'):
                    include_next = True
            elif include_next:
                include_next = False
                result.append(f)
        return result

    @staticmethod
    def _is_link_arg(f: str, cid: str) -> bool:
        if cid == 'intel-cl':
            return f == '/link' or f.startswith('/LIBPATH') or f.endswith('.lib')   # always .lib whether static or dynamic
        else:
            return (f.startswith(('-L', '-l', '-Xlinker')) or
                    f == '-pthread' or
                    (f.startswith('-W') and f != '-Wall' and not f.startswith('-Werror')))

    def _try_openmpi_wrapper(self, prog, cid: str):
        # https://www.open-mpi.org/doc/v4.0/man1/mpifort.1.php
        if cid == 'intel-cl':  # IntelCl doesn't support OpenMPI
            return None
        prog = ExternalProgram(prog, silent=True)
        if not prog.found():
            return None

        # compiler args
        cmd = prog.get_command() + ['--showme:compile']
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=15)
        if p.returncode != 0:
            mlog.debug('Command', mlog.bold(cmd), 'failed to run:')
            mlog.debug(mlog.bold('Standard output\n'), p.stdout)
            mlog.debug(mlog.bold('Standard error\n'), p.stderr)
            return None
        cargs = split_args(p.stdout)
        # link args
        cmd = prog.get_command() + ['--showme:link']
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=15)
        if p.returncode != 0:
            mlog.debug('Command', mlog.bold(cmd), 'failed to run:')
            mlog.debug(mlog.bold('Standard output\n'), p.stdout)
            mlog.debug(mlog.bold('Standard error\n'), p.stderr)
            return None
        libs = split_args(p.stdout)
        # version
        cmd = prog.get_command() + ['--showme:version']
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=15)
        if p.returncode != 0:
            mlog.debug('Command', mlog.bold(cmd), 'failed to run:')
            mlog.debug(mlog.bold('Standard output\n'), p.stdout)
            mlog.debug(mlog.bold('Standard error\n'), p.stderr)
            return None
        v = re.search(r'\d+.\d+.\d+', p.stdout)
        if v:
            version = v.group(0)
        else:
            version = None

        return version, cargs, libs

    def _try_other_wrapper(self, prog, cid: str) -> T.Tuple[str, T.List[str], T.List[str]]:
        prog = ExternalProgram(prog, silent=True)
        if not prog.found():
            return None

        cmd = prog.get_command()
        if cid == 'intel-cl':
            cmd.append('/show')
        else:
            cmd.append('-show')
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=15)
        if p.returncode != 0:
            mlog.debug('Command', mlog.bold(cmd), 'failed to run:')
            mlog.debug(mlog.bold('Standard output\n'), p.stdout)
            mlog.debug(mlog.bold('Standard error\n'), p.stderr)
            return None

        version = None
        stdout = p.stdout
        if 'Intel(R) MPI Library' in p.stdout:  # intel-cl: remove messy compiler logo
            out = stdout.split('\n', 2)
            version = out[0]
            stdout = out[2]

        if version is None:
            p = subprocess.run(cmd + ['-v'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=15)
            if p.returncode == 0:
                version = p.stdout.split('\n', 1)[0]

        args = split_args(stdout)

        return version, args, args

    def _try_msmpi(self) -> T.Tuple[str, T.List[str], T.List[str]]:
        if self.language == 'cpp':
            # MS-MPI does not support the C++ version of MPI, only the standard C API.
            return None
        if 'MSMPI_INC' not in os.environ:
            return None

        incdir = os.environ['MSMPI_INC']
        arch = detect_cpu_family(self.env.coredata.compilers.host)
        if arch == 'x86':
            if 'MSMPI_LIB32' not in os.environ:
                return None
            libdir = os.environ['MSMPI_LIB32']
            post = 'x86'
        elif arch == 'x86_64':
            if 'MSMPI_LIB64' not in os.environ:
                return None
            libdir = os.environ['MSMPI_LIB64']
            post = 'x64'
        else:
            return None

        if self.language == 'fortran':
            return (None,
                    ['-I' + incdir, '-I' + os.path.join(incdir, post)],
                    [os.path.join(libdir, 'msmpi.lib'), os.path.join(libdir, 'msmpifec.lib')])
        else:
            return (None,
                    ['-I' + incdir, '-I' + os.path.join(incdir, post)],
                    [os.path.join(libdir, 'msmpi.lib')])

    @staticmethod
    def get_methods():
        return [DependencyMethods.AUTO, DependencyMethods.PKGCONFIG]
