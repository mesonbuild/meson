project('C++ and FORTRAN', 'cpp', 'fortran')

fc = meson.get_compiler('fortran')
link_with = []
if fc.get_id() == 'intel'
  link_with += fc.find_library('ifport')
endif

e = executable(
  'cppfort',
  ['main.cpp', 'fortran.f90'],
  dependencies : link_with,
)

test('C++ FORTRAN', e)
