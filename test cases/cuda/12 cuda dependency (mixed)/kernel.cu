#include <cuda_runtime.h>

__global__ void kernel (void){
}

void do_cuda_stuff() {
  kernel<<<1,1>>>();
}
