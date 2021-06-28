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

from .. import mesonlib, mlog
from .baseobjects import TV_func, TYPE_var
from .disabler import Disabler
from .exceptions import InterpreterException, InvalidArguments
from .helpers import check_stringlist, get_callee_args
from ._unholder import _unholder

from functools import wraps
import abc
import itertools
import typing as T

def noPosargs(f: TV_func) -> TV_func:
    @wraps(f)
    def wrapped(*wrapped_args: T.Any, **wrapped_kwargs: T.Any) -> T.Any:
        args = get_callee_args(wrapped_args)[2]
        if args:
            raise InvalidArguments('Function does not take positional arguments.')
        return f(*wrapped_args, **wrapped_kwargs)
    return T.cast(TV_func, wrapped)

def builtinMethodNoKwargs(f: TV_func) -> TV_func:
    @wraps(f)
    def wrapped(*wrapped_args: T.Any, **wrapped_kwargs: T.Any) -> T.Any:
        node = wrapped_args[0].current_node
        method_name = wrapped_args[2]
        kwargs = wrapped_args[4]
        if kwargs:
            mlog.warning(f'Method {method_name!r} does not take keyword arguments.',
                         'This will become a hard error in the future',
                         location=node)
        return f(*wrapped_args, **wrapped_kwargs)
    return T.cast(TV_func, wrapped)

def noKwargs(f: TV_func) -> TV_func:
    @wraps(f)
    def wrapped(*wrapped_args: T.Any, **wrapped_kwargs: T.Any) -> T.Any:
        kwargs = get_callee_args(wrapped_args)[3]
        if kwargs:
            raise InvalidArguments('Function does not take keyword arguments.')
        return f(*wrapped_args, **wrapped_kwargs)
    return T.cast(TV_func, wrapped)

def stringArgs(f: TV_func) -> TV_func:
    @wraps(f)
    def wrapped(*wrapped_args: T.Any, **wrapped_kwargs: T.Any) -> T.Any:
        args = get_callee_args(wrapped_args)[2]
        assert(isinstance(args, list))
        check_stringlist(args)
        return f(*wrapped_args, **wrapped_kwargs)
    return T.cast(TV_func, wrapped)

def noArgsFlattening(f: TV_func) -> TV_func:
    setattr(f, 'no-args-flattening', True)  # noqa: B010
    return f

def noSecondLevelHolderResolving(f: TV_func) -> TV_func:
    setattr(f, 'no-second-level-holder-flattening', True)  # noqa: B010
    return f

def permissive_unholder_return(f: TV_func) -> T.Callable[..., TYPE_var]:
    @wraps(f)
    def wrapped(*wrapped_args: T.Any, **wrapped_kwargs: T.Any) -> T.Any:
        res = f(*wrapped_args, **wrapped_kwargs)
        return _unholder(res, permissive=True)
    return T.cast(T.Callable[..., TYPE_var], wrapped)

def disablerIfNotFound(f: TV_func) -> TV_func:
    @wraps(f)
    def wrapped(*wrapped_args: T.Any, **wrapped_kwargs: T.Any) -> T.Any:
        kwargs = get_callee_args(wrapped_args)[3]
        disabler = kwargs.pop('disabler', False)
        ret = f(*wrapped_args, **wrapped_kwargs)
        if disabler and not ret.found():
            return Disabler()
        return ret
    return T.cast(TV_func, wrapped)

class permittedKwargs:

    def __init__(self, permitted: T.Set[str]):
        self.permitted = permitted  # type: T.Set[str]

    def __call__(self, f: TV_func) -> TV_func:
        @wraps(f)
        def wrapped(*wrapped_args: T.Any, **wrapped_kwargs: T.Any) -> T.Any:
            s, node, args, kwargs, _ = get_callee_args(wrapped_args)
            for k in kwargs:
                if k not in self.permitted:
                    mlog.warning(f'''Passed invalid keyword argument "{k}".''', location=node)
                    mlog.warning('This will become a hard error in the future.')
            return f(*wrapped_args, **wrapped_kwargs)
        return T.cast(TV_func, wrapped)


def typed_pos_args(name: str, *types: T.Union[T.Type, T.Tuple[T.Type, ...]],
                   varargs: T.Optional[T.Union[T.Type, T.Tuple[T.Type, ...]]] = None,
                   optargs: T.Optional[T.List[T.Union[T.Type, T.Tuple[T.Type, ...]]]] = None,
                   min_varargs: int = 0, max_varargs: int = 0) -> T.Callable[..., T.Any]:
    """Decorator that types type checking of positional arguments.

    This supports two different models of optional aguments, the first is the
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
        then no optional paramters are taken.

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
            args = get_callee_args(wrapped_args)[2]

            # These are implementation programming errors, end users should never see them.
            assert isinstance(args, list), args
            assert max_varargs >= 0, 'max_varags cannot be negative'
            assert min_varargs >= 0, 'min_varags cannot be negative'
            assert optargs is None or varargs is None, \
                'varargs and optargs not supported together as this would be ambiguous'

            num_args = len(args)
            num_types = len(types)
            a_types = types

            if varargs:
                min_args = num_types + min_varargs
                max_args = num_types + max_varargs
                if max_varargs == 0 and num_args < min_args:
                    raise InvalidArguments(f'{name} takes at least {min_args} arguments, but got {num_args}.')
                elif max_varargs != 0 and (num_args < min_args or num_args > max_args):
                    raise InvalidArguments(f'{name} takes between {min_args} and {max_args} arguments, but got {num_args}.')
            elif optargs:
                if num_args < num_types:
                    raise InvalidArguments(f'{name} takes at least {num_types} arguments, but got {num_args}.')
                elif num_args > num_types + len(optargs):
                    raise InvalidArguments(f'{name} takes at most {num_types + len(optargs)} arguments, but got {num_args}.')
                # Add the number of positional arguments required
                if num_args > num_types:
                    diff = num_args - num_types
                    a_types = tuple(list(types) + list(optargs[:diff]))
            elif num_args != num_types:
                raise InvalidArguments(f'{name} takes exactly {num_types} arguments, but got {num_args}.')

            for i, (arg, type_) in enumerate(itertools.zip_longest(args, a_types, fillvalue=varargs), start=1):
                if not isinstance(arg, type_):
                    if isinstance(type_, tuple):
                        shouldbe = 'one of: {}'.format(", ".join(f'"{t.__name__}"' for t in type_))
                    else:
                        shouldbe = f'"{type_.__name__}"'
                    raise InvalidArguments(f'{name} argument {i} was of type "{type(arg).__name__}" but should have been {shouldbe}')

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
                    diff =  num_types + len(optargs) - num_args
                    nargs[i] = tuple(list(args) + [None] * diff)
                else:
                    nargs[i] = args
            else:
                nargs[i] = tuple(args)
            return f(*nargs, **wrapped_kwargs)

        return T.cast(TV_func, wrapper)
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
                 pairs: bool = False, allow_empty: bool = True) :
        self.container = container
        self.contains = contains
        self.pairs = pairs
        self.allow_empty = allow_empty

    def check(self, value: T.Any) -> T.Optional[str]:
        """Check that a value is valid.

        :param value: A value to check
        :return: If there is an error then a string message, otherwise None
        """
        if not isinstance(value, self.container):
            return f'container type was "{type(value).__name__}", but should have been "{self.container.__name__}"'
        iter_ = iter(value.values()) if isinstance(value, dict) else iter(value)
        for each in iter_:
            if not isinstance(each, self.contains):
                if isinstance(self.contains, tuple):
                    shouldbe = 'one of: {}'.format(", ".join(f'"{t.__name__}"' for t in self.contains))
                else:
                    shouldbe = f'"{self.contains.__name__}"'
                return f'contained a value of type "{type(each).__name__}" but should have been {shouldbe}'
        if self.pairs and len(value) % 2 != 0:
            return 'container should be of even length, but is not'
        if not value and not self.allow_empty:
            return 'container is empty, but not allowed to be'
        return None


_T = T.TypeVar('_T')

class _NULL_T:
    """Special null type for evolution, this is an implementation detail."""


_NULL = _NULL_T()

class KwargInfo(T.Generic[_T]):

    """A description of a keyword argument to a meson function

    This is used to describe a value to the :func:typed_kwargs function.

    :param name: the name of the parameter
    :param types: A type or tuple of types that are allowed, or a :class:ContainerType
    :param required: Whether this is a required keyword argument. defaults to False
    :param listify: If true, then the argument will be listified before being
        checked. This is useful for cases where the Meson DSL allows a scalar or
        a container, but internally we only want to work with containers
    :param default: A default value to use if this isn't set. defaults to None,
        this may be safely set to a mutable type, as long as that type does not
        itself contain mutable types, typed_kwargs will copy the default
    :param since: Meson version in which this argument has been added. defaults to None
    :param deprecated: Meson version in which this argument has been deprecated. defaults to None
    :param validator: A callable that does additional validation. This is mainly
        intended for cases where a string is expected, but only a few specific
        values are accepted. Must return None if the input is valid, or a
        message if the input is invalid
    :param convertor: A callable that converts the raw input value into a
        different type. This is intended for cases such as the meson DSL using a
        string, but the implementation using an Enum. This should not do
        validation, just converstion.
    :param deprecated_values: a dictionary mapping a value to the version of
        meson it was deprecated in.
    :param since_values: a dictionary mapping a value to the version of meson it was
        added in.
    :param not_set_warning: A warning messsage that is logged if the kwarg is not
        set by the user.
    """

    def __init__(self, name: str, types: T.Union[T.Type[_T], T.Tuple[T.Type[_T], ...], ContainerTypeInfo],
                 *, required: bool = False, listify: bool = False,
                 default: T.Optional[_T] = None,
                 since: T.Optional[str] = None,
                 since_values: T.Optional[T.Dict[str, str]] = None,
                 deprecated: T.Optional[str] = None,
                 deprecated_values: T.Optional[T.Dict[str, str]] = None,
                 validator: T.Optional[T.Callable[[_T], T.Optional[str]]] = None,
                 convertor: T.Optional[T.Callable[[_T], TYPE_var]] = None,
                 not_set_warning: T.Optional[str] = None):
        self.name = name
        self.types = types
        self.required = required
        self.listify = listify
        self.default = default
        self.since_values = since_values
        self.since = since
        self.deprecated = deprecated
        self.deprecated_values = deprecated_values
        self.validator = validator
        self.convertor = convertor
        self.not_set_warning = not_set_warning

    def evolve(self, *,
               required: T.Union[bool, _NULL_T] = _NULL,
               listify: T.Union[bool, _NULL_T] = _NULL,
               default: T.Union[_T, None, _NULL_T] = _NULL,
               since: T.Union[str, None, _NULL_T] = _NULL,
               since_values: T.Union[T.Dict[str, str], None, _NULL_T] = _NULL,
               deprecated: T.Union[str, None, _NULL_T] = _NULL,
               deprecated_values: T.Union[T.Dict[str, str], None, _NULL_T] = _NULL,
               validator: T.Union[T.Callable[[_T], T.Optional[str]], None, _NULL_T] = _NULL,
               convertor: T.Union[T.Callable[[_T], TYPE_var], None, _NULL_T] = _NULL) -> 'KwargInfo':
        """Create a shallow copy of this KwargInfo, with modifications.

        This allows us to create a new copy of a KwargInfo with modifications.
        This allows us to use a shared kwarg that implements complex logic, but
        has slight differences in usage, such as being added to different
        functions in different versions of Meson.

        The use the _NULL special value here allows us to pass None, which has
        meaning in many of these cases. _NULL itself is never stored, always
        being replaced by either the copy in self, or the provided new version.
        """
        return type(self)(
            self.name,
            self.types,
            listify=listify if not isinstance(listify, _NULL_T) else self.listify,
            required=required if not isinstance(required, _NULL_T) else self.required,
            default=default if not isinstance(default, _NULL_T) else self.default,
            since=since if not isinstance(since, _NULL_T) else self.since,
            since_values=since_values if not isinstance(since_values, _NULL_T) else self.since_values,
            deprecated=deprecated if not isinstance(deprecated, _NULL_T) else self.deprecated,
            deprecated_values=deprecated_values if not isinstance(deprecated_values, _NULL_T) else self.deprecated_values,
            validator=validator if not isinstance(validator, _NULL_T) else self.validator,
            convertor=convertor if not isinstance(convertor, _NULL_T) else self.convertor,
        )



def typed_kwargs(name: str, *types: KwargInfo) -> T.Callable[..., T.Any]:
    """Decorator for type checking keyword arguments.

    Used to wrap a meson DSL implementation function, where it checks various
    things about keyword arguments, including the type, and various other
    information. For non-required values it sets the value to a default, which
    means the value will always be provided.

    If type tyhpe is a :class:ContainerTypeInfo, then the default value will be
    passed as an argument to the container initializer, making a shallow copy

    :param name: the name of the function, including the object it's attached ot
        (if applicable)
    :param *types: KwargInfo entries for each keyword argument.
    """
    def inner(f: TV_func) -> TV_func:

        @wraps(f)
        def wrapper(*wrapped_args: T.Any, **wrapped_kwargs: T.Any) -> T.Any:
            kwargs, subproject = get_callee_args(wrapped_args, want_subproject=True)[3:5]

            all_names = {t.name for t in types}
            unknowns = set(kwargs).difference(all_names)
            if unknowns:
                # Warn about unknown argumnts, delete them and continue. This
                # keeps current behavior
                ustr = ', '.join([f'"{u}"' for u in sorted(unknowns)])
                mlog.warning(f'{name} got unknown keyword arguments {ustr}')
                for u in unknowns:
                    del kwargs[u]

            for info in types:
                value = kwargs.get(info.name)
                if value is not None:
                    if info.since:
                        feature_name = info.name + ' arg in ' + name
                        FeatureNew.single_use(feature_name, info.since, subproject)
                    if info.deprecated:
                        feature_name = info.name + ' arg in ' + name
                        FeatureDeprecated.single_use(feature_name, info.deprecated, subproject)
                    if info.listify:
                        kwargs[info.name] = value = mesonlib.listify(value)
                    if isinstance(info.types, ContainerTypeInfo):
                        msg = info.types.check(value)
                        if msg is not None:
                            raise InvalidArguments(f'{name} keyword argument "{info.name}" {msg}')
                    else:
                        if not isinstance(value, info.types):
                            if isinstance(info.types, tuple):
                                shouldbe = 'one of: {}'.format(", ".join(f'"{t.__name__}"' for t in info.types))
                            else:
                                shouldbe = f'"{info.types.__name__}"'
                            raise InvalidArguments(f'{name} keyword argument "{info.name}"" was of type "{type(value).__name__}" but should have been {shouldbe}')

                    if info.validator is not None:
                        msg = info.validator(value)
                        if msg is not None:
                            raise InvalidArguments(f'{name} keyword argument "{info.name}" {msg}')

                    warn: bool
                    if info.deprecated_values is not None:
                        for n, version in info.deprecated_values.items():
                            if isinstance(value, (dict, list)):
                                warn = n in value
                            else:
                                warn = n == value

                            if warn:
                                FeatureDeprecated.single_use(f'"{name}" keyword argument "{info.name}" value "{n}"', version, subproject)

                    if info.since_values is not None:
                        for n, version in info.since_values.items():
                            if isinstance(value, (dict, list)):
                                warn = n in value
                            else:
                                warn = n == value

                            if warn:
                                FeatureNew.single_use(f'"{name}" keyword argument "{info.name}" value "{n}"', version, subproject)

                elif info.required:
                    raise InvalidArguments(f'{name} is missing required keyword argument "{info.name}"')
                else:
                    # set the value to the default, this ensuring all kwargs are present
                    # This both simplifies the typing checking and the usage
                    # Create a shallow copy of the container (and do a type
                    # conversion if necessary). This allows mutable types to
                    # be used safely as default values
                    if isinstance(info.types, ContainerTypeInfo):
                        kwargs[info.name] = info.types.container(info.default)
                    else:
                        kwargs[info.name] = info.default
                    if info.not_set_warning:
                        mlog.warning(info.not_set_warning)

                if info.convertor:
                    kwargs[info.name] = info.convertor(kwargs[info.name])

            return f(*wrapped_args, **wrapped_kwargs)
        return T.cast(TV_func, wrapper)
    return inner


class FeatureCheckBase(metaclass=abc.ABCMeta):
    "Base class for feature version checks"

    # In python 3.6 we can just forward declare this, but in 3.5 we can't
    # This will be overwritten by the subclasses by necessity
    feature_registry = {}  # type: T.ClassVar[T.Dict[str, T.Dict[str, T.Set[str]]]]

    def __init__(self, feature_name: str, version: str, extra_message: T.Optional[str] = None):
        self.feature_name = feature_name  # type: str
        self.feature_version = version    # type: str
        self.extra_message = extra_message or ''  # type: str

    @staticmethod
    def get_target_version(subproject: str) -> str:
        # Don't do any checks if project() has not been parsed yet
        if subproject not in mesonlib.project_meson_versions:
            return ''
        return mesonlib.project_meson_versions[subproject]

    @staticmethod
    @abc.abstractmethod
    def check_version(target_version: str, feature_Version: str) -> bool:
        pass

    def use(self, subproject: str) -> None:
        tv = self.get_target_version(subproject)
        # No target version
        if tv == '':
            return
        # Target version is new enough
        if self.check_version(tv, self.feature_version):
            return
        # Feature is too new for target version, register it
        if subproject not in self.feature_registry:
            self.feature_registry[subproject] = {self.feature_version: set()}
        register = self.feature_registry[subproject]
        if self.feature_version not in register:
            register[self.feature_version] = set()
        if self.feature_name in register[self.feature_version]:
            # Don't warn about the same feature multiple times
            # FIXME: This is needed to prevent duplicate warnings, but also
            # means we won't warn about a feature used in multiple places.
            return
        register[self.feature_version].add(self.feature_name)
        self.log_usage_warning(tv)

    @classmethod
    def report(cls, subproject: str) -> None:
        if subproject not in cls.feature_registry:
            return
        warning_str = cls.get_warning_str_prefix(cls.get_target_version(subproject))
        fv = cls.feature_registry[subproject]
        for version in sorted(fv.keys()):
            warning_str += '\n * {}: {}'.format(version, fv[version])
        mlog.warning(warning_str)

    def log_usage_warning(self, tv: str) -> None:
        raise InterpreterException('log_usage_warning not implemented')

    @staticmethod
    def get_warning_str_prefix(tv: str) -> str:
        raise InterpreterException('get_warning_str_prefix not implemented')

    def __call__(self, f: TV_func) -> TV_func:
        @wraps(f)
        def wrapped(*wrapped_args: T.Any, **wrapped_kwargs: T.Any) -> T.Any:
            subproject = get_callee_args(wrapped_args, want_subproject=True)[4]
            if subproject is None:
                raise AssertionError(f'{wrapped_args!r}')
            self.use(subproject)
            return f(*wrapped_args, **wrapped_kwargs)
        return T.cast(TV_func, wrapped)

    @classmethod
    def single_use(cls, feature_name: str, version: str, subproject: str,
                   extra_message: T.Optional[str] = None) -> None:
        """Oneline version that instantiates and calls use()."""
        cls(feature_name, version, extra_message).use(subproject)


class FeatureNew(FeatureCheckBase):
    """Checks for new features"""

    # Class variable, shared across all instances
    #
    # Format: {subproject: {feature_version: set(feature_names)}}
    feature_registry = {}  # type: T.ClassVar[T.Dict[str, T.Dict[str, T.Set[str]]]]

    @staticmethod
    def check_version(target_version: str, feature_version: str) -> bool:
        return mesonlib.version_compare_condition_with_min(target_version, feature_version)

    @staticmethod
    def get_warning_str_prefix(tv: str) -> str:
        return f'Project specifies a minimum meson_version \'{tv}\' but uses features which were added in newer versions:'

    def log_usage_warning(self, tv: str) -> None:
        args = [
            'Project targeting', f"'{tv}'",
            'but tried to use feature introduced in',
            f"'{self.feature_version}':",
            f'{self.feature_name}.',
        ]
        if self.extra_message:
            args.append(self.extra_message)
        mlog.warning(*args)

class FeatureDeprecated(FeatureCheckBase):
    """Checks for deprecated features"""

    # Class variable, shared across all instances
    #
    # Format: {subproject: {feature_version: set(feature_names)}}
    feature_registry = {}  # type: T.ClassVar[T.Dict[str, T.Dict[str, T.Set[str]]]]

    @staticmethod
    def check_version(target_version: str, feature_version: str) -> bool:
        # For deprecation checks we need to return the inverse of FeatureNew checks
        return not mesonlib.version_compare_condition_with_min(target_version, feature_version)

    @staticmethod
    def get_warning_str_prefix(tv: str) -> str:
        return 'Deprecated features used:'

    def log_usage_warning(self, tv: str) -> None:
        args = [
            'Project targeting', f"'{tv}'",
            'but tried to use feature deprecated since',
            f"'{self.feature_version}':",
            f'{self.feature_name}.',
        ]
        if self.extra_message:
            args.append(self.extra_message)
        mlog.warning(*args)


class FeatureCheckKwargsBase(metaclass=abc.ABCMeta):

    @property
    @abc.abstractmethod
    def feature_check_class(self) -> T.Type[FeatureCheckBase]:
        pass

    def __init__(self, feature_name: str, feature_version: str,
                 kwargs: T.List[str], extra_message: T.Optional[str] = None):
        self.feature_name = feature_name
        self.feature_version = feature_version
        self.kwargs = kwargs
        self.extra_message = extra_message

    def __call__(self, f: TV_func) -> TV_func:
        @wraps(f)
        def wrapped(*wrapped_args: T.Any, **wrapped_kwargs: T.Any) -> T.Any:
            kwargs, subproject = get_callee_args(wrapped_args, want_subproject=True)[3:5]
            if subproject is None:
                raise AssertionError(f'{wrapped_args!r}')
            for arg in self.kwargs:
                if arg not in kwargs:
                    continue
                name = arg + ' arg in ' + self.feature_name
                self.feature_check_class.single_use(
                        name, self.feature_version, subproject, self.extra_message)
            return f(*wrapped_args, **wrapped_kwargs)
        return T.cast(TV_func, wrapped)

class FeatureNewKwargs(FeatureCheckKwargsBase):
    feature_check_class = FeatureNew

class FeatureDeprecatedKwargs(FeatureCheckKwargsBase):
    feature_check_class = FeatureDeprecated
