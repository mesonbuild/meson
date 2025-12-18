project(
  'nested folders',
  ['c', 'cpp', 'cython'],
  default_options : ['buildtype=release'],
)

if meson.backend() != 'ninja'
  error('MESON_SKIP_TEST: Ninja backend required')
endif

py = import('python').find_installation(pure: false, required: true)

metric = py.extension_module(
  'metric',
  'package/metrics/metric.pyx',
  subdir: 'package/metrics',
  install: true
)

subdir('package')
