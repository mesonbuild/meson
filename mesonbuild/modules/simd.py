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
from ..interpreter.type_checking import BT_SOURCES_KW, STATIC_LIB_KWS
from ..interpreterbase.decorators import KwargInfo, typed_pos_args, typed_kwargs

from . import ExtensionModule, ModuleInfo

if T.TYPE_CHECKING:
    from ..interpreter import kwargs as kwtypes
    from ..interpreter.type_checking import SourcesVarargsType

    class CheckKw(kwtypes.StaticLibrary):

        compiler: Compiler
        mmx: SourcesVarargsType
        sse: SourcesVarargsType
        sse2: SourcesVarargsType
        sse3: SourcesVarargsType
        ssse3: SourcesVarargsType
        sse41: SourcesVarargsType
        sse42: SourcesVarargsType
        avx: SourcesVarargsType
        avx2: SourcesVarargsType
        neon: SourcesVarargsType


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


class SimdModule(ExtensionModule):

    INFO = ModuleInfo('SIMD', '0.42.0', unstable=True)

    def __init__(self, interpreter):
        super().__init__(interpreter)
        self.methods.update({
            'check': self.check,
        })

    @typed_pos_args('simd.check', str)
    @typed_kwargs('simd.check',
                  KwargInfo('compiler', Compiler, required=True),
                  *[BT_SOURCES_KW.evolve(name=iset) for iset in ISETS],
                  *[a for a in STATIC_LIB_KWS if a.name != 'sources'],
                  allow_unknown=True) # Because we also accept STATIC_LIB_KWS, but build targets have not been completely ported to typed_pos_args/typed_kwargs.
    def check(self, state, args: T.Tuple[str], kwargs: CheckKw):
        result: T.List[build.StaticLibrary] = []
        if 'sources' in kwargs:
            raise mesonlib.MesonException('SIMD module does not support the "sources" keyword')
        prefix = args[0]
        basic_kwargs = {}
        for key, value in kwargs.items():
            if key not in ISETS and key != 'compiler':
                basic_kwargs[key] = value
        compiler = kwargs['compiler']
        conf = build.ConfigurationData()
        for iset in ISETS:
            if iset not in kwargs:
                continue
            iset_fname = kwargs[iset] # Might also be an array or Files. static_library will validate.
            args = compiler.get_instruction_set_args(iset)
            if args is None:
                mlog.log('Compiler supports %s:' % iset, mlog.red('NO'))
                continue
            if args:
                if not compiler.has_multi_arguments(args, state.environment)[0]:
                    mlog.log('Compiler supports %s:' % iset, mlog.red('NO'))
                    continue
            mlog.log('Compiler supports %s:' % iset, mlog.green('YES'))
            conf.values['HAVE_' + iset.upper()] = ('1', 'Compiler supports %s.' % iset)
            libname = prefix + '_' + iset
            lib_kwargs = {'sources': iset_fname,
                          }
            lib_kwargs.update(basic_kwargs)
            langarg_key = compiler.get_language() + '_args'
            old_lang_args = mesonlib.extract_as_list(lib_kwargs, langarg_key)
            all_lang_args = old_lang_args + args
            lib_kwargs[langarg_key] = all_lang_args
            result.append(self.interpreter.func_static_lib(None, [libname], lib_kwargs))
        return [result, conf]

def initialize(*args, **kwargs):
    return SimdModule(*args, **kwargs)
