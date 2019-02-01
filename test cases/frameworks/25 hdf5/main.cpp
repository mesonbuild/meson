#include <iostream>
#include "hdf5.h"


int main(void)
{
herr_t ier;
unsigned maj, min, rel;

ier = H5open();
if (ier) {
    std::cerr << "Unable to initialize HDF5: " << ier << std::endl;
    return EXIT_FAILURE;
}

ier = H5get_libversion(&maj, &min, &rel);
if (ier) {
    std::cerr << "HDF5 did not initialize!" << std::endl;
    return EXIT_FAILURE;
}
std::cout << "C++ HDF5 version " << maj << "." << min << "." << rel << std::endl;

ier = H5close();
if (ier) {
    std::cerr << "Unable to close HDF5: " << ier << std::endl;
    return EXIT_FAILURE;
}
return EXIT_SUCCESS;
}
