# SPDX-License-Identifier: Apache-2.0
# Copyright © 2024 Intel Corporation

project(
  'cbindgen',
  'rust', 'c',
  meson_version : '>= 1.12',
  default_options : {'cpp_std' : 'c++20'},
)

if not find_program('cbindgen', required : false).found()
  error('MESON_SKIP_TEST: cbindgen was not found')
endif

rust = import('rust')

rlib = static_library('rlib', 'lib.rs', rust_abi : 'c')

bound_h = rust.cbindgen('lib.rs', 'lib.h', config : 'config.toml')

test(
  'uses bound rust',
  executable('ctest', 'test1.c', bound_h, link_with : rlib)
)

srcs = structured_sources(
  'lib2.rs',
  {
    'sub' : 'sub.rs',
  }
)

rlib2 = static_library('lib2', srcs, rust_abi : 'c')

bound_h = rust.cbindgen(srcs, 'lib2.h', config : 'config.toml')
test(
  'uses bound rust from structured_sources',
  executable('ctest2', 'test1.c', bound_h, c_args : '-DUSE_LIB2', link_with : rlib2)
)

# The requirement of C++20 for designated initializers means this may not be
# supported everywhere
if add_languages('cpp', native : false, required : false)
  rlib3 = static_library('lib3', 'lib.rs', rust_abi : 'c')

  bound_h = rust.cbindgen('lib.rs', 'lib3.hpp', config : 'config.toml')
  test(
    'generates a c++ header',
    executable('cpptest1', 'test1.cpp', bound_h, link_with : rlib2)
  )
endif
