project('cmake nasm dependency', ['c', 'cpp'])

if get_option('backend').startswith('vs')
  error('MESON_SKIP_TEST: nasm is not supported by vs backend')
endif

# This test aims to trigger CMakeToolchain.update_cmake_compiler_state() _twice_,
# as the 2nd CMake compilers state update resulted in a warning
# "Failed to determine CMake compilers state" after nasm was added as a language.

# First dependency triggers initial compilers state update
sub_dep_1 = dependency('cmTest1')
# Add nasm as a language..
add_languages('nasm', required: true, native: false)
# ...and check for 2nd dependency. Together with cmake_skip_compiler_test = 'always',
# this triggers another CMake compilers state update, this time with nasm
# in the mix
sub_dep_2 = dependency('cmTest2')

exe1 = executable('exe1', ['main.c'], dependencies: [sub_dep_1, sub_dep_2])
test('test1', exe1)
