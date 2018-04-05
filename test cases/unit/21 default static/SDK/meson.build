project('default-static-sdk', 'c')

pkgg = import('pkgconfig')

lib = both_libraries('sdk', 'sdk.c', install: true)
pkgg.generate(lib)
