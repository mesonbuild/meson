# SPDX-License-Identifier: Apache-2.0
# Copyright © 2021 Intel Corporation

"""Helpers for strict type checking."""

from __future__ import annotations
import os
import typing as T

from .. import compilers
from ..build import (EnvironmentVariables, EnvInitValueType, CustomTarget, BuildTarget,
                     CustomTargetIndex, ExtractedObjects, GeneratedList, IncludeDirs)
from ..coredata import UserFeatureOption
from ..interpreterbase.decorators import KwargInfo, ContainerTypeInfo
from ..mesonlib import File, FileMode, MachineChoice, listify, has_path_sep, OptionKey
from ..programs import ExternalProgram

# Helper definition for type checks that are `Optional[T]`
NoneType: T.Type[None] = type(None)

if T.TYPE_CHECKING:
    from typing_extensions import Literal

    from ..interpreterbase import TYPE_var

def in_set_validator(choices: T.Set[str]) -> T.Callable[[str], T.Optional[str]]:
    """Check that the choice given was one of the given set."""

    def inner(check: str) -> T.Optional[str]:
        if check not in choices:
            return f"must be one of {', '.join(sorted(choices))}, not {check}"
        return None

    return inner


def _language_validator(l: T.List[str]) -> T.Optional[str]:
    """Validate language keyword argument.

    Particularly for functions like `add_compiler()`, and `add_*_args()`
    """
    diff = {a.lower() for a in l}.difference(compilers.all_languages)
    if diff:
        return f'unknown languages: {", ".join(diff)}'
    return None


def _install_mode_validator(mode: T.List[T.Union[str, bool, int]]) -> T.Optional[str]:
    """Validate the `install_mode` keyword argument.

    This is a rather odd thing, it's a scalar, or an array of 3 values in the form:
    [(str | False), (str | int | False) = False, (str | int | False) = False]
    where the second and third components are not required and default to False.
    """
    if not mode:
        return None
    if True in mode:
        return 'components can only be permission strings, numbers, or False'
    if len(mode) > 3:
        return 'may have at most 3 elements'

    perms = mode[0]
    if not isinstance(perms, (str, bool)):
        return 'first component must be a permissions string or False'

    if isinstance(perms, str):
        if not len(perms) == 9:
            return ('permissions string must be exactly 9 characters in the form rwxr-xr-x,'
                    f' got {len(perms)}')
        for i in [0, 3, 6]:
            if perms[i] not in {'-', 'r'}:
                return f'permissions character {i+1} must be "-" or "r", not {perms[i]}'
        for i in [1, 4, 7]:
            if perms[i] not in {'-', 'w'}:
                return f'permissions character {i+1} must be "-" or "w", not {perms[i]}'
        for i in [2, 5]:
            if perms[i] not in {'-', 'x', 's', 'S'}:
                return f'permissions character {i+1} must be "-", "s", "S", or "x", not {perms[i]}'
        if perms[8] not in {'-', 'x', 't', 'T'}:
            return f'permission character 9 must be "-", "t", "T", or "x", not {perms[8]}'

        if len(mode) >= 2 and not isinstance(mode[1], (int, str, bool)):
            return 'second componenent can only be a string, number, or False'
        if len(mode) >= 3 and not isinstance(mode[2], (int, str, bool)):
            return 'third componenent can only be a string, number, or False'

    return None


def _install_mode_convertor(mode: T.Optional[T.List[T.Union[str, bool, int]]]) -> FileMode:
    """Convert the DSL form of the `install_mode` keyword argument to `FileMode`

    This is not required, and if not required returns None

    TODO: It's not clear to me why this needs to be None and not just return an
    empty FileMode.
    """
    # this has already been validated by the validator
    return FileMode(*(m if isinstance(m, str) else None for m in mode))


def _lower_strlist(input: T.List[str]) -> T.List[str]:
    """Lower a list of strings.

    mypy (but not pyright) gets confused about using a lambda as the convertor function
    """
    return [i.lower() for i in input]


NATIVE_KW = KwargInfo(
    'native', bool,
    default=False,
    convertor=lambda n: MachineChoice.BUILD if n else MachineChoice.HOST)

LANGUAGE_KW = KwargInfo(
    'language', ContainerTypeInfo(list, str, allow_empty=False),
    listify=True,
    required=True,
    validator=_language_validator,
    convertor=_lower_strlist)

INSTALL_MODE_KW: KwargInfo[T.List[T.Union[str, bool, int]]] = KwargInfo(
    'install_mode',
    ContainerTypeInfo(list, (str, bool, int)),
    listify=True,
    default=[],
    validator=_install_mode_validator,
    convertor=_install_mode_convertor,
)

REQUIRED_KW: KwargInfo[T.Union[bool, UserFeatureOption]] = KwargInfo(
    'required',
    (bool, UserFeatureOption),
    default=True,
    # TODO: extract_required_kwarg could be converted to a convertor
)

DISABLER_KW: KwargInfo[bool] = KwargInfo('disabler', bool, default=False)

def _env_validator(value: T.Union[EnvironmentVariables, T.List['TYPE_var'], T.Dict[str, 'TYPE_var'], str, None],
                   allow_dict_list: bool = True) -> T.Optional[str]:
    def _splitter(v: str) -> T.Optional[str]:
        split = v.split('=', 1)
        if len(split) == 1:
            return f'"{v}" is not two string values separated by an "="'
        return None

    if isinstance(value, str):
        v = _splitter(value)
        if v is not None:
            return v
    elif isinstance(value, list):
        for i in listify(value):
            if not isinstance(i, str):
                return f"All array elements must be a string, not {i!r}"
            v = _splitter(i)
            if v is not None:
                return v
    elif isinstance(value, dict):
        # We don't need to spilt here, just do the type checking
        for k, dv in value.items():
            if allow_dict_list:
                if any(i for i in listify(dv) if not isinstance(i, str)):
                    return f"Dictionary element {k} must be a string or list of strings not {dv!r}"
            elif not isinstance(dv, str):
                return f"Dictionary element {k} must be a string not {dv!r}"
    # We know that otherwise we have an EnvironmentVariables object or None, and
    # we're okay at this point
    return None

def _options_validator(value: T.Union[EnvironmentVariables, T.List['TYPE_var'], T.Dict[str, 'TYPE_var'], str, None]) -> T.Optional[str]:
    # Reusing the env validator is a littl overkill, but nicer than duplicating the code
    return _env_validator(value, allow_dict_list=False)

def split_equal_string(input: str) -> T.Tuple[str, str]:
    """Split a string in the form `x=y`

    This assumes that the string has already been validated to split properly.
    """
    a, b = input.split('=', 1)
    return (a, b)

_FullEnvInitValueType = T.Union[EnvironmentVariables, T.List[str], T.List[T.List[str]], EnvInitValueType, str, None]

# Split _env_convertor() and env_convertor_with_method() to make mypy happy.
# It does not want extra arguments in KwargInfo convertor callable.
def env_convertor_with_method(value: _FullEnvInitValueType,
                              init_method: Literal['set', 'prepend', 'append'] = 'set',
                              separator: str = os.pathsep) -> EnvironmentVariables:
    if isinstance(value, str):
        return EnvironmentVariables(dict([split_equal_string(value)]), init_method, separator)
    elif isinstance(value, list):
        return EnvironmentVariables(dict(split_equal_string(v) for v in listify(value)), init_method, separator)
    elif isinstance(value, dict):
        return EnvironmentVariables(value, init_method, separator)
    elif value is None:
        return EnvironmentVariables()
    return value

def _env_convertor(value: _FullEnvInitValueType) -> EnvironmentVariables:
    return env_convertor_with_method(value)

ENV_KW: KwargInfo[T.Union[EnvironmentVariables, T.List, T.Dict, str, None]] = KwargInfo(
    'env',
    (EnvironmentVariables, list, dict, str, NoneType),
    validator=_env_validator,
    convertor=_env_convertor,
)

DEPFILE_KW: KwargInfo[T.Optional[str]] = KwargInfo(
    'depfile',
    (str, type(None)),
    validator=lambda x: 'Depfile must be a plain filename with a subdirectory' if has_path_sep(x) else None
)

# TODO: CustomTargetIndex should be supported here as well
DEPENDS_KW: KwargInfo[T.List[T.Union[BuildTarget, CustomTarget]]] = KwargInfo(
    'depends',
    ContainerTypeInfo(list, (BuildTarget, CustomTarget)),
    listify=True,
    default=[],
)

DEPEND_FILES_KW: KwargInfo[T.List[T.Union[str, File]]] = KwargInfo(
    'depend_files',
    ContainerTypeInfo(list, (File, str)),
    listify=True,
    default=[],
)

COMMAND_KW: KwargInfo[T.List[T.Union[str, BuildTarget, CustomTarget, CustomTargetIndex, ExternalProgram, File]]] = KwargInfo(
    'command',
    # TODO: should accept CustomTargetIndex as well?
    ContainerTypeInfo(list, (str, BuildTarget, CustomTarget, CustomTargetIndex, ExternalProgram, File), allow_empty=False),
    required=True,
    listify=True,
    default=[],
)

def _override_options_convertor(raw: T.List[str]) -> T.Dict[OptionKey, str]:
    output: T.Dict[OptionKey, str] = {}
    for each in raw:
        k, v = split_equal_string(each)
        output[OptionKey.from_string(k)] = v
    return output


OVERRIDE_OPTIONS_KW: KwargInfo[T.List[str]] = KwargInfo(
    'override_options',
    ContainerTypeInfo(list, str),
    listify=True,
    default=[],
    validator=_options_validator,
    convertor=_override_options_convertor,
)


def _output_validator(outputs: T.List[str]) -> T.Optional[str]:
    for i in outputs:
        if i == '':
            return 'Output must not be empty.'
        elif i.strip() == '':
            return 'Output must not consist only of whitespace.'
        elif has_path_sep(i):
            return f'Output {i!r} must not contain a path segment.'
        elif '@INPUT' in i:
            return f'output {i!r} contains "@INPUT", which is invalid. Did you mean "@PLAINNAME@" or "@BASENAME@?'

    return None

CT_OUTPUT_KW: KwargInfo[T.List[str]] = KwargInfo(
    'output',
    ContainerTypeInfo(list, str, allow_empty=False),
    listify=True,
    required=True,
    default=[],
    validator=_output_validator,
)

CT_INPUT_KW: KwargInfo[T.List[T.Union[str, File, ExternalProgram, BuildTarget, CustomTarget, CustomTargetIndex, ExtractedObjects, GeneratedList]]] = KwargInfo(
    'input',
    ContainerTypeInfo(list, (str, File, ExternalProgram, BuildTarget, CustomTarget, CustomTargetIndex, ExtractedObjects, GeneratedList)),
    listify=True,
    default=[],
)

CT_INSTALL_TAG_KW: KwargInfo[T.List[T.Union[str, bool]]] = KwargInfo(
    'install_tag',
    ContainerTypeInfo(list, (str, bool)),
    listify=True,
    default=[],
    since='0.60.0',
    convertor=lambda x: [y if isinstance(y, str) else None for y in x],
)

INSTALL_TAG_KW: KwargInfo[T.Optional[str]] = KwargInfo('install_tag', (str, NoneType))

INSTALL_KW = KwargInfo('install', bool, default=False)

CT_INSTALL_DIR_KW: KwargInfo[T.List[T.Union[str, bool]]] = KwargInfo(
    'install_dir',
    ContainerTypeInfo(list, (str, bool)),
    listify=True,
    default=[],
)

CT_BUILD_BY_DEFAULT: KwargInfo[T.Optional[bool]] = KwargInfo('build_by_default', (bool, type(None)), since='0.40.0')

CT_BUILD_ALWAYS: KwargInfo[T.Optional[bool]] = KwargInfo(
    'build_always', (bool, NoneType),
    deprecated='0.47.0',
    deprecated_message='combine build_by_default and build_always_stale instead.',
)

CT_BUILD_ALWAYS_STALE: KwargInfo[T.Optional[bool]] = KwargInfo(
    'build_always_stale', (bool, NoneType),
    since='0.47.0',
)

INCLUDE_DIRECTORIES: KwargInfo[T.List[T.Union[str, IncludeDirs]]] = KwargInfo(
    'include_dirs',
    ContainerTypeInfo(list, (str, IncludeDirs)),
    listify=True,
    default=[],
)

# for cases like default_options and override_options
DEFAULT_OPTIONS: KwargInfo[T.List[str]] = KwargInfo(
    'default_options',
    ContainerTypeInfo(list, (str, IncludeDirs)),
    listify=True,
    default=[],
    validator=_options_validator,
)

ENV_METHOD_KW = KwargInfo('method', str, default='set', since='0.62.0',
    validator=in_set_validator({'set', 'prepend', 'append'}))

ENV_SEPARATOR_KW = KwargInfo('separator', str, default=os.pathsep, since='0.62.0')
