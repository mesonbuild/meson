# Copyright 2012-2019 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import abc
import contextlib, os.path, re, tempfile
import enum
import itertools
import typing as T
from functools import lru_cache

from .. import coredata
from .. import mlog
from .. import mesonlib
from ..linkers import LinkerEnvVarsMixin
from ..mesonlib import (
    EnvironmentException, MachineChoice, MesonException,
    Popen_safe, split_args, LibType
)
from ..envconfig import (
    get_env_var
)

from ..arglist import CompilerArgs

if T.TYPE_CHECKING:
    from ..build import BuildTarget
    from ..coredata import OptionDictType
    from ..envconfig import MachineInfo
    from ..environment import Environment
    from ..linkers import DynamicLinker  # noqa: F401
    from ..dependencies import Dependency

    CompilerType = T.TypeVar('CompilerType', bound=Compiler)
    _T = T.TypeVar('_T')

"""This file contains the data files of all compilers Meson knows
about. To support a new compiler, add its information below.
Also add corresponding autodetection code in environment.py."""

header_suffixes = ('h', 'hh', 'hpp', 'hxx', 'H', 'ipp', 'moc', 'vapi', 'di')  # type: T.Tuple[str, ...]
obj_suffixes = ('o', 'obj', 'res')  # type: T.Tuple[str, ...]
lib_suffixes = ('a', 'lib', 'dll', 'dll.a', 'dylib', 'so')  # type: T.Tuple[str, ...]
# Mapping of language to suffixes of files that should always be in that language
# This means we can't include .h headers here since they could be C, C++, ObjC, etc.
lang_suffixes = {
    'c': ('c',),
    'cpp': ('cpp', 'cc', 'cxx', 'c++', 'hh', 'hpp', 'ipp', 'hxx', 'ino'),
    'cuda': ('cu',),
    # f90, f95, f03, f08 are for free-form fortran ('f90' recommended)
    # f, for, ftn, fpp are for fixed-form fortran ('f' or 'for' recommended)
    'fortran': ('f90', 'f95', 'f03', 'f08', 'f', 'for', 'ftn', 'fpp'),
    'd': ('d', 'di'),
    'objc': ('m',),
    'objcpp': ('mm',),
    'rust': ('rs',),
    'vala': ('vala', 'vapi', 'gs'),
    'cs': ('cs',),
    'swift': ('swift',),
    'java': ('java',),
}  # type: T.Dict[str, T.Tuple[str, ...]]
all_languages = lang_suffixes.keys()
cpp_suffixes = lang_suffixes['cpp'] + ('h',)  # type: T.Tuple[str, ...]
c_suffixes = lang_suffixes['c'] + ('h',)  # type: T.Tuple[str, ...]
# List of languages that by default consume and output libraries following the
# C ABI; these can generally be used interchangebly
clib_langs = ('objcpp', 'cpp', 'objc', 'c', 'fortran',)  # type: T.Tuple[str, ...]
# List of languages that can be linked with C code directly by the linker
# used in build.py:process_compilers() and build.py:get_dynamic_linker()
clink_langs = ('d', 'cuda') + clib_langs  # type: T.Tuple[str, ...]
clink_suffixes = tuple()  # type: T.Tuple[str, ...]
for _l in clink_langs + ('vala',):
    clink_suffixes += lang_suffixes[_l]
clink_suffixes += ('h', 'll', 's')
all_suffixes = set(itertools.chain(*lang_suffixes.values(), clink_suffixes))  # type: T.Set[str]

# Languages that should use LDFLAGS arguments when linking.
languages_using_ldflags = {'objcpp', 'cpp', 'objc', 'c', 'fortran', 'd', 'cuda'}  # type: T.Set[str]
# Languages that should use CPPFLAGS arguments when linking.
languages_using_cppflags = {'c', 'cpp', 'objc', 'objcpp'}  # type: T.Set[str]
soregex = re.compile(r'.*\.so(\.[0-9]+)?(\.[0-9]+)?(\.[0-9]+)?$')

# Environment variables that each lang uses.
cflags_mapping = {'c': 'CFLAGS',
                  'cpp': 'CXXFLAGS',
                  'cuda': 'CUFLAGS',
                  'objc': 'OBJCFLAGS',
                  'objcpp': 'OBJCXXFLAGS',
                  'fortran': 'FFLAGS',
                  'd': 'DFLAGS',
                  'vala': 'VALAFLAGS',
                  'rust': 'RUSTFLAGS'}  # type: T.Dict[str, str]

cexe_mapping = {'c': 'CC',
                'cpp': 'CXX'}

# All these are only for C-linkable languages; see `clink_langs` above.

def sort_clink(lang: str) -> int:
    '''
    Sorting function to sort the list of languages according to
    reversed(compilers.clink_langs) and append the unknown langs in the end.
    The purpose is to prefer C over C++ for files that can be compiled by
    both such as assembly, C, etc. Also applies to ObjC, ObjC++, etc.
    '''
    if lang not in clink_langs:
        return 1
    return -clink_langs.index(lang)

def is_header(fname: 'mesonlib.FileOrString') -> bool:
    if isinstance(fname, mesonlib.File):
        fname = fname.fname
    suffix = fname.split('.')[-1]
    return suffix in header_suffixes

def is_source(fname: 'mesonlib.FileOrString') -> bool:
    if isinstance(fname, mesonlib.File):
        fname = fname.fname
    suffix = fname.split('.')[-1].lower()
    return suffix in clink_suffixes

def is_assembly(fname: 'mesonlib.FileOrString') -> bool:
    if isinstance(fname, mesonlib.File):
        fname = fname.fname
    return fname.split('.')[-1].lower() == 's'

def is_llvm_ir(fname: 'mesonlib.FileOrString') -> bool:
    if isinstance(fname, mesonlib.File):
        fname = fname.fname
    return fname.split('.')[-1] == 'll'

@lru_cache(maxsize=None)
def cached_by_name(fname: 'mesonlib.FileOrString') -> bool:
    suffix = fname.split('.')[-1]
    return suffix in obj_suffixes

def is_object(fname: 'mesonlib.FileOrString') -> bool:
    if isinstance(fname, mesonlib.File):
        fname = fname.fname
    return cached_by_name(fname)

def is_library(fname: 'mesonlib.FileOrString') -> bool:
    if isinstance(fname, mesonlib.File):
        fname = fname.fname

    if soregex.match(fname):
        return True

    suffix = fname.split('.')[-1]
    return suffix in lib_suffixes

def is_known_suffix(fname: 'mesonlib.FileOrString') -> bool:
    if isinstance(fname, mesonlib.File):
        fname = fname.fname
    suffix = fname.split('.')[-1]

    return suffix in all_suffixes


class CompileCheckMode(enum.Enum):

    PREPROCESS = 'preprocess'
    COMPILE = 'compile'
    LINK = 'link'


cuda_buildtype_args = {'plain': [],
                       'debug': [],
                       'debugoptimized': [],
                       'release': [],
                       'minsize': [],
                       }  # type: T.Dict[str, T.List[str]]
java_buildtype_args = {'plain': [],
                       'debug': ['-g'],
                       'debugoptimized': ['-g'],
                       'release': [],
                       'minsize': [],
                       'custom': [],
                       }  # type: T.Dict[str, T.List[str]]

rust_buildtype_args = {'plain': [],
                       'debug': [],
                       'debugoptimized': [],
                       'release': [],
                       'minsize': [],
                       'custom': [],
                       }  # type: T.Dict[str, T.List[str]]

d_gdc_buildtype_args = {'plain': [],
                        'debug': [],
                        'debugoptimized': ['-finline-functions'],
                        'release': ['-finline-functions'],
                        'minsize': [],
                        'custom': [],
                        }  # type: T.Dict[str, T.List[str]]

d_ldc_buildtype_args = {'plain': [],
                        'debug': [],
                        'debugoptimized': ['-enable-inlining', '-Hkeep-all-bodies'],
                        'release': ['-enable-inlining', '-Hkeep-all-bodies'],
                        'minsize': [],
                        'custom': [],
                        }  # type: T.Dict[str, T.List[str]]

d_dmd_buildtype_args = {'plain': [],
                        'debug': [],
                        'debugoptimized': ['-inline'],
                        'release': ['-inline'],
                        'minsize': [],
                        'custom': [],
                        }  # type: T.Dict[str, T.List[str]]

mono_buildtype_args = {'plain': [],
                       'debug': [],
                       'debugoptimized': ['-optimize+'],
                       'release': ['-optimize+'],
                       'minsize': [],
                       'custom': [],
                       }  # type: T.Dict[str, T.List[str]]

swift_buildtype_args = {'plain': [],
                        'debug': [],
                        'debugoptimized': [],
                        'release': [],
                        'minsize': [],
                        'custom': [],
                        }  # type: T.Dict[str, T.List[str]]

gnu_winlibs = ['-lkernel32', '-luser32', '-lgdi32', '-lwinspool', '-lshell32',
               '-lole32', '-loleaut32', '-luuid', '-lcomdlg32', '-ladvapi32']  # type: T.List[str]

msvc_winlibs = ['kernel32.lib', 'user32.lib', 'gdi32.lib',
                'winspool.lib', 'shell32.lib', 'ole32.lib', 'oleaut32.lib',
                'uuid.lib', 'comdlg32.lib', 'advapi32.lib']  # type: T.List[str]

clike_optimization_args = {'0': [],
                           'g': [],
                           '1': ['-O1'],
                           '2': ['-O2'],
                           '3': ['-O3'],
                           's': ['-Os'],
                           }  # type: T.Dict[str, T.List[str]]

cuda_optimization_args = {'0': [],
                          'g': ['-O0'],
                          '1': ['-O1'],
                          '2': ['-O2'],
                          '3': ['-O3'],
                          's': ['-O3']
                          }  # type: T.Dict[str, T.List[str]]

cuda_debug_args = {False: [],
                   True: ['-g']}  # type: T.Dict[bool, T.List[str]]

clike_debug_args = {False: [],
                    True: ['-g']}  # type: T.Dict[bool, T.List[str]]

base_options = {'b_pch': coredata.UserBooleanOption('Use precompiled headers', True),
                'b_lto': coredata.UserBooleanOption('Use link time optimization', False),
                'b_sanitize': coredata.UserComboOption('Code sanitizer to use',
                                                       ['none', 'address', 'thread', 'undefined', 'memory', 'address,undefined'],
                                                       'none'),
                'b_lundef': coredata.UserBooleanOption('Use -Wl,--no-undefined when linking', True),
                'b_asneeded': coredata.UserBooleanOption('Use -Wl,--as-needed when linking', True),
                'b_pgo': coredata.UserComboOption('Use profile guided optimization',
                                                  ['off', 'generate', 'use'],
                                                  'off'),
                'b_coverage': coredata.UserBooleanOption('Enable coverage tracking.',
                                                         False),
                'b_colorout': coredata.UserComboOption('Use colored output',
                                                       ['auto', 'always', 'never'],
                                                       'always'),
                'b_ndebug': coredata.UserComboOption('Disable asserts',
                                                     ['true', 'false', 'if-release'], 'false'),
                'b_staticpic': coredata.UserBooleanOption('Build static libraries as position independent',
                                                          True),
                'b_pie': coredata.UserBooleanOption('Build executables as position independent',
                                                    False),
                'b_bitcode': coredata.UserBooleanOption('Generate and embed bitcode (only macOS/iOS/tvOS)',
                                                        False),
                'b_vscrt': coredata.UserComboOption('VS run-time library type to use.',
                                                    ['none', 'md', 'mdd', 'mt', 'mtd', 'from_buildtype', 'static_from_buildtype'],
                                                    'from_buildtype'),
                }  # type: OptionDictType

def option_enabled(boptions: T.List[str], options: 'OptionDictType',
                   option: str) -> bool:
    try:
        if option not in boptions:
            return False
        ret = options[option].value
        assert isinstance(ret, bool), 'must return bool'  # could also be str
        return ret
    except KeyError:
        return False

def get_base_compile_args(options: 'OptionDictType', compiler: 'Compiler') -> T.List[str]:
    args = []  # type T.List[str]
    try:
        if options['b_lto'].value:
            args.extend(compiler.get_lto_compile_args())
    except KeyError:
        pass
    try:
        args += compiler.get_colorout_args(options['b_colorout'].value)
    except KeyError:
        pass
    try:
        args += compiler.sanitizer_compile_args(options['b_sanitize'].value)
    except KeyError:
        pass
    try:
        pgo_val = options['b_pgo'].value
        if pgo_val == 'generate':
            args.extend(compiler.get_profile_generate_args())
        elif pgo_val == 'use':
            args.extend(compiler.get_profile_use_args())
    except KeyError:
        pass
    try:
        if options['b_coverage'].value:
            args += compiler.get_coverage_args()
    except KeyError:
        pass
    try:
        if (options['b_ndebug'].value == 'true' or
                (options['b_ndebug'].value == 'if-release' and
                 options['buildtype'].value in {'release', 'plain'})):
            args += compiler.get_disable_assert_args()
    except KeyError:
        pass
    # This does not need a try...except
    if option_enabled(compiler.base_options, options, 'b_bitcode'):
        args.append('-fembed-bitcode')
    try:
        crt_val = options['b_vscrt'].value
        buildtype = options['buildtype'].value
        try:
            args += compiler.get_crt_compile_args(crt_val, buildtype)
        except AttributeError:
            pass
    except KeyError:
        pass
    return args

def get_base_link_args(options: 'OptionDictType', linker: 'Compiler',
                       is_shared_module: bool) -> T.List[str]:
    args = []  # type: T.List[str]
    try:
        if options['b_lto'].value:
            args.extend(linker.get_lto_link_args())
    except KeyError:
        pass
    try:
        args += linker.sanitizer_link_args(options['b_sanitize'].value)
    except KeyError:
        pass
    try:
        pgo_val = options['b_pgo'].value
        if pgo_val == 'generate':
            args.extend(linker.get_profile_generate_args())
        elif pgo_val == 'use':
            args.extend(linker.get_profile_use_args())
    except KeyError:
        pass
    try:
        if options['b_coverage'].value:
            args += linker.get_coverage_link_args()
    except KeyError:
        pass

    as_needed = option_enabled(linker.base_options, options, 'b_asneeded')
    bitcode = option_enabled(linker.base_options, options, 'b_bitcode')
    # Shared modules cannot be built with bitcode_bundle because
    # -bitcode_bundle is incompatible with -undefined and -bundle
    if bitcode and not is_shared_module:
        args.extend(linker.bitcode_args())
    elif as_needed:
        # -Wl,-dead_strip_dylibs is incompatible with bitcode
        args.extend(linker.get_asneeded_args())

    # Apple's ld (the only one that supports bitcode) does not like -undefined
    # arguments or -headerpad_max_install_names when bitcode is enabled
    if not bitcode:
        args.extend(linker.headerpad_args())
        if (not is_shared_module and
                option_enabled(linker.base_options, options, 'b_lundef')):
            args.extend(linker.no_undefined_link_args())
        else:
            args.extend(linker.get_allow_undefined_link_args())

    try:
        crt_val = options['b_vscrt'].value
        buildtype = options['buildtype'].value
        try:
            args += linker.get_crt_link_args(crt_val, buildtype)
        except AttributeError:
            pass
    except KeyError:
        pass
    return args


class CrossNoRunException(MesonException):
    pass

class RunResult:
    def __init__(self, compiled: bool, returncode: int = 999,
                 stdout: str = 'UNDEFINED', stderr: str = 'UNDEFINED'):
        self.compiled = compiled
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class CompileResult:

    """The result of Compiler.compiles (and friends)."""

    def __init__(self, stdo: T.Optional[str] = None, stde: T.Optional[str] = None,
                 args: T.Optional[T.List[str]] = None,
                 returncode: int = 999, pid: int = -1,
                 text_mode: bool = True,
                 input_name: T.Optional[str] = None,
                 output_name: T.Optional[str] = None,
                 command: T.Optional[T.List[str]] = None, cached: bool = False):
        self.stdout = stdo
        self.stderr = stde
        self.input_name = input_name
        self.output_name = output_name
        self.command = command or []
        self.args = args or []
        self.cached = cached
        self.returncode = returncode
        self.pid = pid
        self.text_mode = text_mode


class Compiler(metaclass=abc.ABCMeta):
    # Libraries to ignore in find_library() since they are provided by the
    # compiler or the C library. Currently only used for MSVC.
    ignore_libs = []  # type: T.List[str]
    # Libraries that are internal compiler implementations, and must not be
    # manually searched.
    internal_libs = []  # type: T.List[str]

    LINKER_PREFIX = None  # type: T.Union[None, str, T.List[str]]
    INVOKES_LINKER = True

    # TODO: these could be forward declarations once we drop 3.5 support
    if T.TYPE_CHECKING:
        language = 'unset'
        id = ''
        warn_args = {}  # type: T.Dict[str, T.List[str]]

    def __init__(self, exelist: T.List[str], version: str,
                 for_machine: MachineChoice, info: 'MachineInfo',
                 linker: T.Optional['DynamicLinker'] = None,
                 full_version: T.Optional[str] = None, is_cross: bool = False):
        self.exelist = exelist
        # In case it's been overridden by a child class already
        if not hasattr(self, 'file_suffixes'):
            self.file_suffixes = lang_suffixes[self.language]
        if not hasattr(self, 'can_compile_suffixes'):
            self.can_compile_suffixes = set(self.file_suffixes)
        self.default_suffix = self.file_suffixes[0]
        self.version = version
        self.full_version = full_version
        self.for_machine = for_machine
        self.base_options = []  # type: T.List[str]
        self.linker = linker
        self.info = info
        self.is_cross = is_cross

    def __repr__(self) -> str:
        repr_str = "<{0}: v{1} `{2}`>"
        return repr_str.format(self.__class__.__name__, self.version,
                               ' '.join(self.exelist))

    @lru_cache(maxsize=None)
    def can_compile(self, src: 'mesonlib.FileOrString') -> bool:
        if isinstance(src, mesonlib.File):
            src = src.fname
        suffix = os.path.splitext(src)[1].lower()
        return bool(suffix) and suffix[1:] in self.can_compile_suffixes

    def get_id(self) -> str:
        return self.id

    def get_linker_id(self) -> str:
        # There is not guarantee that we have a dynamic linker instance, as
        # some languages don't have separate linkers and compilers. In those
        # cases return the compiler id
        try:
            return self.linker.id
        except AttributeError:
            return self.id

    def get_version_string(self) -> str:
        details = [self.id, self.version]
        if self.full_version:
            details += ['"%s"' % (self.full_version)]
        return '(%s)' % (' '.join(details))

    def get_language(self) -> str:
        return self.language

    @classmethod
    def get_display_language(cls) -> str:
        return cls.language.capitalize()

    def get_default_suffix(self) -> str:
        return self.default_suffix

    def get_define(self, dname: str, prefix: str, env: 'Environment',
                   extra_args: T.List[str], dependencies: T.List['Dependency'],
                   disable_cache: bool = False) -> T.Tuple[str, bool]:
        raise EnvironmentException('%s does not support get_define ' % self.get_id())

    def compute_int(self, expression: str, low: T.Optional[int], high: T.Optional[int],
                    guess: T.Optional[int], prefix: str, env: 'Environment', *,
                    extra_args: T.Optional[T.List[str]], dependencies: T.Optional[T.List['Dependency']]) -> int:
        raise EnvironmentException('%s does not support compute_int ' % self.get_id())

    def compute_parameters_with_absolute_paths(self, parameter_list: T.List[str],
                                               build_dir: str) -> T.List[str]:
        raise EnvironmentException('%s does not support compute_parameters_with_absolute_paths ' % self.get_id())

    def has_members(self, typename: str, membernames: T.List[str],
                    prefix: str, env: 'Environment', *,
                    extra_args: T.Optional[T.List[str]] = None,
                    dependencies: T.Optional[T.List['Dependency']] = None) -> T.Tuple[bool, bool]:
        raise EnvironmentException('%s does not support has_member(s) ' % self.get_id())

    def has_type(self, typename: str, prefix: str, env: 'Environment',
                 extra_args: T.List[str], *,
                 dependencies: T.Optional[T.List['Dependency']] = None) -> T.Tuple[bool, bool]:
        raise EnvironmentException('%s does not support has_type ' % self.get_id())

    def symbols_have_underscore_prefix(self, env: 'Environment') -> bool:
        raise EnvironmentException('%s does not support symbols_have_underscore_prefix ' % self.get_id())

    def get_exelist(self) -> T.List[str]:
        return self.exelist.copy()

    def get_linker_exelist(self) -> T.List[str]:
        return self.linker.get_exelist()

    @abc.abstractmethod
    def get_output_args(self, outputname: str) -> T.List[str]:
        pass

    def get_linker_output_args(self, outputname: str) -> T.List[str]:
        return self.linker.get_output_args(outputname)

    def get_builtin_define(self, define: str) -> T.Optional[str]:
        raise EnvironmentException('%s does not support get_builtin_define.' % self.id)

    def has_builtin_define(self, define: str) -> bool:
        raise EnvironmentException('%s does not support has_builtin_define.' % self.id)

    def get_always_args(self) -> T.List[str]:
        return []

    def can_linker_accept_rsp(self) -> bool:
        """
        Determines whether the linker can accept arguments using the @rsp syntax.
        """
        return self.linker.get_accepts_rsp()

    def get_linker_always_args(self) -> T.List[str]:
        return self.linker.get_always_args()

    def get_linker_lib_prefix(self) -> str:
        return self.linker.get_lib_prefix()

    def gen_import_library_args(self, implibname: str) -> T.List[str]:
        """
        Used only on Windows for libraries that need an import library.
        This currently means C, C++, Fortran.
        """
        return []

    def get_linker_args_from_envvars(self,
                                     for_machine: MachineChoice,
                                     is_cross: bool) -> T.List[str]:
        return self.linker.get_args_from_envvars(for_machine, is_cross)

    def get_options(self) -> 'OptionDictType':
        return {}

    def get_option_compile_args(self, options: 'OptionDictType') -> T.List[str]:
        return []

    def get_option_link_args(self, options: 'OptionDictType') -> T.List[str]:
        return self.linker.get_option_args(options)

    def check_header(self, hname: str, prefix: str, env: 'Environment', *,
                     extra_args: T.Optional[T.List[str]] = None,
                     dependencies: T.Optional[T.List['Dependency']] = None) -> T.Tuple[bool, bool]:
        """Check that header is usable.

        Returns a two item tuple of bools. The first bool is whether the
        check succeeded, the second is whether the result was cached (True)
        or run fresh (False).
        """
        raise EnvironmentException('Language %s does not support header checks.' % self.get_display_language())

    def has_header(self, hname: str, prefix: str, env: 'Environment', *,
                   extra_args: T.Optional[T.List[str]] = None,
                   dependencies: T.Optional[T.List['Dependency']] = None,
                   disable_cache: bool = False) -> T.Tuple[bool, bool]:
        """Check that header is exists.

        This check will return true if the file exists, even if it contains:

        ```c
        # error "You thought you could use this, LOLZ!"
        ```

        Use check_header if your header only works in some cases.

        Returns a two item tuple of bools. The first bool is whether the
        check succeeded, the second is whether the result was cached (True)
        or run fresh (False).
        """
        raise EnvironmentException('Language %s does not support header checks.' % self.get_display_language())

    def has_header_symbol(self, hname: str, symbol: str, prefix: str,
                          env: 'Environment', *,
                          extra_args: T.Optional[T.List[str]] = None,
                          dependencies: T.Optional[T.List['Dependency']] = None) -> T.Tuple[bool, bool]:
        raise EnvironmentException('Language %s does not support header symbol checks.' % self.get_display_language())

    def run(self, code: str, env: 'Environment', *,
            extra_args: T.Optional[T.List[str]] = None,
            dependencies: T.Optional[T.List['Dependency']] = None) -> RunResult:
        raise EnvironmentException('Language %s does not support run checks.' % self.get_display_language())

    def sizeof(self, typename: str, prefix: str, env: 'Environment', *,
               extra_args: T.Optional[T.List[str]] = None,
               dependencies: T.Optional[T.List['Dependency']] = None) -> int:
        raise EnvironmentException('Language %s does not support sizeof checks.' % self.get_display_language())

    def alignment(self, typename: str, prefix: str, env: 'Environment', *,
                 extra_args: T.Optional[T.List[str]] = None,
                 dependencies: T.Optional[T.List['Dependency']] = None) -> int:
        raise EnvironmentException('Language %s does not support alignment checks.' % self.get_display_language())

    def has_function(self, funcname: str, prefix: str, env: 'Environment', *,
                     extra_args: T.Optional[T.List[str]] = None,
                     dependencies: T.Optional[T.List['Dependency']] = None) -> T.Tuple[bool, bool]:
        """See if a function exists.

        Returns a two item tuple of bools. The first bool is whether the
        check succeeded, the second is whether the result was cached (True)
        or run fresh (False).
        """
        raise EnvironmentException('Language %s does not support function checks.' % self.get_display_language())

    def unix_args_to_native(self, args: T.List[str]) -> T.List[str]:
        "Always returns a copy that can be independently mutated"
        return args.copy()

    @classmethod
    def native_args_to_unix(cls, args: T.List[str]) -> T.List[str]:
        "Always returns a copy that can be independently mutated"
        return args.copy()

    def find_library(self, libname: str, env: 'Environment', extra_dirs: T.List[str],
                     libtype: LibType = LibType.PREFER_SHARED) -> T.Optional[T.List[str]]:
        raise EnvironmentException('Language {} does not support library finding.'.format(self.get_display_language()))

    def get_library_naming(self, env: 'Environment', libtype: LibType,
                           strict: bool = False) -> T.Optional[T.Tuple[str, ...]]:
        raise EnvironmentException(
            'Language {} does not support get_library_naming.'.format(
                self.get_display_language()))

    def get_program_dirs(self, env: 'Environment') -> T.List[str]:
        return []

    def has_multi_arguments(self, args: T.List[str], env: 'Environment') -> T.Tuple[bool, bool]:
        raise EnvironmentException(
            'Language {} does not support has_multi_arguments.'.format(
                self.get_display_language()))

    def has_multi_link_arguments(self, args: T.List[str], env: 'Environment') -> T.Tuple[bool, bool]:
        return self.linker.has_multi_arguments(args, env)

    def _get_compile_output(self, dirname: str, mode: str) -> str:
        # TODO: mode should really be an enum
        # In pre-processor mode, the output is sent to stdout and discarded
        if mode == 'preprocess':
            return None
        # Extension only matters if running results; '.exe' is
        # guaranteed to be executable on every platform.
        if mode == 'link':
            suffix = 'exe'
        else:
            suffix = 'obj'
        return os.path.join(dirname, 'output.' + suffix)

    def get_compiler_args_for_mode(self, mode: CompileCheckMode) -> T.List[str]:
        # TODO: mode should really be an enum
        args = []  # type: T.List[str]
        args += self.get_always_args()
        if mode is CompileCheckMode.COMPILE:
            args += self.get_compile_only_args()
        elif mode is CompileCheckMode.PREPROCESS:
            args += self.get_preprocess_only_args()
        else:
            assert mode is CompileCheckMode.LINK
        return args

    def compiler_args(self, args: T.Optional[T.Iterable[str]] = None) -> CompilerArgs:
        """Return an appropriate CompilerArgs instance for this class."""
        return CompilerArgs(self, args)

    @contextlib.contextmanager
    def compile(self, code: 'mesonlib.FileOrString',
                extra_args: T.Union[None, CompilerArgs, T.List[str]] = None,
                *, mode: str = 'link', want_output: bool = False,
                temp_dir: T.Optional[str] = None) -> T.Iterator[T.Optional[CompileResult]]:
        # TODO: there isn't really any reason for this to be a contextmanager
        if extra_args is None:
            extra_args = []
        try:
            with tempfile.TemporaryDirectory(dir=temp_dir) as tmpdirname:
                no_ccache = False
                if isinstance(code, str):
                    srcname = os.path.join(tmpdirname,
                                           'testfile.' + self.default_suffix)
                    with open(srcname, 'w') as ofile:
                        ofile.write(code)
                    # ccache would result in a cache miss
                    no_ccache = True
                    contents = code
                elif isinstance(code, mesonlib.File):
                    srcname = code.fname
                    with open(code.fname, 'r') as f:
                        contents = f.read()

                # Construct the compiler command-line
                commands = self.compiler_args()
                commands.append(srcname)
                # Preprocess mode outputs to stdout, so no output args
                if mode != 'preprocess':
                    output = self._get_compile_output(tmpdirname, mode)
                    commands += self.get_output_args(output)
                commands.extend(self.get_compiler_args_for_mode(CompileCheckMode(mode)))
                # extra_args must be last because it could contain '/link' to
                # pass args to VisualStudio's linker. In that case everything
                # in the command line after '/link' is given to the linker.
                commands += extra_args
                # Generate full command-line with the exelist
                command_list = self.get_exelist() + commands.to_native()
                mlog.debug('Running compile:')
                mlog.debug('Working directory: ', tmpdirname)
                mlog.debug('Command line: ', ' '.join(command_list), '\n')
                mlog.debug('Code:\n', contents)
                os_env = os.environ.copy()
                os_env['LC_ALL'] = 'C'
                if no_ccache:
                    os_env['CCACHE_DISABLE'] = '1'
                p, stdo, stde = Popen_safe(command_list, cwd=tmpdirname, env=os_env)
                mlog.debug('Compiler stdout:\n', stdo)
                mlog.debug('Compiler stderr:\n', stde)

                result = CompileResult(stdo, stde, list(commands), p.returncode, p.pid, input_name=srcname)
                if want_output:
                    result.output_name = output
                yield result
        except OSError:
            # On Windows antivirus programs and the like hold on to files so
            # they can't be deleted. There's not much to do in this case. Also,
            # catch OSError because the directory is then no longer empty.
            yield None

    @contextlib.contextmanager
    def cached_compile(self, code: str, cdata: coredata.CoreData, *,
                       extra_args: T.Union[None, T.List[str], CompilerArgs] = None,
                       mode: str = 'link',
                       temp_dir: T.Optional[str] = None) -> T.Iterator[T.Optional[CompileResult]]:
        # TODO: There's isn't really any reason for this to be a context manager

        # Calculate the key
        textra_args = tuple(extra_args) if extra_args is not None else tuple()  # type: T.Tuple[str, ...]
        key = (tuple(self.exelist), self.version, code, textra_args, mode)  # type: coredata.CompilerCheckCacheKey

        # Check if not cached, and generate, otherwise get from the cache
        if key in cdata.compiler_check_cache:
            p = cdata.compiler_check_cache[key]  # type: CompileResult
            p.cached = True
            mlog.debug('Using cached compile:')
            mlog.debug('Cached command line: ', ' '.join(p.command), '\n')
            mlog.debug('Code:\n', code)
            mlog.debug('Cached compiler stdout:\n', p.stdout)
            mlog.debug('Cached compiler stderr:\n', p.stderr)
            yield p
        else:
            with self.compile(code, extra_args=extra_args, mode=mode, want_output=False, temp_dir=temp_dir) as p:
                cdata.compiler_check_cache[key] = p
                yield p

    def get_colorout_args(self, colortype: str) -> T.List[str]:
        # TODO: colortype can probably be an emum
        return []

    # Some compilers (msvc) write debug info to a separate file.
    # These args specify where it should be written.
    def get_compile_debugfile_args(self, rel_obj: str, pch: bool = False) -> T.List[str]:
        return []

    def get_link_debugfile_name(self, targetfile: str) -> str:
        return self.linker.get_debugfile_name(targetfile)

    def get_link_debugfile_args(self, targetfile: str) -> T.List[str]:
        return self.linker.get_debugfile_args(targetfile)

    def get_std_shared_lib_link_args(self) -> T.List[str]:
        return self.linker.get_std_shared_lib_args()

    def get_std_shared_module_link_args(self, options: 'OptionDictType') -> T.List[str]:
        return self.linker.get_std_shared_module_args(options)

    def get_link_whole_for(self, args: T.List[str]) -> T.List[str]:
        return self.linker.get_link_whole_for(args)

    def get_allow_undefined_link_args(self) -> T.List[str]:
        return self.linker.get_allow_undefined_args()

    def no_undefined_link_args(self) -> T.List[str]:
        return self.linker.no_undefined_args()

    def get_instruction_set_args(self, instruction_set: str) -> T.Optional[T.List[str]]:
        """Compiler arguments needed to enable the given instruction set.

        Return type ay be an empty list meaning nothing needed or None
        meaning the given set is not supported.
        """
        return None

    def build_rpath_args(self, env: 'Environment', build_dir: str, from_dir: str,
                         rpath_paths: str, build_rpath: str,
                         install_rpath: str) -> T.Tuple[T.List[str], T.Set[bytes]]:
        return self.linker.build_rpath_args(
            env, build_dir, from_dir, rpath_paths, build_rpath, install_rpath)

    def thread_flags(self, env: 'Environment') -> T.List[str]:
        return []

    def thread_link_flags(self, env: 'Environment') -> T.List[str]:
        return self.linker.thread_flags(env)

    def openmp_flags(self) -> T.List[str]:
        raise EnvironmentException('Language %s does not support OpenMP flags.' % self.get_display_language())

    def openmp_link_flags(self) -> T.List[str]:
        return self.openmp_flags()

    def language_stdlib_only_link_flags(self) -> T.List[str]:
        return []

    def gnu_symbol_visibility_args(self, vistype: str) -> T.List[str]:
        return []

    def get_gui_app_args(self, value: bool) -> T.List[str]:
        return []

    def get_win_subsystem_args(self, value: str) -> T.List[str]:
        # This returns an empty array rather than throws to simplify the code.
        # Otherwise we would have to check whenever calling this function whether
        # the target is for Windows. There are also many cases where this is
        # a meaningless choice, such as with Jave or C#.
        return []

    def has_func_attribute(self, name: str, env: 'Environment') -> T.Tuple[bool, bool]:
        raise EnvironmentException(
            'Language {} does not support function attributes.'.format(self.get_display_language()))

    def get_pic_args(self) -> T.List[str]:
        m = 'Language {} does not support position-independent code'
        raise EnvironmentException(m.format(self.get_display_language()))

    def get_pie_args(self) -> T.List[str]:
        m = 'Language {} does not support position-independent executable'
        raise EnvironmentException(m.format(self.get_display_language()))

    def get_pie_link_args(self) -> T.List[str]:
        return self.linker.get_pie_args()

    def get_argument_syntax(self) -> str:
        """Returns the argument family type.

        Compilers fall into families if they try to emulate the command line
        interface of another compiler. For example, clang is in the GCC family
        since it accepts most of the same arguments as GCC. ICL (ICC on
        windows) is in the MSVC family since it accepts most of the same
        arguments as MSVC.
        """
        return 'other'

    def get_profile_generate_args(self) -> T.List[str]:
        raise EnvironmentException(
            '%s does not support get_profile_generate_args ' % self.get_id())

    def get_profile_use_args(self) -> T.List[str]:
        raise EnvironmentException(
            '%s does not support get_profile_use_args ' % self.get_id())

    def remove_linkerlike_args(self, args: T.List[str]) -> T.List[str]:
        rm_exact = ('-headerpad_max_install_names',)
        rm_prefixes = ('-Wl,', '-L',)
        rm_next = ('-L', '-framework',)
        ret = []  # T.List[str]
        iargs = iter(args)
        for arg in iargs:
            # Remove this argument
            if arg in rm_exact:
                continue
            # If the argument starts with this, but is not *exactly* this
            # f.ex., '-L' should match ['-Lfoo'] but not ['-L', 'foo']
            if arg.startswith(rm_prefixes) and arg not in rm_prefixes:
                continue
            # Ignore this argument and the one after it
            if arg in rm_next:
                next(iargs)
                continue
            ret.append(arg)
        return ret

    def get_lto_compile_args(self) -> T.List[str]:
        return []

    def get_lto_link_args(self) -> T.List[str]:
        return self.linker.get_lto_args()

    def sanitizer_compile_args(self, value: str) -> T.List[str]:
        return []

    def sanitizer_link_args(self, value: str) -> T.List[str]:
        return self.linker.sanitizer_args(value)

    def get_asneeded_args(self) -> T.List[str]:
        return self.linker.get_asneeded_args()

    def headerpad_args(self) -> T.List[str]:
        return self.linker.headerpad_args()

    def bitcode_args(self) -> T.List[str]:
        return self.linker.bitcode_args()

    def get_buildtype_args(self, buildtype: str) -> T.List[str]:
        raise EnvironmentException('{} does not implement get_buildtype_args'.format(self.id))

    def get_buildtype_linker_args(self, buildtype: str) -> T.List[str]:
        return self.linker.get_buildtype_args(buildtype)

    def get_soname_args(self, env: 'Environment', prefix: str, shlib_name: str,
                        suffix: str, soversion: str,
                        darwin_versions: T.Tuple[str, str],
                        is_shared_module: bool) -> T.List[str]:
        return self.linker.get_soname_args(
            env, prefix, shlib_name, suffix, soversion,
            darwin_versions, is_shared_module)

    def get_target_link_args(self, target: 'BuildTarget') -> T.List[str]:
        return target.link_args

    def get_dependency_compile_args(self, dep: 'Dependency') -> T.List[str]:
        return dep.get_compile_args()

    def get_dependency_link_args(self, dep: 'Dependency') -> T.List[str]:
        return dep.get_link_args()

    @classmethod
    def use_linker_args(cls, linker: str) -> T.List[str]:
        """Get a list of arguments to pass to the compiler to set the linker.
        """
        return []

    def get_coverage_args(self) -> T.List[str]:
        return []

    def get_coverage_link_args(self) -> T.List[str]:
        return self.linker.get_coverage_args()

    def get_disable_assert_args(self) -> T.List[str]:
        return []

    def get_crt_compile_args(self, crt_val: str, buildtype: str) -> T.List[str]:
        raise EnvironmentError('This compiler does not support Windows CRT selection')

    def get_crt_link_args(self, crt_val: str, buildtype: str) -> T.List[str]:
        raise EnvironmentError('This compiler does not support Windows CRT selection')

    def get_compile_only_args(self) -> T.List[str]:
        return []

    def get_preprocess_only_args(self) -> T.List[str]:
        raise EnvironmentError('This compiler does not have a preprocessor')

    def get_default_include_dirs(self) -> T.List[str]:
        return []

    def get_largefile_args(self) -> T.List[str]:
        '''Enable transparent large-file-support for 32-bit UNIX systems'''
        if not (self.get_argument_syntax() == 'msvc' or self.info.is_darwin()):
            # Enable large-file support unconditionally on all platforms other
            # than macOS and MSVC. macOS is now 64-bit-only so it doesn't
            # need anything special, and MSVC doesn't have automatic LFS.
            # You must use the 64-bit counterparts explicitly.
            # glibc, musl, and uclibc, and all BSD libcs support this. On Android,
            # support for transparent LFS is available depending on the version of
            # Bionic: https://github.com/android/platform_bionic#32-bit-abi-bugs
            # https://code.google.com/p/android/issues/detail?id=64613
            #
            # If this breaks your code, fix it! It's been 20+ years!
            return ['-D_FILE_OFFSET_BITS=64']
            # We don't enable -D_LARGEFILE64_SOURCE since that enables
            # transitionary features and must be enabled by programs that use
            # those features explicitly.
        return []

    def get_library_dirs(self, env: 'Environment',
                         elf_class: T.Optional[int] = None) -> T.List[str]:
        return []

    def find_framework_paths(self, env: 'Environment') -> T.List[str]:
        raise EnvironmentException('{} does not support find_framework_paths'.format(self.id))

    def attribute_check_func(self, name: str) -> str:
        raise EnvironmentException('{} does not support attribute checks'.format(self.id))

    def get_pch_suffix(self) -> str:
        raise EnvironmentException('{} does not support pre compiled headers'.format(self.id))

    def get_pch_name(self, name: str) -> str:
        raise EnvironmentException('{} does not support pre compiled headers'.format(self.id))

    def get_pch_use_args(self, pch_dir: str, header: str) -> T.List[str]:
        raise EnvironmentException('{} does not support pre compiled headers'.format(self.id))

    def get_has_func_attribute_extra_args(self, name: str) -> T.List[str]:
        raise EnvironmentException('{} does not support function attributes'.format(self.id))

    def name_string(self) -> str:
        return ' '.join(self.exelist)

    @abc.abstractmethod
    def sanity_check(self, work_dir: str, environment: 'Environment') -> None:
        """Check that this compiler actually works.

        This should provide a simple compile/link test. Somthing as simple as:
        ```python
        main(): return 0
        ```
        is good enough here.
        """

    def split_shlib_to_parts(self, fname: str) -> T.Tuple[T.Optional[str], str]:
        return None, fname

    def get_dependency_gen_args(self, outtarget: str, outfile: str) -> T.List[str]:
        return []

    def get_std_exe_link_args(self) -> T.List[str]:
        # TODO: is this a linker property?
        return []

    def get_include_args(self, path: str, is_system: bool) -> T.List[str]:
        return []

    def depfile_for_object(self, objfile: str) -> str:
        return objfile + '.' + self.get_depfile_suffix()

    def get_depfile_suffix(self) -> str:
        raise EnvironmentError('{} does not implement get_depfile_suffix'.format(self.id))

    def get_no_stdinc_args(self) -> T.List[str]:
        """Arguments to turn off default inclusion of standard libraries."""
        return []

    def get_warn_args(self, level: str) -> T.List[str]:
        return []

    def get_werror_args(self) -> T.List[str]:
        return []

    @abc.abstractmethod
    def get_optimization_args(self, optimization_level: str) -> T.List[str]:
        pass

    def get_module_incdir_args(self) -> T.Tuple[str, ...]:
        raise EnvironmentError('{} does not implement get_module_incdir_args'.format(self.id))

    def get_module_outdir_args(self, path: str) -> T.List[str]:
        raise EnvironmentError('{} does not implement get_module_outdir_args'.format(self.id))

    def module_name_to_filename(self, module_name: str) -> str:
        raise EnvironmentError('{} does not implement module_name_to_filename'.format(self.id))

    def get_compiler_check_args(self, mode: CompileCheckMode) -> T.List[str]:
        """Arguments to pass the compiler and/or linker for checks.

        The default implementation turns off optimizations. mode should be
        one of:

        Examples of things that go here:
          - extra arguments for error checking
        """
        return self.get_no_optimization_args()

    def get_no_optimization_args(self) -> T.List[str]:
        """Arguments to the compiler to turn off all optimizations."""
        return []

    def build_wrapper_args(self, env: 'Environment',
                           extra_args: T.Union[None, CompilerArgs, T.List[str]],
                           dependencies: T.Optional[T.List['Dependency']],
                           mode: CompileCheckMode = CompileCheckMode.COMPILE) -> CompilerArgs:
        """Arguments to pass the build_wrapper helper.

        This generally needs to be set on a per-language baises. It provides
        a hook for languages to handle dependencies and extra args. The base
        implementation handles the most common cases, namely adding the
        check_arguments, unwrapping dependencies, and appending extra args.
        """
        if callable(extra_args):
            extra_args = extra_args(mode)
        if extra_args is None:
            extra_args = []
        if dependencies is None:
            dependencies = []

        # Collect compiler arguments
        args = self.compiler_args(self.get_compiler_check_args(mode))
        for d in dependencies:
            # Add compile flags needed by dependencies
            args += d.get_compile_args()
            if mode is CompileCheckMode.LINK:
                # Add link flags needed to find dependencies
                args += d.get_link_args()

        if mode is CompileCheckMode.COMPILE:
            # Add DFLAGS from the env
            args += env.coredata.get_external_args(self.for_machine, self.language)
        elif mode is CompileCheckMode.LINK:
            # Add LDFLAGS from the env
            args += env.coredata.get_external_link_args(self.for_machine, self.language)
        # extra_args must override all other arguments, so we add them last
        args += extra_args
        return args

    @contextlib.contextmanager
    def _build_wrapper(self, code: str, env: 'Environment',
                       extra_args: T.Union[None, CompilerArgs, T.List[str]] = None,
                       dependencies: T.Optional[T.List['Dependency']] = None,
                       mode: str = 'compile', want_output: bool = False,
                       disable_cache: bool = False,
                       temp_dir: str = None) -> T.Iterator[T.Optional[CompileResult]]:
        """Helper for getting a cacched value when possible.

        This method isn't meant to be called externally, it's mean to be
        wrapped by other methods like compiles() and links().
        """
        args = self.build_wrapper_args(env, extra_args, dependencies, CompileCheckMode(mode))
        if disable_cache or want_output:
            with self.compile(code, extra_args=args, mode=mode, want_output=want_output, temp_dir=env.scratch_dir) as r:
                yield r
        else:
            with self.cached_compile(code, env.coredata, extra_args=args, mode=mode, temp_dir=env.scratch_dir) as r:
                yield r

    def compiles(self, code: str, env: 'Environment', *,
                 extra_args: T.Union[None, T.List[str], CompilerArgs] = None,
                 dependencies: T.Optional[T.List['Dependency']] = None,
                 mode: str = 'compile',
                 disable_cache: bool = False) -> T.Tuple[bool, bool]:
        with self._build_wrapper(code, env, extra_args, dependencies, mode, disable_cache=disable_cache) as p:
            return p.returncode == 0, p.cached


    def links(self, code: str, env: 'Environment', *,
              extra_args: T.Union[None, T.List[str], CompilerArgs] = None,
              dependencies: T.Optional[T.List['Dependency']] = None,
              mode: str = 'compile',
              disable_cache: bool = False) -> T.Tuple[bool, bool]:
        return self.compiles(code, env, extra_args=extra_args,
                             dependencies=dependencies, mode='link', disable_cache=disable_cache)

    def get_feature_args(self, kwargs: T.Dict[str, T.Any], build_to_src: str) -> T.List[str]:
        """Used by D for extra language features."""
        # TODO: using a TypeDict here would improve this
        raise EnvironmentError('{} does not implement get_feature_args'.format(self.id))


def get_args_from_envvars(lang: str,
                          for_machine: MachineChoice,
                          is_cross: bool,
                          use_linker_args: bool) -> T.Tuple[T.List[str], T.List[str]]:
    """
    Returns a tuple of (compile_flags, link_flags) for the specified language
    from the inherited environment
    """
    if lang not in cflags_mapping:
        return [], []

    compile_flags = []  # type: T.List[str]
    link_flags = []     # type: T.List[str]

    env_compile_flags = get_env_var(for_machine, is_cross, cflags_mapping[lang])
    if env_compile_flags is not None:
        compile_flags += split_args(env_compile_flags)

    # Link flags (same for all languages)
    if lang in languages_using_ldflags:
        link_flags += LinkerEnvVarsMixin.get_args_from_envvars(for_machine, is_cross)
    if use_linker_args:
        # When the compiler is used as a wrapper around the linker (such as
        # with GCC and Clang), the compile flags can be needed while linking
        # too. This is also what Autotools does. However, we don't want to do
        # this when the linker is stand-alone such as with MSVC C/C++, etc.
        link_flags = compile_flags + link_flags

    # Pre-processor flags for certain languages
    if lang in languages_using_cppflags:
        env_preproc_flags = get_env_var(for_machine, is_cross, 'CPPFLAGS')
        if env_preproc_flags is not None:
            compile_flags += split_args(env_preproc_flags)

    return compile_flags, link_flags


def get_global_options(lang: str,
                       comp: T.Type[Compiler],
                       for_machine: MachineChoice,
                       is_cross: bool) -> 'OptionDictType':
    """Retreive options that apply to all compilers for a given language."""
    description = 'Extra arguments passed to the {}'.format(lang)
    opts = {
        'args': coredata.UserArrayOption(
            description + ' compiler',
            [], split_args=True, user_input=True, allow_dups=True),
        'link_args': coredata.UserArrayOption(
            description + ' linker',
            [], split_args=True, user_input=True, allow_dups=True),
    }  # type: OptionDictType

    # Get from env vars.
    compile_args, link_args = get_args_from_envvars(
        lang,
        for_machine,
        is_cross,
        comp.INVOKES_LINKER)

    for k, o in opts.items():
        if k == 'args':
            o.set_value(compile_args)
        elif k == 'link_args':
            o.set_value(link_args)

    return opts
