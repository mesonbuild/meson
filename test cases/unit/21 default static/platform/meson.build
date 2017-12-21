project('default-static-platform', 'c')

pkgg = import('pkgconfig')

lib = both_libraries('platform', 'platform.c', install: true)
pkgg.generate(lib)
