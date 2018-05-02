      function fortran() bind(C)
      use, intrinsic :: iso_c_binding
      real(kind=c_double) :: fortran
      fortran = 2.0**rand(1)
      end function fortran
