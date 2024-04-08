# SPDX-License-Identifier: Apache-2.0
# Copyright © 2024 Intel Corporation

test(
  'generated include directories from subdir',
  executable(
    'gid3',
    include_gen.process(
      '../include/1.c.in',
      include_directories : inc_private,
    ),
  ),
  should_fail : true,
)
