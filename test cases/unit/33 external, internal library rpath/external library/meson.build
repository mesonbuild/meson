project('system library', 'c')

shared_library('foo_in_system', 'foo.c', install : true)
l = shared_library('faa_pkg', 'faa.c', install: true)

pkg = import('pkgconfig')
pkg.generate(name: 'faa_pkg',
             libraries: l,
             description: 'FAA, a pkg-config test library')
