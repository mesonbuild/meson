project(
  'package',
  'c', 'cpp', 'cython',
  version: '0.1',
  license: 'BSD-3',
  meson_version: '>= 1.1.0',
  default_options: [
    'c_std=c11',
    'cpp_std=c++14',
  ],
)

py = import('python').find_installation(pure: false, required: true)

working = py.extension_module(
  'metric',
  'package/metrics/metric.pyx',
  subdir: 'package/metrics',
  install: true
)

subdir('package')
