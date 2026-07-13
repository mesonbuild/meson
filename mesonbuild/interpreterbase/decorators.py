# SPDX-License-Identifier: Apache-2.0
# Copyright 2013-2021 The Meson development team

from __future__ import annotations

from .. import coredata, mesonlib, mlog
from .disabler import Disabler
from .baseobjects import DefaultObject
from .exceptions import InterpreterException, InvalidArguments
from ._unholder import _unholder

from functools import wraps
import abc
import dataclasses
import itertools
import copy
import typing as T

_T = T.TypeVar('_T')

if T.TYPE_CHECKING:
    from typing_extensions import Protocol, TypeAlias, TypeIs, Unpack

    from .. import mparser
    from ..mesonlib import SubProject
    from ..modules import ModuleObject, ModuleState
    from ..mparser import FunctionNode
    from ..optinterpreter import OptionInterpreter
    from .baseobjects import InterpreterObject, ObjectHolder, TV_func, TYPE_var, TYPE_kwargs
    from .interpreterbase import InterpreterBase
    from .operator import MesonOperator

    _TV_IntegerObject = T.TypeVar('_TV_IntegerObject', bound=InterpreterObject, contravariant=True)
    _TV_ARG1 = T.TypeVar('_TV_ARG1', bound=TYPE_var, contravariant=True)

    class FN_Operator(Protocol[_TV_IntegerObject, _TV_ARG1]):
        def __call__(s, self: _TV_IntegerObject, other: _TV_ARG1) -> TYPE_var: ...
    _TV_FN_Operator = T.TypeVar('_TV_FN_Operator', bound=FN_Operator)

    CalleeArgs: TypeAlias = T.Tuple[mparser.BaseNode, T.Optional[T.List[TYPE_var]], T.Optional[TYPE_kwargs], SubProject]

    MesonVersionTarget = mesonlib.Range[mesonlib.Version] | mesonlib.NoProjectVersion | None

    _FeatureKey: TypeAlias = _T | 'ContainerTypeInfo' | type | tuple[type, ...]
    _FeatureValue: TypeAlias = str | tuple[str, str]
    _FeatureValues: TypeAlias = dict[_FeatureKey, _FeatureValue]

    class _KwargInfoKWs(T.TypedDict, T.Generic[_T], total=False):
        name: str
        required: bool
        listify: bool
        default: _T | None
        since: str | None
        since_message: str | None
        since_values: _FeatureValues | None
        deprecated: str | None
        deprecated_message: str | None
        deprecated_values: _FeatureValues | None
        feature_validator: T.Callable[[_T], T.Iterable[FeatureCheckBase]] | None
        validator: T.Callable[[T.Any], str | None] | None
        convertor: T.Callable[[_T], object] | None
        not_set_warning: str | None
        extra_types: T.Mapping[type, T.Callable[[object], str]] | None
        as_default: list[tuple[object, str | tuple[str, str]]] | None


def is_module(obj: object) -> TypeIs[ModuleObject]:
    return not hasattr(obj, 'current_node')


@T.overload
def get_callee_args(wrapped_args: T.Tuple[InterpreterObject, T.List[TYPE_var], TYPE_kwargs]) -> CalleeArgs: ...


@T.overload
def get_callee_args(wrapped_args: T.Tuple[ObjectHolder, object]) -> CalleeArgs: ...


@T.overload
def get_callee_args(wrapped_args: T.Tuple[InterpreterBase, FunctionNode, T.List[TYPE_var], TYPE_kwargs]) -> CalleeArgs: ...


@T.overload
def get_callee_args(wrapped_args: T.Tuple[ModuleObject, ModuleState, T.List[TYPE_var], TYPE_kwargs]) -> CalleeArgs: ...


@T.overload
def get_callee_args(wrapped_args: T.Tuple[OptionInterpreter, T.List[TYPE_var], TYPE_kwargs]) -> CalleeArgs: ...


def get_callee_args(wrapped_args: T.Union[
            T.Tuple[InterpreterObject, T.List[TYPE_var], TYPE_kwargs],
            T.Tuple[ObjectHolder, object],
            T.Tuple[InterpreterBase, FunctionNode, T.List[TYPE_var], TYPE_kwargs],
            T.Tuple[ModuleObject, ModuleState, T.List[TYPE_var], TYPE_kwargs],
            T.Tuple[OptionInterpreter, T.List[TYPE_var], TYPE_kwargs],
        ]) -> CalleeArgs:
    if is_module(wrapped_args[0]):
        s = wrapped_args[1]
    else:
        s = wrapped_args[0]
    node = s.current_node
    subproject = s.subproject
    args: T.Optional[T.List[TYPE_var]] = None
    kwargs: T.Optional[TYPE_kwargs] = None
    if len(wrapped_args) >= 3:
        args = wrapped_args[-2]
        kwargs = wrapped_args[-1]
    return node, args, kwargs, subproject


def noPosargs(f: TV_func) -> TV_func:
    @wraps(f)
    def wrapped(*wrapped_args: T.Any, **wrapped_kwargs: T.Any) -> T.Any:
        args = get_callee_args(wrapped_args)[1]
        if args:
            raise InvalidArguments('Function does not take positional arguments.')
        return f(*wrapped_args, **wrapped_kwargs)
    return T.cast('TV_func', wrapped)

def noKwargs(f: TV_func) -> TV_func:
    @wraps(f)
    def wrapped(*wrapped_args: T.Any, **wrapped_kwargs: T.Any) -> T.Any:
        kwargs = get_callee_args(wrapped_args)[2]
        if kwargs:
            raise InvalidArguments('Function does not take keyword arguments.')
        return f(*wrapped_args, **wrapped_kwargs)
    return T.cast('TV_func', wrapped)

def noArgsFlattening(f: TV_func) -> TV_func:
    setattr(f, 'no-args-flattening', True)  # noqa: B010
    return f

def noSecondLevelHolderResolving(f: TV_func) -> TV_func:
    setattr(f, 'no-second-level-holder-flattening', True)  # noqa: B010
    return f

def unholder_return(f: TV_func) -> T.Callable[..., TYPE_var]:
    @wraps(f)
    def wrapped(*wrapped_args: T.Any, **wrapped_kwargs: T.Any) -> T.Any:
        res = f(*wrapped_args, **wrapped_kwargs)
        return _unholder(res)
    return T.cast('T.Callable[..., TYPE_var]', wrapped)

def disablerIfNotFound(f: TV_func) -> TV_func:
    @wraps(f)
    def wrapped(*wrapped_args: T.Any, **wrapped_kwargs: T.Any) -> T.Any:
        kwargs = get_callee_args(wrapped_args)[2]
        disabler = kwargs.pop('disabler', False)
        ret = f(*wrapped_args, **wrapped_kwargs)
        if disabler and not ret.found():
            return Disabler()
        return ret
    return T.cast('TV_func', wrapped)

def kwargs_get_close_matches(invalid_kwargs: T.Set[str], valid_kwargs: T.Set[str]) -> T.List[str]:
    with_close_matches = []
    from difflib import get_close_matches
    for invalid in sorted(invalid_kwargs):
        close_matches = get_close_matches(invalid, valid_kwargs)
        with_close_matches.append(f'"{invalid}" (did you mean "{close_matches[0]}"?)' if close_matches else f'"{invalid}"')
    return with_close_matches

def typed_operator(operator: MesonOperator,
                   types: T.Union[T.Type, T.Tuple[T.Type, ...]]) -> T.Callable[['_TV_FN_Operator'], '_TV_FN_Operator']:
    """Decorator that does type checking for operator calls.

    The principle here is similar to typed_pos_args, however much simpler
    since only one other object ever is passed
    """
    def inner(f: '_TV_FN_Operator') -> '_TV_FN_Operator':
        @wraps(f)
        def wrapper(self: 'InterpreterObject', other: TYPE_var) -> TYPE_var:
            if not isinstance(other, types):
                raise InvalidArguments(f'The `{operator.value}` of {self.display_name()} does not accept objects of type {type(other).__name__} ({other})')
            return f(self, other)
        return T.cast('_TV_FN_Operator', wrapper)
    return inner


def _types_description(types: tuple[type | ContainerTypeInfo, ...] | type | ContainerTypeInfo) -> str:
    candidates: list[str] = []
    types_tuple = types if isinstance(types, tuple) else (types, )
    for t in types_tuple:
        if isinstance(t, ContainerTypeInfo):
            desc, extra = t.description()
            if extra:
                desc = f'"{desc}" {extra}'
            else:
                desc = f'"{desc}"'
            candidates.append(desc)
        else:
            candidates.append(f'"{t.__name__}"')
    shouldbe = 'one of: ' if len(candidates) > 1 else ''
    shouldbe += ', '.join(candidates)
    return shouldbe


def _raw_description(t: object) -> str:
    """describe a raw type (ie, one that is not a ContainerTypeInfo)."""
    if isinstance(t, list):
        if t:
            return f"array[{' | '.join(sorted(mesonlib.OrderedSet(type(v).__name__ for v in t)))}]"
        return 'array[]'
    elif isinstance(t, dict):
        if t:
            return f"dict[{' | '.join(sorted(mesonlib.OrderedSet(type(v).__name__ for v in t.values())))}]"
        return 'dict[]'
    return type(t).__name__


def _check_value_type(types: tuple[type | ContainerTypeInfo, ...] | type | ContainerTypeInfo,
                      value: T.Any) -> bool:
    types_tuple = types if isinstance(types, tuple) else (types, )
    for t in types_tuple:
        if isinstance(t, ContainerTypeInfo):
            if t.check(value):
                return True
        elif isinstance(value, t):
            return True
    return False


def _shouldbe_format(name: str, argument_type: T.Literal['positional', 'keyword'],
                     argument_name: str, argument: object,
                     types: tuple[type | ContainerTypeInfo, ...] | type | ContainerTypeInfo,
                     extra: str | None = None) -> str:
    should_be = _types_description(types)
    if extra:
        should_be = f'{should_be}. {extra}'
    return (f'"{name}" {argument_type} argument "{argument_name}" was of type '
            f'"{_raw_description(argument)}" but should have been {should_be}')


def typed_pos_args(name: str, *types: T.Union[T.Type, T.Tuple[T.Type, ...]],
                   varargs: T.Optional[T.Union[T.Type, T.Tuple[T.Type, ...]]] = None,
                   optargs: T.Optional[T.List[T.Union[T.Type, T.Tuple[T.Type, ...]]]] = None,
                   min_varargs: int = 0, max_varargs: int = 0) -> T.Callable[..., T.Any]:
    """Decorator that types type checking of positional arguments.

    This supports two different models of optional arguments, the first is the
    variadic argument model. Variadic arguments are a possibly bounded,
    possibly unbounded number of arguments of the same type (unions are
    supported). The second is the standard default value model, in this case
    a number of optional arguments may be provided, but they are still
    ordered, and they may have different types.

    This function does not support mixing variadic and default arguments.

    :name: The name of the decorated function (as displayed in error messages)
    :varargs: They type(s) of any variadic arguments the function takes. If
        None the function takes no variadic args
    :min_varargs: the minimum number of variadic arguments taken
    :max_varargs: the maximum number of variadic arguments taken. 0 means unlimited
    :optargs: The types of any optional arguments parameters taken. If None
        then no optional parameters are taken.

    Some examples of usage blow:
    >>> @typed_pos_args('mod.func', str, (str, int))
    ... def func(self, state: ModuleState, args: T.Tuple[str, T.Union[str, int]], kwargs: T.Dict[str, T.Any]) -> T.Any:
    ...     pass

    >>> @typed_pos_args('method', str, varargs=str)
    ... def method(self, node: BaseNode, args: T.Tuple[str, T.List[str]], kwargs: T.Dict[str, T.Any]) -> T.Any:
    ...     pass

    >>> @typed_pos_args('method', varargs=str, min_varargs=1)
    ... def method(self, node: BaseNode, args: T.Tuple[T.List[str]], kwargs: T.Dict[str, T.Any]) -> T.Any:
    ...     pass

    >>> @typed_pos_args('method', str, optargs=[(str, int), str])
    ... def method(self, node: BaseNode, args: T.Tuple[str, T.Optional[T.Union[str, int]], T.Optional[str]], kwargs: T.Dict[str, T.Any]) -> T.Any:
    ...     pass

    When should you chose `typed_pos_args('name', varargs=str,
    min_varargs=1)` vs `typed_pos_args('name', str, varargs=str)`?

    The answer has to do with the semantics of the function, if all of the
    inputs are the same type (such as with `files()`) then the former is
    correct, all of the arguments are string names of files. If the first
    argument is something else the it should be separated.
    """
    def inner(f: TV_func) -> TV_func:

        @wraps(f)
        def wrapper(*wrapped_args: T.Any, **wrapped_kwargs: T.Any) -> T.Any:
            args = get_callee_args(wrapped_args)[1]

            # These are implementation programming errors, end users should never see them.
            assert isinstance(args, list), args
            assert max_varargs >= 0, 'max_varags cannot be negative'
            assert min_varargs >= 0, 'min_varags cannot be negative'
            assert optargs is None or varargs is None, \
                'varargs and optargs not supported together as this would be ambiguous'

            num_args = len(args)
            num_types = len(types)
            a_types = types
            last_pos = num_args

            if varargs:
                min_args = num_types + min_varargs
                max_args = num_types + max_varargs
                if max_varargs == 0 and num_args < min_args:
                    raise InvalidArguments(f'"{name}" takes at least {min_args} arguments, but got {num_args}.')
                elif max_varargs != 0 and (num_args < min_args or num_args > max_args):
                    raise InvalidArguments(f'"{name}" takes between {min_args} and {max_args} arguments, but got {num_args}.')
            elif optargs:
                if num_args < num_types:
                    raise InvalidArguments(f'"{name}" takes at least {num_types} arguments, but got {num_args}.')
                elif num_args > num_types + len(optargs):
                    raise InvalidArguments(f'"{name}" takes at most {num_types + len(optargs)} arguments, but got {num_args}.')
                # Add the number of positional arguments required
                if num_args > num_types:
                    diff = num_args - num_types
                    a_types = tuple(list(types) + list(optargs[:diff]))
            elif num_args != num_types:
                raise InvalidArguments(f'"{name}" takes exactly {num_types} arguments, but got {num_args}.')

            for i, (arg, type_) in enumerate(itertools.zip_longest(args, a_types, fillvalue=varargs), start=1):
                if not isinstance(arg, type_):
                    # if DefaultObject is an explicit allowed allowed type allow
                    # it through.
                    if isinstance(arg, DefaultObject):
                        if i >= last_pos:
                            if varargs:
                                msg = 'not allowed for variadic arguments'
                            else:
                                msg = 'not allowed for optional positional arguments'
                        else:
                            msg = 'not allowed for required positional arguments'
                        raise InvalidArguments(f'default() objects are {msg}')
                    raise InvalidArguments(_shouldbe_format(name, 'positional', str(i), arg, type_))

            # Ensure that we're actually passing a tuple.
            # Depending on what kind of function we're calling the length of
            # wrapped_args can vary.
            nargs = list(wrapped_args)
            i = nargs.index(args)
            if varargs:
                # if we have varargs we need to split them into a separate
                # tuple, as python's typing doesn't understand tuples with
                # fixed elements and variadic elements, only one or the other.
                # so in that case we need T.Tuple[int, str, float, T.Tuple[str, ...]]
                pos = args[:len(types)]
                var = list(args[len(types):])
                pos.append(var)
                nargs[i] = tuple(pos)
            elif optargs:
                if num_args < num_types + len(optargs):
                    diff = num_types + len(optargs) - num_args
                    nargs[i] = tuple(list(args) + [None] * diff)
                else:
                    nargs[i] = tuple(args)
            else:
                nargs[i] = tuple(args)
            return f(*nargs, **wrapped_kwargs)

        return T.cast('TV_func', wrapper)
    return inner


class ContainerTypeInfo:

    """Container information for keyword arguments.

    For keyword arguments that are containers (list or dict), this class encodes
    that information.

    :param container: the type of container
    :param contains: the types the container holds
    :param pairs: if the container is supposed to be of even length.
        This is mainly used for interfaces that predate the addition of dictionaries, and use
        `[key, value, key2, value2]` format.
    :param allow_empty: Whether this container is allowed to be empty
        There are some cases where containers not only must be passed, but must
        not be empty, and other cases where an empty container is allowed.
    """

    def __init__(self, container: T.Type, contains: T.Union[T.Type, T.Tuple[T.Type, ...]], *,
                 pairs: bool = False, allow_empty: bool = True):
        self.container = container
        self.contains = contains
        self.pairs = pairs
        self.allow_empty = allow_empty

    def check(self, value: T.Any) -> bool:
        """Check that a value is valid.

        :param value: A value to check
        :return: True if it is valid, False otherwise
        """
        if not isinstance(value, self.container):
            return False
        iter_ = iter(value.values()) if isinstance(value, dict) else iter(value)
        if any(not isinstance(i, self.contains) for i in iter_):
            return False
        if self.pairs and len(value) % 2 != 0:
            return False
        if not value and not self.allow_empty:
            return False
        return True

    def check_any(self, value: T.Any) -> bool:
        """Check a value should emit new/deprecated feature.

        :param value: A value to check
        :return: True if any of the items in value matches, False otherwise
        """
        if not isinstance(value, self.container):
            return False
        iter_ = iter(value.values()) if isinstance(value, dict) else iter(value)
        return any(isinstance(i, self.contains) for i in iter_)

    def description(self) -> tuple[str, str | None]:
        """Human readable description of this container type.

        :return: a tuple of: the type as a string, an extra message if there is one
        """
        container = 'dict' if self.container is dict else 'array'
        if isinstance(self.contains, tuple):
            contains = ' | '.join([t.__name__ for t in self.contains])
        else:
            contains = self.contains.__name__
        s = f'{container}[{contains}]'
        extra: str | None = None
        if self.pairs:
            extra = 'that has even size'
        if not self.allow_empty:
            extra = 'that cannot be empty'
        return s, extra


@dataclasses.dataclass(slots=True, eq=False)
class KwargInfo(T.Generic[_T]):

    """A description of a keyword argument to a meson function

    This is used to describe a value to the :func:TypedArgs function.

    :param name: the name of the parameter
    :param types: A type or tuple of types that are allowed, or a :class:ContainerType
    :param required: Whether this is a required keyword argument. defaults to False
    :param listify: If true, then the argument will be listified before being
        checked. This is useful for cases where the Meson DSL allows a scalar or
        a container, but internally we only want to work with containers
    :param default: A default value to use if this isn't set. defaults to None,
        this may be safely set to a mutable type, as long as that type does not
        itself contain mutable types, TypedArgs will copy the default
    :param since: Meson version in which this argument has been added. defaults to None
    :param since_message: An extra message to pass to FeatureNew when since is triggered
    :param deprecated: Meson version in which this argument has been deprecated. defaults to None
    :param deprecated_message: An extra message to pass to FeatureDeprecated
        when since is triggered
    :param validator: A callable that does additional validation. This is mainly
        intended for cases where a string is expected, but only a few specific
        values are accepted. Must return None if the input is valid, or a
        message if the input is invalid
    :param convertor: A callable that converts the raw input value into a
        different type. This is intended for cases such as the meson DSL using a
        string, but the implementation using an Enum. This should not do
        validation, just conversion.
    :param deprecated_values: a dictionary mapping a value to the version of
        meson it was deprecated in. The Value may be any valid value for this
        argument.
    :param since_values: a dictionary mapping a value to the version of meson it was
        added in.
    :param not_set_warning: A warning message that is logged if the kwarg is not
        set by the user.
    :param feature_validator: A callable returning an iterable of FeatureNew | FeatureDeprecated objects.
    :param extra_types:
        A mapping of types to a callable that is passed that type and returns an
        error message. These types are specifically *not* added to the general
        error message
    :param as_default: Extra values to treat as empty values. These are always considered to be broken.
    """

    name: str
    types: type[_T] | ContainerTypeInfo | tuple[type[_T] | ContainerTypeInfo, ...]
    required: bool = dataclasses.field(default=False, kw_only=True)
    listify: bool = dataclasses.field(default=False, kw_only=True)
    default: _T | None = dataclasses.field(default=None, kw_only=True)
    since: str | None = dataclasses.field(default=None, kw_only=True)
    since_message: str | None = dataclasses.field(default=None, kw_only=True)
    since_values: _FeatureValues | None = dataclasses.field(default=None, kw_only=True)
    deprecated: str | None = dataclasses.field(default=None, kw_only=True)
    deprecated_message: str | None = dataclasses.field(default=None, kw_only=True)
    deprecated_values: _FeatureValues | None = dataclasses.field(default=None, kw_only=True)
    feature_validator: T.Callable[[_T], T.Iterable[FeatureCheckBase]] | None = \
        dataclasses.field(default=None, kw_only=True)
    validator: T.Callable[[T.Any], str | None] | None = \
        dataclasses.field(default=None, kw_only=True)
    convertor: T.Callable[[_T], object] | None = dataclasses.field(default=None, kw_only=True)
    not_set_warning: str | None = dataclasses.field(default=None, kw_only=True)
    extra_types: T.Mapping[type, T.Callable[[object], str]] | None = \
        dataclasses.field(default=None, kw_only=True)
    as_default: list[tuple[object, str | tuple[str, str]]] | None = \
        dataclasses.field(default=None, kw_only=True)

    def evolve(self, **kwargs: Unpack[_KwargInfoKWs]) -> KwargInfo[_T]:
        """Create a shallow copy of this KwargInfo, with modifications.

        This allows us to create a new copy of a KwargInfo with modifications.
        This allows us to use a shared kwarg that implements complex logic, but
        has slight differences in usage, such as being added to different
        functions in different versions of Meson.

        The use the _NULL special value here allows us to pass None, which has
        meaning in many of these cases. _NULL itself is never stored, always
        being replaced by either the copy in self, or the provided new version.
        """
        return dataclasses.replace(self, **kwargs)


@dataclasses.dataclass(slots=True, eq=False)
class TypedArgs:

    name: str
    kw_types: list[KwargInfo] = dataclasses.field(default_factory=list, kw_only=True)
    unknown_kwargs: bool = dataclasses.field(default=False, kw_only=True)

    def _emit_feature_change(self, value: object, values: dict[_T, str | tuple[str, str]],
                             feature: type['FeatureDeprecated'] | type['FeatureNew'],
                             subproject: SubProject, node: mparser.BaseNode, info: KwargInfo) -> None:
        for n, version in values.items():
            if isinstance(version, tuple):
                version, msg = version
            else:
                msg = None

            warning: str | None = None
            if isinstance(n, ContainerTypeInfo):
                if n.check_any(value):
                    d, extra = n.description()
                    warning = f'of type "{d}"'
                    if extra:
                        warning = f'{warning} {extra}'
            elif isinstance(n, (type, tuple)):
                if isinstance(value, n):
                    warning = f'of type "{type(value).__name__}"'
            elif isinstance(value, list):
                if n in value:
                    warning = f'value "{n}" in list'
            elif isinstance(value, dict):
                if n in value:
                    warning = f'value "{n}" in dict keys'
            elif n == value:
                warning = f'value "{n}"'
            if warning:
                feature.single_use(f'"{self.name}" keyword argument "{info.name}" {warning}', version, subproject, msg, location=node)

    # TODO: need to use two different types here to avoid passing the original type through
    def __call__(self, f: TV_func) -> T.Callable[..., T.Any]:
        @wraps(f)
        def wrapper(*wrapped_args: T.Any, **wrapped_kwargs: T.Any) -> T.Any:
            node, _, _kwargs, subproject = get_callee_args(wrapped_args)
            # Cast here, as the convertor function may place something other than a TYPE_var in the kwargs
            kwargs = T.cast('T.Dict[str, object]', _kwargs)

            if not self.unknown_kwargs:
                all_names = {t.name for t in self.kw_types}
                unknowns = set(kwargs).difference(all_names)
                if unknowns:
                    ustr = ', '.join(kwargs_get_close_matches(unknowns, all_names))
                    has_args = '.'
                    if not self.kw_types:
                        has_args = '. Function expects no keyword arguments.'
                    raise InvalidArguments(f'{self.name} got unknown keyword arguments {ustr}{has_args}')

            for info in self.kw_types:
                types_tuple = info.types if isinstance(info.types, tuple) else (info.types,)
                value = kwargs.get(info.name)
                if isinstance(value, DefaultObject):
                    # Ensure that default() is not used for required options
                    # Otherwise, set the value to None, which will send us down
                    # the "unset" path
                    if info.required:
                        raise InvalidArguments(f'"{self.name}" got a default() value for the required keyword argument "{info.name}". '
                                               'default() may not be used for required keyword arguments.')
                    value = None

                if value is not None:
                    extra: str | None
                    if info.since:
                        feature_name = info.name + ' arg in ' + self.name
                        FeatureNew.single_use(feature_name, info.since, subproject, info.since_message, location=node)
                    if info.deprecated:
                        feature_name = info.name + ' arg in ' + self.name
                        FeatureDeprecated.single_use(feature_name, info.deprecated, subproject, info.deprecated_message, location=node)
                    if info.as_default:
                        found = mesonlib.first(info.as_default, lambda x: value == x[0])
                        if found is not None:
                            msg = found[1]
                            extra = ''
                            if isinstance(msg, tuple):
                                msg, extra = msg
                            FeatureBroken.single_use(f"Using '{value}' as an empty value in {info.name}", msg, subproject, extra, node)
                            value = copy.copy(info.default)
                    if info.listify:
                        kwargs[info.name] = value = mesonlib.listify(value)
                    if not _check_value_type(types_tuple, value):
                        extra = None
                        if info.extra_types:
                            extra_desc: T.List[str] = []
                            if isinstance(value, list):
                                for (t, cb), v in itertools.product(info.extra_types.items(), value):
                                    if isinstance(v, t):
                                        extra_desc.append(cb(v))
                            else:
                                for t, cb in info.extra_types.items():
                                    if isinstance(value, t):
                                        extra_desc.append(cb(value))
                            extra = '. '.join(extra_desc)

                        raise InvalidArguments(
                            _shouldbe_format(self.name, 'keyword', info.name, value, types_tuple, extra))

                    if info.validator is not None:
                        msg = info.validator(value)
                        if msg is not None:
                            raise InvalidArguments(f'"{self.name}" keyword argument "{info.name}" {msg}')

                    if info.feature_validator is not None:
                        for each in info.feature_validator(value):
                            each.use(subproject, node)

                    if info.deprecated_values is not None:
                        self._emit_feature_change(value, info.deprecated_values, FeatureDeprecated, subproject, node, info)

                    if info.since_values is not None:
                        self._emit_feature_change(value, info.since_values, FeatureNew, subproject, node, info)

                elif info.required:
                    raise InvalidArguments(f'"{self.name}" is missing required keyword argument "{info.name}"')
                else:
                    # set the value to the default, this ensuring all kwargs are present
                    # This both simplifies the typing checking and the usage
                    assert _check_value_type(types_tuple, info.default), f'In function {self.name} default value of {info.name} is not a valid type, got {type(info.default)} expected {_types_description(types_tuple)}'
                    # Create a shallow copy of the container. This allows mutable
                    # types to be used safely as default values
                    kwargs[info.name] = copy.copy(info.default)
                    if info.not_set_warning:
                        mlog.warning(info.not_set_warning)

                if info.convertor:
                    kwargs[info.name] = info.convertor(kwargs[info.name])

            return f(*wrapped_args, **wrapped_kwargs)
        return T.cast('T.Callable[..., T.Any]', wrapper)


# This cannot be a dataclass due to https://github.com/python/mypy/issues/5374
class FeatureCheckBase(metaclass=mesonlib.SimpleABC):
    "Base class for feature version checks"

    feature_registry: T.ClassVar[T.Dict[str, T.Dict[str, T.Set[T.Tuple[str, T.Optional['mparser.BaseNode']]]]]]
    emit_notice = False
    unconditional = False

    def __init__(self, feature_name: str, feature_version: str, extra_message: str = ''):
        self.feature_name = feature_name
        self.feature_version_for_msg = feature_version
        self.extra_message = extra_message
        self.feature_version = feature_version
        # Map versions in the constraint of the form '0.46.0' to '0.46', to
        # ensure that '0.46' in project(meson_version: '>=0.46') allows
        # using features in '0.46.0'.  Meson versioning is basically
        # semver, i.e. '0.46.0' is the lowest version which satisfies the
        # constraint '>=0.46', but meson.version_compare() is more like
        # rpm versions for historical reasons.
        while self.feature_version.endswith('.0'):
            self.feature_version = self.feature_version[:-2]

    @staticmethod
    def get_target_version(subproject: str) -> MesonVersionTarget:
        # Don't do any checks if project() has not been parsed yet
        if subproject not in mesonlib.project_meson_versions:
            return None
        return mesonlib.project_meson_versions[subproject]

    @staticmethod
    @abc.abstractmethod
    def check_version(target_version: MesonVersionTarget, feature_version: str) -> bool:
        pass

    def use(self, subproject: 'SubProject', location: T.Optional['mparser.BaseNode'] = None) -> None:
        tv = self.get_target_version(subproject)
        # No target version
        if tv is None and not self.unconditional:
            return
        # Target version is new enough, don't warn
        if self.check_version(tv, self.feature_version) and not self.emit_notice:
            return
        # Feature is too new for target version or we want to emit notices, register it
        if subproject not in self.feature_registry:
            self.feature_registry[subproject] = {self.feature_version_for_msg: set()}
        register = self.feature_registry[subproject]
        if self.feature_version_for_msg not in register:
            register[self.feature_version_for_msg] = set()

        feature_key = (self.feature_name, location)
        if feature_key in register[self.feature_version_for_msg]:
            # Don't warn about the same feature multiple times
            # FIXME: This is needed to prevent duplicate warnings, but also
            # means we won't warn about a feature used in multiple places.
            return
        register[self.feature_version_for_msg].add(feature_key)
        # Target version is new enough, don't warn even if it is registered for notice
        if self.check_version(tv, self.feature_version):
            return
        self.log_usage_warning(tv, location)

    @classmethod
    def report(cls, subproject: str) -> None:
        if subproject not in cls.feature_registry:
            return
        warning_str = cls.get_warning_str_prefix(cls.get_target_version(subproject))
        notice_str = cls.get_notice_str_prefix(cls.get_target_version(subproject))
        fv = cls.feature_registry[subproject]
        tv = cls.get_target_version(subproject)
        for version in sorted(fv.keys()):
            message = ', '.join(sorted({f"'{i[0]}'" for i in fv[version]}))
            if cls.check_version(tv, version):
                notice_str += '\n * {}: {{{}}}'.format(version, message)
            else:
                warning_str += '\n * {}: {{{}}}'.format(version, message)
        if '\n' in notice_str:
            mlog.notice(notice_str, fatal=False)
        if '\n' in warning_str:
            mlog.warning(warning_str)

    def log_usage_warning(self, tv: MesonVersionTarget, location: T.Optional['mparser.BaseNode']) -> None:
        raise InterpreterException('log_usage_warning not implemented')

    @staticmethod
    def get_warning_str_prefix(tv: MesonVersionTarget) -> str:
        raise InterpreterException('get_warning_str_prefix not implemented')

    @staticmethod
    def get_notice_str_prefix(tv: MesonVersionTarget) -> str:
        raise InterpreterException('get_notice_str_prefix not implemented')

    def __call__(self, f: TV_func) -> TV_func:
        @wraps(f)
        def wrapped(*wrapped_args: T.Any, **wrapped_kwargs: T.Any) -> T.Any:
            node, _, _, subproject = get_callee_args(wrapped_args)
            if subproject is None:
                raise AssertionError(f'{wrapped_args!r}')
            self.use(subproject, node)
            return f(*wrapped_args, **wrapped_kwargs)
        return T.cast('TV_func', wrapped)

    @classmethod
    def single_use(cls, feature_name: str, version: str, subproject: 'SubProject',
                   extra_message: str = '', location: T.Optional['mparser.BaseNode'] = None) -> None:
        """Oneline version that instantiates and calls use()."""
        cls(feature_name, version, extra_message).use(subproject, location)


class FeatureNew(FeatureCheckBase):
    """Checks for new features"""

    # Class variable, shared across all instances
    #
    # Format: {subproject: {feature_version_for_msg: set(feature_names)}}
    feature_registry = {}

    @staticmethod
    def check_version(target_version: MesonVersionTarget, feature_version: str) -> bool:
        if isinstance(target_version, mesonlib.Range):
            return mesonlib.version_compare_condition_with_min(target_version, feature_version)
        else:
            # Warn for anything newer than the current semver base slot.
            major = coredata.version.split('.', maxsplit=1)[0]
            return mesonlib.version_compare(feature_version, f'<{major}.0')

    @staticmethod
    def get_warning_str_prefix(tv: MesonVersionTarget) -> str:
        if isinstance(tv, mesonlib.Range) and tv.min is not None:
            return f'Project specifies a minimum meson_version \'{tv}\' but uses features which were added in newer versions:'
        else:
            return 'Project specifies no minimum version but uses features which were added in versions:'

    @staticmethod
    def get_notice_str_prefix(tv: MesonVersionTarget) -> str:
        return ''

    def log_usage_warning(self, tv: MesonVersionTarget, location: T.Optional['mparser.BaseNode']) -> None:
        if isinstance(tv, mesonlib.Range) and tv.min is not None:
            prefix = f"Project targets '{tv}'"
        else:
            prefix = 'Project does not target a minimum version'
        args = [
            prefix,
            'but uses feature introduced in',
            f"'{self.feature_version_for_msg}':",
            f'{self.feature_name}.',
        ]
        if self.extra_message:
            args.append(self.extra_message)
        mlog.warning(*args, location=location)

class FeatureDeprecated(FeatureCheckBase):
    """Checks for deprecated features"""

    # Class variable, shared across all instances
    #
    # Format: {subproject: {feature_version_for_msg: set(feature_names)}}
    feature_registry = {}
    emit_notice = True

    @staticmethod
    def check_version(target_version: MesonVersionTarget, feature_version: str) -> bool:
        if isinstance(target_version, mesonlib.Range):
            # For deprecation checks we need to return the inverse of FeatureNew checks
            return not mesonlib.version_compare_condition_with_min(target_version, feature_version)
        else:
            # Always warn for functionality deprecated in the current semver slot (i.e. the current version).
            return False

    @staticmethod
    def get_warning_str_prefix(tv: MesonVersionTarget) -> str:
        return 'Deprecated features used:'

    @staticmethod
    def get_notice_str_prefix(tv: MesonVersionTarget) -> str:
        return 'Future-deprecated features used:'

    def log_usage_warning(self, tv: MesonVersionTarget, location: T.Optional['mparser.BaseNode']) -> None:
        if isinstance(tv, mesonlib.Range):
            prefix = f"Project targets '{tv}'"
        else:
            prefix = 'Project does not target a minimum version'
        args = [
            prefix,
            'but uses feature deprecated since',
            f"'{self.feature_version_for_msg}':",
            f'{self.feature_name}.',
        ]
        if self.extra_message:
            args.append(self.extra_message)
        mlog.warning(*args, location=location)


class FeatureBroken(FeatureCheckBase):
    """Checks for broken features"""

    # Class variable, shared across all instances
    #
    # Format: {subproject: {feature_version_for_msg: set(feature_names)}}
    feature_registry = {}
    unconditional = True

    @staticmethod
    def check_version(target_version: MesonVersionTarget, feature_version: str) -> bool:
        # always warn for broken stuff
        return False

    @staticmethod
    def get_warning_str_prefix(tv: MesonVersionTarget) -> str:
        return 'Broken features used:'

    @staticmethod
    def get_notice_str_prefix(tv: MesonVersionTarget) -> str:
        return ''

    def log_usage_warning(self, tv: MesonVersionTarget, location: T.Optional['mparser.BaseNode']) -> None:
        args = [
            'Project uses feature that was always broken,',
            'and is now deprecated since',
            f"'{self.feature_version_for_msg}':",
            f'{self.feature_name}.',
        ]
        if self.extra_message:
            args.append(self.extra_message)
        mlog.deprecation(*args, location=location)
