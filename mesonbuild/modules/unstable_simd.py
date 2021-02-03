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

import typing as T

from . import ExtensionModule
from .. import mesonlib, compilers, mlog
from ..interpreterbase import FeatureNew, typed_pos_args

class SimdModule(ExtensionModule):

    @FeatureNew('SIMD module', '0.42.0')
    def __init__(self, interpreter):
        super().__init__(interpreter)
        self.snippets.add('check')
        # FIXME add Altivec and AVX512.
        self.isets = ('mmx',
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

    @typed_pos_args('simdmod.check', str)
    def check(self, interpreter, state, args: T.Tuple[str], kwargs):
        result = []
        prefix = args[0]
        if 'compiler' not in kwargs:
            raise mesonlib.MesonException('Must specify compiler keyword')
        if 'sources' in kwargs:
            raise mesonlib.MesonException('SIMD module does not support the "sources" keyword')
        basic_kwargs = {}
        for key, value in kwargs.items():
            if key not in self.isets and key != 'compiler':
                basic_kwargs[key] = value
        compiler = kwargs['compiler'].compiler
        if not isinstance(compiler, compilers.compilers.Compiler):
            raise mesonlib.MesonException('Compiler argument must be a compiler object.')
        cdata = interpreter.func_configuration_data(None, [], {})
        conf = cdata.held_object
        for iset in self.isets:
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
            result.append(interpreter.func_static_lib(None, [libname], lib_kwargs))
        return [result, cdata]

def initialize(*args, **kwargs):
    return SimdModule(*args, **kwargs)
