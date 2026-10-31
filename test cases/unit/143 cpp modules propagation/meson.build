project('cppmodules propagation', 'cpp', default_options: ['cpp_std=c++20'])

# No module argument anywhere: the interface units of the library are recognized
# by their extension, and the executable is scanned because it links with the library.
lib = static_library(
    'lib',
    'lib.ixx',
    'lib_detail.ixx',
)

e = executable(
    'modtest',
    'main.cpp',
    link_with: lib,
)

test('modtest', e)
