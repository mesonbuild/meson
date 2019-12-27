subroutine print_result(N)
integer, intent(in) :: N

if (N==2) then
  print *, '2 threads is correct number.'
else
  write(stderr,'(i3,A)') N,' threads is not what this test expected.'
endif

end subroutine print_result
