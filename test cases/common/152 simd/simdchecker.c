#include<simdfuncs.h>
#include<stdalign.h>
#include<stdio.h>
#include<string.h>

/*
 * A function that checks at runtime which simd accelerations are
 * available and calls the best one. Falls
 * back to plain C implementation if SIMD is not available.
 */

int main(int argc, char **argv) {
    static const float four_initial[4] = {2.0, 3.0, 4.0, 5.0};
    alignas(16) float four[4];
    const float expected[4] = {3.0, 4.0, 5.0, 6.0};
    void (*fptr)(float[4]) = NULL;
    const char *type;
    int i, r=0;

/* Add here. The first matched one is used so put "better" instruction
 * sets at the top.
 */
#if HAVE_NEON
    if(neon_available()) {
        fptr = increment_neon;
        type = "NEON";
    #include<simdtest.h>
    }
#endif
#if HAVE_AVX2
    if(avx2_available()) {
        fptr = increment_avx2;
        type = "AVX2";
    #include<simdtest.h>
    }
#endif
#if HAVE_AVX
    if(avx_available()) {
        fptr = increment_avx;
        type = "AVX";
    #include<simdtest.h>
    }
#endif
#if HAVE_SSE42
    if(sse42_available()) {
        fptr = increment_sse42;
        type = "SSE42";
    #include<simdtest.h>
    }
#endif
#if HAVE_SSE41
    if(sse41_available()) {
        fptr = increment_sse41;
        type = "SSE41";
    #include<simdtest.h>
    }
#endif
#if HAVE_SSSE3
    if(ssse3_available()) {
        fptr = increment_ssse3;
        type = "SSSE3";
    #include<simdtest.h>
    }
#endif
#if HAVE_SSE3
    if(sse3_available()) {
        fptr = increment_sse3;
        type = "SSE3";
    #include<simdtest.h>
    }
#endif
#if HAVE_SSE2
    if(sse2_available()) {
        fptr = increment_sse2;
        type = "SSE2";
    #include<simdtest.h>
    }
#endif
#if HAVE_SSE
    if(sse_available()) {
        fptr = increment_sse;
        type = "SSE";
    #include<simdtest.h>
    }
#endif
#if HAVE_MMX
    if(mmx_available()) {
        fptr = increment_mmx;
        type = "MMX";
    #include<simdtest.h>
    }
#endif
    fptr = increment_fallback;
    type = "fallback";
    #include<simdtest.h>

    return r;
}
