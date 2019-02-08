project('Fortran coarray', 'fortran')

# coarray is required because single-image fallback is an intrinsic feature
coarray = dependency('coarray', required : true)

exe = executable('hello', 'main.f90',
  dependencies : coarray)

test('Coarray hello world', exe)

