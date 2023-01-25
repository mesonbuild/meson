# Copyright (c) 2023, NumPy Developers.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#        notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above
#        copyright notice, this list of conditions and the following
#        disclaimer in the documentation and/or other materials provided
#        with the distribution.
#
#     * Neither the name of the NumPy Developers nor the names of any
#        contributors may be used to endorse or promote products derived
#        from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import typing as T
import re
from dataclasses import dataclass, field
from enum import IntFlag, auto

from ... import mlog
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

class FeatureSupport(IntFlag):
    NONE: int = 0
    ARG: int = auto()
    FILE: int = auto()

    def __str__(self) -> str:
        return ', '.join(self.to_list())

    def to_list(self) -> T.List[str]:
        return [
            attr for attr in ('ARG', 'FILE')
            if getattr(FeatureSupport, attr) in self
        ]

@dataclass(unsafe_hash=True, order=True)
class ImpliedAttr:
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

    def copy(self) -> 'ImpliedAttr':
        return ImpliedAttr(**self.__dict__)

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

    @staticmethod
    def normalize(lst: 'T.List[ImpliedAttr]'
                  ) -> 'T.List[ImpliedAttr]':
        ret: T.List[ImpliedAttr] = []
        for attr in lst:
            if not attr.match:
                if attr not in ret:
                    ret.append(attr)
                continue
            new_ret: T.List[ImpliedAttr] = []
            attr = attr.copy()
            for ret_attr in ret:
                if not attr.match.match(ret_attr.val):
                    new_ret.append(ret_attr)
                    continue
                if not attr.mfilter:
                    continue
                val = attr.mfilter.findall(ret_attr.val)
                if not val:
                    continue
                attr.val += ret_attr.mjoin.join(val)
            if attr not in ret:
                new_ret.append(attr)
            ret = new_ret
        return ret

@dataclass
class TestResult:
    args: T.List[ImpliedAttr] = field(default_factory=list)
    detect: T.List[ImpliedAttr] = field(default_factory=list)
    headers: T.List[ImpliedAttr] = field(default_factory=list)
    defines: T.List[str] = field(default_factory=list)
    undefines: T.List[str] = field(default_factory=list)
    support: FeatureSupport = field(
        default=FeatureSupport.ARG | FeatureSupport.FILE
    )

    def __add__(self, robj: 'TestResult') -> 'TestResult':
        return TestResult(
            args = ImpliedAttr.normalize(self.args + robj.args),
            headers = ImpliedAttr.normalize(self.headers + robj.headers),
            detect = ImpliedAttr.normalize(self.detect + robj.detect),
            defines = self.defines + [
                v for v in robj.defines
                if v not in self.defines
            ],
            undefines = self.undefines + [
                v for v in robj.undefines
                if v not in self.undefines
            ],
            support = self.support & robj.support
        )

    def to_dict(self) -> T.Dict[str, T.List[str]]:
        ret = {}
        for attr in ('args', 'detect', 'headers'):
            ret[attr] = [str(v) for v in getattr(self, attr)]

        for attr in ('defines', 'undefines'):
            ret[attr] = getattr(self, attr)[:]

        ret['support'] = self.support.to_list()
        return ret


if T.TYPE_CHECKING:
    IMPLIED_ATTR = T.Union[
        None, str, T.Dict[str, str], T.List[
            T.Union[str, T.Dict[str, str]]
        ]
    ]

class Convert:
    @staticmethod
    def _implattr(opt_name: str, values: 'IMPLIED_ATTR',
                  ) -> T.Union[None, T.List[ImpliedAttr]]:
        if values is None:
            return None
        ret: T.List[ImpliedAttr] = []
        values = [values] if isinstance(values, (str, dict)) else values
        accepted_keys = ('val', 'match', 'mfilter', 'mjoin')
        for edict in values:
            if isinstance(edict, str):
                ret.append(ImpliedAttr(val=edict))
                continue
            if not isinstance(edict, dict):
                # It shouldn't happen
                continue
            unknown_keys = [k for k in edict.keys() if k not in accepted_keys]
            if unknown_keys:
                raise MesonException(
                    f'feature.new: unknown keys {unknown_keys} in '
                    f'option {opt_name}'
                )
            val = edict.get('val')
            if val is None:
                raise MesonException(
                    f'feature.new: option "{opt_name}" requires '
                    f'a dictionary with key "val" to be set'
                )
            implattr = ImpliedAttr(val=val, mjoin=edict.get('mjoin', ''))
            for cattr in ('match', 'mfilter'):
                cval = edict.get(cattr)
                if not cval:
                    continue
                try:
                    ccval = re.compile(cval)
                except Exception as e:
                    raise MesonException(
                        'feature.new: unable to '
                        f'compile the regex in option "{opt_name}"\n'
                        f'"{cattr}:{cval}" -> {str(e)}'
                    )
                setattr(implattr, cattr, ccval)
            ret.append(implattr)
        return ret

    @staticmethod
    def implattr(opt_name: str) -> T.Callable[
                 ['IMPLIED_ATTR'],
                 T.Union[None, T.List[ImpliedAttr]]]:
        return lambda values: Convert._implattr(opt_name, values)


if T.TYPE_CHECKING:
    class FeatureKwArgs(TypedDict):
        #implies: T.Optional[T.List['FeatureObject']]
        implies: NotRequired[T.List[T.Any]]
        group: NotRequired[T.List[str]]
        detect: NotRequired[T.List[ImpliedAttr]]
        args: NotRequired[T.List[ImpliedAttr]]
        headers: NotRequired[T.List[ImpliedAttr]]
        test_code: NotRequired[T.Union[str, File]]
        extra_tests: NotRequired[T.Dict[str, T.Union[str, File]]]
        disable: NotRequired[str]

    class FeatureUpdateKwArgs(FeatureKwArgs):
        name: NotRequired[str]
        interest: NotRequired[int]

class FeatureObject(ModuleObject):
    name: str
    interest: int
    implies: T.Set['FeatureObject']
    group: T.List[str]
    detect: T.List[ImpliedAttr]
    args: T.List[ImpliedAttr]
    headers: T.List[ImpliedAttr]
    test_code: T.Union[str, File]
    extra_tests: T.Dict[str, T.Union[str, File]]
    disable: str

    def __init__(self, state: 'ModuleState',
                 args: T.List['TYPE_var'],
                 kwargs: 'TYPE_kwargs') -> None:

        super().__init__()

        IMPLIED_ATTR_TYPES = (
            str, ContainerTypeInfo(dict, str),
            ContainerTypeInfo(list, (dict, str)),
        )

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
            KwargInfo(
                'detect', IMPLIED_ATTR_TYPES,
                convertor=Convert.implattr('detect'), default=[]
            ),
            KwargInfo(
                'args', IMPLIED_ATTR_TYPES, convertor=Convert.implattr('args'),
                default=[]
            ),
            KwargInfo(
                'headers', IMPLIED_ATTR_TYPES,
                convertor=Convert.implattr('headers'), default=[]
            ),
            KwargInfo('test_code', (str, File), default=''),
            KwargInfo(
                'extra_tests', (ContainerTypeInfo(dict, (str, File))),
                default={}
            ),
            KwargInfo('disable', (str), default=''),
        )
        def init_attrs(state: 'ModuleState',
                       args: T.Tuple[str, int],
                       kwargs: 'FeatureKwArgs'
                       ) -> None:
            self.name = args[0]
            self.interest = args[1]
            self.implies = set(kwargs['implies'])
            self.group = kwargs['group']
            self.detect = kwargs['detect']
            self.args = kwargs['args']
            self.headers = kwargs['headers']
            self.test_code = kwargs['test_code']
            self.extra_tests = kwargs['extra_tests']
            self.disable: str = kwargs['disable']

        init_attrs(state, args, kwargs)
        self.methods.update({
            'update': self.update_method,
            'get': self.get_method,
        })

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

    def update_method(self, state: 'ModuleState', args: T.List['TYPE_var'],
                      kwargs: 'TYPE_kwargs') -> 'FeatureObject':
        IMPLIED_ATTR_NTYPES = (
            NoneType, str, ContainerTypeInfo(dict, str),
            ContainerTypeInfo(list, (dict, str)),
        )

        @noPosargs
        @typed_kwargs('feature.feature.update',
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
            KwargInfo(
                'detect', IMPLIED_ATTR_NTYPES,
                convertor=Convert.implattr('detect')
            ),
            KwargInfo(
                'args', IMPLIED_ATTR_NTYPES,
                convertor=Convert.implattr('args')
            ),
            KwargInfo(
                'headers', IMPLIED_ATTR_NTYPES,
                convertor=Convert.implattr('headers')
            ),
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
    @typed_pos_args('feature.feature.get', str)
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
            headers = impl_lst,
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

    def test_args(self, state: 'ModuleState', compiler: 'Compiler'
                  ) -> T.Tuple[bool, T.List[ImpliedAttr], T.List[ImpliedAttr]]:
        check_args = compiler.has_multi_arguments
        args: T.List[ImpliedAttr] = []
        skipped_args: T.List[ImpliedAttr] = []
        cached = True
        for a in self.args:
            result, tcached = check_args([a.val], state.environment)
            if result:
                args.append(a)
            else:
                skipped_args.append(a)
            cached &= tcached
        return cached, args, skipped_args

    def test_headers(self, state: 'ModuleState', compiler: 'Compiler',
                     args: T.List[str]) -> T.Tuple[
                         bool, T.List[ImpliedAttr], T.List[ImpliedAttr]
                     ]:
        check_header = compiler.check_header
        headers: T.List[ImpliedAttr] = []
        skipped_headers: T.List[ImpliedAttr] = []
        cached = True
        for h in self.headers:
            result, tcached = check_header(
                hname=h.val, prefix='', env=state.environment,
                extra_args=args
            )
            if result:
                headers.append(h)
            else:
                skipped_headers.append(h)
            cached &= tcached
        return cached, headers, skipped_headers

    def test_extra(self, state: 'ModuleState', compiler: 'Compiler',
                   args: T.List[str], headers: T.List[str]
                   ) -> T.Tuple[bool, T.List[str], T.List[str]]:
        extra: T.List[str] = []
        skipped_extra: T.List[str] = []
        cached = True
        for extra_name, extra_test in self.extra_tests.items():
            tcached, test, stderr = test_code(
                state, compiler, args, headers, extra_test
            )
            if test:
                extra.append(extra_name)
            else:
                skipped_extra.append(extra_name)
            cached &= tcached
        return cached, extra, skipped_extra

    def test(self, state: 'ModuleState', compiler: 'Compiler',
             force_args: T.Optional[T.List[str]] = None
             ) -> TestResult:

        cached, disabled, error, result = self.test_impl(
            state, compiler, force_args
        )
        log_prefix = f'Test feature "{mlog.bold(self.name)}" :'
        cached_msg = f'({mlog.blue("cached")})'if cached else ''
        if not result:
            reason = (
                mlog.yellow('Disabled') if disabled
                else mlog.red('Unsupported')
            )
            mlog.log(
                log_prefix,
                reason,
                cached_msg
            )
            mlog.debug(
                log_prefix,
                reason,
                'due to',
                error
            )
            return TestResult(support=FeatureSupport.NONE)
        mlog.log(
            log_prefix,
            mlog.green('Supported'),
            cached_msg
        )
        return result

    def test_impl(self, state: 'ModuleState', compiler: 'Compiler',
                  force_args: T.Optional[T.List[str]] = None,
                  _caller: T.Optional[T.Set['FeatureObject']] = None,
                  ) -> T.Tuple[
                      bool, bool, str, T.Optional[TestResult]
                  ]:

        prefix = f'implied feature "{self.name}" ' if _caller else ''
        if self.disable:
            return False, True, f'{prefix}disabled due to {self.disable}', None

        _caller = {self, } if not _caller else _caller.union({self, })
        cached = True
        result = TestResult()
        after = TestResult()
        implies: T.List[FeatureObject] = sorted(self.implies.difference(_caller))
        for fet in implies:
            imp_ret = fet.test_impl(state, compiler, force_args, _caller)
            imp_cached, _, _, imp_result = imp_ret
            if not imp_result:
                return imp_ret
            if fet > self:
                after += imp_result
            else:
                result += imp_result
            cached &= imp_cached

        if force_args is None:
            tcached, rargs, skipped_args = self.test_args(state, compiler)
            if (not rargs and skipped_args) and not self.test_code:
                return (
                    tcached, False,
                    f'{prefix}specified arguments {tuple(skipped_args)} '
                    'are not supported and the test file is not specified',
                    None
                )
            result.args = ImpliedAttr.normalize(
                result.args + rargs + after.args
            )
            cached &= tcached
            args = [a.val for a in result.args]
        else:
            args = force_args

        tcached, rheaders, skipped_headers = self.test_headers(
            state, compiler, args
        )
        if not rheaders and skipped_headers:
            return (
                tcached, False,
                f'{prefix}specified headers '
                f'{[h.val for h in skipped_headers]}'
                'are not supported by the compiler',
                None
            )
        cached &= tcached
        result.headers = ImpliedAttr.normalize(
            result.headers + rheaders + after.headers
        )
        headers = [h.val for h in result.headers]

        if self.test_code:
            tcached, test, stderr = test_code(
                state, compiler, args, headers, self.test_code
            )
            if not test:
                return (
                    tcached, False,
                    f'{prefix}compiler was not able to compile the test code\n'
                    f'Arguments: {str(args)}\n'
                    f'Headers: {str(headers)}\n'
                    f':\n"{stderr}"',
                    None
                )
            cached &= tcached

        if not self.detect:
            detect = [
                ImpliedAttr(val=name) for name in (
                    self.group if self.group else [self.name]
                )
            ]
        else:
            detect = self.detect
        result.detect = ImpliedAttr.normalize(
            result.detect + detect + after.detect
        )

        tcached, extra, skipped_extra = self.test_extra(
            state, compiler, args, headers
        )
        cached &= tcached

        result.defines += [
            df for df in [self.name] + self.group + extra + after.defines
            if df not in result.defines
        ]
        result.undefines += [
            udf for udf in skipped_extra + after.undefines
            if udf not in result.undefines
        ]

        support = FeatureSupport.NONE
        if args and not skipped_args:
            support = FeatureSupport.ARG
        if self.test_code:
            support |= FeatureSupport.FILE
        support &= after.support

        result.support &= support
        return cached, False, '', result
