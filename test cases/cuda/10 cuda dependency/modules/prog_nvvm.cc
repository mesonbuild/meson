#include <nvvm.h>
#include <iostream>

int main(void) {
    int versionMajor, versionMinor;
    if (nvvmVersion(&versionMajor, &versionMinor) != NVVM_SUCCESS) {
        std::cout << "NVVM version query failed. Exiting.\n";
        return -1;
    }

    return 0;
}
