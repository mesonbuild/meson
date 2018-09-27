project('pkg-config static dependency', 'c')

pkgconfig = import('pkgconfig')

install_headers('foo.h')

cargs = {'static_library' : '-DSTATIC_COMPILATION'}

libshared = shared_library('shared', 'shared.c',
  install : true)

libbar = both_libraries('bar', 'bar.c',
  c_args : cargs,
  install : true)

libfoo = both_libraries('foo', 'foo.c',
  link_with : [libbar, libshared],
  c_args : cargs,
  install : true)

pkgconfig.generate(libfoo)
