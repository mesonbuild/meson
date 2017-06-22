# Copyright 2012-2014 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
import shutil
import contextlib
import subprocess, os.path
import tempfile
from .import mesonlib
from . import mlog
from .mesonlib import EnvironmentException, MesonException, version_compare, Popen_safe
from . import coredata

"""This file contains the data files of all compilers Meson knows
about. To support a new compiler, add its information below.
Also add corresponding autodetection code in environment.py."""

header_suffixes = ('h', 'hh', 'hpp', 'hxx', 'H', 'ipp', 'moc', 'vapi', 'di')
obj_suffixes = ('o', 'obj', 'res')
lib_suffixes = ('a', 'lib', 'dll', 'dylib', 'so')
# Mapping of language to suffixes of files that should always be in that language
# This means we can't include .h headers here since they could be C, C++, ObjC, etc.
lang_suffixes = {
    'c': ('c',),
    'cpp': ('cpp', 'cc', 'cxx', 'c++', 'hh', 'hpp', 'ipp', 'hxx'),
    # f90, f95, f03, f08 are for free-form fortran ('f90' recommended)
    # f, for, ftn, fpp are for fixed-form fortran ('f' or 'for' recommended)
    'fortran': ('f90', 'f95', 'f03', 'f08', 'f', 'for', 'ftn', 'fpp'),
    'd': ('d', 'di'),
    'objc': ('m',),
    'objcpp': ('mm',),
    'rust': ('rs',),
    'vala': ('vala', 'vapi'),
    'cs': ('cs',),
    'swift': ('swift',),
    'java': ('java',),
}
cpp_suffixes = lang_suffixes['cpp'] + ('h',)
c_suffixes = lang_suffixes['c'] + ('h',)
# List of languages that can be linked with C code directly by the linker
# used in build.py:process_compilers() and build.py:get_dynamic_linker()
clike_langs = ('objcpp', 'objc', 'd', 'cpp', 'c', 'fortran',)
clike_suffixes = ()
for _l in clike_langs:
    clike_suffixes += lang_suffixes[_l]
clike_suffixes += ('h', 'll', 's')

# All these are only for C-like languages; see `clike_langs` above.

def sort_clike(lang):
    '''
    Sorting function to sort the list of languages according to
    reversed(compilers.clike_langs) and append the unknown langs in the end.
    The purpose is to prefer C over C++ for files that can be compiled by
    both such as assembly, C, etc. Also applies to ObjC, ObjC++, etc.
    '''
    if lang not in clike_langs:
        return 1
    return -clike_langs.index(lang)

def is_header(fname):
    if hasattr(fname, 'fname'):
        fname = fname.fname
    suffix = fname.split('.')[-1]
    return suffix in header_suffixes

def is_source(fname):
    if hasattr(fname, 'fname'):
        fname = fname.fname
    suffix = fname.split('.')[-1].lower()
    return suffix in clike_suffixes

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
    suffix = fname.split('.')[-1]
    return suffix in lib_suffixes

gnulike_buildtype_args = {'plain': [],
                          # -O0 is passed for improved debugging information with gcc
                          # See https://github.com/mesonbuild/meson/pull/509
                          'debug': ['-O0', '-g'],
                          'debugoptimized': ['-O2', '-g'],
                          'release': ['-O3'],
                          'minsize': ['-Os', '-g']}

msvc_buildtype_args = {'plain': [],
                       'debug': ["/MDd", "/ZI", "/Ob0", "/Od", "/RTC1"],
                       'debugoptimized': ["/MD", "/Zi", "/O2", "/Ob1"],
                       'release': ["/MD", "/O2", "/Ob2"],
                       'minsize': ["/MD", "/Zi", "/Os", "/Ob1"],
                       }

apple_buildtype_linker_args = {'plain': [],
                               'debug': [],
                               'debugoptimized': [],
                               'release': [],
                               'minsize': [],
                               }

gnulike_buildtype_linker_args = {'plain': [],
                                 'debug': [],
                                 'debugoptimized': [],
                                 'release': ['-Wl,-O1'],
                                 'minsize': [],
                                 }

msvc_buildtype_linker_args = {'plain': [],
                              'debug': [],
                              'debugoptimized': [],
                              'release': [],
                              'minsize': ['/INCREMENTAL:NO'],
                              }

java_buildtype_args = {'plain': [],
                       'debug': ['-g'],
                       'debugoptimized': ['-g'],
                       'release': [],
                       'minsize': [],
                       }

rust_buildtype_args = {'plain': [],
                       'debug': ['-C', 'debuginfo=2'],
                       'debugoptimized': ['-C', 'debuginfo=2', '-C', 'opt-level=2'],
                       'release': ['-C', 'opt-level=3'],
                       'minsize': [], # In a future release: ['-C', 'opt-level=s'],
                       }

d_gdc_buildtype_args = {'plain': [],
                        'debug': ['-g', '-O0'],
                        'debugoptimized': ['-g', '-O'],
                        'release': ['-O3', '-frelease'],
                        'minsize': [],
                        }

d_ldc_buildtype_args = {'plain': [],
                        'debug': ['-g', '-O0'],
                        'debugoptimized': ['-g', '-O'],
                        'release': ['-O3', '-release'],
                        'minsize': [],
                        }

d_dmd_buildtype_args = {'plain': [],
                        'debug': ['-g'],
                        'debugoptimized': ['-g', '-O'],
                        'release': ['-O', '-release'],
                        'minsize': [],
                        }

mono_buildtype_args = {'plain': [],
                       'debug': ['-debug'],
                       'debugoptimized': ['-debug', '-optimize+'],
                       'release': ['-optimize+'],
                       'minsize': [],
                       }

swift_buildtype_args = {'plain': [],
                        'debug': ['-g'],
                        'debugoptimized': ['-g', '-O'],
                        'release': ['-O'],
                        'minsize': [],
                        }

gnu_winlibs = ['-lkernel32', '-luser32', '-lgdi32', '-lwinspool', '-lshell32',
               '-lole32', '-loleaut32', '-luuid', '-lcomdlg32', '-ladvapi32']

msvc_winlibs = ['kernel32.lib', 'user32.lib', 'gdi32.lib',
                'winspool.lib', 'shell32.lib', 'ole32.lib', 'oleaut32.lib',
                'uuid.lib', 'comdlg32.lib', 'advapi32.lib']

gnu_color_args = {'auto': ['-fdiagnostics-color=auto'],
                  'always': ['-fdiagnostics-color=always'],
                  'never': ['-fdiagnostics-color=never'],
                  }

clang_color_args = {'auto': ['-Xclang', '-fcolor-diagnostics'],
                    'always': ['-Xclang', '-fcolor-diagnostics'],
                    'never': ['-Xclang', '-fno-color-diagnostics'],
                    }

base_options = {'b_pch': coredata.UserBooleanOption('b_pch', 'Use precompiled headers', True),
                'b_lto': coredata.UserBooleanOption('b_lto', 'Use link time optimization', False),
                'b_sanitize': coredata.UserComboOption('b_sanitize',
                                                       'Code sanitizer to use',
                                                       ['none', 'address', 'thread', 'undefined', 'memory'],
                                                       'none'),
                'b_lundef': coredata.UserBooleanOption('b_lundef', 'Use -Wl,--no-undefined when linking', True),
                'b_asneeded': coredata.UserBooleanOption('b_asneeded', 'Use -Wl,--as-needed when linking', True),
                'b_pgo': coredata.UserComboOption('b_pgo', 'Use profile guide optimization',
                                                  ['off', 'generate', 'use'],
                                                  'off'),
                'b_coverage': coredata.UserBooleanOption('b_coverage',
                                                         'Enable coverage tracking.',
                                                         False),
                'b_colorout': coredata.UserComboOption('b_colorout', 'Use colored output',
                                                       ['auto', 'always', 'never'],
                                                       'always'),
                'b_ndebug': coredata.UserBooleanOption('b_ndebug',
                                                       'Disable asserts',
                                                       False),
                'b_staticpic': coredata.UserBooleanOption('b_staticpic',
                                                          'Build static libraries as position independent',
                                                          True),
                }

def sanitizer_compile_args(value):
    if value == 'none':
        return []
    args = ['-fsanitize=' + value]
    if value == 'address':
        args.append('-fno-omit-frame-pointer')
    return args

def sanitizer_link_args(value):
    if value == 'none':
        return []
    args = ['-fsanitize=' + value]
    return args

def get_base_compile_args(options, compiler):
    args = []
    # FIXME, gcc/clang specific.
    try:
        if options['b_lto'].value:
            args.append('-flto')
    except KeyError:
        pass
    try:
        args += compiler.get_colorout_args(options['b_colorout'].value)
    except KeyError:
        pass
    try:
        args += sanitizer_compile_args(options['b_sanitize'].value)
    except KeyError:
        pass
    try:
        pgo_val = options['b_pgo'].value
        if pgo_val == 'generate':
            args.append('-fprofile-generate')
        elif pgo_val == 'use':
            args.append('-fprofile-use')
    except KeyError:
        pass
    try:
        if options['b_coverage'].value:
            args += compiler.get_coverage_args()
    except KeyError:
        pass
    try:
        if options['b_ndebug'].value:
            args += ['-DNDEBUG']
    except KeyError:
        pass
    return args

def get_base_link_args(options, linker, is_shared_module):
    args = []
    # FIXME, gcc/clang specific.
    try:
        if options['b_lto'].value:
            args.append('-flto')
    except KeyError:
        pass
    try:
        args += sanitizer_link_args(options['b_sanitize'].value)
    except KeyError:
        pass
    try:
        pgo_val = options['b_pgo'].value
        if pgo_val == 'generate':
            args.append('-fprofile-generate')
        elif pgo_val == 'use':
            args.append('-fprofile-use')
    except KeyError:
        pass
    try:
        if not is_shared_module and 'b_lundef' in linker.base_options and options['b_lundef'].value:
            args.append('-Wl,--no-undefined')
    except KeyError:
        pass
    try:
        if 'b_asneeded' in linker.base_options and options['b_asneeded'].value:
            args.append('-Wl,--as-needed')
    except KeyError:
        pass
    try:
        if options['b_coverage'].value:
            args += linker.get_coverage_link_args()
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
    dedup2_prefixes = ('-I', '-L', '-D', '-U')
    dedup2_suffixes = ()
    dedup2_args = ()
    # Arg prefixes and args that must be de-duped by returning 1
    dedup1_prefixes = ('-l',)
    dedup1_suffixes = ('.lib', '.dll', '.so', '.dylib', '.a')
    # Match a .so of the form path/to/libfoo.so.0.1.0
    # Only UNIX shared libraries require this. Others have a fixed extension.
    dedup1_regex = re.compile(r'([\/\\]|\A)lib.*\.so(\.[0-9]+)?(\.[0-9]+)?(\.[0-9]+)?$')
    dedup1_args = ('-c', '-S', '-E', '-pipe', '-pthread')
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

        a) Whether an argument can be 'overriden' by a later argument.  For
           example, -DFOO defines FOO and -UFOO undefines FOO. In this case, we
           can safely remove the previous occurance and add a new one. The same
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

    def to_native(self):
        # Check if we need to add --start/end-group for circular dependencies
        # between static libraries.
        if get_compiler_uses_gnuld(self.compiler):
            group_started = False
            for each in self:
                if not each.startswith('-l') and not each.endswith('.a'):
                    continue
                i = self.index(each)
                if not group_started:
                    # First occurance of a library
                    self.insert(i, '-Wl,--start-group')
                    group_started = True
            # Last occurance of a library
            if group_started:
                self.insert(i + 1, '-Wl,--end-group')
        return self.compiler.unix_args_to_native(self)

    def append_direct(self, arg):
        '''
        Append the specified argument without any reordering or de-dup
        '''
        super().append(arg)

    def extend_direct(self, iterable):
        '''
        Extend using the elements in the specified iterable without any
        reordering or de-dup
        '''
        super().extend(iterable)

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
            # previous occurance of it and adding a new one, or not adding the
            # new occurance.
            dedup = self._can_dedup(arg)
            if dedup == 1:
                # Argument already exists and adding a new instance is useless
                if arg in self or arg in pre or arg in post:
                    continue
            if dedup == 2:
                # Remove all previous occurances of the arg and add it anew
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
    def __init__(self, exelist, version):
        if isinstance(exelist, str):
            self.exelist = [exelist]
        elif isinstance(exelist, list):
            self.exelist = exelist
        else:
            raise TypeError('Unknown argument to Compiler')
        # In case it's been overriden by a child class already
        if not hasattr(self, 'file_suffixes'):
            self.file_suffixes = lang_suffixes[self.language]
        if not hasattr(self, 'can_compile_suffixes'):
            self.can_compile_suffixes = set(self.file_suffixes)
        self.default_suffix = self.file_suffixes[0]
        self.version = version
        self.base_options = []

    def __repr__(self):
        repr_str = "<{0}: v{1} `{2}`>"
        return repr_str.format(self.__class__.__name__, self.version,
                               ' '.join(self.exelist))

    def can_compile(self, src):
        if hasattr(src, 'fname'):
            src = src.fname
        suffix = os.path.splitext(src)[1].lower()
        if suffix and suffix[1:] in self.can_compile_suffixes:
            return True
        return False

    def get_id(self):
        return self.id

    def get_language(self):
        return self.language

    def get_default_suffix(self):
        return self.default_suffix

    def get_exelist(self):
        return self.exelist[:]

    def get_builtin_define(self, *args, **kwargs):
        raise EnvironmentException('%s does not support get_builtin_define.' % self.id)

    def has_builtin_define(self, *args, **kwargs):
        raise EnvironmentException('%s does not support has_builtin_define.' % self.id)

    def get_always_args(self):
        return []

    def get_linker_always_args(self):
        return []

    def gen_import_library_args(self, implibname):
        """
        Used only on Windows for libraries that need an import library.
        This currently means C, C++, Fortran.
        """
        return []

    def get_options(self):
        return {} # build afresh every time

    def get_option_compile_args(self, options):
        return []

    def get_option_link_args(self, options):
        return []

    def has_header(self, *args, **kwargs):
        raise EnvironmentException('Language %s does not support header checks.' % self.language)

    def has_header_symbol(self, *args, **kwargs):
        raise EnvironmentException('Language %s does not support header symbol checks.' % self.language)

    def compiles(self, *args, **kwargs):
        raise EnvironmentException('Language %s does not support compile checks.' % self.language)

    def links(self, *args, **kwargs):
        raise EnvironmentException('Language %s does not support link checks.' % self.language)

    def run(self, *args, **kwargs):
        raise EnvironmentException('Language %s does not support run checks.' % self.language)

    def sizeof(self, *args, **kwargs):
        raise EnvironmentException('Language %s does not support sizeof checks.' % self.language)

    def alignment(self, *args, **kwargs):
        raise EnvironmentException('Language %s does not support alignment checks.' % self.language)

    def has_function(self, *args, **kwargs):
        raise EnvironmentException('Language %s does not support function checks.' % self.language)

    @classmethod
    def unix_args_to_native(cls, args):
        "Always returns a copy that can be independently mutated"
        return args[:]

    def find_library(self, *args, **kwargs):
        raise EnvironmentException('Language {} does not support library finding.'.format(self.language))

    def get_library_dirs(self):
        return []

    def has_argument(self, arg, env):
        return self.has_multi_arguments([arg], env)

    def has_multi_arguments(self, args, env):
        raise EnvironmentException(
            'Language {} does not support has_multi_arguments.'.format(
                self.language))

    def get_cross_extra_flags(self, environment, link):
        extra_flags = []
        if self.is_cross and environment:
            if 'properties' in environment.cross_info.config:
                props = environment.cross_info.config['properties']
                lang_args_key = self.language + '_args'
                extra_flags += props.get(lang_args_key, [])
                lang_link_args_key = self.language + '_link_args'
                if link:
                    extra_flags += props.get(lang_link_args_key, [])
        return extra_flags

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

    @contextlib.contextmanager
    def compile(self, code, extra_args=None, mode='link'):
        if extra_args is None:
            extra_args = []
        try:
            with tempfile.TemporaryDirectory() as tmpdirname:
                if isinstance(code, str):
                    srcname = os.path.join(tmpdirname,
                                           'testfile.' + self.default_suffix)
                    with open(srcname, 'w') as ofile:
                        ofile.write(code)
                elif isinstance(code, mesonlib.File):
                    srcname = code.fname
                output = self._get_compile_output(tmpdirname, mode)

                # Construct the compiler command-line
                commands = CompilerArgs(self)
                commands.append(srcname)
                commands += extra_args
                commands += self.get_always_args()
                if mode == 'compile':
                    commands += self.get_compile_only_args()
                # Preprocess mode outputs to stdout, so no output args
                if mode == 'preprocess':
                    commands += self.get_preprocess_only_args()
                else:
                    commands += self.get_output_args(output)
                # Generate full command-line with the exelist
                commands = self.get_exelist() + commands.to_native()
                mlog.debug('Running compile:')
                mlog.debug('Working directory: ', tmpdirname)
                mlog.debug('Command line: ', ' '.join(commands), '\n')
                mlog.debug('Code:\n', code)
                p, p.stdo, p.stde = Popen_safe(commands, cwd=tmpdirname)
                mlog.debug('Compiler stdout:\n', p.stdo)
                mlog.debug('Compiler stderr:\n', p.stde)
                p.input_name = srcname
                p.output_name = output
                yield p
        except (PermissionError, OSError):
            # On Windows antivirus programs and the like hold on to files so
            # they can't be deleted. There's not much to do in this case. Also,
            # catch OSError because the directory is then no longer empty.
            pass

    def get_colorout_args(self, colortype):
        return []

    # Some compilers (msvc) write debug info to a separate file.
    # These args specify where it should be written.
    def get_compile_debugfile_args(self, rel_obj, **kwargs):
        return []

    def get_link_debugfile_args(self, rel_obj):
        return []

    def get_std_shared_lib_link_args(self):
        return []

    def get_std_shared_module_link_args(self):
        return self.get_std_shared_lib_link_args()

    def get_link_whole_for(self, args):
        if isinstance(args, list) and not args:
            return []
        raise EnvironmentException('Language %s does not support linking whole archives.' % self.language)

    def build_unix_rpath_args(self, build_dir, from_dir, rpath_paths, install_rpath):
        if not rpath_paths and not install_rpath:
            return []
        # The rpaths we write must be relative, because otherwise
        # they have different length depending on the build
        # directory. This breaks reproducible builds.
        rel_rpaths = []
        for p in rpath_paths:
            if p == from_dir:
                relative = '' # relpath errors out in this case
            else:
                relative = os.path.relpath(p, from_dir)
            rel_rpaths.append(relative)
        paths = ':'.join([os.path.join('$ORIGIN', p) for p in rel_rpaths])
        if len(paths) < len(install_rpath):
            padding = 'X' * (len(install_rpath) - len(paths))
            if not paths:
                paths = padding
            else:
                paths = paths + ':' + padding
        args = ['-Wl,-rpath,' + paths]
        if get_compiler_is_linuxlike(self):
            # Rpaths to use while linking must be absolute. These are not
            # written to the binary. Needed only with GNU ld:
            # https://sourceware.org/bugzilla/show_bug.cgi?id=16936
            # Not needed on Windows or other platforms that don't use RPATH
            # https://github.com/mesonbuild/meson/issues/1897
            lpaths = ':'.join([os.path.join(build_dir, p) for p in rpath_paths])
            args += ['-Wl,-rpath-link,' + lpaths]
        return args

class CCompiler(Compiler):
    def __init__(self, exelist, version, is_cross, exe_wrapper=None):
        # If a child ObjC or CPP class has already set it, don't set it ourselves
        if not hasattr(self, 'language'):
            self.language = 'c'
        super().__init__(exelist, version)
        self.id = 'unknown'
        self.is_cross = is_cross
        self.can_compile_suffixes.add('h')
        if isinstance(exe_wrapper, str):
            self.exe_wrapper = [exe_wrapper]
        else:
            self.exe_wrapper = exe_wrapper

    def needs_static_linker(self):
        return True # When compiling static libraries, so yes.

    def get_always_args(self):
        '''
        Args that are always-on for all C compilers other than MSVC
        '''
        return ['-pipe'] + get_largefile_args(self)

    def get_linker_debug_crt_args(self):
        """
        Arguments needed to select a debug crt for the linker
        This is only needed for MSVC
        """
        return []

    def get_no_stdinc_args(self):
        return ['-nostdinc']

    def get_no_stdlib_link_args(self):
        return ['-nostdlib']

    def get_warn_args(self, level):
        return self.warn_args[level]

    def get_no_warn_args(self):
        # Almost every compiler uses this for disabling warnings
        return ['-w']

    def get_soname_args(self, prefix, shlib_name, suffix, path, soversion, is_shared_module):
        return []

    def split_shlib_to_parts(self, fname):
        return None, fname

    # The default behavior is this, override in MSVC
    def build_rpath_args(self, build_dir, from_dir, rpath_paths, install_rpath):
        return self.build_unix_rpath_args(build_dir, from_dir, rpath_paths, install_rpath)

    def get_dependency_gen_args(self, outtarget, outfile):
        return ['-MMD', '-MQ', outtarget, '-MF', outfile]

    def depfile_for_object(self, objfile):
        return objfile + '.' + self.get_depfile_suffix()

    def get_depfile_suffix(self):
        return 'd'

    def get_exelist(self):
        return self.exelist[:]

    def get_linker_exelist(self):
        return self.exelist[:]

    def get_preprocess_only_args(self):
        return ['-E', '-P']

    def get_compile_only_args(self):
        return ['-c']

    def get_no_optimization_args(self):
        return ['-O0']

    def get_compiler_check_args(self):
        '''
        Get arguments useful for compiler checks such as being permissive in
        the code quality and not doing any optimization.
        '''
        return self.get_no_optimization_args()

    def get_output_args(self, target):
        return ['-o', target]

    def get_linker_output_args(self, outputname):
        return ['-o', outputname]

    def get_coverage_args(self):
        return ['--coverage']

    def get_coverage_link_args(self):
        return ['--coverage']

    def get_werror_args(self):
        return ['-Werror']

    def get_std_exe_link_args(self):
        return []

    def get_include_args(self, path, is_system):
        if path == '':
            path = '.'
        if is_system:
            return ['-isystem', path]
        return ['-I' + path]

    def get_std_shared_lib_link_args(self):
        return ['-shared']

    def get_library_dirs(self):
        stdo = Popen_safe(self.exelist + ['--print-search-dirs'])[1]
        for line in stdo.split('\n'):
            if line.startswith('libraries:'):
                libstr = line.split('=', 1)[1]
                return libstr.split(':')
        return []

    def get_pic_args(self):
        return ['-fPIC']

    def name_string(self):
        return ' '.join(self.exelist)

    def get_pch_use_args(self, pch_dir, header):
        return ['-include', os.path.split(header)[-1]]

    def get_pch_name(self, header_name):
        return os.path.split(header_name)[-1] + '.' + self.get_pch_suffix()

    def get_linker_search_args(self, dirname):
        return ['-L' + dirname]

    def gen_import_library_args(self, implibname):
        """
        The name of the outputted import library

        This implementation is used only on Windows by compilers that use GNU ld
        """
        return ['-Wl,--out-implib=' + implibname]

    def sanity_check_impl(self, work_dir, environment, sname, code):
        mlog.debug('Sanity testing ' + self.language + ' compiler:', ' '.join(self.exelist))
        mlog.debug('Is cross compiler: %s.' % str(self.is_cross))

        extra_flags = []
        source_name = os.path.join(work_dir, sname)
        binname = sname.rsplit('.', 1)[0]
        if self.is_cross:
            binname += '_cross'
            if self.exe_wrapper is None:
                # Linking cross built apps is painful. You can't really
                # tell if you should use -nostdlib or not and for example
                # on OSX the compiler binary is the same but you need
                # a ton of compiler flags to differentiate between
                # arm and x86_64. So just compile.
                extra_flags += self.get_cross_extra_flags(environment, link=False)
                extra_flags += self.get_compile_only_args()
            else:
                extra_flags += self.get_cross_extra_flags(environment, link=True)
        # Is a valid executable output for all toolchains and platforms
        binname += '.exe'
        # Write binary check source
        binary_name = os.path.join(work_dir, binname)
        with open(source_name, 'w') as ofile:
            ofile.write(code)
        # Compile sanity check
        cmdlist = self.exelist + extra_flags + [source_name] + self.get_output_args(binary_name)
        pc, stdo, stde = Popen_safe(cmdlist, cwd=work_dir)
        mlog.debug('Sanity check compiler command line:', ' '.join(cmdlist))
        mlog.debug('Sanity check compile stdout:')
        mlog.debug(stdo)
        mlog.debug('-----\nSanity check compile stderr:')
        mlog.debug(stde)
        mlog.debug('-----')
        if pc.returncode != 0:
            raise EnvironmentException('Compiler {0} can not compile programs.'.format(self.name_string()))
        # Run sanity check
        if self.is_cross:
            if self.exe_wrapper is None:
                # Can't check if the binaries run so we have to assume they do
                return
            cmdlist = self.exe_wrapper + [binary_name]
        else:
            cmdlist = [binary_name]
        mlog.debug('Running test binary command: ' + ' '.join(cmdlist))
        pe = subprocess.Popen(cmdlist)
        pe.wait()
        if pe.returncode != 0:
            raise EnvironmentException('Executables created by {0} compiler {1} are not runnable.'.format(self.language, self.name_string()))

    def sanity_check(self, work_dir, environment):
        code = 'int main(int argc, char **argv) { int class=0; return class; }\n'
        return self.sanity_check_impl(work_dir, environment, 'sanitycheckc.c', code)

    def has_header(self, hname, prefix, env, extra_args=None, dependencies=None):
        fargs = {'prefix': prefix, 'header': hname}
        code = '''{prefix}
        #ifdef __has_include
         #if !__has_include("{header}")
          #error "Header '{header}' could not be found"
         #endif
        #else
         #include <{header}>
        #endif'''
        return self.compiles(code.format(**fargs), env, extra_args,
                             dependencies, 'preprocess')

    def has_header_symbol(self, hname, symbol, prefix, env, extra_args=None, dependencies=None):
        fargs = {'prefix': prefix, 'header': hname, 'symbol': symbol}
        t = '''{prefix}
        #include <{header}>
        int main () {{
            /* If it's not defined as a macro, try to use as a symbol */
            #ifndef {symbol}
                {symbol};
            #endif
        }}'''
        return self.compiles(t.format(**fargs), env, extra_args, dependencies)

    def _get_compiler_check_args(self, env, extra_args, dependencies, mode='compile'):
        if extra_args is None:
            extra_args = []
        elif isinstance(extra_args, str):
            extra_args = [extra_args]
        if dependencies is None:
            dependencies = []
        elif not isinstance(dependencies, list):
            dependencies = [dependencies]
        # Collect compiler arguments
        args = CompilerArgs(self)
        for d in dependencies:
            # Add compile flags needed by dependencies
            args += d.get_compile_args()
            if mode == 'link':
                # Add link flags needed to find dependencies
                args += d.get_link_args()
        # Select a CRT if needed since we're linking
        if mode == 'link':
            args += self.get_linker_debug_crt_args()
        # Read c_args/cpp_args/etc from the cross-info file (if needed)
        args += self.get_cross_extra_flags(env, link=(mode == 'link'))
        if not self.is_cross:
            if mode == 'preprocess':
                # Add CPPFLAGS from the env.
                args += env.coredata.external_preprocess_args[self.language]
            elif mode == 'compile':
                # Add CFLAGS/CXXFLAGS/OBJCFLAGS/OBJCXXFLAGS from the env
                args += env.coredata.external_args[self.language]
            elif mode == 'link':
                # Add LDFLAGS from the env
                args += env.coredata.external_link_args[self.language]
        args += self.get_compiler_check_args()
        # extra_args must override all other arguments, so we add them last
        args += extra_args
        return args

    def compiles(self, code, env, extra_args=None, dependencies=None, mode='compile'):
        args = self._get_compiler_check_args(env, extra_args, dependencies, mode)
        # We only want to compile; not link
        with self.compile(code, args.to_native(), mode) as p:
            return p.returncode == 0

    def _links_wrapper(self, code, env, extra_args, dependencies):
        "Shares common code between self.links and self.run"
        args = self._get_compiler_check_args(env, extra_args, dependencies, mode='link')
        return self.compile(code, args)

    def links(self, code, env, extra_args=None, dependencies=None):
        with self._links_wrapper(code, env, extra_args, dependencies) as p:
            return p.returncode == 0

    def run(self, code, env, extra_args=None, dependencies=None):
        if self.is_cross and self.exe_wrapper is None:
            raise CrossNoRunException('Can not run test applications in this cross environment.')
        with self._links_wrapper(code, env, extra_args, dependencies) as p:
            if p.returncode != 0:
                mlog.debug('Could not compile test file %s: %d\n' % (
                    p.input_name,
                    p.returncode))
                return RunResult(False)
            if self.is_cross:
                cmdlist = self.exe_wrapper + [p.output_name]
            else:
                cmdlist = p.output_name
            try:
                pe, so, se = Popen_safe(cmdlist)
            except Exception as e:
                mlog.debug('Could not run: %s (error: %s)\n' % (cmdlist, e))
                return RunResult(False)

        mlog.debug('Program stdout:\n')
        mlog.debug(so)
        mlog.debug('Program stderr:\n')
        mlog.debug(se)
        return RunResult(True, pe.returncode, so, se)

    def _compile_int(self, expression, prefix, env, extra_args, dependencies):
        fargs = {'prefix': prefix, 'expression': expression}
        t = '''#include <stdio.h>
        {prefix}
        int main() {{ static int a[1-2*!({expression})]; a[0]=0; return 0; }}'''
        return self.compiles(t.format(**fargs), env, extra_args, dependencies)

    def cross_compute_int(self, expression, low, high, guess, prefix, env, extra_args, dependencies):
        if isinstance(guess, int):
            if self._compile_int('%s == %d' % (expression, guess), prefix, env, extra_args, dependencies):
                return guess

        cur = low
        while low < high:
            cur = int((low + high) / 2)
            if cur == low:
                break

            if self._compile_int('%s >= %d' % (expression, cur), prefix, env, extra_args, dependencies):
                low = cur
            else:
                high = cur

        if self._compile_int('%s == %d' % (expression, cur), prefix, env, extra_args, dependencies):
            return cur
        raise EnvironmentException('Cross-compile check overflowed')

    def compute_int(self, expression, low, high, guess, prefix, env, extra_args=None, dependencies=None):
        if extra_args is None:
            extra_args = []
        if self.is_cross:
            return self.cross_compute_int(expression, low, high, guess, prefix, env, extra_args, dependencies)
        fargs = {'prefix': prefix, 'expression': expression}
        t = '''#include<stdio.h>
        {prefix}
        int main(int argc, char **argv) {{
            printf("%ld\\n", (long)({expression}));
            return 0;
        }};'''
        res = self.run(t.format(**fargs), env, extra_args, dependencies)
        if not res.compiled:
            return -1
        if res.returncode != 0:
            raise EnvironmentException('Could not run compute_int test binary.')
        return int(res.stdout)

    def cross_sizeof(self, typename, prefix, env, extra_args=None, dependencies=None):
        if extra_args is None:
            extra_args = []
        fargs = {'prefix': prefix, 'type': typename}
        t = '''#include <stdio.h>
        {prefix}
        int main(int argc, char **argv) {{
            {type} something;
        }}'''
        if not self.compiles(t.format(**fargs), env, extra_args, dependencies):
            return -1
        return self.cross_compute_int('sizeof(%s)' % typename, 1, 128, None, prefix, env, extra_args, dependencies)

    def sizeof(self, typename, prefix, env, extra_args=None, dependencies=None):
        if extra_args is None:
            extra_args = []
        fargs = {'prefix': prefix, 'type': typename}
        if self.is_cross:
            return self.cross_sizeof(typename, prefix, env, extra_args, dependencies)
        t = '''#include<stdio.h>
        {prefix}
        int main(int argc, char **argv) {{
            printf("%ld\\n", (long)(sizeof({type})));
            return 0;
        }};'''
        res = self.run(t.format(**fargs), env, extra_args, dependencies)
        if not res.compiled:
            return -1
        if res.returncode != 0:
            raise EnvironmentException('Could not run sizeof test binary.')
        return int(res.stdout)

    def cross_alignment(self, typename, prefix, env, extra_args=None, dependencies=None):
        if extra_args is None:
            extra_args = []
        fargs = {'prefix': prefix, 'type': typename}
        t = '''#include <stdio.h>
        {prefix}
        int main(int argc, char **argv) {{
            {type} something;
        }}'''
        if not self.compiles(t.format(**fargs), env, extra_args, dependencies):
            return -1
        t = '''#include <stddef.h>
        {prefix}
        struct tmp {{
            char c;
            {type} target;
        }};'''
        return self.cross_compute_int('offsetof(struct tmp, target)', 1, 1024, None, t.format(**fargs), env, extra_args, dependencies)

    def alignment(self, typename, prefix, env, extra_args=None, dependencies=None):
        if extra_args is None:
            extra_args = []
        if self.is_cross:
            return self.cross_alignment(typename, prefix, env, extra_args, dependencies)
        fargs = {'prefix': prefix, 'type': typename}
        t = '''#include <stdio.h>
        #include <stddef.h>
        {prefix}
        struct tmp {{
            char c;
            {type} target;
        }};
        int main(int argc, char **argv) {{
            printf("%d", (int)offsetof(struct tmp, target));
            return 0;
        }}'''
        res = self.run(t.format(**fargs), env, extra_args, dependencies)
        if not res.compiled:
            raise EnvironmentException('Could not compile alignment test.')
        if res.returncode != 0:
            raise EnvironmentException('Could not run alignment test binary.')
        align = int(res.stdout)
        if align == 0:
            raise EnvironmentException('Could not determine alignment of %s. Sorry. You might want to file a bug.' % typename)
        return align

    def get_define(self, dname, prefix, env, extra_args, dependencies):
        delim = '"MESON_GET_DEFINE_DELIMITER"'
        fargs = {'prefix': prefix, 'define': dname, 'delim': delim}
        code = '''
        {prefix}
        #ifndef {define}
        # define {define}
        #endif
        {delim}\n{define}'''
        args = self._get_compiler_check_args(env, extra_args, dependencies,
                                             mode='preprocess').to_native()
        with self.compile(code.format(**fargs), args, 'preprocess') as p:
            if p.returncode != 0:
                raise EnvironmentException('Could not get define {!r}'.format(dname))
        # Get the preprocessed value after the delimiter,
        # minus the extra newline at the end
        return p.stdo.split(delim + '\n')[-1][:-1]

    @staticmethod
    def _no_prototype_templ():
        """
        Try to find the function without a prototype from a header by defining
        our own dummy prototype and trying to link with the C library (and
        whatever else the compiler links in by default). This is very similar
        to the check performed by Autoconf for AC_CHECK_FUNCS.
        """
        # Define the symbol to something else since it is defined by the
        # includes or defines listed by the user or by the compiler. This may
        # include, for instance _GNU_SOURCE which must be defined before
        # limits.h, which includes features.h
        # Then, undef the symbol to get rid of it completely.
        head = '''
        #define {func} meson_disable_define_of_{func}
        {prefix}
        #include <limits.h>
        #undef {func}
        '''
        # Override any GCC internal prototype and declare our own definition for
        # the symbol. Use char because that's unlikely to be an actual return
        # value for a function which ensures that we override the definition.
        head += '''
        #ifdef __cplusplus
        extern "C"
        #endif
        char {func} ();
        '''
        # The actual function call
        main = '''
        int main () {{
          return {func} ();
        }}'''
        return head, main

    @staticmethod
    def _have_prototype_templ():
        """
        Returns a head-er and main() call that uses the headers listed by the
        user for the function prototype while checking if a function exists.
        """
        # Add the 'prefix', aka defines, includes, etc that the user provides
        # This may include, for instance _GNU_SOURCE which must be defined
        # before limits.h, which includes features.h
        head = '{prefix}\n#include <limits.h>\n'
        # We don't know what the function takes or returns, so return it as an int.
        # Just taking the address or comparing it to void is not enough because
        # compilers are smart enough to optimize it away. The resulting binary
        # is not run so we don't care what the return value is.
        main = '''\nint main() {{
            void *a = (void*) &{func};
            long b = (long) a;
            return (int) b;
        }}'''
        return head, main

    def has_function(self, funcname, prefix, env, extra_args=None, dependencies=None):
        """
        First, this function looks for the symbol in the default libraries
        provided by the compiler (stdlib + a few others usually). If that
        fails, it checks if any of the headers specified in the prefix provide
        an implementation of the function, and if that fails, it checks if it's
        implemented as a compiler-builtin.
        """
        if extra_args is None:
            extra_args = []

        # Short-circuit if the check is already provided by the cross-info file
        varname = 'has function ' + funcname
        varname = varname.replace(' ', '_')
        if self.is_cross:
            val = env.cross_info.config['properties'].get(varname, None)
            if val is not None:
                if isinstance(val, bool):
                    return val
                raise EnvironmentException('Cross variable {0} is not a boolean.'.format(varname))

        fargs = {'prefix': prefix, 'func': funcname}

        # glibc defines functions that are not available on Linux as stubs that
        # fail with ENOSYS (such as e.g. lchmod). In this case we want to fail
        # instead of detecting the stub as a valid symbol.
        # We already included limits.h earlier to ensure that these are defined
        # for stub functions.
        stubs_fail = '''
        #if defined __stub_{func} || defined __stub___{func}
        fail fail fail this function is not going to work
        #endif
        '''

        # If we have any includes in the prefix supplied by the user, assume
        # that the user wants us to use the symbol prototype defined in those
        # includes. If not, then try to do the Autoconf-style check with
        # a dummy prototype definition of our own.
        # This is needed when the linker determines symbol availability from an
        # SDK based on the prototype in the header provided by the SDK.
        # Ignoring this prototype would result in the symbol always being
        # marked as available.
        if '#include' in prefix:
            head, main = self._have_prototype_templ()
        else:
            head, main = self._no_prototype_templ()
        templ = head + stubs_fail + main

        if self.links(templ.format(**fargs), env, extra_args, dependencies):
            return True

        # MSVC does not have compiler __builtin_-s.
        if self.get_id() == 'msvc':
            return False

        # Detect function as a built-in
        #
        # Some functions like alloca() are defined as compiler built-ins which
        # are inlined by the compiler and you can't take their address, so we
        # need to look for them differently. On nice compilers like clang, we
        # can just directly use the __has_builtin() macro.
        fargs['no_includes'] = '#include' not in prefix
        t = '''{prefix}
        int main() {{
        #ifdef __has_builtin
            #if !__has_builtin(__builtin_{func})
                #error "__builtin_{func} not found"
            #endif
        #elif ! defined({func})
            /* Check for __builtin_{func} only if no includes were added to the
             * prefix above, which means no definition of {func} can be found.
             * We would always check for this, but we get false positives on
             * MSYS2 if we do. Their toolchain is broken, but we can at least
             * give them a workaround. */
            #if {no_includes:d}
                __builtin_{func};
            #else
                #error "No definition for __builtin_{func} found in the prefix"
            #endif
        #endif
        }}'''
        return self.links(t.format(**fargs), env, extra_args, dependencies)

    def has_members(self, typename, membernames, prefix, env, extra_args=None, dependencies=None):
        if extra_args is None:
            extra_args = []
        fargs = {'prefix': prefix, 'type': typename, 'name': 'foo'}
        # Create code that accesses all members
        members = ''
        for member in membernames:
            members += '{}.{};\n'.format(fargs['name'], member)
        fargs['members'] = members
        t = '''{prefix}
        void bar() {{
            {type} {name};
            {members}
        }};'''
        return self.compiles(t.format(**fargs), env, extra_args, dependencies)

    def has_type(self, typename, prefix, env, extra_args, dependencies=None):
        fargs = {'prefix': prefix, 'type': typename}
        t = '''{prefix}
        void bar() {{
            sizeof({type});
        }};'''
        return self.compiles(t.format(**fargs), env, extra_args, dependencies)

    def symbols_have_underscore_prefix(self, env):
        '''
        Check if the compiler prefixes an underscore to global C symbols
        '''
        symbol_name = b'meson_uscore_prefix'
        code = '''#ifdef __cplusplus
        extern "C" {
        #endif
        void ''' + symbol_name.decode() + ''' () {}
        #ifdef __cplusplus
        }
        #endif
        '''
        args = self.get_cross_extra_flags(env, link=False)
        args += self.get_compiler_check_args()
        n = 'symbols_have_underscore_prefix'
        with self.compile(code, args, 'compile') as p:
            if p.returncode != 0:
                m = 'BUG: Unable to compile {!r} check: {}'
                raise RuntimeError(m.format(n, p.stdo))
            if not os.path.isfile(p.output_name):
                m = 'BUG: Can\'t find compiled test code for {!r} check'
                raise RuntimeError(m.format(n))
            with open(p.output_name, 'rb') as o:
                for line in o:
                    # Check if the underscore form of the symbol is somewhere
                    # in the output file.
                    if b'_' + symbol_name in line:
                        return True
                    # Else, check if the non-underscored form is present
                    elif symbol_name in line:
                        return False
        raise RuntimeError('BUG: {!r} check failed unexpectedly'.format(n))

    def find_library(self, libname, env, extra_dirs):
        # First try if we can just add the library as -l.
        code = '''int main(int argc, char **argv) {
    return 0;
}
        '''
        if extra_dirs and isinstance(extra_dirs, str):
            extra_dirs = [extra_dirs]
        # Gcc + co seem to prefer builtin lib dirs to -L dirs.
        # Only try to find std libs if no extra dirs specified.
        if not extra_dirs:
            args = ['-l' + libname]
            if self.links(code, env, extra_args=args):
                return args
        # Not found? Try to find the library file itself.
        extra_dirs += self.get_library_dirs()
        suffixes = ['so', 'dylib', 'lib', 'dll', 'a']
        for d in extra_dirs:
            for suffix in suffixes:
                trial = os.path.join(d, 'lib' + libname + '.' + suffix)
                if os.path.isfile(trial):
                    return [trial]
                trial2 = os.path.join(d, libname + '.' + suffix)
                if os.path.isfile(trial2):
                    return [trial2]
        return None

    def thread_flags(self):
        return ['-pthread']

    def thread_link_flags(self):
        return ['-pthread']

    def has_multi_arguments(self, args, env):
        return self.compiles('int i;\n', env, extra_args=args)

class CPPCompiler(CCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrap):
        # If a child ObjCPP class has already set it, don't set it ourselves
        if not hasattr(self, 'language'):
            self.language = 'cpp'
        CCompiler.__init__(self, exelist, version, is_cross, exe_wrap)

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

class ObjCCompiler(CCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrap):
        self.language = 'objc'
        CCompiler.__init__(self, exelist, version, is_cross, exe_wrap)

    def sanity_check(self, work_dir, environment):
        # TODO try to use sanity_check_impl instead of duplicated code
        source_name = os.path.join(work_dir, 'sanitycheckobjc.m')
        binary_name = os.path.join(work_dir, 'sanitycheckobjc')
        extra_flags = self.get_cross_extra_flags(environment, link=False)
        if self.is_cross:
            extra_flags += self.get_compile_only_args()
        with open(source_name, 'w') as ofile:
            ofile.write('#import<stdio.h>\n'
                        'int main(int argc, char **argv) { return 0; }\n')
        pc = subprocess.Popen(self.exelist + extra_flags + [source_name, '-o', binary_name])
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('ObjC compiler %s can not compile programs.' % self.name_string())
        if self.is_cross:
            # Can't check if the binaries run so we have to assume they do
            return
        pe = subprocess.Popen(binary_name)
        pe.wait()
        if pe.returncode != 0:
            raise EnvironmentException('Executables created by ObjC compiler %s are not runnable.' % self.name_string())

class ObjCPPCompiler(CPPCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrap):
        self.language = 'objcpp'
        CPPCompiler.__init__(self, exelist, version, is_cross, exe_wrap)

    def sanity_check(self, work_dir, environment):
        # TODO try to use sanity_check_impl instead of duplicated code
        source_name = os.path.join(work_dir, 'sanitycheckobjcpp.mm')
        binary_name = os.path.join(work_dir, 'sanitycheckobjcpp')
        extra_flags = self.get_cross_extra_flags(environment, link=False)
        if self.is_cross:
            extra_flags += self.get_compile_only_args()
        with open(source_name, 'w') as ofile:
            ofile.write('#import<stdio.h>\n'
                        'class MyClass;'
                        'int main(int argc, char **argv) { return 0; }\n')
        pc = subprocess.Popen(self.exelist + extra_flags + [source_name, '-o', binary_name])
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('ObjC++ compiler %s can not compile programs.' % self.name_string())
        if self.is_cross:
            # Can't check if the binaries run so we have to assume they do
            return
        pe = subprocess.Popen(binary_name)
        pe.wait()
        if pe.returncode != 0:
            raise EnvironmentException('Executables created by ObjC++ compiler %s are not runnable.' % self.name_string())

class MonoCompiler(Compiler):
    def __init__(self, exelist, version):
        self.language = 'cs'
        super().__init__(exelist, version)
        self.id = 'mono'
        self.monorunner = 'mono'

    def get_output_args(self, fname):
        return ['-out:' + fname]

    def get_link_args(self, fname):
        return ['-r:' + fname]

    def get_soname_args(self, prefix, shlib_name, suffix, path, soversion, is_shared_module):
        return []

    def get_werror_args(self):
        return ['-warnaserror']

    def split_shlib_to_parts(self, fname):
        return None, fname

    def build_rpath_args(self, build_dir, rpath_paths, install_rpath):
        return []

    def get_dependency_gen_args(self, outtarget, outfile):
        return []

    def get_linker_exelist(self):
        return self.exelist[:]

    def get_compile_only_args(self):
        return []

    def get_linker_output_args(self, outputname):
        return []

    def get_coverage_args(self):
        return []

    def get_coverage_link_args(self):
        return []

    def get_std_exe_link_args(self):
        return []

    def get_include_args(self, path):
        return []

    def get_pic_args(self):
        return []

    def name_string(self):
        return ' '.join(self.exelist)

    def get_pch_use_args(self, pch_dir, header):
        return []

    def get_pch_name(self, header_name):
        return ''

    def sanity_check(self, work_dir, environment):
        src = 'sanity.cs'
        obj = 'sanity.exe'
        source_name = os.path.join(work_dir, src)
        with open(source_name, 'w') as ofile:
            ofile.write('''public class Sanity {
    static public void Main () {
    }
}
''')
        pc = subprocess.Popen(self.exelist + [src], cwd=work_dir)
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('Mono compiler %s can not compile programs.' % self.name_string())
        cmdlist = [self.monorunner, obj]
        pe = subprocess.Popen(cmdlist, cwd=work_dir)
        pe.wait()
        if pe.returncode != 0:
            raise EnvironmentException('Executables created by Mono compiler %s are not runnable.' % self.name_string())

    def needs_static_linker(self):
        return False

    def get_buildtype_args(self, buildtype):
        return mono_buildtype_args[buildtype]

class JavaCompiler(Compiler):
    def __init__(self, exelist, version):
        self.language = 'java'
        super().__init__(exelist, version)
        self.id = 'unknown'
        self.javarunner = 'java'

    def get_soname_args(self, prefix, shlib_name, suffix, path, soversion, is_shared_module):
        return []

    def get_werror_args(self):
        return ['-Werror']

    def split_shlib_to_parts(self, fname):
        return None, fname

    def build_rpath_args(self, build_dir, rpath_paths, install_rpath):
        return []

    def get_dependency_gen_args(self, outtarget, outfile):
        return []

    def get_linker_exelist(self):
        return self.exelist[:]

    def get_compile_only_args(self):
        return []

    def get_output_args(self, subdir):
        if subdir == '':
            subdir = './'
        return ['-d', subdir, '-s', subdir]

    def get_linker_output_args(self, outputname):
        return []

    def get_coverage_args(self):
        return []

    def get_coverage_link_args(self):
        return []

    def get_std_exe_link_args(self):
        return []

    def get_include_args(self, path):
        return []

    def get_pic_args(self):
        return []

    def name_string(self):
        return ' '.join(self.exelist)

    def get_pch_use_args(self, pch_dir, header):
        return []

    def get_pch_name(self, header_name):
        return ''

    def get_buildtype_args(self, buildtype):
        return java_buildtype_args[buildtype]

    def sanity_check(self, work_dir, environment):
        src = 'SanityCheck.java'
        obj = 'SanityCheck'
        source_name = os.path.join(work_dir, src)
        with open(source_name, 'w') as ofile:
            ofile.write('''class SanityCheck {
  public static void main(String[] args) {
    int i;
  }
}
''')
        pc = subprocess.Popen(self.exelist + [src], cwd=work_dir)
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('Java compiler %s can not compile programs.' % self.name_string())
        runner = shutil.which(self.javarunner)
        if runner:
            cmdlist = [runner, obj]
            pe = subprocess.Popen(cmdlist, cwd=work_dir)
            pe.wait()
            if pe.returncode != 0:
                raise EnvironmentException('Executables created by Java compiler %s are not runnable.' % self.name_string())
        else:
            m = "Java Virtual Machine wasn't found, but it's needed by Meson. " \
                "Please install a JRE.\nIf you have specific needs where this " \
                "requirement doesn't make sense, please open a bug at " \
                "https://github.com/mesonbuild/meson/issues/new and tell us " \
                "all about it."
            raise EnvironmentException(m)

    def needs_static_linker(self):
        return False

class ValaCompiler(Compiler):
    def __init__(self, exelist, version):
        self.language = 'vala'
        super().__init__(exelist, version)
        self.version = version
        self.id = 'valac'
        self.is_cross = False

    def name_string(self):
        return ' '.join(self.exelist)

    def needs_static_linker(self):
        return False # Because compiles into C.

    def get_output_args(self, target):
        return ['-o', target]

    def get_compile_only_args(self):
        return ['-C']

    def get_pic_args(self):
        return []

    def get_always_args(self):
        return ['-C']

    def get_warn_args(self, warning_level):
        return []

    def get_no_warn_args(self):
        return ['--disable-warnings']

    def get_werror_args(self):
        return ['--fatal-warnings']

    def sanity_check(self, work_dir, environment):
        code = 'class MesonSanityCheck : Object { }'
        args = self.get_cross_extra_flags(environment, link=False)
        with self.compile(code, args, 'compile') as p:
            if p.returncode != 0:
                msg = 'Vala compiler {!r} can not compile programs' \
                      ''.format(self.name_string())
                raise EnvironmentException(msg)

    def get_buildtype_args(self, buildtype):
        if buildtype == 'debug' or buildtype == 'debugoptimized' or buildtype == 'minsize':
            return ['--debug']
        return []

    def find_library(self, libname, env, extra_dirs):
        if extra_dirs and isinstance(extra_dirs, str):
            extra_dirs = [extra_dirs]
        # Valac always looks in the default vapi dir, so only search there if
        # no extra dirs are specified.
        if not extra_dirs:
            code = 'class MesonFindLibrary : Object { }'
            vapi_args = ['--pkg', libname]
            args = self.get_cross_extra_flags(env, link=False)
            args += vapi_args
            with self.compile(code, args, 'compile') as p:
                if p.returncode == 0:
                    return vapi_args
        # Not found? Try to find the vapi file itself.
        for d in extra_dirs:
            vapi = os.path.join(d, libname + '.vapi')
            if os.path.isfile(vapi):
                return [vapi]
        mlog.debug('Searched {!r} and {!r} wasn\'t found'.format(extra_dirs, libname))
        return None

class RustCompiler(Compiler):
    def __init__(self, exelist, version):
        self.language = 'rust'
        super().__init__(exelist, version)
        self.id = 'rustc'

    def needs_static_linker(self):
        return False

    def name_string(self):
        return ' '.join(self.exelist)

    def sanity_check(self, work_dir, environment):
        source_name = os.path.join(work_dir, 'sanity.rs')
        output_name = os.path.join(work_dir, 'rusttest')
        with open(source_name, 'w') as ofile:
            ofile.write('''fn main() {
}
''')
        pc = subprocess.Popen(self.exelist + ['-o', output_name, source_name], cwd=work_dir)
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('Rust compiler %s can not compile programs.' % self.name_string())
        if subprocess.call(output_name) != 0:
            raise EnvironmentException('Executables created by Rust compiler %s are not runnable.' % self.name_string())

    def get_dependency_gen_args(self, outfile):
        return ['--dep-info', outfile]

    def get_buildtype_args(self, buildtype):
        return rust_buildtype_args[buildtype]

class SwiftCompiler(Compiler):
    def __init__(self, exelist, version):
        self.language = 'swift'
        super().__init__(exelist, version)
        self.version = version
        self.id = 'llvm'
        self.is_cross = False

    def get_linker_exelist(self):
        return self.exelist[:]

    def name_string(self):
        return ' '.join(self.exelist)

    def needs_static_linker(self):
        return True

    def get_werror_args(self):
        return ['--fatal-warnings']

    def get_dependency_gen_args(self, outtarget, outfile):
        return ['-emit-dependencies']

    def depfile_for_object(self, objfile):
        return os.path.splitext(objfile)[0] + '.' + self.get_depfile_suffix()

    def get_depfile_suffix(self):
        return 'd'

    def get_output_args(self, target):
        return ['-o', target]

    def get_linker_output_args(self, target):
        return ['-o', target]

    def get_header_import_args(self, headername):
        return ['-import-objc-header', headername]

    def get_warn_args(self, level):
        return []

    def get_buildtype_args(self, buildtype):
        return swift_buildtype_args[buildtype]

    def get_buildtype_linker_args(self, buildtype):
        return []

    def get_std_exe_link_args(self):
        return ['-emit-executable']

    def get_module_args(self, modname):
        return ['-module-name', modname]

    def get_mod_gen_args(self):
        return ['-emit-module']

    def build_rpath_args(self, *args):
        return [] # FIXME

    def get_include_args(self, dirname):
        return ['-I' + dirname]

    def get_compile_only_args(self):
        return ['-c']

    def sanity_check(self, work_dir, environment):
        src = 'swifttest.swift'
        source_name = os.path.join(work_dir, src)
        output_name = os.path.join(work_dir, 'swifttest')
        with open(source_name, 'w') as ofile:
            ofile.write('''print("Swift compilation is working.")
''')
        extra_flags = self.get_cross_extra_flags(environment, link=True)
        pc = subprocess.Popen(self.exelist + extra_flags + ['-emit-executable', '-o', output_name, src], cwd=work_dir)
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('Swift compiler %s can not compile programs.' % self.name_string())
        if subprocess.call(output_name) != 0:
            raise EnvironmentException('Executables created by Swift compiler %s are not runnable.' % self.name_string())

class DCompiler(Compiler):
    def __init__(self, exelist, version, is_cross):
        self.language = 'd'
        super().__init__(exelist, version)
        self.id = 'unknown'
        self.is_cross = is_cross

    def sanity_check(self, work_dir, environment):
        source_name = os.path.join(work_dir, 'sanity.d')
        output_name = os.path.join(work_dir, 'dtest')
        with open(source_name, 'w') as ofile:
            ofile.write('''void main() {
}
''')
        pc = subprocess.Popen(self.exelist + self.get_output_args(output_name) + [source_name], cwd=work_dir)
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('D compiler %s can not compile programs.' % self.name_string())
        if subprocess.call(output_name) != 0:
            raise EnvironmentException('Executables created by D compiler %s are not runnable.' % self.name_string())

    def needs_static_linker(self):
        return True

    def name_string(self):
        return ' '.join(self.exelist)

    def get_linker_exelist(self):
        return self.exelist[:]

    def get_preprocess_only_args(self):
        return ['-E']

    def get_compile_only_args(self):
        return ['-c']

    def depfile_for_object(self, objfile):
        return objfile + '.' + self.get_depfile_suffix()

    def get_depfile_suffix(self):
        return 'dep'

    def get_pic_args(self):
        return ['-fPIC']

    def get_std_shared_lib_link_args(self):
        return ['-shared']

    def get_soname_args(self, prefix, shlib_name, suffix, path, soversion, is_shared_module):
        # FIXME: Make this work for Windows, MacOS and cross-compiling
        return get_gcc_soname_args(GCC_STANDARD, prefix, shlib_name, suffix, path, soversion, is_shared_module)

    def get_unittest_args(self):
        return ['-unittest']

    def get_buildtype_linker_args(self, buildtype):
        return []

    def get_std_exe_link_args(self):
        return []

    def build_rpath_args(self, build_dir, from_dir, rpath_paths, install_rpath):
        # This method is to be used by LDC and DMD.
        # GDC can deal with the verbatim flags.
        if not rpath_paths and not install_rpath:
            return []
        paths = ':'.join([os.path.join(build_dir, p) for p in rpath_paths])
        if len(paths) < len(install_rpath):
            padding = 'X' * (len(install_rpath) - len(paths))
            if not paths:
                paths = padding
            else:
                paths = paths + ':' + padding
        return ['-L-rpath={}'.format(paths)]

    def _get_compiler_check_args(self, env, extra_args, dependencies, mode='compile'):
        if extra_args is None:
            extra_args = []
        elif isinstance(extra_args, str):
            extra_args = [extra_args]
        if dependencies is None:
            dependencies = []
        elif not isinstance(dependencies, list):
            dependencies = [dependencies]
        # Collect compiler arguments
        args = CompilerArgs(self)
        for d in dependencies:
            # Add compile flags needed by dependencies
            args += d.get_compile_args()
            if mode == 'link':
                # Add link flags needed to find dependencies
                args += d.get_link_args()

        if mode == 'compile':
            # Add DFLAGS from the env
            args += env.coredata.external_args[self.language]
        elif mode == 'link':
            # Add LDFLAGS from the env
            args += env.coredata.external_link_args[self.language]
        # extra_args must override all other arguments, so we add them last
        args += extra_args
        return args

    def compiles(self, code, env, extra_args=None, dependencies=None, mode='compile'):
        args = self._get_compiler_check_args(env, extra_args, dependencies, mode)

        with self.compile(code, args, mode) as p:
            return p.returncode == 0

    def has_multi_arguments(self, args, env):
        return self.compiles('int i;\n', env, extra_args=args)

    @classmethod
    def translate_args_to_nongnu(cls, args):
        dcargs = []
        # Translate common arguments to flags the LDC/DMD compilers
        # can understand.
        # The flags might have been added by pkg-config files,
        # and are therefore out of the user's control.
        for arg in args:
            if arg == '-pthread':
                continue
            if arg.startswith('-Wl,'):
                linkargs = arg[arg.index(',') + 1:].split(',')
                for la in linkargs:
                    dcargs.append('-L' + la.strip())
                continue
            elif arg.startswith('-l'):
                # translate library link flag
                dcargs.append('-L' + arg)
                continue
            elif arg.startswith('-L/') or arg.startswith('-L./'):
                # we need to handle cases where -L is set by e.g. a pkg-config
                # setting to select a linker search path. We can however not
                # unconditionally prefix '-L' with '-L' because the user might
                # have set this flag too to do what it is intended to for this
                # compiler (pass flag through to the linker)
                # Hence, we guess here whether the flag was intended to pass
                # a linker search path.
                dcargs.append('-L' + arg)
                continue
            dcargs.append(arg)

        return dcargs

class GnuDCompiler(DCompiler):
    def __init__(self, exelist, version, is_cross):
        DCompiler.__init__(self, exelist, version, is_cross)
        self.id = 'gcc'
        default_warn_args = ['-Wall', '-Wdeprecated']
        self.warn_args = {'1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}
        self.base_options = ['b_colorout', 'b_sanitize', 'b_staticpic']

    def get_colorout_args(self, colortype):
        if mesonlib.version_compare(self.version, '>=4.9.0'):
            return gnu_color_args[colortype][:]
        return []

    def get_dependency_gen_args(self, outtarget, outfile):
        return ['-fmake-deps=' + outfile]

    def get_output_args(self, target):
        return ['-o', target]

    def get_linker_output_args(self, target):
        return ['-o', target]

    def get_include_args(self, path, is_system):
        return ['-I' + path]

    def get_warn_args(self, level):
        return self.warn_args[level]

    def get_werror_args(self):
        return ['-Werror']

    def get_linker_search_args(self, dirname):
        return ['-L' + dirname]

    def get_buildtype_args(self, buildtype):
        return d_gdc_buildtype_args[buildtype]

    def build_rpath_args(self, build_dir, from_dir, rpath_paths, install_rpath):
        return self.build_unix_rpath_args(build_dir, from_dir, rpath_paths, install_rpath)

    def get_unittest_args(self):
        return ['-funittest']

class LLVMDCompiler(DCompiler):
    def __init__(self, exelist, version, is_cross):
        DCompiler.__init__(self, exelist, version, is_cross)
        self.id = 'llvm'
        self.base_options = ['b_coverage', 'b_colorout']

    def get_colorout_args(self, colortype):
        if colortype == 'always':
            return ['-enable-color']
        return []

    def get_dependency_gen_args(self, outtarget, outfile):
        # LDC using the -deps flag returns a non-Makefile dependency-info file, which
        # the backends can not use. So we disable this feature for now.
        return []

    def get_output_args(self, target):
        return ['-of', target]

    def get_linker_output_args(self, target):
        return ['-of', target]

    def get_include_args(self, path, is_system):
        return ['-I' + path]

    def get_warn_args(self, level):
        if level == '2' or level == '3':
            return ['-wi', '-dw']
        else:
            return ['-wi']

    def get_werror_args(self):
        return ['-w']

    def get_coverage_args(self):
        return ['-cov']

    def get_buildtype_args(self, buildtype):
        return d_ldc_buildtype_args[buildtype]

    def get_pic_args(self):
        return ['-relocation-model=pic']

    def get_linker_search_args(self, dirname):
        # -L is recognized as "add this to the search path" by the linker,
        # while the compiler recognizes it as "pass to linker". So, the first
        # -L is for the compiler, telling it to pass the second -L to the linker.
        return ['-L-L' + dirname]

    @classmethod
    def unix_args_to_native(cls, args):
        return cls.translate_args_to_nongnu(args)

class DmdDCompiler(DCompiler):
    def __init__(self, exelist, version, is_cross):
        DCompiler.__init__(self, exelist, version, is_cross)
        self.id = 'dmd'
        self.base_options = ['b_coverage', 'b_colorout']

    def get_colorout_args(self, colortype):
        if colortype == 'always':
            return ['-color=on']
        return []

    def get_dependency_gen_args(self, outtarget, outfile):
        # LDC using the -deps flag returns a non-Makefile dependency-info file, which
        # the backends can not use. So we disable this feature for now.
        return []

    def get_output_args(self, target):
        return ['-of' + target]

    def get_werror_args(self):
        return ['-w']

    def get_linker_output_args(self, target):
        return ['-of' + target]

    def get_include_args(self, path, is_system):
        return ['-I' + path]

    def get_warn_args(self, level):
        return ['-wi']

    def get_coverage_args(self):
        return ['-cov']

    def get_linker_search_args(self, dirname):
        # -L is recognized as "add this to the search path" by the linker,
        # while the compiler recognizes it as "pass to linker". So, the first
        # -L is for the compiler, telling it to pass the second -L to the linker.
        return ['-L-L' + dirname]

    def get_buildtype_args(self, buildtype):
        return d_dmd_buildtype_args[buildtype]

    def get_std_shared_lib_link_args(self):
        return ['-shared', '-defaultlib=libphobos2.so']

    @classmethod
    def unix_args_to_native(cls, args):
        return cls.translate_args_to_nongnu(args)

class VisualStudioCCompiler(CCompiler):
    std_warn_args = ['/W3']
    std_opt_args = ['/O2']

    def __init__(self, exelist, version, is_cross, exe_wrap):
        CCompiler.__init__(self, exelist, version, is_cross, exe_wrap)
        self.id = 'msvc'
        # /showIncludes is needed for build dependency tracking in Ninja
        # See: https://ninja-build.org/manual.html#_deps
        self.always_args = ['/nologo', '/showIncludes']
        self.warn_args = {'1': ['/W2'],
                          '2': ['/W3'],
                          '3': ['/W4']}
        self.base_options = ['b_pch'] # FIXME add lto, pgo and the like

    # Override CCompiler.get_always_args
    def get_always_args(self):
        return self.always_args

    def get_linker_debug_crt_args(self):
        """
        Arguments needed to select a debug crt for the linker

        Sometimes we need to manually select the CRT (C runtime) to use with
        MSVC. One example is when trying to link with static libraries since
        MSVC won't auto-select a CRT for us in that case and will error out
        asking us to select one.
        """
        return ['/MDd']

    def get_buildtype_args(self, buildtype):
        return msvc_buildtype_args[buildtype]

    def get_buildtype_linker_args(self, buildtype):
        return msvc_buildtype_linker_args[buildtype]

    def get_pch_suffix(self):
        return 'pch'

    def get_pch_name(self, header):
        chopped = os.path.split(header)[-1].split('.')[:-1]
        chopped.append(self.get_pch_suffix())
        pchname = '.'.join(chopped)
        return pchname

    def get_pch_use_args(self, pch_dir, header):
        base = os.path.split(header)[-1]
        pchname = self.get_pch_name(header)
        return ['/FI' + base, '/Yu' + base, '/Fp' + os.path.join(pch_dir, pchname)]

    def get_preprocess_only_args(self):
        return ['/EP']

    def get_compile_only_args(self):
        return ['/c']

    def get_no_optimization_args(self):
        return ['/Od']

    def get_output_args(self, target):
        if target.endswith('.exe'):
            return ['/Fe' + target]
        return ['/Fo' + target]

    def get_dependency_gen_args(self, outtarget, outfile):
        return []

    def get_linker_exelist(self):
        return ['link'] # FIXME, should have same path as compiler.

    def get_linker_always_args(self):
        return ['/nologo']

    def get_linker_output_args(self, outputname):
        return ['/OUT:' + outputname]

    def get_linker_search_args(self, dirname):
        return ['/LIBPATH:' + dirname]

    def get_pic_args(self):
        return [] # PIC is handled by the loader on Windows

    def get_std_shared_lib_link_args(self):
        return ['/DLL']

    def gen_vs_module_defs_args(self, defsfile):
        if not isinstance(defsfile, str):
            raise RuntimeError('Module definitions file should be str')
        # With MSVC, DLLs only export symbols that are explicitly exported,
        # so if a module defs file is specified, we use that to export symbols
        return ['/DEF:' + defsfile]

    def gen_pch_args(self, header, source, pchname):
        objname = os.path.splitext(pchname)[0] + '.obj'
        return objname, ['/Yc' + header, '/Fp' + pchname, '/Fo' + objname]

    def gen_import_library_args(self, implibname):
        "The name of the outputted import library"
        return ['/IMPLIB:' + implibname]

    def build_rpath_args(self, build_dir, from_dir, rpath_paths, install_rpath):
        return []

    # FIXME, no idea what these should be.
    def thread_flags(self):
        return []

    def thread_link_flags(self):
        return []

    def get_options(self):
        return {'c_winlibs': coredata.UserStringArrayOption('c_winlibs',
                                                            'Windows libs to link against.',
                                                            msvc_winlibs)
                }

    def get_option_link_args(self, options):
        return options['c_winlibs'].value[:]

    @classmethod
    def unix_args_to_native(cls, args):
        result = []
        for i in args:
            # -mms-bitfields is specific to MinGW-GCC
            # -pthread is only valid for GCC
            if i in ('-mms-bitfields', '-pthread'):
                continue
            if i.startswith('-L'):
                i = '/LIBPATH:' + i[2:]
            # Translate GNU-style -lfoo library name to the import library
            elif i.startswith('-l'):
                name = i[2:]
                if name in ('m', 'c', 'pthread'):
                    # With MSVC, these are provided by the C runtime which is
                    # linked in by default
                    continue
                else:
                    i = name + '.lib'
            # -pthread in link flags is only used on Linux
            elif i == '-pthread':
                continue
            result.append(i)
        return result

    def get_werror_args(self):
        return ['/WX']

    def get_include_args(self, path, is_system):
        if path == '':
            path = '.'
        # msvc does not have a concept of system header dirs.
        return ['-I' + path]

    # Visual Studio is special. It ignores some arguments it does not
    # understand and you can't tell it to error out on those.
    # http://stackoverflow.com/questions/15259720/how-can-i-make-the-microsoft-c-compiler-treat-unknown-flags-as-errors-rather-t
    def has_multi_arguments(self, args, env):
        warning_text = '9002'
        code = 'int i;\n'
        (fd, srcname) = tempfile.mkstemp(suffix='.' + self.default_suffix)
        os.close(fd)
        with open(srcname, 'w') as ofile:
            ofile.write(code)
        # Read c_args/cpp_args/etc from the cross-info file (if needed)
        extra_args = self.get_cross_extra_flags(env, link=False)
        extra_args += self.get_compile_only_args()
        commands = self.exelist + args + extra_args + [srcname]
        mlog.debug('Running VS compile:')
        mlog.debug('Command line: ', ' '.join(commands))
        mlog.debug('Code:\n', code)
        p, stdo, stde = Popen_safe(commands, cwd=os.path.split(srcname)[0])
        if p.returncode != 0:
            return False
        return not(warning_text in stde or warning_text in stdo)

    def get_compile_debugfile_args(self, rel_obj, pch=False):
        pdbarr = rel_obj.split('.')[:-1]
        pdbarr += ['pdb']
        args = ['/Fd' + '.'.join(pdbarr)]
        # When generating a PDB file with PCH, all compile commands write
        # to the same PDB file. Hence, we need to serialize the PDB
        # writes using /FS since we do parallel builds. This slows down the
        # build obviously, which is why we only do this when PCH is on.
        # This was added in Visual Studio 2013 (MSVC 18.0). Before that it was
        # always on: https://msdn.microsoft.com/en-us/library/dn502518.aspx
        if pch and mesonlib.version_compare(self.version, '>=18.0'):
            args = ['/FS'] + args
        return args

    def get_link_debugfile_args(self, targetfile):
        pdbarr = targetfile.split('.')[:-1]
        pdbarr += ['pdb']
        return ['/DEBUG', '/PDB:' + '.'.join(pdbarr)]

    def get_link_whole_for(self, args):
        # Only since VS2015
        if not isinstance(args, list):
            args = [args]
        return ['/WHOLEARCHIVE:' + x for x in args]


class VisualStudioCPPCompiler(VisualStudioCCompiler, CPPCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrap):
        self.language = 'cpp'
        CPPCompiler.__init__(self, exelist, version, is_cross, exe_wrap)
        VisualStudioCCompiler.__init__(self, exelist, version, is_cross, exe_wrap)
        self.base_options = ['b_pch'] # FIXME add lto, pgo and the like

    def get_options(self):
        return {'cpp_eh': coredata.UserComboOption('cpp_eh',
                                                   'C++ exception handling type.',
                                                   ['none', 'a', 's', 'sc'],
                                                   'sc'),
                'cpp_winlibs': coredata.UserStringArrayOption('cpp_winlibs',
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

GCC_STANDARD = 0
GCC_OSX = 1
GCC_MINGW = 2
GCC_CYGWIN = 3

CLANG_STANDARD = 0
CLANG_OSX = 1
CLANG_WIN = 2
# Possibly clang-cl?

ICC_STANDARD = 0
ICC_OSX = 1
ICC_WIN = 2

def get_gcc_soname_args(gcc_type, prefix, shlib_name, suffix, path, soversion, is_shared_module):
    if soversion is None:
        sostr = ''
    else:
        sostr = '.' + soversion
    if gcc_type in (GCC_STANDARD, GCC_MINGW, GCC_CYGWIN):
        # Might not be correct for mingw but seems to work.
        return ['-Wl,-soname,%s%s.%s%s' % (prefix, shlib_name, suffix, sostr)]
    elif gcc_type == GCC_OSX:
        if is_shared_module:
            return []
        return ['-install_name', os.path.join(path, 'lib' + shlib_name + '.dylib')]
    else:
        raise RuntimeError('Not implemented yet.')

def get_compiler_is_linuxlike(compiler):
    if (getattr(compiler, 'gcc_type', None) == GCC_STANDARD) or \
       (getattr(compiler, 'clang_type', None) == CLANG_STANDARD) or \
       (getattr(compiler, 'icc_type', None) == ICC_STANDARD):
        return True
    return False

def get_compiler_uses_gnuld(c):
    # FIXME: Perhaps we should detect the linker in the environment?
    # FIXME: Assumes that *BSD use GNU ld, but they might start using lld soon
    if (getattr(c, 'gcc_type', None) in (GCC_STANDARD, GCC_MINGW, GCC_CYGWIN)) or \
       (getattr(c, 'clang_type', None) in (CLANG_STANDARD, CLANG_WIN)) or \
       (getattr(c, 'icc_type', None) in (ICC_STANDARD, ICC_WIN)):
        return True
    return False

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


class GnuCompiler:
    # Functionality that is common to all GNU family compilers.
    def __init__(self, gcc_type, defines):
        self.id = 'gcc'
        self.gcc_type = gcc_type
        self.defines = defines or {}
        self.base_options = ['b_pch', 'b_lto', 'b_pgo', 'b_sanitize', 'b_coverage',
                             'b_colorout', 'b_ndebug', 'b_staticpic']
        if self.gcc_type != GCC_OSX:
            self.base_options.append('b_lundef')
            self.base_options.append('b_asneeded')
        # All GCC backends can do assembly
        self.can_compile_suffixes.add('s')

    def get_colorout_args(self, colortype):
        if mesonlib.version_compare(self.version, '>=4.9.0'):
            return gnu_color_args[colortype][:]
        return []

    def get_warn_args(self, level):
        args = super().get_warn_args(level)
        if mesonlib.version_compare(self.version, '<4.8.0') and '-Wpedantic' in args:
            # -Wpedantic was added in 4.8.0
            # https://gcc.gnu.org/gcc-4.8/changes.html
            args[args.index('-Wpedantic')] = '-pedantic'
        return args

    def has_builtin_define(self, define):
        return define in self.defines

    def get_builtin_define(self, define):
        if define in self.defines:
            return self.defines[define]

    def get_pic_args(self):
        if self.gcc_type in (GCC_CYGWIN, GCC_MINGW, GCC_OSX):
            return [] # On Window and OS X, pic is always on.
        return ['-fPIC']

    def get_buildtype_args(self, buildtype):
        return gnulike_buildtype_args[buildtype]

    def get_buildtype_linker_args(self, buildtype):
        if self.gcc_type == GCC_OSX:
            return apple_buildtype_linker_args[buildtype]
        return gnulike_buildtype_linker_args[buildtype]

    def get_pch_suffix(self):
        return 'gch'

    def split_shlib_to_parts(self, fname):
        return os.path.split(fname)[0], fname

    def get_soname_args(self, prefix, shlib_name, suffix, path, soversion, is_shared_module):
        return get_gcc_soname_args(self.gcc_type, prefix, shlib_name, suffix, path, soversion, is_shared_module)

    def get_std_shared_lib_link_args(self):
        if self.gcc_type == GCC_OSX:
            return ['-bundle']
        return ['-shared']

    def get_link_whole_for(self, args):
        return ['-Wl,--whole-archive'] + args + ['-Wl,--no-whole-archive']

    def gen_vs_module_defs_args(self, defsfile):
        if not isinstance(defsfile, str):
            raise RuntimeError('Module definitions file should be str')
        # On Windows targets, .def files may be specified on the linker command
        # line like an object file.
        if self.gcc_type in (GCC_CYGWIN, GCC_MINGW):
            return [defsfile]
        # For other targets, discard the .def file.
        return []

    def get_gui_app_args(self):
        if self.gcc_type in (GCC_CYGWIN, GCC_MINGW):
            return ['-mwindows']
        return []

class GnuCCompiler(GnuCompiler, CCompiler):
    def __init__(self, exelist, version, gcc_type, is_cross, exe_wrapper=None, defines=None):
        CCompiler.__init__(self, exelist, version, is_cross, exe_wrapper)
        GnuCompiler.__init__(self, gcc_type, defines)
        default_warn_args = ['-Wall', '-Winvalid-pch']
        self.warn_args = {'1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}

    def get_options(self):
        opts = {'c_std': coredata.UserComboOption('c_std', 'C language standard to use',
                                                  ['none', 'c89', 'c99', 'c11',
                                                   'gnu89', 'gnu99', 'gnu11'],
                                                  'none')}
        if self.gcc_type == GCC_MINGW:
            opts.update({
                'c_winlibs': coredata.UserStringArrayOption('c_winlibs', 'Standard Win libraries to link against',
                                                            gnu_winlibs), })
        return opts

    def get_option_compile_args(self, options):
        args = []
        std = options['c_std']
        if std.value != 'none':
            args.append('-std=' + std.value)
        return args

    def get_option_link_args(self, options):
        if self.gcc_type == GCC_MINGW:
            return options['c_winlibs'].value[:]
        return []

    def get_std_shared_lib_link_args(self):
        return ['-shared']


class GnuCPPCompiler(GnuCompiler, CPPCompiler):

    def __init__(self, exelist, version, gcc_type, is_cross, exe_wrap, defines):
        CPPCompiler.__init__(self, exelist, version, is_cross, exe_wrap)
        GnuCompiler.__init__(self, gcc_type, defines)
        default_warn_args = ['-Wall', '-Winvalid-pch', '-Wnon-virtual-dtor']
        self.warn_args = {'1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}

    def get_options(self):
        opts = {'cpp_std': coredata.UserComboOption('cpp_std', 'C++ language standard to use',
                                                    ['none', 'c++03', 'c++11', 'c++14', 'c++1z',
                                                     'gnu++03', 'gnu++11', 'gnu++14', 'gnu++1z'],
                                                    'none'),
                'cpp_debugstl': coredata.UserBooleanOption('cpp_debugstl',
                                                           'STL debug mode',
                                                           False)}
        if self.gcc_type == GCC_MINGW:
            opts.update({
                'cpp_winlibs': coredata.UserStringArrayOption('cpp_winlibs', 'Standard Win libraries to link against',
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


class GnuObjCCompiler(GnuCompiler, ObjCCompiler):

    def __init__(self, exelist, version, gcc_type, is_cross, exe_wrapper=None, defines=None):
        ObjCCompiler.__init__(self, exelist, version, is_cross, exe_wrapper)
        GnuCompiler.__init__(self, gcc_type, defines)
        default_warn_args = ['-Wall', '-Winvalid-pch']
        self.warn_args = {'1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}

class GnuObjCPPCompiler(GnuCompiler, ObjCPPCompiler):

    def __init__(self, exelist, version, gcc_type, is_cross, exe_wrapper=None, defines=None):
        ObjCPPCompiler.__init__(self, exelist, version, is_cross, exe_wrapper)
        GnuCompiler.__init__(self, gcc_type, defines)
        default_warn_args = ['-Wall', '-Winvalid-pch', '-Wnon-virtual-dtor']
        self.warn_args = {'1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}


class ClangCompiler:
    def __init__(self, clang_type):
        self.id = 'clang'
        self.clang_type = clang_type
        self.base_options = ['b_pch', 'b_lto', 'b_pgo', 'b_sanitize', 'b_coverage',
                             'b_ndebug', 'b_staticpic', 'b_colorout']
        if self.clang_type != CLANG_OSX:
            self.base_options.append('b_lundef')
            self.base_options.append('b_asneeded')
        # All Clang backends can do assembly and LLVM IR
        self.can_compile_suffixes.update(['ll', 's'])

    def get_pic_args(self):
        if self.clang_type in (CLANG_WIN, CLANG_OSX):
            return [] # On Window and OS X, pic is always on.
        return ['-fPIC']

    def get_colorout_args(self, colortype):
        return clang_color_args[colortype][:]

    def get_buildtype_args(self, buildtype):
        return gnulike_buildtype_args[buildtype]

    def get_buildtype_linker_args(self, buildtype):
        if self.clang_type == CLANG_OSX:
            return apple_buildtype_linker_args[buildtype]
        return gnulike_buildtype_linker_args[buildtype]

    def get_pch_suffix(self):
        return 'pch'

    def get_pch_use_args(self, pch_dir, header):
        # Workaround for Clang bug http://llvm.org/bugs/show_bug.cgi?id=15136
        # This flag is internal to Clang (or at least not documented on the man page)
        # so it might change semantics at any time.
        return ['-include-pch', os.path.join(pch_dir, self.get_pch_name(header))]

    def get_soname_args(self, prefix, shlib_name, suffix, path, soversion, is_shared_module):
        if self.clang_type == CLANG_STANDARD:
            gcc_type = GCC_STANDARD
        elif self.clang_type == CLANG_OSX:
            gcc_type = GCC_OSX
        elif self.clang_type == CLANG_WIN:
            gcc_type = GCC_MINGW
        else:
            raise MesonException('Unreachable code when converting clang type to gcc type.')
        return get_gcc_soname_args(gcc_type, prefix, shlib_name, suffix, path, soversion, is_shared_module)

    def has_multi_arguments(self, args, env):
        return super().has_multi_arguments(
            ['-Werror=unknown-warning-option'] + args,
            env)

    def has_function(self, funcname, prefix, env, extra_args=None, dependencies=None):
        if extra_args is None:
            extra_args = []
        # Starting with XCode 8, we need to pass this to force linker
        # visibility to obey OS X and iOS minimum version targets with
        # -mmacosx-version-min, -miphoneos-version-min, etc.
        # https://github.com/Homebrew/homebrew-core/issues/3727
        if self.clang_type == CLANG_OSX and version_compare(self.version, '>=8.0'):
            extra_args.append('-Wl,-no_weak_imports')
        return super().has_function(funcname, prefix, env, extra_args, dependencies)

    def get_std_shared_module_link_args(self):
        if self.clang_type == CLANG_OSX:
            return ['-bundle', '-Wl,-undefined,dynamic_lookup']
        return ['-shared']

    def get_link_whole_for(self, args):
        if self.clang_type == CLANG_OSX:
            result = []
            for a in args:
                result += ['-Wl,-force_load', a]
            return result
        return ['-Wl,--whole-archive'] + args + ['-Wl,--no-whole-archive']


class ClangCCompiler(ClangCompiler, CCompiler):
    def __init__(self, exelist, version, clang_type, is_cross, exe_wrapper=None):
        CCompiler.__init__(self, exelist, version, is_cross, exe_wrapper)
        ClangCompiler.__init__(self, clang_type)
        default_warn_args = ['-Wall', '-Winvalid-pch']
        self.warn_args = {'1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}

    def get_options(self):
        return {'c_std': coredata.UserComboOption('c_std', 'C language standard to use',
                                                  ['none', 'c89', 'c99', 'c11',
                                                   'gnu89', 'gnu99', 'gnu11'],
                                                  'none')}

    def get_option_compile_args(self, options):
        args = []
        std = options['c_std']
        if std.value != 'none':
            args.append('-std=' + std.value)
        return args

    def get_option_link_args(self, options):
        return []


class ClangCPPCompiler(ClangCompiler, CPPCompiler):
    def __init__(self, exelist, version, cltype, is_cross, exe_wrapper=None):
        CPPCompiler.__init__(self, exelist, version, is_cross, exe_wrapper)
        ClangCompiler.__init__(self, cltype)
        default_warn_args = ['-Wall', '-Winvalid-pch', '-Wnon-virtual-dtor']
        self.warn_args = {'1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}

    def get_options(self):
        return {'cpp_std': coredata.UserComboOption('cpp_std', 'C++ language standard to use',
                                                    ['none', 'c++03', 'c++11', 'c++14', 'c++1z',
                                                     'gnu++11', 'gnu++14', 'gnu++1z'],
                                                    'none')}

    def get_option_compile_args(self, options):
        args = []
        std = options['cpp_std']
        if std.value != 'none':
            args.append('-std=' + std.value)
        return args

    def get_option_link_args(self, options):
        return []

class ClangObjCCompiler(ClangCompiler, GnuObjCCompiler):
    def __init__(self, exelist, version, cltype, is_cross, exe_wrapper=None):
        GnuObjCCompiler.__init__(self, exelist, version, cltype, is_cross, exe_wrapper)
        ClangCompiler.__init__(self, cltype)
        self.base_options = ['b_pch', 'b_lto', 'b_pgo', 'b_sanitize', 'b_coverage']

class ClangObjCPPCompiler(ClangCompiler, GnuObjCPPCompiler):
    def __init__(self, exelist, version, cltype, is_cross, exe_wrapper=None):
        GnuObjCPPCompiler.__init__(self, exelist, version, cltype, is_cross, exe_wrapper)
        ClangCompiler.__init__(self, cltype)
        self.base_options = ['b_pch', 'b_lto', 'b_pgo', 'b_sanitize', 'b_coverage']


# Tested on linux for ICC 14.0.3, 15.0.6, 16.0.4, 17.0.1
class IntelCompiler:
    def __init__(self, icc_type):
        self.id = 'intel'
        self.icc_type = icc_type
        self.lang_header = 'none'
        self.base_options = ['b_pch', 'b_lto', 'b_pgo', 'b_sanitize', 'b_coverage',
                             'b_colorout', 'b_ndebug', 'b_staticpic', 'b_lundef', 'b_asneeded']
        # Assembly
        self.can_compile_suffixes.add('s')

    def get_pic_args(self):
        return ['-fPIC']

    def get_buildtype_args(self, buildtype):
        return gnulike_buildtype_args[buildtype]

    def get_buildtype_linker_args(self, buildtype):
        return gnulike_buildtype_linker_args[buildtype]

    def get_pch_suffix(self):
        return 'pchi'

    def get_pch_use_args(self, pch_dir, header):
        return ['-pch', '-pch_dir', os.path.join(pch_dir), '-x',
                self.lang_header, '-include', header, '-x', 'none']

    def get_pch_name(self, header_name):
        return os.path.split(header_name)[-1] + '.' + self.get_pch_suffix()

    def split_shlib_to_parts(self, fname):
        return os.path.split(fname)[0], fname

    def get_soname_args(self, prefix, shlib_name, suffix, path, soversion, is_shared_module):
        if self.icc_type == ICC_STANDARD:
            gcc_type = GCC_STANDARD
        elif self.icc_type == ICC_OSX:
            gcc_type = GCC_OSX
        elif self.icc_type == ICC_WIN:
            gcc_type = GCC_MINGW
        else:
            raise MesonException('Unreachable code when converting icc type to gcc type.')
        return get_gcc_soname_args(gcc_type, prefix, shlib_name, suffix, path, soversion, is_shared_module)

    def get_std_shared_lib_link_args(self):
        # FIXME: Don't know how icc works on OSX
        # if self.icc_type == ICC_OSX:
        #     return ['-bundle']
        return ['-shared']


class IntelCCompiler(IntelCompiler, CCompiler):
    def __init__(self, exelist, version, icc_type, is_cross, exe_wrapper=None):
        CCompiler.__init__(self, exelist, version, is_cross, exe_wrapper)
        IntelCompiler.__init__(self, icc_type)
        self.lang_header = 'c-header'
        default_warn_args = ['-Wall', '-w3', '-diag-disable:remark', '-Wpch-messages']
        self.warn_args = {'1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}

    def get_options(self):
        c_stds = ['c89', 'c99']
        g_stds = ['gnu89', 'gnu99']
        if mesonlib.version_compare(self.version, '>=16.0.0'):
            c_stds += ['c11']
        opts = {'c_std': coredata.UserComboOption('c_std', 'C language standard to use',
                                                  ['none'] + c_stds + g_stds,
                                                  'none')}
        return opts

    def get_option_compile_args(self, options):
        args = []
        std = options['c_std']
        if std.value != 'none':
            args.append('-std=' + std.value)
        return args

    def get_std_shared_lib_link_args(self):
        return ['-shared']

    def has_multi_arguments(self, args, env):
        return super().has_multi_arguments(args + ['-diag-error', '10006'], env)


class IntelCPPCompiler(IntelCompiler, CPPCompiler):
    def __init__(self, exelist, version, icc_type, is_cross, exe_wrap):
        CPPCompiler.__init__(self, exelist, version, is_cross, exe_wrap)
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
        if mesonlib.version_compare(self.version, '>=15.0.0'):
            c_stds += ['c++11', 'c++14']
            g_stds += ['gnu++11']
        if mesonlib.version_compare(self.version, '>=16.0.0'):
            c_stds += ['c++17']
        if mesonlib.version_compare(self.version, '>=17.0.0'):
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


class FortranCompiler(Compiler):
    def __init__(self, exelist, version, is_cross, exe_wrapper=None):
        self.language = 'fortran'
        super().__init__(exelist, version)
        self.is_cross = is_cross
        self.exe_wrapper = exe_wrapper
        # Not really correct but I don't have Fortran compilers to test with. Sorry.
        self.gcc_type = GCC_STANDARD
        self.id = "IMPLEMENTATION CLASSES MUST SET THIS"

    def name_string(self):
        return ' '.join(self.exelist)

    def get_pic_args(self):
        if self.gcc_type in (GCC_CYGWIN, GCC_MINGW, GCC_OSX):
            return [] # On Window and OS X, pic is always on.
        return ['-fPIC']

    def get_std_shared_lib_link_args(self):
        return ['-shared']

    def needs_static_linker(self):
        return True

    def sanity_check(self, work_dir, environment):
        source_name = os.path.join(work_dir, 'sanitycheckf.f90')
        binary_name = os.path.join(work_dir, 'sanitycheckf')
        with open(source_name, 'w') as ofile:
            ofile.write('''program prog
     print *, "Fortran compilation is working."
end program prog
''')
        extra_flags = self.get_cross_extra_flags(environment, link=True)
        pc = subprocess.Popen(self.exelist + extra_flags + [source_name, '-o', binary_name])
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('Compiler %s can not compile programs.' % self.name_string())
        if self.is_cross:
            if self.exe_wrapper is None:
                # Can't check if the binaries run so we have to assume they do
                return
            cmdlist = self.exe_wrapper + [binary_name]
        else:
            cmdlist = [binary_name]
        pe = subprocess.Popen(cmdlist, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        pe.wait()
        if pe.returncode != 0:
            raise EnvironmentException('Executables created by Fortran compiler %s are not runnable.' % self.name_string())

    def get_std_warn_args(self, level):
        return FortranCompiler.std_warn_args

    def get_buildtype_args(self, buildtype):
        return gnulike_buildtype_args[buildtype]

    def get_buildtype_linker_args(self, buildtype):
        if mesonlib.is_osx():
            return apple_buildtype_linker_args[buildtype]
        return gnulike_buildtype_linker_args[buildtype]

    def split_shlib_to_parts(self, fname):
        return os.path.split(fname)[0], fname

    def get_soname_args(self, prefix, shlib_name, suffix, path, soversion, is_shared_module):
        return get_gcc_soname_args(self.gcc_type, prefix, shlib_name, suffix, path, soversion, is_shared_module)

    def get_dependency_gen_args(self, outtarget, outfile):
        # Disabled until this is fixed:
        # https://gcc.gnu.org/bugzilla/show_bug.cgi?id=62162
        # return ['-cpp', '-MMD', '-MQ', outtarget]
        return []

    def get_output_args(self, target):
        return ['-o', target]

    def get_preprocess_only_args(self):
        return ['-E']

    def get_compile_only_args(self):
        return ['-c']

    def get_linker_exelist(self):
        return self.exelist[:]

    def get_linker_output_args(self, outputname):
        return ['-o', outputname]

    def get_include_args(self, path, is_system):
        return ['-I' + path]

    def get_module_outdir_args(self, path):
        return ['-J' + path]

    def depfile_for_object(self, objfile):
        return objfile + '.' + self.get_depfile_suffix()

    def get_depfile_suffix(self):
        return 'd'

    def get_std_exe_link_args(self):
        return []

    def build_rpath_args(self, build_dir, from_dir, rpath_paths, install_rpath):
        return self.build_unix_rpath_args(build_dir, from_dir, rpath_paths, install_rpath)

    def module_name_to_filename(self, module_name):
        return module_name.lower() + '.mod'

    def get_warn_args(self, level):
        return ['-Wall']

    def get_no_warn_args(self):
        return ['-w']


class GnuFortranCompiler(FortranCompiler):
    def __init__(self, exelist, version, gcc_type, is_cross, exe_wrapper=None, defines=None):
        super().__init__(exelist, version, is_cross, exe_wrapper=None)
        self.gcc_type = gcc_type
        self.defines = defines or {}
        self.id = 'gcc'

    def has_builtin_define(self, define):
        return define in self.defines

    def get_builtin_define(self, define):
        if define in self.defines:
            return self.defines[define]

    def get_always_args(self):
        return ['-pipe']

    def gen_import_library_args(self, implibname):
        """
        The name of the outputted import library

        Used only on Windows
        """
        return ['-Wl,--out-implib=' + implibname]

class G95FortranCompiler(FortranCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrapper=None):
        super().__init__(exelist, version, is_cross, exe_wrapper=None)
        self.id = 'g95'

    def get_module_outdir_args(self, path):
        return ['-fmod=' + path]

    def get_always_args(self):
        return ['-pipe']

    def get_no_warn_args(self):
        # FIXME: Confirm that there's no compiler option to disable all warnings
        return []

    def gen_import_library_args(self, implibname):
        """
        The name of the outputted import library

        Used only on Windows
        """
        return ['-Wl,--out-implib=' + implibname]

class SunFortranCompiler(FortranCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrapper=None):
        super().__init__(exelist, version, is_cross, exe_wrapper=None)
        self.id = 'sun'

    def get_dependency_gen_args(self, outtarget, outfile):
        return ['-fpp']

    def get_always_args(self):
        return []

    def get_warn_args(self, level):
        return []

    def get_module_outdir_args(self, path):
        return ['-moddir=' + path]

class IntelFortranCompiler(IntelCompiler, FortranCompiler):
    std_warn_args = ['-warn', 'all']

    def __init__(self, exelist, version, is_cross, exe_wrapper=None):
        self.file_suffixes = ('f90', 'f', 'for', 'ftn', 'fpp')
        FortranCompiler.__init__(self, exelist, version, is_cross, exe_wrapper)
        # FIXME: Add support for OS X and Windows in detect_fortran_compiler so
        # we are sent the type of compiler
        IntelCompiler.__init__(self, ICC_STANDARD)
        self.id = 'intel'

    def get_module_outdir_args(self, path):
        return ['-module', path]

    def get_warn_args(self, level):
        return IntelFortranCompiler.std_warn_args

class PathScaleFortranCompiler(FortranCompiler):
    std_warn_args = ['-fullwarn']

    def __init__(self, exelist, version, is_cross, exe_wrapper=None):
        super().__init__(exelist, version, is_cross, exe_wrapper=None)
        self.id = 'pathscale'

    def get_module_outdir_args(self, path):
        return ['-module', path]

    def get_std_warn_args(self, level):
        return PathScaleFortranCompiler.std_warn_args

class PGIFortranCompiler(FortranCompiler):
    std_warn_args = ['-Minform=inform']

    def __init__(self, exelist, version, is_cross, exe_wrapper=None):
        super().__init__(exelist, version, is_cross, exe_wrapper=None)
        self.id = 'pgi'

    def get_module_outdir_args(self, path):
        return ['-module', path]

    def get_warn_args(self, level):
        return PGIFortranCompiler.std_warn_args

    def get_no_warn_args(self):
        return ['-silent']


class Open64FortranCompiler(FortranCompiler):
    std_warn_args = ['-fullwarn']

    def __init__(self, exelist, version, is_cross, exe_wrapper=None):
        super().__init__(exelist, version, is_cross, exe_wrapper=None)
        self.id = 'open64'

    def get_module_outdir_args(self, path):
        return ['-module', path]

    def get_warn_args(self, level):
        return Open64FortranCompiler.std_warn_args

class NAGFortranCompiler(FortranCompiler):
    std_warn_args = []

    def __init__(self, exelist, version, is_cross, exe_wrapper=None):
        super().__init__(exelist, version, is_cross, exe_wrapper=None)
        self.id = 'nagfor'

    def get_module_outdir_args(self, path):
        return ['-mdir', path]

    def get_warn_args(self, level):
        return NAGFortranCompiler.std_warn_args

class StaticLinker:
    pass

class VisualStudioLinker(StaticLinker):
    always_args = ['/NOLOGO']

    def __init__(self, exelist):
        self.exelist = exelist

    def get_exelist(self):
        return self.exelist[:]

    def get_std_link_args(self):
        return []

    def get_buildtype_linker_args(self, buildtype):
        return []

    def get_output_args(self, target):
        return ['/OUT:' + target]

    def get_coverage_link_args(self):
        return []

    def get_always_args(self):
        return VisualStudioLinker.always_args

    def get_linker_always_args(self):
        return VisualStudioLinker.always_args

    def build_rpath_args(self, build_dir, from_dir, rpath_paths, install_rpath):
        return []

    def thread_link_flags(self):
        return []

    def get_option_link_args(self, options):
        return []

    @classmethod
    def unix_args_to_native(cls, args):
        return VisualStudioCCompiler.unix_args_to_native(args)

    def get_link_debugfile_args(self, targetfile):
        # Static libraries do not have PDB files
        return []

class ArLinker(StaticLinker):

    def __init__(self, exelist):
        self.exelist = exelist
        self.id = 'ar'
        pc, stdo = Popen_safe(self.exelist + ['-h'])[0:2]
        # Enable deterministic builds if they are available.
        if '[D]' in stdo:
            self.std_args = ['csrD']
        else:
            self.std_args = ['csr']

    def build_rpath_args(self, build_dir, from_dir, rpath_paths, install_rpath):
        return []

    def get_exelist(self):
        return self.exelist[:]

    def get_std_link_args(self):
        return self.std_args

    def get_output_args(self, target):
        return [target]

    def get_buildtype_linker_args(self, buildtype):
        return []

    def get_linker_always_args(self):
        return []

    def get_coverage_link_args(self):
        return []

    def get_always_args(self):
        return []

    def thread_link_flags(self):
        return []

    def get_option_link_args(self, options):
        return []

    @classmethod
    def unix_args_to_native(cls, args):
        return args[:]

    def get_link_debugfile_args(self, targetfile):
        return []
