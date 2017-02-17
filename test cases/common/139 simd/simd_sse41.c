#include<simdconfig.h>
#include<simdfuncs.h>

#include<smmintrin.h>
#include<cpuid.h>
#include<stdint.h>

int sse41_available() {
    return __builtin_cpu_supports("sse4.1");
}

void increment_sse41(float arr[4]) {
    double darr[4];
    __m128d val1 = _mm_set_pd(arr[0], arr[1]);
    __m128d val2 = _mm_set_pd(arr[2], arr[3]);
    __m128d one = _mm_set_pd1(1.0);
    __m128d result = _mm_add_pd(val1, one);
    result = _mm_ceil_pd(result); /* A no-op, only here to use a SSE4.1 intrinsic. */
    _mm_store_pd(darr, result);
    result = _mm_add_pd(val2, one);
    _mm_store_pd(&darr[2], result);
    arr[0] = (float)darr[1];
    arr[1] = (float)darr[0];
    arr[2] = (float)darr[3];
    arr[3] = (float)darr[2];
}
