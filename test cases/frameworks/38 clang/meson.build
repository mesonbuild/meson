# SPDX-License-Identifier: Apache-2.0
# Copyright © 2024 Intel Corporation

project('clangtest', 'c', 'cpp', default_options : ['c_std=c99', 'cpp_std=c++17'])

method = get_option('method')
static = get_option('link-static')

modules_to_find = [
  'clangIndex',
]

dep_clang_c = dependency('clang', modules : modules_to_find, method : 'system', static : static, required : false, language : 'c')
if not dep_clang_c.found()
  error('MESON_SKIP_TEST clang not found.')
endif

test_file = files('test.cpp')

exe = executable('parser', 'main.c', dependencies : dep_clang_c)
test('C API', exe, args : [test_file])
