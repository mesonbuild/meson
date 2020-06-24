program main
use, intrinsic :: iso_fortran_env, only: stderr=>error_unit
use mpi

implicit none

logical :: flag
integer :: ier

call MPI_Init(ier)

if (ier /= 0) then
  write(stderr,*) 'Unable to initialize MPI', ier
  error stop
endif

call MPI_Initialized(flag, ier)
if (ier /= 0) then
  write(stderr,*) 'Unable to check MPI initialization state: ', ier
  error stop
endif

if (.not.flag) error stop "MPI did not initialize!"

call MPI_Finalize(ier)
if (ier /= 0) then
  write(stderr,*) 'Unable to finalize MPI: ', ier
  error stop
endif

print *, "OK: Fortran MPI"

end program
