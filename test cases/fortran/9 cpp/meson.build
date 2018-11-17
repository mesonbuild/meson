project('C++ and FORTRAN', 'cpp', 'fortran')

cpp = meson.get_compiler('cpp')

if cpp.get_id() == 'clang'
  error('MESON_SKIP_TEST Clang C++ does not find -lgfortran for some reason.')
endif

fc = meson.get_compiler('fortran')
link_with = []
if fc.get_id() == 'intel'
  link_with += fc.find_library('ifport')
endif

e = executable(
  'cppfort',
  ['main.cpp', 'fortran.f'],
  dependencies : [link_with],
)

test('C++ FORTRAN', e)
