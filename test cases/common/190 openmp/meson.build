project('openmp', 'c', 'cpp')

cc = meson.get_compiler('c')
if cc.get_id() == 'gcc' and cc.version().version_compare('<4.2.0')
  error('MESON_SKIP_TEST gcc is too old to support OpenMP.')
endif
if cc.get_id() == 'clang' and cc.version().version_compare('<3.7.0')
  error('MESON_SKIP_TEST clang is too old to support OpenMP.')
endif
if cc.get_id() == 'msvc' and cc.version().version_compare('<17')
  error('MESON_SKIP_TEST msvc is too old to support OpenMP.')
endif
if host_machine.system() == 'darwin'
  error('MESON_SKIP_TEST macOS does not support OpenMP.')
endif

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
