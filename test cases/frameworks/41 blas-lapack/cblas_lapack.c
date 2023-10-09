// Basic BLAS/LAPACK example adapted from a test in Spack for OpenBLAS

#include "cblas_lapack.h"

int main(void) {
  // CBLAS:
  blas_int n_elem = 9;
  blas_int incx = 1;
  double A[6] = {1.0, 2.0, 1.0, -3.0, 4.0, -1.0};
  double B[6] = {1.0, 2.0, 1.0, -3.0, 4.0, -1.0};
  double C[9] = {.5, .5, .5, .5, .5, .5, .5, .5, .5};
  double norm;

  CBLAS_FUNC(cblas_dgemm)
  (CblasColMajor, CblasNoTrans, CblasTrans, 3, 3, 2, 1, A, 3, B, 3, 2, C, 3);
  norm = CBLAS_FUNC(cblas_dnrm2)(n_elem, C, incx) - 28.017851;

  if (fabs(norm) < 1e-5) {
    printf("OK: CBLAS result using dgemm and dnrm2 as expected\n");
  } else {
    fprintf(stderr, "CBLAS result using dgemm and dnrm2 incorrect: %f\n", norm);
    exit(EXIT_FAILURE);
  }

  // LAPACK:
  double m[] = {3, 1, 3, 1, 5, 9, 2, 6, 5};
  double x[] = {-1, 3, -3};
  lapack_int ipiv[3];
  lapack_int info;
  lapack_int n = 1;
  lapack_int nrhs = 1;
  lapack_int lda = 3;
  lapack_int ldb = 3;

  LAPACK_FUNC(dgesv)(&n, &nrhs, &m[0], &lda, ipiv, &x[0], &ldb, &info);
  n_elem = 3;
  norm = CBLAS_FUNC(cblas_dnrm2)(n_elem, x, incx) - 4.255715;

  if (fabs(norm) < 1e-5) {
    printf("OK: LAPACK result using dgesv as expected\n");
  } else {
    fprintf(stderr, "LAPACK result using dgesv incorrect: %f\n", norm);
    exit(EXIT_FAILURE);
  }

  return 0;
}
