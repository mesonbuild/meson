# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Intel Corporation

"""An abstract IR for compile arguments.

This provides us with a way to pass arguments around in a non-compiler specific
way internally, and lower them into a non-abstract format when writing them in
the backend.
"""

from __future__ import annotations
import dataclasses
import typing as T

if T.TYPE_CHECKING:
    from typing_extensions import TypeAlias

    # A Union of all Argument types
    Argument: TypeAlias = T.Union[
        'Opaque', 'Warning', 'Error', 'Define', 'Undefine', 'LinkerSearch',
        'LinkLibrary', 'Rpath',
    ]


@dataclasses.dataclass
class Opaque:

    """An opaque argument.

    This is an argument of unknown type, and Meson will do nothing but proxy it
    through, except to apply a prefix to the value if it thinks it's necessary.

    :param value:
    """

    value: str


@dataclasses.dataclass
class Warning:

    """A compiler warning.

    :param target: The warning to enable or disable. This will be stored as
        given (ie, we don't try to convert between compilers).
    :param enable: If true then enable the warning, otherwise suppress it.
    """

    target: str
    enable: bool


@dataclasses.dataclass
class Error:

    """A compiler error.

    :param target: The warning to enable or disable. This will be stored as
        given (ie, we don't try to convert between compilers).
    """

    target: str


@dataclasses.dataclass
class Define:

    """A pre-processor define.

    :param target: The value to define.
    :param value: An optional value to set the define to. If undefined them the
        value will be defined with no value.
    """

    target: str
    value: T.Optional[str]


@dataclasses.dataclass
class Undefine:

    """A pre-processor undefine.

    :param target: The value to define.
    """

    target: str


@dataclasses.dataclass
class LinkerSearch:

    """A location for the linker to search for libraries.

    :param path: The path to search.
    """

    path: str


@dataclasses.dataclass
class LinkLibrary:

    """A library to link with.

    :param name: The name of the library to link.
    :param absolute: If the path is an absolute path
    """

    name: str
    absolute: bool = False


class Rpath:

    """A runtime-path to add to a linked library.

    :param path: the path to add
    """

    path: str


# TODO: rpath
# TODO: rust cfgs
# TODO: other flags we might handle differently and want to convert like lto, sanitizers, etc
