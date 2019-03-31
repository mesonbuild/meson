project('lapack_test', 'c', 'cpp')

cc = meson.get_compiler('c')
ccid = cc.get_id()

# --- C tests
lapack_c = dependency('lapack', required : false)
if not lapack_c.found()
  error('MESON_SKIP_TEST: LAPACK C library not found, skipping tests.')
endif
exec = executable('exec', 'main.c', dependencies : lapack_c)

test('LAPACK C', exec)

# --- C++ tests
lapack_cpp = dependency('lapack', required : false)
if lapack_cpp.found()
  execpp = executable('execpp', 'main.cpp', dependencies : lapack_cpp)
  test('LAPACK C++', execpp)
endif

# --- Fortran tests
if ccid != 'msvc' and ccid != 'clang-cl'
  add_languages('fortran')

  lapack_f = dependency('lapack', required : false)
  if lapack_f.found()
    exef = executable('exef', 'main.f90', dependencies : lapack_f)

    test('LAPACK Fortran', exef)
  endif
endif

# Check we can apply a version constraint
if lapack_c.version() != 'unknown'
  dependency('lapack', version: '>=@0@'.format(lapack_c.version()))
endif
