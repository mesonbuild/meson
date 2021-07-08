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

from .baseobjects import InterpreterObject, MesonInterpreterObject, ObjectHolder, TYPE_var
from .exceptions import InvalidArguments
from ..mesonlib import HoldableObject, MesonBugException

import typing as T

def _unholder(obj: T.Union[TYPE_var, InterpreterObject], *, permissive: bool = False) -> TYPE_var:
    if isinstance(obj, (int, bool, str)):
        return obj
    elif isinstance(obj, list):
        return [_unholder(x, permissive=permissive) for x in obj]
    elif isinstance(obj, dict):
        return {k: _unholder(v, permissive=permissive) for k, v in obj.items()}
    elif isinstance(obj, ObjectHolder):
        assert isinstance(obj.held_object, HoldableObject)
        return obj.held_object
    elif isinstance(obj, MesonInterpreterObject):
        return obj
    elif isinstance(obj, HoldableObject) and permissive:
        return obj
    elif isinstance(obj, HoldableObject):
        raise MesonBugException(f'Argument {obj} of type {type(obj).__name__} is not held by an ObjectHolder.')
    elif isinstance(obj, InterpreterObject):
        raise InvalidArguments(f'Argument {obj} of type {type(obj).__name__} cannot be passed to a method or function')
    raise MesonBugException(f'Unknown object {obj} of type {type(obj).__name__} in the parameters.')
