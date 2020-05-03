project('val2', 'c')
val2 = shared_library('val2', 'val2.c',
  install_rpath : get_option('prefix') / get_option('libdir'),
  install: true)
install_headers('val2.h')
pkgconfig = import('pkgconfig')
pkgconfig.generate(val2, libraries : ['-Wl,-rpath,${libdir}'])
