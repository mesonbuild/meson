project('CMake Components', 'c')

# -- OpenMP via CMake components
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
if cc.get_id() == 'clang-cl'
  error('MESON_SKIP_TEST clang-cl does not support OpenMP.')
endif
if cc.get_id() == 'clang' and host_machine.system() == 'windows'
  error('MESON_SKIP_TEST Windows clang does not support OpenMP.')
endif
if host_machine.system() == 'darwin'
  error('MESON_SKIP_TEST macOS does not support OpenMP.')
endif

env = environment()
env.set('OMP_NUM_THREADS', '2')

omp_c = dependency('openmp', language: 'c', method: 'cmake')
exe_c = executable('openmp_c', 'main.c', dependencies: omp_c)
test('OpenMP_C', exe_c, env: env, timeout: 10)

if add_languages('cpp', required: false)
  omp_cpp = dependency('openmp', language: 'cpp', method: 'cmake')
  exe_cpp = executable('openmp_cpp', 'main.cpp', dependencies: omp_cpp)
  test('OpenMP_C++', exe_cpp, env: env, timeout: 10)
endif

if add_languages('fortran', required: false)
  omp_f = dependency('openmp', language: 'fortran', method: 'cmake')
  exe_f = executable('openmp_f', 'main.f90', dependencies: omp_f)
  test('OpenMP_Fortran', exe_f, env: env, timeout: 10)
endif