implicit none

integer :: x, y

x = 1
y = 0

! include "timestwo.f90"

!$ include "non-existentFile"
! this is not an OpenMP project, so this !$ include should be ignored else configuration error

! double quote and inline comment check
include "timestwo.f90"  ! inline comment check
if (x/=2) error stop 'failed on first include'

! leading space and single quote check
  include 'timestwo.f90'
if (x/=4) error stop 'failed on second include'

! Most Fortran compilers can't handle the non-standard #include,
! including Flang, Gfortran, Ifort and PGI.
! #include "timestwo.f90"

print *, 'OK: Fortran include tests: x=',x

end program