#include <omp.h>
#include <iostream>

int main(void) {
#ifdef _OPENMP
    if (omp_get_max_threads() == 2) {
        return EXIT_SUCCESS;
    } else {
        std::cerr << "Max threads is " << omp_get_max_threads() << " not 2." << std::endl;
        return EXIT_FAILURE;
    }
#else
    std::cerr << "_OPENMP is not defined; is OpenMP compilation working?" << std::endl;
    return EXIT_FAILURE;
#endif
}