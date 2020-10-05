# Copyright 2020 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .._pathlib import Path
from ..envconfig import CMakeSkipCompilerTest
from ..mesonlib import MachineChoice
from .common import language_map
from .. import mlog

import shutil
import typing as T
from enum import Enum
from textwrap import dedent

if T.TYPE_CHECKING:
    from ..envconfig import MachineInfo, Properties, CMakeVariables
    from ..environment import Environment
    from ..compilers import Compiler


_MESON_TO_CMAKE_MAPPING = {
    'arm':          'ARMCC',
    'armclang':     'ARMClang',
    'clang':        'Clang',
    'clang-cl':     'MSVC',
    'flang':        'Flang',
    'g95':          'G95',
    'gcc':          'GNU',
    'intel':        'Intel',
    'intel-cl':     'MSVC',
    'msvc':         'MSVC',
    'pathscale':    'PathScale',
    'pgi':          'PGI',
    'sun':          'SunPro',
}

class CMakeExecScope(Enum):
    SUBPROJECT = 'subproject'
    DEPENDENCY = 'dependency'

class CMakeToolchain:
    def __init__(self, env: 'Environment', for_machine: MachineChoice, exec_scope: CMakeExecScope, out_dir: Path, preload_file: T.Optional[Path] = None) -> None:
        self.env            = env
        self.for_machine    = for_machine
        self.exec_scope     = exec_scope
        self.preload_file   = preload_file
        self.toolchain_file = out_dir / 'CMakeMesonToolchainFile.cmake'
        self.toolchain_file = self.toolchain_file.resolve()
        self.minfo          = self.env.machines[self.for_machine]
        self.properties     = self.env.properties[self.for_machine]
        self.compilers      = self.env.coredata.compilers[self.for_machine]
        self.cmakevars      = self.env.cmakevars[self.for_machine]

        self.variables = self.get_defaults()
        self.variables.update(self.cmakevars.get_variables())

        assert self.toolchain_file.is_absolute()

    def write(self) -> Path:
        if not self.toolchain_file.parent.exists():
            self.toolchain_file.parent.mkdir(parents=True)
        self.toolchain_file.write_text(self.generate())
        mlog.cmd_ci_include(self.toolchain_file.as_posix())
        return self.toolchain_file

    def get_cmake_args(self) -> T.List[str]:
        args = ['-DCMAKE_TOOLCHAIN_FILE=' + self.toolchain_file.as_posix()]
        if self.preload_file is not None:
            args += ['-DMESON_PRELOAD_FILE=' + self.preload_file.as_posix()]
        return args

    def generate(self) -> str:
        res = dedent('''\
            ######################################
            ###  AUTOMATICALLY GENERATED FILE  ###
            ######################################

            # This file was generated from the configuration in the
            # relevant meson machine file. See the meson documentation
            # https://mesonbuild.com/Machine-files.html for more information

            if(DEFINED MESON_PRELOAD_FILE)
                include("${MESON_PRELOAD_FILE}")
            endif()

        ''')

        # Escape all \ in the values
        for key, value in self.variables.items():
            self.variables[key] = [x.replace('\\', '/') for x in value]

        # Set variables from the current machine config
        res += '# Variables from meson\n'
        for key, value in self.variables.items():
            res += 'set(' + key
            for i in value:
                res += ' "{}"'.format(i)

            res += ')\n'
        res += '\n'

        # Add the user provided toolchain file
        user_file = self.properties.get_cmake_toolchain_file()
        if user_file is not None:
            res += dedent('''
                # Load the CMake toolchain file specified by the user
                include("{}")

            '''.format(user_file.as_posix()))

        return res

    def get_defaults(self) -> T.Dict[str, T.List[str]]:
        defaults = {}  # type: T.Dict[str, T.List[str]]

        # Do nothing if the user does not want automatic defaults
        if not self.properties.get_cmake_defaults():
            return defaults

        # Best effort to map the meson system name to CMAKE_SYSTEM_NAME, which
        # is not trivial since CMake lacks a list of all supported
        # CMAKE_SYSTEM_NAME values.
        SYSTEM_MAP = {
            'android': 'Android',
            'linux': 'Linux',
            'windows': 'Windows',
            'freebsd': 'FreeBSD',
            'darwin': 'Darwin',
        }  # type: T.Dict[str, str]

        # Only set these in a cross build. Otherwise CMake will trip up in native
        # builds and thing they are cross (which causes TRY_RUN() to break)
        if self.env.is_cross_build(when_building_for=self.for_machine):
            defaults['CMAKE_SYSTEM_NAME']      = [SYSTEM_MAP.get(self.minfo.system, self.minfo.system)]
            defaults['CMAKE_SYSTEM_PROCESSOR'] = [self.minfo.cpu_family]

        defaults['CMAKE_SIZEOF_VOID_P'] = ['8' if self.minfo.is_64_bit else '4']

        sys_root = self.properties.get_sys_root()
        if sys_root:
            defaults['CMAKE_SYSROOT'] = [sys_root]

        # Determine whether CMake the compiler test should be skipped
        skip_check = self.properties.get_cmake_skip_compiler_test() == CMakeSkipCompilerTest.ALWAYS
        if self.properties.get_cmake_skip_compiler_test() == CMakeSkipCompilerTest.DEP_ONLY and self.exec_scope == CMakeExecScope.DEPENDENCY:
            skip_check = True

        def make_abs(exe: str) -> str:
            if Path(exe).is_absolute():
                return exe

            p = shutil.which(exe)
            if p is None:
                return exe
            return p

        # Set the compiler variables
        for lang, comp_obj in self.compilers.items():
            exe_list = [make_abs(x) for x in comp_obj.get_exelist()]
            comp_id = CMakeToolchain.meson_compiler_to_cmake_id(comp_obj)
            comp_version = comp_obj.version.upper()

            prefix = 'CMAKE_{}_'.format(language_map.get(lang, lang.upper()))

            if not exe_list:
                continue
            elif len(exe_list) == 2:
                defaults[prefix + 'COMPILER']          = [exe_list[1]]
                defaults[prefix + 'COMPILER_LAUNCHER'] = [exe_list[0]]
            else:
                defaults[prefix + 'COMPILER'] = exe_list
            if comp_obj.get_id() == 'clang-cl':
                defaults['CMAKE_LINKER'] = comp_obj.get_linker_exelist()

            # Setting the variables after this check cause CMake to skip
            # validating the compiler
            if not skip_check:
                continue

            defaults[prefix + 'COMPILER_ID']      = [comp_id]
            defaults[prefix + 'COMPILER_VERSION'] = [comp_version]
            #defaults[prefix + 'COMPILER_LOADED']  = ['1']
            defaults[prefix + 'COMPILER_FORCED']  = ['1']
            defaults[prefix + 'COMPILER_WORKS']   = ['TRUE']
            #defaults[prefix + 'ABI_COMPILED']     = ['TRUE']

        return defaults

    @staticmethod
    def meson_compiler_to_cmake_id(cobj: 'Compiler') -> str:
        """Translate meson compiler's into CMAKE compiler ID's.

        Most of these can be handled by a simple table lookup, with a few
        exceptions.

        Clang and Apple's Clang are both identified as "clang" by meson. To make
        things more complicated gcc and vanilla clang both use Apple's ld64 on
        macOS. The only way to know for sure is to do an isinstance() check.
        """
        from ..compilers import (AppleClangCCompiler, AppleClangCPPCompiler,
                                AppleClangObjCCompiler, AppleClangObjCPPCompiler)
        if isinstance(cobj, (AppleClangCCompiler, AppleClangCPPCompiler,
                            AppleClangObjCCompiler, AppleClangObjCPPCompiler)):
            return 'AppleClang'
        # If no mapping, try GNU and hope that the build files don't care
        return _MESON_TO_CMAKE_MAPPING.get(cobj.get_id(), 'GNU')
