program prog
  use mod2
  implicit none

  if (modval1 + modval2 /= 3) then
    stop 1
  end if

end program prog
