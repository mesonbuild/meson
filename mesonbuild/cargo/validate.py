# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations
import typing as T

from dataclasses import InitVar, is_dataclass
from functools import lru_cache

if T.TYPE_CHECKING:
    from .._typing import DataclassInstance

PartialValidator = T.Callable[['ValidatorResult', object], 'ValidatorResult']
Validator = T.Callable[[object], 'ValidatorResult']

# All this is_* and extract_* magic is largely based on dacite
# Copyright (c) 2018 Konrad Hałas
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

def extract_origin_collection(collection: T.Type) -> T.Type:
    try:
        return T.cast('T.Type', collection.__extra__)
    except AttributeError:
        return T.cast('T.Type', collection.__origin__)


def is_generic(type_: T.Type) -> bool:
    return hasattr(type_, "__origin__")


def is_union(type_: T.Type) -> bool:
    if is_generic(type_) and type_.__origin__ == T.Union:
        return True

    try:
        from types import UnionType

        return isinstance(type_, UnionType)
    except ImportError:
        return False


def is_tuple(type_: T.Type) -> bool:
    return is_subclass(type_, tuple)


def is_typed_dict(type_: T.Type) -> bool:
    return hasattr(type_, "__orig_bases__") and T.TypedDict in type_.__orig_bases__


def is_literal(type_: T.Type) -> bool:
    return is_generic(type_) and type_.__origin__ == T.Literal


def is_required(type_: T.Type) -> bool:
    return is_generic(type_) and type_.__origin__ == T.Required


def is_new_type(type_: T.Type) -> bool:
    return hasattr(type_, "__supertype__")


def extract_new_type(type_: T.Type) -> T.Type:
    return T.cast('T.Type', type_.__supertype__)


def is_init_var(type_: T.Type) -> bool:
    return isinstance(type_, InitVar) or type_ is InitVar


def extract_init_var(type_: T.Type) -> T.Union[T.Type, T.Any]:
    try:
        return type_.type
    except AttributeError:
        return T.Any


def is_generic_collection(type_: T.Type) -> bool:
    if not is_generic(type_):
        return False
    origin = extract_origin_collection(type_)
    try:
        return bool(origin and issubclass(origin, T.Collection))
    except (TypeError, AttributeError):
        return False


def extract_generic(type_: T.Type, defaults: T.Tuple = ()) -> T.Tuple:
    try:
        if getattr(type_, "_special", False):
            return defaults
        if type_.__args__ == ():
            return (type_.__args__,)
        return type_.__args__ or defaults
    except AttributeError:
        return defaults


def is_subclass(sub_type: T.Type, base_type: T.Type) -> bool:
    if is_generic_collection(sub_type):
        sub_type = extract_origin_collection(sub_type)
    try:
        return issubclass(sub_type, base_type)
    except TypeError:
        return False


def is_type(type_: T.Type) -> bool:
    try:
        return type_.__origin__ in (type, T.Type)
    except AttributeError:
        return False


class ValidatorResult:
    SUCCESS: 'ValidatorResult'
    CACHE: T.Dict[T.Type, PartialValidator] = {}

    path: T.List[T.Union[str, int]]

    def __init__(self) -> None:
        self.path = []

    def __bool__(self) -> bool:
        return self is ValidatorResult.SUCCESS

    def success(self, obj: object) -> ValidatorResult:
        return ValidatorResult.SUCCESS

    def failure(self, obj: object) -> ValidatorResult:
        return self

    def union(self, validators: T.List[PartialValidator], obj: object) -> ValidatorResult:
        for v in validators:
            path_len = len(self.path)
            if v(self, obj):
                return ValidatorResult.SUCCESS
            self.path[:] = self.path[:path_len]
        return self

    def mapping(self, origin: T.Type[T.Mapping], kv: PartialValidator,
                vv: T.Callable[[object], PartialValidator],
                obj: object) -> ValidatorResult:
        if not isinstance(obj, origin):
            return self
        for k, v in obj.items():
            self.path.append(k)
            if not kv(self, k) or not vv(k)(self, v):
                return self
            self.path.pop()
        return ValidatorResult.SUCCESS

    def sequence(self, origin: T.Type[T.Sequence], iv: PartialValidator, obj: object) -> ValidatorResult:
        if not isinstance(obj, origin):
            return self
        for k, v in enumerate(obj):
            self.path.append(k)
            if not iv(self, v):
                return self
            self.path.pop()
        return ValidatorResult.SUCCESS

    def tuple(self, origin: T.Type[T.Tuple], iv: T.List[PartialValidator], obj: object) -> ValidatorResult:
        if not isinstance(obj, origin) or len(iv) != len(obj):
            return self
        it = iter(iv)
        for k, v in enumerate(obj):
            self.path.append(k)
            if not next(it)(self, v):
                return self
            self.path.pop()
        return ValidatorResult.SUCCESS

    @classmethod
    def _typeddict(cls, type_: T.Type) -> PartialValidator:
        required_keys = {k for k, v in T.get_type_hints(type_, include_extras=True).items()
                         if is_required(v)}
        hints = T.get_type_hints(type_)
        validators: T.Dict[object, PartialValidator] = \
            {k: ValidatorResult.get_validator(hint) for k, hint in hints.items()}
        default = ValidatorResult.failure if type_.__total__ else ValidatorResult.success
        return lambda v, obj: \
            v if not isinstance(obj, dict) else \
            v if any(k not in obj for k in required_keys) else \
            v.mapping(dict, ValidatorResult.success,
                      lambda k: validators.get(k, default),
                      obj)

    @classmethod
    def get_validator(cls, type_: T.Type) -> PartialValidator:
        result = cls.CACHE.get(type_, None)
        if not result:
            result = cls.get_validator_uncached(type_)
            cls.CACHE[type_] = result
        return result

    @classmethod
    def get_validator_uncached(cls, type_: T.Type) -> PartialValidator:
        if type_ == T.Any:
            return ValidatorResult.success

        if is_union(type_):
            validators = [cls.get_validator(t) for t in extract_generic(type_)]
            return lambda v, obj: v.union(validators, obj)

        if is_typed_dict(type_):
            return cls._typeddict(type_)

        if is_new_type(type_):
            return cls.get_validator(extract_new_type(type_))

        if is_literal(type_):
            generic = extract_generic(type_)
            return lambda v, obj: cls.SUCCESS if obj in generic else v

        if is_init_var(type_):
            return cls.get_validator(extract_init_var(type_))

        if is_generic_collection(type_):
            origin = extract_origin_collection(type_)
            generic = extract_generic(type_)
            if not generic:
                return lambda v, obj: cls.SUCCESS if isinstance(obj, origin) else v

            if issubclass(origin, T.Mapping):
                key_type, val_type = extract_generic(type_, defaults=(T.Any, T.Any))
                kv = cls.get_validator(key_type)
                vv = lambda k: cls.get_validator(val_type)
                return lambda v, obj: v.mapping(origin, kv, vv, obj)

            elif is_tuple(type_):
                if len(generic) == 1 and generic[0] == ():
                    return lambda v, obj: cls.SUCCESS if isinstance(obj, origin) and not obj else v
                if len(generic) == 2 and generic[1] is ...:
                    iv = cls.get_validator(generic[0])
                    return lambda v, obj: v.sequence(origin, iv, obj)

                validators = [cls.get_validator(t) for t in generic]
                return lambda v, obj: v.tuple(origin, validators, obj)

            field_type = extract_generic(type_, defaults=(T.Any,))[0]
            iv = cls.get_validator(field_type)
            return lambda v, obj: v.sequence(origin, iv, obj)

        if is_type(type_):
            generic = extract_generic(type_)
            if not generic:
                return lambda v, obj: cls.SUCCESS if isinstance(obj, type) else v

            return lambda v, obj: cls.SUCCESS if isinstance(obj, type) and issubclass(obj, generic[0]) else v

        if is_dataclass(type_):
            return lambda v, obj: cls.SUCCESS if isinstance(obj, type_) else v

        if type_ is complex:
            return lambda v, obj: cls.SUCCESS if isinstance(obj, (int, float, complex)) else v
        elif type_ is float:
            return lambda v, obj: cls.SUCCESS if isinstance(obj, (int, float)) else v
        else:
            return lambda v, obj: cls.SUCCESS if isinstance(obj, type_) else v

ValidatorResult.SUCCESS = ValidatorResult()

def validator(type_: T.Type) -> Validator:
    v = ValidatorResult.get_validator(type_)
    return lambda value: v(ValidatorResult(), value)


@lru_cache(maxsize=None)
def dataclass_field_validators(type_: T.Type[DataclassInstance]) -> T.Dict[str, Validator]:
    hints = T.get_type_hints(type_)
    return {k: validator(hint) for k, hint in hints.items()}
