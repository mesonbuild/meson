project('libPCTest42', ['c'])

lib = static_library('libPCTest42', 'libPCTest.c')

pkg = import('pkgconfig')
pkg.generate(lib, description: 'just a test lib (42)')
