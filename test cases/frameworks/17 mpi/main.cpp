#include <mpi.h>
#include <iostream>

int main(int argc, char **argv)
{
    int L;

    char version[MPI_MAX_LIBRARY_VERSION_STRING];
    MPI_Get_library_version(version, &L);
    std::cout << version << std::endl;

    MPI::Init(argc, argv);
    if (!MPI::Is_initialized()) {
        std::cerr << "MPI did not initialize!" << std::endl;
        return 1;
    }
    MPI::Finalize();
}
