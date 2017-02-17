#include<simdfuncs.h>
#include<stdio.h>

/*
 * A function that checks at runtime which simd accelerations are
 * available and calls the best one. Falls
 * back to plain C implementation if SIMD is not available.
 */

int main(int argc, char **argv) {
    float four[4] = {2.0, 3.0, 4.0, 5.0};
    const float expected[4] = {3.0, 4.0, 5.0, 6.0};
    void (*fptr)(float[4]) = NULL;
    const char *type;
    int i;

/* Add here. The first matched one is used so put "better" instruction
 * sets at the top.
 */
#if HAVE_NEON
    if(fptr == NULL && neon_available()) {
        fptr = increment_neon;
        type = "NEON";
    }
#endif
#if HAVE_AVX2
    if(fptr == NULL && avx2_available()) {
        fptr = increment_avx2;
        type = "AVX2";
    }
#endif
#if HAVE_AVX
    if(fptr == NULL && avx_available()) {
        fptr = increment_avx;
        type = "AVX";
    }
#endif
#if HAVE_SSE42
    if(fptr == NULL && sse42_available()) {
        fptr = increment_sse42;
        type = "SSE42";
    }
#endif
#if HAVE_SSE41
    if(fptr == NULL && sse41_available()) {
        fptr = increment_sse41;
        type = "SSE41";
    }
#endif
#if HAVE_SSSE3
    if(fptr == NULL && ssse3_available()) {
        fptr = increment_ssse3;
        type = "SSSE3";
    }
#endif
#if HAVE_SSE3
    if(fptr == NULL && sse3_available()) {
        fptr = increment_sse3;
        type = "SSE3";
    }
#endif
#if HAVE_SSE2
    if(fptr == NULL && sse2_available()) {
        fptr = increment_sse2;
        type = "SSE2";
    }
#endif
#if HAVE_SSE
    if(fptr == NULL && sse_available()) {
        fptr = increment_sse;
        type = "SSE";
    }
#endif
#if HAVE_MMX
    if(fptr == NULL && mmx_available()) {
        fptr = increment_mmx;
        type = "MMX";
    }
#endif
    if(fptr == NULL) {
        fptr = increment_fallback;
        type = "fallback";
    }
    printf("Using %s.\n", type);
    fptr(four);
    for(i=0; i<4; i++) {
        if(four[i] != expected[i]) {
            printf("Increment function failed, got %f expected %f.\n", four[i], expected[i]);
            return 1;
        }
    }
    return 0;
}
