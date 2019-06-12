# Copyright 2012-2016 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import configparser, os, shlex, subprocess
import typing

from . import mesonlib
from .mesonlib import EnvironmentException
from . import mlog

_T = typing.TypeVar('_T')


# These classes contains all the data pulled from configuration files (native
# and cross file currently), and also assists with the reading environment
# variables.
#
# At this time there isn't an ironclad difference between this an other sources
# of state like `coredata`. But one rough guide is much what is in `coredata` is
# the *output* of the configuration process: the final decisions after tests.
# This, on the other hand has *inputs*. The config files are parsed, but
# otherwise minimally transformed. When more complex fallbacks (environment
# detection) exist, they are defined elsewhere as functions that construct
# instances of these classes.


known_cpu_families = (
    'aarch64',
    'arc',
    'arm',
    'e2k',
    'ia64',
    'mips',
    'mips64',
    'parisc',
    'ppc',
    'ppc64',
    'riscv32',
    'riscv64',
    'rl78',
    'rx',
    's390x',
    'sparc',
    'sparc64',
    'x86',
    'x86_64'
)

# It would feel more natural to call this "64_BIT_CPU_FAMILES", but
# python identifiers cannot start with numbers
CPU_FAMILES_64_BIT = [
    'aarch64',
    'ia64',
    'mips64',
    'ppc64',
    'riscv64',
    'sparc64',
    'x86_64',
]

class MesonConfigFile:
    @classmethod
    def from_config_parser(cls, parser: configparser.ConfigParser) -> typing.Dict[str, typing.Dict[str, typing.Dict[str, str]]]:
        out = {}
        # This is a bit hackish at the moment.
        for s in parser.sections():
            section = {}
            for entry in parser[s]:
                value = parser[s][entry]
                # Windows paths...
                value = value.replace('\\', '\\\\')
                if ' ' in entry or '\t' in entry or "'" in entry or '"' in entry:
                    raise EnvironmentException('Malformed variable name %s in cross file..' % entry)
                try:
                    res = eval(value, {'__builtins__': None}, {'true': True, 'false': False})
                except Exception:
                    raise EnvironmentException('Malformed value in cross file variable %s.' % entry)

                for i in (res if isinstance(res, list) else [res]):
                    if not isinstance(i, (str, int, bool)):
                        raise EnvironmentException('Malformed value in cross file variable %s.' % entry)

                section[entry] = res

            out[s] = section
        return out

class HasEnvVarFallback:
    """
    A tiny class to indicate that this class contains data that can be
    initialized from either a config file or environment file. The `fallback`
    field says whether env vars should be used. Downstream logic (e.g. subclass
    methods) can check it to decide what to do, since env vars are currently
    lazily decoded.

    Frankly, this is a pretty silly class at the moment. The hope is the way
    that we deal with environment variables will become more structured, and
    this can be starting point.
    """
    def __init__(self, fallback: bool = True):
        self.fallback = fallback

class Properties(HasEnvVarFallback):
    def __init__(
            self,
            properties: typing.Optional[typing.Dict[str, typing.Union[str, typing.List[str]]]] = None,
            fallback: bool = True):
        super().__init__(fallback)
        self.properties = properties or {}  # type: typing.Dict[str, typing.Union[str, typing.List[str]]]

    def has_stdlib(self, language: str) -> bool:
        return language + '_stdlib' in self.properties

    # Some of get_stdlib, get_root, get_sys_root are wider than is actually
    # true, but without heterogenious dict annotations it's not practical to
    # narrow them
    def get_stdlib(self, language: str) -> typing.Union[str, typing.List[str]]:
        return self.properties[language + '_stdlib']

    def get_root(self) -> typing.Optional[typing.Union[str, typing.List[str]]]:
        return self.properties.get('root', None)

    def get_sys_root(self) -> typing.Optional[typing.Union[str, typing.List[str]]]:
        return self.properties.get('sys_root', None)

    def __eq__(self, other: typing.Any) -> 'typing.Union[bool, NotImplemented]':
        if isinstance(other, type(self)):
            return self.properties == other.properties
        return NotImplemented

    # TODO consider removing so Properties is less freeform
    def __getitem__(self, key: str) -> typing.Any:
        return self.properties[key]

    # TODO consider removing so Properties is less freeform
    def __contains__(self, item: typing.Any) -> bool:
        return item in self.properties

    # TODO consider removing, for same reasons as above
    def get(self, key: str, default: typing.Any = None) -> typing.Any:
        return self.properties.get(key, default)

class MachineInfo:
    def __init__(self, system: str, cpu_family: str, cpu: str, endian: str):
        self.system = system
        self.cpu_family = cpu_family
        self.cpu = cpu
        self.endian = endian
        self.is_64_bit = cpu_family in CPU_FAMILES_64_BIT  # type: bool

    def __eq__(self, other: typing.Any) -> 'typing.Union[bool, NotImplemented]':
        if self.__class__ is not other.__class__:
            return NotImplemented
        return \
            self.system == other.system and \
            self.cpu_family == other.cpu_family and \
            self.cpu == other.cpu and \
            self.endian == other.endian

    def __ne__(self, other: typing.Any) -> 'typing.Union[bool, NotImplemented]':
        if self.__class__ is not other.__class__:
            return NotImplemented
        return not self.__eq__(other)

    def __repr__(self) -> str:
        return '<MachineInfo: {} {} ({})>'.format(self.system, self.cpu_family, self.cpu)

    @classmethod
    def from_literal(cls, literal: typing.Dict[str, str]) -> 'MachineInfo':
        minimum_literal = {'cpu', 'cpu_family', 'endian', 'system'}
        if set(literal) < minimum_literal:
            raise EnvironmentException(
                'Machine info is currently {}\n'.format(literal) +
                'but is missing {}.'.format(minimum_literal - set(literal)))

        cpu_family = literal['cpu_family']
        if cpu_family not in known_cpu_families:
            mlog.warning('Unknown CPU family %s, please report this at https://github.com/mesonbuild/meson/issues/new' % cpu_family)

        endian = literal['endian']
        if endian not in ('little', 'big'):
            mlog.warning('Unknown endian %s' % endian)

        return cls(literal['system'], cpu_family, literal['cpu'], endian)

    def is_windows(self) -> bool:
        """
        Machine is windows?
        """
        return self.system in {'windows', 'mingw'}

    def is_cygwin(self) -> bool:
        """
        Machine is cygwin?
        """
        return self.system == 'cygwin'

    def is_linux(self) -> bool:
        """
        Machine is linux?
        """
        return self.system == 'linux'

    def is_darwin(self) -> bool:
        """
        Machine is Darwin (iOS/tvOS/OS X)?
        """
        return self.system in {'darwin', 'ios', 'tvos'}

    def is_android(self) -> bool:
        """
        Machine is Android?
        """
        return self.system == 'android'

    def is_haiku(self) -> bool:
        """
        Machine is Haiku?
        """
        return self.system == 'haiku'

    def is_openbsd(self) -> bool:
        """
        Machine is OpenBSD?
        """
        return self.system == 'openbsd'

    # Various prefixes and suffixes for import libraries, shared libraries,
    # static libraries, and executables.
    # Versioning is added to these names in the backends as-needed.

    def get_exe_suffix(self) -> str:
        if self.is_windows() or self.is_cygwin():
            return 'exe'
        else:
            return ''

    def get_object_suffix(self) -> str:
        if self.is_windows():
            return 'obj'
        else:
            return 'o'

    def libdir_layout_is_win(self) -> bool:
        return self.is_windows() or self.is_cygwin()

class BinaryTable(HasEnvVarFallback):
    def __init__(
            self,
            binaries: typing.Optional[typing.Dict[str, typing.Union[str, typing.List[str]]]] = None,
            fallback: bool = True):
        super().__init__(fallback)
        self.binaries = binaries or {}  # type: typing.Dict[str, typing.Union[str, typing.List[str]]]
        for name, command in self.binaries.items():
            if not isinstance(command, (list, str)):
                # TODO generalize message
                raise mesonlib.MesonException(
                    'Invalid type {!r} for binary {!r} in cross file'
                    ''.format(command, name))

    # Map from language identifiers to environment variables.
    evarMap = {
        # Compilers
        'c': 'CC',
        'cpp': 'CXX',
        'cs': 'CSC',
        'd': 'DC',
        'fortran': 'FC',
        'objc': 'OBJC',
        'objcpp': 'OBJCXX',
        'rust': 'RUSTC',
        'vala': 'VALAC',

        # Binutils
        'strip': 'STRIP',
        'ar': 'AR',
        'windres': 'WINDRES',

        'cmake': 'CMAKE',
        'qmake': 'QMAKE',
        'pkgconfig': 'PKG_CONFIG',
    }  # type: typing.Dict[str, str]

    @staticmethod
    def detect_ccache() -> typing.List[str]:
        try:
            subprocess.check_call(['ccache', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except (OSError, subprocess.CalledProcessError):
            return []
        return ['ccache']

    @classmethod
    def _warn_about_lang_pointing_to_cross(cls, compiler_exe: str, evar: str) -> None:
        evar_str = os.environ.get(evar, 'WHO_WOULD_CALL_THEIR_COMPILER_WITH_THIS_NAME')
        if evar_str == compiler_exe:
            mlog.warning('''Env var %s seems to point to the cross compiler.
This is probably wrong, it should always point to the native compiler.''' % evar)

    @classmethod
    def parse_entry(cls, entry: typing.Union[str, typing.List[str]]) -> typing.Tuple[typing.List[str], typing.List[str]]:
        compiler = mesonlib.stringlistify(entry)
        # Ensure ccache exists and remove it if it doesn't
        if compiler[0] == 'ccache':
            compiler = compiler[1:]
            ccache = cls.detect_ccache()
        else:
            ccache = []
        # Return value has to be a list of compiler 'choices'
        return compiler, ccache

    def lookup_entry(self, name: str) -> typing.Optional[typing.List[str]]:
        """Lookup binaryk

        Returns command with args as list if found, Returns `None` if nothing is
        found.

        First tries looking in explicit map, then tries environment variable.
        """
        # Try explict map, don't fall back on env var
        command = self.binaries.get(name)
        if command is not None:
            command = mesonlib.stringlistify(command)
            # Relies on there being no "" env var
            evar = self.evarMap.get(name, "")
            self._warn_about_lang_pointing_to_cross(command[0], evar)
        elif self.fallback:
            # Relies on there being no "" env var
            evar = self.evarMap.get(name, "")
            command = os.environ.get(evar)
            if command is not None:
                command = shlex.split(command)
        return command

class Directories:

    """Data class that holds information about directories for native and cross
    builds.
    """

    def __init__(self, bindir: typing.Optional[str] = None, datadir: typing.Optional[str] = None,
                 includedir: typing.Optional[str] = None, infodir: typing.Optional[str] = None,
                 libdir: typing.Optional[str] = None, libexecdir: typing.Optional[str] = None,
                 localedir: typing.Optional[str] = None, localstatedir: typing.Optional[str] = None,
                 mandir: typing.Optional[str] = None, prefix: typing.Optional[str] = None,
                 sbindir: typing.Optional[str] = None, sharedstatedir: typing.Optional[str] = None,
                 sysconfdir: typing.Optional[str] = None):
        self.bindir = bindir
        self.datadir = datadir
        self.includedir = includedir
        self.infodir = infodir
        self.libdir = libdir
        self.libexecdir = libexecdir
        self.localedir = localedir
        self.localstatedir = localstatedir
        self.mandir = mandir
        self.prefix = prefix
        self.sbindir = sbindir
        self.sharedstatedir = sharedstatedir
        self.sysconfdir = sysconfdir

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)

    def __getitem__(self, key: str) -> typing.Optional[str]:
        # Mypy can't figure out what to do with getattr here, so we'll case for it
        return typing.cast(typing.Optional[str], getattr(self, key))

    def __setitem__(self, key: str, value: typing.Optional[str]) -> None:
        setattr(self, key, value)

    def __iter__(self) -> typing.Iterator[typing.Tuple[str, str]]:
        return iter(self.__dict__.items())
