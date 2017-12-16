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

from .. import coredata
from ..mesonlib import version_compare

from .c import CCompiler, VisualStudioCCompiler
from .compilers import (
    GCC_MINGW,
    gnu_winlibs,
    msvc_winlibs,
    ClangCompiler,
    GnuCompiler,
    IntelCompiler,
)

class CPPCompiler(CCompiler):
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


class ClangCPPCompiler(ClangCompiler, CPPCompiler):
    def __init__(self, exelist, version, cltype, is_cross, exe_wrapper=None, **kwargs):
        CPPCompiler.__init__(self, exelist, version, is_cross, exe_wrapper, **kwargs)
        ClangCompiler.__init__(self, cltype)
        default_warn_args = ['-Wall', '-Winvalid-pch', '-Wnon-virtual-dtor']
        self.warn_args = {'1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}

    def get_options(self):
        return {'cpp_std': coredata.UserComboOption('cpp_std', 'C++ language standard to use',
                                                    ['none', 'c++98', 'c++03', 'c++11', 'c++14', 'c++17', 'c++1z',
                                                     'gnu++11', 'gnu++14', 'gnu++17', 'gnu++1z'],
                                                    'none')}

    def get_option_compile_args(self, options):
        args = []
        std = options['cpp_std']
        if std.value != 'none':
            args.append('-std=' + std.value)
        return args

    def get_option_link_args(self, options):
        return []


class GnuCPPCompiler(GnuCompiler, CPPCompiler):
    def __init__(self, exelist, version, gcc_type, is_cross, exe_wrap, defines, **kwargs):
        CPPCompiler.__init__(self, exelist, version, is_cross, exe_wrap, **kwargs)
        GnuCompiler.__init__(self, gcc_type, defines)
        default_warn_args = ['-Wall', '-Winvalid-pch', '-Wnon-virtual-dtor']
        self.warn_args = {'1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}

    def get_options(self):
        opts = {'cpp_std': coredata.UserComboOption('cpp_std', 'C++ language standard to use',
                                                    ['none', 'c++98', 'c++03', 'c++11', 'c++14', 'c++17', 'c++1z',
                                                     'gnu++03', 'gnu++11', 'gnu++14', 'gnu++17', 'gnu++1z'],
                                                    'none'),
                'cpp_debugstl': coredata.UserBooleanOption('cpp_debugstl',
                                                           'STL debug mode',
                                                           False)}
        if self.gcc_type == GCC_MINGW:
            opts.update({
                'cpp_winlibs': coredata.UserArrayOption('cpp_winlibs', 'Standard Win libraries to link against',
                                                              gnu_winlibs), })
        return opts

    def get_option_compile_args(self, options):
        args = []
        std = options['cpp_std']
        if std.value != 'none':
            args.append('-std=' + std.value)
        if options['cpp_debugstl'].value:
            args.append('-D_GLIBCXX_DEBUG=1')
        return args

    def get_option_link_args(self, options):
        if self.gcc_type == GCC_MINGW:
            return options['cpp_winlibs'].value[:]
        return []

    def get_pch_use_args(self, pch_dir, header):
        return ['-fpch-preprocess', '-include', os.path.split(header)[-1]]


class IntelCPPCompiler(IntelCompiler, CPPCompiler):
    def __init__(self, exelist, version, icc_type, is_cross, exe_wrap, **kwargs):
        CPPCompiler.__init__(self, exelist, version, is_cross, exe_wrap, **kwargs)
        IntelCompiler.__init__(self, icc_type)
        self.lang_header = 'c++-header'
        default_warn_args = ['-Wall', '-w3', '-diag-disable:remark',
                             '-Wpch-messages', '-Wnon-virtual-dtor']
        self.warn_args = {'1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}

    def get_options(self):
        c_stds = []
        g_stds = ['gnu++98']
        if version_compare(self.version, '>=15.0.0'):
            c_stds += ['c++11', 'c++14']
            g_stds += ['gnu++11']
        if version_compare(self.version, '>=16.0.0'):
            c_stds += ['c++17']
        if version_compare(self.version, '>=17.0.0'):
            g_stds += ['gnu++14']
        opts = {'cpp_std': coredata.UserComboOption('cpp_std', 'C++ language standard to use',
                                                    ['none'] + c_stds + g_stds,
                                                    'none'),
                'cpp_debugstl': coredata.UserBooleanOption('cpp_debugstl',
                                                           'STL debug mode',
                                                           False)}
        return opts

    def get_option_compile_args(self, options):
        args = []
        std = options['cpp_std']
        if std.value != 'none':
            args.append('-std=' + std.value)
        if options['cpp_debugstl'].value:
            args.append('-D_GLIBCXX_DEBUG=1')
        return args

    def get_option_link_args(self, options):
        return []

    def has_multi_arguments(self, args, env):
        return super().has_multi_arguments(args + ['-diag-error', '10006'], env)


class VisualStudioCPPCompiler(VisualStudioCCompiler, CPPCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrap, is_64):
        self.language = 'cpp'
        VisualStudioCCompiler.__init__(self, exelist, version, is_cross, exe_wrap, is_64)
        self.base_options = ['b_pch'] # FIXME add lto, pgo and the like

    def get_options(self):
        return {'cpp_eh': coredata.UserComboOption('cpp_eh',
                                                   'C++ exception handling type.',
                                                   ['none', 'a', 's', 'sc'],
                                                   'sc'),
                'cpp_winlibs': coredata.UserArrayOption('cpp_winlibs',
                                                        'Windows libs to link against.',
                                                        msvc_winlibs)
                }

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
        return super(VisualStudioCCompiler, self).get_compiler_check_args()
