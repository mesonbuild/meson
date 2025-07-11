# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Intel Corporation

project(
  'host and build languages',
  host_machine_languages : ['cpp', 'c'],
  build_machine_languages : ['cpp'],
  license : 'Apache-2.0',
  meson_version : '>= 1.8.0',
)

host_main = executable(
  'main_for_host',
  'lib.c', 'main.cpp',
  cpp_args : ['-DHOST_BUILD', '-DFOR_MACHINE="host"'],
  native : false,
)

test('host', host_main)

build_main = executable(
  'main_for_build',
  'main.cpp',
  cpp_args : ['-DFOR_MACHINE="build"'],
  native : true,
)

test('build', build_main)
