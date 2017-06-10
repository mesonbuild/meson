project('LDFLAGS override extdeps', 'c')

subdir('lib')

zlib_dep = dependency('zlib')

e = executable('testzlib', 'main.c', dependencies : zlib_dep)

test('testzlib', e)
