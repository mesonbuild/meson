#include <iostream>
#include "hdf5.h"


int main(void)
{
herr_t ier;
unsigned maj;
unsigned min;
unsigned rel;

ier = H5open();
if (ier) {
    std::cerr << "Unable to initialize HDF5: %d" << ier << std::endl;
    return EXIT_FAILURE;
}

ier = H5get_libversion(&maj, &min, &rel);
if (ier) {
    std::cerr << "HDF5 did not initialize!" << std::endl;
    return EXIT_FAILURE;
}
printf("C++ HDF5 version %d.%d.%d\n", maj, min, rel);

ier = H5close();
if (ier) {
    std::cerr << "Unable to close HDF5: %d"  << ier << std::endl;
    return EXIT_FAILURE;
}
return EXIT_SUCCESS;
}
