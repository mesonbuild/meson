#pragma once

#include<simdconfig.h>

/* Yes, I do know that arr[4] decays into a pointer
 * as a function argument. Don't do this in real code
 * but for this test it is ok.
 */

void increment_fallback(float arr[4]);

#if HAVE_MMX
int mmx_available();
void increment_mmx(float arr[4]);
#endif

#if HAVE_SSE
int sse_available();
void increment_sse(float arr[4]);
#endif

#if HAVE_SSE2
int sse2_available();
void increment_sse2(float arr[4]);
#endif

#if HAVE_SSE3
int sse3_available();
void increment_sse3(float arr[4]);
#endif

#if HAVE_SSSE3
int ssse3_available();
void increment_ssse3(float arr[4]);
#endif

#if HAVE_SSE41
int sse41_available();
void increment_sse41(float arr[4]);
#endif

#if HAVE_SSE42
int sse42_available();
void increment_sse42(float arr[4]);
#endif

#if HAVE_AVX
int avx_available();
void increment_avx(float arr[4]);
#endif

#if HAVE_AVX2
int avx2_available();
void increment_avx2(float arr[4]);
#endif

#if HAVE_NEON
int neon_available();
void increment_neon(float arr[4]);
#endif

#if HAVE_ALTIVEC
int altivec_available();
void increment_altivec(float arr[4]);
#endif

/* And so on. */
