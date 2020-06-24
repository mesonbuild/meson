#include <stdio.h>
#include <mpi.h>

int main(int argc, char **argv)
{
    int ier, flag;
    ier = MPI_Init(&argc, &argv);
    if (ier) {
        fprintf(stderr, "Unable to initialize MPI: %d\n", ier);
        return 1;
    }
    ier = MPI_Initialized(&flag);
    if (ier) {
        fprintf(stderr, "Unable to check MPI initialization state: %d\n", ier);
        return 1;
    }
    if (!flag) {
        fprintf(stderr, "MPI did not initialize!\n");
        return 1;
    }
    ier = MPI_Finalize();
    if (ier) {
        fprintf(stderr, "Unable to finalize MPI: %d\n", ier);
        return 1;
    }
    return 0;
}
