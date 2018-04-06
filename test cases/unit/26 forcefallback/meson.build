project('mainproj', 'c',
  default_options : ['wrap_mode=forcefallback'])

zlib_dep = dependency('zlib', fallback: ['notzlib', 'zlib_dep'])

test_not_zlib = executable('test_not_zlib', ['test_not_zlib.c'], dependencies: [zlib_dep])

test('test_not_zlib', test_not_zlib)
