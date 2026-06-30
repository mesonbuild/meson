project('basic-convert',
        ['c', 'cpp', 'rust'],
        license : 'MIT',
        meson_version : '>= 1.4.0',
        default_options : [
          'buildtype=debugoptimized',
          'b_ndebug=if-release',
          'c_std=c11',
          'cpp_std=c++17',
          'rust_std=2021',
          'build.rust_std=2021',
        ],
)


inc = include_directories('include')

commonlib = static_library('commonlib', 'common.c', include_directories: inc)

shared_library('simplelib', 'main.c',
  include_directories: inc,
  link_with: commonlib
)

subdir('subdir2')
subdir('subdir1')
subdir('subdir3')
subdir('subdir4')
subdir('subdir5')
