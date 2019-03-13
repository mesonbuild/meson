project('Fortran calling C', 'fortran', 'c')

c_lib = library('clib', 'clib.c')

f_call_c = executable('f_call_c', 'f_call_c.f90',
  link_with: c_lib,
  link_language: 'fortran')
test('Fortran calling C', f_call_c)
