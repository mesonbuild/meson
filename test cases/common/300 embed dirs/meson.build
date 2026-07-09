# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Intel Corporation

project(
  'embed dirs',
  meson_version : '>= 1.13.0',
  default_options : {'c_std' : 'c23', 'cpp_std' : 'c++26'},
)

dep = declare_dependency(
  embed_directories : ['embed'],
)

if add_languages('c', required : false, native : false)
  exe = executable(
    'c_prog',
    'main.c',
    embed_directories : ['embed'],
  )

  test('C embed', exe)

  exe = executable(
    'c_with_dep',
    'main.c',
    dependencies : dep,
  )

  test('From dependency object', exe)
endif

if add_languages('cpp', required : false, native : false)
  exe = executable(
    'cpp_prog',
    'main.cpp',
    embed_directories : include_directories('embed'),
  )

  test('C++ embed', exe)
endif
