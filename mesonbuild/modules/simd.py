# Copyright 2017 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import annotations

import typing as T

from .. import mesonlib, mlog
from .. import build
from ..compilers import Compiler
from ..interpreter.type_checking import STATIC_LIB_KWS, SOURCES_KW
from ..interpreterbase import KwargInfo, typed_pos_args, typed_kwargs

from . import ModuleReturnValue, NewExtensionModule, ModuleInfo

if T.TYPE_CHECKING:
    from typing_extensions import TypedDict

    from . import ModuleState
    from ..interpreter import Interpreter
    from ..interpreter import kwargs as kwtypes

    class CheckKw(TypedDict):

        compiler: Compiler
        mmx: T.List[mesonlib.FileOrString]
        sse: T.List[mesonlib.FileOrString]
        sse2: T.List[mesonlib.FileOrString]
        sse3: T.List[mesonlib.FileOrString]
        ssse3: T.List[mesonlib.FileOrString]
        sse41: T.List[mesonlib.FileOrString]
        sse42: T.List[mesonlib.FileOrString]
        avx: T.List[mesonlib.FileOrString]
        avx2: T.List[mesonlib.FileOrString]
        neon: T.List[mesonlib.FileOrString]

# FIXME add Altivec and AVX512.
ISETS = (
    'mmx',
    'sse',
    'sse2',
    'sse3',
    'ssse3',
    'sse41',
    'sse42',
    'avx',
    'avx2',
    'neon',
)

class SimdModule(NewExtensionModule):

    INFO = ModuleInfo('SIMD', '0.42.0', unstable=True)

    def __init__(self, interpreter: Interpreter):
        super().__init__()
        self.methods.update({
            'check': self.check,
        })

        self.interpreter = interpreter

    @typed_pos_args('simd.check', str)
    @typed_kwargs('simd.check',
                  KwargInfo('compiler', Compiler, required=True),
                  *[SOURCES_KW.evolve(name=iset) for iset in ISETS],
                  *STATIC_LIB_KWS,
                  allow_unknown=True) # TODO: Remove after build targets use typed_*_args
    def check(self, state: ModuleState, args: T.Tuple[str], kwargs: CheckKw) -> ModuleReturnValue:
        if 'sources' in kwargs:
            raise mesonlib.MesonException('SIMD module does not support the "sources" keyword')

        result: T.List[build.StaticLibrary] = []
        prefix = args[0]
        compiler = kwargs['compiler']
        conf = build.ConfigurationData()

        static_lib_kwargs = T.cast('T.Dict[str, T.Any]', kwargs.copy())
        del static_lib_kwargs['compiler']
        for iset in ISETS:
            del static_lib_kwargs[iset]
        static_lib_kwargs = T.cast('kwtypes.StaticLibrary', static_lib_kwargs) # type: ignore

        for iset in ISETS:
            if iset not in kwargs:
                continue

            sources = kwargs.get(iset, [])
            if not sources:
                continue

            cargs = compiler.get_instruction_set_args(iset)
            if cargs is None:
                mlog.log(f'Compiler supports {iset}:', mlog.red('NO'))
                continue

            if not compiler.has_multi_arguments(cargs, state.environment)[0]:
                mlog.log(f'Compiler supports {iset}:', mlog.red('NO'))
                continue

            mlog.log(f'Compiler supports {iset}:', mlog.green('YES'))
            conf.values['HAVE_' + iset.upper()] = ('1', f'Compiler supports {iset}.')

            my_name = f'{prefix}_{iset}'

            my_kwargs = static_lib_kwargs.copy()
            my_kwargs['sources'] = sources

            # Add compile args we derived above to those the user provided us
            lang_args_key = compiler.get_language() + '_args'
            old_lang_args = mesonlib.extract_as_list(my_kwargs, lang_args_key)
            all_lang_args = old_lang_args + cargs
            my_kwargs[lang_args_key] = all_lang_args

            lib = self.interpreter.build_target(state.current_node, (my_name, []), my_kwargs, build.StaticLibrary)

            result.append(lib)

        return ModuleReturnValue([result, conf], [conf])

def initialize(*args: T.Any, **kwargs: T.Any) -> SimdModule:
    return SimdModule(*args, **kwargs)
