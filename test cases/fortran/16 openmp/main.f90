 module Amod
use, intrinsic :: iso_fortran_env, only : stderr=>error_unit
interface
module subroutine print_thread_count(N)
integer, intent(in) :: N
end subroutine print_thread_count
end interface
contains
!$ include "mpstuff.f90"
end module Amod

submodule (Amod) Bfoo
contains
module procedure print_thread_count
print '(A,I3,A)', 'You have', N, ' threads.'
end procedure print_thread_count
end submodule Bfoo

program mpdemo

use, intrinsic :: iso_fortran_env, only: stderr=>error_unit
!$ use Amod, only : print_thread_count, print_result
use omp_lib, only: omp_get_max_threads
implicit none

integer :: N, ierr
character(80) :: buf  ! can't be allocatable even through Fortran 2018. Just set arbitrarily large.

call get_environment_variable('OMP_NUM_THREADS', buf, status=ierr)
if (ierr/=0) error stop 'environment variable OMP_NUM_THREADS could not be read'
read(buf,*) N

call print_thread_count(N)
call print_result(N)

if (omp_get_max_threads() /= N) then
  write(stderr, *) 'Max Fortran threads: ', omp_get_max_threads(), '!=', N
  error stop
endif

end program
