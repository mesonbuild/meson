project('compiler find dependency', 'c', 'cpp')

cc = meson.get_compiler('c')
cpp = meson.get_compiler('cpp')

foreach comp : [cc, cpp]
  assert (comp.find_dependency('stdio_int_' + comp.get_id(),
    headers_symbols: [['stdio.h', 'int'],]).found(),
    'base types should always be available')
  assert (not comp.find_dependency('limits_failure_' + comp.get_id(),
    headers_symbols: [['limits.h', 'guint64'],], required: false).found(),
    'guint64 is not defined in limits.h')
endforeach

if cc.find_library('z', required : false).found()
  zlib_dep = cc.find_dependency('zlib', libs: ['z'])
  assert (zlib_dep.found(), 'zlib has been found before.')

  assert (not cc.find_dependency('zlib_wrong_link', libs: ['z'],
    links: '''#include <glib.h>''', required: false).found(),
    '<glib.h> should not be includable.')

  executable('ztest', 'ztest.c', dependencies: zlib_dep)
endif
