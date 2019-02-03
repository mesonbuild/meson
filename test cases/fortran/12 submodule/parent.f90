module mother
real, parameter :: pi = 4.*atan(1.)
real :: tau

interface
module elemental real function pi2tau(pi)
  real, intent(in) :: pi
end function pi2tau
end interface

contains 

end module mother


program hier1
use mother

tau = pi2tau(pi)

print *,'pi=',pi, 'tau=', tau

end program
