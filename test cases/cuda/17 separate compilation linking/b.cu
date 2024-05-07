#include "b.h"

__device__ int g[N];

__device__ void bar(void) { g[threadIdx.x]++; }
