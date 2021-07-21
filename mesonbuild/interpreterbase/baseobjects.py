# Copyright 2013-2021 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .. import mparser
from .exceptions import InvalidCode
from .helpers import flatten, resolve_second_level_holders
from ..mesonlib import HoldableObject

import typing as T

if T.TYPE_CHECKING:
    # Object holders need the actual interpreter
    from ..interpreter import Interpreter

TV_fw_var = T.Union[str, int, bool, list, dict, 'InterpreterObject']
TV_fw_args = T.List[T.Union[mparser.BaseNode, TV_fw_var]]
TV_fw_kwargs = T.Dict[str, T.Union[mparser.BaseNode, TV_fw_var]]

TV_func = T.TypeVar('TV_func', bound=T.Callable[..., T.Any])

TYPE_elementary = T.Union[str, int, bool, T.List[T.Any], T.Dict[str, T.Any]]
TYPE_var = T.Union[TYPE_elementary, HoldableObject, 'MesonInterpreterObject']
TYPE_nvar = T.Union[TYPE_var, mparser.BaseNode]
TYPE_kwargs = T.Dict[str, TYPE_var]
TYPE_nkwargs = T.Dict[str, TYPE_nvar]
TYPE_key_resolver = T.Callable[[mparser.BaseNode], str]

class InterpreterObject:
    def __init__(self, *, subproject: T.Optional[str] = None) -> None:
        self.methods: T.Dict[
            str,
            T.Callable[[T.List[TYPE_var], TYPE_kwargs], TYPE_var]
        ] = {}
        # Current node set during a method call. This can be used as location
        # when printing a warning message during a method call.
        self.current_node:  mparser.BaseNode = None
        self.subproject: str = subproject or ''

    def method_call(
                self,
                method_name: str,
                args: T.List[TYPE_var],
                kwargs: TYPE_kwargs
            ) -> TYPE_var:
        if method_name in self.methods:
            method = self.methods[method_name]
            if not getattr(method, 'no-args-flattening', False):
                args = flatten(args)
            if not getattr(method, 'no-second-level-holder-flattening', False):
                args, kwargs = resolve_second_level_holders(args, kwargs)
            return method(args, kwargs)
        raise InvalidCode(f'Unknown method "{method_name}" in object {self} of type {type(self).__name__}.')

class MesonInterpreterObject(InterpreterObject):
    ''' All non-elementary objects and non-object-holders should be derived from this '''

class MutableInterpreterObject:
    ''' Dummy class to mark the object type as mutable '''

InterpreterObjectTypeVar = T.TypeVar('InterpreterObjectTypeVar', bound=HoldableObject)

class ObjectHolder(InterpreterObject, T.Generic[InterpreterObjectTypeVar]):
    def __init__(self, obj: InterpreterObjectTypeVar, interpreter: 'Interpreter') -> None:
        super().__init__(subproject=interpreter.subproject)
        assert isinstance(obj, HoldableObject), f'This is a bug: Trying to hold object of type `{type(obj).__name__}` that is not an `HoldableObject`'
        self.held_object = obj
        self.interpreter = interpreter
        self.env = self.interpreter.environment

    def __repr__(self) -> str:
        return f'<[{type(self).__name__}] holds [{type(self.held_object).__name__}]: {self.held_object!r}>'

class RangeHolder(MesonInterpreterObject):
    def __init__(self, start: int, stop: int, step: int, *, subproject: str) -> None:
        super().__init__(subproject=subproject)
        self.range = range(start, stop, step)

    def __iter__(self) -> T.Iterator[int]:
        return iter(self.range)

    def __getitem__(self, key: int) -> int:
        return self.range[key]

    def __len__(self) -> int:
        return len(self.range)
