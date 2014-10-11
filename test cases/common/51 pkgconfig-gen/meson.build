project('pkgconfig-gen', 'c')

lib = shared_library('simple', 'simple.c', install : true)
libver = '1.0'
h = install_headers('simple.h')

pkgconfig_gen(libraries : lib, subdirs : '.', version : libver,
name : 'libsimple', filebase : 'simple', description : 'A simple demo library.')
