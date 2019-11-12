## `fortran_std` option

**new in 0.53.0**
Akin to the `c_std` and `cpp_std` options, the `fortran_std` option sets Fortran compilers to warn or error on non-Fortran standard code.
Only the Gfortran and Intel Fortran compilers have support for this option.
Other Fortran compilers ignore the `fortran_std` option.

Supported values for `fortran_std` include:

* `legacy` for non-conforming code--this is especially important for Gfortran, which by default errors on old non-compliant Fortran code
* `f95` for Fortran 95 compliant code.
* `f2003` for Fortran 2003 compliant code.
* `f2008` for Fortran 2008 compliant code.
* `f2018` for Fortran 2018 compliant code.