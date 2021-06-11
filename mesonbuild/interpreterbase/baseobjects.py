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
from .helpers import flatten

import typing as T

TV_fw_var = T.Union[str, int, float, bool, list, dict, 'InterpreterObject']
TV_fw_args = T.List[T.Union[mparser.BaseNode, TV_fw_var]]
TV_fw_kwargs = T.Dict[str, T.Union[mparser.BaseNode, TV_fw_var]]

TV_func = T.TypeVar('TV_func', bound=T.Callable[..., T.Any])

TYPE_elementary = T.Union[str, int, float, bool]
TYPE_var = T.Union[TYPE_elementary, T.List[T.Any], T.Dict[str, T.Any], 'InterpreterObject']
TYPE_nvar = T.Union[TYPE_var, mparser.BaseNode]
TYPE_nkwargs = T.Dict[str, TYPE_nvar]
TYPE_key_resolver = T.Callable[[mparser.BaseNode], str]

class InterpreterObject:
    def __init__(self, *, subproject: T.Optional[str] = None) -> None:
        self.methods = {}  # type: T.Dict[str, T.Callable[[T.List[TYPE_nvar], TYPE_nkwargs], TYPE_var]]
        # Current node set during a method call. This can be used as location
        # when printing a warning message during a method call.
        self.current_node:  mparser.BaseNode = None
        self.subproject: str = subproject or ''

    def method_call(
                self,
                method_name: str,
                args: TV_fw_args,
                kwargs: TV_fw_kwargs
            ) -> TYPE_var:
        if method_name in self.methods:
            method = self.methods[method_name]
            if not getattr(method, 'no-args-flattening', False):
                args = flatten(args)
            return method(args, kwargs)
        raise InvalidCode('Unknown method "%s" in object.' % method_name)

class MesonInterpreterObject(InterpreterObject):
    ''' All non-elementary objects should be derived from this '''

class MutableInterpreterObject:
    ''' Dummy class to mark the object type as mutable '''

TV_InterpreterObject = T.TypeVar('TV_InterpreterObject')

class ObjectHolder(MesonInterpreterObject, T.Generic[TV_InterpreterObject]):
    def __init__(self, obj: TV_InterpreterObject, *, subproject: T.Optional[str] = None) -> None:
        super().__init__(subproject=subproject)
        self.held_object = obj

    def __repr__(self) -> str:
        return f'<Holder: {self.held_object!r}>'

class RangeHolder(MesonInterpreterObject):
    def __init__(self, start: int, stop: int, step: int, *, subproject: T.Optional[str] = None) -> None:
        super().__init__(subproject=subproject)
        self.range = range(start, stop, step)

    def __iter__(self) -> T.Iterator[int]:
        return iter(self.range)

    def __getitem__(self, key: int) -> int:
        return self.range[key]

    def __len__(self) -> int:
        return len(self.range)
