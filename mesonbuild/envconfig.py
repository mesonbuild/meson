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
from .mesonlib import EnvironmentException, MachineChoice, PerMachine
from . import mlog


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

class MesonConfigFile:
    @classmethod
    def parse_datafile(cls, filename):
        config = configparser.ConfigParser()
        try:
            with open(filename, 'r') as f:
                config.read_file(f, filename)
        except FileNotFoundError:
            raise EnvironmentException('File not found: %s.' % filename)
        return cls.from_config_parser(config)

    @classmethod
    def from_config_parser(cls, parser: configparser.ConfigParser):
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
    def __init__(self, fallback = True):
        self.fallback = fallback

class Properties(HasEnvVarFallback):
    def __init__(
            self,
            properties: typing.Optional[typing.Dict[str, typing.Union[str, typing.List[str]]]] = None,
            fallback = True):
        super().__init__(fallback)
        self.properties = properties or {}

    def has_stdlib(self, language):
        return language + '_stdlib' in self.properties

    def get_stdlib(self, language):
        return self.properties[language + '_stdlib']

    def get_root(self):
        return self.properties.get('root', None)

    def get_sys_root(self):
        return self.properties.get('sys_root', None)

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.properties == other.properties
        return NotImplemented

    # TODO consider removing so Properties is less freeform
    def __getitem__(self, key):
        return self.properties[key]

    # TODO consider removing so Properties is less freeform
    def __contains__(self, item):
        return item in self.properties

    # TODO consider removing, for same reasons as above
    def get(self, key, default=None):
        return self.properties.get(key, default)

class MachineInfo:
    def __init__(self, system, cpu_family, cpu, endian):
        self.system = system
        self.cpu_family = cpu_family
        self.cpu = cpu
        self.endian = endian

    def __eq__(self, other):
        if self.__class__ is not other.__class__:
            return NotImplemented
        return \
            self.system == other.system and \
            self.cpu_family == other.cpu_family and \
            self.cpu == other.cpu and \
            self.endian == other.endian

    def __ne__(self, other):
        if self.__class__ is not other.__class__:
            return NotImplemented
        return not self.__eq__(other)

    def __repr__(self):
        return '<MachineInfo: {} {} ({})>'.format(self.system, self.cpu_family, self.cpu)

    @staticmethod
    def from_literal(literal):
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

        return MachineInfo(
            literal['system'],
            cpu_family,
            literal['cpu'],
            endian)

    def is_windows(self):
        """
        Machine is windows?
        """
        return self.system == 'windows'

    def is_cygwin(self):
        """
        Machine is cygwin?
        """
        return self.system == 'cygwin'

    def is_linux(self):
        """
        Machine is linux?
        """
        return self.system == 'linux'

    def is_darwin(self):
        """
        Machine is Darwin (iOS/OS X)?
        """
        return self.system in ('darwin', 'ios')

    def is_android(self):
        """
        Machine is Android?
        """
        return self.system == 'android'

    def is_haiku(self):
        """
        Machine is Haiku?
        """
        return self.system == 'haiku'

    def is_openbsd(self):
        """
        Machine is OpenBSD?
        """
        return self.system == 'openbsd'

    # Various prefixes and suffixes for import libraries, shared libraries,
    # static libraries, and executables.
    # Versioning is added to these names in the backends as-needed.

    def get_exe_suffix(self):
        if self.is_windows() or self.is_cygwin():
            return 'exe'
        else:
            return ''

    def get_object_suffix(self):
        if self.is_windows():
            return 'obj'
        else:
            return 'o'

    def libdir_layout_is_win(self):
        return self.is_windows() \
            or self.is_cygwin()

class PerMachineDefaultable(PerMachine):
    """Extends `PerMachine` with the ability to default from `None`s.
    """
    def __init__(self):
        super().__init__(None, None, None)

    def default_missing(self):
        """Default host to buid and target to host.

        This allows just specifying nothing in the native case, just host in the
        cross non-compiler case, and just target in the native-built
        cross-compiler case.
        """
        if self.host is None:
            self.host = self.build
        if self.target is None:
            self.target = self.host

    def miss_defaulting(self):
        """Unset definition duplicated from their previous to None

        This is the inverse of ''default_missing''. By removing defaulted
        machines, we can elaborate the original and then redefault them and thus
        avoid repeating the elaboration explicitly.
        """
        if self.target == self.host:
            self.target = None
        if self.host == self.build:
            self.host = None

class MachineInfos(PerMachineDefaultable):
    def matches_build_machine(self, machine: MachineChoice):
        return self.build == self[machine]

class BinaryTable(HasEnvVarFallback):
    def __init__(
            self,
            binaries: typing.Optional[typing.Dict[str, typing.Union[str, typing.List[str]]]] = None,

            fallback = True):
        super().__init__(fallback)
        self.binaries = binaries or {}
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
    }

    @classmethod
    def detect_ccache(cls):
        try:
            has_ccache = subprocess.call(['ccache', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            has_ccache = 1
        if has_ccache == 0:
            cmdlist = ['ccache']
        else:
            cmdlist = []
        return cmdlist

    @classmethod
    def _warn_about_lang_pointing_to_cross(cls, compiler_exe, evar):
        evar_str = os.environ.get(evar, 'WHO_WOULD_CALL_THEIR_COMPILER_WITH_THIS_NAME')
        if evar_str == compiler_exe:
            mlog.warning('''Env var %s seems to point to the cross compiler.
This is probably wrong, it should always point to the native compiler.''' % evar)

    @classmethod
    def parse_entry(cls, entry):
        compiler = mesonlib.stringlistify(entry)
        # Ensure ccache exists and remove it if it doesn't
        if compiler[0] == 'ccache':
            compiler = compiler[1:]
            ccache = cls.detect_ccache()
        else:
            ccache = []
        # Return value has to be a list of compiler 'choices'
        return compiler, ccache

    def lookup_entry(self, name):
        """Lookup binary

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

    def __contains__(self, key: str) -> str:
        return hasattr(self, key)

    def __getitem__(self, key: str) -> str:
        return getattr(self, key)

    def __setitem__(self, key: str, value: typing.Optional[str]) -> None:
        setattr(self, key, value)

    def __iter__(self) -> typing.Iterator[typing.Tuple[str, str]]:
        return iter(self.__dict__.items())
