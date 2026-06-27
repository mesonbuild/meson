# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Intel Corporation

if not add_languages('c', required : false, native : false)
  debug('No C language support')
  subdir_done()
endif

cc = meson.get_compiler('c')
if cc.get_id() == 'gcc'
  if cc.version().version_compare('< 15')
    debug('Skipping C test due to GCC being older than 15, and lacking support for #embed')
    subdir_done()
  endif
elif cc.get_id() == 'clang'
  if cc.version().version_compare('< 19')
    debug('Skipping C test due to Clang being older than 19, and lacking support for #embed')
    subdir_done()
  endif
else
  debug('Skipping C test due to compiler @0@, which is not known to support #embed'.format(cc.get_id()))
  subdir_done()
endif

exe = executable(
  'c_prog',
  'main.c',
  embed_directories : embed_dir,
)

test('C embed', exe)

exe = executable(
  'c_with_dep',
  'main.c',
  dependencies : dep,
)

test('From dependency object', exe)
