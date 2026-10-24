project('cppmodules multiple targets', 'cpp', default_options: ['cpp_std=c++20'])

cxx = meson.get_compiler('cpp')
if cxx.get_id() == 'msvc'
    modules_args = ['/interface']
elif cxx.version().version_compare('>=15')
    # The argument which enables modules is -fmodules-ts in GCC 14 and -fmodules in GCC 15
    modules_args = ['-fmodules']
else
    modules_args = ['-fmodules-ts']
endif

lib = static_library(
    'lib',
    'lib.cxx',
    'lib_detail.cxx',
    cpp_args: modules_args,
)

e = executable(
    'modtest',
    'main.cpp',
    link_with: lib,
    cpp_args: modules_args,
)

test('modtest', e)
