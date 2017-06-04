project('mpi', 'c', 'cpp')

mpic = dependency('mpi', language : 'c')
exec = executable('exec',
  'main.c',
  dependencies : [mpic])

test('MPI C', exec)

mpicpp = dependency('mpi', language : 'cpp')
execpp = executable('execpp',
  'main.cpp',
  dependencies : [mpicpp])

test('MPI C++', execpp)

if add_languages('fortran', required : false)
  mpifort = dependency('mpi', language : 'fortran')
  exef = executable('exef',
    'main.f90',
    dependencies : [mpifort])

  test('MPI Fortran', exef)
endif
