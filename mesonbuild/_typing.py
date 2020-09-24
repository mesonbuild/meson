# Copyright 2020 The Meson development team
# Copyright © 2020 Intel Corporation

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Meson specific typing helpers.

This module does some wrapping of typing vs typing_extensions for older
versions of python, and holds typing only helpers such as protocols.
"""

__all__ = [
    'Protocol',
    'TypedDict',
    'ImmutableListProtocol'
]

import typing

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict

try:
    from typing import Protocol
except ImportError:
    # Yes, mypy complains about this. no, it's not a problem
    from typing_extensions import Protocol  # type: ignore


T = typing.TypeVar('T')


class ImmutableListProtocol(Protocol[T]):

    """A protocol used in cases where a list is returned, but should not be
    mutated directly.

    This provides all of the methods of a Sequence, as well as copy(). copy()
    returns a list, which allows mutation as it's a copy and that's (hopefully) safe.
    """

    def __iter__(self) -> typing.Iterator[T]: ...

    @typing.overload
    def __getitem__(self, index: int) -> T:...
    @typing.overload
    def __getitem__(self, index: slice) -> typing.List[T]: ...

    def __contains__(self, item: T) -> bool: ...

    def __reversed__(self) -> T.Iterator[T]: ...

    def __len__(self) -> int: ...

    def __add__(self, other: typing.List[T]) -> typing.List[T]: ...

    def count(self, item: T) -> int: ...

    def index(self, item: T) -> int: ...

    def copy(self) -> typing.List[T]: ...
