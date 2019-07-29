project('Fortran coarray', 'fortran',
  meson_version: '>=0.50')

fc = meson.get_compiler('fortran')
fcid = fc.get_id()

if fcid == 'pgi' or fcid == 'flang'
  error('MESON_SKIP_TEST: At least through: PGI 19.4 and Flang 7.0 do not support Fortran Coarrays.')
endif

# coarray is required because single-image fallback is an intrinsic feature
coarray = dependency('coarray', required : true)

exe = executable('hello', 'main.f90',
  dependencies : coarray)

test('Coarray hello world', exe)

