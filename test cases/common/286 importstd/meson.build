project('importstd', 'cpp', default_options: {'cpp_importstd': 'true', 
                                              'cpp_std': 'c++latest,c++23,c++20'})

cpp = meson.get_compiler('cpp')

if cpp.get_id() == 'gcc' and cpp.version().version_compare('>=15.1')
  istd_supported = true
elif cpp.get_id() == 'msvc' and cpp.version().version_compare('>=19.44.35219')
  istd_supported = get_option('backend') == 'ninja'
else
  istd_supported = false
endif

if istd_supported
  useistd = executable('useistd', 'useistd.cpp')
  test('useistd', useistd)

else
  message('Compiler not yet supported, import std test not run.')
endif
