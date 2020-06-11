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

import os, subprocess
import typing as T

from . import mesonlib
from .mesonlib import EnvironmentException, MachineChoice, PerMachine, split_args
from . import mlog

_T = T.TypeVar('_T')


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
    'alpha',
    'arc',
    'arm',
    'avr',
    'c2000',
    'dspic',
    'e2k',
    'ia64',
    'm68k',
    'microblaze',
    'mips',
    'mips64',
    'parisc',
    'pic24',
    'ppc',
    'ppc64',
    'riscv32',
    'riscv64',
    'rl78',
    'rx',
    's390',
    's390x',
    'sh4',
    'sparc',
    'sparc64',
    'wasm32',
    'wasm64',
    'x86',
    'x86_64',
)

# It would feel more natural to call this "64_BIT_CPU_FAMILES", but
# python identifiers cannot start with numbers
CPU_FAMILES_64_BIT = [
    'aarch64',
    'alpha',
    'ia64',
    'mips64',
    'ppc64',
    'riscv64',
    's390x',
    'sparc64',
    'wasm64',
    'x86_64',
]

def get_env_var_pair(for_machine: MachineChoice,
                     is_cross: bool,
                     var_name: str) -> T.Tuple[T.Optional[str], T.Optional[str]]:
    """
    Returns the exact env var and the value.
    """
    candidates = PerMachine(
        # The prefixed build version takes priority, but if we are native
        # compiling we fall back on the unprefixed host version. This
        # allows native builds to never need to worry about the 'BUILD_*'
        # ones.
        ([var_name + '_FOR_BUILD'] if is_cross else [var_name]),
        # Always just the unprefixed host verions
        [var_name]
    )[for_machine]
    for var in candidates:
        value = os.environ.get(var)
        if value is not None:
            break
    else:
        formatted = ', '.join(['{!r}'.format(var) for var in candidates])
        mlog.debug('None of {} are defined in the environment, not changing global flags.'.format(formatted))
        return None
    mlog.log('Using {!r} from environment with value: {!r}'.format(var, value))
    return var, value

def get_env_var(for_machine: MachineChoice,
                is_cross: bool,
                var_name: str) -> T.Tuple[T.Optional[str], T.Optional[str]]:
    ret = get_env_var_pair(for_machine, is_cross, var_name)
    if ret is None:
        return None
    else:
        var, value = ret
        return value

class Properties:
    def __init__(
            self,
            properties: T.Optional[T.Dict[str, T.Union[str, T.List[str]]]] = None,
    ):
        self.properties = properties or {}  # type: T.Dict[str, T.Union[str, T.List[str]]]

    def has_stdlib(self, language: str) -> bool:
        return language + '_stdlib' in self.properties

    # Some of get_stdlib, get_root, get_sys_root are wider than is actually
    # true, but without heterogenious dict annotations it's not practical to
    # narrow them
    def get_stdlib(self, language: str) -> T.Union[str, T.List[str]]:
        return self.properties[language + '_stdlib']

    def get_root(self) -> T.Optional[T.Union[str, T.List[str]]]:
        return self.properties.get('root', None)

    def get_sys_root(self) -> T.Optional[T.Union[str, T.List[str]]]:
        return self.properties.get('sys_root', None)

    def get_pkg_config_libdir(self) -> T.Optional[T.List[str]]:
        p = self.properties.get('pkg_config_libdir', None)
        if p is None:
            return p
        return mesonlib.listify(p)

    def __eq__(self, other: T.Any) -> 'T.Union[bool, NotImplemented]':
        if isinstance(other, type(self)):
            return self.properties == other.properties
        return NotImplemented

    # TODO consider removing so Properties is less freeform
    def __getitem__(self, key: str) -> T.Any:
        return self.properties[key]

    # TODO consider removing so Properties is less freeform
    def __contains__(self, item: T.Any) -> bool:
        return item in self.properties

    # TODO consider removing, for same reasons as above
    def get(self, key: str, default: T.Any = None) -> T.Any:
        return self.properties.get(key, default)

class MachineInfo:
    def __init__(self, system: str, cpu_family: str, cpu: str, endian: str):
        self.system = system
        self.cpu_family = cpu_family
        self.cpu = cpu
        self.endian = endian
        self.is_64_bit = cpu_family in CPU_FAMILES_64_BIT  # type: bool

    def __eq__(self, other: T.Any) -> 'T.Union[bool, NotImplemented]':
        if self.__class__ is not other.__class__:
            return NotImplemented
        return \
            self.system == other.system and \
            self.cpu_family == other.cpu_family and \
            self.cpu == other.cpu and \
            self.endian == other.endian

    def __ne__(self, other: T.Any) -> 'T.Union[bool, NotImplemented]':
        if self.__class__ is not other.__class__:
            return NotImplemented
        return not self.__eq__(other)

    def __repr__(self) -> str:
        return '<MachineInfo: {} {} ({})>'.format(self.system, self.cpu_family, self.cpu)

    @classmethod
    def from_literal(cls, literal: T.Dict[str, str]) -> 'MachineInfo':
        minimum_literal = {'cpu', 'cpu_family', 'endian', 'system'}
        if set(literal) < minimum_literal:
            raise EnvironmentException(
                'Machine info is currently {}\n'.format(literal) +
                'but is missing {}.'.format(minimum_literal - set(literal)))

        cpu_family = literal['cpu_family']
        if cpu_family not in known_cpu_families:
            mlog.warning('Unknown CPU family {}, please report this at https://github.com/mesonbuild/meson/issues/new'.format(cpu_family))

        endian = literal['endian']
        if endian not in ('little', 'big'):
            mlog.warning('Unknown endian {}'.format(endian))

        return cls(literal['system'], cpu_family, literal['cpu'], endian)

    def is_windows(self) -> bool:
        """
        Machine is windows?
        """
        return self.system == 'windows' or 'mingw' in self.system

    def is_cygwin(self) -> bool:
        """
        Machine is cygwin?
        """
        return self.system.startswith('cygwin')

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

    def is_netbsd(self) -> bool:
        """
        Machine is NetBSD?
        """
        return self.system == 'netbsd'

    def is_openbsd(self) -> bool:
        """
        Machine is OpenBSD?
        """
        return self.system == 'openbsd'

    def is_dragonflybsd(self) -> bool:
        """Machine is DragonflyBSD?"""
        return self.system == 'dragonfly'

    def is_freebsd(self) -> bool:
        """Machine is FreeBSD?"""
        return self.system == 'freebsd'

    def is_sunos(self) -> bool:
        """Machine is illumos or Solaris?"""
        return self.system == 'sunos'

    def is_hurd(self) -> bool:
        """
        Machine is GNU/Hurd?
        """
        return self.system == 'gnu'

    def is_irix(self) -> bool:
        """Machine is IRIX?"""
        return self.system.startswith('irix')

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

class BinaryTable:
    def __init__(
            self,
            binaries: T.Optional[T.Dict[str, T.Union[str, T.List[str]]]] = None,
    ):
        self.binaries = binaries or {}  # type: T.Dict[str, T.Union[str, T.List[str]]]
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

        # Linkers
        'c_ld': 'CC_LD',
        'cpp_ld': 'CXX_LD',
        'd_ld': 'DC_LD',
        'fortran_ld': 'FC_LD',
        'objc_ld': 'OBJC_LD',
        'objcpp_ld': 'OBJCXX_LD',
        'rust_ld': 'RUSTC_LD',

        # Binutils
        'strip': 'STRIP',
        'ar': 'AR',
        'windres': 'WINDRES',

        # Other tools
        'cmake': 'CMAKE',
        'qmake': 'QMAKE',
        'pkgconfig': 'PKG_CONFIG',
    }  # type: T.Dict[str, str]

    # Deprecated environment variables mapped from the new variable to the old one
    # Deprecated in 0.54.0
    DEPRECATION_MAP = {
        'DC_LD': 'D_LD',
        'FC_LD': 'F_LD',
        'RUSTC_LD': 'RUST_LD',
        'OBJCXX_LD': 'OBJCPP_LD',
    }  # type: T.Dict[str, str]

    @staticmethod
    def detect_ccache() -> T.List[str]:
        try:
            subprocess.check_call(['ccache', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except (OSError, subprocess.CalledProcessError):
            return []
        return ['ccache']

    @classmethod
    def parse_entry(cls, entry: T.Union[str, T.List[str]]) -> T.Tuple[T.List[str], T.List[str]]:
        compiler = mesonlib.stringlistify(entry)
        # Ensure ccache exists and remove it if it doesn't
        if compiler[0] == 'ccache':
            compiler = compiler[1:]
            ccache = cls.detect_ccache()
        else:
            ccache = []
        # Return value has to be a list of compiler 'choices'
        return compiler, ccache

    def lookup_entry(self,
                     for_machine: MachineChoice,
                     is_cross: bool,
                     name: str) -> T.Optional[T.List[str]]:
        """Lookup binary in cross/native file and fallback to environment.

        Returns command with args as list if found, Returns `None` if nothing is
        found.
        """
        # Try explicit map, don't fall back on env var
        # Try explict map, then env vars
        for _ in [()]: # a trick to get `break`
            raw_command = self.binaries.get(name)
            if raw_command is not None:
                command = mesonlib.stringlistify(raw_command)
                break # found
            evar = self.evarMap.get(name)
            if evar is not None:
                raw_command = get_env_var(for_machine, is_cross, evar)
                if raw_command is None:
                    deprecated = self.DEPRECATION_MAP.get(evar)
                    if deprecated is not None:
                        raw_command = get_env_var(for_machine, is_cross, deprecated)
                        if raw_command is not None:
                            mlog.deprecation(
                                'The', deprecated, 'environment variable is deprecated in favor of',
                                evar, once=True)
                if raw_command is not None:
                    command = split_args(raw_command)
                    break # found
            command = None


        # Do not return empty or blank string entries
        if command is not None and (len(command) == 0 or len(command[0].strip()) == 0):
            command = None
        return command

class Directories:

    """Data class that holds information about directories for native and cross
    builds.
    """

    def __init__(self, bindir: T.Optional[str] = None, datadir: T.Optional[str] = None,
                 includedir: T.Optional[str] = None, infodir: T.Optional[str] = None,
                 libdir: T.Optional[str] = None, libexecdir: T.Optional[str] = None,
                 localedir: T.Optional[str] = None, localstatedir: T.Optional[str] = None,
                 mandir: T.Optional[str] = None, prefix: T.Optional[str] = None,
                 sbindir: T.Optional[str] = None, sharedstatedir: T.Optional[str] = None,
                 sysconfdir: T.Optional[str] = None):
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

    def __getitem__(self, key: str) -> T.Optional[str]:
        # Mypy can't figure out what to do with getattr here, so we'll case for it
        return T.cast(T.Optional[str], getattr(self, key))

    def __setitem__(self, key: str, value: T.Optional[str]) -> None:
        setattr(self, key, value)

    def __iter__(self) -> T.Iterator[T.Tuple[str, str]]:
        return iter(self.__dict__.items())
