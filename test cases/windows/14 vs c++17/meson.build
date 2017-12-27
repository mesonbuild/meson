project('wincpp', 'cpp')

if meson.get_compiler('cpp').version().version_compare('<19.11')
    error('MESON_SKIP_TEST Visual Studio 2017 (version 15.3) or later is required for C++17 support')
endif

exe = executable('prog', 'main.cpp', override_options: ['cpp_std=c++17'])
test('wincpp', exe)
