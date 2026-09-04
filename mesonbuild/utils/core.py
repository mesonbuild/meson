# SPDX-License-Identifier: Apache-2.0
# Copyright 2012-2022 The Meson development team

"""
Contains the strict minimum to run scripts.

When the backend needs to call back into Meson during compilation for running
scripts or wrapping commands, it is important to load as little python modules
as possible for performance reasons.
"""

from __future__ import annotations

import builtins
import os
import typing as T
from dataclasses import dataclass

if T.TYPE_CHECKING:
    from hashlib import _Hash
    from typing import Literal

    from .. import programs
    from ..mparser import BaseNode
    from .universal import SubProject

    EnvironOrDict = T.Union[dict[str, str], os._Environ[str]]

    EnvInitValueType = dict[str, str | list[str]]


class MesonException(Exception):
    '''Exceptions thrown by Meson'''

    def __init__(self, *args: object, file: str | None = None,
                 lineno: int | None = None, colno: int | None = None):
        super().__init__(*args)
        self.file = file
        self.lineno = lineno
        self.colno = colno

    @classmethod
    def from_node(cls, *args: object, node: BaseNode) -> MesonException:
        """Create a MesonException with location data from a BaseNode

        :param node: A BaseNode to set location data from
        :return: A Meson Exception instance
        """
        return cls(*args, file=node.filename, lineno=node.lineno, colno=node.colno)

class MesonBugException(MesonException):
    '''Exceptions thrown when there is a clear Meson bug that should be reported'''

    def __init__(self, msg: str, file: str | None = None,
                 lineno: int | None = None, colno: int | None = None):
        super().__init__(msg + '\n\n    This is a Meson bug and should be reported!',
                         file=file, lineno=lineno, colno=colno)

class HoldableObject:
    ''' Dummy base class for all objects that can be
        held by an interpreter.baseobjects.ObjectHolder '''
    def __new__(cls, *args: T.Any, **kwargs: T.Any) -> HoldableObject:
        if cls is HoldableObject:
            raise TypeError(f"Can't instantiate abstract class {cls.__name__}")
        return super().__new__(cls)

class EnvironmentVariables(HoldableObject):
    def __init__(self, values: EnvInitValueType | None = None,
                 init_method: Literal['set', 'prepend', 'append'] = 'set', separator: str = os.pathsep) -> None:
        self.envvars: list[tuple[T.Callable[[dict[str, str], str, list[str], str, str | None], str], str, list[str], str]] = []
        # The set of all env vars we have operations for. Only used for self.has_name()
        self.varnames: set[str] = set()
        self.unset_vars: set[str] = set()
        self.can_use_env = True

        if values:
            init_func = getattr(self, init_method)
            for name, value in values.items():
                v = value if isinstance(value, list) else [value]
                init_func(name, v, separator)

    def __repr__(self) -> str:
        repr_str = "<{0}: {1}>"
        return repr_str.format(self.__class__.__name__, self.envvars)

    def hash(self, hasher: _Hash) -> None:
        myenv = self.get_env({})
        for key in sorted(myenv.keys()):
            hasher.update(bytes(key, encoding='utf-8'))
            hasher.update(b',')
            hasher.update(bytes(myenv[key], encoding='utf-8'))
            hasher.update(b';')

    def has_name(self, name: str) -> bool:
        return name in self.varnames

    def get_names(self) -> builtins.set[str]:
        return self.varnames

    def merge(self, other: EnvironmentVariables) -> None:
        for method, name, values, separator in other.envvars:
            self.varnames.add(name)
            self.envvars.append((method, name, values, separator))
            if name in self.unset_vars:
                self.unset_vars.remove(name)
        if other.unset_vars:
            self.can_use_env = False
            self.unset_vars.update(other.unset_vars)

    def set(self, name: str, values: list[str], separator: str = os.pathsep) -> None:
        if name in self.unset_vars:
            raise MesonException(f'You cannot set the already unset variable {name!r}')
        self.varnames.add(name)
        self.envvars.append((self._set, name, values, separator))

    def unset(self, name: str) -> None:
        self.can_use_env = False
        if name in self.varnames:
            raise MesonException(f'You cannot unset the {name!r} variable because it is already set')
        self.unset_vars.add(name)

    def append(self, name: str, values: list[str], separator: str = os.pathsep) -> None:
        self.can_use_env = False
        if name in self.unset_vars:
            raise MesonException(f'You cannot append to unset variable {name!r}')
        self.varnames.add(name)
        self.envvars.append((self._append, name, values, separator))

    def prepend(self, name: str, values: list[str], separator: str = os.pathsep) -> None:
        self.can_use_env = False
        if name in self.unset_vars:
            raise MesonException(f'You cannot prepend to unset variable {name!r}')
        self.varnames.add(name)
        self.envvars.append((self._prepend, name, values, separator))

    @staticmethod
    def _set(env: dict[str, str], name: str, values: list[str], separator: str, default_value: str | None) -> str:
        return separator.join(values)

    @staticmethod
    def _append(env: dict[str, str], name: str, values: list[str], separator: str, default_value: str | None) -> str:
        curr = env.get(name, default_value)
        return separator.join(values if curr is None else [curr] + values)

    @staticmethod
    def _prepend(env: dict[str, str], name: str, values: list[str], separator: str, default_value: str | None) -> str:
        curr = env.get(name, default_value)
        return separator.join(values if curr is None else values + [curr])

    def get_env(self, full_env: EnvironOrDict, default_fmt: str | None = None) -> dict[str, str]:
        env = full_env.copy()
        for method, name, values, separator in self.envvars:
            default_value = default_fmt.format(name) if default_fmt else None
            env[name] = method(env, name, values, separator, default_value)
        for name in self.unset_vars:
            env.pop(name, None)
        return env


@dataclass(eq=False)
class ExecutableSerialisation:

    cmd_args: list[str]
    env: EnvironmentVariables | None = None
    exe_wrapper: programs.ExternalProgram | None = None
    workdir: str | None = None
    extra_paths: list | None = None
    capture: str | None = None
    feed: str | None = None
    tag: str | None = None
    verbose: bool = False
    installdir_map: dict[str, str] | None = None

    def __post_init__(self) -> None:
        self.pickled = False
        self.skip_if_destdir = False
        self.subproject = T.cast('SubProject', '')  # avoid circular import
        self.dry_run = False
