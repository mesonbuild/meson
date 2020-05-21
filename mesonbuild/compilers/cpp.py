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

import copy
import functools
import os.path
import typing as T

from .. import coredata
from .. import mlog
from ..mesonlib import MesonException, MachineChoice, version_compare

from ..linkers import LinkerEnvVarsMixin
from .compilers import (
    gnu_winlibs,
    msvc_winlibs,
    Compiler,
)
from .c_function_attributes import CXX_FUNC_ATTRIBUTES, C_FUNC_ATTRIBUTES
from .mixins.clike import CLikeCompiler
from .mixins.ccrx import CcrxCompiler
from .mixins.c2000 import C2000Compiler
from .mixins.arm import ArmCompiler, ArmclangCompiler
from .mixins.visualstudio import MSVCCompiler, ClangClCompiler
from .mixins.gnu import GnuCompiler
from .mixins.intel import IntelGnuLikeCompiler, IntelVisualStudioLikeCompiler
from .mixins.clang import ClangCompiler
from .mixins.elbrus import ElbrusCompiler
from .mixins.pgi import PGICompiler
from .mixins.emscripten import EmscriptenMixin

if T.TYPE_CHECKING:
    from ..envconfig import MachineInfo


def non_msvc_eh_options(eh, args):
    if eh == 'none':
        args.append('-fno-exceptions')
    elif eh == 's' or eh == 'c':
        mlog.warning('non-MSVC compilers do not support ' + eh + ' exception handling.' +
                     'You may want to set eh to \'default\'.')

class CPPCompiler(CLikeCompiler, Compiler):

    @classmethod
    def attribute_check_func(cls, name):
        try:
            return CXX_FUNC_ATTRIBUTES.get(name, C_FUNC_ATTRIBUTES[name])
        except KeyError:
            raise MesonException('Unknown function attribute "{}"'.format(name))

    language = 'cpp'

    def __init__(self, exelist, version, for_machine: MachineChoice, is_cross: bool,
                 info: 'MachineInfo', exe_wrap: T.Optional[str] = None, **kwargs):
        # If a child ObjCPP class has already set it, don't set it ourselves
        Compiler.__init__(self, exelist, version, for_machine, info, **kwargs)
        CLikeCompiler.__init__(self, is_cross, exe_wrap)

    @staticmethod
    def get_display_language():
        return 'C++'

    def get_no_stdinc_args(self):
        return ['-nostdinc++']

    def sanity_check(self, work_dir, environment):
        code = 'class breakCCompiler;int main(void) { return 0; }\n'
        return self.sanity_check_impl(work_dir, environment, 'sanitycheckcpp.cc', code)

    def get_compiler_check_args(self):
        # -fpermissive allows non-conforming code to compile which is necessary
        # for many C++ checks. Particularly, the has_header_symbol check is
        # too strict without this and always fails.
        return super().get_compiler_check_args() + ['-fpermissive']

    def has_header_symbol(self, hname, symbol, prefix, env, *, extra_args=None, dependencies=None):
        # Check if it's a C-like symbol
        found, cached = super().has_header_symbol(hname, symbol, prefix, env,
                                                  extra_args=extra_args,
                                                  dependencies=dependencies)
        if found:
            return True, cached
        # Check if it's a class or a template
        if extra_args is None:
            extra_args = []
        fargs = {'prefix': prefix, 'header': hname, 'symbol': symbol}
        t = '''{prefix}
        #include <{header}>
        using {symbol};
        int main(void) {{ return 0; }}'''
        return self.compiles(t.format(**fargs), env, extra_args=extra_args,
                             dependencies=dependencies)

    def _test_cpp_std_arg(self, cpp_std_value):
        # Test whether the compiler understands a -std=XY argument
        assert(cpp_std_value.startswith('-std='))

        # This test does not use has_multi_arguments() for two reasons:
        # 1. has_multi_arguments() requires an env argument, which the compiler
        #    object does not have at this point.
        # 2. even if it did have an env object, that might contain another more
        #    recent -std= argument, which might lead to a cascaded failure.
        CPP_TEST = 'int i = static_cast<int>(0);'
        with self.compile(CPP_TEST, extra_args=[cpp_std_value], mode='compile') as p:
            if p.returncode == 0:
                mlog.debug('Compiler accepts {}:'.format(cpp_std_value), 'YES')
                return True
            else:
                mlog.debug('Compiler accepts {}:'.format(cpp_std_value), 'NO')
                return False

    @functools.lru_cache()
    def _find_best_cpp_std(self, cpp_std):
        # The initial version mapping approach to make falling back
        # from '-std=c++14' to '-std=c++1y' was too brittle. For instance,
        # Apple's Clang uses a different versioning scheme to upstream LLVM,
        # making the whole detection logic awfully brittle. Instead, let's
        # just see if feeding GCC or Clang our '-std=' setting works, and
        # if not, try the fallback argument.
        CPP_FALLBACKS = {
            'c++11': 'c++0x',
            'gnu++11': 'gnu++0x',
            'c++14': 'c++1y',
            'gnu++14': 'gnu++1y',
            'c++17': 'c++1z',
            'gnu++17': 'gnu++1z'
        }

        # Currently, remapping is only supported for Clang, Elbrus and GCC
        assert(self.id in frozenset(['clang', 'lcc', 'gcc', 'emscripten']))

        if cpp_std not in CPP_FALLBACKS:
            # 'c++03' and 'c++98' don't have fallback types
            return '-std=' + cpp_std

        for i in (cpp_std, CPP_FALLBACKS[cpp_std]):
            cpp_std_value = '-std=' + i
            if self._test_cpp_std_arg(cpp_std_value):
                return cpp_std_value

        raise MesonException('C++ Compiler does not support -std={}'.format(cpp_std))


class ClangCPPCompiler(ClangCompiler, CPPCompiler):
    def __init__(self, exelist, version, for_machine: MachineChoice,
                 is_cross, info: 'MachineInfo', exe_wrapper=None,
                 defines : T.Optional[T.List[str]] = None, **kwargs):
        CPPCompiler.__init__(self, exelist, version, for_machine, is_cross,
                             info, exe_wrapper, **kwargs)
        ClangCompiler.__init__(self, defines)
        default_warn_args = ['-Wall', '-Winvalid-pch', '-Wnon-virtual-dtor']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}

    def get_options(self):
        opts = CPPCompiler.get_options(self)
        opts.update({
            'eh': coredata.UserComboOption(
                'C++ exception handling type.',
                ['none', 'default', 'a', 's', 'sc'],
                'default',
            ),
            'rtti': coredata.UserBooleanOption('Enable RTTI', True),
            'std': coredata.UserComboOption(
                'C++ language standard to use',
                ['none', 'c++98', 'c++03', 'c++11', 'c++14', 'c++17', 'c++1z', 'c++2a',
                 'gnu++11', 'gnu++14', 'gnu++17', 'gnu++1z', 'gnu++2a'],
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

    def get_option_compile_args(self, options):
        args = []
        std = options['std']
        if std.value != 'none':
            args.append(self._find_best_cpp_std(std.value))

        non_msvc_eh_options(options['eh'].value, args)

        if not options['rtti'].value:
            args.append('-fno-rtti')

        return args

    def get_option_link_args(self, options):
        if self.info.is_windows() or self.info.is_cygwin():
            return options['winlibs'].value[:]
        return []

    def language_stdlib_only_link_flags(self):
        return ['-lstdc++']


class AppleClangCPPCompiler(ClangCPPCompiler):
    def language_stdlib_only_link_flags(self):
        return ['-lc++']


class EmscriptenCPPCompiler(EmscriptenMixin, LinkerEnvVarsMixin, ClangCPPCompiler):
    def __init__(self, exelist, version, for_machine: MachineChoice,
                 is_cross: bool, info: 'MachineInfo', exe_wrapper=None, **kwargs):
        if not is_cross:
            raise MesonException('Emscripten compiler can only be used for cross compilation.')
        ClangCPPCompiler.__init__(self, exelist=exelist, version=version,
                                  for_machine=for_machine, is_cross=is_cross,
                                  info=info, exe_wrapper=exe_wrapper, **kwargs)
        self.id = 'emscripten'

    def get_option_compile_args(self, options):
        args = []
        std = options['std']
        if std.value != 'none':
            args.append(self._find_best_cpp_std(std.value))
        return args


class ArmclangCPPCompiler(ArmclangCompiler, CPPCompiler):
    def __init__(self, exelist, version, for_machine: MachineChoice,
                 is_cross, info: 'MachineInfo', exe_wrapper=None, **kwargs):
        CPPCompiler.__init__(self, exelist=exelist, version=version,
                                  for_machine=for_machine, is_cross=is_cross,
                                  info=info, exe_wrapper=exe_wrapper, **kwargs)
        ArmclangCompiler.__init__(self)
        default_warn_args = ['-Wall', '-Winvalid-pch', '-Wnon-virtual-dtor']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}

    def get_options(self):
        opts = CPPCompiler.get_options(self)
        opts.update({
            'eh': coredata.UserComboOption(
                'C++ exception handling type.',
                ['none', 'default', 'a', 's', 'sc'],
                'default',
            ),
            'std': coredata.UserComboOption(
                'C++ language standard to use',
                [
                    'none', 'c++98', 'c++03', 'c++11', 'c++14', 'c++17',
                    'gnu++98', 'gnu++03', 'gnu++11', 'gnu++14', 'gnu++17',
                ],
                'none',
            ),
        })
        return opts

    def get_option_compile_args(self, options):
        args = []
        std = options['std']
        if std.value != 'none':
            args.append('-std=' + std.value)

        non_msvc_eh_options(options['eh'].value, args)

        return args

    def get_option_link_args(self, options):
        return []


class GnuCPPCompiler(GnuCompiler, CPPCompiler):
    def __init__(self, exelist, version, for_machine: MachineChoice,
                 is_cross, info: 'MachineInfo', exe_wrap, defines, **kwargs):
        CPPCompiler.__init__(self, exelist, version, for_machine, is_cross, info, exe_wrap, **kwargs)
        GnuCompiler.__init__(self, defines)
        default_warn_args = ['-Wall', '-Winvalid-pch', '-Wnon-virtual-dtor']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}

    def get_options(self):
        opts = CPPCompiler.get_options(self)
        opts.update({
            'eh': coredata.UserComboOption(
                'C++ exception handling type.',
                ['none', 'default', 'a', 's', 'sc'],
                'default',
            ),
            'rtti': coredata.UserBooleanOption('Enable RTTI', True),
            'std': coredata.UserComboOption(
                'C++ language standard to use',
                ['none', 'c++98', 'c++03', 'c++11', 'c++14', 'c++17', 'c++1z', 'c++2a',
                'gnu++03', 'gnu++11', 'gnu++14', 'gnu++17', 'gnu++1z', 'gnu++2a'],
                'none',
            ),
            'debugstl': coredata.UserBooleanOption(
                'STL debug mode',
                False,
            )
        })
        if self.info.is_windows() or self.info.is_cygwin():
            opts.update({
                'winlibs': coredata.UserArrayOption(
                    'Standard Win libraries to link against',
                    gnu_winlibs,
                ),
            })
        return opts

    def get_option_compile_args(self, options):
        args = []
        std = options['std']
        if std.value != 'none':
            args.append(self._find_best_cpp_std(std.value))

        non_msvc_eh_options(options['eh'].value, args)

        if not options['rtti'].value:
            args.append('-fno-rtti')

        if options['debugstl'].value:
            args.append('-D_GLIBCXX_DEBUG=1')
        return args

    def get_option_link_args(self, options):
        if self.info.is_windows() or self.info.is_cygwin():
            return options['winlibs'].value[:]
        return []

    def get_pch_use_args(self, pch_dir, header):
        return ['-fpch-preprocess', '-include', os.path.basename(header)]

    def language_stdlib_only_link_flags(self):
        return ['-lstdc++']


class PGICPPCompiler(PGICompiler, CPPCompiler):
    def __init__(self, exelist, version, for_machine: MachineChoice,
                 is_cross, info: 'MachineInfo', exe_wrapper=None, **kwargs):
        CPPCompiler.__init__(self, exelist, version, for_machine, is_cross, info, exe_wrapper, **kwargs)
        PGICompiler.__init__(self)


class ElbrusCPPCompiler(GnuCPPCompiler, ElbrusCompiler):
    def __init__(self, exelist, version, for_machine: MachineChoice,
                 is_cross, info: 'MachineInfo', exe_wrapper=None,
                 defines=None, **kwargs):
        GnuCPPCompiler.__init__(self, exelist, version, for_machine,
                                is_cross, info, exe_wrapper, defines,
                                **kwargs)
        ElbrusCompiler.__init__(self)

    # It does not support c++/gnu++ 17 and 1z, but still does support 0x, 1y, and gnu++98.
    def get_options(self):
        opts = CPPCompiler.get_options(self)
        opts.update({
            'eh': coredata.UserComboOption(
                'C++ exception handling type.',
                ['none', 'default', 'a', 's', 'sc'],
                'default',
            ),
            'std': coredata.UserComboOption(
                'C++ language standard to use',
                [
                    'none', 'c++98', 'c++03', 'c++0x', 'c++11', 'c++14', 'c++1y',
                    'gnu++98', 'gnu++03', 'gnu++0x', 'gnu++11', 'gnu++14', 'gnu++1y',
                ],
                'none',
            ),
            'debugstl': coredata.UserBooleanOption(
                'STL debug mode',
                False,
            ),
        })
        return opts

    # Elbrus C++ compiler does not have lchmod, but there is only linker warning, not compiler error.
    # So we should explicitly fail at this case.
    def has_function(self, funcname, prefix, env, *, extra_args=None, dependencies=None):
        if funcname == 'lchmod':
            return False, False
        else:
            return super().has_function(funcname, prefix, env,
                                        extra_args=extra_args,
                                        dependencies=dependencies)

    # Elbrus C++ compiler does not support RTTI, so don't check for it.
    def get_option_compile_args(self, options):
        args = []
        std = options['std']
        if std.value != 'none':
            args.append(self._find_best_cpp_std(std.value))

        non_msvc_eh_options(options['eh'].value, args)

        if options['debugstl'].value:
            args.append('-D_GLIBCXX_DEBUG=1')
        return args


class IntelCPPCompiler(IntelGnuLikeCompiler, CPPCompiler):
    def __init__(self, exelist, version, for_machine: MachineChoice,
                 is_cross, info: 'MachineInfo', exe_wrap, **kwargs):
        CPPCompiler.__init__(self, exelist, version, for_machine, is_cross,
                             info, exe_wrap, **kwargs)
        IntelGnuLikeCompiler.__init__(self)
        self.lang_header = 'c++-header'
        default_warn_args = ['-Wall', '-w3', '-diag-disable:remark',
                             '-Wpch-messages', '-Wnon-virtual-dtor']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra']}

    def get_options(self):
        opts = CPPCompiler.get_options(self)
        # Every Unix compiler under the sun seems to accept -std=c++03,
        # with the exception of ICC. Instead of preventing the user from
        # globally requesting C++03, we transparently remap it to C++98
        c_stds = ['c++98', 'c++03']
        g_stds = ['gnu++98', 'gnu++03']
        if version_compare(self.version, '>=15.0.0'):
            c_stds += ['c++11', 'c++14']
            g_stds += ['gnu++11']
        if version_compare(self.version, '>=16.0.0'):
            c_stds += ['c++17']
        if version_compare(self.version, '>=17.0.0'):
            g_stds += ['gnu++14']
        opts.update({
            'eh': coredata.UserComboOption(
                'C++ exception handling type.',
                ['none', 'default', 'a', 's', 'sc'],
                'default',
            ),
            'rtti': coredata.UserBooleanOption('Enable RTTI', True),
            'std': coredata.UserComboOption(
                'C++ language standard to use',
                ['none'] + c_stds + g_stds,
                'none',
            ),
            'debugstl': coredata.UserBooleanOption('STL debug mode', False),
        })
        return opts

    def get_option_compile_args(self, options):
        args = []
        std = options['std']
        if std.value != 'none':
            remap_cpp03 = {
                'c++03': 'c++98',
                'gnu++03': 'gnu++98'
            }
            args.append('-std=' + remap_cpp03.get(std.value, std.value))
        if options['eh'].value == 'none':
            args.append('-fno-exceptions')
        if not options['rtti'].value:
            args.append('-fno-rtti')
        if options['debugstl'].value:
            args.append('-D_GLIBCXX_DEBUG=1')
        return args

    def get_option_link_args(self, options):
        return []


class VisualStudioLikeCPPCompilerMixin:

    """Mixin for C++ specific method overrides in MSVC-like compilers."""

    VC_VERSION_MAP = {
        'none': (True, None),
        'vc++11': (True, 11),
        'vc++14': (True, 14),
        'vc++17': (True, 17),
        'vc++latest': (True, "latest"),
        'c++11': (False, 11),
        'c++14': (False, 14),
        'c++17': (False, 17),
        'c++latest': (False, "latest"),
    }

    def get_option_link_args(self, options):
        return options['winlibs'].value[:]

    def _get_options_impl(self, opts, cpp_stds: T.List[str]):
        opts.update({
            'eh': coredata.UserComboOption(
                'C++ exception handling type.',
                ['none', 'default', 'a', 's', 'sc'],
                'default',
            ),
            'rtti': coredata.UserBooleanOption('Enable RTTI', True),
            'std': coredata.UserComboOption(
                'C++ language standard to use',
                cpp_stds,
                'none',
            ),
            'winlibs': coredata.UserArrayOption(
                'Windows libs to link against.',
                msvc_winlibs,
            ),
        })
        return opts

    def get_option_compile_args(self, options):
        args = []

        eh = options['eh']
        if eh.value == 'default':
            args.append('/EHsc')
        elif eh.value == 'none':
            args.append('/EHs-c-')
        else:
            args.append('/EH' + eh.value)

        if not options['rtti'].value:
            args.append('/GR-')

        permissive, ver = self.VC_VERSION_MAP[options['std'].value]

        if ver is not None:
            args.append('/std:c++{}'.format(ver))

        if not permissive:
            args.append('/permissive-')

        return args

    def get_compiler_check_args(self):
        # XXX: this is a hack because so much GnuLike stuff is in the base CPPCompiler class.
        return CLikeCompiler.get_compiler_check_args(self)


class CPP11AsCPP14Mixin:

    """Mixin class for VisualStudio and ClangCl to replace C++11 std with C++14.

    This is a limitation of Clang and MSVC that ICL doesn't share.
    """

    def get_option_compile_args(self, options):
        # Note: there is no explicit flag for supporting C++11; we attempt to do the best we can
        # which means setting the C++ standard version to C++14, in compilers that support it
        # (i.e., after VS2015U3)
        # if one is using anything before that point, one cannot set the standard.
        if options['std'].value in {'vc++11', 'c++11'}:
            mlog.warning(self.id, 'does not support C++11;',
                         'attempting best effort; setting the standard to C++14', once=True)
            # Don't mutate anything we're going to change, we need to use
            # deepcopy since we're messing with members, and we can't simply
            # copy the members because the option proxy doesn't support it.
            options = copy.deepcopy(options)
            if options['std'].value == 'vc++11':
                options['std'].value = 'vc++14'
            else:
                options['std'].value = 'c++14'
        return super().get_option_compile_args(options)


class VisualStudioCPPCompiler(CPP11AsCPP14Mixin, VisualStudioLikeCPPCompilerMixin, MSVCCompiler, CPPCompiler):
    def __init__(self, exelist, version, for_machine: MachineChoice,
                 is_cross: bool, info: 'MachineInfo', exe_wrap, target, **kwargs):
        CPPCompiler.__init__(self, exelist, version, for_machine, is_cross, info, exe_wrap, **kwargs)
        MSVCCompiler.__init__(self, target)
        self.base_options = ['b_pch', 'b_vscrt'] # FIXME add lto, pgo and the like
        self.id = 'msvc'

    def get_options(self):
        cpp_stds = ['none', 'c++11', 'vc++11']
        # Visual Studio 2015 and later
        if version_compare(self.version, '>=19'):
            cpp_stds.extend(['c++14', 'c++latest', 'vc++latest'])
        # Visual Studio 2017 and later
        if version_compare(self.version, '>=19.11'):
            cpp_stds.extend(['vc++14', 'c++17', 'vc++17'])
        return self._get_options_impl(super().get_options(), cpp_stds)

    def get_option_compile_args(self, options):
        if options['std'].value != 'none' and version_compare(self.version, '<19.00.24210'):
            mlog.warning('This version of MSVC does not support cpp_std arguments')
            options = copy.copy(options)
            options['std'].value = 'none'

        args = super().get_option_compile_args(options)

        if version_compare(self.version, '<19.11'):
            try:
                i = args.index('/permissive-')
            except ValueError:
                return args
            del args[i]
        return args

class ClangClCPPCompiler(CPP11AsCPP14Mixin, VisualStudioLikeCPPCompilerMixin, ClangClCompiler, CPPCompiler):
    def __init__(self, exelist, version, for_machine: MachineChoice,
                 is_cross, info: 'MachineInfo', exe_wrap, target, **kwargs):
        CPPCompiler.__init__(self, exelist, version, for_machine, is_cross,
                             info, exe_wrap, **kwargs)
        ClangClCompiler.__init__(self, target)
        self.id = 'clang-cl'

    def get_options(self):
        cpp_stds = ['none', 'c++11', 'vc++11', 'c++14', 'vc++14', 'c++17', 'vc++17', 'c++latest']
        return self._get_options_impl(super().get_options(), cpp_stds)


class IntelClCPPCompiler(VisualStudioLikeCPPCompilerMixin, IntelVisualStudioLikeCompiler, CPPCompiler):

    def __init__(self, exelist, version, for_machine: MachineChoice,
                 is_cross, info: 'MachineInfo', exe_wrap, target, **kwargs):
        CPPCompiler.__init__(self, exelist, version, for_machine, is_cross,
                             info, exe_wrap, **kwargs)
        IntelVisualStudioLikeCompiler.__init__(self, target)

    def get_options(self):
        # This has only been tested with version 19.0,
        cpp_stds = ['none', 'c++11', 'vc++11', 'c++14', 'vc++14', 'c++17', 'vc++17', 'c++latest']
        return self._get_options_impl(super().get_options(), cpp_stds)


class ArmCPPCompiler(ArmCompiler, CPPCompiler):
    def __init__(self, exelist, version, for_machine: MachineChoice,
                 is_cross, info: 'MachineInfo', exe_wrap=None, **kwargs):
        CPPCompiler.__init__(self, exelist, version, for_machine, is_cross,
                             info, exe_wrap, **kwargs)
        ArmCompiler.__init__(self)

    def get_options(self):
        opts = CPPCompiler.get_options(self)
        opts.update({
            'std': coredata.UserComboOption(
                'C++ language standard to use',
                ['none', 'c++03', 'c++11'],
                'none',
            ),
        })
        return opts

    def get_option_compile_args(self, options):
        args = []
        std = options['std']
        if std.value == 'c++11':
            args.append('--cpp11')
        elif std.value == 'c++03':
            args.append('--cpp')
        return args

    def get_option_link_args(self, options):
        return []

    def get_compiler_check_args(self):
        return []


class CcrxCPPCompiler(CcrxCompiler, CPPCompiler):
    def __init__(self, exelist, version, for_machine: MachineChoice,
                 is_cross, info: 'MachineInfo', exe_wrap=None, **kwargs):
        CPPCompiler.__init__(self, exelist, version, for_machine, is_cross,
                             info, exe_wrap, **kwargs)
        CcrxCompiler.__init__(self)

    # Override CCompiler.get_always_args
    def get_always_args(self):
        return ['-nologo', '-lang=cpp']

    def get_option_compile_args(self, options):
        return []

    def get_compile_only_args(self):
        return []

    def get_output_args(self, target):
        return ['-output=obj=%s' % target]

    def get_option_link_args(self, options):
        return []

    def get_compiler_check_args(self):
        return []

class C2000CPPCompiler(C2000Compiler, CPPCompiler):
    def __init__(self, exelist, version, for_machine: MachineChoice,
                 is_cross, info: 'MachineInfo', exe_wrap=None, **kwargs):
        CPPCompiler.__init__(self, exelist, version, for_machine, is_cross,
                             info, exe_wrap, **kwargs)
        C2000Compiler.__init__(self)

    def get_options(self):
        opts = CPPCompiler.get_options(self)
        opts.update({'cpp_std': coredata.UserComboOption('C++ language standard to use',
                                                         ['none', 'c++03'],
                                                         'none')})
        return opts

    def get_always_args(self):
        return ['-nologo', '-lang=cpp']

    def get_option_compile_args(self, options):
        return []

    def get_compile_only_args(self):
        return []

    def get_output_args(self, target):
        return ['-output=obj=%s' % target]

    def get_option_link_args(self, options):
        return []

    def get_compiler_check_args(self):
        return []
