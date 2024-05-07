#include <stdio.h>

#include "b.h"

__global__ void foo(void)
{
    __shared__ int a[N];
    a[threadIdx.x] = threadIdx.x;

    __syncthreads();

    g[threadIdx.x] = a[blockDim.x - threadIdx.x - 1];

    bar();
}

int main(void)
{
    unsigned int i;
    int *dg, hg[N];
    int sum = 0;

    foo<<<1, N>>>();

    if (cudaGetSymbolAddress((void**)&dg, g)) {
        printf("couldn't get the symbol addr\n");
        return 1;
    }
    if (cudaMemcpy(hg, dg, N * sizeof(int), cudaMemcpyDeviceToHost)) {
        printf("couldn't memcpy\n");
        return 1;
    }

    for (i = 0; i < N; i++) {
        sum += hg[i];
    }
    if (sum == 36) {
        printf("PASSED\n");
    } else {
        printf("FAILED (%d)\n", sum);
    }

    return 0;
}
