module gzip

  interface
     function gzopen(path, mode) bind(C)
       use iso_c_binding, only: c_char, c_ptr
       implicit none
       character(c_char), intent(in) :: path(*), mode(*)
       type(c_ptr) :: gzopen
     end function gzopen
  end interface

  interface
     function gzwrite(file, buf, len) bind(C)
       use iso_c_binding, only: c_int, c_ptr
       implicit none
       type(c_ptr), value, intent(in) :: file
       type(*), intent(in) :: buf
       integer(c_int), value, intent(in) :: len
       integer(c_int) :: gzwrite
     end function gzwrite
  end interface

  interface
     function gzclose(file) bind(C)
       use iso_c_binding, only: c_int, c_ptr
       implicit none
       type(c_ptr), value, intent(in) :: file
       integer(c_int) :: gzclose
     end function gzclose
  end interface

end module gzip
