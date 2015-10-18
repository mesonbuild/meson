project('default options', 'cpp', default_options : [
  'buildtype=debugoptimized',
  'cpp_std=c++03',
  'cpp_eh=none'
  ])

cc = meson.get_compiler('cpp')

assert(get_option('buildtype') == 'debugoptimized', 'Build type default value wrong.')

if cc.get_id() == 'msvc'
  assert(get_option('cpp_eh') == 'none', 'MSVC eh value wrong.')
else
  assert(get_option('cpp_std') == 'c++03', 'C++ std value wrong.')
endif
