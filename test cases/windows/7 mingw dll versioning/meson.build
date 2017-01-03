project('mingw dll versioning', 'c')

cc = meson.get_compiler('c')

if cc.get_id() == 'msvc'
  error('MESON_SKIP_TEST: test is only for MinGW')
endif

# Test that MinGW/GCC creates correctly-named dll files and dll.a files,
# and also installs them in the right place
shared_library('some', 'lib.c',
  version : '1.2.3',
  soversion : '0',
  install : true)

shared_library('noversion', 'lib.c',
  install : true)
