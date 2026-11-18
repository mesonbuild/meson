# SPDX-License-Identifier: Apache-2.0
# Copyright © 2024 Intel Corporation

dep_zlib_sub = dep_zlib.partial_dependency(includes : true)

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
