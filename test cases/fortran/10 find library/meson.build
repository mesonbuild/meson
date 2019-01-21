project('find fortran library', 'fortran')

fortranc = meson.get_compiler('fortran')

sources = ['main.f90', 'gzip.f90']
zlib = dependency('zlib')

exe = executable('zlibtest', sources, dependencies : zlib)
test('testzlib', exe)
