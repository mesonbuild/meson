# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Intel Corporation

project(
  'default',
  'cpp',
  meson_version : '>= 1.12.0',
  default_options : {'cpp_std' : 'c++14'},
)

exe = executable(
  'prog',
  'prog.cpp',
  override_options : default(),
)

exe2 = executable(
  'prog2',
  'prog.cpp',
  kwargs : default(),
)

test_kwargs = {
  'protocol' : default(),
}

test('exe_test', exe, kwargs : test_kwargs)

testcase expect_error('default() objects are not allowed for required positional arguments')
  executable(default(), 'prog.cpp')
endtestcase

testcase expect_error('default() objects are not allowed for variadic arguments')
  add_languages(default())
endtestcase

testcase expect_error('default() objects are not allowed for optional positional arguments')
  assert(true, default())
endtestcase

testcase expect_error('"install_symlink" got a default() value for the required keyword argument "install_dir". default() may not be used for required keyword arguments.')
  install_symlink('foo', pointing_to : '/foo', install_dir : default())
endtestcase

foo = default()
get_variable('foo')
unset_variable('foo')
set_variable('var', default())
