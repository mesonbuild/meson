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
#endif

#if HAVE_SSE2
#endif

/* And so on. */
