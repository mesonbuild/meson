project('msvc dll versioning', 'c')

cc = meson.get_compiler('c')

if cc.get_id() != 'msvc'
  error('MESON_SKIP_TEST: test is only for msvc')
endif

# Test that MSVC creates foo-0.dll and bar.dll
shared_library('some', 'lib.c',
  version : '1.2.3',
  soversion : '0',
  install : true)

shared_library('noversion', 'lib.c',
  install : true)
