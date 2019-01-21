project('find fortran library', 'fortran')

fortranc = meson.get_compiler('fortran')

sources = ['main.f90', 'gzip.f90']
zlib = fortranc.find_library('z')

exe = executable('zlibtest', sources, dependencies : zlib)
test('testzlib', exe)
