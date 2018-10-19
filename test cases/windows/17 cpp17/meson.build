project('msvc_cpp17', 'cpp', default_options: ['cpp_std=c++17'])

compiler = meson.get_compiler('cpp')
if compiler.get_id() != 'msvc' or compiler.version().version_compare('<19.11')
    error('MESON_SKIP_TEST Visual Studio 2017 (version 15.3) or later is required for C++17 support')
endif

exe = executable('msvc_cpp17', 'main.cpp')
test('msvc_cpp17', exe)
