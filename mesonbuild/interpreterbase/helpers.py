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

from .. import mesonlib, mparser, mlog
from .exceptions import InvalidArguments, InterpreterException

import collections.abc
import typing as T

if T.TYPE_CHECKING:
    from .baseobjects import TYPE_var, TYPE_kwargs

def flatten(args: T.Union['TYPE_var', T.List['TYPE_var']]) -> T.List['TYPE_var']:
    if isinstance(args, mparser.StringNode):
        assert isinstance(args.value, str)
        return [args.value]
    if not isinstance(args, collections.abc.Sequence):
        return [args]
    result: T.List['TYPE_var'] = []
    for a in args:
        if isinstance(a, list):
            rest = flatten(a)
            result = result + rest
        elif isinstance(a, mparser.StringNode):
            result.append(a.value)
        else:
            result.append(a)
    return result

def resolve_second_level_holders(args: T.List['TYPE_var'], kwargs: 'TYPE_kwargs') -> T.Tuple[T.List['TYPE_var'], 'TYPE_kwargs']:
    def resolver(arg: 'TYPE_var') -> 'TYPE_var':
        if isinstance(arg, list):
            return [resolver(x) for x in arg]
        if isinstance(arg, dict):
            return {k: resolver(v) for k, v in arg.items()}
        if isinstance(arg, mesonlib.SecondLevelHolder):
            return arg.get_default_object()
        return arg
    return [resolver(x) for x in args], {k: resolver(v) for k, v in kwargs.items()}

def check_stringlist(a: T.Any, msg: str = 'Arguments must be strings.') -> None:
    if not isinstance(a, list):
        mlog.debug('Not a list:', str(a))
        raise InvalidArguments('Argument not a list.')
    if not all(isinstance(s, str) for s in a):
        mlog.debug('Element not a string:', str(a))
        raise InvalidArguments(msg)

def default_resolve_key(key: mparser.BaseNode) -> str:
    if not isinstance(key, mparser.IdNode):
        raise InterpreterException('Invalid kwargs format.')
    return key.value

def get_callee_args(wrapped_args: T.Sequence[T.Any], want_subproject: bool = False) -> T.Tuple[T.Any, mparser.BaseNode, T.List['TYPE_var'], 'TYPE_kwargs', T.Optional[str]]:
    s = wrapped_args[0]
    n = len(wrapped_args)
    # Raise an error if the codepaths are not there
    subproject = None  # type: T.Optional[str]
    if want_subproject and n == 2:
        if hasattr(s, 'subproject'):
            # Interpreter base types have 2 args: self, node
            node = wrapped_args[1]
            # args and kwargs are inside the node
            args = None
            kwargs = None
            subproject = s.subproject
        elif hasattr(wrapped_args[1], 'subproject'):
            # Module objects have 2 args: self, interpreter
            node = wrapped_args[1].current_node
            # args and kwargs are inside the node
            args = None
            kwargs = None
            subproject = wrapped_args[1].subproject
        else:
            raise AssertionError(f'Unknown args: {wrapped_args!r}')
    elif n == 3:
        # Methods on objects (*Holder, MesonMain, etc) have 3 args: self, args, kwargs
        node = s.current_node
        args = wrapped_args[1]
        kwargs = wrapped_args[2]
        if want_subproject:
            if hasattr(s, 'subproject'):
                subproject = s.subproject
            elif hasattr(s, 'interpreter'):
                subproject = s.interpreter.subproject
    elif n == 4:
        # Meson functions have 4 args: self, node, args, kwargs
        # Module functions have 4 args: self, state, args, kwargs
        from .interpreterbase import InterpreterBase  # TODO: refactor to avoid this import
        if isinstance(s, InterpreterBase):
            node = wrapped_args[1]
        else:
            node = wrapped_args[1].current_node
        args = wrapped_args[2]
        kwargs = wrapped_args[3]
        if want_subproject:
            if isinstance(s, InterpreterBase):
                subproject = s.subproject
            else:
                subproject = wrapped_args[1].subproject
    else:
        raise AssertionError(f'Unknown args: {wrapped_args!r}')
    # Sometimes interpreter methods are called internally with None instead of
    # empty list/dict
    args = args if args is not None else []
    kwargs = kwargs if kwargs is not None else {}
    return s, node, args, kwargs, subproject
