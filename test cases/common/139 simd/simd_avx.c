#include<simdconfig.h>
#include<simdfuncs.h>

#include<immintrin.h>
#include<cpuid.h>
#include<stdint.h>

int avx_available() {
    return __builtin_cpu_supports("avx");
}

void increment_avx(float arr[4]) {
    double darr[4];
    darr[0] = arr[0];
    darr[1] = arr[1];
    darr[2] = arr[2];
    darr[3] = arr[3];
    __m256d val = _mm256_loadu_pd(darr);
    __m256d one = _mm256_set1_pd(1.0);
    __m256d result = _mm256_add_pd(val, one);
    _mm256_storeu_pd(darr, result);
    arr[0] = (float)darr[0];
    arr[1] = (float)darr[1];
    arr[2] = (float)darr[2];
    arr[3] = (float)darr[3];
}
