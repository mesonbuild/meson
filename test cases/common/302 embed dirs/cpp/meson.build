# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Intel Corporation

if not add_languages('cpp', required : false, native : false)
  debug('No C++ support')
  subdir_done()
endif

cpp = meson.get_compiler('cpp')
if cpp.get_id() == 'gcc'
  if cpp.version().version_compare('< 15')
    debug('Skipping C++ test due to G++ being older than 15, and lacking support for #embed')
    subdir_done()
  endif
elif cpp.get_id() == 'clang'
  if cpp.version().version_compare('< 19')
    debug('Skipping C++ test due to Clang++ being older than 19, and lacking support for #embed')
    subdir_done()
  endif
else
  debug('Skipping C++ test due to compiler @0@, which is not known to support #embed'.format(cpp.get_id()))
  subdir_done()
endif

exe = executable(
  'cpp_prog',
  'main.cpp',
  embed_directories : '../embed',
)

test('C++ embed', exe)
