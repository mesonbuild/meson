! minimal BLAS test
program AHH

implicit none
integer :: n, incx, xs
real :: multval
integer :: x(4)
external sccal

! A very simple test case, scalar x vector
n = 4
multval = 3.0
incx = 1
x = [1, 2, 3, 4]

call sscal(n, multval, x, incx)

xs = int(sum(x))

if (xs == 30) then
    print '("OK: BLAS sum of scaled 1-D array = ",i2)', xs
else
    print '("NOK: BLAS sum of scaled 1-D array = ",i2)', xs
end if
end
