## Addition of OpenMP dependency

An OpenMP dependency (`openmp`) has been added that encapsulates the various
flags used by compilers to enable OpenMP and checks for the existence of the
`omp.h` header. The `language` keyword may be passed to force the use of a
specific compiler for the checks.
