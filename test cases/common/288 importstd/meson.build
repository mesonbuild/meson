project('importstd', 'cpp', default_options: {'cpp_importstd': 'true',
                                              'cpp_std': 'c++latest,c++23,c++20'})

cpp = meson.get_compiler('cpp')

cpp_id = cpp.get_id()
cpp_version = cpp.version()

if cpp_id == 'gcc' and cpp_version.version_compare('>=15.3')
  # Versions between 15.0 and 15.2 are too unreliable to test.
  # The same version number of GCC works in some distros
  # but fails in others.
  istd_supported = true
elif cpp_id == 'msvc' and cpp_version.version_compare('>=19.44.35219')
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
