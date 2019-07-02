# Copyright 2019 The meson development team
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Provides mixins for GNU compilers and GNU-like compilers."""

import abc
import functools
import os
import pathlib
import subprocess
import typing

from ... import mesonlib
from ... import mlog

# XXX: prevent circular references.
# FIXME: this really is a posix interface not a c-like interface
clike_debug_args = {False: [],
                    True: ['-g']}

gnulike_buildtype_args = {'plain': [],
                          'debug': [],
                          'debugoptimized': [],
                          'release': [],
                          'minsize': [],
                          'custom': [],
                          }

apple_buildtype_linker_args = {'plain': [],
                               'debug': [],
                               'debugoptimized': [],
                               'release': [],
                               'minsize': [],
                               'custom': [],
                               }

gnulike_buildtype_linker_args = {'plain': [],
                                 'debug': [],
                                 'debugoptimized': [],
                                 'release': ['-Wl,-O1'],
                                 'minsize': [],
                                 'custom': [],
                                 }

gnu_optimization_args = {'0': [],
                         'g': ['-Og'],
                         '1': ['-O1'],
                         '2': ['-O2'],
                         '3': ['-O3'],
                         's': ['-Os'],
                         }

gnulike_instruction_set_args = {'mmx': ['-mmmx'],
                                'sse': ['-msse'],
                                'sse2': ['-msse2'],
                                'sse3': ['-msse3'],
                                'ssse3': ['-mssse3'],
                                'sse41': ['-msse4.1'],
                                'sse42': ['-msse4.2'],
                                'avx': ['-mavx'],
                                'avx2': ['-mavx2'],
                                'avx2': ['-mavx2'],
                                'neon': ['-mfpu=neon'],
                                }

gnu_symbol_visibility_args = {'': [],
                              'default': ['-fvisibility=default'],
                              'internal': ['-fvisibility=internal'],
                              'hidden': ['-fvisibility=hidden'],
                              'protected': ['-fvisibility=protected'],
                              'inlineshidden': ['-fvisibility=hidden', '-fvisibility-inlines-hidden'],
                              }

gnu_color_args = {'auto': ['-fdiagnostics-color=auto'],
                  'always': ['-fdiagnostics-color=always'],
                  'never': ['-fdiagnostics-color=never'],
                  }


def get_macos_dylib_install_name(prefix, shlib_name, suffix, soversion):
    install_name = prefix + shlib_name
    if soversion is not None:
        install_name += '.' + soversion
    install_name += '.dylib'
    return '@rpath/' + install_name


def get_gcc_soname_args(compiler_type, prefix, shlib_name, suffix, soversion, darwin_versions, is_shared_module):
    if compiler_type.is_standard_compiler:
        sostr = '' if soversion is None else '.' + soversion
        return ['-Wl,-soname,%s%s.%s%s' % (prefix, shlib_name, suffix, sostr)]
    elif compiler_type.is_windows_compiler:
        # For PE/COFF the soname argument has no effect with GNU LD
        return []
    elif compiler_type.is_osx_compiler:
        if is_shared_module:
            return []
        name = get_macos_dylib_install_name(prefix, shlib_name, suffix, soversion)
        args = ['-install_name', name]
        if darwin_versions:
            args += ['-compatibility_version', darwin_versions[0], '-current_version', darwin_versions[1]]
        return args
    else:
        raise RuntimeError('Not implemented yet.')


# TODO: The result from calling compiler should be cached. So that calling this
# function multiple times don't add latency.
def gnulike_default_include_dirs(compiler, lang):
    if lang == 'cpp':
        lang = 'c++'
    env = os.environ.copy()
    env["LC_ALL"] = 'C'
    cmd = compiler + ['-x{}'.format(lang), '-E', '-v', '-']
    p = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        env=env
    )
    stderr = p.stderr.read().decode('utf-8', errors='replace')
    parse_state = 0
    paths = []
    for line in stderr.split('\n'):
        if parse_state == 0:
            if line == '#include "..." search starts here:':
                parse_state = 1
        elif parse_state == 1:
            if line == '#include <...> search starts here:':
                parse_state = 2
            else:
                paths.append(line[1:])
        elif parse_state == 2:
            if line == 'End of search list.':
                break
            else:
                paths.append(line[1:])
    if not paths:
        mlog.warning('No include directory found parsing "{cmd}" output'.format(cmd=" ".join(cmd)))
    return paths


class GnuLikeCompiler(metaclass=abc.ABCMeta):
    """
    GnuLikeCompiler is a common interface to all compilers implementing
    the GNU-style commandline interface. This includes GCC, Clang
    and ICC. Certain functionality between them is different and requires
    that the actual concrete subclass define their own implementation.
    """
    def __init__(self, compiler_type):
        self.compiler_type = compiler_type
        self.base_options = ['b_pch', 'b_lto', 'b_pgo', 'b_sanitize', 'b_coverage',
                             'b_ndebug', 'b_staticpic', 'b_pie']
        if (not self.compiler_type.is_osx_compiler and
                not self.compiler_type.is_windows_compiler and
                not mesonlib.is_openbsd()):
            self.base_options.append('b_lundef')
        if not self.compiler_type.is_windows_compiler:
            self.base_options.append('b_asneeded')
        # All GCC-like backends can do assembly
        self.can_compile_suffixes.add('s')

    def get_asneeded_args(self):
        # GNU ld cannot be installed on macOS
        # https://github.com/Homebrew/homebrew-core/issues/17794#issuecomment-328174395
        # Hence, we don't need to differentiate between OS and ld
        # for the sake of adding as-needed support
        if self.compiler_type.is_osx_compiler:
            return '-Wl,-dead_strip_dylibs'
        else:
            return '-Wl,--as-needed'

    def get_pic_args(self):
        if self.compiler_type.is_osx_compiler or self.compiler_type.is_windows_compiler:
            return [] # On Window and OS X, pic is always on.
        return ['-fPIC']

    def get_pie_args(self):
        return ['-fPIE']

    def get_pie_link_args(self):
        return ['-pie']

    def get_buildtype_args(self, buildtype):
        return gnulike_buildtype_args[buildtype]

    @abc.abstractmethod
    def get_optimization_args(self, optimization_level):
        raise NotImplementedError("get_optimization_args not implemented")

    def get_debug_args(self, is_debug):
        return clike_debug_args[is_debug]

    def get_buildtype_linker_args(self, buildtype):
        if self.compiler_type.is_osx_compiler:
            return apple_buildtype_linker_args[buildtype]
        return gnulike_buildtype_linker_args[buildtype]

    @abc.abstractmethod
    def get_pch_suffix(self):
        raise NotImplementedError("get_pch_suffix not implemented")

    def split_shlib_to_parts(self, fname):
        return os.path.dirname(fname), fname

    def get_soname_args(self, *args):
        return get_gcc_soname_args(self.compiler_type, *args)

    def get_std_shared_lib_link_args(self):
        return ['-shared']

    def get_std_shared_module_link_args(self, options):
        if self.compiler_type.is_osx_compiler:
            return ['-bundle', '-Wl,-undefined,dynamic_lookup']
        return ['-shared']

    def get_link_whole_for(self, args):
        if self.compiler_type.is_osx_compiler:
            result = []
            for a in args:
                result += ['-Wl,-force_load', a]
            return result
        return ['-Wl,--whole-archive'] + args + ['-Wl,--no-whole-archive']

    def get_instruction_set_args(self, instruction_set):
        return gnulike_instruction_set_args.get(instruction_set, None)

    def get_default_include_dirs(self):
        return gnulike_default_include_dirs(self.exelist, self.language)

    @abc.abstractmethod
    def openmp_flags(self):
        raise NotImplementedError("openmp_flags not implemented")

    def gnu_symbol_visibility_args(self, vistype):
        return gnu_symbol_visibility_args[vistype]

    def gen_vs_module_defs_args(self, defsfile):
        if not isinstance(defsfile, str):
            raise RuntimeError('Module definitions file should be str')
        # On Windows targets, .def files may be specified on the linker command
        # line like an object file.
        if self.compiler_type.is_windows_compiler:
            return [defsfile]
        # For other targets, discard the .def file.
        return []

    def get_argument_syntax(self):
        return 'gcc'

    def get_profile_generate_args(self):
        return ['-fprofile-generate']

    def get_profile_use_args(self):
        return ['-fprofile-use', '-fprofile-correction']

    def get_allow_undefined_link_args(self):
        if self.compiler_type.is_osx_compiler:
            # Apple ld
            return ['-Wl,-undefined,dynamic_lookup']
        elif self.compiler_type.is_windows_compiler:
            # For PE/COFF this is impossible
            return []
        elif mesonlib.is_sunos():
            return []
        else:
            # GNU ld and LLVM lld
            return ['-Wl,--allow-shlib-undefined']

    def get_gui_app_args(self, value):
        if self.compiler_type.is_windows_compiler:
            return ['-mwindows' if value else '-mconsole']
        return []

    def compute_parameters_with_absolute_paths(self, parameter_list, build_dir):
        for idx, i in enumerate(parameter_list):
            if i[:2] == '-I' or i[:2] == '-L':
                parameter_list[idx] = i[:2] + os.path.normpath(os.path.join(build_dir, i[2:]))

        return parameter_list

    @functools.lru_cache()
    def _get_search_dirs(self, env):
        extra_args = ['--print-search-dirs']
        stdo = None
        with self._build_wrapper('', env, extra_args=extra_args,
                                 dependencies=None, mode='compile',
                                 want_output=True) as p:
            stdo = p.stdo
        return stdo

    def _split_fetch_real_dirs(self, pathstr):
        # We need to use the path separator used by the compiler for printing
        # lists of paths ("gcc --print-search-dirs"). By default
        # we assume it uses the platform native separator.
        pathsep = os.pathsep

        # clang uses ':' instead of ';' on Windows https://reviews.llvm.org/D61121
        # so we need to repair things like 'C:\foo:C:\bar'
        if pathsep == ';':
            pathstr = re.sub(r':([^/\\])', r';\1', pathstr)

        # pathlib treats empty paths as '.', so filter those out
        paths = [p for p in pathstr.split(pathsep) if p]

        result = []
        for p in paths:
            # GCC returns paths like this:
            # /usr/lib/gcc/x86_64-linux-gnu/8/../../../../x86_64-linux-gnu/lib
            # It would make sense to normalize them to get rid of the .. parts
            # Sadly when you are on a merged /usr fs it also kills these:
            # /lib/x86_64-linux-gnu
            # since /lib is a symlink to /usr/lib. This would mean
            # paths under /lib would be considered not a "system path",
            # which is wrong and breaks things. Store everything, just to be sure.
            pobj = pathlib.Path(p)
            unresolved = pobj.as_posix()
            if pobj.exists():
                if unresolved not in result:
                    result.append(unresolved)
                try:
                    resolved = pathlib.Path(p).resolve().as_posix()
                    if resolved not in result:
                        result.append(resolved)
                except FileNotFoundError:
                    pass
        return tuple(result)

    def get_compiler_dirs(self, env, name):
        '''
        Get dirs from the compiler, either `libraries:` or `programs:`
        '''
        stdo = self._get_search_dirs(env)
        for line in stdo.split('\n'):
            if line.startswith(name + ':'):
                return self._split_fetch_real_dirs(line.split('=', 1)[1])
        return ()


class GnuCompiler(GnuLikeCompiler):
    """
    GnuCompiler represents an actual GCC in its many incarnations.
    Compilers imitating GCC (Clang/Intel) should use the GnuLikeCompiler ABC.
    """
    def __init__(self, compiler_type, defines: dict):
        super().__init__(compiler_type)
        self.id = 'gcc'
        self.defines = defines or {}
        self.base_options.append('b_colorout')

    def get_colorout_args(self, colortype: str) -> typing.List[str]:
        if mesonlib.version_compare(self.version, '>=4.9.0'):
            return gnu_color_args[colortype][:]
        return []

    def get_warn_args(self, level: str) -> list:
        args = super().get_warn_args(level)
        if mesonlib.version_compare(self.version, '<4.8.0') and '-Wpedantic' in args:
            # -Wpedantic was added in 4.8.0
            # https://gcc.gnu.org/gcc-4.8/changes.html
            args[args.index('-Wpedantic')] = '-pedantic'
        return args

    def has_builtin_define(self, define: str) -> bool:
        return define in self.defines

    def get_builtin_define(self, define):
        if define in self.defines:
            return self.defines[define]

    def get_optimization_args(self, optimization_level: str):
        return gnu_optimization_args[optimization_level]

    def get_pch_suffix(self) -> str:
        return 'gch'

    def openmp_flags(self) -> typing.List[str]:
        return ['-fopenmp']
