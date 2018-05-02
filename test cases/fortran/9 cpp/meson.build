project('C++ and FORTRAN', 'cpp', 'fortran')

cpp = meson.get_compiler('cpp')

if cpp.get_id() == 'clang'
  error('MESON_SKIP_TEST Clang C++ does not find -lgfortran for some reason.')
endif

e = executable('cppfort', 'main.cpp', 'fortran.f')
test('C++ FORTRAN', e)
