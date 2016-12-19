project('simple fortran', 'fortran')

add_global_arguments('-fbounds-check', language : 'fortran')

e = executable('simple', 'simple.f95',
  fortran_args : '-ffree-form')
test('Simple Fortran', e)
