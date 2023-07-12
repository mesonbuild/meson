# Copyright (c) 2023, NumPy Developers.
# All rights reserved.

import typing as T
import re
from dataclasses import dataclass, field
from enum import IntFlag, auto

from ...mesonlib import File, MesonException
from ...interpreter.type_checking import NoneType
from ...interpreterbase.decorators import (
    noKwargs, noPosargs, KwargInfo, typed_kwargs, typed_pos_args,
    ContainerTypeInfo, noArgsFlattening
)
from .. import ModuleObject
from .utils import test_code, get_compiler

if T.TYPE_CHECKING:
    from typing import TypedDict
    from typing_extensions import NotRequired
    from ...interpreterbase import TYPE_var, TYPE_kwargs
    from ...compilers import Compiler
    from .. import ModuleState

@dataclass(unsafe_hash=True, order=True)
class ConflictAttr:
    """
    Data class representing an feature attribute that may conflict
    with other features attributes.

    The reason behind this class to clear any possible conflicts with
    compiler arguments when they joined together due gathering
    the implied features or concatenate non-implied features.

    Attributes:
        val: The value of the feature attribute.
        match: Regular expression pattern for matching conflicted values
               (optional).
        mfilter: Regular expression pattern for filtering these conflicted values
               (optional).
        mjoin: String used to join filtered values (optional)

    """
    val: str = field(hash=True, compare=True)
    match: T.Union[re.Pattern, None] = field(
        default=None, hash=False, compare=False
    )
    mfilter: T.Union[re.Pattern, None] = field(
        default=None, hash=False, compare=False
    )
    mjoin: str = field(default='', hash=False, compare=False)

    def __str__(self) -> str:
        return self.val

    def copy(self) -> 'ConflictAttr':
        return ConflictAttr(**self.__dict__)

    def to_dict(self) -> T.Dict[str, str]:
        ret: T.Dict[str, str] = {}
        for attr in ('val', 'mjoin'):
            ret[attr] = getattr(self, attr)
        for attr in ('match', 'mfilter'):
            val = getattr(self, attr)
            if not val:
                val = ''
            else:
                val = str(val)
            ret[attr] = val
        return ret

class KwargConfilctAttr(KwargInfo):
    def __init__(self, func_name: str, opt_name: str, default: T.Any = None):
        types = [
            str, ContainerTypeInfo(dict, str),
            ContainerTypeInfo(list, (dict, str))
        ]
        if default is None:
            types += [NoneType]
        super().__init__(
            opt_name, tuple(types),
            convertor = lambda values: self.convert(
                func_name, opt_name, values
            ),
            default = default
        )

    @staticmethod
    def convert(func_name:str, opt_name: str, values: 'IMPLIED_ATTR',
                ) -> T.Union[None, T.List[ConflictAttr]]:
        if values is None:
            return None
        ret: T.List[ConflictAttr] = []
        values = [values] if isinstance(values, (str, dict)) else values
        accepted_keys = ('val', 'match', 'mfilter', 'mjoin')
        for edict in values:
            if isinstance(edict, str):
                if edict:
                    ret.append(ConflictAttr(val=edict))
                continue
            if not isinstance(edict, dict):
                # It shouldn't happen
                # TODO: need exception here
                continue
            unknown_keys = [k for k in edict.keys() if k not in accepted_keys]
            if unknown_keys:
                raise MesonException(
                    f'{func_name}: unknown keys {unknown_keys} in '
                    f'option {opt_name}'
                )
            val = edict.get('val')
            if val is None:
                raise MesonException(
                    f'{func_name}: option "{opt_name}" requires '
                    f'a dictionary with key "val" to be set'
                )
            implattr = ConflictAttr(val=val, mjoin=edict.get('mjoin', ''))
            for cattr in ('match', 'mfilter'):
                cval = edict.get(cattr)
                if not cval:
                    continue
                try:
                    ccval = re.compile(cval)
                except Exception as e:
                    raise MesonException(
                        '{func_name}: unable to '
                        f'compile the regex in option "{opt_name}"\n'
                        f'"{cattr}:{cval}" -> {str(e)}'
                    )
                setattr(implattr, cattr, ccval)
            ret.append(implattr)
        return ret

if T.TYPE_CHECKING:
    IMPLIED_ATTR = T.Union[
        None, str, T.Dict[str, str], T.List[
            T.Union[str, T.Dict[str, str]]
        ]
    ]
    class FeatureKwArgs(TypedDict):
        #implies: T.Optional[T.List['FeatureObject']]
        implies: NotRequired[T.List[T.Any]]
        group: NotRequired[T.List[str]]
        detect: NotRequired[T.List[ConflictAttr]]
        args: NotRequired[T.List[ConflictAttr]]
        test_code: NotRequired[T.Union[str, File]]
        extra_tests: NotRequired[T.Dict[str, T.Union[str, File]]]
        disable: NotRequired[str]

    class FeatureUpdateKwArgs(FeatureKwArgs):
        name: NotRequired[str]
        interest: NotRequired[int]

class FeatureObject(ModuleObject):
    """
    A data class that represents the feature.

    A feature is a unit of work that can be developed, tested, and deployed independently.

    Attributes:
      name: The name of the feature.
      interest: The interest level of the feature.
                It used for sorting and to determine succor features.
      implies: A set of features objects that are implied by this feature.
               (Optional)
               This means that if this feature is enabled,
               then the implied features will also be enabled.
               If any of the implied features is not supported by the platform
               or the compiler this feature will also considerd not supported.
      group: A list of

      detect: A list of strings that identify the methods that can be used to detect whether the feature is supported.
      args: A list of strings that identify the arguments that are required to enable this feature.
      test_code: A string or a file object that contains the test code for this feature.
      extra_tests: A dictionary that maps from the name of a test to the test code for that test.
      disable: A string that specifies why this feature is disabled.
    """
    name: str
    interest: int
    implies: T.Set['FeatureObject']
    group: T.List[str]
    detect: T.List[ConflictAttr]
    args: T.List[ConflictAttr]
    test_code: T.Union[str, File]
    extra_tests: T.Dict[str, T.Union[str, File]]
    disable: str

    def __init__(self, state: 'ModuleState',
                 args: T.List['TYPE_var'],
                 kwargs: 'TYPE_kwargs') -> None:

        super().__init__()

        @typed_pos_args('feature.new', str, int)
        @typed_kwargs('feature.new',
            KwargInfo(
                'implies',
                (FeatureObject, ContainerTypeInfo(list, FeatureObject)),
                default=[], listify=True
            ),
            KwargInfo(
                'group', (str, ContainerTypeInfo(list, str)),
                default=[], listify=True
            ),
            KwargConfilctAttr('feature.new', 'detect', default=[]),
            KwargConfilctAttr('feature.new', 'args', default=[]),
            KwargInfo('test_code', (str, File), default=''),
            KwargInfo(
                'extra_tests', (ContainerTypeInfo(dict, (str, File))),
                default={}
            ),
            KwargInfo('disable', (str), default=''),
        )
        def init_attrs(state: 'ModuleState',
                       args: T.Tuple[str, int],
                       kwargs: 'FeatureKwArgs') -> None:
            self.name = args[0]
            self.interest = args[1]
            self.implies = set(kwargs['implies'])
            self.group = kwargs['group']
            self.detect = kwargs['detect']
            self.args = kwargs['args']
            self.test_code = kwargs['test_code']
            self.extra_tests = kwargs['extra_tests']
            self.disable: str = kwargs['disable']
            if not self.detect:
                if self.group:
                    self.detect = [ConflictAttr(val=f) for f in self.group]
                else:
                    self.detect = [ConflictAttr(val=self.name)]

        init_attrs(state, args, kwargs)
        self.methods.update({
            'update': self.update_method,
            'get': self.get_method,
        })

    def update_method(self, state: 'ModuleState', args: T.List['TYPE_var'],
                      kwargs: 'TYPE_kwargs') -> 'FeatureObject':
        @noPosargs
        @typed_kwargs('feature.update',
            KwargInfo('name', (NoneType, str)),
            KwargInfo('interest', (NoneType, int)),
            KwargInfo(
                'implies', (
                    NoneType, FeatureObject,
                    ContainerTypeInfo(list, FeatureObject)
                ),
                listify=True
            ),
            KwargInfo(
                'group', (NoneType, str, ContainerTypeInfo(list, str)),
                listify=True
            ),
            KwargConfilctAttr('feature.update', 'detect'),
            KwargConfilctAttr('feature.update', 'args'),
            KwargInfo('test_code', (NoneType, str, File)),
            KwargInfo(
                'extra_tests', (
                    NoneType, ContainerTypeInfo(dict, (str, File)))
            ),
            KwargInfo('disable', (NoneType, str)),
        )
        def update(state: 'ModuleState', args: T.List['TYPE_var'],
                   kwargs: 'FeatureUpdateKwArgs') -> None:
            for k, v in kwargs.items():
                if v is not None and k != 'implies':
                    setattr(self, k, v)
            implies = kwargs.get('implies')
            if implies is not None:
                self.implies = set(implies)
        update(state, args, kwargs)
        return self

    @noKwargs
    @typed_pos_args('feature.get', str)
    def get_method(self, state: 'ModuleState', args: T.Tuple[str],
                   kwargs: 'TYPE_kwargs') -> 'TYPE_var':

        impl_lst = lambda lst: [v.to_dict() for v in lst]
        noconv = lambda v: v
        dfunc = dict(
            name = noconv,
            interest = noconv,
            group = noconv,
            implies = lambda v: [fet.name for fet in sorted(v)],
            detect = impl_lst,
            args = impl_lst,
            test_code = noconv,
            extra_tests = noconv,
            disable = noconv
        )
        cfunc = dfunc.get(args[0])
        if cfunc is None:
            raise MesonException(f'Key {args[0]!r} is not in the feature.')
        return cfunc(getattr(self, args[0]))

    def get_implicit(self, _caller: T.Set['FeatureObject'] = None
                     ) -> T.Set['FeatureObject']:
        # infinity recursive guard since
        # features can imply each other
        _caller = {self, } if not _caller else _caller.union({self, })
        implies = self.implies.difference(_caller)
        ret = self.implies
        for sub_fet in implies:
            ret = ret.union(sub_fet.get_implicit(_caller))
        return ret

    def __hash__(self) -> int:
        return hash(str(id(self)) + self.name)

    def __eq__(self, robj: object) -> bool:
        if not isinstance(robj, FeatureObject):
            return False
        return self is robj and self.name == robj.name

    def __lt__(self, robj: object) -> T.Any:
        if not isinstance(robj, FeatureObject):
            return NotImplemented
        return self.interest < robj.interest

    def __le__(self, robj: object) -> T.Any:
        if not isinstance(robj, FeatureObject):
            return NotImplemented
        return self.interest <= robj.interest

    def __gt__(self, robj: object) -> T.Any:
        return robj < self

    def __ge__(self, robj: object) -> T.Any:
        return robj <= self

