project('library versions', 'c')

shared_library('some', 'lib.c',
  version : '1.2.3',
  soversion : '0',
  install : true)

shared_library('noversion', 'lib.c',
  install : true)

shared_library('onlyversion', 'lib.c',
  version : '1.4.5',
  install : true)

shared_library('onlysoversion', 'lib.c',
  # Also test that int soversion is acceptable
  soversion : 5,
  install : true)
