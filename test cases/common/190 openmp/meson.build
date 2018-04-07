project('openmp', 'c', 'cpp')

openmp = dependency('openmp')

exec = executable('exec',
  'main.c',
  dependencies : [openmp])

execpp = executable('execpp',
  'main.cpp',
  dependencies : [openmp])

env = environment()
env.set('OMP_NUM_THREADS', '2')

test('OpenMP C', exec, env : env)
test('OpenMP C++', execpp, env : env)


if add_languages('fortran', required : false)
  exef = executable('exef',
    'main.f90',
    dependencies : [openmp])

  test('OpenMP Fortran', execpp, env : env)
endif
