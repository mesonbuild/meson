# SPDX-License-Identifier: Apache-2.0
# Copyright © 2024 Intel Corporation

project('cbindgen', 'rust', 'c', meson_version : '>= 1.5')

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
