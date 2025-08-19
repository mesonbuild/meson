#include <cuda_runtime.h>
#include <cublas_v2.h>
#include <cupti.h>
#include <cupti_checkpoint.h>
#include <cupti_pcsampling_util.h>
#include <iostream>

void do_cuda_stuff(void);

int cuda_devices(void) {
    int result = 0;
    cudaGetDeviceCount(&result);
    return result;
}

int main(void) {
    // known-error calls to ensure the library is loaded/linked
    (void)::CUPTI::PcSamplingUtil::CuptiUtilGetHeaderData(nullptr);
    (void)::NV::Cupti::Checkpoint::cuptiCheckpointFree(nullptr);

    int n = cuda_devices();
    if (n == 0) {
        std::cout << "No CUDA hardware found. Exiting.\n";
        return 0;
    }

    std::cout << "Found " << n << " CUDA devices.\n";

    do_cuda_stuff();

    uint32_t version;
    if (cuptiGetVersion(&version) != CUPTI_SUCCESS) {
        std::cout << "CUPTI version query failed. Exiting.\n";
        return -1;
    }

    cublasHandle_t handle;
    if (cublasCreate(&handle) != CUBLAS_STATUS_SUCCESS) {
        std::cout << "cuBLAS initialization failed. Exiting.\n";
        return -1;
    }

    std::cout << "Initialized cuBLAS\n";
    if (cublasDestroy(handle) != CUBLAS_STATUS_SUCCESS) {
        std::cout << "cuBLAS de-initialization failed. Exiting.\n";
        return -1;
    }

    return 0;
}
