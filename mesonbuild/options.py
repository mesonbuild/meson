# SPDX-License-Identifier: Apache-2.0
# Copyright 2013-2024 Contributors to the The Meson project
# Copyright © 2019-2025 Intel Corporation

from __future__ import annotations
from collections import OrderedDict
from itertools import chain
import dataclasses
import enum
import os
import pathlib

import typing as T

from .mesonlib import (
    HoldableObject,
    default_prefix,
    default_datadir,
    default_includedir,
    default_infodir,
    default_libdir,
    default_libexecdir,
    default_localedir,
    default_mandir,
    default_sbindir,
    default_sysconfdir,
    MesonException,
    MesonBugException,
    listify_array_value,
    MachineChoice,
)
from . import mlog

if T.TYPE_CHECKING:
    from typing_extensions import Literal, Final, TypeAlias, TypedDict

    from .envconfig import MachineInfo
    from .mesonlib import SubProject
    from .compilers.compilers import Language

    DeprecatedType: TypeAlias = T.Union[bool, str, T.Dict[str, str], T.List[str]]
    AnyOptionType: TypeAlias = T.Union[
        'UserBooleanOption', 'UserComboOption', 'UserFeatureOption',
        'UserIntegerOption', 'UserStdOption', 'UserStringArrayOption',
        'UserStringOption', 'UserUmaskOption']
    ElementaryOptionValues: TypeAlias = T.Union[str, int, bool, T.List[str]]
    MutableKeyedOptionDictType: TypeAlias = T.Dict['OptionKey', AnyOptionType]

    _OptionKeyTuple: TypeAlias = T.Tuple[T.Optional[str], MachineChoice, str]

    class OptionKeyState(TypedDict):
        name: str
        subproject: T.Optional[str]
        machine: MachineChoice

DEFAULT_YIELDING = False

# Can't bind this near the class method it seems, sadly.
_T = T.TypeVar('_T')

backendlist = ['ninja', 'vs', 'vs2010', 'vs2012', 'vs2013', 'vs2015', 'vs2017', 'vs2019', 'vs2022', 'vs2026', 'xcode', 'none']
genvslitelist = ['vs2022', 'vs2026']
buildtypelist = ['plain', 'debug', 'debugoptimized', 'release', 'minsize', 'custom']

# This is copied from coredata. There is no way to share this, because this
# is used in the OptionKey constructor, and the coredata lists are
# OptionKeys...
_BUILTIN_NAMES = {
    'prefix',
    'bindir',
    'datadir',
    'includedir',
    'infodir',
    'libdir',
    'licensedir',
    'libexecdir',
    'localedir',
    'localstatedir',
    'mandir',
    'sbindir',
    'sharedstatedir',
    'sysconfdir',
    'auto_features',
    'backend',
    'buildtype',
    'debug',
    'default_library',
    'default_both_libraries',
    'errorlogs',
    'genvslite',
    'install_umask',
    'layout',
    'optimization',
    'prefer_static',
    'stdsplit',
    'strip',
    'unity',
    'unity_size',
    'warning_level',
    'werror',
    'wrap_mode',
    'force_fallback_for',
    'pkg_config_path',
    'cmake_prefix_path',
    'vsenv',
    'os2_emxomf',
}

_BAD_VALUE = 'Qwert Zuiopü'
_optionkey_cache: T.Dict[_OptionKeyTuple, OptionKey] = {}


class OptionKey:

    """Represents an option key in the various option dictionaries.

    This provides a flexible, powerful way to map option names from their
    external form (things like subproject:build.option) to something that
    internally easier to reason about and produce.
    """

    __slots__ = ('name', 'subproject', 'machine', '_hash')

    name: str
    subproject: T.Optional[str]  # None is global, empty string means top level project
    machine: MachineChoice
    _hash: int

    def __new__(cls,
                name: str = '',
                subproject: T.Optional[str] = None,
                machine: MachineChoice = MachineChoice.HOST) -> OptionKey:
        """The use of the __new__ method allows to add a transparent cache
        to the OptionKey object creation, without breaking its API.
        """
        if not name:
            return super().__new__(cls)  # for unpickling, do not cache now

        tuple_: _OptionKeyTuple = (subproject, machine, name)
        try:
            return _optionkey_cache[tuple_]
        except KeyError:
            instance = super().__new__(cls)
            instance._init(name, subproject, machine)
            _optionkey_cache[tuple_] = instance
            return instance

    def _init(self, name: str, subproject: T.Optional[str], machine: MachineChoice) -> None:
        # We don't use the __init__ method, because it would be called after __new__
        # while we need __new__ to initialise the object before populating the cache.

        if not isinstance(machine, MachineChoice):
            raise MesonException(f'Internal error, bad machine type: {machine}')
        if not isinstance(name, str):
            raise MesonBugException(f'Key name is not a string: {name}')
        assert ':' not in name

        object.__setattr__(self, 'name', name)
        object.__setattr__(self, 'subproject', subproject)
        object.__setattr__(self, 'machine', machine)
        object.__setattr__(self, '_hash', hash((name, subproject, machine)))

    def __setattr__(self, key: str, value: object) -> None:
        raise AttributeError('OptionKey instances do not support mutation.')

    def __getstate__(self) -> OptionKeyState:
        return {
            'name': self.name,
            'subproject': self.subproject,
            'machine': self.machine,
        }

    def __setstate__(self, state: OptionKeyState) -> None:
        # Here, the object is created using __new__()
        self._init(**state)
        _optionkey_cache[self._to_tuple()] = self

    def __hash__(self) -> int:
        return self._hash

    def _to_tuple(self) -> _OptionKeyTuple:
        return (self.subproject, self.machine, self.name)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, OptionKey):
            return self._to_tuple() == other._to_tuple()
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        if isinstance(other, OptionKey):
            return self._to_tuple() != other._to_tuple()
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        if isinstance(other, OptionKey):
            if self.subproject is None:
                return other.subproject is not None
            elif other.subproject is None:
                return False
            return self._to_tuple() < other._to_tuple()
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, OptionKey):
            if self.subproject is None and other.subproject is not None:
                return True
            elif self.subproject is not None and other.subproject is None:
                return False
            return self._to_tuple() <= other._to_tuple()
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, OptionKey):
            if other.subproject is None:
                return self.subproject is not None
            elif self.subproject is None:
                return False
            return self._to_tuple() > other._to_tuple()
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, OptionKey):
            if self.subproject is None and other.subproject is not None:
                return False
            elif self.subproject is not None and other.subproject is None:
                return True
            return self._to_tuple() >= other._to_tuple()
        return NotImplemented

    def __str__(self) -> str:
        out = self.name
        if self.machine is MachineChoice.BUILD:
            out = f'build.{out}'
        if self.subproject is not None:
            out = f'{self.subproject}:{out}'
        return out

    def __repr__(self) -> str:
        return f'OptionKey({self.name!r}, {self.subproject!r}, {self.machine!r})'

    @classmethod
    def from_string(cls, raw: str) -> 'OptionKey':
        """Parse the raw command line format into a three part tuple.

        This takes strings like `mysubproject:build.myoption` and Creates an
        OptionKey out of them.
        """
        assert isinstance(raw, str)
        try:
            subproject, raw2 = raw.split(':')
        except ValueError:
            subproject, raw2 = None, raw

        for_machine = MachineChoice.HOST
        try:
            prefix, raw3 = raw2.split('.')
            if prefix == 'build':
                for_machine = MachineChoice.BUILD
            else:
                raw3 = raw2
        except ValueError:
            raw3 = raw2

        opt = raw3
        assert ':' not in opt
        assert opt.count('.') < 2

        return cls(opt, subproject, for_machine)

    def evolve(self,
               name: T.Optional[str] = None,
               subproject: T.Optional[str] = _BAD_VALUE,
               machine: T.Optional[MachineChoice] = None) -> 'OptionKey':
        """Create a new copy of this key, but with altered members.

        For example:
        >>> a = OptionKey('foo', '', MachineChoice.Host)
        >>> b = OptionKey('foo', 'bar', MachineChoice.Host)
        >>> b == a.evolve(subproject='bar')
        True
        """
        # We have to be a little clever with lang here, because lang is valid
        # as None, for non-compiler options
        return OptionKey(name if name is not None else self.name,
                         subproject if subproject != _BAD_VALUE else self.subproject, # None is a valid value so it can'the default value in method declaration.
                         machine if machine is not None else self.machine)

    def as_root(self) -> OptionKey:
        """Convenience method for key.evolve(subproject='')."""
        if self.subproject != '':
            return self.evolve(subproject='')
        return self

    def as_build(self) -> OptionKey:
        """Convenience method for key.evolve(machine=MachineChoice.BUILD)."""
        if self.machine != MachineChoice.BUILD:
            return self.evolve(machine=MachineChoice.BUILD)
        return self

    def as_host(self) -> OptionKey:
        """Convenience method for key.evolve(machine=MachineChoice.HOST)."""
        if self.machine != MachineChoice.HOST:
            return self.evolve(machine=MachineChoice.HOST)
        return self

    def has_module_prefix(self) -> bool:
        return '.' in self.name

    def get_module_prefix(self) -> T.Optional[str]:
        if self.has_module_prefix():
            return self.name.split('.', 1)[0]
        return None

    def is_for_build(self) -> bool:
        return self.machine is MachineChoice.BUILD

if T.TYPE_CHECKING:
    OptionDict: TypeAlias = T.Dict[OptionKey, ElementaryOptionValues]

@dataclasses.dataclass
class UserOption(T.Generic[_T], HoldableObject):

    name: str
    description: str
    value_: dataclasses.InitVar[_T]
    yielding: bool = DEFAULT_YIELDING
    deprecated: DeprecatedType = False
    readonly: bool = dataclasses.field(default=False)
    parent: T.Optional[UserOption] = None

    def __post_init__(self, value_: _T) -> None:
        self.value = self.validate_value(value_)
        # Final isn't technically allowed in a __post_init__ method
        self.default: Final[_T] = self.value  # type: ignore[misc]

    def listify(self, value: ElementaryOptionValues) -> T.List[str]:
        if isinstance(value, list):
            return value
        if isinstance(value, bool):
            return ['true'] if value else ['false']
        if isinstance(value, int):
            return [str(value)]
        return [value]

    def printable_value(self, value: ElementaryOptionValues) -> ElementaryOptionValues:
        assert isinstance(value, (str, int, bool, list))
        return value

    def printable_choices(self) -> T.Optional[T.List[str]]:
        return None

    # Check that the input is a valid value and return the
    # "cleaned" or "native" version. For example the Boolean
    # option could take the string "true" and return True.
    def validate_value(self, value: object) -> _T:
        raise RuntimeError('Derived option class did not override validate_value.')

@dataclasses.dataclass
class EnumeratedUserOption(UserOption[_T]):

    """A generic UserOption that has enumerated values."""

    choices: T.List[_T] = dataclasses.field(default_factory=list)

    def printable_choices(self) -> T.Optional[T.List[str]]:
        return [str(c) for c in self.choices]


class UserStringOption(UserOption[str]):

    def validate_value(self, value: object) -> str:
        if not isinstance(value, str):
            raise MesonException(f'The value of option "{self.name}" is "{value}", which is not a string.')
        return value

@dataclasses.dataclass
class UserBooleanOption(EnumeratedUserOption[bool]):

    choices: T.List[bool] = dataclasses.field(default_factory=lambda: [True, False])

    def validate_value(self, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if not isinstance(value, str):
            raise MesonException(f'Option "{self.name}" value {value} cannot be converted to a boolean')
        if value.lower() == 'true':
            return True
        if value.lower() == 'false':
            return False
        raise MesonException(f'Option "{self.name}" value {value} is not boolean (true or false).')


class _UserIntegerBase(UserOption[_T]):

    min_value: T.Optional[int]
    max_value: T.Optional[int]

    if T.TYPE_CHECKING:
        def toint(self, v: str) -> int: ...

    def __post_init__(self, value_: _T) -> None:
        super().__post_init__(value_)
        choices: T.List[str] = []
        if self.min_value is not None:
            choices.append(f'>= {self.min_value!s}')
        if self.max_value is not None:
            choices.append(f'<= {self.max_value!s}')
        self.__choices: str = ', '.join(choices)

    def printable_choices(self) -> T.Optional[T.List[str]]:
        return [self.__choices]

    def validate_value(self, value: object) -> _T:
        if isinstance(value, str):
            value = T.cast('_T', self.toint(value))
        if isinstance(value, bool) or not isinstance(value, int):
            raise MesonException(f'Value {value!r} for option "{self.name}" is not an integer.')
        if self.min_value is not None and value < self.min_value:
            raise MesonException(f'Value {value} for option "{self.name}" is less than minimum value {self.min_value}.')
        if self.max_value is not None and value > self.max_value:
            raise MesonException(f'Value {value} for option "{self.name}" is more than maximum value {self.max_value}.')
        return T.cast('_T', value)


@dataclasses.dataclass
class UserIntegerOption(_UserIntegerBase[int]):

    min_value: T.Optional[int] = None
    max_value: T.Optional[int] = None

    def toint(self, valuestring: str) -> int:
        try:
            return int(valuestring)
        except ValueError:
            raise MesonException(f'Value string "{valuestring}" for option "{self.name}" is not convertible to an integer.')


class OctalInt(int):
    # NinjaBackend.get_user_option_args uses str() to converts it to a command line option
    # UserUmaskOption.toint() uses int(str, 8) to convert it to an integer
    # So we need to use oct instead of dec here if we do not want values to be misinterpreted.
    def __str__(self) -> str:
        return oct(int(self))


@dataclasses.dataclass
class UserUmaskOption(_UserIntegerBase[T.Union["Literal['preserve']", OctalInt]]):

    min_value: T.Optional[int] = dataclasses.field(default=0, init=False)
    max_value: T.Optional[int] = dataclasses.field(default=0o777, init=False)

    def printable_value(self, value: ElementaryOptionValues) -> ElementaryOptionValues:
        if isinstance(value, int):
            return format(value, '04o')
        return value

    def validate_value(self, value: object) -> T.Union[Literal['preserve'], OctalInt]:
        if value == 'preserve':
            return 'preserve'
        return OctalInt(super().validate_value(value))

    def toint(self, valuestring: str) -> int:
        try:
            return int(valuestring, 8)
        except ValueError as e:
            raise MesonException(f'Invalid mode for option "{self.name}" {e}')


@dataclasses.dataclass
class UserComboOption(EnumeratedUserOption[str]):

    def validate_value(self, value: object) -> str:
        if value not in self.choices:
            if isinstance(value, bool):
                _type = 'boolean'
            elif isinstance(value, (int, float)):
                _type = 'number'
            else:
                _type = 'string'
            optionsstring = ', '.join([f'"{item}"' for item in self.choices])
            raise MesonException('Value "{}" (of type "{}") for option "{}" is not one of the choices.'
                                 ' Possible choices are (as string): {}.'.format(
                                     value, _type, self.name, optionsstring))

        assert isinstance(value, str), 'for mypy'
        return value

@dataclasses.dataclass
class UserArrayOption(UserOption[T.List[_T]]):

    value_: dataclasses.InitVar[T.Union[_T, T.List[_T]]]
    choices: T.Optional[T.List[_T]] = None
    split_args: bool = False
    allow_dups: bool = False

    def printable_choices(self) -> T.Optional[T.List[str]]:
        if self.choices is None:
            return None
        return [str(c) for c in self.choices]


@dataclasses.dataclass
class UserStringArrayOption(UserArrayOption[str]):

    def listify(self, value: object) -> T.List[str]:
        try:
            return listify_array_value(value, self.split_args)
        except MesonException as e:
            raise MesonException(f'error in option "{self.name}": {e!s}')

    def validate_value(self, value: object) -> T.List[str]:
        newvalue = self.listify(value)

        if not self.allow_dups and len(set(newvalue)) != len(newvalue):
            msg = 'Duplicated values in array option is deprecated. ' \
                  'This will become a hard error in meson 2.0.'
            mlog.deprecation(msg)
        for i in newvalue:
            if not isinstance(i, str):
                raise MesonException(f'String array element "{newvalue!s}" for option "{self.name}" is not a string.')
        if self.choices:
            bad = [x for x in newvalue if x not in self.choices]
            if bad:
                raise MesonException('Value{} "{}" for option "{}" {} not in allowed choices: "{}"'.format(
                    '' if len(bad) == 1 else 's',
                    ', '.join(bad),
                    self.name,
                    'is' if len(bad) == 1 else 'are',
                    ', '.join(self.choices))
                )
        return newvalue


@dataclasses.dataclass
class UserFeatureOption(UserComboOption):

    choices: T.List[str] = dataclasses.field(
        # Ensure we get a copy with the lambda
        default_factory=lambda: ['enabled', 'disabled', 'auto'], init=False)


_U = T.TypeVar('_U', bound=UserOption)


def choices_are_different(a: _U, b: _U) -> bool:
    """Are the choices between two options the same?

    :param a: A UserOption[T]
    :param b: A second UserOption[T]
    :return: True if the choices have changed, otherwise False
    """
    if isinstance(a, EnumeratedUserOption):
        # We expect `a` and `b` to be of the same type, but can't really annotate it that way.
        assert isinstance(b, EnumeratedUserOption), 'for mypy'
        return a.choices != b.choices
    elif isinstance(a, UserArrayOption):
        # We expect `a` and `b` to be of the same type, but can't really annotate it that way.
        assert isinstance(b, UserArrayOption), 'for mypy'
        return a.choices != b.choices
    elif isinstance(a, _UserIntegerBase):
        assert isinstance(b, _UserIntegerBase), 'for mypy'
        return a.max_value != b.max_value or a.min_value != b.min_value

    return False


class UserStdOption(UserComboOption):
    '''
    UserOption specific to c_std and cpp_std options. User can set a list of
    STDs in preference order and it selects the first one supported by current
    compiler.

    For historical reasons, some compilers (msvc) allowed setting a GNU std and
    silently fell back to C std. This is now deprecated. Projects that support
    both GNU and MSVC compilers should set e.g. c_std=gnu11,c11.

    This is not using self.deprecated mechanism we already have for project
    options because we want to print a warning if ALL values are deprecated, not
    if SOME values are deprecated.
    '''
    def __init__(self, lang: str, all_stds: T.List[str]) -> None:
        self.lang = lang.lower()
        self.all_stds = ['none'] + all_stds
        # Map a deprecated std to its replacement. e.g. gnu11 -> c11.
        self.deprecated_stds: T.Dict[str, str] = {}
        opt_name = 'cpp_std' if lang == 'c++' else f'{lang}_std'
        super().__init__(opt_name, f'{lang} language standard to use', 'none', choices=['none'])

    def set_versions(self, versions: T.List[str], gnu: bool = False, gnu_deprecated: bool = False) -> None:
        assert all(std in self.all_stds for std in versions)
        self.choices += versions
        if gnu:
            gnu_stds_map = {f'gnu{std[1:]}': std for std in versions}
            if gnu_deprecated:
                self.deprecated_stds.update(gnu_stds_map)
            else:
                self.choices += gnu_stds_map.keys()

    def validate_value(self, value: object) -> str:
        try:
            candidates = listify_array_value(value)
        except MesonException as e:
            raise MesonException(f'error in option "{self.name}": {e!s}')
        for std in candidates:
            if not isinstance(std, str):
                raise MesonException(f'String array element "{candidates!s}" for option "{self.name}" is not a string.')
        unknown = ','.join(std for std in candidates if std not in self.all_stds)
        if unknown:
            raise MesonException(f'Unknown option "{self.name}" value {unknown}. Possible values are {self.all_stds}.')
        # Check first if any of the candidates are not deprecated
        for std in candidates:
            if std in self.choices:
                return std
        # Fallback to a deprecated std if any
        for std in candidates:
            newstd = self.deprecated_stds.get(std)
            if newstd is not None:
                mlog.deprecation(
                    f'None of the values {candidates} are supported by the {self.lang} compiler.\n' +
                    f'However, the deprecated {std} std currently falls back to {newstd}.\n' +
                    'This will be an error in meson 2.0.\n' +
                    'If the project supports both GNU and MSVC compilers, a value such as\n' +
                    '"c_std=gnu11,c11" specifies that GNU is preferred but it can safely fallback to plain c11.', once=True)
                return newstd
        raise MesonException(f'None of values {candidates} are supported by the {self.lang.upper()} compiler. ' +
                             f'Possible values for option "{self.name}" are {self.choices}')


def argparse_name_to_arg(name: str) -> str:
    if name == 'warning_level':
        return '--warnlevel'
    return '--' + name.replace('_', '-')


def prefixed_default(opt: AnyOptionType, name: OptionKey, prefix: str = '') -> ElementaryOptionValues:
    try:
        return BUILTIN_DIR_NOPREFIX_OPTIONS[name][prefix]
    except KeyError:
        return opt.default


# Update `docs/markdown/Builtin-options.md` after changing the options below
# Also update mesonlib._BUILTIN_NAMES. See the comment there for why this is required.
# Please also update completion scripts in $MESONSRC/data/shell-completions/
BUILTIN_DIR_OPTIONS: T.Mapping[OptionKey, AnyOptionType] = {
    OptionKey(o.name): o for o in [
        UserStringOption('prefix', 'Installation prefix', default_prefix()),
        UserStringOption('bindir', 'Executable directory', 'bin'),
        UserStringOption('datadir', 'Data file directory', default_datadir()),
        UserStringOption('includedir', 'Header file directory', default_includedir()),
        UserStringOption('infodir', 'Info page directory', default_infodir()),
        UserStringOption('libdir', 'Library directory', default_libdir()),
        UserStringOption('licensedir', 'Licenses directory', ''),
        UserStringOption('libexecdir', 'Library executable directory', default_libexecdir()),
        UserStringOption('localedir', 'Locale data directory', default_localedir()),
        UserStringOption('localstatedir', 'Localstate data directory', 'var'),
        UserStringOption('mandir', 'Manual page directory', default_mandir()),
        UserStringOption('sbindir', 'System executable directory', default_sbindir()),
        UserStringOption('sharedstatedir', 'Architecture-independent data directory', 'com'),
        UserStringOption('sysconfdir', 'Sysconf data directory', default_sysconfdir()),
    ]
}

BUILTIN_CORE_OPTIONS: T.Mapping[OptionKey, AnyOptionType] = {
    OptionKey(o.name): o for o in T.cast('T.List[AnyOptionType]', [
        UserFeatureOption('auto_features', "Override value of all 'auto' features", 'auto'),
        UserComboOption('backend', 'Backend to use', 'ninja', choices=backendlist, readonly=True),
        UserComboOption(
            'genvslite',
            'Setup multiple buildtype-suffixed ninja-backend build directories, '
            'and a [builddir]_vs containing a Visual Studio meta-backend with multiple configurations that calls into them',
            'vs2022',
            choices=genvslitelist
        ),
        UserComboOption('buildtype', 'Build type to use', 'debug', choices=buildtypelist),
        UserBooleanOption('debug', 'Enable debug symbols and other information', True),
        UserComboOption('default_library', 'Default library type', 'shared', choices=['shared', 'static', 'both']),
        UserComboOption('default_both_libraries', 'Default library type for both_libraries', 'shared',
                        choices=['shared', 'static', 'auto']),
        UserBooleanOption('errorlogs', "Whether to print the logs from failing tests", True),
        UserUmaskOption('install_umask', 'Default umask to apply on permissions of installed files', OctalInt(0o022)),
        UserComboOption('layout', 'Build directory layout', 'mirror', choices=['mirror', 'flat']),
        UserComboOption('namingscheme', 'How target file names are formed', 'classic', choices=['platform', 'classic']),
        UserComboOption('optimization', 'Optimization level', '0', choices=['plain', '0', 'g', '1', '2', '3', 's']),
        UserBooleanOption('prefer_static', 'Whether to try static linking before shared linking', False),
        UserBooleanOption('stdsplit', 'Split stdout and stderr in test logs', True),
        UserBooleanOption('strip', 'Strip targets on install', False),
        UserComboOption('unity', 'Unity build', 'off', choices=['on', 'off', 'subprojects']),
        UserIntegerOption('unity_size', 'Unity block size', 4, min_value=2),
        UserComboOption('warning_level', 'Compiler warning level to use', '1', choices=['0', '1', '2', '3', 'everything']),
        UserBooleanOption('werror', 'Treat warnings as errors', False),
        UserComboOption('wrap_mode', 'Wrap mode', 'default', choices=['default', 'nofallback', 'nodownload', 'forcefallback', 'nopromote']),
        UserStringArrayOption('force_fallback_for', 'Force fallback for those subprojects', []),
        UserBooleanOption('vsenv', 'Activate Visual Studio environment', False, readonly=True),
        UserBooleanOption('os2_emxomf', 'Use OMF format on OS/2', False),

        # Pkgconfig module
        UserBooleanOption('pkgconfig.relocatable', 'Generate pkgconfig files as relocatable', False),

        # Python module
        UserIntegerOption('python.bytecompile', 'Whether to compile bytecode', 0, min_value=-1, max_value=2),
        UserComboOption('python.install_env', 'Which python environment to install to', 'prefix',
                        choices=['auto', 'prefix', 'system', 'venv']),
        UserStringOption('python.platlibdir', 'Directory for site-specific, platform-specific files.', ''),
        UserStringOption('python.purelibdir', 'Directory for site-specific, non-platform-specific files.', ''),
        UserBooleanOption('python.allow_limited_api', 'Whether to allow use of the Python Limited API', True),
        UserStringOption('python.build_config', 'Config file containing the build details for the target Python installation.', ''),
    ])
}

BUILTIN_OPTIONS = OrderedDict(chain(BUILTIN_DIR_OPTIONS.items(), BUILTIN_CORE_OPTIONS.items()))

BUILTIN_OPTIONS_PER_MACHINE: T.Mapping[OptionKey, AnyOptionType] = {
    OptionKey(o.name): o for o in [
        UserStringArrayOption('pkg_config_path', 'List of additional paths for pkg-config to search', []),
        UserStringArrayOption('cmake_prefix_path', 'List of additional prefixes for cmake to search', []),
    ]
}

# Special prefix-dependent defaults for installation directories that reside in
# a path outside of the prefix in FHS and common usage.
BUILTIN_DIR_NOPREFIX_OPTIONS: T.Dict[OptionKey, T.Dict[str, str]] = {
    OptionKey('sysconfdir'):     {'/usr': '/etc'},
    OptionKey('localstatedir'):  {'/usr': '/var',     '/usr/local': '/var/local'},
    OptionKey('sharedstatedir'): {'/usr': '/var/lib', '/usr/local': '/var/local/lib'},
    OptionKey('python.platlibdir'): {},
    OptionKey('python.purelibdir'): {},
}

MSCRT_VALS = ['none', 'md', 'mdd', 'mt', 'mtd']

COMPILER_BASE_OPTIONS: T.Mapping[OptionKey, AnyOptionType] = {
    OptionKey(o.name): o for o in T.cast('T.List[AnyOptionType]', [
        UserBooleanOption('b_pch', 'Use precompiled headers', True),
        UserBooleanOption('b_lto', 'Use link time optimization', False),
        UserIntegerOption('b_lto_threads', 'Use multiple threads for Link Time Optimization', 0),
        UserComboOption('b_lto_mode', 'Select between different LTO modes.', 'default', choices=['default', 'thin']),
        UserBooleanOption('b_thinlto_cache', 'Use LLVM ThinLTO caching for faster incremental builds', False),
        UserStringOption('b_thinlto_cache_dir', 'Directory to store ThinLTO cache objects', ''),
        UserStringArrayOption('b_sanitize', 'Code sanitizer to use', []),
        UserBooleanOption('b_lundef', 'Use -Wl,--no-undefined when linking', True),
        UserBooleanOption('b_asneeded', 'Use -Wl,--as-needed when linking', True),
        UserComboOption(
            'b_pgo', 'Use profile guided optimization', 'off', choices=['off', 'generate', 'use']),
        UserBooleanOption('b_coverage', 'Enable coverage tracking.', False),
        UserComboOption(
            'b_colorout', 'Use colored output', 'always', choices=['auto', 'always', 'never']),
        UserBooleanOption('b_freestanding', 'Build without a hosted standard library', False),
        UserComboOption(
            'b_ndebug', 'Disable asserts', 'false', choices=['true', 'false', 'if-release']),
        UserBooleanOption('b_staticpic', 'Build static libraries as position independent', True),
        UserBooleanOption('b_pie', 'Build executables as position independent', False),
        UserBooleanOption('b_bitcode', 'Generate and embed bitcode (only macOS/iOS/tvOS)', False),
        UserComboOption(
            'b_vscrt', 'VS run-time library type to use.', 'from_buildtype',
            choices=MSCRT_VALS + ['from_buildtype', 'static_from_buildtype']),
    ])
}

class OptionSource(enum.IntEnum):
    """Where a per-project option value comes from, in order of increasing priority."""

    # compiler and linker arguments from environment variables such as $CFLAGS
    ENVIRONMENT = 0
    # default_options in the project's own project() call
    PROJECT = 1
    # default_options in the project() call of another project, as in "sub:opt=value"
    TOPLEVEL = 2
    # default_options in the subproject() or dependency() call
    SUBPROJECT = 3
    # machine file and environment variables, read on the first run and kept afterwards
    MACHINE_FILE = 4
    # command line
    COMMAND_LINE = 5
    # forced by the interpreter, e.g. from `dependency(static: true)`
    RUNTIME = 6
    # detected on the first run and kept afterwards, e.g. the Visual Studio backend
    DETECTED = 7


class OptionStore:
    DEFAULT_DEPENDENTS = {'plain': ('plain', False),
                          'debug': ('0', True),
                          'debugoptimized': ('2', True),
                          'release': ('3', False),
                          'minsize': ('s', True),
                          }

    def __init__(self, is_cross: bool) -> None:
        self.options: T.Dict['OptionKey', 'AnyOptionType'] = {}
        self.subprojects: T.Set[str] = set()
        self.project_options: T.Set[OptionKey] = set()
        self.module_options: T.Set[OptionKey] = set()
        from .compilers import all_languages
        self.all_languages = set(all_languages)
        # Values of global options; the option objects only hold the default
        self.globals: OptionDict = {}
        # Per-project values, including those of project options
        self.augments: OptionDict = {}
        self.is_cross = is_cross

        # Pending options are configuration dependent options that could be
        # initialized later, such as compiler options
        self.pending_options: OptionDict = {}
        # Per-project option values for each source, to be resolved
        # into self.augments as each project is configured.  MACHINE_FILE
        # and COMMAND_LINE also include global options, which override
        # PROJECT for subprojects.
        self.all_options: T.Dict[OptionSource, OptionDict] = {source: {} for source in OptionSource}
        # Array options whose value is extended with the value of another option,
        # if that value comes from environment variables; e.g. <lang>_link_args
        # with $CFLAGS if the compiler acts as a linker driver
        self.extra_args_from_env: T.Dict[OptionKey, OptionKey] = {}
        # Global options that were set by the last resolution of the toplevel project
        self.custom_globals: T.Set[OptionKey] = set()
        # Class for host-aware path handling
        self.pure_path_class: T.Type[pathlib.PurePath] = pathlib.PurePath

    def set_host_machine(self, machine: MachineInfo) -> None:
        """Use the given MachineInfo for host-aware path handling."""
        self.pure_path_class = machine.pure_path_class

    def _is_host_absolute(self, path: str) -> bool:
        """Check if path is absolute according to host machine path semantics."""
        path_obj = self.pure_path_class(path)
        if isinstance(path_obj, pathlib.PureWindowsPath) and path_obj.root:
            # Accept Windows root-relative paths (root but no drive, like /myprog)
            # so that the same path can be used in cross-compilation setups
            return True
        return path_obj.is_absolute()

    def ensure_and_validate_key(self, key: T.Union[OptionKey, str]) -> OptionKey:
        if isinstance(key, str):
            return OptionKey(key)
        # FIXME. When not cross building all "build" options need to fall back
        # to "host" options due to how the old code worked.
        #
        # This is NOT how it should be.
        #
        # This needs to be changed to that trying to add or access "build" keys
        # is a hard error and fix issues that arise.
        #
        # I did not do this yet, because it would make this MR even
        # more massive than it already is. Later then.
        if not (self.is_cross and self.is_per_machine_option(key)):
            key = key.as_host()
        return key

    def get_pending_value(self, key: OptionKey, default: T.Optional[ElementaryOptionValues] = None) -> ElementaryOptionValues | None:
        key = self.ensure_and_validate_key(key)
        if key in self.options:
            return self.get_value_for(key)
        return self.pending_options.get(key, default)

    def __len__(self) -> int:
        return len(self.options)

    def resolve_option(self, key: OptionKey) -> AnyOptionType:
        key = self.ensure_and_validate_key(key)
        potential = self.options.get(key, None)
        if self.is_project_option(key):
            assert key.subproject is not None
            if potential is None:
                raise KeyError(f'Tried to access nonexistant project option {key}.')
        else:
            if potential is None:
                parent_key = OptionKey(key.name, subproject=None, machine=key.machine)
                if parent_key not in self.options:
                    raise KeyError(f'Tried to access nonexistant project parent option {parent_key}.')
                # This is a global option but it can still have per-project
                # augment, so return the subproject key.
                return self.options[parent_key]
        return potential

    def get_option_and_value_for(self, key: OptionKey) -> T.Tuple[AnyOptionType, ElementaryOptionValues]:
        key = self.ensure_and_validate_key(key)
        option_object = self.resolve_option(key)
        if key in self.augments:
            assert key.subproject is not None
            computed_value = self.augments[key]
        elif option_object.yielding:
            computed_value = self.get_value_for(key.as_root())
        else:
            computed_value = self.globals.get(key.evolve(subproject=None), option_object.default)
        return (option_object, self._add_extra_args_from_env(key, computed_value))

    def _add_extra_args_from_env(self, key: OptionKey, value: ElementaryOptionValues) -> ElementaryOptionValues:
        """Add to value the arguments from environment variables that
           extra_args_from_env associates to key, if any."""
        suffix_key = self.extra_args_from_env.get(key.evolve(subproject=None))
        if suffix_key is not None and \
                self._highest_priority_source(suffix_key) is OptionSource.ENVIRONMENT:
            suffix = self.all_options[OptionSource.ENVIRONMENT][suffix_key]
            assert isinstance(value, list), 'for mypy'
            assert isinstance(suffix, list), 'for mypy'
            value = value + suffix
        return value

    def option_has_value(self, key: OptionKey, value: ElementaryOptionValues) -> bool:
        option_object, current_value = self.get_option_and_value_for(key)
        return option_object.validate_value(value) == current_value

    def get_value_for(self, name: 'T.Union[OptionKey, str]', subproject: T.Optional[str] = None) -> ElementaryOptionValues:
        if isinstance(name, str):
            key = OptionKey(name, subproject)
        else:
            assert subproject is None
            key = name
        _, resolved_value = self.get_option_and_value_for(key)
        return resolved_value

    def add_system_option(self, key: T.Union[OptionKey, str], valobj: AnyOptionType) -> None:
        key = self.ensure_and_validate_key(key)
        if '.' in key.name:
            raise MesonException(f'Internal error: non-module option has a period in its name {key.name}.')
        self.add_system_option_internal(key, valobj)

    def add_system_option_internal(self, key: OptionKey, valobj: AnyOptionType) -> None:
        assert isinstance(valobj, UserOption)
        if key in self.options:
            return

        global_key = key.evolve(subproject=None)
        added_global = global_key not in self.options
        if key.subproject is not None:
            self.add_system_option_internal(global_key, valobj)
        else:
            self.options[global_key] = valobj

        pval = self.pending_options.pop(key, None)
        if pval is None:
            return

        try:
            self.set_option(key, pval)
        except MesonException:
            # Do not leave behind an option whose value was never set, so
            # that the value is checked again if the option is added later.
            self.pending_options[key] = pval
            if added_global:
                del self.options[global_key]
                if global_key in self.globals:
                    self.pending_options[global_key] = self.globals.pop(global_key)
            raise

    def add_compiler_option(self, language: Language, key: T.Union[OptionKey, str], valobj: AnyOptionType) -> None:
        key = self.ensure_and_validate_key(key)
        if not key.name.startswith(language + '_'):
            raise MesonException(f'Internal error: all compiler option names must start with language prefix. ({key.name} vs {language}_)')
        self.add_system_option(key, valobj)

    def add_project_option(self, key: T.Union[OptionKey, str], valobj: AnyOptionType) -> None:
        key = self.ensure_and_validate_key(key)
        assert key.subproject is not None
        if key in self.options:
            raise MesonException(f'Internal error: tried to add a project option {key} that already exists.')
        if valobj.yielding and key.subproject:
            parent_key = key.as_root()
            try:
                parent_option = self.options[parent_key]
                # If parent object has different type, do not yield.
                # This should probably be an error.
                if type(parent_option) is type(valobj):
                    valobj.parent = parent_option
            except KeyError:
                # Subproject is set to yield, but top level
                # project does not have an option of the same
                pass
        valobj.yielding = valobj.parent is not None

        self.options[key] = valobj
        self.project_options.add(key)
        assert key not in self.pending_options

    def add_module_option(self, modulename: str, key: T.Union[OptionKey, str], valobj: AnyOptionType) -> None:
        key = self.ensure_and_validate_key(key)
        if key.name.startswith('build.'):
            raise MesonException('FATAL internal error: somebody goofed option handling.')
        if not key.name.startswith(modulename + '.'):
            raise MesonException('Internal error: module option name {key.name} does not start with module prefix {modulename}.')
        self.add_system_option_internal(key, valobj)
        self.module_options.add(key)

    def add_builtin_option(self, key: OptionKey, opt: AnyOptionType) -> None:
        assert key.subproject is None
        if key not in self.options:
            self.globals[key] = opt.validate_value(prefixed_default(opt, key, default_prefix()))

        modulename = key.get_module_prefix()
        if modulename:
            self.add_module_option(modulename, key, opt)
        else:
            self.add_system_option(key, opt)

    def init_builtins(self) -> None:
        # Create builtin options with default values
        for key, opt in BUILTIN_OPTIONS.items():
            self.add_builtin_option(key, opt)
        for for_machine in iter(MachineChoice):
            for key, opt in BUILTIN_OPTIONS_PER_MACHINE.items():
                self.add_builtin_option(key.evolve(machine=for_machine), opt)

    def sanitize_prefix(self, prefix: str) -> str:
        prefix = os.path.expanduser(prefix)
        if not self._is_host_absolute(prefix):
            raise MesonException(f'prefix value {prefix!r} must be an absolute path')
        if prefix.endswith('/') or prefix.endswith('\\'):
            # On Windows we need to preserve the trailing slash if the
            # string is of type 'C:\' because 'C:' is not an absolute path.
            if len(prefix) == 3 and prefix[1] == ':':
                pass
            # If prefix is a single character, preserve it since it is
            # the root directory.
            elif len(prefix) == 1:
                pass
            else:
                prefix = prefix[:-1]
        return prefix

    def sanitize_dir_option_value(self, prefix: str, option: OptionKey, value: ElementaryOptionValues) -> ElementaryOptionValues:
        '''
        If the option is an installation directory option, the value is an
        absolute path and resides within prefix, return the value
        as a path relative to the prefix. Otherwise, return it as is.

        This way everyone can do f.ex, get_option('libdir') and usually get
        the library directory relative to prefix, even though it really
        should not be relied upon.
        '''
        if not isinstance(value, str):
            return value
        path = self.pure_path_class(value)
        if option.name.endswith('dir') and path.is_absolute() and \
           option not in BUILTIN_DIR_NOPREFIX_OPTIONS:
            try:
                # Try to relativize the path.
                path = path.relative_to(prefix)
            except ValueError:
                # Path is not relative, let’s keep it as is.
                pass
            if '..' in path.parts:
                raise MesonException(
                    f"The value of the '{option}' option is '{value}' but "
                    "directory options are not allowed to contain '..'.\n"
                    f"If you need a path outside of the {prefix!r} prefix, "
                    "please use an absolute path."
                )
        # .as_posix() keeps the posix-like file separators Meson uses.
        return path.as_posix()

    def set_option(self, key: OptionKey, new_value: ElementaryOptionValues, first_invocation: bool = False) -> bool:
        changed = False
        error_key = key
        if error_key.subproject == '':
            error_key = error_key.evolve(subproject=None)

        if key.name == 'prefix':
            assert isinstance(new_value, str), 'for mypy'
            new_value = self.sanitize_prefix(new_value)
        elif self.is_builtin_option(key):
            prefix = self.get_value_for('prefix')
            assert isinstance(prefix, str), 'for mypy'
            new_value = self.sanitize_dir_option_value(prefix, key, new_value)

        try:
            opt = self.resolve_option(key)
        except KeyError:
            raise MesonException(f'Unknown option: "{error_key}".')

        if opt.deprecated is True:
            mlog.deprecation(f'Option "{error_key}" is deprecated')
        elif isinstance(opt.deprecated, list):
            for v in opt.listify(new_value):
                if v in opt.deprecated:
                    mlog.deprecation(f'Option "{error_key}" value {v!r} is deprecated')
        elif isinstance(opt.deprecated, dict):
            def replace(v: str) -> str:
                assert isinstance(opt.deprecated, dict) # No, Mypy can not tell this from two lines above
                newvalue = opt.deprecated.get(v)
                if newvalue is not None:
                    mlog.deprecation(f'Option "{error_key}" value {v!r} is replaced by {newvalue!r}')
                    return newvalue
                return v
            valarr = [replace(v) for v in opt.listify(new_value)]
            new_value = ','.join(valarr)
        elif isinstance(opt.deprecated, str):
            mlog.deprecation(f'Option "{error_key}" is replaced by {opt.deprecated!r}')
            # Change both this aption and the new one pointed to.
            changed |= self.set_option(key.evolve(name=opt.deprecated), new_value, first_invocation)

        new_value = opt.validate_value(new_value)
        global_key = key.evolve(subproject=None)
        if key.subproject is None:
            old_value = self.globals.get(key, opt.default)
            self.globals[key] = new_value
        else:
            old_value = self.augments.get(key, self.globals.get(global_key, opt.default))
            self.augments[key] = new_value

        changed |= old_value != new_value
        if opt.readonly and changed and not first_invocation:
            raise MesonException(f'Tried to modify read only option "{error_key}"')
        return changed

    def set_user_option(self, o: OptionKey, new_value: ElementaryOptionValues, first_invocation: bool = False) -> bool:
        # This is complicated by the fact that a string can have two meanings:
        #
        # default_options: 'foo=bar'
        #
        # can be either
        #
        # A) a system option in which case the subproject is None
        # B) a project option, in which case the subproject is ''
        #
        # The key parsing function can not handle the difference between the two
        # and defaults to A.
        if o in self.options:
            return self.set_option(o, new_value, first_invocation)

        # could also be an augment...
        global_option = o.evolve(subproject=None)
        if o.subproject is not None and global_option in self.options:
            return self.set_option(o, new_value, first_invocation)

        if self.accept_as_pending_option(o, first_invocation=first_invocation):
            old_value = self.pending_options.get(o, None)
            self.pending_options[o] = new_value
            return old_value is None or str(old_value) != new_value
        elif o.subproject is None:
            o = o.as_root()
            return self.set_option(o, new_value, first_invocation)
        else:
            raise MesonException(f'Unknown option: "{o}".')

    def set_from_configure_command(self, D_args: T.Dict[OptionKey, T.Optional[str]]) -> bool:
        """Update the options from the command line.  Return whether anything
           changed, in which case the options have to be resolved again, either
           with resolve_configured() or by configuring the project."""
        dirty = False
        for key, valstr in D_args.items():
            # Due to backwards compatibility we ignore all build-machine options
            # when building natively.
            if not self.is_cross and key.is_for_build():
                continue
            try:
                opt: T.Optional[AnyOptionType] = self.resolve_option(key)
            except KeyError:
                opt = None
            if valstr is None:
                removed = self.all_options[OptionSource.MACHINE_FILE].pop(key, None) is not None
                removed |= self.all_options[OptionSource.COMMAND_LINE].pop(key, None) is not None
                if not removed:
                    if opt is None:
                        raise MesonException(f"Unknown option: {key}")
                    continue
            else:
                if opt is not None and opt.readonly and opt.validate_value(valstr) != self.get_value_for(key):
                    raise MesonException(f'Tried to modify read only option "{key}"')
                old_value = self.all_options[OptionSource.COMMAND_LINE].get(key)
                self.all_options[OptionSource.COMMAND_LINE][key] = valstr
                if old_value == valstr:
                    continue

            dirty = True
        return dirty

    def resolve_configured(self) -> None:
        """Resolve again the options of the toplevel project and of the subprojects
           that were configured, for example after set_from_configure_command()."""
        self._resolve_toplevel(first_invocation=False)
        for subproject in sorted(self.subprojects):
            self._resolve_subproject(subproject, first_invocation=False)

    def _user_options(self, user_options: T.Mapping[OptionKey, T.Optional[ElementaryOptionValues]]) -> OptionDict:
        # Due to backwards compatibility we ignore all build-machine options
        # when building natively.
        return {key: valstr for key, valstr in user_options.items()
                if valstr is not None and (self.is_cross or not key.is_for_build())}

    def set_machine_file_options(self, machine_file_options: OptionDict) -> None:
        """Store the options from the machine file and environment variables.
           They are only read when the build directory is set up for the first
           time, and later changes to them are ignored."""
        self.all_options[OptionSource.MACHINE_FILE] = self._user_options(machine_file_options)

    def set_user_options(self, cmd_line_options: T.Mapping[OptionKey, T.Optional[ElementaryOptionValues]]) -> None:
        """Initialize the option store before any project is configured."""
        self.all_options[OptionSource.RUNTIME] = {}
        self.all_options[OptionSource.COMMAND_LINE] = self._user_options(cmd_line_options)
        # default_options for other projects are recorded again as the
        # projects are configured, and all subprojects are resolved again.
        self.all_options[OptionSource.TOPLEVEL] = {}
        self.subprojects = set()

    def get_value_object(self, key: OptionKey) -> AnyOptionType:
        key = self.ensure_and_validate_key(key)
        return self.options[key]

    def remove(self, key: OptionKey) -> None:
        del self.options[key]
        try:
            self.project_options.remove(key)
        except KeyError:
            pass

    def __contains__(self, key: OptionKey) -> bool:
        key = self.ensure_and_validate_key(key)
        return key in self.options

    def __repr__(self) -> str:
        return repr(self.options)

    def keys(self) -> T.KeysView[OptionKey]:
        return self.options.keys()

    def values(self) -> T.ValuesView[AnyOptionType]:
        return self.options.values()

    def items(self) -> T.ItemsView['OptionKey', 'AnyOptionType']:
        return self.options.items()

    def is_project_option(self, key: OptionKey) -> bool:
        """Convenience method to check if this is a project option."""
        return key in self.project_options

    def is_per_machine_option(self, optname: OptionKey) -> bool:
        if optname.evolve(subproject=None, machine=MachineChoice.HOST) in BUILTIN_OPTIONS_PER_MACHINE:
            return True
        return self.is_compiler_option(optname)

    def is_reserved_name(self, key: OptionKey) -> bool:
        if key.name in _BUILTIN_NAMES:
            return True
        if '_' not in key.name:
            return False
        prefix = key.name.split('_')[0]
        # Pylint seems to think that it is faster to build a set object
        # and all related work just to test whether a string has one of two
        # values. It is not, thank you very much.
        if prefix in ('b', 'backend'): # pylint: disable=R6201
            return True
        if prefix in self.all_languages:
            return True
        return False

    def is_builtin_option(self, key: OptionKey) -> bool:
        """Convenience method to check if this is a builtin option."""
        return key.name in _BUILTIN_NAMES or self.is_module_option(key)

    def is_base_option(self, key: OptionKey) -> bool:
        """Convenience method to check if this is a base option."""
        # The "startswith" check is just an optimization
        return key.name.startswith('b_') and key.evolve(subproject=None, machine=MachineChoice.HOST) in COMPILER_BASE_OPTIONS

    def is_backend_option(self, key: OptionKey) -> bool:
        """Convenience method to check if this is a backend option."""
        return key.name.startswith('backend_')

    def is_compiler_option(self, key: OptionKey) -> bool:
        """Convenience method to check if this is a compiler option."""

        # FIXME, duplicate of is_reserved_name above. Should maybe store a cache instead.
        if '_' not in key.name:
            return False
        prefix = key.name.split('_')[0]
        if prefix in self.all_languages:
            return True
        return False

    def is_module_option(self, key: OptionKey) -> bool:
        return key in self.module_options

    def hard_reset_from_prefix(self, prefix: str) -> None:
        prefix = self.sanitize_prefix(prefix)
        for optkey, prefix_mapping in BUILTIN_DIR_NOPREFIX_OPTIONS.items():
            if optkey not in self.options:
                continue
            valobj = self.options[optkey]
            if prefix in prefix_mapping:
                new_value = prefix_mapping[prefix]
            else:
                _v = valobj.default
                assert isinstance(_v, str), 'for mypy'
                new_value = _v
            self.globals[optkey] = valobj.validate_value(new_value)
        prefix_key = OptionKey('prefix')
        if prefix_key in self.options:
            self.globals[prefix_key] = self.options[prefix_key].validate_value(prefix)

    def _global_overrides_subproject(self, key: OptionKey) -> bool:
        """Whether the machine file or command line set the global value of key,
           which then wins over the subproject's own project() default_options."""
        global_key = key.evolve(subproject=None)
        return (global_key in self.all_options[OptionSource.MACHINE_FILE] or
                global_key in self.all_options[OptionSource.COMMAND_LINE]) and \
            not self.is_project_option(global_key.as_root())

    @staticmethod
    def _buildtype_first(options: OptionDict) -> OptionDict:
        """Move "buildtype" to the front, so that its expansion into "debug"
           and "optimization" comes before explicit values for them."""
        buildtype = {k: v for k, v in options.items() if k.name == 'buildtype'}
        return {**buildtype, **options}

    def _collect_values(self, subproject: str) -> OptionDict:
        """Collect the values of the options of a project from all sources;
           for the toplevel project, this includes global options.  Return
           the values after merging them.

           Values that are not set by any source anymore are removed, so
           that the caller only has to apply the new values."""
        toplevel = subproject == ''
        values: OptionDict = {}
        for source in OptionSource:
            for key, valstr in self._buildtype_first(self.all_options[source]).items():
                # Only look at the options of this project; for the toplevel
                # project, global options are included too.
                if key.subproject != subproject and not (toplevel and key.subproject is None):
                    continue
                # A subproject's own default_options do not override a global
                # option that was set in a machine file or on the command line.
                # This is an exception to the overall priorities.
                if source is OptionSource.PROJECT and not toplevel and self._global_overrides_subproject(key):
                    continue
                values[key] = valstr
                # "buildtype" is a shortcut for "debug" and "optimization".
                if key.name == 'buildtype' and isinstance(valstr, str) and valstr in self.DEFAULT_DEPENDENTS:
                    optimization, debug = self.DEFAULT_DEPENDENTS[valstr]
                    values[key.evolve(name='optimization')] = optimization
                    values[key.evolve(name='debug')] = debug

        # Values that are not set by any source anymore go back to the global
        # value or, for project options, to the default.
        for key in [k for k in self.augments if k.subproject == subproject and k not in values]:
            del self.augments[key]
        for key in [k for k in self.pending_options if k.subproject == subproject and k not in values]:
            del self.pending_options[key]
        return values

    def initialize_from_top_level_project_call(self, project_default_options: OptionDict) -> None:
        for key in [k for k in self.all_options[OptionSource.PROJECT] if not k.subproject]:
            del self.all_options[OptionSource.PROJECT][key]
        for key, valstr in project_default_options.items():
            # Due to backwards compatibility we ignore build-machine options
            # when building natively.
            if not self.is_cross and key.is_for_build():
                continue
            if key.subproject:
                # Subproject options from toplevel project() have low priority
                # and will be processed when the subproject is found
                self.all_options[OptionSource.TOPLEVEL][key] = valstr
            else:
                # Setting a project option with default_options
                # should arguably be a hard error; the default
                # value of project option should be set in the option
                # file, not in the project call.
                self.all_options[OptionSource.PROJECT][key] = valstr

        self._resolve_toplevel()

    def _resolve_toplevel(self, first_invocation: bool = True) -> None:
        """Compute the values of global options and of the toplevel project's
           options from all sources."""
        values = self._collect_values('')

        # Global options that are not set by any source anymore go back to the default.
        for key in self.custom_globals - values.keys():
            self.globals.pop(key, None)
            self.pending_options.pop(key, None)
        self.custom_globals = {k for k in values if k.subproject is None}

        # The installation prefix determines the default of some directories.
        prefix = values.get(OptionKey('prefix'), default_prefix())
        if not isinstance(prefix, str):
            raise MesonException('Incorrect type for prefix option (expected string)')
        self.hard_reset_from_prefix(prefix)

        for key, valstr in values.items():
            if key.name != 'prefix':
                self.pending_options.pop(key, None)
                self.set_user_option(key, valstr, first_invocation)

    def accept_as_pending_option(self, key: OptionKey, first_invocation: bool = False) -> bool:
        # Some base options (sanitizers etc) might get added later.
        # Permitting them all is not strictly correct.
        if self.is_compiler_option(key):
            return True
        if first_invocation and self.is_backend_option(key):
            return True
        return self.is_base_option(key)

    def initialize_from_subproject_call(self,
                                        subproject: str,
                                        spcall_default_options: OptionDict,
                                        project_default_options: OptionDict) -> None:
        # Replace the values from the previous run.
        for source in (OptionSource.PROJECT, OptionSource.SUBPROJECT):
            for key in [k for k in self.all_options[source] if k.subproject == subproject]:
                del self.all_options[source][key]

        for source, default_options in ((OptionSource.PROJECT, project_default_options),
                                        (OptionSource.SUBPROJECT, spcall_default_options)):
            for key, valstr in default_options.items():
                if key.subproject == subproject:
                    without_subp = key.evolve(subproject=None)
                    raise MesonException(f'subproject name not needed in default_options; use "{without_subp}" instead of "{key}"')

                # Due to backwards compatibility we ignore all build-machine options
                # when building natively.
                if not self.is_cross and key.is_for_build():
                    pass
                elif key.subproject is None:
                    key = key.evolve(subproject=subproject)
                    self.all_options[source][key] = valstr
                elif key.subproject == '':
                    # Options for the toplevel project in the default_options of a
                    # subproject have no effect.
                    pass
                elif key.subproject in self.subprojects and not self.option_has_value(key, valstr):
                    mlog.warning(f'option {key} is set in subproject {subproject} but has already been processed')
                else:
                    self.all_options[OptionSource.TOPLEVEL][key] = valstr

        self._resolve_subproject(subproject)
        self.subprojects.add(subproject)

    def _resolve_subproject(self, subproject: str, first_invocation: bool = True) -> None:
        """Compute the values of a subproject's options from all sources."""
        values = self._collect_values(subproject)
        for key, valstr in values.items():
            self.pending_options.pop(key, None)
            self.set_user_option(key, valstr, first_invocation)

    def _highest_priority_source(self, key: OptionKey) -> T.Optional[OptionSource]:
        """Return the source with the highest priority that sets key, or None."""
        for source in reversed(OptionSource):
            if key in self.all_options[source]:
                return source
        return None

    def set_option_suffix(self, key: OptionKey, suffix_key: OptionKey) -> None:
        """Append the value of suffix_key to the value of a global array option,
           whatever the source of the latter, if the value of suffix_key comes
           from environment variables."""
        key = self.ensure_and_validate_key(key)
        assert key.subproject is None
        self.extra_args_from_env[key] = self.ensure_and_validate_key(suffix_key)

    def compute_value_for(self, key: OptionKey) -> ElementaryOptionValues:
        """Compute the value of an option for a subproject that is known to be
           used, but whose project() has not been reached yet.  Nothing is
           stored, and the value can change once the subproject's own
           default_options are known.

           Unlike resolve(), this does not apply values that are derived from
           other options, such as those implied by "buildtype"."""
        key = self.ensure_and_validate_key(key)
        # The toplevel project is resolved before any subproject.
        if key.subproject == '' or key.subproject in self.subprojects:
            return self.get_value_for(key)

        # Same as resolve(), but only looking for the source with the highest priority.
        for source in reversed(OptionSource):
            if key not in self.all_options[source]:
                continue
            if source is OptionSource.PROJECT and self._global_overrides_subproject(key):
                continue
            value = self.resolve_option(key).validate_value(self.all_options[source][key])
            return self._add_extra_args_from_env(key, value)
        return self.get_value_for(key)

    def set_environment_options(self, env_options: T.Mapping[OptionKey, T.List[str]]) -> None:
        """Store the compiler and linker arguments from environment variables,
           which are only read on the first run."""
        self.all_options[OptionSource.ENVIRONMENT] = self._user_options(env_options)

    def set_detected_option(self, key: OptionKey, value: ElementaryOptionValues) -> None:
        """Set the value of a global option that was detected on the first run."""
        assert key.subproject is None
        self.all_options[OptionSource.DETECTED][key] = value
        self.set_option(key, value, first_invocation=True)

    def lock_readonly_option(self, key: OptionKey, value: ElementaryOptionValues) -> None:
        # A read-only option cannot change after the first run.  Enforce that its
        # initial value remains active by placing it in the highest-priority layer.
        self.set_detected_option(key, value)

    def set_runtime_option(self, key: OptionKey, value: ElementaryOptionValues) -> None:
        """Force the value of a per-project option, overriding even the
           machine file and command line."""
        assert key.subproject is not None
        self.all_options[OptionSource.RUNTIME][key] = value
        if key.subproject in self.subprojects:
            # This is the source with the highest priority, no need to resolve again.
            self.set_user_option(key, value, True)

    def update_project_options(self, project_options: MutableKeyedOptionDictType, subproject: SubProject) -> None:
        for key, value in project_options.items():
            assert key.machine is MachineChoice.HOST
            if key not in self.options:
                self.add_project_option(key, value)
                continue
            if key.subproject != subproject:
                raise MesonBugException(f'Tried to set an option for subproject {key.subproject} from {subproject}!')

            oldval = self.get_value_object(key)
            if type(oldval) is not type(value):
                self.set_option(key, value.default)
            elif choices_are_different(oldval, value):
                # If the choices have changed, use the new value, but attempt
                # to keep the old options. If they are not valid keep the new
                # defaults but warn.
                old_value = self.augments.pop(key, oldval.default)
                self.options[key] = value
                try:
                    self.augments[key] = value.validate_value(old_value)
                except MesonException:
                    mlog.warning(f'Old value(s) of {key} are no longer valid, resetting to default ({value.default}).',
                                 fatal=False)

        # Find any extranious keys for this project and remove them
        potential_removed_keys = self.options.keys() - project_options.keys()
        for key in potential_removed_keys:
            if self.is_project_option(key) and key.subproject == subproject:
                self.remove(key)
