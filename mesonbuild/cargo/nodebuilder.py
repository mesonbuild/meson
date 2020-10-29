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

"""A set of classes to simplify building AST nodes.

These provide a simplified API that allows the user to spend less time
worrying about building the AST correctly.
"""

from pathlib import Path
import contextlib
import typing as T

from .. import mparser
from ..mesonlib import MesonException

if T.TYPE_CHECKING:
    TYPE_mixed = T.Union[str, int, bool, Path, mparser.BaseNode]
    TYPE_mixed_list = T.Union[TYPE_mixed, T.Sequence[TYPE_mixed]]
    TYPE_mixed_dict = T.Dict[str, TYPE_mixed_list]


__all__ = ['NodeBuilder']


class _Builder:

    """Private helper class for shared utility functions."""

    def __init__(self, subdir: Path) -> None:
        self.subdir = subdir
        # Keep a public set of all assigned build targtets
        # This is neede to reference a target later
        self.variables: T.Set[str] = set()

    def empty(self) -> mparser.BaseNode:
        return mparser.BaseNode(0, 0, '')

    def token(self, value: 'TYPE_mixed_list' = '') -> mparser.Token:
        return mparser.Token('', self.subdir.as_posix(), 0, 0, 0, None, value)

    def nodeify(self, value: 'TYPE_mixed_list') -> mparser.BaseNode:
        if isinstance(value, str):
            return self.string(value)
        elif isinstance(value, Path):
            return self.string(value.as_posix())
        elif isinstance(value, bool):
            return self.bool(value)
        elif isinstance(value, int):
            return self.number(value)
        elif isinstance(value, list):
            return self.array(value)
        elif isinstance(value, mparser.BaseNode):
            return value
        raise RuntimeError('invalid type of value: {} ({})'.format(type(value).__name__, str(value)))

    def string(self, value: str) -> mparser.StringNode:
        return mparser.StringNode(self.token(value))

    def bool(self, value: bool) -> mparser.BooleanNode:
        return mparser.BooleanNode(self.token(value))

    def number(self, value: int) -> mparser.NumberNode:
        return mparser.NumberNode(self.token(value))

    def id(self, value: str) -> mparser.IdNode:
        return mparser.IdNode(self.token(value))

    def array(self, value: 'TYPE_mixed_list') -> mparser.ArrayNode:
        args = self.arguments(value, {})
        return mparser.ArrayNode(args, 0, 0, 0, 0)

    def arguments(self, args: 'TYPE_mixed_list', kwargs: 'TYPE_mixed_dict') -> mparser.ArgumentNode:
        node = mparser.ArgumentNode(self.token())
        node.arguments = [self.nodeify(x) for x in args]
        node.kwargs = {self.id(k): self.nodeify(v) for k, v in kwargs.items()}
        return node

    def function(self, name: str, args: T.Optional[mparser.ArgumentNode] = None) -> mparser.FunctionNode:
        if args is None:
            args = self.arguments([], {})
        return mparser.FunctionNode(self.subdir.as_posix(), 0, 0, 0, 0, name, args)

    def assign(self, name: str, value: mparser.BaseNode) -> mparser.AssignmentNode:
        return mparser.AssignmentNode(self.subdir.as_posix(), 0, 0, name, value)

    def plus_assign(self, name: str, value: mparser.BaseNode) -> mparser.PlusAssignmentNode:
        return mparser.PlusAssignmentNode(self.subdir.as_posix(), 0, 0, name, value)

    def method(self, name: str, base: mparser.BaseNode, args: mparser.ArgumentNode) -> mparser.MethodNode:
        return mparser.MethodNode('', 0, 0, base, name, args)


class ArgumentBuilder:

    def __init__(self, builder: _Builder):
        self._builder = builder
        self._posargs: T.List['TYPE_mixed'] = []
        self._kwargs: 'TYPE_mixed_dict' = {}

    def positional(self, arg: 'TYPE_mixed_list') -> None:
        self._posargs.append(arg)

    def keyword(self, name: str, arg: 'TYPE_mixed_list') -> None:
        assert name not in self._kwargs
        self._kwargs[name] = arg

    def finalize(self) -> mparser.ArgumentNode:
        # XXX: I think this is okay
        return self._builder.arguments(self._posargs, self._kwargs)


class FunctionBuilder:

    def __init__(self, name: str, builder: _Builder):
        self.name = name
        self._builder = builder
        self._arguments = builder.arguments([], {})
        self._methods: T.List[T.Tuple[str, mparser.ArgumentNode]] = []

    @contextlib.contextmanager
    def argument_builder(self) -> T.Iterator[ArgumentBuilder]:
        b = ArgumentBuilder(self._builder)
        yield b
        self._arguments = b.finalize()

    @contextlib.contextmanager
    def method_builder(self, name: str) -> T.Iterator[ArgumentBuilder]:
        b = ArgumentBuilder(self._builder)
        yield b
        self._methods.append((name, b.finalize()))

    def finalize(self) -> T.Union[mparser.FunctionNode, mparser.MethodNode]:
        cur: T.Union[mparser.FunctionNode, mparser.MethodNode] = \
            self._builder.function(self.name, self._arguments)
        # go over the methods in reversed order, emmited a Method Node for each of them
        for name, args in reversed(self._methods):
            cur = self._builder.method(name, cur, args)
        return cur


class AssignmentBuilder:

    def __init__(self, name: str, builder: _Builder):
        self.name = name
        self._builder = builder
        self._node: T.Optional[mparser.AssignmentNode] = None

    @contextlib.contextmanager
    def function_builder(self, name: str) -> T.Iterator[ArgumentBuilder]:
        b = FunctionBuilder(name, self._builder)
        with b.argument_builder() as a:
            yield a
        self._node = self._builder.assign(self.name, b.finalize())

    @contextlib.contextmanager
    def array_builder(self) -> T.Iterator[ArgumentBuilder]:
        b = ArgumentBuilder(self._builder)
        yield b
        array = mparser.ArrayNode(b.finalize(), 0, 0, 0, 0) # _builder.array expects raw arguments
        self._node = self._builder.assign(self.name, array)

    def finalize(self) -> mparser.AssignmentNode:
        assert self._node is not None, 'You need to build an assignment before finalizing'
        return self._node


class PlusAssignmentBuilder:

    def __init__(self, name: str, builder: _Builder):
        self.name = name
        self._builder = builder
        self._node: T.Optional[mparser.PlusAssignmentNode] = None

    @contextlib.contextmanager
    def function_builder(self, name: str) -> T.Iterator[ArgumentBuilder]:
        b = FunctionBuilder(name, self._builder)
        with b.argument_builder() as a:
            yield a
        self._node = self._builder.plus_assign(self.name, b.finalize())

    @contextlib.contextmanager
    def array_builder(self) -> T.Iterator[ArgumentBuilder]:
        b = ArgumentBuilder(self._builder)
        yield b
        array = mparser.ArrayNode(b.finalize(), 0, 0, 0, 0) # _builder.array expects raw arguments
        self._node = self._builder.plus_assign(self.name, array)

    def finalize(self) -> mparser.PlusAssignmentNode:
        assert self._node is not None, 'You need to build an assignment before finalizing'
        return self._node


class IfBuilder:

    def __init__(self, builder: _Builder):
        self._builder = builder
        self._condition: T.Optional[mparser.BaseNode] = None
        self._body: T.Optional[mparser.CodeBlockNode] = None

    @contextlib.contextmanager
    def condition_builder(self) -> T.Iterator['NodeBuilder']:
        b = NodeBuilder(_builder=self._builder)
        yield b
        cond = b.finalize()
        assert len(cond.lines) == 1, 'this is a bit of a hack'
        self._condition = cond.lines[0]

    @contextlib.contextmanager
    def body_builder(self) -> T.Iterator['NodeBuilder']:
        b = NodeBuilder(_builder=self._builder)
        yield b
        self._body = b.finalize()

    def finalize(self) -> T.Union[mparser.IfNode, mparser.CodeBlockNode]:
        # If this is a CodeBlockNode, it's the `else` clause
        assert self._body is not None, 'A body is required'
        if self._condition:
            return mparser.IfNode(self._builder.empty(), self._condition, self._body)
        return self._body


class IfClauseBuilder:

    def __init__(self, builder: _Builder):
        self._builder = builder
        self._node = mparser.IfClauseNode(mparser.BaseNode(0, 0, ''))

    @contextlib.contextmanager
    def if_builder(self) -> T.Iterator[IfBuilder]:
        b = IfBuilder(self._builder)
        yield b
        ret = b.finalize()
        if isinstance(ret, mparser.IfNode):
            self._node.ifs.append(ret)
        else:
            assert self._node.elseblock is None, 'Cannot create two else blocks'
            self._node.elseblock = ret

    def finalize(self) -> mparser.IfClauseNode:
        return self._node


class ObjectBuilder:

    """A way to get an object, and do things with it."""

    def __init__(self, name: str, builder: _Builder):
        self._builder = builder
        self._object = builder.id(name)
        self._methods: T.List[T.Tuple[str, mparser.ArgumentNode]] = []

    @contextlib.contextmanager
    def method_builder(self, name: str) -> T.Iterator[ArgumentBuilder]:
        b = ArgumentBuilder(self._builder)
        yield b
        self._methods.append((name, b.finalize()))

    def finalize(self) -> mparser.MethodNode:
        cur: T.Union[mparser.IdNode, mparser.MethodNode] = self._object
        assert self._methods, "Don't use ObjectBuilder for getting an id"
        for name, args in self._methods:
            cur = self._builder.method(name, cur, args)
        assert isinstance(cur, mparser.MethodNode), 'mypy and pylance need this'
        return cur


class NodeBuilder:

    """The main builder class.

    This is the only one that you want to instantiate directly, use the
    context manager methods to build the rest.

    The design of this is such that you open each new element, add it's
    arguments, and as each context manager closes it inserts itself into
    it's parent.
    """

    def __init__(self, subdir: T.Optional[Path] = None, *, _builder: T.Optional[_Builder] = None):
        assert _builder is not None or subdir is not None
        self._builder = _builder if _builder is not None else _Builder(subdir)
        self.__node = mparser.CodeBlockNode(self._builder.token())

    def append(self, node: mparser.BaseNode) -> None:
        self.__node.lines.append(node)

    def id(self, name: str) -> mparser.IdNode:
        """Create an IdNode of variable."""
        if name not in self._builder.variables:
            raise MesonException(f'Cannot create ID for non-existant variable {name}')
        return self._builder.id(name)

    def finalize(self) -> mparser.CodeBlockNode:
        return self.__node

    @contextlib.contextmanager
    def function_builder(self, name: str) -> T.Iterator[ArgumentBuilder]:
        # These are un-assigned functions, they don't go into the target dict
        b = FunctionBuilder(name, self._builder)
        with b.argument_builder() as a:
            yield a
        self.append(b.finalize())

    @contextlib.contextmanager
    def assignment_builder(self, name: str) -> T.Iterator[AssignmentBuilder]:
        b = AssignmentBuilder(name, self._builder)
        yield b

        # If we've created a target, then they need to be saved into the target dict
        target = b.finalize()
        self._builder.variables.add(b.name)
        self.append(target)

    @contextlib.contextmanager
    def plus_assignment_builder(self, name: str) -> T.Iterator[PlusAssignmentBuilder]:
        assert name in self._builder.variables, 'cannot augment a variable that isnt defined'
        b = PlusAssignmentBuilder(name, self._builder)
        yield b
        self.append(b.finalize())

    @contextlib.contextmanager
    def if_builder(self) -> T.Iterator[IfClauseBuilder]:
        b = IfClauseBuilder(self._builder)
        yield b
        self.append(b.finalize())

    @contextlib.contextmanager
    def object_builder(self, name: str) -> T.Iterator[ObjectBuilder]:
        b = ObjectBuilder(name, self._builder)
        yield b
        self.append(b.finalize())
