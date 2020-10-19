# Copyright 2012-2017 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os.path
import typing as T

from .. import coredata
from ..mesonlib import MachineChoice, MesonException, mlog, version_compare
from ..linkers import LinkerEnvVarsMixin
from .c_function_attributes import C_FUNC_ATTRIBUTES
from .mixins.clike import CLikeCompiler
from .mixins.ccrx import CcrxCompiler
from .mixins.xc16 import Xc16Compiler
from .mixins.compcert import CompCertCompiler
from .mixins.c2000 import C2000Compiler
from .mixins.arm import ArmCompiler, ArmclangCompiler
from .mixins.visualstudio import MSVCCompiler, ClangClCompiler
from .mixins.gnu import GnuCompiler
from .mixins.intel import IntelGnuLikeCompiler, IntelVisualStudioLikeCompiler
from .mixins.clang import ClangCompiler
from .mixins.elbrus import ElbrusCompiler
from .mixins.pgi import PGICompiler
from .mixins.emscripten import EmscriptenMixin
from .compilers import (
    gnu_winlibs,
    msvc_winlibs,
    Compiler,
)

if T.TYPE_CHECKING:
    from ..coredata import OptionDictType
    from ..dependencies import Dependency, ExternalProgram
    from ..envconfig import MachineInfo
    from ..environment import Environment
    from ..linkers import DynamicLinker

    CompilerMixinBase = Compiler
else:
    CompilerMixinBase = object



class CCompiler(CLikeCompiler, Compiler):

    @staticmethod
    def attribute_check_func(name: str) -> str:
        try:
            return C_FUNC_ATTRIBUTES[name]
        except KeyError:
            raise MesonException('Unknown function attribute "{}"'.format(name))

    language = 'c'

    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice, is_cross: bool,
                 info: 'MachineInfo', exe_wrapper: T.Optional['ExternalProgram'] = None,
                 linker: T.Optional['DynamicLinker'] = None,
                 full_version: T.Optional[str] = None):
        # If a child ObjC or CPP class has already set it, don't set it ourselves
        Compiler.__init__(self, exelist, version, for_machine, info,
                          is_cross=is_cross, full_version=full_version, linker=linker)
        CLikeCompiler.__init__(self, exe_wrapper)

    def get_no_stdinc_args(self) -> T.List[str]:
        return ['-nostdinc']

    def sanity_check(self, work_dir: str, environment: 'Environment') -> None:
        code = 'int main(void) { int class=0; return class; }\n'
        return self._sanity_check_impl(work_dir, environment, 'sanitycheckc.c', code)

    def has_header_symbol(self, hname: str, symbol: str, prefix: str,
                          env: 'Environment', *,
                          extra_args: T.Optional[T.List[str]] = None,
                          dependencies: T.Optional[T.List['Dependency']] = None) -> T.Tuple[bool, bool]:
        fargs = {'prefix': prefix, 'header': hname, 'symbol': symbol}
        t = '''{prefix}
        #include <{header}>
        int main(void) {{
            /* If it's not defined as a macro, try to use as a symbol */
            #ifndef {symbol}
                {symbol};
            #endif
            return 0;
        }}'''
        return self.compiles(t.format(**fargs), env, extra_args=extra_args,
                             dependencies=dependencies)


class ClangCCompiler(ClangCompiler, CCompiler):

    _C17_VERSION = '>=6.0.0'
    _C18_VERSION = '>=8.0.0'
    _C2X_VERSION = '>=9.0.0'

    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice, is_cross: bool,
                 info: 'MachineInfo', exe_wrapper: T.Optional['ExternalProgram'] = None,
                 linker: T.Optional['DynamicLinker'] = None,
                 defines: T.Optional[T.Dict[str, str]] = None,
                 full_version: T.Optional[str] = None):
        CCompiler.__init__(self, exelist, version, for_machine, is_cross, info, exe_wrapper, linker=linker, full_version=full_version)
        ClangCompiler.__init__(self, defines)
        default_warn_args = ['-Wall', '-Winvalid-pch']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}

    def get_options(self) -> 'OptionDictType':
        opts = CCompiler.get_options(self)
        c_stds = ['c89', 'c99', 'c11']
        g_stds = ['gnu89', 'gnu99', 'gnu11']
        # https://releases.llvm.org/6.0.0/tools/clang/docs/ReleaseNotes.html
        # https://en.wikipedia.org/wiki/Xcode#Latest_versions
        if version_compare(self.version, self._C17_VERSION):
            c_stds += ['c17']
            g_stds += ['gnu17']
        if version_compare(self.version, self._C18_VERSION):
            c_stds += ['c18']
            g_stds += ['gnu18']
        if version_compare(self.version, self._C2X_VERSION):
            c_stds += ['c2x']
            g_stds += ['gnu2x']
        opts.update({
            'std': coredata.UserComboOption(
                'C language standard to use',
                ['none'] + c_stds + g_stds,
                'none',
            ),
        })
        if self.info.is_windows() or self.info.is_cygwin():
            opts.update({
                'winlibs': coredata.UserArrayOption(
                    'Standard Win libraries to link against',
                    gnu_winlibs,
                ),
            })
        return opts

    def get_option_compile_args(self, options: 'OptionDictType') -> T.List[str]:
        args = []
        std = options['std']
        if std.value != 'none':
            args.append('-std=' + std.value)
        return args

    def get_option_link_args(self, options: 'OptionDictType') -> T.List[str]:
        if self.info.is_windows() or self.info.is_cygwin():
            # without a typedict mypy can't understand this.
            libs = options['winlibs'].value.copy()
            assert isinstance(libs, list)
            for l in libs:
                assert isinstance(l, str)
            return libs
        return []


class AppleClangCCompiler(ClangCCompiler):

    """Handle the differences between Apple Clang and Vanilla Clang.

    Right now this just handles the differences between the versions that new
    C standards were added.
    """

    _C17_VERSION = '>=10.0.0'
    _C18_VERSION = '>=11.0.0'
    _C2X_VERSION = '>=11.0.0'


class EmscriptenCCompiler(EmscriptenMixin, LinkerEnvVarsMixin, ClangCCompiler):
    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice, is_cross: bool,
                 info: 'MachineInfo', exe_wrapper: T.Optional['ExternalProgram'] = None,
                 linker: T.Optional['DynamicLinker'] = None,
                 defines: T.Optional[T.Dict[str, str]] = None,
                 full_version: T.Optional[str] = None):
        if not is_cross:
            raise MesonException('Emscripten compiler can only be used for cross compilation.')
        ClangCCompiler.__init__(self, exelist, version, for_machine, is_cross,
                                info, exe_wrapper=exe_wrapper, linker=linker,
                                defines=defines, full_version=full_version)
        self.id = 'emscripten'


class ArmclangCCompiler(ArmclangCompiler, CCompiler):
    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice, is_cross: bool,
                 info: 'MachineInfo', exe_wrapper: T.Optional['ExternalProgram'] = None,
                 linker: T.Optional['DynamicLinker'] = None,
                 full_version: T.Optional[str] = None):
        CCompiler.__init__(self, exelist, version, for_machine, is_cross,
                           info, exe_wrapper, linker=linker, full_version=full_version)
        ArmclangCompiler.__init__(self)
        default_warn_args = ['-Wall', '-Winvalid-pch']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}

    def get_options(self) -> 'OptionDictType':
        opts = CCompiler.get_options(self)
        opts.update({
            'std': coredata.UserComboOption(
                'C language standard to use',
                ['none', 'c90', 'c99', 'c11', 'gnu90', 'gnu99', 'gnu11'],
                'none',
            ),
        })
        return opts

    def get_option_compile_args(self, options: 'OptionDictType') -> T.List[str]:
        args = []
        std = options['std']
        if std.value != 'none':
            args.append('-std=' + std.value)
        return args

    def get_option_link_args(self, options: 'OptionDictType') -> T.List[str]:
        return []


class GnuCCompiler(GnuCompiler, CCompiler):

    _C18_VERSION = '>=8.0.0'
    _C2X_VERSION = '>=9.0.0'

    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice, is_cross: bool,
                 info: 'MachineInfo', exe_wrapper: T.Optional['ExternalProgram'] = None,
                 linker: T.Optional['DynamicLinker'] = None,
                 defines: T.Optional[T.Dict[str, str]] = None,
                 full_version: T.Optional[str] = None):
        CCompiler.__init__(self, exelist, version, for_machine, is_cross, info, exe_wrapper, linker=linker, full_version=full_version)
        GnuCompiler.__init__(self, defines)
        default_warn_args = ['-Wall', '-Winvalid-pch']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}

    def get_options(self) -> 'OptionDictType':
        opts = CCompiler.get_options(self)
        c_stds = ['c89', 'c99', 'c11']
        g_stds = ['gnu89', 'gnu99', 'gnu11']
        if version_compare(self.version, self._C18_VERSION):
            c_stds += ['c17', 'c18']
            g_stds += ['gnu17', 'gnu18']
        if version_compare(self.version, self._C2X_VERSION):
            c_stds += ['c2x']
            g_stds += ['gnu2x']
        opts.update({
            'std': coredata.UserComboOption(
                'C language standard to use',
                ['none'] + c_stds + g_stds,
                'none',
            ),
        })
        if self.info.is_windows() or self.info.is_cygwin():
            opts.update({
                'winlibs': coredata.UserArrayOption(
                    'Standard Win libraries to link against',
                    gnu_winlibs,
                ),
            })
        return opts

    def get_option_compile_args(self, options: 'OptionDictType') -> T.List[str]:
        args = []
        std = options['std']
        if std.value != 'none':
            args.append('-std=' + std.value)
        return args

    def get_option_link_args(self, options: 'OptionDictType') -> T.List[str]:
        if self.info.is_windows() or self.info.is_cygwin():
            # without a typeddict mypy can't figure this out
            libs = options['winlibs'].value.copy()
            assert isinstance(libs, list)
            for l in libs:
                assert isinstance(l, str)
            return libs
        return []

    def get_pch_use_args(self, pch_dir: str, header: str) -> T.List[str]:
        return ['-fpch-preprocess', '-include', os.path.basename(header)]


class PGICCompiler(PGICompiler, CCompiler):
    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice, is_cross: bool,
                 info: 'MachineInfo', exe_wrapper: T.Optional['ExternalProgram'] = None,
                 linker: T.Optional['DynamicLinker'] = None,
                 full_version: T.Optional[str] = None):
        CCompiler.__init__(self, exelist, version, for_machine, is_cross,
                           info, exe_wrapper, linker=linker, full_version=full_version)
        PGICompiler.__init__(self)


class NvidiaHPC_CCompiler(PGICompiler, CCompiler):
    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice, is_cross: bool,
                 info: 'MachineInfo', exe_wrapper: T.Optional['ExternalProgram'] = None,
                 linker: T.Optional['DynamicLinker'] = None,
                 full_version: T.Optional[str] = None):
        CCompiler.__init__(self, exelist, version, for_machine, is_cross,
                           info, exe_wrapper, linker=linker, full_version=full_version)
        PGICompiler.__init__(self)
        self.id = 'nvidia_hpc'


class ElbrusCCompiler(GnuCCompiler, ElbrusCompiler):
    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice, is_cross: bool,
                 info: 'MachineInfo', exe_wrapper: T.Optional['ExternalProgram'] = None,
                 linker: T.Optional['DynamicLinker'] = None,
                 defines: T.Optional[T.Dict[str, str]] = None,
                 full_version: T.Optional[str] = None):
        GnuCCompiler.__init__(self, exelist, version, for_machine, is_cross,
                              info, exe_wrapper, defines=defines,
                              linker=linker, full_version=full_version)
        ElbrusCompiler.__init__(self)

    # It does support some various ISO standards and c/gnu 90, 9x, 1x in addition to those which GNU CC supports.
    def get_options(self) -> 'OptionDictType':
        opts = CCompiler.get_options(self)
        opts.update({
            'std': coredata.UserComboOption(
                'C language standard to use',
                [
                    'none', 'c89', 'c90', 'c9x', 'c99', 'c1x', 'c11',
                    'gnu89', 'gnu90', 'gnu9x', 'gnu99', 'gnu1x', 'gnu11',
                    'iso9899:2011', 'iso9899:1990', 'iso9899:199409', 'iso9899:1999',
                ],
                'none',
            ),
        })
        return opts

    # Elbrus C compiler does not have lchmod, but there is only linker warning, not compiler error.
    # So we should explicitly fail at this case.
    def has_function(self, funcname: str, prefix: str, env: 'Environment', *,
                     extra_args: T.Optional[T.List[str]] = None,
                     dependencies: T.Optional[T.List['Dependency']] = None) -> T.Tuple[bool, bool]:
        if funcname == 'lchmod':
            return False, False
        else:
            return super().has_function(funcname, prefix, env,
                                        extra_args=extra_args,
                                        dependencies=dependencies)


class IntelCCompiler(IntelGnuLikeCompiler, CCompiler):
    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice, is_cross: bool,
                 info: 'MachineInfo', exe_wrapper: T.Optional['ExternalProgram'] = None,
                 linker: T.Optional['DynamicLinker'] = None,
                 full_version: T.Optional[str] = None):
        CCompiler.__init__(self, exelist, version, for_machine, is_cross,
                           info, exe_wrapper, linker=linker, full_version=full_version)
        IntelGnuLikeCompiler.__init__(self)
        self.lang_header = 'c-header'
        default_warn_args = ['-Wall', '-w3', '-diag-disable:remark']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra']}

    def get_options(self) -> 'OptionDictType':
        opts = CCompiler.get_options(self)
        c_stds = ['c89', 'c99']
        g_stds = ['gnu89', 'gnu99']
        if version_compare(self.version, '>=16.0.0'):
            c_stds += ['c11']
        opts.update({
            'std': coredata.UserComboOption(
                'C language standard to use',
                ['none'] + c_stds + g_stds,
                'none',
            ),
        })
        return opts

    def get_option_compile_args(self, options: 'OptionDictType') -> T.List[str]:
        args = []
        std = options['std']
        if std.value != 'none':
            args.append('-std=' + std.value)
        return args


class VisualStudioLikeCCompilerMixin(CompilerMixinBase):

    """Shared methods that apply to MSVC-like C compilers."""

    def get_options(self) -> 'OptionDictType':
        opts = super().get_options()
        opts.update({
            'winlibs': coredata.UserArrayOption(
                'Windows libs to link against.',
                msvc_winlibs,
            ),
        })
        return opts

    def get_option_link_args(self, options: 'OptionDictType') -> T.List[str]:
        # need a TypeDict to make this work
        libs = options['winlibs'].value.copy()
        assert isinstance(libs, list)
        for l in libs:
            assert isinstance(l, str)
        return libs


class VisualStudioCCompiler(MSVCCompiler, VisualStudioLikeCCompilerMixin, CCompiler):

    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice,
                 is_cross: bool, info: 'MachineInfo', target: str,
                 exe_wrapper: T.Optional['ExternalProgram'] = None,
                 linker: T.Optional['DynamicLinker'] = None,
                 full_version: T.Optional[str] = None):
        CCompiler.__init__(self, exelist, version, for_machine, is_cross,
                           info, exe_wrapper, linker=linker,
                           full_version=full_version)
        MSVCCompiler.__init__(self, target)

    def get_options(self) -> 'OptionDictType':
        opts = super().get_options()
        c_stds = ['none', 'c89', 'c99', 'c11',
                  # Need to have these to be compatible with projects
                  # that set c_std to e.g. gnu99.
                  # https://github.com/mesonbuild/meson/issues/7611
                  'gnu89', 'gnu90', 'gnu9x', 'gnu99', 'gnu1x', 'gnu11']
        opts.update({
            'std': coredata.UserComboOption(
                'C language standard to use',
                c_stds,
                'none',
            ),
        })
        return opts

    def get_option_compile_args(self, options: 'OptionDictType') -> T.List[str]:
        args = []
        std = options['std']
        # As of MVSC 16.7, /std:c11 is the only valid C standard option.
        if std.value in {'c11', 'gnu11'}:
            args.append('/std:c11')
        return args


class ClangClCCompiler(ClangClCompiler, VisualStudioLikeCCompilerMixin, CCompiler):
    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice,
                 is_cross: bool, info: 'MachineInfo', target: str,
                 exe_wrapper: T.Optional['ExternalProgram'] = None,
                 linker: T.Optional['DynamicLinker'] = None,
                 full_version: T.Optional[str] = None):
        CCompiler.__init__(self, exelist, version, for_machine, is_cross,
                           info, exe_wrapper, linker=linker,
                           full_version=full_version)
        ClangClCompiler.__init__(self, target)

    def get_options(self) -> 'OptionDictType':
        # Clang-cl can compile up to c99, but doesn't have a std-swtich for
        # them. Unlike recent versions of MSVC it doesn't (as of 10.0.1)
        # support c11
        opts = super().get_options()
        c_stds = ['none', 'c89', 'c99',
                  # Need to have these to be compatible with projects
                  # that set c_std to e.g. gnu99.
                  # https://github.com/mesonbuild/meson/issues/7611
                  'gnu89', 'gnu90', 'gnu9x', 'gnu99']
        opts.update({
            'std': coredata.UserComboOption(
                'C language standard to use',
                c_stds,
                'none',
            ),
        })
        return opts


class IntelClCCompiler(IntelVisualStudioLikeCompiler, VisualStudioLikeCCompilerMixin, CCompiler):

    """Intel "ICL" compiler abstraction."""

    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice,
                 is_cross: bool, info: 'MachineInfo', target: str,
                 exe_wrapper: T.Optional['ExternalProgram'] = None,
                 linker: T.Optional['DynamicLinker'] = None,
                 full_version: T.Optional[str] = None):
        CCompiler.__init__(self, exelist, version, for_machine, is_cross,
                           info, exe_wrapper, linker=linker,
                           full_version=full_version)
        IntelVisualStudioLikeCompiler.__init__(self, target)

    def get_options(self) -> 'OptionDictType':
        opts = super().get_options()
        c_stds = ['none', 'c89', 'c99', 'c11']
        opts.update({
            'std': coredata.UserComboOption(
                'C language standard to use',
                c_stds,
                'none',
            ),
        })
        return opts

    def get_option_compile_args(self, options: 'OptionDictType') -> T.List[str]:
        args = []
        std = options['std']
        if std.value == 'c89':
            mlog.warning("ICL doesn't explicitly implement c89, setting the standard to 'none', which is close.", once=True)
        elif std.value != 'none':
            args.append('/Qstd:' + std.value)
        return args


class ArmCCompiler(ArmCompiler, CCompiler):
    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice,
                 is_cross: bool, info: 'MachineInfo',
                 exe_wrapper: T.Optional['ExternalProgram'] = None,
                 linker: T.Optional['DynamicLinker'] = None,
                 full_version: T.Optional[str] = None):
        CCompiler.__init__(self, exelist, version, for_machine, is_cross,
                           info, exe_wrapper, linker=linker,
                           full_version=full_version)
        ArmCompiler.__init__(self)

    def get_options(self) -> 'OptionDictType':
        opts = CCompiler.get_options(self)
        opts.update({
            'std': coredata.UserComboOption(
                'C language standard to use',
                ['none', 'c90', 'c99'],
                'none',
            ),
        })
        return opts

    def get_option_compile_args(self, options: 'OptionDictType') -> T.List[str]:
        args = []
        std = options['std']
        if std.value != 'none':
            args.append('--' + std.value)
        return args


class CcrxCCompiler(CcrxCompiler, CCompiler):
    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice,
                 is_cross: bool, info: 'MachineInfo',
                 exe_wrapper: T.Optional['ExternalProgram'] = None,
                 linker: T.Optional['DynamicLinker'] = None,
                 full_version: T.Optional[str] = None):
        CCompiler.__init__(self, exelist, version, for_machine, is_cross,
                           info, exe_wrapper, linker=linker, full_version=full_version)
        CcrxCompiler.__init__(self)

    # Override CCompiler.get_always_args
    def get_always_args(self) -> T.List[str]:
        return ['-nologo']

    def get_options(self) -> 'OptionDictType':
        opts = CCompiler.get_options(self)
        opts.update({
            'std': coredata.UserComboOption(
                'C language standard to use',
                ['none', 'c89', 'c99'],
                'none',
            ),
        })
        return opts

    def get_no_stdinc_args(self) -> T.List[str]:
        return []

    def get_option_compile_args(self, options: 'OptionDictType') -> T.List[str]:
        args = []
        std = options['std']
        if std.value == 'c89':
            args.append('-lang=c')
        elif std.value == 'c99':
            args.append('-lang=c99')
        return args

    def get_compile_only_args(self) -> T.List[str]:
        return []

    def get_no_optimization_args(self) -> T.List[str]:
        return ['-optimize=0']

    def get_output_args(self, target: str) -> T.List[str]:
        return ['-output=obj=%s' % target]

    def get_werror_args(self) -> T.List[str]:
        return ['-change_message=error']

    def get_include_args(self, path: str, is_system: bool) -> T.List[str]:
        if path == '':
            path = '.'
        return ['-include=' + path]


class Xc16CCompiler(Xc16Compiler, CCompiler):
    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice,
                 is_cross: bool, info: 'MachineInfo',
                 exe_wrapper: T.Optional['ExternalProgram'] = None,
                 linker: T.Optional['DynamicLinker'] = None,
                 full_version: T.Optional[str] = None):
        CCompiler.__init__(self, exelist, version, for_machine, is_cross,
                           info, exe_wrapper, linker=linker, full_version=full_version)
        Xc16Compiler.__init__(self)

    def get_options(self) -> 'OptionDictType':
        opts = CCompiler.get_options(self)
        opts.update({'c_std': coredata.UserComboOption('C language standard to use',
                                                       ['none', 'c89', 'c99', 'gnu89', 'gnu99'],
                                                       'none')})
        return opts

    def get_no_stdinc_args(self) -> T.List[str]:
        return []

    def get_option_compile_args(self, options: 'OptionDictType') -> T.List[str]:
        args = []
        std = options['c_std']
        if std.value != 'none':
            args.append('-ansi')
            args.append('-std=' + std.value)
        return args

    def get_compile_only_args(self) -> T.List[str]:
        return []

    def get_no_optimization_args(self) -> T.List[str]:
        return ['-O0']

    def get_output_args(self, target: str) -> T.List[str]:
        return ['-o%s' % target]

    def get_werror_args(self) -> T.List[str]:
        return ['-change_message=error']

    def get_include_args(self, path: str, is_system: bool) -> T.List[str]:
        if path == '':
            path = '.'
        return ['-I' + path]

class CompCertCCompiler(CompCertCompiler, CCompiler):
    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice,
                 is_cross: bool, info: 'MachineInfo',
                 exe_wrapper: T.Optional['ExternalProgram'] = None,
                 linker: T.Optional['DynamicLinker'] = None,
                 full_version: T.Optional[str] = None):
        CCompiler.__init__(self, exelist, version, for_machine, is_cross,
                           info, exe_wrapper, linker=linker, full_version=full_version)
        CompCertCompiler.__init__(self)

    def get_options(self) -> 'OptionDictType':
        opts = CCompiler.get_options(self)
        opts.update({'c_std': coredata.UserComboOption('C language standard to use',
                                                       ['none', 'c89', 'c99'],
                                                       'none')})
        return opts

    def get_option_compile_args(self, options: 'OptionDictType') -> T.List[str]:
        return []

    def get_no_optimization_args(self) -> T.List[str]:
        return ['-O0']

    def get_output_args(self, target: str) -> T.List[str]:
        return ['-o{}'.format(target)]

    def get_werror_args(self) -> T.List[str]:
        return ['-Werror']

    def get_include_args(self, path: str, is_system: bool) -> T.List[str]:
        if path == '':
            path = '.'
        return ['-I' + path]

class C2000CCompiler(C2000Compiler, CCompiler):
    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice,
                 is_cross: bool, info: 'MachineInfo',
                 exe_wrapper: T.Optional['ExternalProgram'] = None,
                 linker: T.Optional['DynamicLinker'] = None,
                 full_version: T.Optional[str] = None):
        CCompiler.__init__(self, exelist, version, for_machine, is_cross,
                           info, exe_wrapper, linker=linker, full_version=full_version)
        C2000Compiler.__init__(self)

    # Override CCompiler.get_always_args
    def get_always_args(self) -> T.List[str]:
        return []

    def get_options(self) -> 'OptionDictType':
        opts = CCompiler.get_options(self)
        opts.update({'c_std': coredata.UserComboOption('C language standard to use',
                                                       ['none', 'c89', 'c99', 'c11'],
                                                       'none')})
        return opts

    def get_no_stdinc_args(self) -> T.List[str]:
        return []

    def get_option_compile_args(self, options: 'OptionDictType') -> T.List[str]:
        args = []
        std = options['c_std']
        if std.value != 'none':
            args.append('--' + std.value)
        return args

    def get_compile_only_args(self) -> T.List[str]:
        return []

    def get_no_optimization_args(self) -> T.List[str]:
        return ['-Ooff']

    def get_output_args(self, target: str) -> T.List[str]:
        return ['--output_file=%s' % target]

    def get_werror_args(self) -> T.List[str]:
        return ['-change_message=error']

    def get_include_args(self, path: str, is_system: bool) -> T.List[str]:
        if path == '':
            path = '.'
        return ['--include_path=' + path]
