project('Fortran coarray', 'fortran')

coarray = dependency('Coarray', required : false)

exe = executable('hello', 'main.f90',
  dependencies : coarray)

test('Coarray hello world', exe)

