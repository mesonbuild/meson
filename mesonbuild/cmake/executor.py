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

import subprocess as S
from pathlib import Path
from threading import Thread
import typing as T
import re
import os
import shutil
import ctypes
import textwrap

from .. import mlog, mesonlib
from ..mesonlib import PerMachine, Popen_safe, version_compare, MachineChoice
from ..environment import Environment
from ..envconfig import get_env_var

if T.TYPE_CHECKING:
    from ..dependencies.base import ExternalProgram

TYPE_result = T.Tuple[int, T.Optional[str], T.Optional[str]]

class CMakeExecutor:
    # The class's copy of the CMake path. Avoids having to search for it
    # multiple times in the same Meson invocation.
    class_cmakebin = PerMachine(None, None)
    class_cmakevers = PerMachine(None, None)
    class_cmake_cache = {}  # type: T.Dict[T.Any, TYPE_result]

    def __init__(self, environment: Environment, version: str, for_machine: MachineChoice, silent: bool = False):
        self.min_version = version
        self.environment = environment
        self.for_machine = for_machine
        self.cmakebin, self.cmakevers = self.find_cmake_binary(self.environment, silent=silent)
        self.always_capture_stderr = True
        self.print_cmout = False
        self.prefix_paths = []      # type: T.List[str]
        self.extra_cmake_args = []  # type: T.List[str]
        if self.cmakebin is False:
            self.cmakebin = None
            return

        if not version_compare(self.cmakevers, self.min_version):
            mlog.warning(
                'The version of CMake', mlog.bold(self.cmakebin.get_path()),
                'is', mlog.bold(self.cmakevers), 'but version', mlog.bold(self.min_version),
                'is required')
            self.cmakebin = None
            return

        self.prefix_paths = self.environment.coredata.builtins_per_machine[self.for_machine]['cmake_prefix_path'].value
        env_pref_path = get_env_var(
            self.for_machine,
            self.environment.is_cross_build(),
            'CMAKE_PREFIX_PATH')
        if env_pref_path is not None:
            env_pref_path = re.split(r':|;', env_pref_path)
            env_pref_path = [x for x in env_pref_path if x]  # Filter out empty strings
            if not self.prefix_paths:
                self.prefix_paths = []
            self.prefix_paths += env_pref_path

        if self.prefix_paths:
            self.extra_cmake_args += ['-DCMAKE_PREFIX_PATH={}'.format(';'.join(self.prefix_paths))]

    def find_cmake_binary(self, environment: Environment, silent: bool = False) -> T.Tuple['ExternalProgram', str]:
        from ..dependencies.base import find_external_program

        # Only search for CMake the first time and store the result in the class
        # definition
        if CMakeExecutor.class_cmakebin[self.for_machine] is False:
            mlog.debug('CMake binary for %s is cached as not found' % self.for_machine)
        elif CMakeExecutor.class_cmakebin[self.for_machine] is not None:
            mlog.debug('CMake binary for %s is cached.' % self.for_machine)
        else:
            assert CMakeExecutor.class_cmakebin[self.for_machine] is None

            mlog.debug('CMake binary for %s is not cached' % self.for_machine)
            for potential_cmakebin in find_external_program(
                    environment, self.for_machine, 'cmake', 'CMake',
                    environment.default_cmake, allow_default_for_cross=False):
                version_if_ok = self.check_cmake(potential_cmakebin)
                if not version_if_ok:
                    continue
                if not silent:
                    mlog.log('Found CMake:', mlog.bold(potential_cmakebin.get_path()),
                             '(%s)' % version_if_ok)
                CMakeExecutor.class_cmakebin[self.for_machine] = potential_cmakebin
                CMakeExecutor.class_cmakevers[self.for_machine] = version_if_ok
                break
            else:
                if not silent:
                    mlog.log('Found CMake:', mlog.red('NO'))
                # Set to False instead of None to signify that we've already
                # searched for it and not found it
                CMakeExecutor.class_cmakebin[self.for_machine] = False
                CMakeExecutor.class_cmakevers[self.for_machine] = None

        return CMakeExecutor.class_cmakebin[self.for_machine], CMakeExecutor.class_cmakevers[self.for_machine]

    def check_cmake(self, cmakebin: 'ExternalProgram') -> T.Optional[str]:
        if not cmakebin.found():
            mlog.log('Did not find CMake {!r}'.format(cmakebin.name))
            return None
        try:
            p, out = Popen_safe(cmakebin.get_command() + ['--version'])[0:2]
            if p.returncode != 0:
                mlog.warning('Found CMake {!r} but couldn\'t run it'
                             ''.format(' '.join(cmakebin.get_command())))
                return None
        except FileNotFoundError:
            mlog.warning('We thought we found CMake {!r} but now it\'s not there. How odd!'
                         ''.format(' '.join(cmakebin.get_command())))
            return None
        except PermissionError:
            msg = 'Found CMake {!r} but didn\'t have permissions to run it.'.format(' '.join(cmakebin.get_command()))
            if not mesonlib.is_windows():
                msg += '\n\nOn Unix-like systems this is often caused by scripts that are not executable.'
            mlog.warning(msg)
            return None
        cmvers = re.search(r'(cmake|cmake3)\s*version\s*([\d.]+)', out).group(2)
        return cmvers

    def set_exec_mode(self, print_cmout: T.Optional[bool] = None, always_capture_stderr: T.Optional[bool] = None) -> None:
        if print_cmout is not None:
            self.print_cmout = print_cmout
        if always_capture_stderr is not None:
            self.always_capture_stderr = always_capture_stderr

    def _cache_key(self, args: T.List[str], build_dir: str, env):
        fenv = frozenset(env.items()) if env is not None else None
        targs = tuple(args)
        return (self.cmakebin, targs, build_dir, fenv)

    def _call_cmout_stderr(self, args: T.List[str], build_dir: str, env) -> TYPE_result:
        cmd = self.cmakebin.get_command() + args
        proc = S.Popen(cmd, stdout=S.PIPE, stderr=S.PIPE, cwd=build_dir, env=env)

        # stdout and stderr MUST be read at the same time to avoid pipe
        # blocking issues. The easiest way to do this is with a separate
        # thread for one of the pipes.
        def print_stdout():
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                mlog.log(line.decode(errors='ignore').strip('\n'))
            proc.stdout.close()

        t = Thread(target=print_stdout)
        t.start()

        try:
            # Read stderr line by line and log non trace lines
            raw_trace = ''
            tline_start_reg = re.compile(r'^\s*(.*\.(cmake|txt))\(([0-9]+)\):\s*(\w+)\(.*$')
            inside_multiline_trace = False
            while True:
                line = proc.stderr.readline()
                if not line:
                    break
                line = line.decode(errors='ignore')
                if tline_start_reg.match(line):
                    raw_trace += line
                    inside_multiline_trace = not line.endswith(' )\n')
                elif inside_multiline_trace:
                    raw_trace += line
                else:
                    mlog.warning(line.strip('\n'))

        finally:
            proc.stderr.close()
            t.join()
            proc.wait()

        return proc.returncode, None, raw_trace

    def _call_cmout(self, args: T.List[str], build_dir: str, env) -> TYPE_result:
        cmd = self.cmakebin.get_command() + args
        proc = S.Popen(cmd, stdout=S.PIPE, stderr=S.STDOUT, cwd=build_dir, env=env)
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            mlog.log(line.decode(errors='ignore').strip('\n'))
        proc.stdout.close()
        proc.wait()
        return proc.returncode, None, None

    def _call_quiet(self, args: T.List[str], build_dir: str, env) -> TYPE_result:
        os.makedirs(build_dir, exist_ok=True)
        cmd = self.cmakebin.get_command() + args
        ret = S.run(cmd, env=env, cwd=build_dir, close_fds=False,
                    stdout=S.PIPE, stderr=S.PIPE, universal_newlines=False)
        rc = ret.returncode
        out = ret.stdout.decode(errors='ignore')
        err = ret.stderr.decode(errors='ignore')
        call = ' '.join(cmd)
        mlog.debug("Called `{}` in {} -> {}".format(call, build_dir, rc))
        return rc, out, err

    def _call_impl(self, args: T.List[str], build_dir: str, env) -> TYPE_result:
        if not self.print_cmout:
            return self._call_quiet(args, build_dir, env)
        else:
            if self.always_capture_stderr:
                return self._call_cmout_stderr(args, build_dir, env)
            else:
                return self._call_cmout(args, build_dir, env)

    def call(self, args: T.List[str], build_dir: str, env=None, disable_cache: bool = False) -> TYPE_result:
        if env is None:
            env = os.environ

        args = args + self.extra_cmake_args
        if disable_cache:
            return self._call_impl(args, build_dir, env)

        # First check if cached, if not call the real cmake function
        cache = CMakeExecutor.class_cmake_cache
        key = self._cache_key(args, build_dir, env)
        if key not in cache:
            cache[key] = self._call_impl(args, build_dir, env)
        return cache[key]

    def call_with_fake_build(self, args: T.List[str], build_dir: str, env=None) -> TYPE_result:
        # First check the cache
        cache = CMakeExecutor.class_cmake_cache
        key = self._cache_key(args, build_dir, env)
        if key in cache:
            return cache[key]

        os.makedirs(build_dir, exist_ok=True)

        # Try to set the correct compiler for C and C++
        # This step is required to make try_compile work inside CMake
        fallback = os.path.realpath(__file__)  # A file used as a fallback wehen everything else fails
        compilers = self.environment.coredata.compilers[MachineChoice.BUILD]

        def make_abs(exe: str, lang: str) -> str:
            if os.path.isabs(exe):
                return exe

            p = shutil.which(exe)
            if p is None:
                mlog.debug('Failed to find a {} compiler for CMake. This might cause CMake to fail.'.format(lang))
                p = fallback
            return p

        def choose_compiler(lang: str) -> T.Tuple[str, str]:
            exe_list = []
            if lang in compilers:
                exe_list = compilers[lang].get_exelist()
            else:
                try:
                    comp_obj = self.environment.compiler_from_language(lang, MachineChoice.BUILD)
                    if comp_obj is not None:
                        exe_list = comp_obj.get_exelist()
                except Exception:
                    pass

            if len(exe_list) == 1:
                return make_abs(exe_list[0], lang), ''
            elif len(exe_list) == 2:
                return make_abs(exe_list[1], lang), make_abs(exe_list[0], lang)
            else:
                mlog.debug('Failed to find a {} compiler for CMake. This might cause CMake to fail.'.format(lang))
                return fallback, ''

        c_comp, c_launcher = choose_compiler('c')
        cxx_comp, cxx_launcher = choose_compiler('cpp')
        fortran_comp, fortran_launcher = choose_compiler('fortran')

        # on Windows, choose_compiler returns path with \ as separator - replace by / before writing to CMAKE file
        c_comp = c_comp.replace('\\', '/')
        c_launcher = c_launcher.replace('\\', '/')
        cxx_comp = cxx_comp.replace('\\', '/')
        cxx_launcher = cxx_launcher.replace('\\', '/')
        fortran_comp = fortran_comp.replace('\\', '/')
        fortran_launcher = fortran_launcher.replace('\\', '/')

        # Reset the CMake cache
        (Path(build_dir) / 'CMakeCache.txt').write_text('CMAKE_PLATFORM_INFO_INITIALIZED:INTERNAL=1\n')

        # Fake the compiler files
        comp_dir = Path(build_dir) / 'CMakeFiles' / self.cmakevers
        comp_dir.mkdir(parents=True, exist_ok=True)

        c_comp_file = comp_dir / 'CMakeCCompiler.cmake'
        cxx_comp_file = comp_dir / 'CMakeCXXCompiler.cmake'
        fortran_comp_file = comp_dir / 'CMakeFortranCompiler.cmake'

        if c_comp and not c_comp_file.is_file():
            c_comp_file.write_text(textwrap.dedent('''\
                # Fake CMake file to skip the boring and slow stuff
                set(CMAKE_C_COMPILER "{}") # Should be a valid compiler for try_compile, etc.
                set(CMAKE_C_COMPILER_LAUNCHER "{}") # The compiler launcher (if presentt)
                set(CMAKE_C_COMPILER_ID "GNU") # Pretend we have found GCC
                set(CMAKE_COMPILER_IS_GNUCC 1)
                set(CMAKE_C_COMPILER_LOADED 1)
                set(CMAKE_C_COMPILER_WORKS TRUE)
                set(CMAKE_C_ABI_COMPILED TRUE)
                set(CMAKE_C_SOURCE_FILE_EXTENSIONS c;m)
                set(CMAKE_C_IGNORE_EXTENSIONS h;H;o;O;obj;OBJ;def;DEF;rc;RC)
                set(CMAKE_SIZEOF_VOID_P "{}")
            '''.format(c_comp, c_launcher, ctypes.sizeof(ctypes.c_voidp))))

        if cxx_comp and not cxx_comp_file.is_file():
            cxx_comp_file.write_text(textwrap.dedent('''\
                # Fake CMake file to skip the boring and slow stuff
                set(CMAKE_CXX_COMPILER "{}") # Should be a valid compiler for try_compile, etc.
                set(CMAKE_CXX_COMPILER_LAUNCHER "{}") # The compiler launcher (if presentt)
                set(CMAKE_CXX_COMPILER_ID "GNU") # Pretend we have found GCC
                set(CMAKE_COMPILER_IS_GNUCXX 1)
                set(CMAKE_CXX_COMPILER_LOADED 1)
                set(CMAKE_CXX_COMPILER_WORKS TRUE)
                set(CMAKE_CXX_ABI_COMPILED TRUE)
                set(CMAKE_CXX_IGNORE_EXTENSIONS inl;h;hpp;HPP;H;o;O;obj;OBJ;def;DEF;rc;RC)
                set(CMAKE_CXX_SOURCE_FILE_EXTENSIONS C;M;c++;cc;cpp;cxx;mm;CPP)
                set(CMAKE_SIZEOF_VOID_P "{}")
            '''.format(cxx_comp, cxx_launcher, ctypes.sizeof(ctypes.c_voidp))))

        if fortran_comp and not fortran_comp_file.is_file():
            fortran_comp_file.write_text(textwrap.dedent('''\
                # Fake CMake file to skip the boring and slow stuff
                set(CMAKE_Fortran_COMPILER "{}") # Should be a valid compiler for try_compile, etc.
                set(CMAKE_Fortran_COMPILER_LAUNCHER "{}") # The compiler launcher (if presentt)
                set(CMAKE_Fortran_COMPILER_ID "GNU") # Pretend we have found GCC
                set(CMAKE_COMPILER_IS_GNUG77 1)
                set(CMAKE_Fortran_COMPILER_LOADED 1)
                set(CMAKE_Fortran_COMPILER_WORKS TRUE)
                set(CMAKE_Fortran_ABI_COMPILED TRUE)
                set(CMAKE_Fortran_IGNORE_EXTENSIONS h;H;o;O;obj;OBJ;def;DEF;rc;RC)
                set(CMAKE_Fortran_SOURCE_FILE_EXTENSIONS f;F;fpp;FPP;f77;F77;f90;F90;for;For;FOR;f95;F95)
                set(CMAKE_SIZEOF_VOID_P "{}")
            '''.format(fortran_comp, fortran_launcher, ctypes.sizeof(ctypes.c_voidp))))

        return self.call(args, build_dir, env)

    def found(self) -> bool:
        return self.cmakebin is not None

    def version(self) -> str:
        return self.cmakevers

    def executable_path(self) -> str:
        return self.cmakebin.get_path()

    def get_command(self) -> T.List[str]:
        return self.cmakebin.get_command()

    def get_cmake_prefix_paths(self) -> T.List[str]:
        return self.prefix_paths

    def machine_choice(self) -> MachineChoice:
        return self.for_machine
