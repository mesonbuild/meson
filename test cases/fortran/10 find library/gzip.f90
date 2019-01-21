module gzip

  use iso_c_binding, only: c_char, c_ptr, c_int
  implicit none

  interface
     function gzopen(path, mode) bind(C)
       import c_char, c_ptr

       character(c_char), intent(in) :: path(*), mode(*)
       type(c_ptr) :: gzopen
     end function gzopen
  end interface

  interface
     function gzwrite(file, buf, len) bind(C)
       import c_int, c_ptr

       type(c_ptr), value, intent(in) :: file
       type(*), intent(in) :: buf
       integer(c_int), value, intent(in) :: len
       integer(c_int) :: gzwrite
     end function gzwrite
  end interface

  interface
     function gzclose(file) bind(C)
       import c_int, c_ptr

       type(c_ptr), value, intent(in) :: file
       integer(c_int) :: gzclose
     end function gzclose
  end interface

end module gzip
