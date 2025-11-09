project('importstd', 'cpp', default_options: {'cpp_importstd': 'true', 
                                              'cpp_std': 'c++23'})

cpp = meson.get_compiler('cpp')

if cpp.get_id() == 'gcc' and cpp.version().version_compare('>=15.1')
  istd_supported = true
else
  istd_supported = false
endif

if istd_supported
  useistd = executable('useistd', 'useistd.cpp')
  test('useistd', useistd)

else
  message('Compiler not yet supported, import std test not run.')
endif
