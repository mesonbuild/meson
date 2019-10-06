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

import contextlib, enum, os.path, re, tempfile
import typing
from typing import Optional, Tuple, List

from ..linkers import StaticLinker, GnuLikeDynamicLinkerMixin, SolarisDynamicLinker
from .. import coredata
from .. import mlog
from .. import mesonlib
from ..mesonlib import (
    EnvironmentException, MachineChoice, MesonException, OrderedSet,
    Popen_safe, split_args
)
from ..envconfig import (
    Properties,
)

if typing.TYPE_CHECKING:
    from ..coredata import OptionDictType
    from ..environment import Environment
    from ..linkers import DynamicLinker  # noqa: F401

"""This file contains the data files of all compilers Meson knows
about. To support a new compiler, add its information below.
Also add corresponding autodetection code in environment.py."""

header_suffixes = ('h', 'hh', 'hpp', 'hxx', 'H', 'ipp', 'moc', 'vapi', 'di')
obj_suffixes = ('o', 'obj', 'res')
lib_suffixes = ('a', 'lib', 'dll', 'dll.a', 'dylib', 'so')
# Mapping of language to suffixes of files that should always be in that language
# This means we can't include .h headers here since they could be C, C++, ObjC, etc.
lang_suffixes = {
    'c': ('c',),
    'cpp': ('cpp', 'cc', 'cxx', 'c++', 'hh', 'hpp', 'ipp', 'hxx'),
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
}
all_languages = lang_suffixes.keys()
cpp_suffixes = lang_suffixes['cpp'] + ('h',)
c_suffixes = lang_suffixes['c'] + ('h',)
# List of languages that by default consume and output libraries following the
# C ABI; these can generally be used interchangebly
clib_langs = ('objcpp', 'cpp', 'objc', 'c', 'fortran',)
# List of languages that can be linked with C code directly by the linker
# used in build.py:process_compilers() and build.py:get_dynamic_linker()
clink_langs = ('d', 'cuda') + clib_langs
clink_suffixes = ()
for _l in clink_langs + ('vala',):
    clink_suffixes += lang_suffixes[_l]
clink_suffixes += ('h', 'll', 's')

# Languages that should use LDFLAGS arguments when linking.
languages_using_ldflags = ('objcpp', 'cpp', 'objc', 'c', 'fortran', 'd', 'cuda')
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
                  'rust': 'RUSTFLAGS'}

# execinfo is a compiler lib on BSD
unixy_compiler_internal_libs = ('m', 'c', 'pthread', 'dl', 'rt', 'execinfo')

# All these are only for C-linkable languages; see `clink_langs` above.

def sort_clink(lang):
    '''
    Sorting function to sort the list of languages according to
    reversed(compilers.clink_langs) and append the unknown langs in the end.
    The purpose is to prefer C over C++ for files that can be compiled by
    both such as assembly, C, etc. Also applies to ObjC, ObjC++, etc.
    '''
    if lang not in clink_langs:
        return 1
    return -clink_langs.index(lang)

def is_header(fname):
    if hasattr(fname, 'fname'):
        fname = fname.fname
    suffix = fname.split('.')[-1]
    return suffix in header_suffixes

def is_source(fname):
    if hasattr(fname, 'fname'):
        fname = fname.fname
    suffix = fname.split('.')[-1].lower()
    return suffix in clink_suffixes

def is_assembly(fname):
    if hasattr(fname, 'fname'):
        fname = fname.fname
    return fname.split('.')[-1].lower() == 's'

def is_llvm_ir(fname):
    if hasattr(fname, 'fname'):
        fname = fname.fname
    return fname.split('.')[-1] == 'll'

def is_object(fname):
    if hasattr(fname, 'fname'):
        fname = fname.fname
    suffix = fname.split('.')[-1]
    return suffix in obj_suffixes

def is_library(fname):
    if hasattr(fname, 'fname'):
        fname = fname.fname

    if soregex.match(fname):
        return True

    suffix = fname.split('.')[-1]
    return suffix in lib_suffixes

cuda_buildtype_args = {'plain': [],
                       'debug': [],
                       'debugoptimized': [],
                       'release': [],
                       'minsize': [],
                       }
java_buildtype_args = {'plain': [],
                       'debug': ['-g'],
                       'debugoptimized': ['-g'],
                       'release': [],
                       'minsize': [],
                       'custom': [],
                       }

rust_buildtype_args = {'plain': [],
                       'debug': [],
                       'debugoptimized': [],
                       'release': [],
                       'minsize': [],
                       'custom': [],
                       }

d_gdc_buildtype_args = {'plain': [],
                        'debug': [],
                        'debugoptimized': ['-finline-functions'],
                        'release': ['-frelease', '-finline-functions'],
                        'minsize': [],
                        'custom': [],
                        }

d_ldc_buildtype_args = {'plain': [],
                        'debug': [],
                        'debugoptimized': ['-enable-inlining', '-Hkeep-all-bodies'],
                        'release': ['-release', '-enable-inlining', '-Hkeep-all-bodies'],
                        'minsize': [],
                        'custom': [],
                        }

d_dmd_buildtype_args = {'plain': [],
                        'debug': [],
                        'debugoptimized': ['-inline'],
                        'release': ['-release', '-inline'],
                        'minsize': [],
                        'custom': [],
                        }

mono_buildtype_args = {'plain': [],
                       'debug': [],
                       'debugoptimized': ['-optimize+'],
                       'release': ['-optimize+'],
                       'minsize': [],
                       'custom': [],
                       }

swift_buildtype_args = {'plain': [],
                        'debug': [],
                        'debugoptimized': [],
                        'release': [],
                        'minsize': [],
                        'custom': [],
                        }

gnu_winlibs = ['-lkernel32', '-luser32', '-lgdi32', '-lwinspool', '-lshell32',
               '-lole32', '-loleaut32', '-luuid', '-lcomdlg32', '-ladvapi32']

msvc_winlibs = ['kernel32.lib', 'user32.lib', 'gdi32.lib',
                'winspool.lib', 'shell32.lib', 'ole32.lib', 'oleaut32.lib',
                'uuid.lib', 'comdlg32.lib', 'advapi32.lib']

clike_optimization_args = {'0': [],
                           'g': [],
                           '1': ['-O1'],
                           '2': ['-O2'],
                           '3': ['-O3'],
                           's': ['-Os'],
                           }

cuda_optimization_args = {'0': [],
                          'g': ['-O0'],
                          '1': ['-O1'],
                          '2': ['-O2'],
                          '3': ['-O3'],
                          's': ['-O3']
                          }

cuda_debug_args = {False: [],
                   True: ['-g']}

clike_debug_args = {False: [],
                    True: ['-g']}

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
                                                    ['none', 'md', 'mdd', 'mt', 'mtd', 'from_buildtype'],
                                                    'from_buildtype'),
                }

def option_enabled(boptions, options, option):
    try:
        if option not in boptions:
            return False
        return options[option].value
    except KeyError:
        return False

def get_base_compile_args(options, compiler):
    args = []
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
            args += ['-DNDEBUG']
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

def get_base_link_args(options, linker, is_shared_module):
    args = []
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

    # Apple's ld (the only one that supports bitcode) does not like any
    # -undefined arguments at all, so don't pass these when using bitcode
    if not bitcode:
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
    def __init__(self, compiled, returncode=999, stdout='UNDEFINED', stderr='UNDEFINED'):
        self.compiled = compiled
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

class CompilerArgs(list):
    '''
    Class derived from list() that manages a list of compiler arguments. Should
    be used while constructing compiler arguments from various sources. Can be
    operated with ordinary lists, so this does not need to be used everywhere.

    All arguments must be inserted and stored in GCC-style (-lfoo, -Idir, etc)
    and can converted to the native type of each compiler by using the
    .to_native() method to which you must pass an instance of the compiler or
    the compiler class.

    New arguments added to this class (either with .append(), .extend(), or +=)
    are added in a way that ensures that they override previous arguments.
    For example:

    >>> a = ['-Lfoo', '-lbar']
    >>> a += ['-Lpho', '-lbaz']
    >>> print(a)
    ['-Lpho', '-Lfoo', '-lbar', '-lbaz']

    Arguments will also be de-duped if they can be de-duped safely.

    Note that because of all this, this class is not commutative and does not
    preserve the order of arguments if it is safe to not. For example:
    >>> ['-Ifoo', '-Ibar'] + ['-Ifez', '-Ibaz', '-Werror']
    ['-Ifez', '-Ibaz', '-Ifoo', '-Ibar', '-Werror']
    >>> ['-Ifez', '-Ibaz', '-Werror'] + ['-Ifoo', '-Ibar']
    ['-Ifoo', '-Ibar', '-Ifez', '-Ibaz', '-Werror']

    '''
    # NOTE: currently this class is only for C-like compilers, but it can be
    # extended to other languages easily. Just move the following to the
    # compiler class and initialize when self.compiler is set.

    # Arg prefixes that override by prepending instead of appending
    prepend_prefixes = ('-I', '-L')
    # Arg prefixes and args that must be de-duped by returning 2
    dedup2_prefixes = ('-I', '-isystem', '-L', '-D', '-U')
    dedup2_suffixes = ()
    dedup2_args = ()
    # Arg prefixes and args that must be de-duped by returning 1
    #
    # NOTE: not thorough. A list of potential corner cases can be found in
    # https://github.com/mesonbuild/meson/pull/4593#pullrequestreview-182016038
    dedup1_prefixes = ('-l', '-Wl,-l', '-Wl,--export-dynamic')
    dedup1_suffixes = ('.lib', '.dll', '.so', '.dylib', '.a')
    # Match a .so of the form path/to/libfoo.so.0.1.0
    # Only UNIX shared libraries require this. Others have a fixed extension.
    dedup1_regex = re.compile(r'([\/\\]|\A)lib.*\.so(\.[0-9]+)?(\.[0-9]+)?(\.[0-9]+)?$')
    dedup1_args = ('-c', '-S', '-E', '-pipe', '-pthread')
    # In generate_link() we add external libs without de-dup, but we must
    # *always* de-dup these because they're special arguments to the linker
    always_dedup_args = tuple('-l' + lib for lib in unixy_compiler_internal_libs)
    compiler = None

    def _check_args(self, args):
        cargs = []
        if len(args) > 2:
            raise TypeError("CompilerArgs() only accepts at most 2 arguments: "
                            "The compiler, and optionally an initial list")
        elif not args:
            return cargs
        elif len(args) == 1:
            if isinstance(args[0], (Compiler, StaticLinker)):
                self.compiler = args[0]
            else:
                raise TypeError("you must pass a Compiler instance as one of "
                                "the arguments")
        elif len(args) == 2:
            if isinstance(args[0], (Compiler, StaticLinker)):
                self.compiler = args[0]
                cargs = args[1]
            elif isinstance(args[1], (Compiler, StaticLinker)):
                cargs = args[0]
                self.compiler = args[1]
            else:
                raise TypeError("you must pass a Compiler instance as one of "
                                "the two arguments")
        else:
            raise AssertionError('Not reached')
        return cargs

    def __init__(self, *args):
        super().__init__(self._check_args(args))

    @classmethod
    def _can_dedup(cls, arg):
        '''
        Returns whether the argument can be safely de-duped. This is dependent
        on three things:

        a) Whether an argument can be 'overridden' by a later argument.  For
           example, -DFOO defines FOO and -UFOO undefines FOO. In this case, we
           can safely remove the previous occurrence and add a new one. The same
           is true for include paths and library paths with -I and -L. For
           these we return `2`. See `dedup2_prefixes` and `dedup2_args`.
        b) Arguments that once specified cannot be undone, such as `-c` or
           `-pipe`. New instances of these can be completely skipped. For these
           we return `1`. See `dedup1_prefixes` and `dedup1_args`.
        c) Whether it matters where or how many times on the command-line
           a particular argument is present. This can matter for symbol
           resolution in static or shared libraries, so we cannot de-dup or
           reorder them. For these we return `0`. This is the default.

        In addition to these, we handle library arguments specially.
        With GNU ld, we surround library arguments with -Wl,--start/end-group
        to recursively search for symbols in the libraries. This is not needed
        with other linkers.
        '''
        # A standalone argument must never be deduplicated because it is
        # defined by what comes _after_ it. Thus dedupping this:
        # -D FOO -D BAR
        # would yield either
        # -D FOO BAR
        # or
        # FOO -D BAR
        # both of which are invalid.
        if arg in cls.dedup2_prefixes:
            return 0
        if arg in cls.dedup2_args or \
           arg.startswith(cls.dedup2_prefixes) or \
           arg.endswith(cls.dedup2_suffixes):
            return 2
        if arg in cls.dedup1_args or \
           arg.startswith(cls.dedup1_prefixes) or \
           arg.endswith(cls.dedup1_suffixes) or \
           re.search(cls.dedup1_regex, arg):
            return 1
        return 0

    @classmethod
    def _should_prepend(cls, arg):
        if arg.startswith(cls.prepend_prefixes):
            return True
        return False

    def to_native(self, copy: bool = False) -> typing.List[str]:
        # Check if we need to add --start/end-group for circular dependencies
        # between static libraries, and for recursively searching for symbols
        # needed by static libraries that are provided by object files or
        # shared libraries.
        if copy:
            new = self.copy()
        else:
            new = self
        # This covers all ld.bfd, ld.gold, ld.gold, and xild on Linux, which
        # all act like (or are) gnu ld
        # TODO: this could probably be added to the DynamicLinker instead
        if (hasattr(self.compiler, 'linker') and
                self.compiler.linker is not None and
                isinstance(self.compiler.linker, (GnuLikeDynamicLinkerMixin, SolarisDynamicLinker))):
            group_start = -1
            group_end = -1
            for i, each in enumerate(new):
                if not each.startswith(('-Wl,-l', '-l')) and not each.endswith('.a') and \
                   not soregex.match(each):
                    continue
                group_end = i
                if group_start < 0:
                    # First occurrence of a library
                    group_start = i
            if group_start >= 0:
                # Last occurrence of a library
                new.insert(group_end + 1, '-Wl,--end-group')
                new.insert(group_start, '-Wl,--start-group')
        # Remove system/default include paths added with -isystem
        if hasattr(self.compiler, 'get_default_include_dirs'):
            default_dirs = self.compiler.get_default_include_dirs()
            bad_idx_list = []
            for i, each in enumerate(new):
                # Remove the -isystem and the path if the path is a dafault path
                if (each == '-isystem' and
                        i < (len(new) - 1) and
                        new[i + 1] in default_dirs):
                    bad_idx_list += [i, i + 1]
                elif each.startswith('-isystem=') and each[9:] in default_dirs:
                    bad_idx_list += [i]
                elif each.startswith('-isystem') and each[8:] in default_dirs:
                    bad_idx_list += [i]
            for i in reversed(bad_idx_list):
                new.pop(i)
        return self.compiler.unix_args_to_native(new)

    def append_direct(self, arg):
        '''
        Append the specified argument without any reordering or de-dup except
        for absolute paths to libraries, etc, which can always be de-duped
        safely.
        '''
        if os.path.isabs(arg):
            self.append(arg)
        else:
            super().append(arg)

    def extend_direct(self, iterable):
        '''
        Extend using the elements in the specified iterable without any
        reordering or de-dup except for absolute paths where the order of
        include search directories is not relevant
        '''
        for elem in iterable:
            self.append_direct(elem)

    def extend_preserving_lflags(self, iterable):
        normal_flags = []
        lflags = []
        for i in iterable:
            if i not in self.always_dedup_args and (i.startswith('-l') or i.startswith('-L')):
                lflags.append(i)
            else:
                normal_flags.append(i)
        self.extend(normal_flags)
        self.extend_direct(lflags)

    def __add__(self, args):
        new = CompilerArgs(self, self.compiler)
        new += args
        return new

    def __iadd__(self, args):
        '''
        Add two CompilerArgs while taking into account overriding of arguments
        and while preserving the order of arguments as much as possible
        '''
        pre = []
        post = []
        if not isinstance(args, list):
            raise TypeError('can only concatenate list (not "{}") to list'.format(args))
        for arg in args:
            # If the argument can be de-duped, do it either by removing the
            # previous occurrence of it and adding a new one, or not adding the
            # new occurrence.
            dedup = self._can_dedup(arg)
            if dedup == 1:
                # Argument already exists and adding a new instance is useless
                if arg in self or arg in pre or arg in post:
                    continue
            if dedup == 2:
                # Remove all previous occurrences of the arg and add it anew
                if arg in self:
                    self.remove(arg)
                if arg in pre:
                    pre.remove(arg)
                if arg in post:
                    post.remove(arg)
            if self._should_prepend(arg):
                pre.append(arg)
            else:
                post.append(arg)
        # Insert at the beginning
        self[:0] = pre
        # Append to the end
        super().__iadd__(post)
        return self

    def __radd__(self, args):
        new = CompilerArgs(args, self.compiler)
        new += self
        return new

    def __mul__(self, args):
        raise TypeError("can't multiply compiler arguments")

    def __imul__(self, args):
        raise TypeError("can't multiply compiler arguments")

    def __rmul__(self, args):
        raise TypeError("can't multiply compiler arguments")

    def append(self, arg):
        self.__iadd__([arg])

    def extend(self, args):
        self.__iadd__(args)

class Compiler:
    # Libraries to ignore in find_library() since they are provided by the
    # compiler or the C library. Currently only used for MSVC.
    ignore_libs = ()
    # Libraries that are internal compiler implementations, and must not be
    # manually searched.
    internal_libs = ()

    LINKER_PREFIX = None  # type: typing.Union[None, str, typing.List[str]]

    def __init__(self, exelist, version, for_machine: MachineChoice,
                 linker: typing.Optional['DynamicLinker'] = None, **kwargs):
        if isinstance(exelist, str):
            self.exelist = [exelist]
        elif isinstance(exelist, list):
            self.exelist = exelist
        else:
            raise TypeError('Unknown argument to Compiler')
        # In case it's been overridden by a child class already
        if not hasattr(self, 'file_suffixes'):
            self.file_suffixes = lang_suffixes[self.language]
        if not hasattr(self, 'can_compile_suffixes'):
            self.can_compile_suffixes = set(self.file_suffixes)
        self.default_suffix = self.file_suffixes[0]
        self.version = version
        if 'full_version' in kwargs:
            self.full_version = kwargs['full_version']
        else:
            self.full_version = None
        self.for_machine = for_machine
        self.base_options = []
        self.linker = linker

    def __repr__(self):
        repr_str = "<{0}: v{1} `{2}`>"
        return repr_str.format(self.__class__.__name__, self.version,
                               ' '.join(self.exelist))

    def can_compile(self, src) -> bool:
        if hasattr(src, 'fname'):
            src = src.fname
        suffix = os.path.splitext(src)[1].lower()
        if suffix and suffix[1:] in self.can_compile_suffixes:
            return True
        return False

    def get_id(self) -> str:
        return self.id

    def get_version_string(self) -> str:
        details = [self.id, self.version]
        if self.full_version:
            details += ['"%s"' % (self.full_version)]
        return '(%s)' % (' '.join(details))

    def get_language(self) -> str:
        return self.language

    def get_display_language(self) -> str:
        return self.language.capitalize()

    def get_default_suffix(self) -> str:
        return self.default_suffix

    def get_define(self, dname, prefix, env, extra_args, dependencies) -> Tuple[str, bool]:
        raise EnvironmentException('%s does not support get_define ' % self.get_id())

    def compute_int(self, expression, low, high, guess, prefix, env, extra_args, dependencies) -> int:
        raise EnvironmentException('%s does not support compute_int ' % self.get_id())

    def compute_parameters_with_absolute_paths(self, parameter_list, build_dir):
        raise EnvironmentException('%s does not support compute_parameters_with_absolute_paths ' % self.get_id())

    def has_members(self, typename, membernames, prefix, env, *, extra_args=None, dependencies=None) -> Tuple[bool, bool]:
        raise EnvironmentException('%s does not support has_member(s) ' % self.get_id())

    def has_type(self, typename, prefix, env, extra_args, *, dependencies=None) -> Tuple[bool, bool]:
        raise EnvironmentException('%s does not support has_type ' % self.get_id())

    def symbols_have_underscore_prefix(self, env) -> bool:
        raise EnvironmentException('%s does not support symbols_have_underscore_prefix ' % self.get_id())

    def get_exelist(self):
        return self.exelist[:]

    def get_linker_exelist(self) -> typing.List[str]:
        return self.linker.get_exelist()

    def get_linker_output_args(self, outputname: str) -> typing.List[str]:
        return self.linker.get_output_args(outputname)

    def get_builtin_define(self, *args, **kwargs):
        raise EnvironmentException('%s does not support get_builtin_define.' % self.id)

    def has_builtin_define(self, *args, **kwargs):
        raise EnvironmentException('%s does not support has_builtin_define.' % self.id)

    def get_always_args(self):
        return []

    def can_linker_accept_rsp(self) -> bool:
        """
        Determines whether the linker can accept arguments using the @rsp syntax.
        """
        return self.linker.get_accepts_rsp()

    def get_linker_always_args(self):
        return self.linker.get_always_args()

    def get_linker_lib_prefix(self):
        return self.linker.get_lib_prefix()

    def gen_import_library_args(self, implibname):
        """
        Used only on Windows for libraries that need an import library.
        This currently means C, C++, Fortran.
        """
        return []

    def use_preproc_flags(self) -> bool:
        """
        Whether the compiler (or processes it spawns) cares about CPPFLAGS
        """
        return self.get_language() in {'c', 'cpp', 'objc', 'objcpp'}

    def use_ldflags(self) -> bool:
        """
        Whether the compiler (or processes it spawns) cares about LDFLAGS
        """
        return self.get_language() in languages_using_ldflags

    def get_linker_args_from_envvars(self) -> typing.List[str]:
        return self.linker.get_args_from_envvars()

    def get_args_from_envvars(self) -> typing.Tuple[typing.List[str], typing.List[str]]:
        """
        Returns a tuple of (compile_flags, link_flags) for the specified language
        from the inherited environment
        """
        def log_var(var, val: Optional[str]):
            if val:
                mlog.log('Appending {} from environment: {!r}'.format(var, val))
            else:
                mlog.debug('No {} in the environment, not changing global flags.'.format(var))

        lang = self.get_language()
        compiler_is_linker = self.linker is not None and self.linker.invoked_by_compiler()

        if lang not in cflags_mapping:
            return [], []

        compile_flags = []  # type: typing.List[str]
        link_flags = []     # type: typing.List[str]

        env_compile_flags = os.environ.get(cflags_mapping[lang])
        log_var(cflags_mapping[lang], env_compile_flags)
        if env_compile_flags is not None:
            compile_flags += split_args(env_compile_flags)

        # Link flags (same for all languages)
        if self.use_ldflags():
            env_link_flags = self.get_linker_args_from_envvars()
        else:
            env_link_flags = []
        log_var('LDFLAGS', env_link_flags)
        link_flags += env_link_flags
        if compiler_is_linker:
            # When the compiler is used as a wrapper around the linker (such as
            # with GCC and Clang), the compile flags can be needed while linking
            # too. This is also what Autotools does. However, we don't want to do
            # this when the linker is stand-alone such as with MSVC C/C++, etc.
            link_flags = compile_flags + link_flags

        # Pre-processor flags for certain languages
        if self.use_preproc_flags():
            env_preproc_flags = os.environ.get('CPPFLAGS')
            log_var('CPPFLAGS', env_preproc_flags)
            if env_preproc_flags is not None:
                compile_flags += split_args(env_preproc_flags)

        return compile_flags, link_flags

    def get_options(self):
        opts = {} # build afresh every time
        description = 'Extra arguments passed to the {}'.format(self.get_display_language())
        opts.update({
            self.language + '_args': coredata.UserArrayOption(
                description + ' compiler',
                [], split_args=True, user_input=True, allow_dups=True),
            self.language + '_link_args': coredata.UserArrayOption(
                description + ' linker',
                [], split_args=True, user_input=True, allow_dups=True),
        })

        return opts

    def get_and_default_options(self, properties: Properties):
        """
        Take default values from env variables and/or config files.
        """
        opts = self.get_options()

        if properties.fallback:
            # Get from env vars.
            compile_args, link_args = self.get_args_from_envvars()
        else:
            compile_args = []
            link_args = []

        for k, o in opts.items():
            if k in properties:
                # Get from configuration files.
                o.set_value(properties[k])
            elif k == self.language + '_args':
                o.set_value(compile_args)
            elif k == self.language + '_link_args':
                o.set_value(link_args)

        return opts

    def get_option_compile_args(self, options):
        return []

    def get_option_link_args(self, options: 'OptionDictType') -> typing.List[str]:
        return self.linker.get_option_args(options)

    def check_header(self, *args, **kwargs) -> Tuple[bool, bool]:
        raise EnvironmentException('Language %s does not support header checks.' % self.get_display_language())

    def has_header(self, *args, **kwargs) -> Tuple[bool, bool]:
        raise EnvironmentException('Language %s does not support header checks.' % self.get_display_language())

    def has_header_symbol(self, *args, **kwargs) -> Tuple[bool, bool]:
        raise EnvironmentException('Language %s does not support header symbol checks.' % self.get_display_language())

    def compiles(self, *args, **kwargs) -> Tuple[bool, bool]:
        raise EnvironmentException('Language %s does not support compile checks.' % self.get_display_language())

    def links(self, *args, **kwargs) -> Tuple[bool, bool]:
        raise EnvironmentException('Language %s does not support link checks.' % self.get_display_language())

    def run(self, *args, **kwargs) -> RunResult:
        raise EnvironmentException('Language %s does not support run checks.' % self.get_display_language())

    def sizeof(self, *args, **kwargs) -> int:
        raise EnvironmentException('Language %s does not support sizeof checks.' % self.get_display_language())

    def alignment(self, *args, **kwargs) -> int:
        raise EnvironmentException('Language %s does not support alignment checks.' % self.get_display_language())

    def has_function(self, *args, **kwargs) -> Tuple[bool, bool]:
        raise EnvironmentException('Language %s does not support function checks.' % self.get_display_language())

    @classmethod
    def unix_args_to_native(cls, args):
        "Always returns a copy that can be independently mutated"
        return args[:]

    @classmethod
    def native_args_to_unix(cls, args: typing.List[str]) -> typing.List[str]:
        "Always returns a copy that can be independently mutated"
        return args[:]

    def find_library(self, *args, **kwargs):
        raise EnvironmentException('Language {} does not support library finding.'.format(self.get_display_language()))

    def get_library_dirs(self, *args, **kwargs):
        return ()

    def get_program_dirs(self, *args, **kwargs):
        return []

    def has_multi_arguments(self, args, env) -> Tuple[bool, bool]:
        raise EnvironmentException(
            'Language {} does not support has_multi_arguments.'.format(
                self.get_display_language()))

    def has_multi_link_arguments(self, args: typing.List[str], env: 'Environment') -> Tuple[bool, bool]:
        return self.linker.has_multi_arguments(args, env)

    def _get_compile_output(self, dirname, mode):
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

    def get_compiler_args_for_mode(self, mode):
        args = []
        args += self.get_always_args()
        if mode == 'compile':
            args += self.get_compile_only_args()
        if mode == 'preprocess':
            args += self.get_preprocess_only_args()
        return args

    @contextlib.contextmanager
    def compile(self, code, extra_args=None, *, mode='link', want_output=False, temp_dir=None):
        if extra_args is None:
            extra_args = []
        try:
            with tempfile.TemporaryDirectory(dir=temp_dir) as tmpdirname:
                if isinstance(code, str):
                    srcname = os.path.join(tmpdirname,
                                           'testfile.' + self.default_suffix)
                    with open(srcname, 'w') as ofile:
                        ofile.write(code)
                elif isinstance(code, mesonlib.File):
                    srcname = code.fname

                # Construct the compiler command-line
                commands = CompilerArgs(self)
                commands.append(srcname)
                # Preprocess mode outputs to stdout, so no output args
                if mode != 'preprocess':
                    output = self._get_compile_output(tmpdirname, mode)
                    commands += self.get_output_args(output)
                commands.extend(self.get_compiler_args_for_mode(mode))
                # extra_args must be last because it could contain '/link' to
                # pass args to VisualStudio's linker. In that case everything
                # in the command line after '/link' is given to the linker.
                commands += extra_args
                # Generate full command-line with the exelist
                commands = self.get_exelist() + commands.to_native()
                mlog.debug('Running compile:')
                mlog.debug('Working directory: ', tmpdirname)
                mlog.debug('Command line: ', ' '.join(commands), '\n')
                mlog.debug('Code:\n', code)
                os_env = os.environ.copy()
                os_env['LC_ALL'] = 'C'
                p, p.stdo, p.stde = Popen_safe(commands, cwd=tmpdirname, env=os_env)
                mlog.debug('Compiler stdout:\n', p.stdo)
                mlog.debug('Compiler stderr:\n', p.stde)
                p.commands = commands
                p.input_name = srcname
                if want_output:
                    p.output_name = output
                p.cached = False  # Make sure that the cached attribute always exists
                yield p
        except (PermissionError, OSError):
            # On Windows antivirus programs and the like hold on to files so
            # they can't be deleted. There's not much to do in this case. Also,
            # catch OSError because the directory is then no longer empty.
            pass

    @contextlib.contextmanager
    def cached_compile(self, code, cdata: coredata.CoreData, *, extra_args=None, mode: str = 'link', temp_dir=None):
        assert(isinstance(cdata, coredata.CoreData))

        # Calculate the key
        textra_args = tuple(extra_args) if extra_args is not None else None
        key = (tuple(self.exelist), self.version, code, textra_args, mode)

        # Check if not cached
        if key not in cdata.compiler_check_cache:
            with self.compile(code, extra_args=extra_args, mode=mode, want_output=False, temp_dir=temp_dir) as p:
                # Remove all attributes except the following
                # This way the object can be serialized
                tokeep = ['args', 'commands', 'input_name', 'output_name',
                          'pid', 'returncode', 'stdo', 'stde', 'text_mode']
                todel = [x for x in vars(p).keys() if x not in tokeep]
                for i in todel:
                    delattr(p, i)
                p.cached = False
                cdata.compiler_check_cache[key] = p
                yield p
                return

        # Return cached
        p = cdata.compiler_check_cache[key]
        p.cached = True
        mlog.debug('Using cached compile:')
        mlog.debug('Cached command line: ', ' '.join(p.commands), '\n')
        mlog.debug('Code:\n', code)
        mlog.debug('Cached compiler stdout:\n', p.stdo)
        mlog.debug('Cached compiler stderr:\n', p.stde)
        yield p

    def get_colorout_args(self, colortype):
        return []

    # Some compilers (msvc) write debug info to a separate file.
    # These args specify where it should be written.
    def get_compile_debugfile_args(self, rel_obj, **kwargs):
        return []

    def get_link_debugfile_args(self, targetfile: str) -> typing.List[str]:
        return self.linker.get_debugfile_args(targetfile)

    def get_std_shared_lib_link_args(self) -> typing.List[str]:
        return self.linker.get_std_shared_lib_args()

    def get_std_shared_module_link_args(self, options: 'OptionDictType') -> typing.List[str]:
        return self.linker.get_std_shared_module_args(options)

    def get_link_whole_for(self, args: typing.List[str]) -> typing.List[str]:
        return self.linker.get_link_whole_for(args)

    def get_allow_undefined_link_args(self) -> typing.List[str]:
        return self.linker.get_allow_undefined_args()

    def no_undefined_link_args(self) -> typing.List[str]:
        return self.linker.no_undefined_args()

    # Compiler arguments needed to enable the given instruction set.
    # May be [] meaning nothing needed or None meaning the given set
    # is not supported.
    def get_instruction_set_args(self, instruction_set):
        return None

    def build_rpath_args(self, env: 'Environment', build_dir: str, from_dir: str,
                         rpath_paths: str, build_rpath: str,
                         install_rpath: str) -> typing.List[str]:
        return self.linker.build_rpath_args(
            env, build_dir, from_dir, rpath_paths, build_rpath, install_rpath)

    def thread_flags(self, env):
        return []

    def openmp_flags(self):
        raise EnvironmentException('Language %s does not support OpenMP flags.' % self.get_display_language())

    def language_stdlib_only_link_flags(self):
        return []

    def gnu_symbol_visibility_args(self, vistype):
        return []

    def get_gui_app_args(self, value):
        return []

    def has_func_attribute(self, name, env):
        raise EnvironmentException(
            'Language {} does not support function attributes.'.format(self.get_display_language()))

    def get_pic_args(self):
        m = 'Language {} does not support position-independent code'
        raise EnvironmentException(m.format(self.get_display_language()))

    def get_pie_args(self):
        m = 'Language {} does not support position-independent executable'
        raise EnvironmentException(m.format(self.get_display_language()))

    def get_pie_link_args(self) -> typing.List[str]:
        return self.linker.get_pie_args()

    def get_argument_syntax(self):
        """Returns the argument family type.

        Compilers fall into families if they try to emulate the command line
        interface of another compiler. For example, clang is in the GCC family
        since it accepts most of the same arguments as GCC. ICL (ICC on
        windows) is in the MSVC family since it accepts most of the same
        arguments as MSVC.
        """
        return 'other'

    def get_profile_generate_args(self):
        raise EnvironmentException(
            '%s does not support get_profile_generate_args ' % self.get_id())

    def get_profile_use_args(self):
        raise EnvironmentException(
            '%s does not support get_profile_use_args ' % self.get_id())

    def get_undefined_link_args(self) -> typing.List[str]:
        return self.linker.get_undefined_link_args()

    def remove_linkerlike_args(self, args):
        return [x for x in args if not x.startswith('-Wl')]

    def get_lto_compile_args(self) -> List[str]:
        return []

    def get_lto_link_args(self) -> List[str]:
        return self.linker.get_lto_args()

    def sanitizer_compile_args(self, value: str) -> List[str]:
        return []

    def sanitizer_link_args(self, value: str) -> List[str]:
        return self.linker.sanitizer_args(value)

    def get_asneeded_args(self) -> typing.List[str]:
        return self.linker.get_asneeded_args()

    def bitcode_args(self) -> typing.List[str]:
        return self.linker.bitcode_args()

    def get_linker_debug_crt_args(self) -> typing.List[str]:
        return self.linker.get_debug_crt_args()

    def get_buildtype_linker_args(self, buildtype: str) -> typing.List[str]:
        return self.linker.get_buildtype_args(buildtype)

    def get_soname_args(self, env: 'Environment', prefix: str, shlib_name: str,
                        suffix: str, soversion: str, darwin_versions: typing.Tuple[str, str],
                        is_shared_module: bool) -> typing.List[str]:
        return self.linker.get_soname_args(
            env, prefix, shlib_name, suffix, soversion,
            darwin_versions, is_shared_module)

    def get_target_link_args(self, target):
        return target.link_args

    def get_dependency_compile_args(self, dep):
        return dep.get_compile_args()

    def get_dependency_link_args(self, dep):
        return dep.get_link_args()


@enum.unique
class CompilerType(enum.Enum):
    GCC_STANDARD = 0
    GCC_OSX = 1
    GCC_MINGW = 2
    GCC_CYGWIN = 3

    CLANG_STANDARD = 10
    CLANG_OSX = 11
    CLANG_MINGW = 12
    CLANG_EMSCRIPTEN = 13
    # Possibly clang-cl?

    ICC_STANDARD = 20
    ICC_OSX = 21
    ICC_WIN = 22

    ARM_WIN = 30

    CCRX_WIN = 40

    PGI_STANDARD = 50
    PGI_OSX = 51
    PGI_WIN = 52

    @property
    def is_standard_compiler(self):
        return self.name in ('GCC_STANDARD', 'CLANG_STANDARD', 'ICC_STANDARD', 'PGI_STANDARD')

    @property
    def is_osx_compiler(self):
        return self.name in ('GCC_OSX', 'CLANG_OSX', 'ICC_OSX', 'PGI_OSX')

    @property
    def is_windows_compiler(self):
        return self.name in ('GCC_MINGW', 'GCC_CYGWIN', 'CLANG_MINGW', 'ICC_WIN', 'ARM_WIN', 'CCRX_WIN', 'PGI_WIN')

def get_compiler_is_linuxlike(compiler):
    compiler_type = getattr(compiler, 'compiler_type', None)
    return compiler_type and compiler_type.is_standard_compiler

def get_largefile_args(compiler):
    '''
    Enable transparent large-file-support for 32-bit UNIX systems
    '''
    if get_compiler_is_linuxlike(compiler):
        # Enable large-file support unconditionally on all platforms other
        # than macOS and Windows. macOS is now 64-bit-only so it doesn't
        # need anything special, and Windows doesn't have automatic LFS.
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
