project(
  'nested folders',
  ['c', 'cpp', 'cython'],
  default_options : ['buildtype=release'],
)

if meson.backend() != 'ninja'
  error('MESON_SKIP_TEST: Ninja backend required')
endif

py = import('python').find_installation()
py_dep = py.dependency(required: false)

if not py_dep.found()
  error('MESON_SKIP_TEST: Python library not found.')
endif

metric = py.extension_module(
  'metric',
  'package/metrics/metric.pyx',
  subdir: 'package/metrics',
  install: true
)

subdir('package')
