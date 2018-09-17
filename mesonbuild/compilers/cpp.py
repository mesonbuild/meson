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

import functools
import os.path

from .. import coredata
from .. import mlog
from ..mesonlib import MesonException, version_compare

from .c import CCompiler, VisualStudioCCompiler
from .compilers import (
    CompilerType,
    gnu_winlibs,
    msvc_winlibs,
    ClangCompiler,
    GnuCompiler,
    ElbrusCompiler,
    IntelCompiler,
    ArmCompiler,
    ArmclangCompiler,
)
from .c_function_attributes import CXX_FUNC_ATTRIBUTES

class CPPCompiler(CCompiler):

    @classmethod
    def attribute_check_func(cls, name):
        return CXX_FUNC_ATTRIBUTES.get(name, super().attribute_check_func(name))

    def __init__(self, exelist, version, is_cross, exe_wrap, **kwargs):
        # If a child ObjCPP class has already set it, don't set it ourselves
        if not hasattr(self, 'language'):
            self.language = 'cpp'
        CCompiler.__init__(self, exelist, version, is_cross, exe_wrap, **kwargs)

    def get_display_language(self):
        return 'C++'

    def get_no_stdinc_args(self):
        return ['-nostdinc++']

    def sanity_check(self, work_dir, environment):
        code = 'class breakCCompiler;int main(int argc, char **argv) { return 0; }\n'
        return self.sanity_check_impl(work_dir, environment, 'sanitycheckcpp.cc', code)

    def get_compiler_check_args(self):
        # -fpermissive allows non-conforming code to compile which is necessary
        # for many C++ checks. Particularly, the has_header_symbol check is
        # too strict without this and always fails.
        return super().get_compiler_check_args() + ['-fpermissive']

    def has_header_symbol(self, hname, symbol, prefix, env, extra_args=None, dependencies=None):
        # Check if it's a C-like symbol
        if super().has_header_symbol(hname, symbol, prefix, env, extra_args, dependencies):
            return True
        # Check if it's a class or a template
        if extra_args is None:
            extra_args = []
        fargs = {'prefix': prefix, 'header': hname, 'symbol': symbol}
        t = '''{prefix}
        #include <{header}>
        using {symbol};
        int main () {{ return 0; }}'''
        return self.compiles(t.format(**fargs), env, extra_args, dependencies)

    def _test_cpp_std_arg(self, cpp_std_value):
        # Test whether the compiler understands a -std=XY argument
        assert(cpp_std_value.startswith('-std='))

        # This test does not use has_multi_arguments() for two reasons:
        # 1. has_multi_arguments() requires an env argument, which the compiler
        #    object does not have at this point.
        # 2. even if it did have an env object, that might contain another more
        #    recent -std= argument, which might lead to a cascaded failure.
        CPP_TEST = 'int i = static_cast<int>(0);'
        with self.compile(code=CPP_TEST, extra_args=[cpp_std_value], mode='compile') as p:
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

        # Currently, remapping is only supported for Clang and GCC
        assert(self.id in frozenset(['clang', 'gcc']))

        if cpp_std not in CPP_FALLBACKS:
            # 'c++03' and 'c++98' don't have fallback types
            return '-std=' + cpp_std

        for i in (cpp_std, CPP_FALLBACKS[cpp_std]):
            cpp_std_value = '-std=' + i
            if self._test_cpp_std_arg(cpp_std_value):
                return cpp_std_value

        raise MesonException('C++ Compiler does not support -std={}'.format(cpp_std))


class ClangCPPCompiler(ClangCompiler, CPPCompiler):
    def __init__(self, exelist, version, compiler_type, is_cross, exe_wrapper=None, **kwargs):
        CPPCompiler.__init__(self, exelist, version, is_cross, exe_wrapper, **kwargs)
        ClangCompiler.__init__(self, compiler_type)
        default_warn_args = ['-Wall', '-Winvalid-pch', '-Wnon-virtual-dtor']
        self.warn_args = {'1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}

    def get_options(self):
        opts = CPPCompiler.get_options(self)
        opts.update({'cpp_std': coredata.UserComboOption('cpp_std', 'C++ language standard to use',
                                                         ['none', 'c++98', 'c++03', 'c++11', 'c++14', 'c++17', 'c++1z', 'c++2a',
                                                          'gnu++11', 'gnu++14', 'gnu++17', 'gnu++1z', 'gnu++2a'],
                                                         'none')})
        return opts

    def get_option_compile_args(self, options):
        args = []
        std = options['cpp_std']
        if std.value != 'none':
            args.append(self._find_best_cpp_std(std.value))
        return args

    def get_option_link_args(self, options):
        return []

    def language_stdlib_only_link_flags(self):
        return ['-lstdc++']


class ArmclangCPPCompiler(ArmclangCompiler, CPPCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrapper=None, **kwargs):
        CPPCompiler.__init__(self, exelist, version, is_cross, exe_wrapper, **kwargs)
        ArmclangCompiler.__init__(self)
        default_warn_args = ['-Wall', '-Winvalid-pch', '-Wnon-virtual-dtor']
        self.warn_args = {'1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}

    def get_options(self):
        opts = CPPCompiler.get_options(self)
        opts.update({'cpp_std': coredata.UserComboOption('cpp_std', 'C++ language standard to use',
                                                         ['none', 'c++98', 'c++03', 'c++11', 'c++14', 'c++17',
                                                          'gnu++98', 'gnu++03', 'gnu++11', 'gnu++14', 'gnu++17'],
                                                         'none')})
        return opts

    def get_option_compile_args(self, options):
        args = []
        std = options['cpp_std']
        if std.value != 'none':
            args.append('-std=' + std.value)
        return args

    def get_option_link_args(self, options):
        return []


class GnuCPPCompiler(GnuCompiler, CPPCompiler):
    def __init__(self, exelist, version, compiler_type, is_cross, exe_wrap, defines, **kwargs):
        CPPCompiler.__init__(self, exelist, version, is_cross, exe_wrap, **kwargs)
        GnuCompiler.__init__(self, compiler_type, defines)
        default_warn_args = ['-Wall', '-Winvalid-pch', '-Wnon-virtual-dtor']
        self.warn_args = {'1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}

    def get_options(self):
        opts = CPPCompiler.get_options(self)
        opts.update({'cpp_std': coredata.UserComboOption('cpp_std', 'C++ language standard to use',
                                                         ['none', 'c++98', 'c++03', 'c++11', 'c++14', 'c++17', 'c++1z', 'c++2a',
                                                          'gnu++03', 'gnu++11', 'gnu++14', 'gnu++17', 'gnu++1z', 'gnu++2a'],
                                                         'none'),
                     'cpp_debugstl': coredata.UserBooleanOption('cpp_debugstl',
                                                                'STL debug mode',
                                                                False)})
        if self.compiler_type == CompilerType.GCC_MINGW:
            opts.update({
                'cpp_winlibs': coredata.UserArrayOption('cpp_winlibs', 'Standard Win libraries to link against',
                                                        gnu_winlibs), })
        return opts

    def get_option_compile_args(self, options):
        args = []
        std = options['cpp_std']
        if std.value != 'none':
            args.append(self._find_best_cpp_std(std.value))
        if options['cpp_debugstl'].value:
            args.append('-D_GLIBCXX_DEBUG=1')
        return args

    def get_option_link_args(self, options):
        if self.compiler_type == CompilerType.GCC_MINGW:
            return options['cpp_winlibs'].value[:]
        return []

    def get_pch_use_args(self, pch_dir, header):
        return ['-fpch-preprocess', '-include', os.path.basename(header)]

    def language_stdlib_only_link_flags(self):
        return ['-lstdc++']


class ElbrusCPPCompiler(GnuCPPCompiler, ElbrusCompiler):
    def __init__(self, exelist, version, compiler_type, is_cross, exe_wrapper=None, defines=None, **kwargs):
        GnuCPPCompiler.__init__(self, exelist, version, compiler_type, is_cross, exe_wrapper, defines, **kwargs)
        ElbrusCompiler.__init__(self, compiler_type, defines)

    # It does not support c++/gnu++ 17 and 1z, but still does support 0x, 1y, and gnu++98.
    def get_options(self):
        opts = CPPCompiler.get_options(self)
        opts['cpp_std'] = coredata.UserComboOption('cpp_std', 'C++ language standard to use',
                                                   ['none', 'c++98', 'c++03', 'c++0x', 'c++11', 'c++14', 'c++1y',
                                                    'gnu++98', 'gnu++03', 'gnu++0x', 'gnu++11', 'gnu++14', 'gnu++1y'],
                                                   'none')
        return opts

    # Elbrus C++ compiler does not have lchmod, but there is only linker warning, not compiler error.
    # So we should explicitly fail at this case.
    def has_function(self, funcname, prefix, env, extra_args=None, dependencies=None):
        if funcname == 'lchmod':
            return False
        else:
            return super().has_function(funcname, prefix, env, extra_args, dependencies)


class IntelCPPCompiler(IntelCompiler, CPPCompiler):
    def __init__(self, exelist, version, compiler_type, is_cross, exe_wrap, **kwargs):
        CPPCompiler.__init__(self, exelist, version, is_cross, exe_wrap, **kwargs)
        IntelCompiler.__init__(self, compiler_type)
        self.lang_header = 'c++-header'
        default_warn_args = ['-Wall', '-w3', '-diag-disable:remark',
                             '-Wpch-messages', '-Wnon-virtual-dtor']
        self.warn_args = {'1': default_warn_args,
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
        opts.update({'cpp_std': coredata.UserComboOption('cpp_std', 'C++ language standard to use',
                                                         ['none'] + c_stds + g_stds,
                                                         'none'),
                     'cpp_debugstl': coredata.UserBooleanOption('cpp_debugstl',
                                                                'STL debug mode',
                                                                False)})
        return opts

    def get_option_compile_args(self, options):
        args = []
        std = options['cpp_std']
        if std.value != 'none':
            remap_cpp03 = {
                'c++03': 'c++98',
                'gnu++03': 'gnu++98'
            }
            args.append('-std=' + remap_cpp03.get(std.value, std.value))
        if options['cpp_debugstl'].value:
            args.append('-D_GLIBCXX_DEBUG=1')
        return args

    def get_option_link_args(self, options):
        return []


class VisualStudioCPPCompiler(VisualStudioCCompiler, CPPCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrap, is_64):
        CPPCompiler.__init__(self, exelist, version, is_cross, exe_wrap)
        VisualStudioCCompiler.__init__(self, exelist, version, is_cross, exe_wrap, is_64)
        self.base_options = ['b_pch', 'b_vscrt'] # FIXME add lto, pgo and the like

    def get_options(self):
        opts = CPPCompiler.get_options(self)
        opts.update({'cpp_eh': coredata.UserComboOption('cpp_eh',
                                                        'C++ exception handling type.',
                                                        ['none', 'a', 's', 'sc'],
                                                        'sc'),
                     'cpp_winlibs': coredata.UserArrayOption('cpp_winlibs',
                                                             'Windows libs to link against.',
                                                             msvc_winlibs)})
        return opts

    def get_option_compile_args(self, options):
        args = []
        std = options['cpp_eh']
        if std.value != 'none':
            args.append('/EH' + std.value)
        return args

    def get_option_link_args(self, options):
        return options['cpp_winlibs'].value[:]

    def get_compiler_check_args(self):
        # Visual Studio C++ compiler doesn't support -fpermissive,
        # so just use the plain C args.
        return VisualStudioCCompiler.get_compiler_check_args(self)


class ArmCPPCompiler(ArmCompiler, CPPCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrap=None, **kwargs):
        CPPCompiler.__init__(self, exelist, version, is_cross, exe_wrap, **kwargs)
        ArmCompiler.__init__(self)

    def get_options(self):
        opts = CPPCompiler.get_options(self)
        opts.update({'cpp_std': coredata.UserComboOption('cpp_std', 'C++ language standard to use',
                                                         ['none', 'c++03', 'c++11'],
                                                         'none')})
        return opts

    def get_option_compile_args(self, options):
        args = []
        std = options['cpp_std']
        if std.value == 'c++11':
            args.append('--cpp11')
        elif std.value == 'c++03':
            args.append('--cpp')
        return args

    def get_option_link_args(self, options):
        return []

    def get_compiler_check_args(self):
        return []
