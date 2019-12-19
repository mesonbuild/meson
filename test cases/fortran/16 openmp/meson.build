# This test is complementary to "common/190 openmp"
project('openmp', 'fortran')

fc = meson.get_compiler('fortran')
if fc.get_id() == 'gcc' and fc.version().version_compare('<4.2.0')
  error('MESON_SKIP_TEST gcc is too old to support OpenMP.')
endif
if host_machine.system() == 'darwin'
  error('MESON_SKIP_TEST macOS does not support OpenMP.')
endif

openmp = dependency('openmp', language : 'fortran')

env = environment()
env.set('OMP_NUM_THREADS', '2')

exef = executable('exef',
  'main.f90',
  dependencies : [openmp])
test('OpenMP Fortran', exef, env : env, timeout: 10)
