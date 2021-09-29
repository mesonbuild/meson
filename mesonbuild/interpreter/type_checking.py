# SPDX-License-Identifier: Apache-2.0
# Copyright © 2021 Intel Corporation

"""Helpers for strict type checking."""

import typing as T

from .. import compilers
from ..build import EnvironmentVariables
from ..coredata import UserFeatureOption
from ..interpreterbase import TYPE_var
from ..interpreterbase.decorators import KwargInfo, ContainerTypeInfo
from ..mesonlib import FileMode, MachineChoice, listify

# Helper definition for type checks that are `Optional[T]`
NoneType: T.Type[None] = type(None)


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
    Where the second and third arguments are not required, and are considered to
    default to False.
    """
    if not mode:
        return None
    if True in mode:
        return 'can only be a string or false, not true'
    if len(mode) > 3:
        return 'may have at most 3 elements'

    perms = mode[0]
    if not isinstance(perms, (str, bool)):
        return 'permissions part must be a string or false'

    if isinstance(perms, str):
        if not len(perms) == 9:
            return (f'permissions string must be exactly 9 characters, got "{len(perms)}" '
                   'in the form rwxr-xr-x')
        for i in [0, 3, 6]:
            if perms[i] not in {'-', 'r'}:
                return f'bit {i} must be "-" or "r", not {perms[i]}'
        for i in [1, 4, 7]:
            if perms[i] not in {'-', 'w'}:
                return f'bit {i} must be "-" or "w", not {perms[i]}'
        for i in [2, 5]:
            if perms[i] not in {'-', 'x', 's', 'S'}:
                return f'bit {i} must be "-", "s", "S", or "x", not {perms[i]}'
        if perms[8] not in {'-', 'x', 't', 'T'}:
            return f'bit 8 must be "-", "t", "T", or "x", not {perms[8]}'

        if len(mode) >= 2 and not isinstance(mode[1], (int, str, bool)):
            return 'second componenent must be a string, number, or False if provided'
        if len(mode) >= 3 and not isinstance(mode[2], (int, str, bool)):
            return 'third componenent must be a string, number, or False if provided'

    return None


def _install_mode_convertor(mode: T.Optional[T.List[T.Union[str, bool, int]]]) -> FileMode:
    """Convert the DSL form of the `install_mode` keyword arugment to `FileMode`

    This is not required, and if not required returns None

    TODO: It's not clear to me why this needs to be None and not just return an
    emtpy FileMode.
    """
    # this has already been validated by the validator
    return FileMode(*[m if isinstance(m, str) else None for m in mode])


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

def _env_validator(value: T.Union[EnvironmentVariables, T.List['TYPE_var'], T.Dict[str, 'TYPE_var'], str, None]) -> T.Optional[str]:
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
            if not isinstance(dv, str):
                return f"Dictionary element {k} must be a string not {dv!r}"
    # We know that otherwise we have an EnvironmentVariables object or None, and
    # we're okay at this point
    return None


def _env_convertor(value: T.Union[EnvironmentVariables, T.List[str], T.Dict[str, str], str, None]) -> EnvironmentVariables:
    def splitter(input: str) -> T.Tuple[str, str]:
        a, b = input.split('=', 1)
        return (a.strip(), b.strip())

    if isinstance(value, (str, list)):
        return EnvironmentVariables(dict(splitter(v) for v in listify(value)))
    elif isinstance(value, dict):
        return EnvironmentVariables(value)
    elif value is None:
        return EnvironmentVariables()
    return value


ENV_KW: KwargInfo[T.Union[EnvironmentVariables, T.List, T.Dict, str, None]] = KwargInfo(
    'env',
    (EnvironmentVariables, list, dict, str, NoneType),
    validator=_env_validator,
    convertor=_env_convertor,
)
