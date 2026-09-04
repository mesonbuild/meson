# SPDX-License-Identifier: Apache-2.0
# Copyright 2012-2017 The Meson development team

from __future__ import annotations

import functools
import os
import textwrap
import typing as T

from mesonbuild.mesonlib import (
    LibType,
    MesonException,
    version_compare,
)

from .. import mesonlib, options
from .compilers import (
    CompileCheckMode,
    Compiler,
    ManyInOneLinkerOptionStyle,
    clike_debug_args,
)
from .mixins.clang import ClangCompiler
from .mixins.clike import CLikeCompiler
from .mixins.elbrus import ElbrusCompiler
from .mixins.gnu import GnuCompiler, gnu_optimization_args
from .mixins.intel import IntelGnuLikeCompiler, IntelLLVMLikeCompiler, IntelVisualStudioLikeCompiler
from .mixins.pgi import PGICompiler

if T.TYPE_CHECKING:
    from ..build import BuildTarget
    from ..dependencies import Dependency
    from ..environment import Environment
    from ..linkers.linkers import DynamicLinker
    from ..mesonlib import MachineChoice
    from ..options import MutableKeyedOptionDictType


class FortranCompiler(CLikeCompiler, Compiler):

    language = 'fortran'

    def __init__(self, exelist: list[str], version: str, for_machine: MachineChoice,
                 env: Environment, linker: DynamicLinker | None = None,
                 full_version: str | None = None):
        Compiler.__init__(self, [], exelist, version, for_machine, env,
                          full_version=full_version, linker=linker)
        CLikeCompiler.__init__(self)

    def has_function(self, funcname: str, prefix: str, *,
                     extra_args: list[str] | None = None,
                     dependencies: list[Dependency] | None = None) -> tuple[bool, bool]:
        raise MesonException('Fortran does not have "has_function" capability.\n'
                             'It is better to test if a Fortran capability is working like:\n\n'
                             "meson.get_compiler('fortran').links('block; end block; end program')\n\n"
                             'that example is to see if the compiler has Fortran 2008 Block element.')

    def _get_basic_compiler_args(self, mode: CompileCheckMode) -> tuple[list[str], list[str]]:
        cargs = self.get_external_compile_args()
        largs = self.get_external_link_args()
        return cargs, largs

    def _sanity_check_source_code(self) -> str:
        return textwrap.dedent('''
            PROGRAM MAIN
                PRINT *, "Fortran compilation is working."
            END
            ''')

    def get_optimization_args(self, optimization_level: str) -> list[str]:
        return gnu_optimization_args[optimization_level]

    def get_debug_args(self, is_debug: bool) -> list[str]:
        return clike_debug_args[is_debug]

    def get_preprocess_only_args(self) -> list[str]:
        return ['-cpp'] + super().get_preprocess_only_args()

    def get_module_incdir_args(self) -> tuple[str, ...]:
        return ('-I', )

    def get_module_outdir_args(self, path: str) -> list[str]:
        return ['-module', path]

    def compute_parameters_with_absolute_paths(self, parameter_list: list[str],
                                               build_dir: str) -> list[str]:
        for idx, i in enumerate(parameter_list):
            if i[:2] == '-I' or i[:2] == '-L':
                parameter_list[idx] = i[:2] + os.path.normpath(os.path.join(build_dir, i[2:]))

        return parameter_list

    def module_name_to_filename(self, module_name: str) -> str:
        if '_' in module_name:  # submodule
            s = module_name.lower()
            if self.id in {'gcc', 'intel', 'intel-cl'}:
                filename = s.replace('_', '@') + '.smod'
            elif self.id in {'pgi', 'flang'}:
                filename = s.replace('_', '-') + '.mod'
            else:
                filename = s + '.mod'
        else:  # module
            filename = module_name.lower() + '.mod'

        return filename

    def find_library(self, libname: str, extra_dirs: list[str], libtype: LibType = LibType.PREFER_SHARED,
                     lib_prefix_warning: bool = True, ignore_system_dirs: bool = False,
                     skip_link_check: bool = False) -> list[str] | None:
        code = 'stop; end program'
        return self._find_library_impl(libname, extra_dirs, code, libtype, lib_prefix_warning, ignore_system_dirs, skip_link_check)

    def has_multi_arguments(self, args: list[str]) -> tuple[bool, bool]:
        return self._has_multi_arguments(args, 'stop; end program')

    def has_multi_link_arguments(self, args: list[str], to_host_args: bool = True) -> tuple[bool, bool]:
        return self._has_multi_link_arguments(args, 'stop; end program')

    def get_options(self) -> MutableKeyedOptionDictType:
        opts = super().get_options()

        key = self.form_compileropt_key('std')
        opts[key] = options.UserComboOption(
            self.make_option_name(key),
            'Fortran language standard to use',
            'none',
            choices=['none'])

        return opts

    def _compile_int(self, expression: str, prefix: str,
                     extra_args: None | list[str] | T.Callable[[CompileCheckMode], list[str]],
                     dependencies: list[Dependency] | None) -> bool:
        # Use a trick for emulating a static assert
        # Taken from https://github.com/j3-fortran/fortran_proposals/issues/70
        t = f'''program test
            {prefix}
            real(merge(kind(1.),-1,({expression}))), parameter :: fail = 1.
        end program test'''
        return self.compiles(t, extra_args=extra_args, dependencies=dependencies)[0]

    def _cross_compute_int(self, expression: str, low: int | None, high: int | None,
                           guess: int | None, prefix: str,
                           extra_args: None | list[str] | T.Callable[[CompileCheckMode], list[str]] = None,
                           dependencies: list[Dependency] | None = None) -> int:
        # This only difference between this implementation and that of CLikeCompiler
        # is a change in logical conjunction operator (.and. instead of &&)

        # Try user's guess first
        if isinstance(guess, int):
            if self._compile_int(f'{expression} == {guess}', prefix, extra_args, dependencies):
                return guess

        # If no bounds are given, compute them in the limit of int32
        maxint = 0x7fffffff
        minint = -0x80000000
        if not isinstance(low, int) or not isinstance(high, int):
            if self._compile_int(f'{expression} >= 0', prefix, extra_args, dependencies):
                low = cur = 0
                while self._compile_int(f'{expression} > {cur}', prefix, extra_args, dependencies):
                    low = cur + 1
                    if low > maxint:
                        raise mesonlib.EnvironmentException('Cross-compile check overflowed')
                    cur = min(cur * 2 + 1, maxint)
                high = cur
            else:
                high = cur = -1
                while self._compile_int(f'{expression} < {cur}', prefix, extra_args, dependencies):
                    high = cur - 1
                    if high < minint:
                        raise mesonlib.EnvironmentException('Cross-compile check overflowed')
                    cur = max(cur * 2, minint)
                low = cur
        else:
            # Sanity check limits given by user
            if high < low:
                raise mesonlib.EnvironmentException('high limit smaller than low limit')
            condition = f'{expression} <= {high} .and. {expression} >= {low}'
            if not self._compile_int(condition, prefix, extra_args, dependencies):
                raise mesonlib.EnvironmentException('Value out of given range')

        # Binary search
        while low != high:
            cur = low + int((high - low) / 2)
            if self._compile_int(f'{expression} <= {cur}', prefix, extra_args, dependencies):
                high = cur
            else:
                low = cur + 1

        return low

    def compute_int(self, expression: str, low: int | None, high: int | None,
                    guess: int | None, prefix: str, *,
                    extra_args: None | list[str] | T.Callable[[CompileCheckMode], list[str]],
                    dependencies: list[Dependency] | None = None) -> int:
        if extra_args is None:
            extra_args = []
        if self.is_cross:
            return self._cross_compute_int(expression, low, high, guess, prefix, extra_args, dependencies)
        t = f'''program test
            {prefix}
            print '(i0)', {expression}
        end program test
        '''
        res = self.run(t, extra_args=extra_args, dependencies=dependencies)
        if not res.compiled:
            return -1
        if res.returncode != 0:
            raise mesonlib.EnvironmentException('Could not run compute_int test binary.')
        return int(res.stdout)

    def _cross_sizeof(self, typename: str, prefix: str, *,
                      extra_args: None | list[str] | T.Callable[[CompileCheckMode], list[str]] = None,
                      dependencies: list[Dependency] | None = None) -> int:
        if extra_args is None:
            extra_args = []
        t = f'''program test
            use iso_c_binding
            {prefix}
            {typename} :: something
        end program test
        '''
        if not self.compiles(t, extra_args=extra_args,
                             dependencies=dependencies)[0]:
            return -1
        return self._cross_compute_int('c_sizeof(x)', None, None, None, prefix + '\nuse iso_c_binding\n' + typename + ' :: x', extra_args, dependencies)

    def sizeof(self, typename: str, prefix: str, *,
               extra_args: None | list[str] | T.Callable[[CompileCheckMode], list[str]] = None,
               dependencies: list[Dependency] | None = None) -> tuple[int, bool]:
        if extra_args is None:
            extra_args = []
        if self.is_cross:
            r = self._cross_sizeof(typename, prefix, extra_args=extra_args,
                                   dependencies=dependencies)
            return r, False
        t = f'''program test
            use iso_c_binding
            {prefix}
            {typename} :: x
            print '(i0)', c_sizeof(x)
        end program test
        '''
        res = self.cached_run(t, extra_args=extra_args,
                              dependencies=dependencies)
        if not res.compiled:
            return -1, False
        if res.returncode != 0:
            raise mesonlib.EnvironmentException('Could not run sizeof test binary.')
        return int(res.stdout), res.cached

    @functools.lru_cache
    def output_is_64bit(self) -> bool:
        '''
        returns true if the output produced is 64-bit, false if 32-bit
        '''
        return self.sizeof('type(c_ptr)', '')[0] == 8


class GnuFortranCompiler(GnuCompiler, FortranCompiler):

    def __init__(self, exelist: list[str], version: str, for_machine: MachineChoice,
                 env: Environment,
                 defines: dict[str, str] | None = None,
                 linker: DynamicLinker | None = None,
                 full_version: str | None = None):
        FortranCompiler.__init__(self, exelist, version, for_machine,
                                 env, linker=linker, full_version=full_version)
        GnuCompiler.__init__(self, defines)
        default_warn_args = ['-Wall']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic', '-fimplicit-none'],
                          'everything': default_warn_args + ['-Wextra', '-Wpedantic', '-fimplicit-none']}

    def get_options(self) -> MutableKeyedOptionDictType:
        opts = super().get_options()
        fortran_stds = ['legacy', 'f95', 'f2003']
        if version_compare(self.version, '>=4.4.0'):
            fortran_stds += ['f2008']
        if version_compare(self.version, '>=8.0.0'):
            fortran_stds += ['f2018']
        self._update_language_stds(opts, fortran_stds)
        return opts

    def get_option_std_args(self, target: BuildTarget, subproject: str | None = None) -> list[str]:
        args: list[str] = []
        std = self.get_compileropt_value('std', target, subproject)
        assert isinstance(std, str)
        if std != 'none':
            args.append('-std=' + std)
        return args

    def get_dependency_gen_args(self, outtarget: str, outfile: str) -> list[str]:
        # Disabled until this is fixed:
        # https://gcc.gnu.org/bugzilla/show_bug.cgi?id=62162
        # return ['-cpp', '-MD', '-MQ', outtarget]
        return []

    def get_module_outdir_args(self, path: str) -> list[str]:
        return ['-J' + path]

    def language_stdlib_only_link_flags(self) -> list[str]:
        # We need to apply the search prefix here, as these link arguments may
        # be passed to a different compiler with a different set of default
        # search paths, such as when using Clang for C/C++ and gfortran for
        # fortran,
        search_dirs: list[str] = []
        for d in self.get_compiler_dirs('libraries'):
            search_dirs.append(f'-L{d}')
        return search_dirs + ['-lgfortran', '-lm']

    def has_header(self, hname: str, prefix: str, *,
                   extra_args: None | list[str] | T.Callable[[CompileCheckMode], list[str]] = None,
                   dependencies: list[Dependency] | None = None,
                   disable_cache: bool = False) -> tuple[bool, bool]:
        '''
        Derived from mixins/clike.py:has_header, but without C-style usage of
        __has_include which breaks with GCC-Fortran 10:
        https://github.com/mesonbuild/meson/issues/7017
        '''
        code = f'{prefix}\n#include <{hname}>'
        return self.compiles(code, extra_args=extra_args,
                             dependencies=dependencies, mode=CompileCheckMode.PREPROCESS, disable_cache=disable_cache)


class ElbrusFortranCompiler(ElbrusCompiler, FortranCompiler):
    def __init__(self, exelist: list[str], version: str, for_machine: MachineChoice,
                 env: Environment,
                 defines: dict[str, str] | None = None,
                 linker: DynamicLinker | None = None,
                 full_version: str | None = None):
        FortranCompiler.__init__(self, exelist, version, for_machine,
                                 env, linker=linker, full_version=full_version)
        ElbrusCompiler.__init__(self)

    def get_options(self) -> MutableKeyedOptionDictType:
        opts = super().get_options()
        self._update_language_stds(opts, ['f95', 'f2003', 'f2008', 'gnu', 'legacy', 'f2008ts'])
        return opts

    def get_module_outdir_args(self, path: str) -> list[str]:
        return ['-J' + path]

    def language_stdlib_only_link_flags(self) -> list[str]:
        # No need to add search paths here, because LCC ships everything
        # (C, C++, Fortran) and always knows where to look for its stuff
        return ['-lgfortran', '-lm']


class G95FortranCompiler(FortranCompiler):

    LINKER_OPTION_STYLE = ManyInOneLinkerOptionStyle('-Wl,', ',')
    id = 'g95'

    def __init__(self, exelist: list[str], version: str, for_machine: MachineChoice,
                 env: Environment, linker: DynamicLinker | None = None,
                 full_version: str | None = None):
        FortranCompiler.__init__(self, exelist, version, for_machine,
                                 env, linker=linker, full_version=full_version)
        default_warn_args = ['-Wall']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-pedantic'],
                          'everything': default_warn_args + ['-Wextra', '-pedantic']}

    def get_module_outdir_args(self, path: str) -> list[str]:
        return ['-fmod=' + path]


class SunFortranCompiler(FortranCompiler):

    LINKER_OPTION_STYLE = ManyInOneLinkerOptionStyle('-Wl,', ',')
    id = 'sun'

    def get_dependency_gen_args(self, outtarget: str, outfile: str) -> list[str]:
        return ['-fpp']

    def get_always_args(self) -> list[str]:
        return []

    def get_warn_args(self, level: str) -> list[str]:
        return []

    def get_module_incdir_args(self) -> tuple[str, ...]:
        return ('-M', )

    def get_module_outdir_args(self, path: str) -> list[str]:
        return ['-moddir=' + path]

    def openmp_flags(self) -> list[str]:
        return ['-xopenmp']


class IntelFortranCompiler(IntelGnuLikeCompiler, FortranCompiler):

    id = 'intel'

    def __init__(self, exelist: list[str], version: str, for_machine: MachineChoice,
                 env: Environment, linker: DynamicLinker | None = None,
                 full_version: str | None = None):
        FortranCompiler.__init__(self, exelist, version, for_machine,
                                 env, linker=linker, full_version=full_version)
        # FIXME: Add support for OS X and Windows in detect_fortran_compiler so
        # we are sent the type of compiler
        IntelGnuLikeCompiler.__init__(self)
        self.file_suffixes = ('f90', 'f', 'for', 'ftn', 'fpp', )
        default_warn_args = ['-warn', 'general', '-warn', 'truncated_source']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args + ['-warn', 'unused'],
                          '3': ['-warn', 'all'],
                          'everything': ['-warn', 'all']}

    def get_options(self) -> MutableKeyedOptionDictType:
        opts = super().get_options()
        self._update_language_stds(opts, ['none', 'legacy', 'f95', 'f2003', 'f2008', 'f2018'])
        return opts

    def get_option_std_args(self, target: BuildTarget, subproject: str | None = None) -> list[str]:
        args: list[str] = []
        std = self.get_compileropt_value('std', target, subproject)
        stds = {'legacy': 'none', 'f95': 'f95', 'f2003': 'f03', 'f2008': 'f08', 'f2018': 'f18'}
        assert isinstance(std, str)
        if std != 'none':
            args.append('-stand=' + stds[std])
        return args

    def get_preprocess_only_args(self) -> list[str]:
        return ['-cpp', '-EP']

    def get_werror_args(self) -> list[str]:
        return ['-warn', 'errors']

    def language_stdlib_only_link_flags(self) -> list[str]:
        # TODO: needs default search path added
        return ['-lifcore', '-limf']

    def get_dependency_gen_args(self, outtarget: str, outfile: str) -> list[str]:
        return ['-gen-dep=' + outtarget, '-gen-depformat=make']


class IntelLLVMFortranCompiler(IntelLLVMLikeCompiler, IntelFortranCompiler):

    id = 'intel-llvm'

    def get_preprocess_only_args(self) -> list[str]:
        return ['-preprocess-only']

    def get_dependency_gen_args(self, outtarget: str, outfile: str) -> list[str]:
        return []

class IntelClFortranCompiler(IntelVisualStudioLikeCompiler, FortranCompiler):

    always_args = ['/nologo']

    def __init__(self, exelist: list[str], version: str, for_machine: MachineChoice,
                 env: Environment, target: str,
                 linker: DynamicLinker | None = None,
                 full_version: str | None = None):
        FortranCompiler.__init__(self, exelist, version, for_machine,
                                 env, linker=linker, full_version=full_version)
        IntelVisualStudioLikeCompiler.__init__(self, target)
        self.file_suffixes = ('f90', 'f', 'for', 'ftn', 'fpp', )

        default_warn_args = ['/warn:general', '/warn:truncated_source']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args + ['/warn:unused'],
                          '3': ['/warn:all'],
                          'everything': ['/warn:all']}

    def get_options(self) -> MutableKeyedOptionDictType:
        opts = super().get_options()
        self._update_language_stds(opts, ['none', 'legacy', 'f95', 'f2003', 'f2008', 'f2018'])
        return opts

    def get_option_std_args(self, target: BuildTarget, subproject: str | None = None) -> list[str]:
        args: list[str] = []
        std = self.get_compileropt_value('std', target, subproject)
        stds = {'legacy': 'none', 'f95': 'f95', 'f2003': 'f03', 'f2008': 'f08', 'f2018': 'f18'}
        assert isinstance(std, str)
        if std != 'none':
            args.append('/stand:' + stds[std])
        return args

    def get_werror_args(self) -> list[str]:
        return ['/warn:errors']

    def get_module_outdir_args(self, path: str) -> list[str]:
        return ['/module:' + path]


class IntelLLVMClFortranCompiler(IntelClFortranCompiler):

    id = 'intel-llvm-cl'

class PathScaleFortranCompiler(FortranCompiler):

    id = 'pathscale'

    def __init__(self, exelist: list[str], version: str, for_machine: MachineChoice,
                 env: Environment, linker: DynamicLinker | None = None,
                 full_version: str | None = None):
        FortranCompiler.__init__(self, exelist, version, for_machine,
                                 env, linker=linker, full_version=full_version)
        default_warn_args = ['-fullwarn']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args,
                          '3': default_warn_args,
                          'everything': default_warn_args}

    def openmp_flags(self) -> list[str]:
        return ['-mp']


class PGIFortranCompiler(PGICompiler, FortranCompiler):

    def __init__(self, exelist: list[str], version: str, for_machine: MachineChoice,
                 env: Environment, linker: DynamicLinker | None = None,
                 full_version: str | None = None):
        FortranCompiler.__init__(self, exelist, version, for_machine,
                                 env, linker=linker, full_version=full_version)
        PGICompiler.__init__(self)

        default_warn_args = ['-Minform=inform']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args,
                          '3': default_warn_args + ['-Mdclchk'],
                          'everything': default_warn_args + ['-Mdclchk']}

    def language_stdlib_only_link_flags(self) -> list[str]:
        # TODO: needs default search path added
        return ['-lpgf90rtl', '-lpgf90', '-lpgf90_rpm1', '-lpgf902',
                '-lpgf90rtl', '-lpgftnrtl', '-lrt']


class NvidiaHPC_FortranCompiler(PGICompiler, FortranCompiler):

    id = 'nvidia_hpc'

    def __init__(self, exelist: list[str], version: str, for_machine: MachineChoice,
                 env: Environment, linker: DynamicLinker | None = None,
                 full_version: str | None = None):
        FortranCompiler.__init__(self, exelist, version, for_machine,
                                 env, linker=linker, full_version=full_version)
        PGICompiler.__init__(self)

        default_warn_args = ['-Minform=inform']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args,
                          '3': default_warn_args + ['-Mdclchk'],
                          'everything': default_warn_args + ['-Mdclchk']}


class ClassicFlangFortranCompiler(ClangCompiler, FortranCompiler):

    id = 'flang'

    def __init__(self, exelist: list[str], version: str, for_machine: MachineChoice,
                 env: Environment, linker: DynamicLinker | None = None,
                 full_version: str | None = None):
        FortranCompiler.__init__(self, exelist, version, for_machine,
                                 env, linker=linker, full_version=full_version)
        ClangCompiler.__init__(self, {})
        default_warn_args = ['-Minform=inform']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args,
                          '3': default_warn_args,
                          'everything': default_warn_args}

    def language_stdlib_only_link_flags(self) -> list[str]:
        # We need to apply the search prefix here, as these link arguments may
        # be passed to a different compiler with a different set of default
        # search paths, such as when using Clang for C/C++ and gfortran for
        # fortran,
        # XXX: Untested....
        search_dirs: list[str] = []
        for d in self.get_compiler_dirs('libraries'):
            search_dirs.append(f'-L{d}')
        return search_dirs + ['-lflang', '-lpgmath']


class ArmLtdFlangFortranCompiler(ClassicFlangFortranCompiler):

    id = 'armltdflang'


class LlvmFlangFortranCompiler(ClangCompiler, FortranCompiler):

    id = 'llvm-flang'

    def __init__(self, exelist: list[str], version: str, for_machine: MachineChoice,
                 env: Environment, linker: DynamicLinker | None = None,
                 full_version: str | None = None):
        FortranCompiler.__init__(self, exelist, version, for_machine,
                                 env, linker=linker, full_version=full_version)
        ClangCompiler.__init__(self, {})
        default_warn_args = ['-Wall']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args,
                          '3': default_warn_args,
                          'everything': default_warn_args}

    def get_colorout_args(self, colortype: str) -> list[str]:
        # not yet supported, see https://github.com/llvm/llvm-project/issues/89888
        return []

    def get_dependency_gen_args(self, outtarget: str, outfile: str) -> list[str]:
        # not yet supported, see https://github.com/llvm/llvm-project/issues/89888
        return []

    def get_module_outdir_args(self, path: str) -> list[str]:
        # different syntax from classic flang (which supported `-module`), see
        # https://github.com/llvm/llvm-project/issues/66969
        return ['-module-dir', path]

    def gnu_symbol_visibility_args(self, vistype: str) -> list[str]:
        # flang doesn't support symbol visibility flag yet, see
        # https://github.com/llvm/llvm-project/issues/92459
        return []

    def language_stdlib_only_link_flags(self) -> list[str]:
        # matching setup from ClassicFlangFortranCompiler
        search_dirs: list[str] = []
        for d in self.get_compiler_dirs('libraries'):
            search_dirs.append(f'-L{d}')
        # does not automatically link to Fortran_main anymore after
        # https://github.com/llvm/llvm-project/commit/9d6837d595719904720e5ff68ec1f1a2665bdc2f
        # note that this changed again in flang 19 with
        # https://github.com/llvm/llvm-project/commit/8d5386669ed63548daf1bee415596582d6d78d7d;
        # it seems flang 18 doesn't work if something accidentally includes a program unit, see
        # https://github.com/llvm/llvm-project/issues/92496
        # Only link FortranRuntime and FortranDecimal for flang < 19, see
        # https://github.com/scipy/scipy/issues/21562#issuecomment-2942938509
        if version_compare(self.version, '<19'):
            search_dirs += ['-lFortranRuntime', '-lFortranDecimal']
        return search_dirs


class Open64FortranCompiler(FortranCompiler):

    id = 'open64'

    def __init__(self, exelist: list[str], version: str, for_machine: MachineChoice,
                 env: Environment, linker: DynamicLinker | None = None,
                 full_version: str | None = None):
        FortranCompiler.__init__(self, exelist, version, for_machine,
                                 env, linker=linker, full_version=full_version)
        default_warn_args = ['-fullwarn']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args,
                          '3': default_warn_args,
                          'everything': default_warn_args}

    def openmp_flags(self) -> list[str]:
        return ['-mp']


class NAGFortranCompiler(FortranCompiler):

    id = 'nagfor'

    def __init__(self, exelist: list[str], version: str, for_machine: MachineChoice,
                 env: Environment, linker: DynamicLinker | None = None,
                 full_version: str | None = None):
        FortranCompiler.__init__(self, exelist, version, for_machine,
                                 env, linker=linker, full_version=full_version)
        # Warnings are on by default; -w disables (by category):
        self.warn_args = {
            '0': ['-w=all'],
            '1': [],
            '2': [],
            '3': [],
            'everything': [],
        }

    def get_always_args(self) -> list[str]:
        return self.get_nagfor_quiet(self.version)

    def get_module_outdir_args(self, path: str) -> list[str]:
        return ['-mdir', path]

    @staticmethod
    def get_nagfor_quiet(version: str) -> list[str]:
        return ['-quiet'] if version_compare(version, '>=7100') else []

    def get_pic_args(self) -> list[str]:
        return ['-PIC']

    def get_preprocess_only_args(self) -> list[str]:
        return ['-fpp']

    def get_std_exe_link_args(self) -> list[str]:
        return self.get_always_args()

    def openmp_flags(self) -> list[str]:
        return ['-openmp']
