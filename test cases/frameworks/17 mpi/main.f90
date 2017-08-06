program mpitest
  implicit none
  include 'mpif.h'
  logical :: flag
  integer :: ier
  call MPI_Init(ier)
  if (ier /= 0) then
    print *, 'Unable to initialize MPI: ', ier
    stop 1
  endif
  call MPI_Initialized(flag, ier)
  if (ier /= 0) then
    print *, 'Unable to check MPI initialization state: ', ier
    stop 1
  endif
  call MPI_Finalize(ier)
  if (ier /= 0) then
    print *, 'Unable to finalize MPI: ', ier
    stop 1
  endif
end program mpitest
