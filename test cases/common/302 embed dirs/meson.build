# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Intel Corporation

project(
  'embed dirs',
  meson_version : '>= 1.13.0',
  default_options : {'c_std' : 'c23', 'cpp_std' : 'c++26'},
)

embed_dir = include_directories('embed')

dep = declare_dependency(
  embed_directories : ['embed'],
)

subdir('c')
subdir('cpp')
