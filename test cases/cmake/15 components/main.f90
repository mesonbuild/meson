use, intrinsic :: iso_fortran_env, only: stderr=>error_unit
use omp_lib
implicit none

if (omp_get_max_threads() /= 2) then
  write(stderr, *) 'Max Fortran threads is', omp_get_max_threads(), 'not 2.'
  error stop
endif

end program