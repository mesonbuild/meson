#include <iostream>

#if USEMKL == 1
#include "mkl_lapacke.h"
#elif USEATLAS == 1
#include "cblas.h"
#include "clapack.h"
#else
#include "lapacke.h"
#endif
int main(void) {

    int n, nrhs, lda, ldb, info;
    double *A, *b;
    int *ipiv;

    n = 2; nrhs = 1;


     lda=n, ldb=n;
     A = (double *)malloc(n*n*sizeof(double));
     b = (double *)malloc(n*nrhs*sizeof(double));
     ipiv = (int *)malloc(n*sizeof(int)) ;


     A[0] = 1.;
     A[1] = 0.5;
     A[2] = 0.5;
     A[3] = 1./3.;


#if USEATLAS==1
     info = clapack_dgesv( 102, n, nrhs, A, lda, ipiv, b, ldb );
#else
     info = LAPACKE_dgesv( LAPACK_COL_MAJOR, n, nrhs, A, lda, ipiv, b, ldb );
#endif

     if (info != 0) return EXIT_FAILURE;

     return EXIT_SUCCESS;
}
