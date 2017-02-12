#include<simdconfig.h>
#include<simdfuncs.h>

#include<xmmintrin.h>
#include<cpuid.h>
#include<stdint.h>

int sse_available() {
    return __builtin_cpu_supports("sse");
}

void increment_sse(float arr[4]) {
    __m128 val = _mm_load_ps(arr);
    __m128 one = _mm_set_ps1(1.0);
    __m128 result = _mm_add_ps(val, one);
    _mm_storeu_ps(arr, result);
}
