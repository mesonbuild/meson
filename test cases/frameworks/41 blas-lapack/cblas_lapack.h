// Unified CBLAS and LAPACK header to account for the various name mangling
// schemes used by Accelerate, OpenBLAS, MKL & co. As well as for the names of
// header files varying (e.g. cblas.h, Accelerate/Accelerate.h, mkl_cblas.h)
//
// Accelerate.h (via cblas_new.h) contains non-suffixed names, and the suffixed
// symbols are added via aliases inserted with __asm.
// OpenBLAS headers do contain suffixed names (e.g., `cblas_dgemm64_`)
// The end result after the standardization discussion in
// https://github.com/Reference-LAPACK/lapack/issues/666 should be
// `cblas_dgemm_64`, however that isn't yet final or implemented.
//
// # Actual symbols present in MKL:

//   00000000003e4970 T cblas_dgemm
//   00000000003e4970 T cblas_dgemm_
//   00000000003e34e0 T cblas_dgemm_64
//   00000000003e34e0 T cblas_dgemm_64_
//
//   00000000004e9f80 T dgesv
//   00000000004e9f80 T dgesv_
//   00000000004ea050 T dgesv_64
//   00000000004ea050 T dgesv_64_
//
//
// # Actual symbols present in OpenBLAS (in `libopenblas64`):
//
//   00000000000a3430 T cblas_dgemm64_
//
//   00000000000a6e50 T dgesv_64_

// Name mangling adapted/extended from NumPy's npy_cblas.h
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#ifdef ACCELERATE_NEW_LAPACK
#if __MAC_OS_X_VERSION_MAX_ALLOWED < 130300
#ifdef HAVE_BLAS_ILP64
#error "Accelerate ILP64 support is only available with macOS 13.3 SDK or later"
#endif
#else
#define NO_APPEND_FORTRAN
#ifdef HAVE_BLAS_ILP64
#define BLAS_SYMBOL_SUFFIX $NEWLAPACK$ILP64
#else
#define BLAS_SYMBOL_SUFFIX $NEWLAPACK
#endif
#endif
#endif

#ifdef NO_APPEND_FORTRAN
#define BLAS_FORTRAN_SUFFIX
#else
#define BLAS_FORTRAN_SUFFIX _
#endif

#ifndef BLAS_SYMBOL_SUFFIX
#define BLAS_SYMBOL_SUFFIX
#endif

#define BLAS_FUNC_CONCAT(name, suffix, suffix2) name##suffix##suffix2
#define BLAS_FUNC_EXPAND(name, suffix, suffix2)                                \
  BLAS_FUNC_CONCAT(name, suffix, suffix2)

#define CBLAS_FUNC(name) BLAS_FUNC_EXPAND(name, , BLAS_SYMBOL_SUFFIX)
#ifdef OPENBLAS_ILP64_NAMING_SCHEME
#define BLAS_FUNC(name)                                                        \
  BLAS_FUNC_EXPAND(name, BLAS_FORTRAN_SUFFIX, BLAS_SYMBOL_SUFFIX)
#define LAPACK_FUNC(name) BLAS_FUNC(name)
#else
#define BLAS_FUNC(name)                                                        \
  BLAS_FUNC_EXPAND(name, BLAS_SYMBOL_SUFFIX, BLAS_FORTRAN_SUFFIX)
#define LAPACK_FUNC(name) BLAS_FUNC(name)
#endif

#ifdef HAVE_BLAS_ILP64
#define blas_int long
#define lapack_int long
#else
#define blas_int int
#define lapack_int int
#endif

enum CBLAS_ORDER { CblasRowMajor = 101, CblasColMajor = 102 };
enum CBLAS_TRANSPOSE {
  CblasNoTrans = 111,
  CblasTrans = 112,
  CblasConjTrans = 113
};

#ifdef __cplusplus
extern "C" {
#endif

void CBLAS_FUNC(cblas_dgemm)(const enum CBLAS_ORDER Order,
                             const enum CBLAS_TRANSPOSE TransA,
                             const enum CBLAS_TRANSPOSE TransB,
                             const blas_int M, const blas_int N,
                             const blas_int K, const double alpha,
                             const double *A, const blas_int lda,
                             const double *B, const blas_int ldb,
                             const double beta, double *C, const blas_int ldc);

double CBLAS_FUNC(cblas_dnrm2)(const blas_int N, const double *X,
                               const blas_int incX);

void LAPACK_FUNC(dgesv)(lapack_int *n, lapack_int *nrhs, double *a,
                        lapack_int *lda, lapack_int *ipivot, double *b,
                        lapack_int *ldb, lapack_int *info);

#ifdef __cplusplus
}
#endif
