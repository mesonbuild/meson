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
from textwrap import dedent

from ... import mlog
from .feature import FeatureObject

if T.TYPE_CHECKING:
    from ...compilers import Compiler
    from ...interpreterbase import TYPE_var, TYPE_kwargs
    from .. import ModuleState

def test_code_main(code: str) -> str:
    return dedent(f'''\
        int main(int, char **argv)
        {{
           char *src = argv[1];
           {dedent(code)}
           return 0;
        }}
    ''')

def test_code(NAME: str, code: str) -> str:
    return dedent(f'''\
        #if defined(DETECT_FEATURES) && defined(__{NAME}__)
            #error "HOST/ARCH doesn't support {NAME}"
        #endif
        {test_code_main(code)}
    ''')

def feature(state: 'ModuleState', name: str, interest: int,
            kwargs: 'TYPE_kwargs') -> FeatureObject:
    code = kwargs.get('test_code')
    extra_tests = kwargs.get('extra_tests')
    if isinstance(code, str):
        kwargs['test_code'] = test_code(name, code)
    if isinstance(extra_tests, dict):
        kwargs['extra_tests'] = {
            tname: test_code_main(code) if isinstance(code, str) else code
            for tname, code in extra_tests.items()
        }
    return FeatureObject(state, [name, interest], kwargs)

def _init_features(state: 'ModuleState') -> T.Dict[str, FeatureObject]:
    features: T.Dict[str, FeatureObject] = {}
    fet: T.Callable[[str, int, 'TYPE_kwargs'], FeatureObject] = \
        lambda name, interest, kwargs: features.setdefault(
            name, feature(state, name, interest, kwargs)
        )

    cpu_family = state.build_machine.cpu_family
    is_x86 = cpu_family in ('x86', 'x86_64', 'x64')
    SSE = fet('SSE', 1, dict(
        headers='xmmintrin.h',
        disable=(
            f'not supported by build machine "{cpu_family}"'
            if not is_x86 else ''
        ),
        test_code='''\
            __m128 s0 = _mm_loadu_ps((float*)src);
            __m128 s1 = _mm_loadu_ps((float*)src+4);
            __m128 rt = _mm_add_ps(s0, s1);
            _mm_storeu_ps((float*)src, rt);
        '''
    ))
    SSE2 = fet('SSE2', 2, dict(
        implies=SSE, headers='emmintrin.h',
        test_code='''\
            __m128i s0 = _mm_loadu_si128((__m128i*)src);
            __m128i s1 = _mm_loadu_si128((__m128i*)src+16);
            __m128i rt = _mm_add_epi16(s0, s1);
            _mm_storeu_si128((__m128i*)src, rt);
        '''
    ))
    SSE3 = fet('SSE3', 3, dict(
        implies=SSE2, headers='pmmintrin.h',
        test_code='''\
            __m128 s0 = _mm_loadu_ps((float*)src);
            __m128 s1 = _mm_loadu_ps((float*)src+4);
            __m128 rt = _mm_hadd_ps(s0, s1);
            _mm_storeu_ps((float*)src, rt);
        '''
    ))
    if state.build_machine.is_64_bit:
        SSE.update_method(state, [], dict(implies=[SSE2, SSE3]))
        SSE2.update_method(state, [], dict(implies=[SSE, SSE3]))

    SSSE3 = fet('SSSE3', 4, dict(
        implies=SSE3, headers='tmmintrin.h',
        test_code='''\
            __m128i s0 = _mm_loadu_si128((__m128i*)src);
            __m128i s1 = _mm_loadu_si128((__m128i*)src+16);
            __m128i rt = _mm_hadd_epi16(s0, s1);
            _mm_storeu_si128((__m128i*)src, rt);
        '''
    ))
    SSE41 = fet('SSE41', 5, dict(
        implies=SSSE3, headers='smmintrin.h',
        test_code='''\
            __m128 s0 = _mm_loadu_ps((float*)src);
            __m128 rt = _mm_ceil_ps(s0);
            _mm_storeu_ps((float*)src, rt);
        '''
    ))
    POPCNT = fet('POPCNT', 6, dict(
        implies=SSE41, headers='popcntintrin.h',
        test_code='''\
            unsigned long long a = *((unsigned long long*)src);
            unsigned int b = *((unsigned int*)src+4);
            int rt;
        #if defined(_M_X64) || defined(__x86_64__)
            a = _mm_popcnt_u64(a);
        #endif
            b = _mm_popcnt_u32(b);
            rt = (int)a + (int)b;
            _mm_storeu_si128((__m128i*)src, _mm_set1_epi32(rt));
        '''
    ))
    SSE42 = fet('SSE42', 7, dict(
        implies=POPCNT,
        test_code='''\
            __m128i s0 = _mm_loadu_si128((__m128i*)src);
            __m128i s1 = _mm_loadu_si128((__m128i*)src+16);
            __m128i rt = _mm_cmpgt_epi64(s0, s1);
            _mm_storeu_si128((__m128i*)src, rt);
        '''
    ))
    # 7-20 left as margin for any extra features
    AVX = fet('AVX', 20, dict(
        implies=SSE42,
        headers='immintrin.h',
        detect=dict(val='AVX', match='.*'),
        test_code='''\
            __m256 s0 = _mm256_loadu_ps((float*)src);
            __m256 s1 = _mm256_loadu_ps((float*)src+8);
            __m256 rt = _mm256_add_ps(s0, s1);
            _mm256_storeu_ps((float*)src, rt);
        '''
    ))
    # Amd abandon these two features, should we remove them?
    XOP = fet('XOP', 21, dict(
        implies=AVX, headers='x86intrin.h',
        test_code='''\
            __m128i s0 = _mm_loadu_si128((__m128i*)src);
            __m128i s1 = _mm_loadu_si128((__m128i*)src+16);
            __m128i rt = _mm_comge_epu32(s0, s1);
            _mm_storeu_si128((__m128i*)src, rt);
        '''
    ))
    FMA4 = fet('FMA4', 22, dict(
        implies=AVX, headers='x86intrin.h',
        test_code='''\
            __m128 s0 = _mm_loadu_ps((float*)src);
            __m128 s1 = _mm_loadu_ps((float*)src+4);
            __m128 s2 = _mm_loadu_ps((float*)src+8);
            __m128 rt = _mm256_macc_ps(s0, s1, s2);
            _mm_storeu_ps((float*)src, rt);
        '''
    ))
    # x86 half-precision
    F16C = fet('F16C', 23, dict(
        implies=AVX,
        test_code=f'''\
            __m128i s0 = _mm_loadu_si128((__m128i*)src);
            __m128 rt = _mm_cvtph_ps(s0);
            _mm_storeu_ps((float*)src, rt);
        '''
    ))
    FMA3 = fet('FMA3', 24, dict(
        implies=F16C,
        test_code=f'''\
            __m256 s0 = _mm256_loadu_ps((float*)src);
            __m256 s1 = _mm256_loadu_ps((float*)src + 8);
            __m256 s2 = _mm256_loadu_ps((float*)src + 16);
            __m256 rt = _mm256_fmadd_ps(s0, s1, s2);
            _mm256_storeu_ps((float*)src, rt);
        '''
    ))
    AVX2 = fet('AVX2', 25, dict(
        implies=F16C,
        test_code=f'''\
            __m256i s0 = _mm256_loadu_si256((__m256i*)src);
            __m256i rt = _mm256_abs_epi16(s0);
            _mm256_storeu_si256((__m256i*)src, rt);
        '''
    ))
    # 25-40 left as margin for any extra features
    AVX512_COMMON = fet('AVX512_COMMON', 40, dict(
        implies=[FMA3, AVX2],
        group = ['AVX512F', 'AVX512CD'],
        detect = [
            dict(val='AVX512F', match='.*'),
            'AVX512CD'
        ],
        test_code=f'''\
            __m512i s0 = _mm512_loadu_si512((__m512i*)src);
            __m512i rt = _mm512_abs_epi32(s0);
            /* avx512cd */
            rt = _mm512_lzcnt_epi32(rt);
            _mm512_storeu_si512((__m512i*)src, rt);
        ''',
        extra_tests = dict(
            AVX512F_REDUCE=f'''\
                __m512i si = _mm512_loadu_si512((__m512i*)src);
                __m512 ps = _mm512_loadu_ps((__m512*)src);
                __m512d pd = _mm512_loadu_pd((__m512d*)src);
                /* add */
                float sum_ps  = _mm512_reduce_add_ps(ps);
                double sum_pd = _mm512_reduce_add_pd(pd);
                int sum_int   = (int)_mm512_reduce_add_epi64(si);
                    sum_int  += (int)_mm512_reduce_add_epi32(si);
                /* mul */
                sum_ps  += _mm512_reduce_mul_ps(ps);
                sum_pd  += _mm512_reduce_mul_pd(pd);
                sum_int += (int)_mm512_reduce_mul_epi64(si);
                sum_int += (int)_mm512_reduce_mul_epi32(si);
                /* min */
                sum_ps  += _mm512_reduce_min_ps(ps);
                sum_pd  += _mm512_reduce_min_pd(pd);
                sum_int += (int)_mm512_reduce_min_epi32(si);
                sum_int += (int)_mm512_reduce_min_epu32(si);
                sum_int += (int)_mm512_reduce_min_epi64(si);
                /* max */
                sum_ps  += _mm512_reduce_max_ps(ps);
                sum_pd  += _mm512_reduce_max_pd(pd);
                sum_int += (int)_mm512_reduce_max_epi32(si);
                sum_int += (int)_mm512_reduce_max_epu32(si);
                sum_int += (int)_mm512_reduce_max_epi64(si);
                /* and */
                sum_int += (int)_mm512_reduce_and_epi32(si);
                sum_int += (int)_mm512_reduce_and_epi64(si);
                /* or */
                sum_int += (int)_mm512_reduce_or_epi32(si);
                sum_int += (int)_mm512_reduce_or_epi64(si);
                sum_int += (int)sum_ps + (int)sum_pd;
                *(int*)src = sum_int;
            '''
        )
    ))
    AVX512_KNL = fet('AVX512_KNL', 41, dict(
        implies=AVX512_COMMON,
        group = ['AVX512ER', 'AVX512PF'],
        test_code=f'''\
            int base[128];
            __m512d ad = _mm512_loadu_pd((__m512d*)src);
            /* ER */
            __m512i a = _mm512_castpd_si512(_mm512_exp2a23_pd(ad));
            /* PF */
            _mm512_mask_prefetch_i64scatter_pd(
                base, _mm512_cmpeq_epi64_mask(a, a), a, 1, _MM_HINT_T1
            );
            *(int*)src = base[0];
        '''
    ))
    AVX512_KNM = fet('AVX512_KNM', 42, dict(
        implies=AVX512_KNL,
        group = ['AVX5124FMAPS', 'AVX5124VNNIW', 'AVX512VPOPCNTDQ'],
        test_code=f'''\
            __m512i si = _mm512_loadu_si512((__m512i*)src);
            __m512 ps  = _mm512_loadu_ps((__m512*)src + 64);
            /* 4FMAPS */
            ps = _mm512_4fmadd_ps(ps, ps, ps, ps, ps, NULL);
            /* 4VNNIW */
            si = _mm512_4dpwssd_epi32(si, si, si, si, si, NULL);
            /* VPOPCNTDQ */
            si = _mm512_popcnt_epi64(si);
            si = _mm512_add_epi32(si, _mm512_castps_si512(ps));
            _mm512_storeu_si512((__m512i*)src, si);
        '''
    ))
    AVX512_SKX = fet('AVX512_SKX', 43, dict(
        implies=AVX512_COMMON,
        group = ['AVX512VL', 'AVX512BW', 'AVX512DQ'],
        test_code=f'''\
            __m512i aa = _mm512_abs_epi32(_mm512_loadu_si512((__m512i*)src));
            /* VL */
            __m256i a = _mm256_abs_epi64(_mm512_extracti64x4_epi64(aa, 1));
            /* DQ */
            __m512i b = _mm512_broadcast_i32x8(a);
            /* BW */
            b = _mm512_abs_epi16(b);
            _mm512_storeu_si512((__m512i*)src, b);
        ''',
        extra_tests = dict(
            AVX512BW_MASK=f'''\
                __m512i s0 = _mm512_loadu_si512((__m512i*)src);
                __m512i s1 = _mm512_loadu_si512((__m512i*)src + 64);
                __mmask64 m64 = _mm512_cmpeq_epi8_mask(s0, s1);
                m64 = _kor_mask64(m64, m64);
                m64 = _kxor_mask64(m64, m64);
                m64 = _cvtu64_mask64(_cvtmask64_u64(m64));
                m64 = _mm512_kunpackd(m64, m64);
                m64 = (__mmask64)_mm512_kunpackw((__mmask32)m64, (__mmask32)m64);
                *(int*)src = (int)_cvtmask64_u64(m64);
            ''',
            AVX512DQ_MASK=f'''\
                __m512i s0 = _mm512_loadu_si512((__m512i*)src);
                __m512i s1 = _mm512_loadu_si512((__m512i*)src + 64);
                __mmask8 m8 = _mm512_cmpeq_epi64_mask(s0, s1);
                m8 = _kor_mask8(m8, m8);
                m8 = _kxor_mask8(m8, m8);
                m8 = _cvtu32_mask8(_cvtmask8_u32(m8));
                *(int*)src = (int)_cvtmask8_u32(m8);
            '''
        )
    ))
    AVX512_CLX = fet('AVX512_CLX', 44, dict(
        implies=AVX512_SKX,
        group = 'AVX512VNNI',
        test_code=f'''\
            /* VNNI */
            __m512i a = _mm512_loadu_si512((__m512i*)src);
                    a = _mm512_dpbusd_epi32(a, _mm512_setzero_si512(), a);
            _mm512_storeu_si512((__m512i*)src, a);
        '''
    ))
    AVX512_CNL = fet('AVX512_CNL', 45, dict(
        implies=AVX512_SKX,
        group = ['AVX512IFMA', 'AVX512VBMI'],
        test_code=f'''\
            __m512i a = _mm512_loadu_si512((const __m512i*)src);
            /* IFMA */
            a = _mm512_madd52hi_epu64(a, a, _mm512_setzero_si512());
            /* VMBI */
            a = _mm512_permutex2var_epi8(a, _mm512_setzero_si512(), a);
            _mm512_storeu_si512((__m512i*)src, a);
        '''
    ))
    AVX512_ICL = fet('AVX512_ICL', 46, dict(
        implies=[AVX512_CLX, AVX512_CNL],
        group = ['AVX512VBMI2', 'AVX512BITALG', 'AVX512VPOPCNTDQ'],
        test_code=f'''\
            __m512i a = _mm512_loadu_si512((__m512i*)src);
            /* VBMI2 */
            a = _mm512_shrdv_epi64(a, a, _mm512_setzero_si512());
            /* BITLAG */
            a = _mm512_popcnt_epi8(a);
            /* VPOPCNTDQ */
            a = _mm512_popcnt_epi64(a);
            _mm512_storeu_si512((__m512i*)src, a);
        '''
    ))
    return features

def _features_args(state: 'ModuleState',
                   compiler: 'Compiler',
                   features: T.Dict[str, FeatureObject]) -> None:
    cid = compiler.get_id()
    # for both unix-like and msvc-like
    if 'intel' in cid:
        # Intel Compiler doesn't support AVX2 or FMA3 independently
        for fet, implies in (
            'FMA3', ('F16C', 'AVX2'),
            'AVX2', ('F16C', 'FMA3'),
        ):
            features[fet].update_method(state, [], {
                'implies': [features[sub_fet] for sub_fet in implies]
            })
        for dis_fet in ('XOP', 'FMA4'):
            features[dis_fet].update_method(state, [], {
                'disable': 'Intel Compiler does not support it'
            })
    if 'intel-cl' in cid:
        for fet in (
            'SSE', 'SSE2', 'SSE3', 'SSSE3', 'AVX'
        ):
            features[fet].update_method(state, [], {
                'args': dict(val='/arch:' + fet, match='/arch:.*')
            })
        # POPCNT, and F16C don't own private FLAGS still
        # Intel's compiler provides ABI capability for them.
        for fet, arg in (
            ('SSE42', dict(
                val='/arch:SSE4.2', match='/arch:.*'
            )),
            ('FMA3', dict(
                val='/arch:CORE-AVX2', match='/arch:.*'
            )),
            ('AVX2', dict(
                val='/arch:CORE-AVX2', match='/arch:.*'
            )),
            ('AVX512_COMMON', dict(
                val='/Qx:COMMON-AVX512', match='/arch:.*'
            )),
            ('AVX512_KNL', dict(
                val='/Qx:KNL', match='/[arch|Qx]:.*'
            )),
            ('AVX512_KNM', dict(
                val='/Qx:KNM', match='/[arch|Qx]:.*'
            )),
            ('AVX512_SKX', dict(
                val='/Qx:SKYLAKE-AVX512', match='/[arch|Qx]:.*'
            )),
            ('AVX512_CLX', dict(
                val='/Qx:CASCADELAKE', match='/[arch|Qx]:.*'
            )),
            ('AVX512_CNL', dict(
                val='/Qx:CANNONLAKE', match='/[arch|Qx]:.*'
            )),
            ('AVX512_ICL', dict(
                val='/Qx:ICELAKE-CLIENT', match='/[arch|Qx]:.*'
            )),
        ):
            features[fet].update_method(state, [], {'args': arg})
    elif 'intel' in cid:
        for fet in (
            'SSE', 'SSE2', 'SSE3', 'SSSE3', 'AVX'
        ):
            features[fet].update_method(state, [], {
                'args': '-m' + fet.lower()
            })
        # POPCNT, and F16C don't own private FLAGS still
        # Intel's compiler provides ABI capability for them.

        # we specify the arguments that we need to filterd
        # from implied features rather than blinedly removes all args(.*)
        # since args may updated from outside.
        filter_all = ".*m[sse|avx|arch\=|-x[a-z0-9\-]].*"
        for fet, arg in (
            ('SSE41', dict(val='-msse4.1')),
            ('SSE42', dict(val='-msse4.2')),
            ('FMA3', dict(val='-march=core-avx2', match='.*m[sse|avx].*')),
            ('AVX2', dict(val='-march=core-avx2', match='.*m[sse|avx].*')),
            ('AVX512_COMMON', dict(
                val='-march=common-avx512', match='.*m[sse|avx|arch\=].*'
            )),
            ('AVX512_KNL', dict(
                val='-xKNL', match=filter_all
            )),
            ('AVX512_KNM', dict(
                val='-xKNM', match=filter_all
            )),
            ('AVX512_SKX', dict(
                val='-xSKYLAKE-AVX512', match=filter_all
            )),
            ('AVX512_CLX', dict(
                val='-xCASCADELAKE', match=filter_all
            )),
            ('AVX512_CNL', dict(
                val='-xCANNONLAKE', match=filter_all
            )),
            ('AVX512_ICL', dict(
                val='-xICELAKE-CLIENT', match=filter_all
            )),
        ):
            features[fet].update_method(state, [], {'args': arg})
    elif 'msvc' in cid:
        # SSE3, SSSE3, SSE41, POPCNT, SSE42, F16C, XOP and FMA4
        # don't own private FLAGS still MS's compiler provides
        # ABI capability for them.
        for fet, arg in (
            ('SSE', dict(val='/arch:SSE')),
            ('SSE2', dict(val='/arch:SSE2', match='/arch:.*')),
            ('AVX', dict(val='/arch:AVX', match='/arch:.*')),
            ('AVX2', dict(val='/arch:AVX2', match='/arch:.*')),
            ('FMA3', dict(val='/arch:AVX2', match='/arch:.*')),
            ('AVX512_COMMON', dict(val='/arch:AVX512', match='/arch:.*')),
            ('AVX512_SKX', dict(val='/arch:AVX512', match='/arch:.*')),
        ):
            features[fet].update_method(state, [], {'args': arg})
        # MSVC special headers
        for fet, header in (
            ('POPCNT', 'nmmintrin.h'),
            ('XOP', 'ammintrin.h'),
            ('FMA4', 'ammintrin.h'),
        ):
            features[fet].update_method(state, [], {'headers': header})

        # MSVC doesn't support FMA3 or AVX2 independently
        # same for AVX512_COMMON and AVX512_SKX
        for fet, implies in (
            'FMA3', ('F16C', 'AVX2'),
            'AVX2', ('F16C', 'FMA3'),
            'AVX512_COMMON', ('FMA3', 'AVX2', 'AVX512_SKX'),
        ):
            features[fet].update_method(state, [], {
                'implies': [features[sub_fet] for sub_fet in implies]
            })
        for dis_fet in ('AVX512_KNL', 'AVX512_KNM'):
            features[dis_fet].update_method(state, [], {
                'disable': 'MSVC compiler does not support it'
            })
    # unix-like (gcc, clang)
    else:
        for fet in (
            'SSE', 'SSE2', 'SSE3', 'SSSE3', 'POPCNT',
            'AVX', 'F16C', 'XOP', 'FMA4', 'AVX2'
        ):
            features[fet].update_method(state, [], {
                'args': '-m' + fet.lower()
            })

        for fet, args in (
            ('SSE41', '-msse4.1'),
            ('SSE42', '-msse4.2'),
            ('FMA3', '-mfma'),
            # should we add "-mno-mmx"?
            ('AVX512_COMMON', '-mavx512f -mavx512cd'),
            ('AVX512_KNL', '-mavx512er -mavx512pf'),
            ('AVX512_KNM', '-mavx5124fmaps -mavx5124vnniw -mavx512vpopcntdq'),
            ('AVX512_SKX', '-mavx512vl -mavx512bw -mavx512dq'),
            ('AVX512_CLX', '-mavx512vnni'),
            ('AVX512_CNL', '-mavx512ifma -mavx512vbmi'),
            ('AVX512_ICL', '-mavx512vbmi2 -mavx512bitalg -mavx512vpopcntdq')
        ):
            features[fet].update_method(state, [], {
                'args': args.split()
            })

        for fet in (
            'SSE', 'SSE2', 'SSE3', 'SSSE3', 'POPCNT',
            'AVX', 'F16C', 'XOP', 'FMA4', 'AVX2'
        ):
            features[fet].update_method(state, [], {
                'args': '-m' + fet.lower()
            })

def x86_features(state: 'ModuleState', compiler: 'Compiler'
                 ) -> T.Dict[str, FeatureObject]:
    features: T.Dict[str, FeatureObject] = _init_features(state)
    _features_args(state, compiler, features)
    return features
