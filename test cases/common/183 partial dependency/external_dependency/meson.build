# SPDX-License-Identifier: Apache-2.0
# Copyright © 2024 Intel Corporation

# TODO: don't use compile whenever we get includes and compile args separated
dep_zlib_sub = dep_zlib.partial_dependency(compile_args : true, includes : true)

executable(
  'zlib header only test',
  'header_only.c',
  dependencies : dep_zlib_sub,
)

executable(
  'zlib link test',
  'link.c',
  dependencies : [dep_zlib_sub, dep_zlib],
)
