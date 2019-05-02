project('Fortran calling C', 'fortran', 'c')

ccid = meson.get_compiler('c').get_id()
if ccid == 'msvc' or ccid == 'clang-cl'
  error('MESON_SKIP_TEST: MSVC and GCC do not interoperate like this.')
endif

c_lib = library('clib', 'clib.c')

f_call_c = executable('f_call_c', 'f_call_c.f90',
  link_with: c_lib,
  link_language: 'fortran')
test('Fortran calling C', f_call_c)
