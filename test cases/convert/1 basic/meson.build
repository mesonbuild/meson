project('basic-convert', 'c')

inc = include_directories('include')

commonlib = static_library('commonlib', 'common.c', include_directories: inc)

shared_library('simplelib', 'main.c',
  include_directories: inc,
  link_with: commonlib
)

subdir('subdir2')
subdir('subdir1')
subdir('subdir3')
