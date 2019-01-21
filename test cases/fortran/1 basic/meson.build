project('simple fortran', 'fortran')

fc = meson.get_compiler('fortran')
if fc == 'gcc'
  add_global_arguments('-fbounds-check', language : 'fortran')
endif

e = executable('simple', 'simple.f90',
  fortran_args : '-ffree-form')
test('Simple Fortran', e)
