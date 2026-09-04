# SPDX-License-Identifier: Apache-2.0
# Copyright 2012-2017 The Meson development team

from __future__ import annotations

import os.path
import re
import subprocess
import typing as T

from .. import mlog, options
from ..mesonlib import MesonException, first, version_compare
from .compilers import CompileCheckMode, Compiler, PrefixArgumentLinkerOptionStyle, clike_debug_args

if T.TYPE_CHECKING:
    from .. import build
    from ..compilers.compilers import Language
    from ..dependencies import Dependency
    from ..environment import Environment
    from ..linkers.linkers import DynamicLinker
    from ..mesonlib import MachineChoice
    from ..options import MutableKeyedOptionDictType

swift_optimization_args: dict[str, list[str]] = {
    'plain': [],
    '0': [],
    'g': [],
    '1': ['-O'],
    '2': ['-O'],
    '3': ['-O'],
    's': ['-O'],
}

class SwiftCompiler(Compiler):

    LINKER_OPTION_STYLE = PrefixArgumentLinkerOptionStyle('-Xlinker')
    language = 'swift'
    id = 'llvm'

    def __init__(self, exelist: list[str], version: str, for_machine: MachineChoice,
                 env: Environment, full_version: str | None = None,
                 linker: DynamicLinker | None = None):
        super().__init__([], exelist, version, for_machine, env,
                         full_version=full_version, linker=linker)
        self.version = version
        if self.info.is_darwin():
            try:
                self.sdk_path = subprocess.check_output(['xcrun', '--show-sdk-path'],
                                                        universal_newlines=True,
                                                        encoding='utf-8', stderr=subprocess.STDOUT).strip()
            except subprocess.CalledProcessError as e:
                mlog.error("Failed to get Xcode SDK path: " + e.output)
                raise MesonException('Xcode license not accepted yet. Run `sudo xcodebuild -license`.')
            except FileNotFoundError:
                mlog.error('xcrun not found. Install Xcode to compile Swift code.')
                raise MesonException('Could not detect Xcode. Please install it to compile Swift code.')

    def get_pic_args(self) -> list[str]:
        return []

    def get_pie_args(self) -> list[str]:
        return []

    def needs_static_linker(self) -> bool:
        return True

    def get_werror_args(self) -> list[str]:
        return ['-warnings-as-errors']

    def get_dependency_gen_args(self, outtarget: str, outfile: str) -> list[str]:
        return ['-emit-dependencies']

    def get_dependency_compile_args(self, dep: Dependency) -> list[str]:
        args = dep.get_compile_args()
        # Some deps might sneak in a hardcoded path to an older macOS SDK, which can
        # cause compilation errors. Let's replace all .sdk paths with the current one.
        # SwiftPM does it this way: https://github.com/swiftlang/swift-package-manager/pull/6772
        # Not tested on anything else than macOS for now.
        if not self.info.is_darwin():
            return args
        pattern = re.compile(r'.*\/MacOSX[^\/]*\.sdk(\/.*|$)')
        for i, arg in enumerate(args):
            if arg.startswith('-I'):
                match = pattern.match(arg)
                if match:
                    args[i] = '-I' + self.sdk_path + match.group(1)
        return args

    def depfile_for_object(self, objfile: str) -> str | None:
        return os.path.splitext(objfile)[0] + '.' + self.get_depfile_suffix()

    def get_depfile_suffix(self) -> str:
        return 'd'

    def get_output_args(self, target: str) -> list[str]:
        return ['-o', target]

    def get_header_import_args(self, headername: str) -> list[str]:
        return ['-import-objc-header', headername]

    def get_warn_args(self, level: str) -> list[str]:
        return []

    def get_std_exe_link_args(self) -> list[str]:
        return ['-emit-executable']

    def get_module_args(self, modname: str) -> list[str]:
        return ['-module-name', modname]

    def get_mod_gen_args(self) -> list[str]:
        return ['-emit-module']

    def get_include_args(self, path: str, is_system: bool) -> list[str]:
        return ['-I' + path]

    def get_compile_only_args(self) -> list[str]:
        return ['-c']

    def get_options(self) -> MutableKeyedOptionDictType:
        opts = super().get_options()

        key = self.form_compileropt_key('std')
        opts[key] = options.UserComboOption(
            self.make_option_name(key),
            'Swift language version.',
            'none',
            # List them with swiftc -frontend -swift-version ''
            choices=['none', '4', '4.2', '5', '6'])

        return opts

    def get_option_std_args(self, target: build.BuildTarget, subproject: str | None = None) -> list[str]:
        args: list[str] = []

        std = self.get_compileropt_value('std', target, subproject)
        assert isinstance(std, str)

        if std != 'none':
            args += ['-swift-version', std]

        # Pass C compiler -std=... arg to swiftc
        c_langs: list[Language] = ['objc', 'c']
        if target.uses_swift_cpp_interop():
            c_langs = ['objcpp', 'cpp', *c_langs]

        c_lang = first(c_langs, lambda x: x in target.compilers)
        if c_lang is not None:
            cc = target.compilers[c_lang]
            args.extend(arg for c_arg in cc.get_option_std_args(target, subproject) for arg in ['-Xcc', c_arg])

        return args

    def get_working_directory_args(self, path: str) -> list[str] | None:
        if version_compare(self.version, '<4.2'):
            return None

        return ['-working-directory', path]

    def get_cxx_interoperability_args(self, target: build.BuildTarget | None = None) -> list[str]:
        if target is not None and not target.uses_swift_cpp_interop():
            return []

        if version_compare(self.version, '<5.9'):
            raise MesonException(f'Compiler {self} does not support C++ interoperability')

        return ['-cxx-interoperability-mode=default']

    def get_library_args(self) -> list[str]:
        return ['-parse-as-library']

    def compute_parameters_with_absolute_paths(self, parameter_list: list[str],
                                               build_dir: str) -> list[str]:
        for idx, i in enumerate(parameter_list):
            if i[:2] == '-I' or i[:2] == '-L':
                parameter_list[idx] = i[:2] + os.path.normpath(os.path.join(build_dir, i[2:]))

        return parameter_list

    def _sanity_check_compile_args(self, sourcename: str, binname: str
                                   ) -> tuple[list[str], list[str]]:
        args, largs = super()._sanity_check_compile_args(sourcename, binname)
        if self._sanity_check_mode() is CompileCheckMode.LINK:
            largs.extend(self.get_std_exe_link_args())
        return args, largs

    def _sanity_check_source_code(self) -> str:
        return 'print("Swift compilation is working.")'

    def get_debug_args(self, is_debug: bool) -> list[str]:
        return clike_debug_args[is_debug]

    def get_optimization_args(self, optimization_level: str) -> list[str]:
        return swift_optimization_args[optimization_level]
