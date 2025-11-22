project('importstd', 'cpp', default_options: {'cpp_importstd': 'true',
                                              'cpp_std': 'c++latest,c++23,c++20'})

cpp = meson.get_compiler('cpp')

cpp_id = cpp.get_id()
cpp_version = cpp.version()

if cpp_id == 'gcc' and cpp_version.version_compare('>=15.1')
  if host_machine.system() == 'windows'
    istd_supported = cpp_version.version_compare('>=15.3')
  else
    if cpp_version.version_compare('=15.2.0') or cpp_version.version_compare('>=15.3.0')
      istd_supported = true
    else
      istd_supported = false
    endif
  endif
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
