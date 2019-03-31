module demo_svd
use, intrinsic :: iso_fortran_env, only: stderr=>error_unit, sp=>real32
implicit none

integer, parameter :: LRATIO=8
integer, parameter :: M=2, N=2

integer, parameter :: Lwork = LRATIO*M !at least 5M for sgesvd

real(sp) :: U(M,M), VT(N,N), errmag(N)
real(sp) :: S(N), truthS(N), SWORK(LRATIO*M) !this Swork is real

contains

subroutine errchk(info)

integer, intent(in) :: info

if (info /= 0) then
  write(stderr,*) 'SGESVD return code', info
  if (info > 0) write(stderr,'(A,I3,A)') 'index #',info,' has sigma=0'
  stop 1
endif

end subroutine errchk

end module demo_svd


program demo
use demo_svd
implicit none

integer :: info
real(sp) :: A(M, N)

A = reshape([1., 1./2, &
             1./2, 1./3], shape(A), order=[2,1])

truthS = [1.267592, 0.065741]

call sgesvd('A','N',M,N, A, M,S,U,M,VT, N, SWORK, LWORK, info)

errmag = abs(s-truthS)
if (any(errmag > 1e-3)) then
  print *,'estimated singular values: ',S
  print *,'true singular values: ',truthS
  write(stderr,*) 'large error on singular values', errmag
  stop 1
endif

call errchk(info)

print *,'OK: Fortran SVD'

end program
