project('val1', 'c')
val1 = shared_library('val1', 'val1.c',
  build_rpath : '/XYZZYABCDE',
  install_rpath : get_option('prefix') / get_option('libdir'),
  install: true)
install_headers('val1.h')
pkgconfig = import('pkgconfig')
pkgconfig.generate(val1, libraries : ['-Wl,-rpath,${libdir}'])
