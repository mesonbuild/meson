#include <mpi.h>
#include <iostream>

int main(int argc, char **argv)
{
    MPI::Init(argc, argv);
    if (!MPI::Is_initialized()) {
        std::cerr << "MPI did not initialize!\n";
        return 1;
    }
    MPI::Finalize();
}
