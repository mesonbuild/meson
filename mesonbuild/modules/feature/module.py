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

from ...compilers import Compiler
from ...interpreter.type_checking import NoneType
from ...interpreterbase.decorators import (
    noKwargs, noPosargs, KwargInfo, typed_kwargs, typed_pos_args,
    ContainerTypeInfo,
)
from .. import ModuleInfo, NewExtensionModule, ModuleReturnValue

from .feature import FeatureObject
from .utils import get_compiler
from .x86_features import x86_features

if T.TYPE_CHECKING:
    from typing import TypedDict
    from ...interpreterbase import TYPE_var, TYPE_kwargs
    from .. import ModuleState
    from .feature import FeatureKwArgs

    class TestKwArgs(TypedDict):
        compiler: T.Optional[Compiler]
        force_args: T.Optional[T.List[str]]
        any: T.Optional[bool]

class Module(NewExtensionModule):
    INFO = ModuleInfo('feature', '0.1.0')

    def __init__(self) -> None:
        super().__init__()
        self.methods.update({
            'new': self.new_method,
            'cpu_features': self.cpu_features_method,
            'test': self.test_method,
            'implicit': self.implicit_method,
            'ahead': self.ahead_method,
            'untied': self.untied_method,
            'sort': self.sort_method,
        })

    def new_method(self, state: 'ModuleState',
                   args: T.List['TYPE_var'],
                   kwargs: 'TYPE_kwargs') -> FeatureObject:
        return FeatureObject(state, args, kwargs)

    @noPosargs
    @typed_kwargs('feature.cpu_features',
        KwargInfo(
            'compiler', (NoneType, Compiler),
        ),
    )
    def cpu_features_method(self, state: 'ModuleState',
                            args: T.List['TYPE_var'],
                            kwargs: T.Dict[str, Compiler]
                            ) -> T.Dict[str, FeatureObject]:
        compiler = kwargs['compiler']
        if compiler is None:
            compiler = get_compiler(state)

        features: T.Dict[str, FeatureObject] = {}
        for func in (
            x86_features,
        ):
            features.update(func(state, compiler))
        return features

    @typed_pos_args('feature.test', varargs=FeatureObject, min_varargs=1)
    @typed_kwargs('feature.test',
        KwargInfo('compiler', (NoneType, Compiler)),
        KwargInfo(
            'force_args', (NoneType, str, ContainerTypeInfo(list, str)),
            listify=True
        ),
        KwargInfo('any', bool, default=False)
    )
    def test_method(self, state: 'ModuleState',
                    args: T.Tuple[T.List[FeatureObject]],
                    kwargs: 'TestKwArgs'
                    ) -> T.List[T.Union[bool, T.Dict[str, T.Any]]]:

        compiler = kwargs.get('compiler')
        force_args = kwargs.get('force_args')
        any_ = kwargs['any']

        if not compiler:
            compiler = get_compiler(state)

        features = self.ahead(args[0])
        if any_:
            features = self.implicit_c(features)

        result = features[0].test(state, compiler, force_args)
        supported_features = []
        if result is not None:
            supported_features = [features[0]]
            for fet in features[1:]:
                ret = fet.test(state, compiler, force_args)
                if ret is None:
                    if any_:
                        continue
                    result = ret
                    break
                supported_features += [fet]
                result += ret

        if result is None:
            return [False, {}]

        result = result.to_dict()
        result['features'] = [
            fet.name for fet in self.implicit_c(supported_features)
        ]
        return [True, result]

    @typed_pos_args('feature.implicit', varargs=FeatureObject, min_varargs=1)
    @noKwargs
    def implicit_method(self, state: 'ModuleState',
                        args: T.Tuple[T.List[FeatureObject]],
                        kwargs: 'TYPE_kwargs'
                        ) -> T.List[FeatureObject]:

        features = args[0]
        return self.implicit(features)

    @typed_pos_args('feature.ahead', varargs=FeatureObject, min_varargs=1)
    @noKwargs
    def ahead_method(self, state: 'ModuleState',
                     args: T.Tuple[T.List[FeatureObject]],
                     kwargs: 'TYPE_kwargs'
                     ) -> T.List[FeatureObject]:

        features = args[0]
        return self.ahead(features)

    @typed_pos_args('feature.untied', varargs=FeatureObject, min_varargs=1)
    @noKwargs
    def untied_method(self, state: 'ModuleState',
                      args: T.Tuple[T.List[FeatureObject]],
                      kwargs: 'TYPE_kwargs'
                      ) -> T.List[FeatureObject]:
        features = args[0]
        ret: T.List[FeatureObject] = []
        for fet in features:
            tied = {
                sub_fet for sub_fet in ret
                if sub_fet in fet.implies and fet in sub_fet.implies
            }
            if tied:
                stied = sorted(tied.union({fet, }))
                if fet not in stied[1:]:
                    continue
                ret.remove(stied[0])
            ret.append(fet)
        return ret

    @typed_pos_args('feature.sort', varargs=FeatureObject, min_varargs=1)
    @noKwargs
    def sort_method(self, state: 'ModuleState',
                    args: T.Tuple[T.List[FeatureObject]],
                    kwargs: 'TYPE_kwargs'
                    ) -> T.List[FeatureObject]:
        return sorted(args[0])

    @staticmethod
    def implicit(features: T.Sequence[FeatureObject]) -> T.List[FeatureObject]:
        implicit = set().union(*[fet.get_implicit() for fet in features])
        # since features can imply each other
        implicit.difference_update(set(features))
        return sorted(implicit)

    @staticmethod
    def implicit_c(features: T.Sequence[FeatureObject]) -> T.List[FeatureObject]:
        implicit = set().union(*[fet.get_implicit() for fet in features], features)
        return sorted(implicit)

    @staticmethod
    def ahead(features: T.Sequence[FeatureObject]) -> T.List[FeatureObject]:
        implicit = set().union(*[fet.get_implicit() for fet in features])
        ahead = [fet for fet in features if fet not in implicit]
        if len(ahead) == 0:
            # return the highest interested feature
            # if all features imply each other
            ahead = list(sorted(features, reverse=True)[:1])
        return ahead

