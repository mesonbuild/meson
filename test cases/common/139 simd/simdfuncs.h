#pragma once

#include<simdconfig.h>

/* Yes, I do know that arr[4] decays into a pointer
 * here. Don't do this in real code but for test code
 * it is ok.
 */

void increment_fallback(float arr[4]);

#if HAVE_MMX
void increment_mmx(float arr[4]);
#endif

