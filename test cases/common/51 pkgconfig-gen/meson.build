project('pkgconfig-gen', 'c')

pkgg = import('pkgconfig')

lib = shared_library('simple', 'simple.c', install : true)
libver = '1.0'
h = install_headers('simple.h')

pkgg.generate(
  libraries : lib,
  subdirs : '.',
  version : libver,
  name : 'libsimple',
  filebase : 'simple',
  description : 'A simple demo library.'
)
